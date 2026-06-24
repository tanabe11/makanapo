import Foundation

enum LoadState: Equatable {
    case idle, loading, loaded, offline
    case error(String)
}

@MainActor
final class DealsStore: ObservableObject {
    @Published private(set) var deals: [Deal] = []
    @Published private(set) var state: LoadState = .idle

    private let loader: DealsLoading
    private let cacheURL: URL

    init(loader: DealsLoading,
         cacheURL: URL = FileManager.default
            .urls(for: .cachesDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("deals.json")) {
        self.loader = loader
        self.cacheURL = cacheURL
    }

    func refresh() async {
        if deals.isEmpty { state = .loading }
        do {
            let data = try await loader.load()
            let decoded = try JSONDecoder().decode([Deal].self, from: data)
            try? data.write(to: cacheURL, options: .atomic)
            deals = Self.visible(decoded)
            state = .loaded
        } catch {
            if let cached = try? Data(contentsOf: cacheURL),
               let decoded = try? JSONDecoder().decode([Deal].self, from: cached) {
                deals = Self.visible(decoded)
                state = .offline
            } else {
                state = .error(error.localizedDescription)
            }
        }
    }

    /// What the app surfaces in v1: verified (`active`) deals only.
    /// Trust (the `last_verified` differentiator) is the whole value prop, so
    /// `unverified` / `expired` records stay in the data feed but are not shown.
    static func visible(_ input: [Deal]) -> [Deal] {
        sorted(input.filter { $0.status == .active })
    }

    static func sorted(_ input: [Deal]) -> [Deal] {
        func rank(_ s: DealStatus) -> Int {
            switch s {
            case .active: return 0
            case .unverified: return 1
            case .expired: return 2
            case .unknown: return 3
            }
        }
        return input.sorted { a, b in
            if rank(a.status) != rank(b.status) { return rank(a.status) < rank(b.status) }
            let an = a.neighborhood ?? "~", bn = b.neighborhood ?? "~"
            if an != bn { return an < bn }
            return a.name < b.name
        }
    }
}
