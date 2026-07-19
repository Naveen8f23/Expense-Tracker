import XCTest
@testable import Ledger

@MainActor
final class SyncHealthStoreTests: XCTestCase {
    private let baseURL = URL(string: "https://turnny-vm.test")!

    func testLoadWithNoBaseURLSetsUnknownAndDoesNotTouchTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called"); throw StubTransportError() }
        let store = SyncHealthStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: nil)

        XCTAssertEqual(store.health, .unknown)
        XCTAssertNotNil(store.errorMessage)
    }

    func testNoGmailConnectionYetIsNotConnectedNotAnError() async {
        let stub = StubURLSession { _ in StubURLSession.json(#"{"detail": "No Gmail connection configured yet"}"#, status: 404) }
        let store = SyncHealthStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.health, .notConnected)
        XCTAssertNil(store.errorMessage)
    }

    func testConnectedButNotYetSyncedIsPendingFirstSync() async {
        let stub = StubURLSession { _ in
            StubURLSession.json(#"{"connected": true, "email_address": "naveen8f23@gmail.com", "synced": false}"#)
        }
        let store = SyncHealthStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.health, .pendingFirstSync)
    }

    func testSyncedWithNoFailuresOrErrorIsHealthy() async {
        let stub = StubURLSession { _ in
            StubURLSession.json("""
            {
              "connected": true, "email_address": "naveen8f23@gmail.com", "synced": true,
              "last_sync_started_at": "2026-07-19T14:00:00+00:00",
              "last_sync_at": "2026-07-19T14:00:05+00:00", "last_error": null,
              "last_scanned": 6, "last_matched": 1, "last_skipped": 5, "last_failed": 0
            }
            """)
        }
        let store = SyncHealthStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.health, .healthy)
        XCTAssertEqual(store.status?.lastScanned, 6)
    }

    func testSyncedWithFailedMessagesIsIssues() async {
        let stub = StubURLSession { _ in
            StubURLSession.json("""
            {
              "connected": true, "email_address": "naveen8f23@gmail.com", "synced": true,
              "last_sync_started_at": "2026-07-19T14:00:00+00:00",
              "last_sync_at": "2026-07-19T14:00:05+00:00", "last_error": null,
              "last_scanned": 6, "last_matched": 1, "last_skipped": 3, "last_failed": 2
            }
            """)
        }
        let store = SyncHealthStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.health, .issues)
    }

    func testSyncedWithALastErrorIsIssuesEvenWithZeroFailedCount() async {
        let stub = StubURLSession { _ in
            StubURLSession.json("""
            {
              "connected": true, "email_address": "naveen8f23@gmail.com", "synced": true,
              "last_sync_started_at": "2026-07-19T14:00:00+00:00",
              "last_sync_at": "2026-07-19T14:00:05+00:00", "last_error": "OAuth refresh failed",
              "last_scanned": 0, "last_matched": 0, "last_skipped": 0, "last_failed": 0
            }
            """)
        }
        let store = SyncHealthStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.health, .issues)
    }

    func testUnreachableHostSurfacesAsUnknownWithAnErrorMessage() async {
        let stub = StubURLSession { _ in throw StubTransportError() }
        let store = SyncHealthStore { APIClient(baseURL: $0, session: stub) }

        await store.load(baseURL: baseURL)

        XCTAssertEqual(store.health, .unknown)
        XCTAssertNotNil(store.errorMessage)
    }
}
