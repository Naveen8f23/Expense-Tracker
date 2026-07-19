import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    // Owned here, not inside ReviewView, so its BACKLOG.md K4 badge count is visible on the tab
    // item itself — a child view's @StateObject can't be read from the parent TabView around it.
    @StateObject private var needsReviewStore = NeedsReviewStore()
    @State private var selectedTab = 0
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TabView(selection: $selectedTab) {
            LedgerListView()
                .tabItem {
                    Label("Ledger", systemImage: "list.bullet.rectangle")
                }
                .tag(0)

            AnalyticsView()
                .tabItem {
                    Label("Analytics", systemImage: "chart.pie")
                }
                .tag(1)

            ReviewView(store: needsReviewStore)
                .tabItem {
                    Label("Review", systemImage: "checklist")
                }
                .tag(2)
                // A 0-value badge renders nothing, so this naturally hides once the queue is empty.
                .badge(needsReviewStore.totalCount)
        }
        .task { await refreshNeedsReview() }
        // BACKLOG.md K4 — the badge reflects the queue size "as of the last time it was fetched
        // (app foreground/tab switch)", not a live count. These are the only two refresh triggers;
        // there is no polling/push mechanism (ADR-0024).
        .onChange(of: selectedTab) { _, newValue in
            if newValue == 2 { Task { await refreshNeedsReview() } }
        }
        .onChange(of: scenePhase) { _, newPhase in
            if newPhase == .active { Task { await refreshNeedsReview() } }
        }
    }

    private func refreshNeedsReview() async {
        await needsReviewStore.load(baseURL: connectionSettings.baseURL)
    }
}

#Preview {
    RootTabView()
        .environmentObject(ConnectionSettingsStore())
}
