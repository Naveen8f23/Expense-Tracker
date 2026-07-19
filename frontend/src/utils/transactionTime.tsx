import type { Transaction } from "../api/client";

function formatTime12Hour(hours: number, minutes: number): string {
  const period = hours >= 12 ? "PM" : "AM";
  const hour12 = hours % 12 === 0 ? 12 : hours % 12;
  return `${hour12}:${String(minutes).padStart(2, "0")} ${period}`;
}

// Renders a transaction's date plus a time. Not every source template provides a real
// transaction time -- the UPI templates are date-only (REQUIREMENTS.md Appendix A) -- so those
// rows fall back to the source email's received time instead, visually marked (a "~" prefix plus
// a tooltip) since that's when the email arrived, not necessarily the bank's own transaction
// time. Shared by TransactionsView and PayeeHistoryPanel so the two views can't drift apart.
export function TransactionDateTime({ txn }: { txn: Transaction }) {
  if (txn.txn_time) {
    const [hours, minutes] = txn.txn_time.split(":").map(Number);
    return (
      <>
        {txn.txn_date} {formatTime12Hour(hours, minutes)}
      </>
    );
  }

  // email_received_at is stored/serialized as a naive UTC timestamp (no offset suffix) -- append
  // "Z" so the browser parses it as UTC and converts to the viewer's local time, rather than
  // silently misinterpreting it as already being in the browser's own timezone.
  const received = new Date(`${txn.email_received_at}Z`);
  const approxTime = formatTime12Hour(received.getHours(), received.getMinutes());
  return (
    <>
      {txn.txn_date}{" "}
      <span
        className="time-approx"
        title="Approximate — based on when the source email arrived, not extracted from the transaction itself"
      >
        ~{approxTime}
      </span>
    </>
  );
}
