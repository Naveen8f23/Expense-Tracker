import Foundation

/// Drives BACKLOG.md J6's "Manage categories" screen — full CRUD (list, create, rename, delete
/// with reassign-on-delete), reached from the gear-icon toolbar alongside Connection Settings.
/// Same per-call-`baseURL`, injectable-client-factory shape as the other stores for testability.
@MainActor
final class CategoryManagementStore: ObservableObject {
    @Published private(set) var categories: [Category] = []
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?

    /// Set when a delete failed because the category is in use (E6's 409 + affected count) — the
    /// view offers a reassignment picker in response instead of a dead end, per J6's acceptance
    /// criterion that this must be a real flow, not a silent failure.
    @Published private(set) var pendingReassignment: PendingReassignment?

    struct PendingReassignment: Identifiable {
        let id: Int
        let name: String
        let transactionCount: Int
    }

    private let makeClient: (URL) -> APIClient

    init(makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) }) {
        self.makeClient = makeClient
    }

    func load(baseURL: URL?) async {
        guard let baseURL else {
            errorMessage = "Set up the backend connection first (gear icon)."
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            categories = try await makeClient(baseURL).listCategories().items
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    @discardableResult
    func createCategory(baseURL: URL?, name: String) async -> Bool {
        guard let baseURL else { return false }
        do {
            let created = try await makeClient(baseURL).createCategory(name: name)
            categories.append(created)
            sortCategories()
            return true
        } catch {
            errorMessage = Self.describe(error)
            return false
        }
    }

    @discardableResult
    func renameCategory(baseURL: URL?, id: Int, name: String) async -> Bool {
        guard let baseURL else { return false }
        do {
            let updated = try await makeClient(baseURL).renameCategory(id: id, name: name)
            if let index = categories.firstIndex(where: { $0.id == id }) {
                categories[index] = updated
            }
            sortCategories()
            return true
        } catch {
            errorMessage = Self.describe(error)
            return false
        }
    }

    /// Attempts a plain delete first. If the category is in use, records `pendingReassignment`
    /// rather than surfacing a dead-end error, so the view can offer a reassignment target.
    func deleteCategory(baseURL: URL?, id: Int) async {
        guard let baseURL else { return }
        do {
            try await makeClient(baseURL).deleteCategory(id: id)
            categories.removeAll { $0.id == id }
        } catch APIError.categoryInUse(let message, let transactionCount) {
            let name = categories.first(where: { $0.id == id })?.name ?? message
            pendingReassignment = PendingReassignment(id: id, name: name, transactionCount: transactionCount)
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    /// Completes a delete that was blocked by `pendingReassignment`, moving its transactions to
    /// `reassignTo` first (E6).
    func confirmReassignmentAndDelete(baseURL: URL?, reassignTo: Int) async {
        guard let baseURL, let pending = pendingReassignment else { return }
        do {
            try await makeClient(baseURL).deleteCategory(id: pending.id, reassignTo: reassignTo)
            categories.removeAll { $0.id == pending.id }
            pendingReassignment = nil
        } catch {
            errorMessage = Self.describe(error)
            pendingReassignment = nil
        }
    }

    func cancelReassignment() {
        pendingReassignment = nil
    }

    private func sortCategories() {
        categories.sort { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
