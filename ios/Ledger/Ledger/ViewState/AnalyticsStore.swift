import Foundation

/// Which granularity the owner is currently viewing (requested directly, 2026-07-20, as a
/// follow-up to the original month-only view). A week is Monday-start, per the owner's own
/// choice when asked — `canonicalAnchor`/`shift` below mirror the backend's exact
/// `anchor - timedelta(days=anchor.weekday())` algorithm (`app/application/analytics.py`) rather
/// than relying on Foundation's own `weekOfYear` component, so client and server can never
/// disagree about which 7 days make up "this week."
enum AnalyticsPeriod: String, CaseIterable, Identifiable, Equatable {
    case day, week, month, year

    var id: String { rawValue }

    var label: String {
        switch self {
        case .day: return "Day"
        case .week: return "Week"
        case .month: return "Month"
        case .year: return "Year"
        }
    }
}

/// Drives BACKLOG.md L1 (summary) + L2 (category breakdown) for a flexible day/week/month/year
/// period. Both endpoints share one period+anchor cursor (same reasoning as the original
/// month-only cursor, ADR-0021: G3 reuses G2's period rather than a separate picker), so this
/// remains one store, not two.
///
/// `period`/`anchorDate` are mutated only by plain synchronous functions, never by anything that
/// also triggers its own reload — the same race this store's month-only predecessor already found
/// and fixed live: `AnalyticsView` drives loading via `.task(id: store.cursor)`, which SwiftUI
/// already restarts whenever the cursor changes, so a second independent reload call would race
/// it with no defined winner.
@MainActor
final class AnalyticsStore: ObservableObject {
    /// A single `Equatable` value combining `period` + `anchorDate` for `.task(id:)` to key off —
    /// SwiftUI's `task(id:)` needs one value to watch, not two.
    struct Cursor: Equatable {
        let period: AnalyticsPeriod
        let anchorDate: Date
    }

    @Published private(set) var period: AnalyticsPeriod
    @Published private(set) var anchorDate: Date
    @Published private(set) var summary: PeriodAnalytics?
    @Published private(set) var categoryBreakdown: [CategoryBreakdownItem] = []
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?

    var cursor: Cursor { Cursor(period: period, anchorDate: anchorDate) }

    private let makeClient: (URL) -> APIClient
    private static let calendar = Calendar(identifier: .gregorian)

    init(
        makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) },
        initialPeriod: AnalyticsPeriod = .month,
        initialAnchorDate: Date = Date()
    ) {
        self.makeClient = makeClient
        self.period = initialPeriod
        self.anchorDate = Self.canonicalAnchor(for: initialPeriod, from: initialAnchorDate)
    }

    func load(baseURL: URL?) async {
        guard let baseURL else {
            errorMessage = "Set up the backend connection first (gear icon)."
            summary = nil
            categoryBreakdown = []
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let client = makeClient(baseURL)
            let dateParam = WireDate.format(anchorDate)
            async let summaryResult = client.periodAnalytics(period: period.rawValue, date: dateParam)
            async let breakdownResult = client.periodCategoryBreakdown(period: period.rawValue, date: dateParam)
            let (periodSummary, breakdown) = try await (summaryResult, breakdownResult)
            summary = periodSummary
            categoryBreakdown = breakdown.categories
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    /// Re-anchors to the equivalent point in the newly-selected period — e.g. switching from
    /// "month" to "week" while viewing July 2026 lands on the week containing July 1st, rather
    /// than resetting to today (keeps context, matches the spirit of the original month cursor).
    func selectPeriod(_ newPeriod: AnalyticsPeriod) {
        period = newPeriod
        anchorDate = Self.canonicalAnchor(for: newPeriod, from: anchorDate)
    }

    func goToPrevious() { shift(by: -1) }
    func goToNext() { shift(by: 1) }

    private func shift(by value: Int) {
        let calendar = Self.calendar
        switch period {
        case .day:
            anchorDate = calendar.date(byAdding: .day, value: value, to: anchorDate) ?? anchorDate
        case .week:
            anchorDate = calendar.date(byAdding: .day, value: value * 7, to: anchorDate) ?? anchorDate
        case .month:
            anchorDate = calendar.date(byAdding: .month, value: value, to: anchorDate) ?? anchorDate
        case .year:
            anchorDate = calendar.date(byAdding: .year, value: value, to: anchorDate) ?? anchorDate
        }
    }

    /// Normalizes to the canonical start of the period containing `date` — the first of the
    /// month, January 1st, or (for a week) the Monday computed the same way the backend computes
    /// it, so repeated `goToPrevious`/`goToNext` calls (built on this canonical value) never drift
    /// out of step with what the server considers "this period."
    static func canonicalAnchor(for period: AnalyticsPeriod, from date: Date) -> Date {
        let calendar = Self.calendar
        let startOfDay = calendar.startOfDay(for: date)
        switch period {
        case .day:
            return startOfDay
        case .week:
            // Foundation's `.weekday` is always Sunday=1...Saturday=7, regardless of any
            // `firstWeekday` setting — converted here to "days since Monday" (0...6) to match
            // Python's `date.weekday()` (Monday=0) exactly, the same convention
            // `app/application/analytics.py`'s `week_bounds` uses.
            let sundayBased = calendar.component(.weekday, from: startOfDay)
            let daysSinceMonday = (sundayBased + 5) % 7
            return calendar.date(byAdding: .day, value: -daysSinceMonday, to: startOfDay) ?? startOfDay
        case .month:
            let components = calendar.dateComponents([.year, .month], from: startOfDay)
            return calendar.date(from: components) ?? startOfDay
        case .year:
            let components = calendar.dateComponents([.year], from: startOfDay)
            return calendar.date(from: components) ?? startOfDay
        }
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
