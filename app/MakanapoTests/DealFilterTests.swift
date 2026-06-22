import XCTest
@testable import Makanapo

final class DealFilterTests: XCTestCase {
    private func decode(_ s: String) throws -> Deal {
        try JSONDecoder().decode(Deal.self, from: s.data(using: .utf8)!)
    }

    func test_happyHour_bySubcategory() throws {
        let d = try decode(#"{"id":"1","name":"Vein","category":"food","subcategory":"happy_hour","discount":"18% off","source_url":"https://e.com","last_verified":"2026-06-22","status":"active"}"#)
        XCTAssertTrue(d.isHappyHour)
        XCTAssertTrue(DealFilter.happyHour.matches(d))
        XCTAssertFalse(DealFilter.kamaaina.matches(d))
    }

    func test_kamaaina_byRequiresID() throws {
        let d = try decode(#"{"id":"2","name":"Spa","category":"service","subcategory":"spa_massage","discount":"10% off (kamaaina rate)","requires_id":true,"redemption":"show_id","source_url":"https://e.com","last_verified":"2026-06-22","status":"active"}"#)
        XCTAssertTrue(d.requiresID == true)
        XCTAssertTrue(d.isKamaaina)
        XCTAssertTrue(DealFilter.kamaaina.matches(d))
        XCTAssertFalse(DealFilter.happyHour.matches(d))
    }

    func test_all_matchesEverything() throws {
        let d = try decode(#"{"id":"3","name":"X","category":"food","source_url":"https://e.com","last_verified":"2026-06-22","status":"unverified"}"#)
        XCTAssertTrue(DealFilter.all.matches(d))
    }
}
