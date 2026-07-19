import SwiftUI

/// Categories are fully user-defined (no fixed list, EXT-2) — there's no backend field to key a
/// color off of, so this assigns one deterministically from the category's name alone: the same
/// name always gets the same color, both across app launches and independently from the web
/// dashboard (which has no color-coding of its own to match). Purely a display concern — nothing
/// downstream (extraction, categorization, analytics totals) reads or depends on this.
enum CategoryColor {
    /// SwiftUI's built-in adaptive colors — each already has a distinct light/dark rendering, so
    /// no custom hex/appearance handling is needed here. `.red`/`.green` are deliberately excluded:
    /// those are reserved for debit/credit amount coloring (`TransactionRowView`) and reusing them
    /// here would blur that separate, more important signal.
    private static let palette: [Color] = [
        .indigo, .teal, .orange, .pink, .purple, .brown, .cyan, .yellow, .mint, .blue,
    ]

    static func color(for categoryName: String?) -> Color {
        guard let categoryName, !categoryName.isEmpty else { return .secondary }
        return palette[stableHash(categoryName) % palette.count]
    }

    /// `String.hashValue` is randomized per process launch (Swift's hash seeding) — not usable
    /// here, since the whole point is the same name mapping to the same color every time. A plain
    /// djb2 over UTF-8 bytes is stable and more than good enough for this (display-only, not
    /// security-sensitive) purpose.
    private static func stableHash(_ string: String) -> Int {
        var hash = 5381
        for byte in string.utf8 {
            hash = ((hash << 5) &+ hash) &+ Int(byte)
        }
        return abs(hash)
    }
}
