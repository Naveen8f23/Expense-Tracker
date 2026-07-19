import XCTest
@testable import Ledger

@MainActor
final class TransactionDetailStoreTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!

    func testLoadWithNoBaseURLSetsErrorAndDoesNotTouchTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = TransactionDetailStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: nil, id: 1)

        XCTAssertNil(store.transaction)
        XCTAssertNotNil(store.errorMessage)
    }

    func testLoadPopulatesTransaction() async {
        let stub = StubURLSession { _ in StubURLSession.json(Self.transactionJSON(dismissed: false)) }
        let store = TransactionDetailStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL, id: 1)

        XCTAssertEqual(store.transaction?.id, 1)
        XCTAssertEqual(store.transaction?.payee.name, "Golkondas Cafe")
    }

    func testSaveSendsCorrectionAndUpdatesLocalTransaction() async throws {
        var capturedBody: [String: Any]?
        let stub = StubURLSession { request in
            if request.httpMethod == "PATCH" {
                capturedBody = try? JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: Any]
                return StubURLSession.json(Self.transactionJSON(dismissed: false, amount: "999.00"))
            }
            return StubURLSession.json(Self.transactionJSON(dismissed: false))
        }
        let store = TransactionDetailStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL, id: 1)

        var correction = TransactionCorrectionRequest()
        correction.amount = "999.00"
        let success = await store.save(baseURL: baseURL, correction: correction)

        XCTAssertTrue(success)
        XCTAssertEqual(store.transaction?.amount, "999.00")
        XCTAssertEqual(capturedBody?["amount"] as? String, "999.00")
        XCTAssertNil(capturedBody?["category_id"], "unset fields must not be sent")
    }

    func testDismissMarksTransactionDismissed() async {
        let stub = StubURLSession { request in
            if request.url?.path.hasSuffix("/dismiss") == true {
                return StubURLSession.json(Self.transactionJSON(dismissed: true))
            }
            return StubURLSession.json(Self.transactionJSON(dismissed: false))
        }
        let store = TransactionDetailStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL, id: 1)

        let success = await store.dismissTransaction(baseURL: baseURL)

        XCTAssertTrue(success)
        XCTAssertEqual(store.transaction?.dismissed, true)
    }

    func testSaveFailureSurfacesErrorAndReturnsFalse() async {
        let stub = StubURLSession { request in
            if request.httpMethod == "PATCH" {
                return StubURLSession.json(#"{"detail": "boom"}"#, status: 500)
            }
            return StubURLSession.json(Self.transactionJSON(dismissed: false))
        }
        let store = TransactionDetailStore { APIClient(baseURL: $0, session: stub) }
        await store.load(baseURL: baseURL, id: 1)

        let success = await store.save(baseURL: baseURL, correction: TransactionCorrectionRequest())

        XCTAssertFalse(success)
        XCTAssertNotNil(store.errorMessage)
    }

    private static func transactionJSON(dismissed: Bool, amount: String = "120.00") -> String {
        """
        {
          "id": 1, "amount": "\(amount)", "currency": "INR", "txn_date": "2026-07-19",
          "txn_time": null, "email_received_at": null,
          "payee": { "id": 1, "name": "Golkondas Cafe", "identifier": null },
          "instrument_last4": null, "category_id": null, "category_name": null,
          "payment_method": "upi", "txn_type": "debit", "reference_number": null,
          "confidence_score": 1.0, "review_status": "auto_accepted", "email_message_id": 7,
          "dismissed": \(dismissed), "created_at": "2026-07-19T14:32:11+00:00"
        }
        """
    }
}
