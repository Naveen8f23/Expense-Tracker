import Foundation

/// Wraps every backend endpoint Ledger calls (BACKLOG.md I2) — no view or view-state type is
/// permitted to use `URLSession` directly (see `ios/Ledger/README.md`'s dependency-direction
/// rule), the same discipline `frontend/src/api/client.ts` follows for the web dashboard.
final class APIClient {
    private let baseURL: URL
    private let session: URLSessionProtocol
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(baseURL: URL, session: URLSessionProtocol = URLSession.shared) {
        self.baseURL = baseURL
        self.session = session
        self.decoder = JSONDecoder()
        self.decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.encoder = JSONEncoder()
        self.encoder.keyEncodingStrategy = .convertToSnakeCase
    }

    // MARK: - Transactions (E1-E4, H2)

    func listTransactions(_ filters: TransactionFilters = TransactionFilters()) async throws -> TransactionListResponse {
        var query: [URLQueryItem] = [
            .init(name: "limit", value: String(filters.limit)),
            .init(name: "offset", value: String(filters.offset)),
        ]
        if let payee = filters.payee { query.append(.init(name: "payee", value: payee)) }
        if let categoryId = filters.categoryId { query.append(.init(name: "category_id", value: String(categoryId))) }
        if let dateFrom = filters.dateFrom { query.append(.init(name: "date_from", value: dateFrom)) }
        if let dateTo = filters.dateTo { query.append(.init(name: "date_to", value: dateTo)) }
        if let amountMin = filters.amountMin { query.append(.init(name: "amount_min", value: amountMin)) }
        if let amountMax = filters.amountMax { query.append(.init(name: "amount_max", value: amountMax)) }
        if let paymentMethod = filters.paymentMethod { query.append(.init(name: "payment_method", value: paymentMethod)) }
        if let txnType = filters.txnType { query.append(.init(name: "txn_type", value: txnType)) }
        if let q = filters.q { query.append(.init(name: "q", value: q)) }
        return try await get("/transactions", query: query)
    }

    func getTransaction(id: Int) async throws -> Transaction {
        try await get("/transactions/\(id)")
    }

    func correctTransaction(id: Int, _ correction: TransactionCorrectionRequest) async throws -> Transaction {
        try await send("/transactions/\(id)", method: "PATCH", body: correction)
    }

    func dismissTransaction(id: Int) async throws -> Transaction {
        try await sendNoBody("/transactions/\(id)/dismiss", method: "POST")
    }

    func addManualTransaction(_ request: ManualTransactionRequest) async throws -> Transaction {
        try await send("/transactions", method: "POST", body: request)
    }

    func recentTransactions(sinceId: Int) async throws -> RecentTransactionsResponse {
        try await get("/transactions/recent", query: [.init(name: "since_id", value: String(sinceId))])
    }

    // MARK: - Needs-review (E5, F4 addendum)

    func needsReviewQueue() async throws -> NeedsReviewResponse {
        try await get("/needs-review")
    }

    func ignoreNeedsReviewEmail(id: Int) async throws -> EmailMessage {
        try await sendNoBody("/needs-review/emails/\(id)/ignore", method: "POST")
    }

    // MARK: - Categories (E6)

    func listCategories() async throws -> CategoryListResponse {
        try await get("/categories")
    }

    func createCategory(name: String) async throws -> Category {
        try await send("/categories", method: "POST", body: CategoryCreateRequest(name: name))
    }

    func renameCategory(id: Int, name: String) async throws -> Category {
        try await send("/categories/\(id)", method: "PATCH", body: CategoryRenameRequest(name: name))
    }

    /// Throws `APIError.categoryInUse` (not a plain `.httpError`) for the one endpoint whose 409
    /// body is a nested object rather than a plain string `detail` (BACKLOG.md I2 ground truth).
    func deleteCategory(id: Int, reassignTo: Int? = nil) async throws {
        var query: [URLQueryItem] = []
        if let reassignTo { query.append(.init(name: "reassign_to", value: String(reassignTo))) }
        let (data, status) = try await perform("/categories/\(id)", method: "DELETE", query: query)
        guard (200..<300).contains(status) else {
            if status == 409, let conflict = try? decoder.decode(CategoryInUseWrapper.self, from: data) {
                throw APIError.categoryInUse(message: conflict.detail.message, transactionCount: conflict.detail.transactionCount)
            }
            throw APIError.httpError(status: status, detail: extractDetail(from: data))
        }
    }

    // MARK: - Sync status (E7)

    func syncStatus() async throws -> SyncStatus {
        try await get("/sync/status")
    }

    func health() async throws -> HealthStatus {
        try await get("/health")
    }

    // MARK: - Analytics (G2-G4)

    func monthlyAnalytics(month: String? = nil) async throws -> MonthlyAnalytics {
        var query: [URLQueryItem] = []
        if let month { query.append(.init(name: "month", value: month)) }
        return try await get("/analytics/monthly", query: query)
    }

