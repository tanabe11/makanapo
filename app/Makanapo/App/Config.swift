import Foundation

enum Config {
    /// Published deals (jsDelivr CDN, public repo). No bundled fallback.
    static let dealsURL = URL(string: "https://cdn.jsdelivr.net/gh/tanabe11/makanapo@main/data/deals.json")!

    // --- OWNER INPUT: replace with the real makana.fm radio3 (AzuraCast) values ---
    /// Direct audio stream (e.g. https://<host>/listen/<shortcode>/radio.mp3)
    static let radioStreamURL = URL(string: "https://REPLACE_ME/listen/radio3/radio.mp3")!
    /// AzuraCast now-playing JSON (e.g. https://<host>/api/nowplaying/<shortcode>)
    static let nowPlayingURL = URL(string: "https://REPLACE_ME/api/nowplaying/radio3")!
}
