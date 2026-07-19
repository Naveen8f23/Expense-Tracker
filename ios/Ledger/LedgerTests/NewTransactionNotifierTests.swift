import XCTest
@testable import Ledger

@MainActor
final class NewTransactionNotifierTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!
    private var defaults: UserDefaults!
    private let suiteName = "NewTransactionNotifierTests"

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: suiteName)
        defaults.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        super.tearDown()
    }

    private func makeNotifier(session: StubURLSession) -> NewTransactionNotifier {
        NewTransactionNotifier(makeClient: { APIClient(baseURL: $0, session: session) }, defaults: defaults)
    }

    func testFirstPollEstablishesBaselineWithoutNotifying() async {
        var requestedSinceId: String?
        let stub = StubURLSession { request in
            requestedSinceId = request.url?.query
            return StubURLSession.json("""
            { "items": [\(Self.transactionJSON(id: 5)), \(Self.transactionJSON(id: 7))] }
            """)
        }
        let notifier = makeNotifier(session: stub)

        // First poll ever: even though the "recent" endpoint returns real rows (an empty-history
        // start, mirrors the web dashboard's own ADR-0019 bug), nothing should be treated as new
        // — there's no prior baseline to compare against.
        await notifier.poll(baseURL: baseURL)

        XCTAssertEqual(requestedSinceId, "since_id=0")
    }

    func testPollWithNoInitialItemsKeepsBaselineAtZeroForTheNextPoll() async {
        var callCount = 0
        var requestedSinceIds: [String] = []
        let stub = StubURLSession { request in
            callCount += 1
            requestedSinceIds.append(request.url?.query ?? "")
            if callCount == 1 {
                return StubURLSession.json(#"{ "items": [] }"#)
            }
            return StubURLSession.json("""
            { "items": [\(Self.transactionJSON(id: 9))] }
            """)
        }
        let notifier = makeNotifier(session: stub)

        await notifier.poll(baseURL: baseURL) // establishes baseline: nothing existed yet
        await notifier.poll(baseURL: baseURL) // id 9 is genuinely new now (this is the ADR-0019 bug: an empty-at-first-poll history must not leave the *next* real arrival stuck as "already seen")

        XCTAssertEqual(requestedSinceIds, ["since_id=0", "since_id=0"], "no items were seen yet, so since_id stays 0 until something real arrives")
    }

    func testBaselineAdvancesToTheHighestIdSeenAcrossPolls() async {
        var requestedQueries: [String] = []
        var callCount = 0
        let stub = StubURLSession { request in
            callCount += 1
            requestedQueries.append(request.url?.query ?? "")
            if callCount == 1 {
                return StubURLSession.json("""
                { "items": [\(Self.transactionJSON(id: 3)), \(Self.transactionJSON(id: 12)), \(Self.transactionJSON(id: 8))] }
                """)
            }
            return StubURLSession.json(#"{ "items": [] }"#)
        }
        let notifier = makeNotifier(session: stub)

        await notifier.poll(baseURL: baseURL) // baseline: highest id (12) among 3/12/8
        await notifier.poll(baseURL: baseURL) // must ask for anything newer than 12, not 8 or 3

        XCTAssertEqual(requestedQueries, ["since_id=0", "since_id=12"])
    }

    func testStartPollingIsANoOpWithNoBaseURL() {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let notifier = makeNotifier(session: stub)

        notifier.startPolling(baseURL: nil)

        // No crash, no request — nothing to assert beyond "didn't touch the network," covered by
        // the stub's own XCTFail.
    }

    /// BACKLOG.md M3 — a fresh `NewTransactionNotifier` instance (as a `BGAppRefreshTask` launch
    /// would create, in a new process with no connection to the foreground loop's in-memory
    /// state) must pick up the *persisted* baseline rather than re-treating existing history as
    /// new, as long as both instances share the same `UserDefaults`.
    func testBaselinePersistsAcrossSeparateNotifierInstancesSharingTheSameDefaults() async {
        let stub1 = StubURLSession { _ in
            StubURLSession.json("""
            { "items": [\(Self.transactionJSON(id: 3)), \(Self.transactionJSON(id: 12))] }
            """)
        }
        let firstRunNotifier = makeNotifier(session: stub1)
        await firstRunNotifier.poll(baseURL: baseURL) // simulates the foreground loop's first poll

        var secondRunQuery: String?
        let stub2 = StubURLSession { request in
            secondRunQuery = request.url?.query
            return StubURLSession.json(#"{ "items": [] }"#)
        }
        // A brand-new instance, as a background task launch would create — same `defaults`.
        let backgroundRunNotifier = makeNotifier(session: stub2)
        await backgroundRunNotifier.poll(baseURL: baseURL)

        XCTAssertEqual(secondRunQuery, "since_id=12", "a fresh instance must resume from the persisted baseline, not restart from 0")
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
