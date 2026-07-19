import Foundation

/// Drives BACKLOG.md L3 — a payee's running history and total (ANL-3), reached by tapping a payee
/// name anywhere it appears (transaction rows, the review queue). Same per-call-`baseURL`,
/// injectable-client-factory shape as the other stores for testability.
@MainActor
final class PayeeHistoryStore: ObservableObject {
    @Published private(set) var summary: PayeeHistoryResponse?
    @Published private(set) var transactions: [Transaction] = []
    @Published private(set) var categories: [Category] = []
    @Published private(set) var isLoading = false
    @Published private(set) var isLoadingMore = false
    @Published private(set) var errorMessage: String?

    var hasMore: Bool {
        guard let summary else { return false }
        return transactions.count < summary.transactionCount
    }

    private let makeClient: (URL) -> APIClient

    init(makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) }) {
        self.makeClient = makeClient
    }

    func load(baseURL: URL?, payee: String) async {
        guard let baseURL else {
            errorMessage = "Set up the backend connection first (gear icon)."
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let client = makeClient(baseURL)
            let response = try await client.payeeHistory(payee: payee)
            summary = response
            transactions = response.items
            if categories.isEmpty {
                categories = try await client.listCategories().items
            }
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    func loadMore(baseURL: URL?, payee: String) async {
        guard let baseURL, hasMore, !isLoadingMore else { return }
        isLoadingMore = true
        defer { isLoadingMore = false }
        do {
            let response = try await makeClient(baseURL).payeeHistory(payee: payee, offset: transactions.count)
            transactions.append(contentsOf: response.items)
            summary = response
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
