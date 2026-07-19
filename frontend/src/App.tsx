import { useCallback, useEffect, useState } from "react";
import { getHealth } from "./api/client";
import AnalyticsView from "./components/AnalyticsView";
import NeedsReviewView from "./components/NeedsReviewView";
import TransactionsView from "./components/TransactionsView";
import { useNewTransactionNotifications } from "./hooks/useNewTransactionNotifications";

type BackendStatus = { kind: "loading" } | { kind: "healthy" } | { kind: "error"; message: string };
type View = "transactions" | "needs-review" | "analytics";

function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({ kind: "loading" });
  const [view, setView] = useState<View>("transactions");
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [pendingTransactionId, setPendingTransactionId] = useState<number | null>(null);

  useEffect(() => {
    getHealth()
      .then(() => setBackendStatus({ kind: "healthy" }))
      .catch((err) => setBackendStatus({ kind: "error", message: String(err) }));
  }, []);

  const onNewTransactions = useCallback(() => {
    setRefreshSignal((n) => n + 1);
  }, []);

  const onNotificationClick = useCallback((transactionId: number) => {
    setView("transactions");
    setPendingTransactionId(transactionId);
  }, []);

  // Polls the backend's SyncScheduler-produced transactions in the background (no "sync now"
  // button, per the owner's request) and fires a real browser Notification for each new one.
  const { permission, requestPermission } = useNewTransactionNotifications({
    onNewTransactions,
    onNotificationClick,
  });

  if (backendStatus.kind !== "healthy") {
    return (
      <main className="dashboard-app">
        <h1>Expense Tracker</h1>
        {backendStatus.kind === "loading" && <p>Checking backend…</p>}
        {backendStatus.kind === "error" && (
          <p>backend: unreachable ({backendStatus.message})</p>
        )}
      </main>
    );
  }

  return (
    <main className="dashboard-app">
      <div className="app-header">
        <h1>Expense Tracker</h1>
        {permission === "default" && (
          <button onClick={requestPermission}>Enable new-transaction notifications</button>
        )}
        {permission === "denied" && (
          <span className="metadata">Notifications blocked in browser settings</span>
        )}
      </div>
      <nav className="tabs">
        <button
          className={view === "transactions" ? "tab-active" : ""}
          onClick={() => setView("transactions")}
        >
          Transactions
        </button>
        <button
          className={view === "needs-review" ? "tab-active" : ""}
          onClick={() => setView("needs-review")}
        >
          Needs Review
        </button>
        <button
          className={view === "analytics" ? "tab-active" : ""}
          onClick={() => setView("analytics")}
        >
          Analytics
        </button>
      </nav>
      {view === "transactions" && (
        <TransactionsView
          externalRefreshSignal={refreshSignal}
          openTransactionId={pendingTransactionId}
          onOpenedTransaction={() => setPendingTransactionId(null)}
        />
      )}
      {view === "needs-review" && <NeedsReviewView />}
      {view === "analytics" && <AnalyticsView />}
    </main>
  );
}

export default App;
