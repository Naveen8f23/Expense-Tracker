import XCTest
@testable import Ledger

@MainActor
final class ConnectionSettingsStoreTests: XCTestCase {
    private var defaults: UserDefaults!
    private let suiteName = "ConnectionSettingsStoreTests"

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: suiteName)
        defaults.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        super.tearDown()
    }

    func testDefaultsToPortEightThousandWhenNothingSaved() {
        let store = ConnectionSettingsStore(defaults: defaults)
        XCTAssertEqual(store.host, "")
        XCTAssertEqual(store.port, "8000")
        XCTAssertNil(store.baseURL, "no host yet — must not synthesize a URL")
    }

    func testSavePersistsHostAndPortAcrossInstances() {
        let store = ConnectionSettingsStore(defaults: defaults)
        store.host = "turnny-vm"
        store.port = "8000"
        store.save()

        let reloaded = ConnectionSettingsStore(defaults: defaults)
        XCTAssertEqual(reloaded.host, "turnny-vm")
        XCTAssertEqual(reloaded.baseURL?.absoluteString, "http://turnny-vm:8000")
    }

    func testCheckReachabilityHealthyAndSyncedReportsReachable() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/health" {
                return StubURLSession.json(#"{"status":"ok"}"#)
            }
            return StubURLSession.json("""
            { "connected": true, "email_address": "naveen8f23@gmail.com", "synced": true }
            """)
        }
        let store = ConnectionSettingsStore(defaults: defaults) { APIClient(baseURL: $0, session: stub) }
        store.host = "turnny-vm"
        store.port = "8000"

        await store.checkReachability()

        XCTAssertEqual(store.reachability, .reachable(connected: true, synced: true))
    }

    func testCheckReachabilityNoGmailConnectionYetIsStillReachable() async {
        let stub = StubURLSession { request in
            if request.url?.path == "/health" {
                return StubURLSession.json(#"{"status":"ok"}"#)
            }
            return StubURLSession.json(#"{"detail": "No Gmail connection configured yet"}"#, status: 404)
        }
        let store = ConnectionSettingsStore(defaults: defaults) { APIClient(baseURL: $0, session: stub) }
        store.host = "turnny-vm"
        store.port = "8000"

        await store.checkReachability()

        XCTAssertEqual(store.reachability, .reachable(connected: false, synced: false))
    }

    func testCheckReachabilityUnreachableHostReportsUnreachableNotAHang() async {
        let stub = StubURLSession { _ in throw StubTransportError() }
        let store = ConnectionSettingsStore(defaults: defaults) { APIClient(baseURL: $0, session: stub) }
        store.host = "wrong-host"
        store.port = "8000"

        await store.checkReachability()

        guard case .unreachable = store.reachability else {
            return XCTFail("expected .unreachable, got \(store.reachability)")
        }
    }

    func testCheckReachabilityWithNoHostConfiguredDoesNotCallTheNetwork() async {
        let stub = StubURLSession { _ in XCTFail("should never be called with no host"); throw StubTransportError() }
        let store = ConnectionSettingsStore(defaults: defaults) { APIClient(baseURL: $0, session: stub) }

        await store.checkReachability()

        guard case .unreachable = store.reachability else {
            return XCTFail("expected .unreachable, got \(store.reachability)")
        }
    }
}
