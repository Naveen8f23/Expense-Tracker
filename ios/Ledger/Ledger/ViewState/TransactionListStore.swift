import Foundation

/// Drives the Ledger tab's transaction list (BACKLOG.md J1). Takes `baseURL` per call rather
/// than holding a reference to `ConnectionSettingsStore` — keeps this store constructible with a
/// plain no-arg initializer (simpler `@StateObject` wiring) and always uses whatever `baseURL`
/// the caller currently has, so an edited connection setting takes effect on the next load
/// without this store needing to observe `ConnectionSettingsStore` itself.
@MainActor
final class TransactionListStore: ObservableObject {
    @Published private(set) var transactions: [Transaction] = []
    @Published private(set) var total: Int = 0
    @Published private(set) var categories: [Category] = []
    @Published private(set) var isLoading = false
    @Published private(set) var isLoadingMore = false
    @Published private(set) var errorMessage: String?

    var hasMore: Bool { transactions.count < total }

    private let makeClient: (URL) -> APIClient

    init(makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) }) {
        self.makeClient = makeClient
    }

    /// Fetches the first page, replacing whatever was previously loaded.
    func load(baseURL: URL?, filters: TransactionFilters) async {
        guard let baseURL else {
            errorMessage = "Set up the backend connection first (gear icon)."
            transactions = []
            total = 0
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        var firstPage = filters
        firstPage.offset = 0
        do {
            let client = makeClient(baseURL)
            let response = try await client.listTransactions(firstPage)
            transactions = response.items
            total = response.total
            // Categories are only needed for the filter sheet's picker — fetched once per load
            // rather than on every keystroke, since they change rarely.
            if categories.isEmpty {
                categories = try await client.listCategories().items
            }
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    /// Fetches the next page and appends it (BACKLOG.md J1's pagination criterion).
    func loadMore(baseURL: URL?, filters: TransactionFilters) async {
        guard let baseURL, hasMore, !isLoadingMore else { return }
        isLoadingMore = true
        defer { isLoadingMore = false }

        var nextPage = filters
        nextPage.offset = transactions.count
        do {
            let response = try await makeClient(baseURL).listTransactions(nextPage)
            transactions.append(contentsOf: response.items)
            total = response.total
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
