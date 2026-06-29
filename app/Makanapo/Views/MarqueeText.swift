import SwiftUI

/// Single-line marquee: while `playing`, one copy of `text` drifts slowly left,
/// fully exits the left edge, then re-enters from the right — looping forever.
/// When not playing, shows the plain (truncated) text.
///
/// Driven by `TimelineView` (offset derived from absolute time) rather than a
/// `withAnimation` loop, so it always resumes after stop/play and never gets
/// stuck. Apply `.font`/`.foregroundStyle` on the caller — they propagate to the
/// inner Text via the environment.
struct MarqueeText: View {
    let text: String
    var playing: Bool
    var speed: CGFloat = 45              // points per second (gentle)
    var alignment: Alignment = .leading // alignment of the static (not-playing) text

    @State private var textWidth: CGFloat = 0
    @State private var containerWidth: CGFloat = 0

    private var scrolls: Bool { playing && textWidth > 1 && containerWidth > 0 }

    var body: some View {
        Group {
            if scrolls {
                TimelineView(.animation(paused: !playing)) { ctx in
                    Text(text)
                        .lineLimit(1)
                        .fixedSize()
                        .offset(x: offset(at: ctx.date))
                }
            } else {
                Text(text).lineLimit(1).truncationMode(.tail)
            }
        }
        .frame(maxWidth: .infinity, alignment: scrolls ? .leading : alignment)
        .clipped()
        .background(GeometryReader { g in
            Color.clear.preference(key: MarqueeContainerWidthKey.self, value: g.size.width)
        })
        .background(measurer)
        .onPreferenceChange(MarqueeContainerWidthKey.self) { containerWidth = $0 }
        .onPreferenceChange(MarqueeTextWidthKey.self) { textWidth = $0 }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(text)
    }

    /// x-offset of the single text: starts off the right edge (containerWidth),
    /// travels left until fully off-screen (-textWidth), then wraps.
    private func offset(at date: Date) -> CGFloat {
        let distance = containerWidth + textWidth
        guard distance > 0, speed > 0 else { return containerWidth }
        let period = Double(distance / speed)
        let t = date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: period)
        let progress = CGFloat(t / period)            // 0 → 1
        return containerWidth - progress * distance   // containerWidth → -textWidth
    }

    /// Invisible single copy that reports its natural width up via a preference.
    private var measurer: some View {
        Text(text)
            .lineLimit(1)
            .fixedSize()
            .background(GeometryReader { g in
                Color.clear.preference(key: MarqueeTextWidthKey.self, value: g.size.width)
            })
            .hidden()
    }
}

private struct MarqueeContainerWidthKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = max(value, nextValue()) }
}
private struct MarqueeTextWidthKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = max(value, nextValue()) }
}
