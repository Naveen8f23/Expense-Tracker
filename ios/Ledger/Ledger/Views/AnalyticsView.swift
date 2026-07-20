import SwiftUI

// BACKLOG.md L1 (summary) + L2 (category breakdown), now for a flexible day/week/month/year
// period rather than month-only — both endpoints share one period+anchor cursor (ADR-0021's
// "shared cursor" reasoning still applies) rather than a separate picker per card.
struct AnalyticsView: View {
    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    @StateObject private var store = AnalyticsStore()

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Analytics")
                // Driven by `store.cursor` (see AnalyticsStore's doc comment) — this is the one
                // and only trigger for loading; `goToPrevious`/`goToNext`/`selectPeriod` just
                // change `period`/`anchorDate` and let SwiftUI restart this task, rather than each
                // also calling load() themselves and racing with this one.
                .task(id: store.cursor) { await reload() }
                .refreshable { await reload() }
        }
    }

    @ViewBuilder
    private var content: some View {
        if let errorMessage = store.errorMessage, store.summary == nil {
            ContentUnavailableView {
                Label("Couldn't load analytics", systemImage: "wifi.slash")
            } description: {
                Text(errorMessage)
            } actions: {
                Button("Try again") { Task { await reload() } }
            }
        } else {
            // The period picker and cursor switcher live outside the List (mirrors
            // LedgerListView's own payeeField/chipsRow, which sit beside its List rather than
            // inside a Section) — a `Section`'s direct, non-`ForEach` content didn't reliably
            // re-render on cursor changes when nested inside the List below, verified live with
            // the original month-only switcher. Moving it out uses the same List/VStack split
            // already proven to work elsewhere in this app.
            VStack(spacing: 0) {
                periodPicker
                    .padding(.horizontal, 16)
                    .padding(.top, 12)
                cursorSwitcher
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                list
            }
        }
    }

    @ViewBuilder
    private var list: some View {
        List {
            if store.isLoading && store.summary == nil {
                Section {
                    ProgressView()
                }
            } else if let summary = store.summary {
                // ADR-0021's sign convention: `net` is `total_debit - total_credit` — positive
                // means money spent, not received.
                Section("Summary") {
                    LabeledContent("Debit") { amountText(summary.totalDebit, color: .red) }
                    LabeledContent("Credit") { amountText(summary.totalCredit, color: .green) }
                    LabeledContent("Net") { amountText(netMagnitude(summary.net), color: netColor(summary)) }
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
            } else if store.summary != nil {
                Section {
                    Text("No spending in this \(store.period.label.lowercased())").foregroundStyle(.secondary)
                }
            }
        }
        .listStyle(.insetGrouped)
    }

    private var periodPicker: some View {
        Picker(
            "Period",
            selection: Binding(get: { store.period }, set: { store.selectPeriod($0) })
        ) {
            ForEach(AnalyticsPeriod.allCases) { period in
                Text(period.label).tag(period)
            }
        }
        .pickerStyle(.segmented)
    }

    private var cursorSwitcher: some View {
        HStack {
            Button {
                store.goToPrevious()
            } label: {
                Image(systemName: "chevron.left")
            }
            .accessibilityLabel("Previous \(store.period.label.lowercased())")
            Spacer()
            Text(cursorLabel)
                .font(.headline)
            Spacer()
            Button {
                store.goToNext()
            } label: {
                Image(systemName: "chevron.right")
            }
            .accessibilityLabel("Next \(store.period.label.lowercased())")
        }
    }

    /// Formatted from the summary's own `startDate`/`endDate` (rather than recomputed client-side
    /// from `store.anchorDate`) so the label always matches exactly what the server actually
    /// aggregated, never a client-side guess about period boundaries.
    private var cursorLabel: String {
        guard let summary = store.summary, let start = WireDate.parse(summary.startDate) else {
            return ""
        }
        switch store.period {
        case .day:
            return Self.dayFormatter.string(from: start)
        case .week:
            guard let end = WireDate.parse(summary.endDate) else { return Self.dayFormatter.string(from: start) }
            return "\(Self.dayFormatter.string(from: start)) – \(Self.dayFormatter.string(from: end))"
        case .month:
            return Self.monthFormatter.string(from: start)
        case .year:
            return Self.yearFormatter.string(from: start)
        }
    }

    private static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d, yyyy"
        return formatter
    }()

    private static let monthFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMMM yyyy"
        return formatter
    }()

    private static let yearFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy"
        return formatter
    }()

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

    /// Green when more was received than spent this period, red otherwise. `net` is
    /// `totalDebit - totalCredit` (ADR-0021), so received-minus-spent is its negation.
    private func netColor(_ summary: PeriodAnalytics) -> Color {
        guard let debit = Double(summary.totalDebit), let credit = Double(summary.totalCredit) else {
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
