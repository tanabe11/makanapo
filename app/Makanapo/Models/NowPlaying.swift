import Foundation

struct NowPlaying: Equatable {
    let stationName: String
    let title: String?
    let artist: String?
    let isLive: Bool
    let streamerName: String?

    var display: String {
        if isLive, let s = streamerName, !s.isEmpty { return "\(s)（ライブ）" }
        let t = (title?.isEmpty == false) ? title : nil
        let a = (artist?.isEmpty == false) ? artist : nil
        switch (t, a) {
        case let (.some(t), .some(a)): return "\(t) — \(a)"
        case let (.some(t), .none): return t
        default: return stationName
        }
    }
}

enum AzuraCastParser {
    private struct Payload: Decodable {
        struct Station: Decodable { let name: String }
        struct Song: Decodable { let title: String?; let artist: String? }
        struct NP: Decodable { let song: Song }
        struct Live: Decodable { let is_live: Bool; let streamer_name: String? }
        let station: Station
        let now_playing: NP
        let live: Live
    }

    static func parse(_ data: Data) throws -> NowPlaying {
        let p = try JSONDecoder().decode(Payload.self, from: data)
        return NowPlaying(stationName: p.station.name,
                          title: p.now_playing.song.title,
                          artist: p.now_playing.song.artist,
                          isLive: p.live.is_live,
                          streamerName: p.live.streamer_name)
    }
}
