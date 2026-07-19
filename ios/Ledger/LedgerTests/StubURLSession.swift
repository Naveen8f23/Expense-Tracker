import Foundation
@testable import Ledger

/// Deterministic `URLSessionProtocol` stand-in — lets `APIClientTests` exercise the client against
/// recorded fixture JSON with no real backend running (BACKLOG.md I2's testability criterion).
final class StubURLSession: URLSessionProtocol {
    typealias Handler = (URLRequest) throws -> (Data, HTTPURLResponse)

    private let handler: Handler
    private(set) var lastRequest: URLRequest?

    init(handler: @escaping Handler) {
        self.handler = handler
    }

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        lastRequest = request
        let (data, response) = try handler(request)
        return (data, response)
    }

    /// Convenience for building a canned JSON response.
    static func json(_ string: String, status: Int = 200) -> (Data, HTTPURLResponse) {
        let data = Data(string.utf8)
        let response = HTTPURLResponse(
            url: URL(string: "https://turnny-vm.test")!,
            statusCode: status,
            httpVersion: nil,
            headerFields: ["Content-Type": "application/json"]
        )!
        return (data, response)
    }
}

struct StubTransportError: Error {}
