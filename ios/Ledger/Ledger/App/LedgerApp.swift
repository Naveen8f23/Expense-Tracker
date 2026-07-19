import BackgroundTasks
import SwiftUI

@main
struct LedgerApp: App {
    // Owned here (not per-view) so every later screen (J1 onward) can build an `APIClient` from
    // the same saved connection settings via `@EnvironmentObject`.
    @StateObject private var connectionSettings = ConnectionSettingsStore()
    @Environment(\.scenePhase) private var scenePhase

    /// BACKLOG.md M3 — a best-effort supplement to M2's foreground polling, explicitly documented
    /// as unreliable (Constitution principle 21): iOS decides if/when this actually runs, based on
    /// the owner's own usage patterns and battery state, often not more than a few times a day or
    /// less. This is never to be presented as a dependable channel.
    static let backgroundRefreshIdentifier = "com.naveen8f23.Ledger.refresh"

    init() {
        // Must happen before the app finishes launching, so this runs in `init()` rather than
        // waiting for the first view to appear (registering `using: nil` runs the handler on a
        // background queue BGTaskScheduler manages itself).
        BGTaskScheduler.shared.register(forTaskWithIdentifier: Self.backgroundRefreshIdentifier, using: nil) { task in
            // The launch handler itself isn't guaranteed to run on the main actor, but the work
            // it kicks off (constructing `NewTransactionNotifier`/`ConnectionSettingsStore`, both
            // @MainActor) needs to be — hop explicitly rather than widening either type's
            // isolation just for this one caller.
            Task { @MainActor in
                // BGTaskScheduler guarantees this matches the identifier's own declared type; a
                // mismatch here would be a framework-level bug, not a runtime data issue.
                Self.handleAppRefresh(task as! BGAppRefreshTask)
            }
        }
    }

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(connectionSettings)
                // Requested directly by the owner: Ledger is always dark, regardless of the
                // phone's own system light/dark setting — a fixed identity, not a toggle. Applied
                // once here at the window root so it also covers every `.sheet`/`.alert` presented
                // from anywhere in the app, not just the root hierarchy itself. Safe to do broadly
                // since every view already uses semantic/system colors (`.primary`, `.secondary`,
                // system list backgrounds, SwiftUI's built-in adaptive palette for
                // `CategoryColor`) rather than any hardcoded light-only color — confirmed by
                // grepping for `Color.white`/`Color.black`/`UIColor` before making this change.
                .preferredColorScheme(.dark)
        }
        .onChange(of: scenePhase) { _, newPhase in
            if newPhase == .background {
                Self.scheduleAppRefresh()
            }
        }
    }

    /// iOS treats `earliestBeginDate` as a hint, not a promise — actual timing is entirely up to
    /// the system. Re-submitted every time a refresh runs (successfully or not) and every time the
    /// app backgrounds, since a `BGAppRefreshTaskRequest` is consumed the moment iOS acts on it.
    private static func scheduleAppRefresh() {
        let request = BGAppRefreshTaskRequest(identifier: backgroundRefreshIdentifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 15 * 60)
        try? BGTaskScheduler.shared.submit(request)
    }

    @MainActor
    private static func handleAppRefresh(_ task: BGAppRefreshTask) {
        // Keep the mechanism alive for next time regardless of how this run goes.
        scheduleAppRefresh()

        let notifier = NewTransactionNotifier()
        let connectionSettings = ConnectionSettingsStore()
        let operation = Task {
            if let baseURL = connectionSettings.baseURL {
                await notifier.poll(baseURL: baseURL)
            }
            task.setTaskCompleted(success: true)
        }
        task.expirationHandler = {
            operation.cancel()
        }
    }
}
