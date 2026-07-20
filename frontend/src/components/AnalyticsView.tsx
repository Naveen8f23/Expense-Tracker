import { useEffect, useState } from "react";
import {
  getCategoryBreakdown,
  getMonthlySummary,
  type CategoryBreakdownItem,
  type MonthlySummary,
} from "../api/client";

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function shiftMonth(month: string, delta: number): string {
  const [year, m] = month.split("-").map(Number);
  const date = new Date(year, m - 1 + delta, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(month: string): string {
  const [year, m] = month.split("-").map(Number);
  return new Date(year, m - 1, 1).toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
}

export default function AnalyticsView() {
  const [month, setMonth] = useState(currentMonth());
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdownItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([getMonthlySummary(month), getCategoryBreakdown(month)])
      .then(([summaryResponse, breakdownResponse]) => {
        setSummary(summaryResponse);
        setCategories(breakdownResponse.categories);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [month]);

  return (
    <div className="view">
      <h2>Analytics</h2>

      <div className="month-nav">
        <button onClick={() => setMonth((m) => shiftMonth(m, -1))}>← Previous</button>
        <span className="month-label">{monthLabel(month)}</span>
        <button onClick={() => setMonth((m) => shiftMonth(m, 1))}>Next →</button>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p>Loading…</p>}

      {!loading && !error && summary && (
        <>
          <div className="analytics-summary-cards">
            <div className="summary-card">
              <span className="metadata">Spent</span>
              <span className="amount-debit">₹{summary.total_debit}</span>
            </div>
            <div className="summary-card">
              <span className="metadata">Received</span>
              <span className="amount-credit">₹{summary.total_credit}</span>
            </div>
            <div className="summary-card">
              <span className="metadata">Net</span>
              <span
                className={
                  parseFloat(summary.total_credit) - parseFloat(summary.total_debit) > 0
                    ? "amount-credit"
                    : "amount-debit"
                }
              >
                ₹{summary.net}
              </span>
            </div>
            <div className="summary-card">
              <span className="metadata">Transactions</span>
              <span>{summary.transaction_count}</span>
            </div>
          </div>

          <h3>Spend by category</h3>
          {categories.length === 0 ? (
            <p>No spending recorded for this month.</p>
          ) : (
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Total</th>
                  <th>Transactions</th>
                </tr>
              </thead>
              <tbody>
                {categories.map((c) => (
                  <tr key={c.category_id ?? "uncategorized"}>
                    <td>{c.category_name}</td>
                    <td className="amount-debit">₹{c.total}</td>
                    <td>{c.transaction_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
