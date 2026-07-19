import Foundation

// Request bodies for the write endpoints (BACKLOG.md I2). `TransactionCorrectionRequest` uses a
// hand-written `encode(to:)` with `encodeIfPresent` so that a field the caller didn't set is
// **omitted from the JSON entirely**, not sent as an explicit `null` — the backend's PATCH
// semantics treat an omitted field as "leave unchanged" (see `correct_transaction.py`); sending
// `null` is a different, unintended instruction.
struct TransactionCorrectionRequest: Encodable {
    var amount: String?
    var txnDate: String?
    var payeeName: String?
    var categoryId: Int?
    var paymentMethod: String?
    var txnType: String?

    private enum CodingKeys: String, CodingKey {
        case amount, txnDate, payeeName, categoryId, paymentMethod, txnType
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(amount, forKey: .amount)
        try container.encodeIfPresent(txnDate, forKey: .txnDate)
        try container.encodeIfPresent(payeeName, forKey: .payeeName)
        try container.encodeIfPresent(categoryId, forKey: .categoryId)
        try container.encodeIfPresent(paymentMethod, forKey: .paymentMethod)
        try container.encodeIfPresent(txnType, forKey: .txnType)
    }
}

struct ManualTransactionRequest: Encodable {
    let amount: String
    let txnDate: String
    let payeeName: String
    let paymentMethod: String
    let txnType: String
    var categoryId: Int?
}

struct CategoryCreateRequest: Encodable {
    let name: String
}

struct CategoryRenameRequest: Encodable {
    let name: String
}

/// Query filters for `GET /transactions` (E1). Building this as a plain struct — rather than a
/// long parameter list — keeps `APIClient.listTransactions` from needing 10 positional arguments.
struct TransactionFilters {
    var payee: String?
    var categoryId: Int?
    var dateFrom: String?
    var dateTo: String?
    var amountMin: String?
    var amountMax: String?
    var paymentMethod: String?
    var txnType: String?
    var q: String?
    var limit: Int = 50
    var offset: Int = 0

    init() {}
}
