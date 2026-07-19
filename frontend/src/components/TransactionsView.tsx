import { useEffect, useState } from "react";
import {
  listTransactions,
  type PaymentMethod,
  type Transaction,
  type TransactionFilters,
  type TransactionType,
} from "../api/client";
import AddTransactionPanel from "./AddTransactionPanel";
import PayeeHistoryPanel from "./PayeeHistoryPanel";
import TransactionDetailPanel from "./TransactionDetailPanel";
import { TransactionDateTime } from "../utils/transactionTime";

const PAGE_SIZE = 50;
// G1: debounce free-text/payee input so typing doesn't fire one request per keystroke.
const SEARCH_DEBOUNCE_MS = 400;

const FILTER_LABELS: Partial<Record<keyof TransactionFilters, string>> = {
  q: "Search",
  payee: "Payee",
  category_id: "Category",
  txn_type: "Type",
  payment_method: "Method",
  date_from: "From",
  date_to: "To",
  amount_min: "Min ₹",
  amount_max: "Max ₹",
};

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
  // Controlled draft for the two debounced free-text inputs -- kept separate from `filters` so
  // typing feels immediate while the actual fetch-triggering state only updates after the pause.
  const [searchDraft, setSearchDraft] = useState({ q: "", payee: "" });
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedPayee, setSelectedPayee] = useState<string | null>(null);
  const [addingTransaction, setAddingTransaction] = useState(false);
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

  useEffect(() => {
    const timeout = setTimeout(() => {
      setFilters((prev) => {
        const nextQ = searchDraft.q || undefined;
        const nextPayee = searchDraft.payee || undefined;
        if (prev.q === nextQ && prev.payee === nextPayee) return prev;
        return { ...prev, q: nextQ, payee: nextPayee };
      });
      setOffset(0);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchDraft.q, searchDraft.payee]);

  function updateFilter<K extends keyof TransactionFilters>(key: K, value: TransactionFilters[K]) {
    setOffset(0);
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function removeFilter(key: keyof TransactionFilters) {
    updateFilter(key, undefined);
    if (key === "q" || key === "payee") {
      setSearchDraft((prev) => ({ ...prev, [key]: "" }));
    }
  }

  function clearAllFilters() {
    setFilters({});
    setOffset(0);
    setSearchDraft({ q: "", payee: "" });
  }

  function refresh() {
    setReloadToken((token) => token + 1);
  }

  const activeFilterChips = (Object.entries(filters) as [keyof TransactionFilters, unknown][])
    .filter(([, value]) => value !== undefined && value !== "")
    .map(([key, value]) => ({ key, label: `${FILTER_LABELS[key] ?? key}: ${String(value)}` }));

  return (
    <div className="view">
      <div className="view-header">
        <h2>Transactions</h2>
        <button type="button" onClick={() => setAddingTransaction(true)}>
          + Add transaction
        </button>
      </div>

      <div className="filter-bar">
        <input
          type="text"
          placeholder="Search payee or category…"
          value={searchDraft.q}
          onChange={(e) => setSearchDraft((prev) => ({ ...prev, q: e.target.value }))}
        />
        <input
          type="text"
          placeholder="Payee contains…"
          value={searchDraft.payee}
          onChange={(e) => setSearchDraft((prev) => ({ ...prev, payee: e.target.value }))}
        />
        <select
          value={filters.txn_type ?? ""}
          onChange={(e) =>
            updateFilter("txn_type", (e.target.value || undefined) as TransactionType | undefined)
          }
        >
          <option value="">All types</option>
          <option value="debit">Debit</option>
          <option value="credit">Credit</option>
        </select>
        <select
          value={filters.payment_method ?? ""}
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
        <input
          type="date"
          value={filters.date_from ?? ""}
          onChange={(e) => updateFilter("date_from", e.target.value || undefined)}
        />
        <input
          type="date"
          value={filters.date_to ?? ""}
          onChange={(e) => updateFilter("date_to", e.target.value || undefined)}
        />
        <input
          type="number"
          placeholder="Min ₹"
          value={filters.amount_min ?? ""}
          onChange={(e) => updateFilter("amount_min", e.target.value || undefined)}
        />
        <input
          type="number"
          placeholder="Max ₹"
          value={filters.amount_max ?? ""}
          onChange={(e) => updateFilter("amount_max", e.target.value || undefined)}
        />
        <button type="button" onClick={clearAllFilters} disabled={activeFilterChips.length === 0}>
          Clear all filters
        </button>
      </div>

      {activeFilterChips.length > 0 && (
        <div className="filter-chips">
          {activeFilterChips.map(({ key, label }) => (
            <span key={key} className="filter-chip">
              {label}
              <button type="button" aria-label={`Remove ${label} filter`} onClick={() => removeFilter(key)}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}

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
                  <td>
                    <TransactionDateTime txn={txn} />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="link-button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedPayee(txn.payee.name);
                      }}
                    >
                      {txn.payee.name}
                    </button>
                    {txn.email_message_id === null && (
                      <span className="badge-manual" title="Manually added — no source email">
                        Manual
                      </span>
                    )}
                  </td>
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

      {selectedPayee !== null && (
        <PayeeHistoryPanel
          payeeName={selectedPayee}
          onClose={() => setSelectedPayee(null)}
          onOpenTransaction={(transactionId) => {
            setSelectedPayee(null);
            setSelectedId(transactionId);
          }}
        />
      )}

      {addingTransaction && (
        <AddTransactionPanel
          onClose={() => setAddingTransaction(false)}
          onCreated={() => {
            refresh();
          }}
        />
      )}
    </div>
  );
}
