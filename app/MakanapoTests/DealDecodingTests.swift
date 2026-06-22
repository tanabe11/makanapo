import XCTest
@testable import Makanapo

final class DealDecodingTests: XCTestCase {
    func test_decodesFullRecord() throws {
        let json = """
        {"id":"vein-kakaako-b90b1a","name":"Vein at Kaka'ako","category":"food",
         "subcategory":"happy_hour","discount":"18% off","conditions":"dine-in",
         "redemption":"show_id","requires_id":false,"address":"685 Auahi St",
         "lat":21.29,"lng":-157.85,"neighborhood":"Kakaako","hours":"HH 16:30-18:00",
         "source_url":"https://www.veinatkakaako.com/","last_verified":"2026-06-22",
         "status":"active"}
        """.data(using: .utf8)!
        let deal = try JSONDecoder().decode(Deal.self, from: json)
        XCTAssertEqual(deal.id, "vein-kakaako-b90b1a")
        XCTAssertEqual(deal.name, "Vein at Kaka'ako")
        XCTAssertEqual(deal.status, .active)
        XCTAssertEqual(deal.discount, "18% off")
        XCTAssertEqual(deal.neighborhood, "Kakaako")
    }

    func test_decodesMinimalRecord_optionalsAbsent() throws {
        let json = """
        {"id":"x","name":"Some Place","category":"service",
         "source_url":"https://example.com","last_verified":"2026-06-22","status":"unverified"}
        """.data(using: .utf8)!
        let deal = try JSONDecoder().decode(Deal.self, from: json)
        XCTAssertNil(deal.discount)
        XCTAssertEqual(deal.status, .unverified)
        XCTAssertEqual(deal.sourceURL.absoluteString, "https://example.com")
    }

    func test_unknownStatusFallsBackToUnknown() throws {
        let json = """
        {"id":"x","name":"N","category":"food","source_url":"https://e.com",
         "last_verified":"2026-06-22","status":"weird_value"}
        """.data(using: .utf8)!
        let deal = try JSONDecoder().decode(Deal.self, from: json)
        XCTAssertEqual(deal.status, .unknown)
    }
}
