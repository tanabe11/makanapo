import SwiftUI

struct DealDetailView: View {
    let deal: Deal
    @EnvironmentObject var loc: LocalizationManager
    @Environment(\.openURL) private var openURL

    var body: some View {
        List {
            Section {
                if let d = deal.discount { row(loc.t(.detailDiscount), d) }
                if let c = deal.conditions { row(loc.t(.detailConditions), c) }
                if let r = deal.redemption { row(loc.t(.detailRedemption), redemptionText(r)) }
                if let h = deal.hours { row(loc.t(.detailHours), h) }
                if let a = deal.address { row(loc.t(.detailAddress), a) }
                if let n = deal.neighborhood { row(loc.t(.detailNeighborhood), n) }
            }
            Section(loc.t(.freshnessSection)) {
                row(loc.t(.lastVerified), deal.lastVerified)
                row(loc.t(.statusRow), statusText)
            }
            Section {
                Button { openURL(deal.sourceURL) } label: {
                    Label(loc.t(.verifyAtSource), systemImage: "arrow.up.right.square")
                }
                if let maps = mapsURL {
                    Button { openURL(maps) } label: {
                        Label(loc.t(.openInMaps), systemImage: "map")
                    }
                }
            }
        }
        .navigationTitle(deal.name)
        .navigationBarTitleDisplayMode(.inline)
    }

    private func row(_ k: String, _ v: String) -> some View {
        HStack(alignment: .top) {
            Text(k).foregroundStyle(.secondary)
            Spacer()
            Text(v).multilineTextAlignment(.trailing)
        }
    }

    private func redemptionText(_ r: String) -> String {
        switch r {
        case "show_id": return loc.t(.redemptionShowID)
        case "code": return loc.t(.redemptionCode)
        case "online": return loc.t(.redemptionOnline)
        default: return r
        }
    }

    private var statusText: String {
        switch deal.status {
        case .active: return loc.t(.statusActive)
        case .unverified: return loc.t(.statusUnverified)
        case .expired: return loc.t(.statusExpired)
        case .unknown: return loc.t(.statusUnknown)
        }
    }

    private var mapsURL: URL? {
        if let lat = deal.lat, let lng = deal.lng {
            return URL(string: "http://maps.apple.com/?ll=\(lat),\(lng)&q=\(query)")
        }
        if let a = deal.address,
           let enc = a.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) {
            return URL(string: "http://maps.apple.com/?q=\(enc)")
        }
        return nil
    }

    private var query: String {
        deal.name.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "place"
    }
}
