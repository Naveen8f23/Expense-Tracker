import XCTest
@testable import Ledger

final class APIClientTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!

    // MARK: - Transactions

    func testListTransactionsDecodesGroundTruthShape() async throws {
        let json = """
        {
          "items": [
            {
              "id": 1,
              "amount": "120.00",
              "currency": "INR",
              "txn_date": "2026-07-19",
              "txn_time": null,
              "email_received_at": "2026-07-19T14:32:10+00:00",
              "payee": { "id": 1, "name": "Golkondas Cafe", "identifier": "cafe@upi" },
              "instrument_last4": "4958",
              "category_id": null,
              "category_name": null,
              "payment_method": "upi",
              "txn_type": "debit",
              "reference_number": "123456789012",
              "confidence_score": 1.0,
              "review_status": "auto_accepted",
              "email_message_id": 7,
              "dismissed": false,
              "created_at": "2026-07-19T14:32:11.123456+00:00"
            }
          ],
          "total": 137,
          "limit": 50,
          "offset": 0
        }
        """
        let stub = StubURLSession { _ in StubURLSession.json(json) }
        let client = APIClient(baseURL: baseURL, session: stub)

        let response = try await client.listTransactions()

        XCTAssertEqual(response.total, 137)
        XCTAssertEqual(response.items.count, 1)
        let txn = response.items[0]
        XCTAssertEqual(txn.amount, "120.00")
        XCTAssertEqual(txn.txnTime, nil)
        XCTAssertEqual(txn.payee.name, "Golkondas Cafe")
        XCTAssertEqual(txn.instrumentLast4, "4958")
        XCTAssertEqual(txn.reviewStatus, "auto_accepted")
        XCTAssertNil(txn.sourceEmail, "sourceEmail key is absent on the list endpoint")
    }

    func testGetTransactionIncludesSourceEmail() async throws {
        let json = """
        {
          "id": 1, "amount": "120.00", "currency": "INR", "txn_date": "2026-07-19",
          "txn_time": null, "email_received_at": "2026-07-19T14:32:10+00:00",
          "payee": { "id": 1, "name": "Golkondas Cafe", "identifier": "cafe@upi" },
          "instrument_last4": "4958", "category_id": null, "category_name": null,
          "payment_method": "upi", "txn_type": "debit", "reference_number": "123456789012",
          "confidence_score": 1.0, "review_status": "auto_accepted", "email_message_id": 7,
          "dismissed": false, "created_at": "2026-07-19T14:32:11.123456+00:00",
          "source_email": {
            "id": 7, "message_id": "18abc", "received_at": "2026-07-19T14:32:10+00:00",
            "status": "matched", "classified_pattern_id": "hdfc_upi_debit_v1", "content": "raw body"
          }
        }
        """
        let stub = StubURLSession { _ in StubURLSession.json(json) }
        let client = APIClient(baseURL: baseURL, session: stub)

        let txn = try await client.getTransaction(id: 1)

        XCTAssertEqual(txn.sourceEmail?.messageId, "18abc")
        XCTAssertEqual(txn.sourceEmail?.status, "matched")
    }

    func testCorrectTransactionOmitsUnsetFieldsFromRequestBody() async throws {
        var correction = TransactionCorrectionRequest()
        correction.categoryId = 3
        let stub = StubURLSession { request in
            let body = try XCTUnwrap(request.httpBody)
            let object = try JSONSerialization.jsonObject(with: body) as? [String: Any]
            XCTAssertEqual(object?.count, 1, "only the field actually set should be sent")
            XCTAssertEqual(object?["category_id"] as? Int, 3)
            XCTAssertNil(object?["amount"], "unset fields must be omitted, not sent as null")
            return StubURLSession.json(Self.minimalTransactionJSON)
        }
        let client = APIClient(baseURL: baseURL, session: stub)

        _ = try await client.correctTransaction(id: 1, correction)
    }

    func testDismissTransactionSendsNoRequestBody() async throws {
        let stub = StubURLSession { request in
            XCTAssertNil(request.httpBody)
            XCTAssertEqual(request.httpMethod, "POST")
            return StubURLSession.json(Self.minimalTransactionJSON)
        }
        let client = APIClient(baseURL: baseURL, session: stub)

        let txn = try await client.dismissTransaction(id: 1)
        XCTAssertEqual(txn.dismissed, true)
    }

    // MARK: - Sync status (three distinct shapes, BACKLOG.md I2 ground truth)

    func testSyncStatusConnectedAndSynced() async throws {
        let json = """
        {
          "connected": true, "email_address": "naveen8f23@gmail.com", "synced": true,
          "last_sync_started_at": "2026-07-19T14:00:00+00:00",
          "last_sync_at": "2026-07-19T14:00:05+00:00", "last_error": null,
          "last_scanned": 42, "last_matched": 10, "last_skipped": 30, "last_failed": 2
        }
        """
        let stub = StubURLSession { _ in StubURLSession.json(json) }
        let client = APIClient(baseURL: baseURL, session: stub)

        let status = try await client.syncStatus()
        XCTAssertEqual(status.synced, true)
        XCTAssertEqual(status.lastScanned, 42)
    }

    func testSyncStatusConnectedButNeverSynced() async throws {
        // last_sync_* keys are absent entirely, not null — decoding must not throw.
        let json = """
        { "connected": true, "email_address": "naveen8f23@gmail.com", "synced": false }
        """
        let stub = StubURLSession { _ in StubURLSession.json(json) }
        let client = APIClient(baseURL: baseURL, session: stub)

        let status = try await client.syncStatus()
        XCTAssertEqual(status.synced, false)
        XCTAssertNil(status.lastScanned)
        XCTAssertNil(status.lastSyncAt)
    }

    func testSyncStatusNotConnectedSurfacesAsHTTPError() async throws {
        let json = """
        { "detail": "No Gmail connection configured yet" }
        """
        let stub = StubURLSession { _ in StubURLSession.json(json, status: 404) }
        let client = APIClient(baseURL: baseURL, session: stub)

        do {
            _ = try await client.syncStatus()
            XCTFail("expected an error")
        } catch APIError.httpError(let status, let detail) {
            XCTAssertEqual(status, 404)
            XCTAssertEqual(detail, "No Gmail connection configured yet")
        }
    }

    // MARK: - Category delete: two distinct error shapes

    func testDeleteCategoryNotFoundIsPlainStringDetail() async throws {
        let json = """
        { "detail": "No category with id 99" }
        """
        let stub = StubURLSession { _ in StubURLSession.json(json, status: 404) }
        let client = APIClient(baseURL: baseURL, session: stub)

        do {
            try await client.deleteCategory(id: 99)
            XCTFail("expected an error")
        } catch APIError.httpError(let status, let detail) {
            XCTAssertEqual(status, 404)
            XCTAssertEqual(detail, "No category with id 99")
        }
    }

    func testDeleteCategoryInUseIsNestedConflictDetail() async throws {
        let json = """
        { "detail": { "message": "Category 3 is used by 5 transaction(s)", "transaction_count": 5 } }
        """
        let stub = StubURLSession { _ in StubURLSession.json(json, status: 409) }
        let client = APIClient(baseURL: baseURL, session: stub)

        do {
            try await client.deleteCategory(id: 3)
            XCTFail("expected an error")
        } catch APIError.categoryInUse(let message, let count) {
            XCTAssertEqual(count, 5)
            XCTAssertTrue(message.contains("5 transaction"))
        }
    }

    // MARK: - Unreachable host

    func testUnreachableHostSurfacesAsUnreachableNotACrash() async throws {
        let stub = StubURLSession { _ in throw StubTransportError() }
        let client = APIClient(baseURL: baseURL, session: stub)

        do {
            _ = try await client.syncStatus()
            XCTFail("expected an error")
        } catch APIError.unreachable {
            // expected
        }
    }

    // MARK: - Payee path encoding

    func testPayeeHistoryPercentEncodesTheNameExactlyOnce() async throws {
        let stub = StubURLSession { request in
            let path = request.url?.path ?? ""
            XCTAssertTrue(path.contains("Golkondas Cafe") || request.url?.absoluteString.contains("Golkondas%20Cafe") == true)
            XCTAssertFalse(request.url?.absoluteString.contains("%2520") ?? true, "must not double-encode")
            return StubURLSession.json("""
            {
              "payee_name": "Golkondas Cafe", "total_debit": "500.00", "total_credit": "0.00",
              "net": "500.00", "transaction_count": 12, "limit": 50, "offset": 0, "items": []
            }
            """)
        }
        let client = APIClient(baseURL: baseURL, session: stub)

        let history = try await client.payeeHistory(payee: "Golkondas Cafe")
        XCTAssertEqual(history.transactionCount, 12)
    }

    private static let minimalTransactionJSON = """
    {
      "id": 1, "amount": "120.00", "currency": "INR", "txn_date": "2026-07-19",
      "txn_time": null, "email_received_at": null,
      "payee": { "id": 1, "name": "Golkondas Cafe", "identifier": null },
      "instrument_last4": null, "category_id": null, "category_name": null,
      "payment_method": "upi", "txn_type": "debit", "reference_number": null,
      "confidence_score": 1.0, "review_status": "user_confirmed", "email_message_id": null,
      "dismissed": true, "created_at": "2026-07-19T14:32:11.123456+00:00"
    }
    """
}
