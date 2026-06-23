import Foundation

@MainActor
final class LocalizationManager: ObservableObject {
    enum Lang: String { case en, ja }

    @Published private(set) var lang: Lang
    private let key = "app_language"

    init() {
        if let saved = UserDefaults.standard.string(forKey: "app_language"),
           let l = Lang(rawValue: saved) {
            lang = l
        } else {
            // First launch: follow the device language.
            let pref = Locale.preferredLanguages.first ?? "en"
            lang = pref.hasPrefix("ja") ? .ja : .en
        }
    }

    func toggle() {
        lang = (lang == .ja) ? .en : .ja
        UserDefaults.standard.set(lang.rawValue, forKey: key)
    }

    func t(_ k: L10n) -> String { k.value(lang) }
}

enum L10n {
    case pickerAll, pickerHappyHour, pickerKamaaina
    case loading, loadFailed, retry, noResults
    case verifiedPrefix, unverified, expired
    case detailDiscount, detailConditions, detailRedemption, detailHours, detailAddress, detailNeighborhood
    case freshnessSection, lastVerified, statusRow
    case statusActive, statusUnverified, statusExpired, statusUnknown
    case verifyAtSource, openInMaps, tapToListen
    case dealsTitle, menuRefresh, showMap, showList
    case menuAbout, aboutTagline, aboutDescription, aboutDataNote, aboutPrivacy
    case aboutVersion, aboutVisitSite, aboutClose
    case adLabel, adHouseRadio

    func value(_ lang: LocalizationManager.Lang) -> String {
        lang == .ja ? pair.ja : pair.en
    }

    private var pair: (ja: String, en: String) {
        switch self {
        case .pickerAll: return ("すべて", "All")
        case .pickerHappyHour: return ("ハッピーアワー", "Happy Hour")
        case .pickerKamaaina: return ("カマアイナ", "Kama'aina")
        case .loading: return ("読み込み中…", "Loading…")
        case .loadFailed: return ("割引を読み込めませんでした", "Couldn't load deals")
        case .retry: return ("再試行", "Retry")
        case .noResults: return ("この絞り込みに該当する割引はありません", "No deals match this filter")
        case .verifiedPrefix: return ("確認", "Verified")
        case .unverified: return ("未確認", "Unverified")
        case .expired: return ("期限切れ", "Expired")
        case .detailDiscount: return ("割引", "Discount")
        case .detailConditions: return ("条件", "Conditions")
        case .detailRedemption: return ("利用方法", "Redemption")
        case .detailHours: return ("時間", "Hours")
        case .detailAddress: return ("住所", "Address")
        case .detailNeighborhood: return ("地区", "Neighborhood")
        case .freshnessSection: return ("鮮度", "Freshness")
        case .lastVerified: return ("最終確認日", "Last verified")
        case .statusRow: return ("状態", "Status")
        case .statusActive: return ("確認済み", "Verified")
        case .statusUnverified: return ("未確認", "Unverified")
        case .statusExpired: return ("期限切れ", "Expired")
        case .statusUnknown: return ("不明", "Unknown")
        case .verifyAtSource: return ("公式で確認", "Verify at source")
        case .openInMaps: return ("マップで開く", "Open in Maps")
        case .tapToListen: return ("タップで再生", "Tap to listen")
        case .dealsTitle: return ("ハッピーアワー & カマアイナ", "Happy Hour & Kama'aina")
        case .menuRefresh: return ("再読み込み", "Refresh")
        case .showMap: return ("地図で見る", "Show map")
        case .showList: return ("一覧で見る", "Show list")
        case .menuAbout: return ("このアプリについて", "About")
        case .aboutTagline:
            return ("ホノルルのカマアイナ割引＆ハッピーアワー", "Honolulu kama'aina discounts & happy hour")
        case .aboutDescription:
            return (
                "makanapo は、ホノルルのカマアイナ割引とハッピーアワー情報をまとめたアプリです。各情報には最終確認日を表示し、鮮度を大切にしています。",
                "Makanapo gathers Honolulu kama'aina discounts and happy-hour deals. Every listing shows when it was last verified, so you can trust it's fresh."
            )
        case .aboutDataNote:
            return (
                "情報は公式サイト等の一次情報に基づきます。ご利用前に「公式で確認」リンクで最新をご確認ください。",
                "Info is based on primary sources (official sites). Tap “Verify at source” to confirm before you go."
            )
        case .aboutPrivacy:
            return ("閲覧専用・アカウント不要。個人情報は収集しません。",
                    "Read-only, no account, and we don't collect personal data.")
        case .aboutVersion: return ("バージョン", "Version")
        case .aboutVisitSite: return ("makana.fm を開く", "Visit makana.fm")
        case .aboutClose: return ("閉じる", "Close")
        case .adLabel: return ("PR", "Ad")
        case .adHouseRadio: return ("makana.fm — ハワイのラジオを聴く", "makana.fm — listen to Hawaii radio")
        }
    }
}
