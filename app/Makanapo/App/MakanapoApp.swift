import SwiftUI

@main
struct MakanapoApp: App {
    @StateObject private var dealsStore = DealsStore(
        loader: URLSessionDealsLoader(url: Config.dealsURL)
    )

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(dealsStore)
        }
    }
}
