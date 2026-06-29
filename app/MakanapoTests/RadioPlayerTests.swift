import XCTest
@testable import Makanapo

/// Records how the player drives the audio engine, so we can assert the
/// live-radio lifecycle (every play starts a FRESH stream — no resumed buffer).
private final class FakeEngine: RadioEngine {
    private(set) var playedURLs: [URL] = []
    private(set) var stopCount = 0
    func play(url: URL) { playedURLs.append(url) }
    func stop() { stopCount += 1 }
}

/// No-op metadata so toggle() doesn't hit the network during tests.
private struct StubNowPlaying: NowPlayingProviding {
    func fetch() async throws -> NowPlaying { throw CancellationError() }
}

@MainActor
final class RadioPlayerTests: XCTestCase {
    private let url = URL(string: "https://example.com/live.m3u8")!

    private func makePlayer() -> (RadioPlayer, FakeEngine) {
        let engine = FakeEngine()
        let player = RadioPlayer(streamURL: url, engine: engine, metadata: StubNowPlaying())
        return (player, engine)
    }

    func test_play_startsFreshStreamFromURL() {
        let (player, engine) = makePlayer()
        player.toggle()
        XCTAssertTrue(player.isPlaying)
        XCTAssertEqual(engine.playedURLs, [url])
        XCTAssertEqual(engine.stopCount, 0)
    }

    func test_stop_releasesStream() {
        let (player, engine) = makePlayer()
        player.toggle() // play
        player.toggle() // stop
        XCTAssertFalse(player.isPlaying)
        XCTAssertEqual(engine.stopCount, 1)
    }

    func test_replay_recreatesStream_doesNotResumeBuffer() {
        let (player, engine) = makePlayer()
        player.toggle() // play
        player.toggle() // stop
        player.toggle() // play again
        // Two independent fresh starts (live edge each time), not a resumed buffer.
        XCTAssertEqual(engine.playedURLs, [url, url])
        XCTAssertEqual(engine.stopCount, 1)
        XCTAssertTrue(player.isPlaying)
    }
}
