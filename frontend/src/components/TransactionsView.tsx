import { useEffect, useState } from "react";
import {
  listTransactions,
  type PaymentMethod,
  type Transaction,
  type TransactionFilters,
  type TransactionType,
} from "../api/client";
import TransactionDetailPanel from "./TransactionDetailPanel";

const PAGE_SIZE = 50;

function formatAmount(txn: Transaction): string {
  const sign = txn.txn_type === "debit" ? "-" : "+";
  return `${sign}₹${txn.amount}`;
}

interface Props {
  // externalRefreshSignal: bumped by the parent (e.g. when the background SyncScheduler's
  // polling detects a new transaction) to force a refetch regardless of filters/pagination.
  externalRefreshSignal?: number;
  // openTransactionId: set by the parent (e.g. clicking a new-transaction notification) to open
  // that transaction's detail panel directly, even if it isn't on the currently-loaded page.
  openTransactionId?: number | null;
  onOpenedTransaction?: () => void;
}

export default function TransactionsView({
  externalRefreshSignal,
  openTransactionId,
  onOpenedTransaction,
}: Props) {
  const [filters, setFilters] = useState<TransactionFilters>({});
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listTransactions({ ...filters, limit: PAGE_SIZE, offset })
      .then((response) => {
        setItems(response.items);
        setTotal(response.total);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [filters, offset, reloadToken, externalRefreshSignal]);

  useEffect(() => {
    if (openTransactionId != null) {
      setSelectedId(openTransactionId);
      onOpenedTransaction?.();
    }
  }, [openTransactionId, onOpenedTransaction]);

  function updateFilter<K extends keyof TransactionFilters>(key: K, value: TransactionFilters[K]) {
    setOffset(0);
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function refresh() {
    setReloadToken((token) => token + 1);
  }

  return (
    <div className="view">
      <h2>Transactions</h2>

      <div className="filter-bar">
        <input
          type="text"
          placeholder="Search payee or category…"
          onChange={(e) => updateFilter("q", e.target.value)}
        />
        <input
          type="text"
          placeholder="Payee contains…"
          onChange={(e) => updateFilter("payee", e.target.value)}
        />
        <select
          onChange={(e) =>
            updateFilter("txn_type", (e.target.value || undefined) as TransactionType | undefined)
          }
        >
          <option value="">All types</option>
          <option value="debit">Debit</option>
          <option value="credit">Credit</option>
        </select>
        <select
          onChange={(e) =>
            updateFilter(
              "payment_method",
              (e.target.value || undefined) as PaymentMethod | undefined,
            )
          }
        >
          <option value="">All methods</option>
          <option value="upi">UPI</option>
          <option value="credit_card">Credit Card</option>
        </select>
        <input type="date" onChange={(e) => updateFilter("date_from", e.target.value)} />
        <input type="date" onChange={(e) => updateFilter("date_to", e.target.value)} />
        <input
          type="number"
          placeholder="Min ₹"
          onChange={(e) => updateFilter("amount_min", e.target.value)}
        />
        <input
          type="number"
          placeholder="Max ₹"
          onChange={(e) => updateFilter("amount_max", e.target.value)}
        />
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p>Loading…</p>}

      {!loading && !error && (
        <>
          <table className="transactions-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Payee</th>
                <th>Category</th>
                <th>Method</th>
                <th>Amount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((txn) => (
                <tr key={txn.id} onClick={() => setSelectedId(txn.id)} className="row-clickable">
                  <td>{txn.txn_date}</td>
                  <td>{txn.payee.name}</td>
                  <td>{txn.category_name ?? "—"}</td>
                  <td>{txn.payment_method === "upi" ? "UPI" : "Credit Card"}</td>
                  <td className={txn.txn_type === "debit" ? "amount-debit" : "amount-credit"}>
                    {formatAmount(txn)}
                  </td>
                  <td>{txn.review_status}</td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6}>No transactions match these filters.</td>
                </tr>
              )}
            </tbody>
          </table>

          <div className="pagination">
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
              Previous
            </button>
            <span>
              {total === 0 ? 0 : offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
            </span>
            <button
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </>
      )}

      {selectedId !== null && (
        <TransactionDetailPanel
          transactionId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={() => {
            refresh();
          }}
        />
      )}
    </div>
  );
}
