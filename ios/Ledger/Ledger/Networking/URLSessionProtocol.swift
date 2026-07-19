import Foundation

/// Narrow seam over `URLSession` so tests can inject a stub instead of hitting the network —
/// the "unit-testable ... without a real backend running" acceptance criterion (BACKLOG.md I2).
protocol URLSessionProtocol {
    func data(for request: URLRequest) async throws -> (Data, URLResponse)
}

extension URLSession: URLSessionProtocol {}
