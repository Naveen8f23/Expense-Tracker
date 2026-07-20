import SwiftUI

/// A single `Identifiable` value driving `.sheet(item:)` for the payee history panel — shared by
/// every place a payee name is tappable (BACKLOG.md L3: transaction rows, the review queue). Using
/// one value, not a separate `Bool` + `String` pair, avoids a real race found live: presenting via
/// `.sheet(isPresented:)` while a second @State held *which* payee let the sheet's content closure
/// read the String's stale default in between the two being set, even though both were set in the
/// same synchronous closure.
struct PayeeSelection: Identifiable {
    let name: String
    var id: String { name }
}

// BACKLOG.md L3 (ANL-3), mirrors web G4 — reached by tapping a payee name anywhere it appears
// (transaction rows, the review queue). Shows the running total and a clickable transaction list;
// tapping one opens the existing `TransactionDetailView` on top.
struct PayeeHistoryView: View {
    let payeeName: String

    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    @StateObject private var store = PayeeHistoryStore()
    @Environment(\.dismiss) private var dismiss
    @State private var selectedTransaction: Transaction?

    var body: some View {
        NavigationStack {
            content
                .navigationTitle(payeeName)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Done") { dismiss() }
                    }
                }
                .sheet(item: $selectedTransaction) { transaction in
                    TransactionDetailView(
                        transactionId: transaction.id,
                        categories: store.categories,
                        onChanged: { Task { await reload() } }
                    )
                }
                .task { await reload() }
                .refreshable { await reload() }
        }
    }

    @ViewBuilder
    private var content: some View {
        if let errorMessage = store.errorMessage, store.summary == nil {
            ContentUnavailableView {
                Label("Couldn't load payee history", systemImage: "wifi.slash")
            } description: {
                Text(errorMessage)
            } actions: {
                Button("Try again") { Task { await reload() } }
            }
        } else if store.isLoading && store.summary == nil {
            ProgressView()
        } else {
            List {
                if let summary = store.summary {
                    Section {
                        LabeledContent("Debit") { amountText(summary.totalDebit, color: .red) }
                        LabeledContent("Credit") { amountText(summary.totalCredit, color: .green) }
                        LabeledContent("Net") { amountText(netMagnitude(summary.net), color: netColor(summary)) }
                        LabeledContent("Transactions", value: "\(summary.transactionCount)")
                    }
                }

                Section("History") {
                    ForEach(store.transactions) { transaction in
                        Button {
                            selectedTransaction = transaction
                        } label: {
                            TransactionRowView(transaction: transaction)
                        }
                        .buttonStyle(.plain)
                    }
                    if store.hasMore {
                        HStack {
                            Spacer()
                            if store.isLoadingMore {
                                ProgressView()
                            } else {
                                Button("Load more") { Task { await store.loadMore(baseURL: connectionSettings.baseURL, payee: payeeName) } }
                            }
                            Spacer()
                        }
                    }
                }
            }
            .listStyle(.insetGrouped)
        }
    }

    private func amountText(_ value: String, color: Color) -> some View {
        Text("\u{20B9}\(value)")
            .font(.body.monospacedDigit())
            .foregroundStyle(color)
    }

    /// Green when more was received than spent, red otherwise — mirrors AnalyticsView's own
    /// `netColor`. `net` is `totalDebit - totalCredit` (ADR-0021), so credit-minus-debit is its
    /// negation.
    private func netColor(_ summary: PayeeHistoryResponse) -> Color {
        guard let debit = Double(summary.totalDebit), let credit = Double(summary.totalCredit) else {
            return .primary
        }
        return credit - debit > 0 ? .green : .red
    }

    /// Shown as a magnitude since `netColor` already conveys the direction — mirrors
    /// AnalyticsView's own `netMagnitude`.
    private func netMagnitude(_ netString: String) -> String {
        guard let net = Double(netString) else { return netString }
        return String(format: "%.2f", abs(net))
    }

    private func reload() async {
        await store.load(baseURL: connectionSettings.baseURL, payee: payeeName)
    }
}

#Preview {
    PayeeHistoryView(payeeName: "Golkondas Cafe")
        .environmentObject(ConnectionSettingsStore())
}
