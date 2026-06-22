import Foundation

enum DealStatus: String, Codable {
    case active, expired, unverified, unknown

    init(from decoder: Decoder) throws {
        let raw = try decoder.singleValueContainer().decode(String.self)
        self = DealStatus(rawValue: raw) ?? .unknown
    }
}

struct Deal: Identifiable, Codable, Equatable {
    let id: String
    let name: String
    let category: String
    let status: DealStatus
    let sourceURL: URL
    let lastVerified: String

    var subcategory: String?
    var discount: String?
    var conditions: String?
    var redemption: String?
    var code: String?
    var address: String?
    var lat: Double?
    var lng: Double?
    var neighborhood: String?
    var hours: String?
    var validUntil: String?

    enum CodingKeys: String, CodingKey {
        case id, name, category, status, subcategory, discount, conditions
        case redemption, code, address, lat, lng, neighborhood, hours
        case sourceURL = "source_url"
        case lastVerified = "last_verified"
        case validUntil = "valid_until"
    }
}
