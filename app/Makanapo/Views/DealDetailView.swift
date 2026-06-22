import SwiftUI

struct DealDetailView: View {
    let deal: Deal
    @Environment(\.openURL) private var openURL

    var body: some View {
        List {
            Section {
                if let d = deal.discount { row("割引", d) }
                if let c = deal.conditions { row("条件", c) }
                if let r = deal.redemption { row("利用方法", r) }
                if let h = deal.hours { row("時間", h) }
                if let a = deal.address { row("住所", a) }
                if let n = deal.neighborhood { row("地区", n) }
            }
            Section("鮮度") {
                row("最終確認日", deal.lastVerified)
                row("ステータス", statusText)
            }
            Section {
                Button { openURL(deal.sourceURL) } label: {
                    Label("公式で確認", systemImage: "arrow.up.right.square")
                }
                if let maps = mapsURL {
                    Button { openURL(maps) } label: {
                        Label("マップで開く", systemImage: "map")
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

    private var statusText: String {
        switch deal.status {
        case .active: return "確認済み"
        case .unverified: return "未確認"
        case .expired: return "期限切れ"
        case .unknown: return "不明"
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
