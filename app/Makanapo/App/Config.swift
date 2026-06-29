import Foundation

enum Config {
    /// Published deals (jsDelivr CDN, public repo). No bundled fallback.
    static let dealsURL = URL(string: "https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json")!

    // makana.fm radio (AzuraCast @ radio.makana.fm, station shortcode "makana.fm")
    /// Live HLS stream (adaptive AAC). AVPlayer is built for HLS and handles it far more
    /// reliably than a raw Icecast MP3 mount, which stalls/doesn't recover well on iOS.
    /// (MP3 fallback mount: https://radio.makana.fm/listen/makana.fm/radio.mp3)
    static let radioStreamURL = URL(string: "https://radio.makana.fm/hls/makana.fm/live.m3u8")!
    /// AzuraCast now-playing JSON.
    static let nowPlayingURL = URL(string: "https://radio.makana.fm/api/nowplaying/makana.fm")!
}