    func categoryBreakdown(month: String? = nil) async throws -> CategoryBreakdownResponse {
        var query: [URLQueryItem] = []
        if let month { query.append(.init(name: "month", value: month)) }
        return try await get("/analytics/by-category", query: query)
    }

    /// Flexible day/week/month/year summary — a separate endpoint from `monthlyAnalytics` above,
    /// which stays exactly as it was for the web dashboard (BACKLOG.md L1 follow-up).
    func periodAnalytics(period: String, date: String) async throws -> PeriodAnalytics {
        try await get(
            "/analytics/summary",
            query: [.init(name: "period", value: period), .init(name: "date", value: date)]
        )
    }

    func periodCategoryBreakdown(period: String, date: String) async throws -> PeriodCategoryBreakdownResponse {
        try await get(
            "/analytics/category-breakdown",
            query: [.init(name: "period", value: period), .init(name: "date", value: date)]
        )
    }

    func payeeHistory(payee: String, limit: Int = 50, offset: Int = 0) async throws -> PayeeHistoryResponse {
        // `payee` is passed as its own path segment (not string-interpolated into `path`) so
        // `perform` percent-encodes it exactly once, however many spaces/special characters a
        // real payee name contains — see `perform`'s segment-by-segment URL construction below.
        try await get(
            "/analytics/by-payee",
            pathComponents: [payee],
            query: [.init(name: "limit", value: String(limit)), .init(name: "offset", value: String(offset))]
        )
    }

    // MARK: - Request plumbing

    private func get<T: Decodable>(_ path: String, pathComponents: [String] = [], query: [URLQueryItem] = []) async throws -> T {
        let (data, status) = try await perform(path, method: "GET", pathComponents: pathComponents, query: query)
        return try decodeOrThrow(T.self, data: data, status: status)
    }

    private func send<T: Decodable, Body: Encodable>(_ path: String, method: String, body: Body) async throws -> T {
        let jsonBody = try encoder.encode(body)
        let (data, status) = try await perform(path, method: method, jsonBody: jsonBody)
        return try decodeOrThrow(T.self, data: data, status: status)
    }

    private func sendNoBody<T: Decodable>(_ path: String, method: String) async throws -> T {
        let (data, status) = try await perform(path, method: method)
        return try decodeOrThrow(T.self, data: data, status: status)
    }

    private func perform(
        _ path: String,
        method: String,
        pathComponents: [String] = [],
        query: [URLQueryItem] = [],
        jsonBody: Data? = nil
    ) async throws -> (Data, Int) {
        // Build the URL segment-by-segment so each component (including a raw, unescaped payee
        // name) is percent-encoded exactly once by `appendingPathComponent` — string-interpolating
        // an already-escaped value into `path` and letting a single `appendingPathComponent` call
        // handle the whole string risks double-encoding (e.g. "%20" becoming "%2520").
        var resolvedURL = baseURL
        for segment in path.split(separator: "/") {
            resolvedURL = resolvedURL.appendingPathComponent(String(segment))
        }
        for component in pathComponents {
            resolvedURL = resolvedURL.appendingPathComponent(component)
        }
        guard var components = URLComponents(url: resolvedURL, resolvingAgainstBaseURL: false) else {
            throw APIError.decodingFailed("Could not build a URL for \(path)")
        }
        if !query.isEmpty {
            components.queryItems = query
        }
        guard let url = components.url else {
            throw APIError.decodingFailed("Could not build a URL for \(path)")
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        // A short, explicit timeout — not URLRequest's ~60s default — so an unreachable/wrong
        // host fails fast into `.unreachable` instead of looking like a hang (I3's "not an
        // infinite spinner" acceptance criterion).
        request.timeoutInterval = 8
        if let jsonBody {
            request.httpBody = jsonBody
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.unreachable(error.localizedDescription)
        }
        guard let http = response as? HTTPURLResponse else {
            throw APIError.unreachable("No HTTP response received")
        }
        return (data, http.statusCode)
    }

    private func decodeOrThrow<T: Decodable>(_ type: T.Type, data: Data, status: Int) throws -> T {
        guard (200..<300).contains(status) else {
            throw APIError.httpError(status: status, detail: extractDetail(from: data))
        }
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingFailed(String(describing: error))
        }
    }

    private func extractDetail(from data: Data) -> String {
        if let wrapper = try? decoder.decode(DetailStringWrapper.self, from: data) {
            return wrapper.detail
        }
        return String(data: data, encoding: .utf8) ?? "Unknown error"
    }
}

private struct DetailStringWrapper: Decodable {
    let detail: String
}

private struct CategoryInUseWrapper: Decodable {
    let detail: CategoryInUseDetail
}

private struct CategoryInUseDetail: Decodable {
    let message: String
    let transactionCount: Int
}

struct HealthStatus: Codable, Equatable {
    let status: String
}
