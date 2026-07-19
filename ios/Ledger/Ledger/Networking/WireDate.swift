import Foundation

/// Shared `yyyy-MM-dd` conversion between a SwiftUI `Date` and the backend's date-only wire
/// format (`txn_date`, `date_from`/`date_to` — see Networking/Models.swift's note on why these
/// are `String`, not `Date`, at the model layer). Used by both the filter sheet and the
/// transaction detail form — pulled out once a second call site needed it, rather than kept as
/// two private copies.
enum WireDate {
    private static let formatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = .current
        return formatter
    }()

    static func format(_ date: Date) -> String {
        formatter.string(from: date)
    }

    static func parse(_ string: String?) -> Date? {
        guard let string else { return nil }
        return formatter.date(from: string)
    }
}
