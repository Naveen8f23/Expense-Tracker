import Foundation

/// Drives BACKLOG.md J7's sync-health indicator — a small colored dot in the Ledger tab's nav bar
/// reflecting `GET /sync/status` (B5/E7), mirroring the confirmed design. Tapping it reveals the
/// full scanned/matched/skipped/failed counts the endpoint already returns. Framework-agnostic
/// (no SwiftUI import) like the other stores — the view maps `health` to an actual color.
@MainActor
final class SyncHealthStore: ObservableObject {
    enum Health: Equatable {
        case unknown
        case notConnected
        case pendingFirstSync
        case healthy
        case issues
    }

    @Published private(set) var status: SyncStatus?
    @Published private(set) var health: Health = .unknown
    @Published private(set) var errorMessage: String?

    private let makeClient: (URL) -> APIClient

    init(makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) }) {
        self.makeClient = makeClient
    }

    func load(baseURL: URL?) async {
        guard let baseURL else {
            status = nil
            errorMessage = "Set up the backend connection first (gear icon)."
            health = .unknown
            return
        }
        do {
            let result = try await makeClient(baseURL).syncStatus()
            status = result
            errorMessage = nil
            health = Self.classify(result)
        } catch APIError.httpError(404, _) {
            // No Gmail account connected yet — a real, distinct state, not an error (mirrors
            // ConnectionSettingsStore's own treatment of the same 404).
            status = nil
            errorMessage = nil
            health = .notConnected
        } catch {
            status = nil
            errorMessage = Self.describe(error)
            health = .unknown
        }
    }

    private static func classify(_ status: SyncStatus) -> Health {
        guard status.connected else { return .notConnected }
        guard status.synced else { return .pendingFirstSync }
        if status.lastError != nil || (status.lastFailed ?? 0) > 0 { return .issues }
        return .healthy
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
