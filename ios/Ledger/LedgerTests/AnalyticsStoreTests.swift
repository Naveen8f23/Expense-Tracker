import XCTest
@testable import Ledger

@MainActor
final class AnalyticsStoreTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!
    // A fixed Wednesday, chosen so day/week/month/year all have unambiguous, easily-checked bounds.
    private let wednesday = WireDate.parse("2026-07-15")!

    func testLoadWithNoBaseURLSetsErrorAndDoesNotTouchTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AnalyticsStore(makeClient: { APIClient(baseURL: $0, session: stub) }, initialAnchorDate: wednesday)

        await store.load(baseURL: nil)

        XCTAssertNil(store.summary)
        XCTAssertNotNil(store.errorMessage)
    }

    func testLoadPopulatesSummaryAndCategoryBreakdown() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/analytics/category-breakdown" {
                return StubURLSession.json("""
                { "period": "month", "start_date": "2026-07-01", "end_date": "2026-07-31", "categories": [
                  { "category_id": 1, "category_name": "Food", "total": "500.00", "transaction_count": 3 },
                  { "category_id": null, "category_name": "Uncategorized", "total": "120.00", "transaction_count": 1 }
                ]}
                """)
            }
            return StubURLSession.json("""
            { "period": "month", "start_date": "2026-07-01", "end_date": "2026-07-31",
              "total_debit": "620.00", "total_credit": "50.00", "net": "570.00", "transaction_count": 4 }
            """)
        }
        let store = AnalyticsStore(makeClient: { APIClient(baseURL: $0, session: stub) }, initialAnchorDate: wednesday)

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.summary?.totalDebit, "620.00")
        XCTAssertEqual(store.summary?.net, "570.00")
        XCTAssertEqual(store.categoryBreakdown.map(\.categoryName), ["Food", "Uncategorized"])
    }

    func testLoadSendsThePeriodAndDateAsQueryParams() async {
        // `load()` fires both requests concurrently (`async let`), so each stub invocation must
        // assert independently on its own request rather than writing into a var shared across
        // closures — a shared mutable capture here is a genuine data race (crashed under Swift's
        // runtime exclusivity checking when first written this way).
        let stub = StubURLSession { request in
            let items = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems ?? []
            let byName = Dictionary(uniqueKeysWithValues: items.map { ($0.name, $0.value) })
            XCTAssertEqual(byName["period"], "week")
            XCTAssertEqual(byName["date"], "2026-07-13", "must send the canonical Monday, not the raw anchor")
            if request.url?.path == "/analytics/category-breakdown" {
                return StubURLSession.json("""
                { "period": "week", "start_date": "2026-07-13", "end_date": "2026-07-19", "categories": [] }
                """)
            }
            return StubURLSession.json("""
            { "period": "week", "start_date": "2026-07-13", "end_date": "2026-07-19",
              "total_debit": "0", "total_credit": "0", "net": "0", "transaction_count": 0 }
            """)
        }
        let store = AnalyticsStore(
            makeClient: { APIClient(baseURL: $0, session: stub) },
            initialPeriod: .week,
            initialAnchorDate: wednesday
        )

        await store.load(baseURL: baseURL)

        XCTAssertNotNil(store.summary)
    }

    func testServerErrorSurfacesInErrorMessage() async {
        let stub = StubURLSession { _ in StubURLSession.json(#"{"detail": "boom"}"#, status: 500) }
        let store = AnalyticsStore(makeClient: { APIClient(baseURL: $0, session: stub) }, initialAnchorDate: wednesday)

        await store.load(baseURL: baseURL)

        XCTAssertNotNil(store.errorMessage)
        XCTAssertNil(store.summary)
    }

    // MARK: - canonicalAnchor (period-switch normalization)

    func testCanonicalAnchorForDayIsStartOfThatDay() {
        let anchor = AnalyticsStore.canonicalAnchor(for: .day, from: wednesday)
        XCTAssertEqual(WireDate.format(anchor), "2026-07-15")
    }

    func testCanonicalAnchorForWeekIsTheMondayMatchingTheBackend() {
        // 2026-07-15 is a Wednesday; the backend's week_bounds computes 2026-07-13 (Monday).
        let anchor = AnalyticsStore.canonicalAnchor(for: .week, from: wednesday)
        XCTAssertEqual(WireDate.format(anchor), "2026-07-13")
    }

    func testCanonicalAnchorForWeekOnASundayStillLandsOnTheSamePrecedingMonday() {
        let sunday = WireDate.parse("2026-07-19")!
        let anchor = AnalyticsStore.canonicalAnchor(for: .week, from: sunday)
        XCTAssertEqual(WireDate.format(anchor), "2026-07-13")
    }

    func testCanonicalAnchorForMonthIsTheFirstOfMonth() {
        let anchor = AnalyticsStore.canonicalAnchor(for: .month, from: wednesday)
        XCTAssertEqual(WireDate.format(anchor), "2026-07-01")
    }

    func testCanonicalAnchorForYearIsJanuaryFirst() {
        let anchor = AnalyticsStore.canonicalAnchor(for: .year, from: wednesday)
        XCTAssertEqual(WireDate.format(anchor), "2026-01-01")
    }

    // MARK: - goToPrevious / goToNext (deliberately synchronous, no network — see doc comment)

    func testGoToPreviousDayMovesBackOneDay() {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AnalyticsStore(
            makeClient: { APIClient(baseURL: $0, session: stub) }, initialPeriod: .day, initialAnchorDate: wednesday
        )

        store.goToPrevious()

        XCTAssertEqual(WireDate.format(store.anchorDate), "2026-07-14")
    }

    func testGoToNextWeekMovesForwardSevenDays() {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AnalyticsStore(
            makeClient: { APIClient(baseURL: $0, session: stub) }, initialPeriod: .week, initialAnchorDate: wednesday
        )

        store.goToNext()

        XCTAssertEqual(WireDate.format(store.anchorDate), "2026-07-20", "must move a full 7 days, from the canonical Monday")
    }

    func testGoToNextMonthMovesForwardAndRollsOverIntoTheNextYear() {
        let december = WireDate.parse("2026-12-01")!
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AnalyticsStore(
            makeClient: { APIClient(baseURL: $0, session: stub) }, initialPeriod: .month, initialAnchorDate: december
        )

        store.goToNext()

        XCTAssertEqual(WireDate.format(store.anchorDate), "2027-01-01", "must roll over into the next year")
    }

    func testGoToPreviousYearMovesBackOneYear() {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AnalyticsStore(
            makeClient: { APIClient(baseURL: $0, session: stub) }, initialPeriod: .year, initialAnchorDate: wednesday
        )

        store.goToPrevious()

        XCTAssertEqual(WireDate.format(store.anchorDate), "2025-01-01")
    }

    // MARK: - selectPeriod (re-anchors into the new period, doesn't reset to today)

    func testSelectPeriodReanchorsIntoTheNewPeriodFromTheCurrentAnchor() {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AnalyticsStore(
            makeClient: { APIClient(baseURL: $0, session: stub) }, initialPeriod: .month, initialAnchorDate: wednesday
        )
        XCTAssertEqual(WireDate.format(store.anchorDate), "2026-07-01")

        store.selectPeriod(.week)

        XCTAssertEqual(store.period, .week)
        XCTAssertEqual(WireDate.format(store.anchorDate), "2026-06-29", "the Monday of the week containing July 1st")
    }
}
