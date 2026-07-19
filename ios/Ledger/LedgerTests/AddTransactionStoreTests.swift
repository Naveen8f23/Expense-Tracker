import XCTest
@testable import Ledger

@MainActor
final class AddTransactionStoreTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!

    func testSaveWithNoBaseURLSetsErrorAndDoesNotTouchTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = AddTransactionStore { APIClient(baseURL: $0, session: stub) }

        let ok = await store.save(baseURL: nil, request: Self.request())

        XCTAssertFalse(ok)
        XCTAssertNotNil(store.errorMessage)
    }

    func testSaveSendsTheRequestAndSucceeds() async throws {
        var capturedBody: [String: Any]?
        let stub = StubURLSession { request in
            capturedBody = try? JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: Any]
            return StubURLSession.json(Self.transactionJSON())
        }
        let store = AddTransactionStore { APIClient(baseURL: $0, session: stub) }

        let ok = await store.save(baseURL: baseURL, request: Self.request())

        XCTAssertTrue(ok)
        XCTAssertNil(store.errorMessage)
        XCTAssertEqual(capturedBody?["amount"] as? String, "120.00")
        XCTAssertEqual(capturedBody?["payee_name"] as? String, "Corner Store")
    }

    func testSaveServerErrorSurfacesInErrorMessageAndReturnsFalse() async {
        let stub = StubURLSession { _ in StubURLSession.json(#"{"detail": "boom"}"#, status: 500) }
        let store = AddTransactionStore { APIClient(baseURL: $0, session: stub) }

        let ok = await store.save(baseURL: baseURL, request: Self.request())

        XCTAssertFalse(ok)
        XCTAssertNotNil(store.errorMessage)
    }

    func testCreateCategoryReturnsTheCreatedCategory() async {
        let stub = StubURLSession { _ in StubURLSession.json(#"{"id":9,"name":"Cash"}"#) }
        let store = AddTransactionStore { APIClient(baseURL: $0, session: stub) }

        let created = await store.createCategory(baseURL: baseURL, name: "Cash")

        XCTAssertEqual(created?.id, 9)
        XCTAssertEqual(created?.name, "Cash")
    }

    private static func request() -> ManualTransactionRequest {
        ManualTransactionRequest(
            amount: "120.00", txnDate: "2026-07-19", payeeName: "Corner Store",
            paymentMethod: "upi", txnType: "debit", categoryId: nil
        )
    }

    private static func transactionJSON() -> String {
        """
        {
          "id": 1, "amount": "120.00", "currency": "INR", "txn_date": "2026-07-19",
          "txn_time": null, "email_received_at": null,
          "payee": { "id": 1, "name": "Corner Store", "identifier": null },
          "instrument_last4": null, "category_id": null, "category_name": null,
          "payment_method": "upi", "txn_type": "debit", "reference_number": null,
          "confidence_score": 1.0, "review_status": "user_confirmed", "email_message_id": null,
          "dismissed": false, "created_at": "2026-07-19T14:32:11+00:00"
        }
        """
    }
}
