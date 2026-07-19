import Foundation

/// Drives BACKLOG.md L1 (monthly summary) + L2 (category breakdown) — both endpoints share one
/// month cursor (ADR-0021: G3 reuses G2's month rather than a separate period picker), so this is
/// one store, not two. Same per-call-`baseURL`, injectable-client-factory shape as the other
/// stores for testability.
///
/// `month` is deliberately mutated by a *plain synchronous* function, not an `async` one that also
/// triggers its own reload — `AnalyticsView` drives loading via `.task(id: store.month)`, which
/// SwiftUI already restarts whenever `month` changes. Combining that with a second, independent
/// `load()` call inside an async `goToPreviousMonth`/`goToNextMonth` created two racing loads per
/// month change with no defined winner — verified live, where a real device build after tapping
/// "Previous month" left the label and figures showing the old month, because the `.task`-driven
/// reload (using the already-updated `month`) and the explicit in-function reload interleaved
/// unpredictably. One trigger, driven by SwiftUI itself, removes the race entirely.
@MainActor
final class AnalyticsStore: ObservableObject {
    @Published private(set) var month: String
    @Published private(set) var monthly: MonthlyAnalytics?
    @Published private(set) var categoryBreakdown: [CategoryBreakdownItem] = []
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?

    private let makeClient: (URL) -> APIClient

    init(makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) }, initialMonth: String? = nil) {
        self.makeClient = makeClient
        self.month = initialMonth ?? Self.monthString(for: Date())
    }

    func load(baseURL: URL?) async {
        guard let baseURL else {
            errorMessage = "Set up the backend connection first (gear icon)."
            monthly = nil
            categoryBreakdown = []
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let client = makeClient(baseURL)
            async let monthlyResult = client.monthlyAnalytics(month: month)
            async let breakdownResult = client.categoryBreakdown(month: month)
            let (monthlySummary, breakdown) = try await (monthlyResult, breakdownResult)
            monthly = monthlySummary
            categoryBreakdown = breakdown.categories
        } catch {
            errorMessage = Self.describe(error)
        }
    }

    func goToPreviousMonth() {
        month = Self.shiftMonth(month, by: -1)
    }

    func goToNextMonth() {
        month = Self.shiftMonth(month, by: 1)
    }

    /// Fixed-format, non-user-facing date parsing must pin `locale` to `en_US_POSIX` — without it,
    /// `DateFormatter` can behave inconsistently under some device locale/calendar settings (a
    /// well-known Foundation gotcha) for a literal pattern like "yyyy-MM".
    private static func makeFixedFormatFormatter() -> DateFormatter {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.dateFormat = "yyyy-MM"
        return formatter
    }

    private static func monthString(for date: Date) -> String {
        makeFixedFormatFormatter().string(from: date)
    }

    private static func shiftMonth(_ month: String, by delta: Int) -> String {
        let formatter = makeFixedFormatFormatter()
        guard let date = formatter.date(from: month) else { return month }
        let shifted = Calendar(identifier: .gregorian).date(byAdding: .month, value: delta, to: date) ?? date
        return formatter.string(from: shifted)
    }

    private static func describe(_ error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }
}
