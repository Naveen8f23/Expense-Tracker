import SwiftUI

struct RootTabView: View {
    var body: some View {
        TabView {
            LedgerListView()
                .tabItem {
                    Label("Ledger", systemImage: "list.bullet.rectangle")
                }

            AnalyticsView()
                .tabItem {
                    Label("Analytics", systemImage: "chart.pie")
                }

            ReviewView()
                .tabItem {
                    Label("Review", systemImage: "checklist")
                }
        }
    }
}

#Preview {
    RootTabView()
}
