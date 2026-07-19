import SwiftUI

// BACKLOG.md J1. Amount is the raw wire string (see Networking/Models.swift's note on why it's
// String, not Decimal) — good enough for a list row; real locale-aware formatting is a nicety for
// later. Date+time uses `TransactionDisplayTime`, mirroring the web dashboard's own Epic G
// follow-up (real `txn_time` when the template captured one, else an approximate "~" time from
// the source email/manual-entry timestamp) — this row originally showed only the date, missing
// that parity; fixed once noticed. Tappable — opens J3's detail sheet — hence the chevron.
struct TransactionRowView: View {
    let transaction: Transaction
    /// BACKLOG.md L3 — when set, the payee name becomes its own tappable target (opening
    /// `PayeeHistoryView`), separate from tapping the rest of the row (which opens J3's detail
    /// sheet). `nil` by default so existing call sites (previews, `PayeeHistoryView`'s own
    /// transaction list) keep plain, non-interactive payee text.
    var onPayeeTapped: (() -> Void)? = nil

    /// A category's color-coding (`CategoryColor`) is deterministic from its name, so the same
    /// category always reads the same way — a thin leading stripe here doubles as a quick visual
    /// scan aid down a long list, the same idea as the small dot next to the category caption.
    private var categoryColor: Color { CategoryColor.color(for: transaction.categoryName) }

    var body: some View {
        HStack(spacing: 10) {
            RoundedRectangle(cornerRadius: 2)
                .fill(categoryColor.opacity(0.7))
                .frame(width: 4)
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    if let onPayeeTapped {
                        Button(action: onPayeeTapped) {
                            Text(transaction.payee.name)
                                .font(.body)
                                .foregroundStyle(.primary)
                                .underline()
                        }
                        .buttonStyle(.plain)
                    } else {
                        Text(transaction.payee.name)
                            .font(.body)
                    }
                    if transaction.emailMessageId == nil {
                        Text("Manual")
                            .font(.caption2)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.accentColor.opacity(0.15))
                            .foregroundStyle(Color.accentColor)
                            .clipShape(Capsule())
                    }
                }
                HStack(spacing: 4) {
                    Circle()
                        .fill(categoryColor)
                        .frame(width: 6, height: 6)
                    Text(transaction.categoryName ?? "Uncategorized")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(amountText)
                    .font(.body.monospacedDigit())
                    .foregroundStyle(transaction.txnType == "credit" ? .green : .red)
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
