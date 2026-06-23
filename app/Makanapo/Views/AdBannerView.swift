import SwiftUI

/// Bottom ad banner. Currently a HOUSE ad (promotes makana.fm). The slot is
/// isolated here so a real ad network (e.g. AdMob `BannerView`) can replace the
/// body later without touching the rest of the layout.
struct AdBannerView: View {
    @EnvironmentObject var loc: LocalizationManager

    // House creative — swap for a real ad unit when available.
    private let url = URL(string: "https://makana.fm")!

    var body: some View {
        Link(destination: url) {
            HStack(spacing: 10) {
                Text(loc.t(.adLabel))
                    .font(.caption2).bold()
                    .padding(.horizontal, 5).padding(.vertical, 2)
                    .background(Color.secondary.opacity(0.2))
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                Image(systemName: "antenna.radiowaves.left.and.right")
                    .foregroundStyle(.indigo)
                Text(loc.t(.adHouseRadio))
                    .font(.subheadline)
                    .lineLimit(1)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity)
            .background(.ultraThinMaterial)
            .foregroundStyle(.primary)
        }
        .accessibilityLabel(loc.t(.adHouseRadio))
    }
}
