import Foundation

protocol DealsLoading {
    func load() async throws -> Data
}

struct URLSessionDealsLoader: DealsLoading {
    let url: URL
    var session: URLSession = .shared

    func load() async throws -> Data {
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return data
    }
}
