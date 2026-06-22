import Foundation
import AVFoundation
import MediaPlayer

@MainActor
final class RadioPlayer: ObservableObject {
    @Published private(set) var isPlaying = false
    @Published private(set) var nowPlaying: NowPlaying?

    private let player = AVPlayer(url: Config.radioStreamURL)
    private let metadata = AzuraCastClient(url: Config.nowPlayingURL)
    private var pollTask: Task<Void, Never>?

    init() {
        configureSession()
        configureRemoteCommands()
    }

    func toggle() {
        if isPlaying {
            player.pause()
            isPlaying = false
        } else {
            try? AVAudioSession.sharedInstance().setActive(true)
            player.play()
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
