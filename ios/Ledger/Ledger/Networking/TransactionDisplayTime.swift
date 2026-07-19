import Foundation

/// Mirrors `frontend/src/utils/transactionTime.tsx`'s `TransactionDateTime` — not every source
/// template captures a real transaction time (the UPI templates are date-only,
/// REQUIREMENTS.md Appendix A), so those rows fall back to the source email's received time,
/// then (for a manually-added transaction with neither) to when the row was created — each tier
/// marked with a "~" prefix since it's an approximation, not the extracted transaction time.
enum TransactionDisplayTime {
    private static let isoFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .none
        formatter.timeStyle = .short
        return formatter
    }()

    /// e.g. "2026-07-19 2:32 PM" (real time) or "2026-07-19 ~2:32 PM" (approximate).
    static func string(for transaction: Transaction) -> String {
        if let txnTime = transaction.txnTime, let formatted = formattedTxnTime(txnTime) {
            return "\(transaction.txnDate) \(formatted)"
        }
        let source = transaction.emailReceivedAt ?? transaction.createdAt
        guard let date = parseISODateTime(source) else { return transaction.txnDate }
        return "\(transaction.txnDate) ~\(timeFormatter.string(from: date))"
    }

    static func isApproximate(_ transaction: Transaction) -> Bool {
        transaction.txnTime == nil
    }

    /// Matches the web's tooltip text — surfaced on iOS as an accessibility hint rather than a
    /// hover tooltip, since touch has no hover state.
    static func approximationReason(_ transaction: Transaction) -> String {
        transaction.emailReceivedAt != nil
            ? "Approximate — based on when the source email arrived, not extracted from the transaction itself"
            : "Approximate — based on when this manually-added transaction was recorded"
    }

    private static func formattedTxnTime(_ txnTime: String) -> String? {
        let parts = txnTime.split(separator: ":")
        guard parts.count >= 2, let hour = Int(parts[0]), let minute = Int(parts[1]) else { return nil }
        var components = DateComponents()
        components.hour = hour
        components.minute = minute
        guard let date = Calendar.current.date(from: components) else { return nil }
        return timeFormatter.string(from: date)
    }

    /// Two real-world quirks to handle, confirmed against the actual running backend (not
    /// assumed): (1) `created_at` carries up to microsecond precision, which
    /// `ISO8601DateFormatter` doesn't reliably parse even with `.withFractionalSeconds` (that
    /// option assumes millisecond precision) — the fractional part is stripped entirely, since
    /// only the time-of-day down to the minute is ever displayed. (2) `email_received_at` and
    /// `created_at` are serialized with **no timezone suffix at all** (e.g.
    /// `"2026-07-19T10:40:39"`, not `"...+00:00"`) — `ISO8601DateFormatter` silently fails to
    /// parse a string with no offset, so this appends `"Z"` first, exactly like the web
    /// dashboard's own handling (`frontend/src/utils/transactionTime.tsx`) does for the same
    /// naive-UTC values.
    private static func parseISODateTime(_ string: String) -> Date? {
        guard let tIndex = string.firstIndex(of: "T") else { return nil }
        let afterT = string[string.index(after: tIndex)...]
        let hasOffset = afterT.contains("+") || afterT.contains("-") || afterT.hasSuffix("Z")

        var normalized = string
        if let dotIndex = string[tIndex...].firstIndex(of: ".") {
            let afterDot = string[string.index(after: dotIndex)...]
            let offsetStart = afterDot.firstIndex(where: { $0 == "+" || $0 == "-" || $0 == "Z" })
            let suffix = offsetStart.map { String(string[$0...]) } ?? ""
            normalized = String(string[..<dotIndex]) + suffix
        }
        if !hasOffset {
            normalized += "Z"
        }
        return isoFormatter.date(from: normalized)
    }
}
