// Thin API client — the ONLY place in the frontend that knows how to reach the backend.
// UI components must go through functions exported here, never call fetch() directly,
// so the backend's API Layer stays the sole door into the system (docs/ARCHITECTURE.md §3).

// Dev (`npm run dev`, .env): the Vite dev server and backend are different origins/ports, so
// this must be an absolute URL. Production (`npm run build`, .env.production, ADR-0020): the
// backend serves this build itself (same origin), so that file sets this to "" -- relative
// requests -- rather than hardcoding a host/port that depends on how this build gets deployed
// (e.g. via the VM's SSH tunnel, which can use any local port).
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface HealthStatus {
  status: string;
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch(`${BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      detail = await response.text();
    }
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

export type PaymentMethod = "upi" | "credit_card";
export type TransactionType = "debit" | "credit";
export type ReviewStatus = "auto_accepted" | "needs_review" | "user_confirmed";
export type EmailMessageStatus = "unprocessed" | "matched" | "needs_review" | "ignored";

export interface Payee {
  id: number;
  name: string;
  identifier: string | null;
}

export interface Transaction {
  id: number;
  amount: string;
  currency: string;
  txn_date: string;
  txn_time: string | null;
  payee: Payee;
  instrument_last4: string | null;
  category_id: number | null;
  category_name: string | null;
  payment_method: PaymentMethod;
  txn_type: TransactionType;
  reference_number: string | null;
  confidence_score: number;
  review_status: ReviewStatus;
  email_message_id: number;
  dismissed: boolean;
  created_at: string;
}

export interface EmailMessage {
  id: number;
  message_id: string;
  received_at: string;
  status: EmailMessageStatus;
  classified_pattern_id: string | null;
  content: string;
}

export interface TransactionWithSourceEmail extends Transaction {
  source_email: EmailMessage;
}

export interface Category {
  id: number;
  name: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  limit: number;
  offset: number;
}

export interface TransactionFilters {
  payee?: string;
  category_id?: number;
  date_from?: string;
  date_to?: string;
  amount_min?: string;
  amount_max?: string;
  payment_method?: PaymentMethod;
  txn_type?: TransactionType;
  q?: string;
  limit?: number;
  offset?: number;
}

export interface TransactionCorrection {
  amount?: string;
  txn_date?: string;
  payee_name?: string;
  category_id?: number;
  payment_method?: PaymentMethod;
  txn_type?: TransactionType;
}

export interface NeedsReviewQueue {
  unmatched_emails: EmailMessage[];
  low_confidence_transactions: Transaction[];
}

export interface SyncStatus {
  connected: boolean;
  email_address: string;
  synced: boolean;
  last_sync_started_at?: string | null;
  last_sync_at?: string | null;
  last_error?: string | null;
  last_scanned?: number | null;
  last_matched?: number | null;
  last_skipped?: number | null;
  last_failed?: number | null;
}

export async function listTransactions(
  filters: TransactionFilters,
): Promise<TransactionListResponse> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return request(`/transactions${query ? `?${query}` : ""}`);
}

export async function getRecentTransactions(sinceId: number): Promise<{ items: Transaction[] }> {
  return request(`/transactions/recent?since_id=${sinceId}`);
}

export async function getTransaction(id: number): Promise<TransactionWithSourceEmail> {
  return request(`/transactions/${id}`);
}

export async function correctTransaction(
  id: number,
  correction: TransactionCorrection,
): Promise<Transaction> {
  return request(`/transactions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(correction),
  });
}

export async function dismissTransaction(id: number): Promise<Transaction> {
  return request(`/transactions/${id}/dismiss`, { method: "POST" });
}

export async function getNeedsReview(): Promise<NeedsReviewQueue> {
  return request(`/needs-review`);
}

export async function ignoreNeedsReviewEmail(emailId: number): Promise<EmailMessage> {
  return request(`/needs-review/emails/${emailId}/ignore`, { method: "POST" });
}

export async function listCategories(): Promise<{ items: Category[] }> {
  return request(`/categories`);
}

export async function createCategory(name: string): Promise<Category> {
  return request(`/categories`, { method: "POST", body: JSON.stringify({ name }) });
}

export async function getSyncStatus(): Promise<SyncStatus> {
  return request(`/sync/status`);
}
