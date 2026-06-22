import XCTest
@testable import Makanapo

private struct StubLoader: DealsLoading {
    let result: Result<Data, Error>
    func load() async throws -> Data { try result.get() }
}
private struct StubError: Error {}

final class DealsStoreTests: XCTestCase {
    private func tmpCacheURL() -> URL {
        FileManager.default.temporaryDirectory
            .appendingPathComponent("deals-\(UUID().uuidString).json")
    }
    private let sample = """
    [{"id":"a","name":"Active Two","category":"food","source_url":"https://e.com",
      "last_verified":"2026-06-22","status":"active","neighborhood":"Waikiki"},
     {"id":"b","name":"Active One","category":"food","source_url":"https://e.com",
      "last_verified":"2026-06-22","status":"active","neighborhood":"Kakaako"},
     {"id":"c","name":"Unverified","category":"food","source_url":"https://e.com",
      "last_verified":"2026-06-22","status":"unverified","neighborhood":"Kakaako"}]
    """.data(using: .utf8)!

    func test_refresh_loadsAndSorts_activeFirstThenNeighborhoodThenName() async throws {
        let store = await DealsStore(loader: StubLoader(result: .success(sample)),
                                     cacheURL: tmpCacheURL())
        await store.refresh()
        let deals = await store.deals
        XCTAssertEqual(deals.map(\.id), ["b", "a", "c"]) // active(Kakaako,Waikiki) then unverified
        let state = await store.state
        XCTAssertEqual(state, .loaded)
    }

    func test_refresh_writesCache_andOfflineReadsIt() async throws {
        let cache = tmpCacheURL()
        let ok = await DealsStore(loader: StubLoader(result: .success(sample)), cacheURL: cache)
        await ok.refresh()
        // New store with a failing loader but same cache → offline path
        let offline = await DealsStore(loader: StubLoader(result: .failure(StubError())), cacheURL: cache)
        await offline.refresh()
        let deals = await offline.deals
        XCTAssertEqual(deals.count, 3)
        let state = await offline.state
        XCTAssertEqual(state, .offline)
    }

    func test_refresh_noCacheNoNetwork_error() async throws {
        let store = await DealsStore(loader: StubLoader(result: .failure(StubError())),
                                     cacheURL: tmpCacheURL())
        await store.refresh()
        let deals = await store.deals
        XCTAssertTrue(deals.isEmpty)
        if case .error = await store.state {} else { XCTFail("expected .error") }
    }
}
