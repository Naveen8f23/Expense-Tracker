import XCTest
@testable import Ledger

@MainActor
final class TransactionListStoreTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!

    func testLoadWithNoBaseURLSetsErrorAndDoesNotTouchTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = TransactionListStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: nil, filters: TransactionFilters())

        XCTAssertTrue(store.transactions.isEmpty)
        XCTAssertNotNil(store.errorMessage)
    }

    func testLoadPopulatesTransactionsTotalAndCategoriesOnce() async {
        var categoryCallCount = 0
        let stub = StubURLSession { request in
            if request.url?.path == "/categories" {
                categoryCallCount += 1
                return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"}]}"#)
            }
            return StubURLSession.json("""
            { "items": [\(Self.transactionJSON(id: 1))], "total": 3, "limit": 50, "offset": 0 }
            """)
        }
        let store = TransactionListStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL, filters: TransactionFilters())
        XCTAssertEqual(store.transactions.count, 1)
        XCTAssertEqual(store.total, 3)
        XCTAssertEqual(store.categories.map(\.name), ["Food"])
        XCTAssertEqual(categoryCallCount, 1)

        // A second load (e.g. pull-to-refresh) must not re-fetch categories.
        await store.load(baseURL: baseURL, filters: TransactionFilters())
        XCTAssertEqual(categoryCallCount, 1)
    }

    func testLoadMoreAppendsAndRespectsHasMore() async {
        let stub = StubURLSession { request in
            let offset = request.url?.query?.contains("offset=1") == true
            if request.url?.path == "/categories" {
                return StubURLSession.json(#"{"items":[]}"#)
            }
            let id = offset ? 2 : 1
            return StubURLSession.json("""
            { "items": [\(Self.transactionJSON(id: id))], "total": 2, "limit": 1, "offset": 0 }
            """)
        }
        let store = TransactionListStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL, filters: TransactionFilters())
        XCTAssertEqual(store.transactions.map(\.id), [1])
        XCTAssertTrue(store.hasMore)

        await store.loadMore(baseURL: baseURL, filters: TransactionFilters())
        XCTAssertEqual(store.transactions.map(\.id), [1, 2])
        XCTAssertFalse(store.hasMore, "total is 2 and we now have 2 loaded")
    }

    func testServerErrorSurfacesInErrorMessage() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/categories" {
                return StubURLSession.json(#"{"items":[]}"#)
            }
            return StubURLSession.json(#"{"detail": "boom"}"#, status: 500)
        }
        let store = TransactionListStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL, filters: TransactionFilters())

        XCTAssertTrue(store.transactions.isEmpty)
        XCTAssertNotNil(store.errorMessage)
    }

    private static func transactionJSON(id: Int) -> String {
        """
        {
          "id": \(id), "amount": "120.00", "currency": "INR", "txn_date": "2026-07-19",
          "txn_time": null, "email_received_at": null,
          "payee": { "id": 1, "name": "Golkondas Cafe", "identifier": null },
          "instrument_last4": null, "category_id": null, "category_name": null,
          "payment_method": "upi", "txn_type": "debit", "reference_number": null,
          "confidence_score": 1.0, "review_status": "auto_accepted", "email_message_id": 7,
          "dismissed": false, "created_at": "2026-07-19T14:32:11+00:00"
        }
        """
    }
}
