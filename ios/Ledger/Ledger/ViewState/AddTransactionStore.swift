import Foundation

/// Drives BACKLOG.md M1 — the manual "add a transaction" escape hatch (COR-5, mirrors web H2).
/// Create-only: no fetch, no edit of an existing transaction (that's J3's job). Same per-call-
/// `baseURL`, injectable-client-factory shape as the other stores for testability.
@MainActor
final class AddTransactionStore: ObservableObject {
    @Published private(set) var isSaving = false
    @Published private(set) var errorMessage: String?

    private let makeClient: (URL) -> APIClient

    init(makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) }) {
        self.makeClient = makeClient
    }

    /// BACKLOG.md M1 reuses J6's inline "+ New category…" pattern.
    func createCategory(baseURL: URL?, name: String) async -> Category? {
        guard let baseURL else { return nil }
        do {
            return try await makeClient(baseURL).createCategory(name: name)
        } catch {
            errorMessage = Self.describe(error)
            return nil
        }
    }

    @discardableResult
    func save(baseURL: URL?, request: ManualTransactionRequest) async -> Bool {
        guard let baseURL else {
            errorMessage = "Set up the backend connection first (gear icon)."
            return false
        }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }
        do {
            _ = try await makeClient(baseURL).addManualTransaction(request)
            return true
        } catch {
            errorMessage = Self.describe(error)
            return false
        }
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
