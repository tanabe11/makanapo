import Foundation
import AVFoundation
import MediaPlayer

/// Drives the actual audio output. Abstracted so the player's lifecycle logic
/// is testable without AVFoundation.
protocol RadioEngine: AnyObject {
    /// Start playback from a FRESH stream item — always the live edge, never a
    /// resumed/stale buffer. Safe to call repeatedly.
    func play(url: URL)
    /// Stop and release the buffered item (so the next play starts clean).
    func stop()
}

/// AVPlayer-backed engine. A live Icecast/HLS stream is non-seekable, so we never
/// pause-and-resume the same item (that replays the stale buffer). Instead every
/// play installs a brand-new AVPlayerItem → live edge with no leftover buffer.
final class AVRadioEngine: RadioEngine {
    private let player: AVPlayer = {
        let p = AVPlayer()
        p.automaticallyWaitsToMinimizeStalling = true // smoother recovery on flaky networks
        return p
    }()

    func play(url: URL) {
        player.replaceCurrentItem(with: AVPlayerItem(url: url))
        player.play()
    }

    func stop() {
        player.pause()
        player.replaceCurrentItem(with: nil) // drop the buffer
    }
}

@MainActor
final class RadioPlayer: ObservableObject {
    @Published private(set) var isPlaying = false
    @Published private(set) var nowPlaying: NowPlaying?

    private let streamURL: URL
    private let engine: RadioEngine
    private let metadata: NowPlayingProviding
    private var pollTask: Task<Void, Never>?

    init(streamURL: URL = Config.radioStreamURL,
         engine: RadioEngine = AVRadioEngine(),
         metadata: NowPlayingProviding = AzuraCastClient(url: Config.nowPlayingURL)) {
        self.streamURL = streamURL
        self.engine = engine
        self.metadata = metadata
        configureSession()
        configureRemoteCommands()
    }

    func toggle() {
        if isPlaying {
            engine.stop()
            isPlaying = false
        } else {
            try? AVAudioSession.sharedInstance().setActive(true)
            engine.play(url: streamURL) // fresh stream → live edge, no stale buffer
            isPlaying = true
            startMetadata()
        }
        updateNowPlayingInfo()
    }

    func startMetadata() {
        pollTask?.cancel()
        pollTask = Task { [weak self] in
            while !Task.isCancelled {
                if let np = try? await self?.metadata.fetch() {
                    self?.nowPlaying = np
                    self?.updateNowPlayingInfo()
                }
                try? await Task.sleep(nanoseconds: 25_000_000_000) // 25s
            }
        }
    }

    private func configureSession() {
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .default)
    }

    private func configureRemoteCommands() {
        let center = MPRemoteCommandCenter.shared()
        center.playCommand.addTarget { [weak self] _ in self?.resume(); return .success }
        center.pauseCommand.addTarget { [weak self] _ in self?.pause(); return .success }
        center.togglePlayPauseCommand.addTarget { [weak self] _ in self?.toggle(); return .success }
    }

    private func resume() { if !isPlaying { toggle() } }
    private func pause() { if isPlaying { toggle() } }

    private func updateNowPlayingInfo() {
        let info: [String: Any] = [
            MPMediaItemPropertyTitle: nowPlaying?.display ?? "makana.fm",
            MPMediaItemPropertyArtist: nowPlaying?.stationName ?? "makana.fm",
            MPNowPlayingInfoPropertyIsLiveStream: true,
            MPNowPlayingInfoPropertyPlaybackRate: isPlaying ? 1.0 : 0.0
        ]
        MPNowPlayingInfoCenter.default().nowPlayingInfo = info
    }
}
