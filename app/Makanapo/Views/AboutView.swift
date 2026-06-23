import SwiftUI

struct AboutView: View {
    @EnvironmentObject var loc: LocalizationManager
    @Environment(\.dismiss) private var dismiss

    private var version: String {
        let info = Bundle.main.infoDictionary
        let v = info?["CFBundleShortVersionString"] as? String ?? "—"
        let b = info?["CFBundleVersion"] as? String ?? "—"
        return "\(v) (\(b))"
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(spacing: 8) {
                        Image("AppLogo")
                            .resizable()
                            .scaledToFit()
                            .frame(width: 84, height: 84)
                            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                        Text("makana.fm").font(.title2).bold()
                        Text(loc.t(.aboutTagline))
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                }

                Section { Text(loc.t(.aboutDescription)) }

                Section {
                    Text(loc.t(.aboutDataNote))
                    Text(loc.t(.aboutPrivacy))
                }

                Section {
                    Link(destination: URL(string: "https://makana.fm")!) {
                        Label(loc.t(.aboutVisitSite), systemImage: "antenna.radiowaves.left.and.right")
                    }
                    HStack {
                        Text(loc.t(.aboutVersion))
                        Spacer()
                        Text(version).foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle(loc.t(.menuAbout))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(loc.t(.aboutClose)) { dismiss() }
                }
            }
        }
    }
}
