import SwiftUI

@main
struct LedgerApp: App {
    // Owned here (not per-view) so every later screen (J1 onward) can build an `APIClient` from
    // the same saved connection settings via `@EnvironmentObject`.
    @StateObject private var connectionSettings = ConnectionSettingsStore()

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(connectionSettings)
        }
    }
}
