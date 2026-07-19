import XCTest
@testable import Ledger

@MainActor
final class NeedsReviewStoreTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!

    func testLoadWithNoBaseURLSetsErrorAndDoesNotTouchTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = NeedsReviewStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: nil)

        XCTAssertTrue(store.unmatchedEmails.isEmpty)
        XCTAssertTrue(store.lowConfidenceTransactions.isEmpty)
        XCTAssertNotNil(store.errorMessage)
    }

    func testLoadPopulatesBothHalvesAndCategoriesOnce() async {
        var categoryCallCount = 0
        let stub = StubURLSession { request in
            if request.url?.path == "/categories" {
                categoryCallCount += 1
                return StubURLSession.json(#"{"items":[{"id":1,"name":"Food"}]}"#)
            }
            return StubURLSession.json("""
            {
              "unmatched_emails": [\(Self.emailJSON(id: 1, classifiedPatternId: nil))],
              "low_confidence_transactions": [\(Self.transactionJSON(id: 7))]
            }
            """)
        }
        let store = NeedsReviewStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)
        XCTAssertEqual(store.unmatchedEmails.map(\.id), [1])
        XCTAssertEqual(store.lowConfidenceTransactions.map(\.id), [7])
        XCTAssertEqual(store.categories.map(\.name), ["Food"])
        XCTAssertEqual(categoryCallCount, 1)

        await store.load(baseURL: baseURL)
        XCTAssertEqual(categoryCallCount, 1, "a second load must not re-fetch categories")
    }

    func testServerErrorSurfacesInErrorMessage() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/categories" {
                return StubURLSession.json(#"{"items":[]}"#)
            }
            return StubURLSession.json(#"{"detail": "boom"}"#, status: 500)
        }
        let store = NeedsReviewStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)

        XCTAssertNotNil(store.errorMessage)
        XCTAssertTrue(store.unmatchedEmails.isEmpty)
    }

    func testIgnoreEmailRemovesItLocallyOnSuccess() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/categories" {
                return StubURLSession.json(#"{"items":[]}"#)
            }
            if request.url?.path.hasSuffix("/ignore") == true {
                return StubURLSession.json(Self.emailJSON(id: 1, classifiedPatternId: nil, status: "ignored"))
            }
            return StubURLSession.json("""
            {
              "unmatched_emails": [\(Self.emailJSON(id: 1, classifiedPatternId: nil)), \(Self.emailJSON(id: 2, classifiedPatternId: nil))],
              "low_confidence_transactions": []
            }
            """)
        }
        let store = NeedsReviewStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL)
        XCTAssertEqual(store.unmatchedEmails.map(\.id), [1, 2])

        let ok = await store.ignoreEmail(baseURL: baseURL, id: 1)

        XCTAssertTrue(ok)
        XCTAssertEqual(store.unmatchedEmails.map(\.id), [2])
        XCTAssertNil(store.actionErrorMessage)
    }

    func testIgnoreEmailServerErrorSurfacesInActionErrorMessageAndKeepsTheRow() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/categories" {
                return StubURLSession.json(#"{"items":[]}"#)
            }
            if request.url?.path.hasSuffix("/ignore") == true {
                return StubURLSession.json(#"{"detail": "boom"}"#, status: 500)
            }
            return StubURLSession.json("""
            { "unmatched_emails": [\(Self.emailJSON(id: 1, classifiedPatternId: nil))], "low_confidence_transactions": [] }
            """)
        }
        let store = NeedsReviewStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL)

        let ok = await store.ignoreEmail(baseURL: baseURL, id: 1)

        XCTAssertFalse(ok)
        XCTAssertEqual(store.unmatchedEmails.map(\.id), [1], "a failed ignore must not remove the row")
        XCTAssertNotNil(store.actionErrorMessage)

        store.clearActionError()
        XCTAssertNil(store.actionErrorMessage)
    }

    func testTotalCountSumsBothHalves() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/categories" {
                return StubURLSession.json(#"{"items":[]}"#)
            }
            return StubURLSession.json("""
            {
              "unmatched_emails": [\(Self.emailJSON(id: 1, classifiedPatternId: nil)), \(Self.emailJSON(id: 2, classifiedPatternId: "hdfc_upi_debit_v1"))],
              "low_confidence_transactions": [\(Self.transactionJSON(id: 7))]
            }
            """)
        }
        let store = NeedsReviewStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.totalCount, 3)
    }

    private static func emailJSON(id: Int, classifiedPatternId: String?, status: String = "needs_review") -> String {
        let patternField = classifiedPatternId.map { "\"\($0)\"" } ?? "null"
        return """
        {
          "id": \(id), "message_id": "18abc\(id)", "received_at": "2026-07-19T14:32:10",
          "status": "\(status)", "classified_pattern_id": \(patternField), "content": "raw body"
        }
        """
    }

    private static func transactionJSON(id: Int) -> String {
        """
        {
          "id": \(id), "amount": "120.00", "currency": "INR", "txn_date": "2026-07-19",
          "txn_time": null, "email_received_at": null,
          "payee": { "id": 1, "name": "Golkondas Cafe", "identifier": null },
          "instrument_last4": null, "category_id": null, "category_name": null,
          "payment_method": "upi", "txn_type": "debit", "reference_number": null,
          "confidence_score": 0.4, "review_status": "needs_review", "email_message_id": 7,
          "dismissed": false, "created_at": "2026-07-19T14:32:11+00:00"
        }
        """
    }
}
