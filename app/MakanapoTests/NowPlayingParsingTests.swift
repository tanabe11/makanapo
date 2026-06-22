import XCTest
@testable import Makanapo

final class NowPlayingParsingTests: XCTestCase {
    func test_parsesSongAndStation() throws {
        let json = """
        {"station":{"name":"makana.fm"},
         "now_playing":{"song":{"title":"Aloha","artist":"Kuana"}},
         "live":{"is_live":false,"streamer_name":""}}
        """.data(using: .utf8)!
        let np = try AzuraCastParser.parse(json)
        XCTAssertEqual(np.stationName, "makana.fm")
        XCTAssertEqual(np.title, "Aloha")
        XCTAssertEqual(np.artist, "Kuana")
        XCTAssertFalse(np.isLive)
        XCTAssertEqual(np.display, "Aloha — Kuana")
    }

    func test_liveStreamerAndMissingSong() throws {
        let json = """
        {"station":{"name":"makana.fm"},
         "now_playing":{"song":{"title":"","artist":""}},
         "live":{"is_live":true,"streamer_name":"DJ Pō"}}
        """.data(using: .utf8)!
        let np = try AzuraCastParser.parse(json)
        XCTAssertTrue(np.isLive)
        XCTAssertEqual(np.display, "DJ Pō（ライブ）")
    }
}
