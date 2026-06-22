import SwiftUI

struct DealRow: View {
    let deal: Deal
    @EnvironmentObject var loc: LocalizationManager

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(deal.name).font(.headline)
            if let d = deal.discount {
                Text(d).font(.subheadline).foregroundStyle(.orange)
            }
            HStack(spacing: 8) {
                if let n = deal.neighborhood {
                    Text(n).font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                freshness
            }
        }
        .padding(.vertical, 4)
    }

    @ViewBuilder private var freshness: some View {
        switch deal.status {
        case .active:
            Label("\(loc.t(.verifiedPrefix)) \(deal.lastVerified)", systemImage: "checkmark.seal")
                .font(.caption2).foregroundStyle(.green)
        case .unverified:
            Label(loc.t(.unverified), systemImage: "questionmark.circle")
                .font(.caption2).foregroundStyle(.secondary)
        case .expired:
            Label(loc.t(.expired), systemImage: "xmark.circle")
                .font(.caption2).foregroundStyle(.red)
        case .unknown:
            EmptyView()
        }
    }
}
