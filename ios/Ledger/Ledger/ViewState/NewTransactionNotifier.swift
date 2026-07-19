import Foundation
import UserNotifications

/// Drives BACKLOG.md M2 (REQUIREMENTS.md MOB-4, ADR-0024) — polls `GET /transactions/recent`
/// on the same ~5s cadence as the web dashboard's `useNewTransactionNotifications` hook and fires
/// a local `UNNotificationRequest` per new transaction. In-app/foreground-only by design: nothing
/// arrives once Ledger has been fully backgrounded for more than iOS's short suspended-but-alive
/// window, or force-quit — a deliberate, accepted scope (ADR-0024), not a bug to "fix" later.
///
/// `hasBaseline` is tracked explicitly, not inferred from `lastSeenId == nil` — the web dashboard's
/// own equivalent hook (ADR-0019) had exactly this bug: an empty-at-first-load history left
/// `lastSeenId` still nil after the first poll, so the *next* genuinely-new transaction was
/// silently absorbed into the "baseline" instead of notifying. An explicit flag can't have that
/// ambiguity.
///
/// Both are persisted in `UserDefaults` (BACKLOG.md M3) rather than kept purely in memory — a
/// `BGAppRefreshTask` run can launch a fresh process with no connection to the foreground
/// polling loop's in-memory state; without persisting where the *previous* run (foreground or
/// background) left off, every background-triggered check would re-treat the whole history as
/// "baseline" and never actually notify anything.
@MainActor
final class NewTransactionNotifier: NSObject, ObservableObject {
    /// Set when a notification is tapped; the root view observes this to open that transaction's
    /// J3 detail sheet. Consumed (set back to nil) by whoever presents it.
    @Published var deepLinkTransactionId: Int?

    private let defaults: UserDefaults
    private static let lastSeenIdKey = "newTransactionNotifier.lastSeenId"
    private static let hasBaselineKey = "newTransactionNotifier.hasBaseline"

    private var lastSeenId: Int {
        get { defaults.integer(forKey: Self.lastSeenIdKey) }
        set { defaults.set(newValue, forKey: Self.lastSeenIdKey) }
    }
    private var hasBaseline: Bool {
        get { defaults.bool(forKey: Self.hasBaselineKey) }
        set { defaults.set(newValue, forKey: Self.hasBaselineKey) }
    }

    private var pollTask: Task<Void, Never>?
    private let makeClient: (URL) -> APIClient
    private let pollIntervalNanoseconds: UInt64

    init(
        makeClient: @escaping (URL) -> APIClient = { APIClient(baseURL: $0) },
        pollIntervalNanoseconds: UInt64 = 5_000_000_000,
        defaults: UserDefaults = .standard
    ) {
        self.makeClient = makeClient
        self.pollIntervalNanoseconds = pollIntervalNanoseconds
        self.defaults = defaults
        super.init()
    }

    func requestAuthorization() {
        UNUserNotificationCenter.current().delegate = self
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { _, _ in }
    }

    /// A no-op if already polling — safe to call repeatedly (e.g. on every scenePhase change to
    /// `.active`) without spawning a second concurrent loop.
    func startPolling(baseURL: URL?) {
        guard pollTask == nil, let baseURL else { return }
        pollTask = Task { [weak self] in
            while !Task.isCancelled {
                await self?.poll(baseURL: baseURL)
                try? await Task.sleep(nanoseconds: self?.pollIntervalNanoseconds ?? 5_000_000_000)
            }
        }
    }

    func stopPolling() {
        pollTask?.cancel()
        pollTask = nil
    }

    /// Exposed directly (not just via the polling loop) so it's unit-testable without waiting on
    /// real sleeps.
    func poll(baseURL: URL) async {
        do {
            let response = try await makeClient(baseURL).recentTransactions(sinceId: lastSeenId)
            if hasBaseline {
                for transaction in response.items {
                    scheduleNotification(for: transaction)
                }
            }
            if let maxId = response.items.map(\.id).max() {
                lastSeenId = max(lastSeenId, maxId)
            }
            hasBaseline = true
        } catch {
            // Best-effort — try again next cycle rather than surfacing a persistent error UI for
            // a background polling loop the owner never directly interacts with.
        }
    }

    private func scheduleNotification(for transaction: Transaction) {
        let content = UNMutableNotificationContent()
        content.title = transaction.txnType == "credit" ? "Money received" : "New transaction"
        content.body = "\(transaction.payee.name) — \u{20B9}\(transaction.amount)"
        content.sound = .default
        content.userInfo = ["transactionId": transaction.id]
        let request = UNNotificationRequest(identifier: "txn-\(transaction.id)", content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request)
    }
}

extension NewTransactionNotifier: UNUserNotificationCenterDelegate {
    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        if let id = response.notification.request.content.userInfo["transactionId"] as? Int {
            Task { @MainActor in self.deepLinkTransactionId = id }
        }
        completionHandler()
    }

    /// Shows the banner even while Ledger is already in the foreground — without this, iOS
    /// suppresses local notifications for the frontmost app by default, which would make the
    /// whole feature invisible during exactly the scenario it's built for (MOB-4).
    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner, .badge, .sound])
    }
}
