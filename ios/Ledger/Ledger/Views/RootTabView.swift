import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    // Owned here, not inside ReviewView, so its BACKLOG.md K4 badge count is visible on the tab
    // item itself — a child view's @StateObject can't be read from the parent TabView around it.
    @StateObject private var needsReviewStore = NeedsReviewStore()
    // BACKLOG.md M2 — owned here (not any one tab) since polling/notifying must keep running
    // regardless of which tab is currently showing.
    @StateObject private var notifier = NewTransactionNotifier()
    @State private var deepLinkCategories: [Category] = []
    @State private var selectedTab = 0
    @Environment(\.scenePhase) private var scenePhase

    /// A single `Identifiable` wrapper around the notifier's plain `Int?`, mirroring
    /// `PayeeSelection`'s own reasoning — `.sheet(item:)` needs one value, not a derived Bool.
    private struct DeepLinkTarget: Identifiable { let id: Int }

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
        .task {
            await refreshNeedsReview()
            notifier.requestAuthorization()
            notifier.startPolling(baseURL: connectionSettings.baseURL)
        }
        // BACKLOG.md K4 — the badge reflects the queue size "as of the last time it was fetched
        // (app foreground/tab switch)", not a live count. These are the only two refresh triggers;
        // there is no polling/push mechanism (ADR-0024).
        .onChange(of: selectedTab) { _, newValue in
            if newValue == 2 { Task { await refreshNeedsReview() } }
        }
        .onChange(of: scenePhase) { _, newPhase in
            if newPhase == .active {
                Task { await refreshNeedsReview() }
                // No-op if already running (BACKLOG.md M2) — iOS suspends the poll loop's Task
                // along with the rest of the process once fully backgrounded; this just covers
                // the case where the loop somehow isn't running yet (e.g. right after launch).
                notifier.startPolling(baseURL: connectionSettings.baseURL)
            }
        }
        .sheet(
            item: Binding(
                get: { notifier.deepLinkTransactionId.map(DeepLinkTarget.init) },
                set: { if $0 == nil { notifier.deepLinkTransactionId = nil } }
            )
        ) { target in
            TransactionDetailView(transactionId: target.id, categories: deepLinkCategories)
        }
        .task(id: notifier.deepLinkTransactionId) {
            guard notifier.deepLinkTransactionId != nil, let baseURL = connectionSettings.baseURL else { return }
            deepLinkCategories = (try? await APIClient(baseURL: baseURL).listCategories().items) ?? []
        }
        // The "AccentColor" asset alone didn't reach system controls (tab bar selection, nav bar
        // buttons, DatePicker chevrons) in this build — confirmed by pixel-sampling a screenshot,
        // they rendered plain system blue despite the asset compiling correctly (`assetutil`
        // confirmed its RGB values). Setting `.tint` explicitly here, once, at the root guarantees
        // every descendant reads it via the environment rather than depending on that implicit link.
        .tint(Color.accentColor)
    }

    private func refreshNeedsReview() async {
        await needsReviewStore.load(baseURL: connectionSettings.baseURL)
    }
}

#Preview {
    RootTabView()
        .environmentObject(ConnectionSettingsStore())
}
