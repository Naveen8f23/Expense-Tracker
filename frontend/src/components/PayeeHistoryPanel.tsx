import { useEffect, useState } from "react";
import { getPayeeHistory, type PayeeHistory } from "../api/client";
import { TransactionDateTime } from "../utils/transactionTime";

interface Props {
  payeeName: string;
  onClose: () => void;
  onOpenTransaction: (transactionId: number) => void;
}

export default function PayeeHistoryPanel({ payeeName, onClose, onOpenTransaction }: Props) {
  const [history, setHistory] = useState<PayeeHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getPayeeHistory(payeeName)
      .then(setHistory)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [payeeName]);

  return (
    <div className="panel-overlay" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-header">
          <h3>{payeeName}</h3>
          <button onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        {loading && <p>Loading…</p>}
        {error && <p className="error">{error}</p>}

        {history && !loading && (
          <>
            <div className="analytics-summary-cards">
              <div className="summary-card">
                <span className="metadata">Spent</span>
                <span className="amount-debit">₹{history.total_debit}</span>
              </div>
              <div className="summary-card">
                <span className="metadata">Received</span>
                <span className="amount-credit">₹{history.total_credit}</span>
              </div>
              <div className="summary-card">
                <span className="metadata">Net</span>
                <span>₹{history.net}</span>
              </div>
              <div className="summary-card">
                <span className="metadata">Transactions</span>
                <span>{history.transaction_count}</span>
              </div>
            </div>

            <ul className="review-list">
              {history.items.map((txn) => (
                <li
                  key={txn.id}
                  className="row-clickable"
                  onClick={() => onOpenTransaction(txn.id)}
                >
                  <div className="review-row">
                    <span>
                      <TransactionDateTime txn={txn} />
                    </span>
                    <span className={txn.txn_type === "debit" ? "amount-debit" : "amount-credit"}>
                      {txn.txn_type === "debit" ? "-" : "+"}₹{txn.amount}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
