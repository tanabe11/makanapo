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
    var requiresID: Bool?

    enum CodingKeys: String, CodingKey {
        case id, name, category, status, subcategory, discount, conditions
        case redemption, code, address, lat, lng, neighborhood, hours
        case sourceURL = "source_url"
        case lastVerified = "last_verified"
        case validUntil = "valid_until"
        case requiresID = "requires_id"
    }
}

/// The single most useful one-line highlight to surface for a deal.
enum DealHighlight: Equatable {
    case discount(String)   // a specific, informative discount
    case time(String)       // the happy-hour time window
    case happyHourTag       // generic happy-hour deal with no time → a clean tag
    case none
}

extension Deal {
    /// Generic happy-hour labels carry no real information ("happy hour specials",
    /// "happy hour pricing on select food and drinks") — we prefer the time instead.
    static func isGenericHappyHourDiscount(_ d: String) -> Bool {
        let s = d.lowercased()
        return s.contains("happy hour special") || s.contains("happy hour pricing")
    }

    /// What to show as the deal's headline: a specific discount wins; otherwise the
    /// happy-hour time window; otherwise a clean Happy Hour tag.
    var highlight: DealHighlight {
        if let d = discount, !Self.isGenericHappyHourDiscount(d) { return .discount(d) }
        if let h = hours, !h.isEmpty { return .time(h) }
        if isHappyHour { return .happyHourTag }
        if let d = discount { return .discount(d) }
        return .none
    }
}

extension Deal {
    /// Time-window discount (subcategory happy_hour, or text mentions happy hour / pau hana).
    var isHappyHour: Bool {
        if subcategory?.lowercased().contains("happy") == true { return true }
        let t = "\(discount ?? "") \(conditions ?? "") \(hours ?? "")".lowercased()
        return t.contains("happy hour") || t.contains("pau hana")
    }

    /// Local-resident discount (needs Hawaii ID, or text mentions kama'aina).
    var isKamaaina: Bool {
        if requiresID == true || redemption == "show_id" { return true }
        let t = "\(discount ?? "") \(conditions ?? "")".lowercased()
        return t.contains("kama")
    }
}

/// Browse genre for grouping the list (esp. the Kama'aina view, which mixes
/// restaurants with spas/salons/fitness).
enum DealGenre: Int, CaseIterable, Identifiable {
    case food, spa, beauty, fitness, other
    var id: Int { rawValue }
}

extension Deal {
    var genre: DealGenre {
        if category == "food" { return .food }
        let s = (subcategory ?? "").lowercased()
        if s.contains("spa") || s.contains("massage") { return .spa }
        if s.contains("salon") || s.contains("nail") || s.contains("barber")
            || s.contains("hair") || s.contains("beauty") { return .beauty }
        if s.contains("fitness") || s.contains("yoga") || s.contains("gym") { return .fitness }
        return .other
    }
}

enum DealFilter: String, CaseIterable, Identifiable {
    case all, happyHour, kamaaina
    var id: Self { self }

    var label: String {
        switch self {
        case .all: return "すべて"
        case .happyHour: return "ハッピーアワー"
        case .kamaaina: return "カマアイナ"
        }
    }

    func matches(_ deal: Deal) -> Bool {
        switch self {
        case .all: return true
        case .happyHour: return deal.isHappyHour
        case .kamaaina: return deal.isKamaaina
        }
    }
}
