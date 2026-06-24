import XCTest
@testable import Makanapo

/// The one-line "highlight" shown for a deal: a specific discount wins; a generic
/// happy-hour label ("happy hour specials"/"pricing…") is replaced by the time
/// window, or a clean Happy Hour tag when no time is known.
final class DealHighlightTests: XCTestCase {
    private func decode(_ s: String) throws -> Deal {
        try JSONDecoder().decode(Deal.self, from: s.data(using: .utf8)!)
    }

    func test_specificDiscount_wins_evenWithTime() throws {
        let d = try decode(#"{"id":"1","name":"X","category":"food","subcategory":"happy_hour","discount":"18% off all pasta during happy hour","hours":"3-6pm","source_url":"https://e.com","last_verified":"2026-06-22","status":"active"}"#)
        XCTAssertEqual(d.highlight, .discount("18% off all pasta during happy hour"))
    }

    func test_genericSpecials_showsTime() throws {
        let d = try decode(#"{"id":"2","name":"X","category":"food","subcategory":"happy_hour","discount":"happy hour specials","hours":"3:00pm – 6:00pm","source_url":"https://e.com","last_verified":"2026-06-22","status":"active"}"#)
        XCTAssertEqual(d.highlight, .time("3:00pm – 6:00pm"))
    }

    func test_genericPricing_showsTime() throws {
        let d = try decode(#"{"id":"3","name":"X","category":"food","subcategory":"happy_hour","discount":"happy hour pricing on select food and drinks","hours":"Mon-Fri 16:00-18:00","source_url":"https://e.com","last_verified":"2026-06-22","status":"active"}"#)
        XCTAssertEqual(d.highlight, .time("Mon-Fri 16:00-18:00"))
    }

    func test_genericLabel_noTime_showsHappyHourTag() throws {
        let d = try decode(#"{"id":"4","name":"X","category":"food","subcategory":"happy_hour","discount":"happy hour specials","source_url":"https://e.com","last_verified":"2026-06-22","status":"active"}"#)
        XCTAssertEqual(d.highlight, .happyHourTag)
    }

    func test_kamaainaDiscount_isKept() throws {
        let d = try decode(#"{"id":"5","name":"X","category":"food","discount":"10% off with valid Hawaii ID","requires_id":true,"source_url":"https://e.com","last_verified":"2026-06-22","status":"active"}"#)
        XCTAssertEqual(d.highlight, .discount("10% off with valid Hawaii ID"))
    }
}
