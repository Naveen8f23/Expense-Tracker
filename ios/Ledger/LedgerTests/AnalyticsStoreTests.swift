import XCTest
@testable import Ledger

@MainActor
final class AnalyticsStoreTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!

    func testLoadWithNoBaseURLSetsErrorAndDoesNotTouchTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AnalyticsStore(makeClient: { APIClient(baseURL: $0, session: stub) }, initialMonth: "2026-07")

        await store.load(baseURL: nil)

        XCTAssertNil(store.monthly)
        XCTAssertNotNil(store.errorMessage)
    }

    func testLoadPopulatesMonthlySummaryAndCategoryBreakdown() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/analytics/by-category" {
                return StubURLSession.json("""
                { "month": "2026-07", "categories": [
                  { "category_id": 1, "category_name": "Food", "total": "500.00", "transaction_count": 3 },
                  { "category_id": null, "category_name": "Uncategorized", "total": "120.00", "transaction_count": 1 }
                ]}
                """)
            }
            return StubURLSession.json("""
            { "month": "2026-07", "total_debit": "620.00", "total_credit": "50.00", "net": "570.00", "transaction_count": 4 }
            """)
        }
        let store = AnalyticsStore(makeClient: { APIClient(baseURL: $0, session: stub) }, initialMonth: "2026-07")

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.monthly?.totalDebit, "620.00")
        XCTAssertEqual(store.monthly?.net, "570.00")
        XCTAssertEqual(store.categoryBreakdown.map(\.categoryName), ["Food", "Uncategorized"])
    }

    func testServerErrorSurfacesInErrorMessage() async {
        let stub = StubURLSession { _ in StubURLSession.json(#"{"detail": "boom"}"#, status: 500) }
        let store = AnalyticsStore(makeClient: { APIClient(baseURL: $0, session: stub) }, initialMonth: "2026-07")

        await store.load(baseURL: baseURL)

        XCTAssertNotNil(store.errorMessage)
        XCTAssertNil(store.monthly)
    }

    func testGoToPreviousMonthMovesBackWithoutTouchingTheNetwork() {
        // Deliberately synchronous and side-effect-free (see AnalyticsStore's doc comment) —
        // AnalyticsView drives the actual reload via `.task(id: store.month)`, not this call.
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AnalyticsStore(makeClient: { APIClient(baseURL: $0, session: stub) }, initialMonth: "2026-07")

        store.goToPreviousMonth()

        XCTAssertEqual(store.month, "2026-06")
    }

    func testGoToNextMonthMovesForwardAndRollsOverIntoTheNextYear() {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AnalyticsStore(makeClient: { APIClient(baseURL: $0, session: stub) }, initialMonth: "2026-12")

        store.goToNextMonth()

        XCTAssertEqual(store.month, "2027-01", "must roll over into the next year")
    }
}
