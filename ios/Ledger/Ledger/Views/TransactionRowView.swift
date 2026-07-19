import SwiftUI

// BACKLOG.md J1. Amount is the raw wire string (see Networking/Models.swift's note on why it's
// String, not Decimal) — good enough for a list row; real locale-aware formatting is a nicety for
// later. Date+time uses `TransactionDisplayTime`, mirroring the web dashboard's own Epic G
// follow-up (real `txn_time` when the template captured one, else an approximate "~" time from
// the source email/manual-entry timestamp) — this row originally showed only the date, missing
// that parity; fixed once noticed. Tappable — opens J3's detail sheet — hence the chevron.
struct TransactionRowView: View {
    let transaction: Transaction

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(transaction.payee.name)
                        .font(.body)
                    if transaction.emailMessageId == nil {
                        Text("Manual")
                            .font(.caption2)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.secondary.opacity(0.15))
                            .clipShape(Capsule())
                    }
                }
                Text(transaction.categoryName ?? "Uncategorized")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(amountText)
                    .font(.body.monospacedDigit())
                    .foregroundStyle(transaction.txnType == "credit" ? .green : .primary)
                Text(TransactionDisplayTime.string(for: transaction))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .accessibilityHint(
                        TransactionDisplayTime.isApproximate(transaction)
                            ? TransactionDisplayTime.approximationReason(transaction)
                            : ""
                    )
            }
            Image(systemName: "chevron.right")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .foregroundStyle(.primary)
        .contentShape(Rectangle())
    }

    private var amountText: String {
        let sign = transaction.txnType == "credit" ? "+" : "-"
        return "\(sign)\u{20B9}\(transaction.amount)"
    }
}

#Preview {
    List {
        TransactionRowView(transaction: Transaction(
            id: 1, amount: "120.00", currency: "INR", txnDate: "2026-07-19", txnTime: nil,
            emailReceivedAt: nil, payee: Payee(id: 1, name: "Golkondas Cafe", identifier: nil),
            instrumentLast4: "4958", categoryId: nil, categoryName: "Food",
            paymentMethod: "upi", txnType: "debit", referenceNumber: nil, confidenceScore: 1.0,
            reviewStatus: "auto_accepted", emailMessageId: 7, dismissed: false,
            createdAt: "2026-07-19T14:32:11+00:00", sourceEmail: nil
        ))
        TransactionRowView(transaction: Transaction(
            id: 2, amount: "500.00", currency: "INR", txnDate: "2026-07-18", txnTime: nil,
            emailReceivedAt: nil, payee: Payee(id: 2, name: "Cash purchase", identifier: nil),
            instrumentLast4: nil, categoryId: nil, categoryName: nil,
            paymentMethod: "upi", txnType: "debit", referenceNumber: nil, confidenceScore: 1.0,
            reviewStatus: "user_confirmed", emailMessageId: nil, dismissed: false,
            createdAt: "2026-07-18T09:00:00+00:00", sourceEmail: nil
        ))
    }
}
