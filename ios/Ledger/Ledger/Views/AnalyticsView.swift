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
                    LabeledContent("Debit") { amountText(monthly.totalDebit, color: .red) }
                    LabeledContent("Credit") { amountText(monthly.totalCredit, color: .green) }
                    LabeledContent("Net") { amountText(netMagnitude(monthly.net), color: netColor(monthly)) }
                }
            }

            if !store.categoryBreakdown.isEmpty {
                // ANL-2, debit-only (a refund isn't spend) — already enforced server-side
                // (ADR-0021); this view reuses whatever order/bucketing the backend returns
                // rather than reinterpreting it. The proportional bar is purely a display
                // computation over that same data, not a second source of truth for the totals.
                Section("By Category") {
                    ForEach(store.categoryBreakdown) { item in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Circle()
                                    .fill(CategoryColor.color(for: item.categoryName))
                                    .frame(width: 8, height: 8)
                                Text(item.categoryName)
                                Spacer()
                                Text("\u{20B9}\(item.total)")
                                    .font(.body.monospacedDigit())
                                    .foregroundStyle(.secondary)
                            }
                            GeometryReader { geometry in
                                RoundedRectangle(cornerRadius: 2)
                                    .fill(CategoryColor.color(for: item.categoryName).opacity(0.35))
                                    .frame(width: geometry.size.width * categoryShare(item), height: 4)
                            }
                            .frame(height: 4)
                        }
                        .padding(.vertical, 2)
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

    /// This category's share of the breakdown's total spend, as a `0...1` fraction for the bar's
    /// width — a display-only computation, purely derived from what's already on screen.
    private func categoryShare(_ item: CategoryBreakdownItem) -> Double {
        let categoryTotal = Double(item.total) ?? 0
        let grandTotal = store.categoryBreakdown.reduce(0.0) { $0 + (Double($1.total) ?? 0) }
        guard grandTotal > 0 else { return 0 }
        return min(categoryTotal / grandTotal, 1.0)
    }

    private func amountText(_ value: String, color: Color) -> some View {
        Text("\u{20B9}\(value)")
            .font(.body.monospacedDigit())
            .foregroundStyle(color)
    }

    /// Green when more was received than spent this month, red otherwise. `net` is
    /// `totalDebit - totalCredit` (ADR-0021), so received-minus-spent is its negation.
    private func netColor(_ monthly: MonthlyAnalytics) -> Color {
        guard let debit = Double(monthly.totalDebit), let credit = Double(monthly.totalCredit) else {
            return .primary
        }
        return credit - debit > 0 ? .green : .red
    }

    /// `net` (`totalDebit - totalCredit`, ADR-0021) is negative whenever credit exceeds debit —
    /// shown as a magnitude here since `netColor` already conveys the direction; a green "-900.99"
    /// reads as a contradiction rather than a surplus.
    private func netMagnitude(_ netString: String) -> String {
        guard let net = Double(netString) else { return netString }
        return String(format: "%.2f", abs(net))
    }

    private func reload() async {
        await store.load(baseURL: connectionSettings.baseURL)
    }
}

#Preview {
    AnalyticsView()
        .environmentObject(ConnectionSettingsStore())
}
