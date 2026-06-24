import SwiftUI

struct DealRow: View {
    let deal: Deal
    @EnvironmentObject var loc: LocalizationManager

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(deal.name).font(.headline)
            highlight
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

    /// Headline line: a specific discount, else the happy-hour time, else a tag.
    @ViewBuilder private var highlight: some View {
        switch deal.highlight {
        case .discount(let d):
            Text(d).font(.subheadline).foregroundStyle(.orange)
        case .time(let t):
            Label(t, systemImage: "clock").font(.subheadline).foregroundStyle(.orange)
        case .happyHourTag:
            Text(loc.t(.pickerHappyHour)).font(.subheadline).foregroundStyle(.orange)
        case .none:
            EmptyView()
        }
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
