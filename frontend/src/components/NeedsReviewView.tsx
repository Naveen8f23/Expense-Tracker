import { useEffect, useState } from "react";
import { getNeedsReview, ignoreNeedsReviewEmail, type NeedsReviewQueue } from "../api/client";
import TransactionDetailPanel from "./TransactionDetailPanel";

export default function NeedsReviewView() {
  const [queue, setQueue] = useState<NeedsReviewQueue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [expandedEmailId, setExpandedEmailId] = useState<number | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    getNeedsReview()
      .then(setQueue)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleIgnore(emailId: number) {
    try {
      await ignoreNeedsReviewEmail(emailId);
      load();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="view">
      <h2>Needs Review</h2>
      {error && <p className="error">{error}</p>}
      {loading && <p>Loading…</p>}

      {queue && !loading && (
        <>
          <h3>Unrecognized emails ({queue.unmatched_emails.length})</h3>
          {queue.unmatched_emails.length === 0 && <p>Nothing here — good.</p>}
          <ul className="review-list">
            {queue.unmatched_emails.map((email) => (
              <li key={email.id}>
                <div className="review-row">
                  <span>
                    {email.message_id} · received {email.received_at}
                  </span>
                  <span className="review-actions">
                    <button onClick={() => setExpandedEmailId((id) => (id === email.id ? null : email.id))}>
                      {expandedEmailId === email.id ? "Hide" : "View"}
                    </button>
                    <button className="button-danger" onClick={() => handleIgnore(email.id)}>
                      Ignore
                    </button>
                  </span>
                </div>
                {expandedEmailId === email.id && <pre className="source-email">{email.content}</pre>}
              </li>
            ))}
          </ul>

          <h3>Low-confidence transactions ({queue.low_confidence_transactions.length})</h3>
          {queue.low_confidence_transactions.length === 0 && <p>Nothing here — good.</p>}
          <ul className="review-list">
            {queue.low_confidence_transactions.map((txn) => (
              <li key={txn.id}>
                <div className="review-row">
                  <span>
                    {txn.txn_date} · {txn.payee.name} · ₹{txn.amount} · confidence{" "}
                    {txn.confidence_score}
                  </span>
                  <button onClick={() => setSelectedId(txn.id)}>Review</button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {selectedId !== null && (
        <TransactionDetailPanel
          transactionId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={load}
        />
      )}
    </div>
  );
}
