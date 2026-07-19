import SwiftUI

// BACKLOG.md L1 (monthly summary) + L2 (category breakdown). Both endpoints share one month
// cursor (ADR-0021) rather than a separate period picker.
struct AnalyticsView: View {
    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    @StateObject private var store = AnalyticsStore()

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Analytics")
                // Driven by `store.month` (see AnalyticsStore's doc comment) — this is the one
                // and only trigger for loading; `goToPreviousMonth`/`goToNextMonth` just change
                // `month` and let SwiftUI restart this task, rather than each also calling load()
                // themselves and racing with this one.
                .task(id: store.month) { await reload() }
                .refreshable { await reload() }
        }
    }

    @ViewBuilder
    private var content: some View {
        if let errorMessage = store.errorMessage, store.monthly == nil {
            ContentUnavailableView {
                Label("Couldn't load analytics", systemImage: "wifi.slash")
            } description: {
                Text(errorMessage)
            } actions: {
                Button("Try again") { Task { await reload() } }
            }
        } else {
            // The month switcher lives outside the List (mirrors LedgerListView's own
            // payeeField/chipsRow, which sit beside its List rather than inside a Section) — a
            // `Section`'s direct, non-`ForEach` content didn't reliably re-render on `store.month`
            // changes when nested inside the List below, verified live: the label and every
            // figure on screen stayed frozen after tapping Previous/Next despite the store's
            // `month` genuinely changing (confirmed via direct instrumentation). Moving it out
            // uses the same List/VStack split already proven to work elsewhere in this app.
            VStack(spacing: 0) {
                monthSwitcher
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                list
            }
        }
    }

    @ViewBuilder
    private var list: some View {
        List {
            if store.isLoading && store.monthly == nil {
                Section {
                    ProgressView()
                }
            } else if let monthly = store.monthly {
                // ADR-0021's sign convention: `net` is `total_debit - total_credit` — positive
                // means money spent, not received.
                Section("Summary") {
                    LabeledContent("Spent") { amountText(monthly.totalDebit, color: .primary) }
                    LabeledContent("Received") { amountText(monthly.totalCredit, color: .green) }
                    LabeledContent("Net") { amountText(monthly.net, color: .primary) }
                }
            }

            if !store.categoryBreakdown.isEmpty {
                // ANL-2, debit-only (a refund isn't spend) — already enforced server-side
                // (ADR-0021); this view reuses whatever order/bucketing the backend returns
                // rather than reinterpreting it.
                Section("By Category") {
                    ForEach(store.categoryBreakdown) { item in
                        HStack {
                            Text(item.categoryName)
                            Spacer()
                            Text("\u{20B9}\(item.total)")
                                .font(.body.monospacedDigit())
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            } else if store.monthly != nil {
                Section {
                    Text("No spending this month").foregroundStyle(.secondary)
                }
            }
        }
        .listStyle(.insetGrouped)
    }

    private var monthSwitcher: some View {
        HStack {
            Button {
                store.goToPreviousMonth()
            } label: {
                Image(systemName: "chevron.left")
            }
            .accessibilityLabel("Previous month")
            Spacer()
            Text(store.month)
                .font(.headline)
            Spacer()
            Button {
                store.goToNextMonth()
            } label: {
                Image(systemName: "chevron.right")
            }
            .accessibilityLabel("Next month")
        }
    }

    private func amountText(_ value: String, color: Color) -> some View {
        Text("\u{20B9}\(value)")
            .font(.body.monospacedDigit())
            .foregroundStyle(color)
    }

    private func reload() async {
        await store.load(baseURL: connectionSettings.baseURL)
    }
}

#Preview {
    AnalyticsView()
        .environmentObject(ConnectionSettingsStore())
}
