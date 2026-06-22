import SwiftUI

/// Tracks vertical scroll offset using the native iOS 18+ API where available.
/// On iOS 16–17 it is a no-op (the radio stays in hero form — graceful fallback).
private struct TrackScroll: ViewModifier {
    let onChange: (CGFloat) -> Void
    func body(content: Content) -> some View {
        if #available(iOS 18.0, *) {
            content.onScrollGeometryChange(for: CGFloat.self) { geo in
                geo.contentOffset.y
            } action: { _, newValue in
                onChange(newValue)
            }
        } else {
            content
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var dealsStore: DealsStore
    @EnvironmentObject var radio: RadioPlayer
    @Environment(\.scenePhase) private var scenePhase
    @State private var scrolledY: CGFloat = 0
    @State private var filter: DealFilter = .all

    private var collapsed: Bool { scrolledY > 60 }
    private var shownDeals: [Deal] { dealsStore.deals.filter { filter.matches($0) } }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Radio bar is OUTSIDE the scroll -> always pinned at top.
                RadioHeader(player: radio, collapsed: collapsed)
                    .background(.ultraThinMaterial)
                    .animation(.easeInOut(duration: 0.2), value: collapsed)
                Divider()

                Picker("絞り込み", selection: $filter) {
                    ForEach(DealFilter.allCases) { f in
                        Text(f.label).tag(f)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.vertical, 6)
                Divider()

                ScrollView {
                    dealsSection
                }
                .modifier(TrackScroll { scrolledY = $0 })
            }
            .navigationTitle("makanapo")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: String.self) { id in
                if let deal = dealsStore.deals.first(where: { $0.id == id }) {
                    DealDetailView(deal: deal)
                }
            }
        }
        .task { await dealsStore.refresh() }
        .onChange(of: scenePhase) { phase in
            if phase == .active { Task { await dealsStore.refresh() } }
        }
    }

    @ViewBuilder private var dealsSection: some View {
        if !dealsStore.deals.isEmpty {
            if shownDeals.isEmpty {
                Text("この絞り込みに該当する割引はありません")
                    .font(.subheadline).foregroundStyle(.secondary).padding(40)
            } else {
                LazyVStack(spacing: 0) {
                    ForEach(shownDeals) { deal in
                        NavigationLink(value: deal.id) {
                            DealRow(deal: deal).padding(.horizontal)
                        }
                        .buttonStyle(.plain)
                        Divider()
                    }
                }
            }
        } else if case .error(let msg) = dealsStore.state {
            VStack(spacing: 12) {
                Image(systemName: "wifi.slash").font(.largeTitle).foregroundStyle(.secondary)
                Text("割引を読み込めませんでした").font(.headline)
                Text(msg).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
                Button("再試行") { Task { await dealsStore.refresh() } }
                    .buttonStyle(.borderedProminent)
            }
            .padding(40)
        } else {
            ProgressView("読み込み中…").padding(40)
        }
    }
}
