import Foundation

struct AzuraCastClient {
    let url: URL
    var session: URLSession = .shared

    func fetch() async throws -> NowPlaying {
        var req = URLRequest(url: url)
        req.cachePolicy = .reloadIgnoringLocalCacheData
        let (data, _) = try await session.data(for: req)
        return try AzuraCastParser.parse(data)
    }
}
