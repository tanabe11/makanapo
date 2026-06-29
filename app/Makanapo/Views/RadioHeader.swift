import SwiftUI
import Foundation

struct RadioHeader: View {
    @ObservedObject var player: RadioPlayer
    @EnvironmentObject var loc: LocalizationManager
    let collapsed: Bool
    /// Shared identity so the play button glides + resizes between hero/slim
    /// instead of snapping between two separate view trees.
    @Namespace private var ns

    var body: some View {
        ZStack {
            if collapsed { slim } else { hero }
        }
    }

    private var slim: some View {
        HStack(spacing: 10) {
            playButton(size: 30)
            VStack(alignment: .leading, spacing: 0) {
                Text("makana.fm").font(.caption).bold()
                MarqueeText(text: player.nowPlaying?.display ?? "♪", playing: player.isPlaying)
                    .font(.caption2).foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal, 14).padding(.vertical, 8)
        .background(.ultraThinMaterial)
    }

    private var hero: some View {
        VStack(spacing: 8) {
            Text("RADIO").font(.caption).tracking(2).foregroundStyle(.secondary)
            playButton(size: 96)
            MarqueeText(text: player.nowPlaying?.display ?? "♪ \(loc.t(.tapToListen))",
                        playing: player.isPlaying, alignment: .center)
                .font(.subheadline).foregroundStyle(.secondary)
                .padding(.horizontal)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 20)
    }

    private func playButton(size: CGFloat) -> some View {
        Button { player.toggle() } label: {
            // Gentle "alive" pulse while playing. TimelineView derives the scale
            // from absolute time, so it keeps pulsing across the hero⇄slim switch
            // (where the button is a different view instance).
            TimelineView(.animation(minimumInterval: 1.0 / 30.0, paused: !player.isPlaying)) { ctx in
                let t = ctx.date.timeIntervalSinceReferenceDate
                let scale = player.isPlaying ? 1.0 + 0.03 * (1 + sin(t * 2 * .pi / 1.4)) : 1.0
                Image(systemName: player.isPlaying ? "pause.circle.fill" : "play.circle.fill")
                    .resizable().frame(width: size, height: size)
                    .foregroundStyle(.orange)
                    .scaleEffect(scale)
            }
        }
        .matchedGeometryEffect(id: "playButton", in: ns)
    }
}
