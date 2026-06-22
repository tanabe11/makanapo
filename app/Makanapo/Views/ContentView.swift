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

    private var collapsed: Bool { scrolledY > 60 }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Radio bar is OUTSIDE the scroll -> always pinned at top.
                // Morphs hero <-> slim based on how far the list is scrolled.
                RadioHeader(player: radio, collapsed: collapsed)
                    .background(.ultraThinMaterial)
                    .animation(.easeInOut(duration: 0.2), value: collapsed)
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
            LazyVStack(spacing: 0) {
                ForEach(dealsStore.deals) { deal in
                    NavigationLink(value: deal.id) {
                        DealRow(deal: deal).padding(.horizontal)
                    }
                    .buttonStyle(.plain)
                    Divider()
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
