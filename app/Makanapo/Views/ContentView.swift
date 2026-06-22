import SwiftUI

struct ContentView: View {
    @EnvironmentObject var dealsStore: DealsStore

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("ホノルルの割引")
                .navigationBarTitleDisplayMode(.inline)
        }
        .task { await dealsStore.refresh() }
    }

    @ViewBuilder private var content: some View {
        if !dealsStore.deals.isEmpty {
            list
        } else if case .error(let msg) = dealsStore.state {
            retry(message: msg)
        } else {
            ProgressView("読み込み中…")
        }
    }

    private var list: some View {
        List(dealsStore.deals) { deal in
            NavigationLink(value: deal.id) {
                DealRow(deal: deal)
            }
        }
        .listStyle(.plain)
        .refreshable { await dealsStore.refresh() }
        .navigationDestination(for: String.self) { id in
            if let deal = dealsStore.deals.first(where: { $0.id == id }) {
                DealDetailView(deal: deal)
            }
        }
    }

    private func retry(message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "wifi.slash").font(.largeTitle).foregroundStyle(.secondary)
            Text("割引を読み込めませんでした").font(.headline)
            Text(message).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("再試行") { Task { await dealsStore.refresh() } }
                .buttonStyle(.borderedProminent)
        }
        .padding()
    }
}
