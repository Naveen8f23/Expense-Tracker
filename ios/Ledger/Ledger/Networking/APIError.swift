import Foundation

/// Every failure mode `APIClient` can produce. Callers must handle this explicitly — there is no
/// silently-swallowed failure path (Constitution principle 21): a network failure, a non-2xx
/// response, and a decode failure are all distinct, inspectable cases.
enum APIError: Error, Equatable {
    /// The request never got a response at all — host unreachable, no network, DNS failure, etc.
    /// This is the case I3's reachability check surfaces as "backend unreachable."
    case unreachable(String)
    /// A response came back with a non-2xx status. `detail` is the backend's plain-string
    /// `{"detail": "..."}` message where one exists.
    case httpError(status: Int, detail: String)
    /// The specific `DELETE /categories/{id}` 409 shape (E6) — nested, not a plain string,
    /// carrying the count of transactions currently using the category.
    case categoryInUse(message: String, transactionCount: Int)
    /// The response was 2xx but didn't decode into the expected shape.
    case decodingFailed(String)
}

extension APIError: LocalizedError {
    var errorDescription: String? {
        switch self {
        case .unreachable(let reason):
            return "Couldn't reach the backend: \(reason)"
        case .httpError(let status, let detail):
            return "\(detail) (HTTP \(status))"
        case .categoryInUse(let message, _):
            return message
        case .decodingFailed(let reason):
            return "Unexpected response from the backend: \(reason)"
        }
    }
}
