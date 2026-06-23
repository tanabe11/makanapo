import SwiftUI
import MapKit

@available(iOS 17.0, *)
struct DealMapView: View {
    let deals: [Deal]
    @State private var selectedID: String?
    @State private var camera: MapCameraPosition = .region(
        MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: 21.295, longitude: -157.83),
            span: MKCoordinateSpan(latitudeDelta: 0.12, longitudeDelta: 0.12)))

    private var geocoded: [Deal] {
        deals.filter { $0.lat != nil && $0.lng != nil }
    }
    private var selected: Deal? {
        geocoded.first { $0.id == selectedID }
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            Map(position: $camera, selection: $selectedID) {
                ForEach(geocoded) { deal in
                    Marker(deal.name,
                           coordinate: CLLocationCoordinate2D(latitude: deal.lat!, longitude: deal.lng!))
                        .tint(deal.status == .active ? .green : .orange)
                        .tag(deal.id)
                }
            }
            .ignoresSafeArea(edges: .bottom)

            if let deal = selected {
                NavigationLink(value: deal.id) {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(deal.name).font(.headline)
                            if let d = deal.discount {
                                Text(d).font(.subheadline).foregroundStyle(.orange).lineLimit(1)
                            }
                        }
                        Spacer()
                        Image(systemName: "chevron.right").foregroundStyle(.secondary)
                    }
                    .padding()
                    .background(.regularMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding()
                }
                .buttonStyle(.plain)
            }
        }
    }
}
