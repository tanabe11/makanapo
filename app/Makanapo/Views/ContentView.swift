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
    @EnvironmentObject var loc: LocalizationManager
    @Environment(\.scenePhase) private var scenePhase
    @State private var scrolledY: CGFloat = 0
    @State private var filter: DealFilter = .all
    @State private var showMap = false

    private var collapsed: Bool { !showMap && scrolledY > 60 }
    private var shownDeals: [Deal] { dealsStore.deals.filter { filter.matches($0) } }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                RadioHeader(player: radio, collapsed: collapsed)
                    .background(.ultraThinMaterial)
                    .animation(.easeInOut(duration: 0.2), value: collapsed)
                Divider()

                Picker("filter", selection: $filter) {
                    ForEach(DealFilter.allCases) { f in
                        Text(filterLabel(f)).tag(f)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.vertical, 6)
                Divider()

                if #available(iOS 17.0, *), showMap {
                    DealMapView(deals: shownDeals)
                } else {
                    ScrollView {
                        dealsSection
                    }
                    .modifier(TrackScroll { scrolledY = $0 })
                }
            }
            .navigationTitle("makanapo")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if #available(iOS 17.0, *) {
                        Button { showMap.toggle() } label: {
                            Image(systemName: showMap ? "list.bullet" : "map")
                        }
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button { loc.toggle() } label: {
                        Label(loc.lang == .ja ? "EN" : "日本語", systemImage: "globe")
                            .font(.subheadline)
                    }
                }
            }
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

    private func filterLabel(_ f: DealFilter) -> String {
        switch f {
        case .all: return loc.t(.pickerAll)
        case .happyHour: return loc.t(.pickerHappyHour)
        case .kamaaina: return loc.t(.pickerKamaaina)
        }
    }

    @ViewBuilder private var dealsSection: some View {
        if !dealsStore.deals.isEmpty {
            if shownDeals.isEmpty {
                Text(loc.t(.noResults))
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
        } else if case .error = dealsStore.state {
            VStack(spacing: 12) {
                Image(systemName: "wifi.slash").font(.largeTitle).foregroundStyle(.secondary)
                Text(loc.t(.loadFailed)).font(.headline)
                Button(loc.t(.retry)) { Task { await dealsStore.refresh() } }
                    .buttonStyle(.borderedProminent)
            }
            .padding(40)
        } else {
            ProgressView(loc.t(.loading)).padding(40)
        }
    }
}
