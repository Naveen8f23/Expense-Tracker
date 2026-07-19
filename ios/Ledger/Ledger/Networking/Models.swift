import Foundation

// Wire models for the backend's REST/JSON API (BACKLOG.md I2). Field names are camelCase here;
// `APIClient` configures its JSONDecoder/JSONEncoder with snake_case conversion, so these map
// directly onto the backend's actual field names (see `backend/app/presentation/serializers.py`)
// without hand-written CodingKeys.
//
// Money fields (amount, totalDebit, totalCredit, net, total) are `String`, not `Decimal` or
// `Double` — the backend serializes `Decimal` as `str(Decimal)` to avoid float rounding, and
// Swift's `Decimal` has no built-in string-based JSON decoding strategy. Parsing to `Decimal`
// for display/arithmetic is a later story's (J/L) concern, not this client's.
//
// Similarly, date/time/datetime fields are left as `String` (not `Date`) — the backend emits a
// mix of date-only, time-only, and microsecond-precision ISO datetimes, and formatting them is a
// presentation concern for later stories, not this networking layer's.

struct Payee: Codable, Equatable {
    let id: Int
    let name: String
    let identifier: String?
}

struct Transaction: Codable, Equatable, Identifiable {
    let id: Int
    let amount: String
    let currency: String
    let txnDate: String
    let txnTime: String?
    let emailReceivedAt: String?
    let payee: Payee
    let instrumentLast4: String?
    let categoryId: Int?
    let categoryName: String?
    let paymentMethod: String
    let txnType: String
    let referenceNumber: String?
    let confidenceScore: Double
    let reviewStatus: String
    let emailMessageId: Int?
    let dismissed: Bool
    let createdAt: String
    /// Only present on the `GET /transactions/{id}` response; nil everywhere else (including when
    /// the transaction has no source email — a manually-added transaction, H2/ADR-0022).
    let sourceEmail: EmailMessage?
}

struct EmailMessage: Codable, Equatable, Identifiable {
    let id: Int
    let messageId: String
    let receivedAt: String
    let status: String
    let classifiedPatternId: String?
    let content: String
}

struct TransactionListResponse: Codable {
    let items: [Transaction]
    let total: Int
    let limit: Int
    let offset: Int
}

struct RecentTransactionsResponse: Codable {
    let items: [Transaction]
}

struct NeedsReviewResponse: Codable {
    let unmatchedEmails: [EmailMessage]
    let lowConfidenceTransactions: [Transaction]
}

struct Category: Codable, Equatable, Identifiable {
    let id: Int
    let name: String
}

struct CategoryListResponse: Codable {
    let items: [Category]
}

struct SyncStatus: Codable, Equatable {
    let connected: Bool
    let emailAddress: String
    let synced: Bool
    // Absent entirely (not null) in the JSON until the first sync has run — see APIClient's
    // decoder, which must tolerate missing keys here, not just null ones.
    let lastSyncStartedAt: String?
    let lastSyncAt: String?
    let lastError: String?
    let lastScanned: Int?
    let lastMatched: Int?
    let lastSkipped: Int?
    let lastFailed: Int?
}

struct MonthlyAnalytics: Codable, Equatable {
    let month: String
    let totalDebit: String
    let totalCredit: String
    let net: String
    let transactionCount: Int
}

struct CategoryBreakdownItem: Codable, Equatable, Identifiable {
    let categoryId: Int?
    let categoryName: String
    let total: String
    let transactionCount: Int

    var id: Int { categoryId ?? -1 }
}

struct CategoryBreakdownResponse: Codable {
    let month: String
    let categories: [CategoryBreakdownItem]
}

struct PayeeHistoryResponse: Codable {
    let payeeName: String
    let totalDebit: String
    let totalCredit: String
    let net: String
    let transactionCount: Int
    let limit: Int
    let offset: Int
    let items: [Transaction]
}
