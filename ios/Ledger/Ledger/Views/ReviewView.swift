import SwiftUI

// BACKLOG.md Epic K — the needs-review queue (mirrors web F4). Lists both halves GET /needs-review
// already returns (E5): unmatched emails and low-confidence transactions, each with a reason chip.
struct ReviewView: View {
    @EnvironmentObject private var connectionSettings: ConnectionSettingsStore
    @ObservedObject var store: NeedsReviewStore
    @State private var selectedTransaction: Transaction?
    // BACKLOG.md L3 — tapping a low-confidence transaction's payee name opens the payee history
    // panel instead of K3's detail sheet. A single Identifiable value, not a Bool+String pair —
    // see PayeeSelection's doc comment for the real race that shape caused.
    @State private var payeeSelection: PayeeSelection?

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Review")
                .alert(
                    "Couldn't ignore email",
                    isPresented: Binding(
                        get: { store.actionErrorMessage != nil },
                        set: { isPresented in if !isPresented { store.clearActionError() } }
                    )
                ) {
                    Button("OK", role: .cancel) {}
                } message: {
                    Text(store.actionErrorMessage ?? "")
                }
                .sheet(item: $selectedTransaction) { transaction in
                    TransactionDetailView(
                        transactionId: transaction.id,
                        categories: store.categories,
                        // K3 — tapping a low-confidence item reuses J3's own detail sheet rather
                        // than a separate review-specific form. Reload the whole queue afterward:
                        // a correction sets review_status to USER_CONFIRMED (E3) and a dismiss
                        // excludes it entirely, either way it should drop out of a fresh fetch.
                        onChanged: { Task { await reload() } }
                    )
                }
                .sheet(item: $payeeSelection) { selection in
                    PayeeHistoryView(payeeName: selection.name)
                }
                .task { await reload() }
                .refreshable { await reload() }
        }
    }

    @ViewBuilder
    private var content: some View {
        if let errorMessage = store.errorMessage, store.unmatchedEmails.isEmpty, store.lowConfidenceTransactions.isEmpty {
            ContentUnavailableView {
                Label("Couldn't load the review queue", systemImage: "wifi.slash")
            } description: {
                Text(errorMessage)
            } actions: {
                Button("Try again") { Task { await reload() } }
            }
        } else if store.unmatchedEmails.isEmpty && store.lowConfidenceTransactions.isEmpty && !store.isLoading {
            ContentUnavailableView("Nothing needs review", systemImage: "checkmark.circle")
        } else {
            List {
                if !store.unmatchedEmails.isEmpty {
                    Section("Unmatched Emails") {
                        ForEach(store.unmatchedEmails) { email in
                            NavigationLink {
                                SourceEmailView(email: email, onIgnore: {
                                    await store.ignoreEmail(baseURL: connectionSettings.baseURL, id: email.id)
                                })
                            } label: {
                                unmatchedEmailRow(email)
                            }
                            .swipeActions(edge: .trailing) {
                                // Same action as SourceEmailView's toolbar button below — a visible
                                // button was added there since a swipe gesture alone turned out not
                                // to be discoverable enough (raised directly by the owner while
                                // testing). Kept here too since some users do expect/prefer it.
                                Button(role: .destructive) {
                                    Task { await store.ignoreEmail(baseURL: connectionSettings.baseURL, id: email.id) }
                                } label: {
                                    Label("Ignore", systemImage: "xmark.circle")
                                }
                            }
                        }
                    }
                }

                if !store.lowConfidenceTransactions.isEmpty {
                    Section("Needs Review") {
                        ForEach(store.lowConfidenceTransactions) { transaction in
                            // Same reasoning as LedgerListView's rows (BACKLOG.md L3): the payee
                            // name is its own tappable target, so the row can't be one big Button.
                            lowConfidenceRow(transaction) {
                                payeeSelection = PayeeSelection(name: transaction.payee.name)
                            }
                            .contentShape(Rectangle())
                            .onTapGesture { selectedTransaction = transaction }
                        }
                    }
                }
            }
            .listStyle(.insetGrouped)
        }
    }

    @ViewBuilder
    private func unmatchedEmailRow(_ email: EmailMessage) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(email.receivedAt)
                    .font(.body)
                Spacer()
                reasonChip(email.classifiedPatternId == nil ? "Unrecognized" : "Extraction failed")
            }
            Text(email.status)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    @ViewBuilder
    private func lowConfidenceRow(_ transaction: Transaction, onPayeeTapped: @escaping () -> Void) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Button(action: onPayeeTapped) {
                    Text(transaction.payee.name)
                        .font(.body)
                        .foregroundStyle(.primary)
                        .underline()
                }
                .buttonStyle(.plain)
                Text(TransactionDisplayTime.string(for: transaction))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            reasonChip("Low confidence")
            Image(systemName: "chevron.right")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
    }

    @ViewBuilder
    private func reasonChip(_ label: String) -> some View {
        Text(label)
            .font(.caption2)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(Color.orange.opacity(0.15))
            .foregroundStyle(.orange)
            .clipShape(Capsule())
    }

    private func reload() async {
        await store.load(baseURL: connectionSettings.baseURL)
    }
}

#Preview {
    ReviewView(store: NeedsReviewStore())
        .environmentObject(ConnectionSettingsStore())
}
