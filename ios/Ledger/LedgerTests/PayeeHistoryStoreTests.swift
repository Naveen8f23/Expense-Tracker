import XCTest
@testable import Ledger

@MainActor
final class PayeeHistoryStoreTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!

    func testLoadWithNoBaseURLSetsErrorAndDoesNotTouchTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = PayeeHistoryStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: nil, payee: "Golkondas Cafe")

        XCTAssertNil(store.summary)
        XCTAssertNotNil(store.errorMessage)
    }

    func testLoadPopulatesSummaryTransactionsAndCategoriesOnce() async {
        var categoryCallCount = 0
        let stub = StubURLSession { request in
            if request.url?.path == "/categories" {
                categoryCallCount += 1
                return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"}]}"#)
            }
            return StubURLSession.json("""
            {
              "payee_name": "Golkondas Cafe", "total_debit": "500.00", "total_credit": "0.00",
              "net": "500.00", "transaction_count": 2, "limit": 50, "offset": 0,
              "items": [\(Self.transactionJSON(id: 1))]
            }
            """)
        }
        let store = PayeeHistoryStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL, payee: "Golkondas Cafe")
        XCTAssertEqual(store.summary?.transactionCount, 2)
        XCTAssertEqual(store.transactions.map(\.id), [1])
        XCTAssertEqual(store.categories.map(\.name), ["Food"])
        XCTAssertTrue(store.hasMore, "1 loaded of 2 total")

        await store.load(baseURL: baseURL, payee: "Golkondas Cafe")
        XCTAssertEqual(categoryCallCount, 1, "a second load must not re-fetch categories")
    }

    func testLoadMoreAppendsAndRespectsHasMore() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/categories" {
                return StubURLSession.json(#"{"items":[]}"#)
            }
            let offset = request.url?.query?.contains("offset=1") == true
            let id = offset ? 2 : 1
            return StubURLSession.json("""
            {
              "payee_name": "Golkondas Cafe", "total_debit": "500.00", "total_credit": "0.00",
              "net": "500.00", "transaction_count": 2, "limit": 1, "offset": \(offset ? 1 : 0),
              "items": [\(Self.transactionJSON(id: id))]
            }
            """)
        }
        let store = PayeeHistoryStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL, payee: "Golkondas Cafe")
        XCTAssertEqual(store.transactions.map(\.id), [1])

        await store.loadMore(baseURL: baseURL, payee: "Golkondas Cafe")
        XCTAssertEqual(store.transactions.map(\.id), [1, 2])
        XCTAssertFalse(store.hasMore)
    }

    func testServerErrorSurfacesInErrorMessage() async {
        let stub = StubURLSession { _ in StubURLSession.json(#"{"detail": "boom"}"#, status: 500) }
        let store = PayeeHistoryStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL, payee: "Nobody")

        XCTAssertNotNil(store.errorMessage)
        XCTAssertNil(store.summary)
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
