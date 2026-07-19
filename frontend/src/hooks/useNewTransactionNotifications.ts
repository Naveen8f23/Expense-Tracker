import { useEffect, useRef, useState } from "react";
import { getRecentTransactions, type Transaction } from "../api/client";

// Matches the backend SyncScheduler's default interval (app/infrastructure/sync_scheduler.py) --
// no point polling faster than the background sync itself can produce new rows.
const POLL_INTERVAL_MS = 5000;

interface Options {
  onNewTransactions: (transactions: Transaction[]) => void;
  onNotificationClick: (transactionId: number) => void;
}

export function useNewTransactionNotifications({ onNewTransactions, onNotificationClick }: Options) {
  const lastSeenId = useRef(0);
  const hasBaseline = useRef(false);
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "denied",
  );

  // Refs so the poll loop below always calls the latest callbacks without needing to restart
  // its setTimeout chain (and without a stale closure) whenever the parent re-renders.
  const onNewTransactionsRef = useRef(onNewTransactions);
  onNewTransactionsRef.current = onNewTransactions;
  const onNotificationClickRef = useRef(onNotificationClick);
  onNotificationClickRef.current = onNotificationClick;

  function requestPermission() {
    if (typeof Notification === "undefined") return;
    Notification.requestPermission().then(setPermission);
  }

  useEffect(() => {
    let cancelled = false;
    let timeoutId: number;

    async function poll() {
      try {
        // The first poll only establishes a baseline (today's existing transactions) -- it must
        // never fire a notification for everything that already existed before the tab opened.
        // Tracked via a separate flag, not "lastSeenId === null": a baseline of zero existing
        // transactions must still count as an established baseline, or the first genuinely new
        // transaction afterward would be silently swallowed as if it were part of it.
        const isBaseline = !hasBaseline.current;
        const { items } = await getRecentTransactions(isBaseline ? 0 : lastSeenId.current);

        if (items.length > 0) {
          lastSeenId.current = Math.max(...items.map((t) => t.id));
        }
        hasBaseline.current = true;

        if (!isBaseline && items.length > 0) {
          onNewTransactionsRef.current(items);
          if (typeof Notification !== "undefined" && Notification.permission === "granted") {
            for (const txn of items) {
              const sign = txn.txn_type === "debit" ? "-" : "+";
              const notification = new Notification("New transaction detected", {
                body: `${sign}₹${txn.amount} · ${txn.payee.name}`,
                tag: `txn-${txn.id}`,
              });
              notification.onclick = () => {
                window.focus();
                onNotificationClickRef.current(txn.id);
                notification.close();
              };
            }
          }
        }
      } catch {
        // Transient network hiccup -- just try again next interval, never crash the poll loop.
      }
      if (!cancelled) {
        timeoutId = window.setTimeout(poll, POLL_INTERVAL_MS);
      }
    }

    timeoutId = window.setTimeout(poll, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, []);

  return { permission, requestPermission };
}
