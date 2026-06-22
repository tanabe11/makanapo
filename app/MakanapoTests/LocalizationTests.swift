import XCTest
@testable import Makanapo

final class LocalizationTests: XCTestCase {
    func test_stringTable_returnsJapaneseAndEnglish() {
        XCTAssertEqual(L10n.pickerAll.value(.ja), "すべて")
        XCTAssertEqual(L10n.pickerAll.value(.en), "All")
        XCTAssertEqual(L10n.verifyAtSource.value(.ja), "公式で確認")
        XCTAssertEqual(L10n.verifyAtSource.value(.en), "Verify at source")
        XCTAssertEqual(L10n.pickerKamaaina.value(.en), "Kama'aina")
    }

    @MainActor
    func test_toggle_flipsLanguage() {
        let m = LocalizationManager()
        let before = m.lang
        m.toggle()
        XCTAssertNotEqual(m.lang, before)
        m.toggle()
        XCTAssertEqual(m.lang, before)
    }
}
