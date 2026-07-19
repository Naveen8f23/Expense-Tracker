import { useEffect, useState } from "react";
import {
  correctTransaction,
  createCategory,
  dismissTransaction,
  getTransaction,
  listCategories,
  type Category,
  type PaymentMethod,
  type TransactionCorrection,
  type TransactionType,
  type TransactionWithSourceEmail,
} from "../api/client";

const NEW_CATEGORY_VALUE = "__new__";

interface Props {
  transactionId: number;
  onClose: () => void;
  onChanged: () => void;
}

export default function TransactionDetailPanel({ transactionId, onClose, onChanged }: Props) {
  const [txn, setTxn] = useState<TransactionWithSourceEmail | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showEmail, setShowEmail] = useState(false);

  const [amount, setAmount] = useState("");
  const [txnDate, setTxnDate] = useState("");
  const [payeeName, setPayeeName] = useState("");
  const [categorySelection, setCategorySelection] = useState<string>("");
  const [newCategoryName, setNewCategoryName] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("upi");
  const [txnType, setTxnType] = useState<TransactionType>("debit");

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([getTransaction(transactionId), listCategories()])
      .then(([fetchedTxn, categoryResponse]) => {
        setTxn(fetchedTxn);
        setCategories(categoryResponse.items);
        setAmount(fetchedTxn.amount);
        setTxnDate(fetchedTxn.txn_date);
        setPayeeName(fetchedTxn.payee.name);
        setCategorySelection(fetchedTxn.category_id ? String(fetchedTxn.category_id) : "");
        setPaymentMethod(fetchedTxn.payment_method);
        setTxnType(fetchedTxn.txn_type);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [transactionId]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      let categoryId: number | undefined;
      if (categorySelection === NEW_CATEGORY_VALUE) {
        if (!newCategoryName.trim()) {
          throw new Error("Enter a name for the new category.");
        }
        const created = await createCategory(newCategoryName.trim());
        categoryId = created.id;
      } else if (categorySelection) {
        categoryId = Number(categorySelection);
      }

      const correction: TransactionCorrection = {
        amount,
        txn_date: txnDate,
        payee_name: payeeName,
        payment_method: paymentMethod,
        txn_type: txnType,
        ...(categoryId !== undefined ? { category_id: categoryId } : {}),
      };
      await correctTransaction(transactionId, correction);
      onChanged();
      onClose();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDismiss() {
    setSaving(true);
    setError(null);
    try {
      await dismissTransaction(transactionId);
      onChanged();
      onClose();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="panel-overlay" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-header">
          <h3>Transaction #{transactionId}</h3>
          <button onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        {loading && <p>Loading…</p>}
        {error && <p className="error">{error}</p>}

        {txn && !loading && (
          <>
            <label>
              Amount
              <input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </label>
            <label>
              Date
              <input type="date" value={txnDate} onChange={(e) => setTxnDate(e.target.value)} />
            </label>
            <label>
              Payee
              <input type="text" value={payeeName} onChange={(e) => setPayeeName(e.target.value)} />
            </label>
            <label>
              Category
              <select value={categorySelection} onChange={(e) => setCategorySelection(e.target.value)}>
                <option value="">Uncategorized</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
                <option value={NEW_CATEGORY_VALUE}>+ New category…</option>
              </select>
            </label>
            {categorySelection === NEW_CATEGORY_VALUE && (
              <input
                type="text"
                placeholder="New category name"
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
              />
            )}
            <label>
              Payment method
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
              >
                <option value="upi">UPI</option>
                <option value="credit_card">Credit Card</option>
              </select>
            </label>
            <label>
              Type
              <select value={txnType} onChange={(e) => setTxnType(e.target.value as TransactionType)}>
                <option value="debit">Debit</option>
                <option value="credit">Credit</option>
              </select>
            </label>

            <p className="metadata">
              Reference: {txn.reference_number ?? "—"} · Instrument: {txn.instrument_last4 ?? "—"} ·
              Confidence: {txn.confidence_score}
            </p>

            <div className="panel-actions">
              <button onClick={handleSave} disabled={saving}>
                Save
              </button>
              <button onClick={handleDismiss} disabled={saving} className="button-danger">
                Not a real expense
              </button>
              <button onClick={() => setShowEmail((v) => !v)} disabled={saving}>
                {showEmail ? "Hide source email" : "View source email"}
              </button>
            </div>

            {showEmail && (
              // The cached email is untrusted external content (a real bank/UPI notification,
              // per ADR-0006 with phishing-hardening explicitly deferred but not eliminated as a
              // risk) -- rendered as plain escaped text, never via dangerouslySetInnerHTML, so a
              // malicious email can never execute script in the dashboard's origin.
              <pre className="source-email">{txn.source_email.content}</pre>
            )}
          </>
        )}
      </div>
    </div>
  );
}
