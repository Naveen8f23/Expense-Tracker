import Foundation

/// Holds the backend connection settings (BACKLOG.md I3, REQUIREMENTS.md MOB-5) and performs the
/// reachability check. Owned at the app level (`LedgerApp`) and shared via `environmentObject` so
/// later stories (J1 onward) can build an `APIClient` from the same saved `baseURL` without each
/// screen re-reading `UserDefaults` itself.
///
/// Plain `UserDefaults`, not Keychain — a Tailscale hostname/port isn't a credential (I3).
@MainActor
final class ConnectionSettingsStore: ObservableObject {
    enum ReachabilityState: Equatable {
        case unknown
        case checking
        case reachable(connected: Bool, synced: Bool)
        case unreachable(String)
    }

    @Published var host: String
    @Published var port: String
    @Published private(set) var reachability: ReachabilityState = .unknown

    private let defaults: UserDefaults
    /// Builds the `APIClient` used for the reachability check. Defaults to a real client, but
    /// tests inject one backed by a `StubURLSession` — the same testability seam as `APIClient`
    /// itself (BACKLOG.md I2), so this store's logic is verifiable with no real backend running.
    private let makeClient: (URL) -> APIClient
    private static let hostKey = "connectionSettings.host"
    private static let portKey = "connectionSettings.port"

    init(defaults: UserDefaults = .standard, makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) }) {
        self.defaults = defaults
        self.makeClient = makeClient
        self.host = defaults.string(forKey: Self.hostKey) ?? ""
        self.port = defaults.string(forKey: Self.portKey) ?? "8000"
    }

    var baseURL: URL? {
        let trimmedHost = host.trimmingCharacters(in: .whitespaces)
        guard !trimmedHost.isEmpty, let portNumber = Int(port), portNumber > 0 else { return nil }
        // Plain HTTP: the backend has no TLS certificate — it's only ever reached over the
        // owner's private Tailscale network (ADR-0002, ADR-0020, ADR-0025), never the public
        // internet. See the ATS exception in Info.plist.
        return URL(string: "http://\(trimmedHost):\(portNumber)")
    }

    func save() {
        defaults.set(host, forKey: Self.hostKey)
        defaults.set(port, forKey: Self.portKey)
    }

    func checkReachability() async {
        guard let baseURL else {
            reachability = .unreachable("Enter a host and port first")
            return
        }
        reachability = .checking
        let client = makeClient(baseURL)

        do {
            _ = try await client.health()
        } catch {
            reachability = .unreachable(Self.describe(error))
            return
        }

        // The backend is reachable at this point (health succeeded). A 404 from /sync/status
        // just means no Gmail account is connected yet — that's still "reachable," not an error.
        do {
            let status = try await client.syncStatus()
            reachability = .reachable(connected: status.connected, synced: status.synced)
        } catch APIError.httpError(404, _) {
            reachability = .reachable(connected: false, synced: false)
        } catch {
            reachability = .reachable(connected: false, synced: false)
        }
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
