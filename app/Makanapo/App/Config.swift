import Foundation

enum Config {
    /// Published deals (jsDelivr CDN, public repo). No bundled fallback.
    static let dealsURL = URL(string: "https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json")!

    // makana.fm radio (AzuraCast @ radio.makana.fm, station shortcode "makana.fm")
    /// Live MP3 stream. (HLS alt: https://radio.makana.fm/hls/makana.fm/aac_hifi.m3u8)
    static let radioStreamURL = URL(string: "https://radio.makana.fm/listen/makana.fm/radio.mp3")!
    /// AzuraCast now-playing JSON.
    static let nowPlayingURL = URL(string: "https://radio.makana.fm/api/nowplaying/makana.fm")!
}
