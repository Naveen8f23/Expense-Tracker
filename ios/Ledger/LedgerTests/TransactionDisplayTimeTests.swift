import XCTest
@testable import Ledger

final class TransactionDisplayTimeTests: XCTestCase {
    private func makeTransaction(
        txnTime: String?,
        emailReceivedAt: String?,
        createdAt: String = "2026-07-19T09:00:00"
    ) -> Transaction {
        Transaction(
            id: 1, amount: "120.00", currency: "INR", txnDate: "2026-07-19", txnTime: txnTime,
            emailReceivedAt: emailReceivedAt, payee: Payee(id: 1, name: "Test", identifier: nil),
            instrumentLast4: nil, categoryId: nil, categoryName: nil, paymentMethod: "upi",
            txnType: "debit", referenceNumber: nil, confidenceScore: 1.0,
            reviewStatus: "auto_accepted", emailMessageId: 7, dismissed: false, createdAt: createdAt,
            sourceEmail: nil
        )
    }

    func testRealTxnTimeHasNoApproximationMarker() {
        let txn = makeTransaction(txnTime: "14:32:00", emailReceivedAt: "2026-07-19T14:32:10")

        let text = TransactionDisplayTime.string(for: txn)

        // Avoid asserting an exact 12-hour-format string — that's locale-dependent (this just
        // needs to prove a real time was appended, with no approximation marker).
        XCTAssertTrue(text.hasPrefix("2026-07-19 "))
        XCTAssertNotEqual(text, "2026-07-19 ")
        XCTAssertFalse(text.contains("~"))
        XCTAssertFalse(TransactionDisplayTime.isApproximate(txn))
    }

    func testMissingTxnTimeFallsBackToEmailReceivedTimeWithApproximationMarker() {
        let txn = makeTransaction(txnTime: nil, emailReceivedAt: "2026-07-19T14:32:10")

        let text = TransactionDisplayTime.string(for: txn)

        XCTAssertTrue(text.contains("~"), "no real txn_time should show the approximation marker")
        XCTAssertTrue(TransactionDisplayTime.isApproximate(txn))
        XCTAssertTrue(TransactionDisplayTime.approximationReason(txn).contains("source email"))
    }

    func testManualEntryWithNoEmailFallsBackToCreatedAt() {
        // H2's manual-add case: no txn_time, no email_received_at at all.
        let txn = makeTransaction(txnTime: nil, emailReceivedAt: nil, createdAt: "2026-07-19T09:15:00")

        let text = TransactionDisplayTime.string(for: txn)

        XCTAssertTrue(text.contains("~"))
        XCTAssertTrue(TransactionDisplayTime.approximationReason(txn).contains("manually-added"))
    }

    func testTolerateMicrosecondPrecisionInCreatedAt() {
        // The backend's real `created_at` shape (6-digit fractional seconds, no timezone suffix
        // at all) — must not crash or silently fall back to just the date.
        let txn = makeTransaction(
            txnTime: nil, emailReceivedAt: nil, createdAt: "2026-07-19T09:15:00.123456"
        )

        let text = TransactionDisplayTime.string(for: txn)

        XCTAssertNotEqual(text, txn.txnDate, "should include a parsed approximate time, not just the bare date")
    }

    func testAlsoToleratesAnExplicitOffsetIfOneIsEverPresent() {
        // Defensive: if the backend's serialization ever changes to include an explicit offset
        // (unlike its current naive-UTC shape), parsing must still work rather than double-append
        // a "Z" onto an already-offset string.
        let txn = makeTransaction(txnTime: nil, emailReceivedAt: "2026-07-19T14:32:10+05:30")

        let text = TransactionDisplayTime.string(for: txn)

        XCTAssertNotEqual(text, txn.txnDate)
    }
}
