import { useEffect, useState } from "react";
import {
  createCategory,
  createManualTransaction,
  listCategories,
  type Category,
  type PaymentMethod,
  type TransactionType,
} from "../api/client";

const NEW_CATEGORY_VALUE = "__new__";

function today(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
    now.getDate(),
  ).padStart(2, "0")}`;
}

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

// H2, COR-5: an escape hatch for the rare transaction with no corresponding email (e.g. cash) --
// a separate create-only panel rather than retrofitting TransactionDetailPanel (which is
// fetch-and-edit shaped around an existing transaction id). Reuses the same panel/field markup
// and inline "+ New category…" pattern for a consistent look.
export default function AddTransactionPanel({ onClose, onCreated }: Props) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [amount, setAmount] = useState("");
  const [txnDate, setTxnDate] = useState(today());
  const [payeeName, setPayeeName] = useState("");
  const [categorySelection, setCategorySelection] = useState<string>("");
  const [newCategoryName, setNewCategoryName] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("upi");
  const [txnType, setTxnType] = useState<TransactionType>("debit");

  useEffect(() => {
    setLoading(true);
    setError(null);
    listCategories()
      .then((response) => setCategories(response.items))
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      if (!amount || !payeeName.trim()) {
        throw new Error("Amount and payee are required.");
      }

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

      await createManualTransaction({
        amount,
        txn_date: txnDate,
        payee_name: payeeName.trim(),
        payment_method: paymentMethod,
        txn_type: txnType,
        ...(categoryId !== undefined ? { category_id: categoryId } : {}),
      });
      onCreated();
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
          <h3>Add transaction</h3>
          <button onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <p className="manual-banner">
          Manually added — no source email. Use this only for the rare transaction with nothing
          in your inbox (e.g. cash), not as a regular habit.
        </p>

        {error && <p className="error">{error}</p>}
        {loading && <p>Loading…</p>}

        {!loading && (
          <>
            <label>
              Amount
              <input
                type="number"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </label>
            <label>
              Date
              <input type="date" value={txnDate} onChange={(e) => setTxnDate(e.target.value)} />
            </label>
            <label>
              Payee
              <input
                type="text"
                value={payeeName}
                onChange={(e) => setPayeeName(e.target.value)}
              />
            </label>
            <label>
              Category
              <select
                value={categorySelection}
                onChange={(e) => setCategorySelection(e.target.value)}
              >
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

            <div className="panel-actions">
              <button onClick={handleSave} disabled={saving}>
                Add transaction
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
