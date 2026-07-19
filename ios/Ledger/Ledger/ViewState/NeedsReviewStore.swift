import Foundation

/// Drives BACKLOG.md Epic K's Review tab — both halves `GET /needs-review` returns (E5): emails
/// that never became a transaction at all, and transactions an AI fallback produced but that were
/// never auto-accepted (EXT-4/EXT-5). Same per-call-`baseURL`, injectable-client-factory shape as
/// the other stores for testability.
@MainActor
final class NeedsReviewStore: ObservableObject {
    @Published private(set) var unmatchedEmails: [EmailMessage] = []
    @Published private(set) var lowConfidenceTransactions: [Transaction] = []
    @Published private(set) var categories: [Category] = []
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var actionErrorMessage: String?

    /// BACKLOG.md K4 — the Review tab's badge count, as of the last fetch (not live/real-time;
    /// there is no push mechanism to update it silently in the background, ADR-0024).
    var totalCount: Int { unmatchedEmails.count + lowConfidenceTransactions.count }

    private let makeClient: (URL) -> APIClient

    init(makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) }) {
        self.makeClient = makeClient
    }

    func load(baseURL: URL?) async {
        guard let baseURL else {
            errorMessage = "Set up the backend connection first (gear icon)."
            unmatchedEmails = []
            lowConfidenceTransactions = []
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let client = makeClient(baseURL)
            let response = try await client.needsReviewQueue()
            unmatchedEmails = response.unmatchedEmails
            lowConfidenceTransactions = response.lowConfidenceTransactions
            // Only needed for K3's detail sheet picker — fetched once per load, same reasoning as
            // TransactionListStore's own categories fetch.
            if categories.isEmpty {
                categories = try await client.listCategories().items
            }
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    /// BACKLOG.md K2 — swipe-to-ignore for an unmatched email. Removed from the local list on
    /// success rather than waiting for a reload, mirroring `TransactionListStore.dismissTransaction`.
    @discardableResult
    func ignoreEmail(baseURL: URL?, id: Int) async -> Bool {
        guard let baseURL else { return false }
        do {
            _ = try await makeClient(baseURL).ignoreNeedsReviewEmail(id: id)
            unmatchedEmails.removeAll { $0.id == id }
            return true
        } catch {
            actionErrorMessage = Self.describe(error)
            return false
        }
    }

    func clearActionError() {
        actionErrorMessage = nil
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
