import SwiftUI

struct RadioHeader: View {
    @ObservedObject var player: RadioPlayer
    let collapsed: Bool

    var body: some View {
        if collapsed { slim } else { hero }
    }

    private var slim: some View {
        HStack(spacing: 10) {
            playButton(size: 30)
            VStack(alignment: .leading, spacing: 0) {
                Text("makana.fm").font(.caption).bold()
                Text(player.nowPlaying?.display ?? "♪")
                    .font(.caption2).foregroundStyle(.secondary).lineLimit(1)
            }
            Spacer()
        }
        .padding(.horizontal, 14).padding(.vertical, 8)
        .background(.ultraThinMaterial)
    }

    private var hero: some View {
        VStack(spacing: 8) {
            Text("MAKANA.FM RADIO").font(.caption).tracking(2).foregroundStyle(.secondary)
            playButton(size: 96)
            Text(player.nowPlaying?.display ?? "♪ tap to listen")
                .font(.subheadline).foregroundStyle(.secondary).lineLimit(2)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 20)
    }

    private func playButton(size: CGFloat) -> some View {
        Button { player.toggle() } label: {
            Image(systemName: player.isPlaying ? "pause.circle.fill" : "play.circle.fill")
                .resizable().frame(width: size, height: size)
                .foregroundStyle(.orange)
        }
    }
}
