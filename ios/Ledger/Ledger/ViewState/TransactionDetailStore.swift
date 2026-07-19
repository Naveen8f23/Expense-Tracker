import Foundation

/// Drives BACKLOG.md J3 — loading a single transaction, correcting it, and dismissing it
/// ("Not a real expense," COR-4). Same per-call-`baseURL`, injectable-client-factory shape as
/// `TransactionListStore`/`ConnectionSettingsStore` for testability.
@MainActor
final class TransactionDetailStore: ObservableObject {
    @Published private(set) var transaction: Transaction?
    @Published private(set) var isLoading = false
    @Published private(set) var isSaving = false
    @Published private(set) var errorMessage: String?

    private let makeClient: (URL) -> APIClient

    init(makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) }) {
        self.makeClient = makeClient
    }

    func load(baseURL: URL?, id: Int) async {
        guard let baseURL else {
            errorMessage = "Set up the backend connection first (gear icon)."
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            transaction = try await makeClient(baseURL).getTransaction(id: id)
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    /// Returns `true` on success so the view knows to dismiss and tell its parent to refresh.
    @discardableResult
    func save(baseURL: URL?, correction: TransactionCorrectionRequest) async -> Bool {
        guard let baseURL, let id = transaction?.id else { return false }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }
        do {
            transaction = try await makeClient(baseURL).correctTransaction(id: id, correction)
            return true
        } catch {
            errorMessage = Self.describe(error)
            return false
        }
    }

    @discardableResult
    func dismissTransaction(baseURL: URL?) async -> Bool {
        guard let baseURL, let id = transaction?.id else { return false }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }
        do {
            transaction = try await makeClient(baseURL).dismissTransaction(id: id)
            return true
        } catch {
            errorMessage = Self.describe(error)
            return false
        }
    }

    /// BACKLOG.md J6 — inline "+ New category…" from the detail sheet's picker (mirrors web F5).
    /// Returns the created `Category` so the caller can select it and add it to the picker's
    /// local options without waiting for a full categories refresh.
    func createCategory(baseURL: URL?, name: String) async -> Category? {
        guard let baseURL else { return nil }
        do {
            return try await makeClient(baseURL).createCategory(name: name)
        } catch {
            errorMessage = Self.describe(error)
            return nil
        }
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
