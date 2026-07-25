#!/usr/bin/env python3
"""Print-ready business card artwork, front and back.

Design coordinates are authored at 89x51mm / 1049x601 px (~300dpi) to match
docs/superpowers/specs/2026-07-25-business-card-design.md, then scaled to the
output DPI. Real QR codes come from segno and are drawn module-by-module so
every module edge lands on a pixel boundary at any output size.
"""
import segno
from PIL import Image, ImageDraw, ImageFont
from functools import lru_cache

DESIGN_W, DESIGN_H = 1049, 601          # spec coordinate space
CARD_W_MM, CARD_H_MM = 89.0, 51.0
BLEED_MM = 3.0
DPI = 600

BLUE = (0x23, 0x84, 0xCB)
INK = (0x3A, 0x3A, 0x3A)
NAME_INK = (0x1A, 0x1A, 0x1A)           # darker than the contacts, so the name leads
GRAY = (0x6E, 0x6E, 0x6E)
WHITE = (255, 255, 255)

import os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{REPO}/img/card/print"
SERIF = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
SANS = "/System/Library/Fonts/Supplemental/Arial.ttf"

TAG = "Hawaiʻi's Internet Radio Station"
CTA, IG_BACK = "Tap and Listen!", "@makana.fm"
TITLE, NAME = "Founder & CEO", "Johnny Tanabe"
MAIL, IG_FRONT = "j@makana.fm", "@johnny_makana.fm"

QR_FRONT = ("https://instagram.com/johnny_makana.fm", "m")
QR_BACK_L = ("https://makana.fm/", "q")
QR_BACK_R = ("https://instagram.com/makana.fm", "m")

S = (CARD_W_MM / 25.4 * DPI) / DESIGN_W          # design px -> output px


def px(v):
    return int(round(v * S))


def font(path, design_size):
    return ImageFont.truetype(path, max(1, px(design_size)))


@lru_cache(maxsize=4)
def logo(path, design_w):
    lg = Image.open(path)
    w = px(design_w)
    return lg.resize((w, round(lg.height * w / lg.width)), Image.LANCZOS)


@lru_cache(maxsize=8)
def qr_matrix(url, ecc):
    q = segno.make(url, error=ecc, mode="byte")
    rows = [list(r) for r in q.matrix]
    return tuple(tuple(bool(v) for v in r) for r in rows), q.version


def draw_qr(im, x, y, size, url, ecc, border_modules=0):
    """Draw a QR so each module edge lands exactly on a pixel boundary.

    size = full graphic edge in output px, including border_modules of quiet
    zone on each side. Module widths differ by at most 1px, which keeps the
    edges hard instead of resampling them soft.
    """
    m, _ = qr_matrix(url, ecc)
    n = len(m)
    units = n + border_modules * 2
    d = ImageDraw.Draw(im)
    if border_modules:
        d.rectangle([x, y, x + size - 1, y + size - 1], fill=WHITE)

    def edge(i):
        return x + round(i * size / units)

    def edgey(i):
        return y + round(i * size / units)

    for r in range(n):
        for c in range(n):
            if m[r][c]:
                d.rectangle([edge(c + border_modules), edgey(r + border_modules),
                             edge(c + border_modules + 1) - 1,
                             edgey(r + border_modules + 1) - 1], fill=(0, 0, 0))


def th(d, t, f):
    b = d.textbbox((0, 0), t, font=f)
    return b[3] - b[1]


def tracked(d, x, y, txt, f, tr, fill):
    for ch in txt:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tr


def tracked_w(d, txt, f, tr):
    return sum(d.textlength(c, font=f) for c in txt) + tr * (len(txt) - 1)


def mail_icon(d, x, y, s, w):
    d.rectangle([x, y, x + s, y + s * 0.72], outline=INK, width=w)
    d.line([(x, y), (x + s / 2, y + s * 0.42), (x + s, y)], fill=INK, width=w)


def ig_icon(d, x, y, s, w):
    d.rounded_rectangle([x, y, x + s, y + s], radius=int(s * 0.28), outline=INK, width=w)
    d.ellipse([x + s * 0.28, y + s * 0.28, x + s * 0.72, y + s * 0.72], outline=INK, width=w)
    d.ellipse([x + s * 0.76, y + s * 0.15, x + s * 0.87, y + s * 0.26], fill=INK)


def render_front(canvas, ox, oy):
    """ox/oy = output-px offset of the trim area's top-left corner."""
    d = ImageDraw.Draw(canvas)

    def X(v):
        return ox + px(v)

    def Y(v):
        return oy + px(v)

    # Horizontal lockup from the original card: mark, the small wordmark beneath
    # it, and the script wordmark. The script one reads at ~5mm; the small one is
    # 1.27mm here, under the print floor, and is kept at the user's request.
    lg = logo(f"{REPO}/img/card/logo_h_blue.png", 354)      # 30.0 x 11.8 mm
    canvas.paste(lg, (X(74), Y(55)), lg)

    f_t, f_n, f_c = font(SERIF, 28), font(SERIF, 72), font(SERIF, 31)
    nw = tracked_w(d, NAME, f_n, px(8))
    nx = ox + (px(DESIGN_W) - nw) / 2                       # name centred on the card
    d.text((nx, Y(228)), TITLE, font=f_t, fill=GRAY)        # title on the name's left edge
    tracked(d, nx, Y(272), NAME, f_n, px(8), INK)

    icon, w = px(32), max(1, px(3))
    for i, (drawer, txt) in enumerate([(mail_icon, MAIL), (ig_icon, IG_FRONT)]):
        yy = Y(440 + i * 62)
        drawer(d, X(74), yy + (th(d, txt, f_c) - icon) / 2 + px(4), icon, w)
        d.text((X(132), yy), txt, font=f_c, fill=INK)

    # shifted right to a 4.7mm margin and trimmed to 14.0mm so the name clears it;
    # ink-to-ink separation from the name is 3.9mm
    draw_qr(canvas, X(829), Y(364), px(165), *QR_FRONT, border_modules=0)


def render_back(canvas, ox, oy):
    d = ImageDraw.Draw(canvas)

    def X(v):
        return ox + px(v)

    def Y(v):
        return oy + px(v)

    lg = logo(f"{REPO}/img/card/logo_white.png", 130)
    canvas.paste(lg, (ox + (px(DESIGN_W) - lg.width) // 2, Y(44)), lg)

    f_tag = font(SERIF, 60)
    tw = d.textlength(TAG, font=f_tag)
    d.text((ox + (px(DESIGN_W) - tw) / 2, Y(200)), TAG, font=f_tag, fill=WHITE)

    panel = px(220)
    for x_design, (url, ecc), label in ((282, QR_BACK_L, CTA), (546, QR_BACK_R, IG_BACK)):
        draw_qr(canvas, X(x_design), Y(293), panel, url, ecc, border_modules=4)
        f_lab = font(SANS, 30)
        lw = d.textlength(label, font=f_lab)
        d.text((X(x_design) + (panel - lw) / 2, Y(525)), label, font=f_lab, fill=WHITE)


def build(side, bleed):
    bleed_px = px(BLEED_MM / CARD_W_MM * DESIGN_W) if bleed else 0
    w = px(DESIGN_W) + bleed_px * 2
    h = px(DESIGN_H) + bleed_px * 2
    bg = WHITE if side == "front" else BLUE
    canvas = Image.new("RGB", (w, h), bg)
    (render_front if side == "front" else render_back)(canvas, bleed_px, bleed_px)
    return canvas


import os
os.makedirs(OUT, exist_ok=True)
print(f"output {DPI} dpi   scale {S:.4f}x from the {DESIGN_W}x{DESIGN_H} spec space\n")
for side in ("front", "back"):
    for bleed in (False, True):
        im = build(side, bleed)
        tag = "bleed3mm" if bleed else "trim"
        name = f"card_{side}_{tag}_{DPI}dpi.png"
        im.save(f"{OUT}/{name}", dpi=(DPI, DPI))
        mm_w = im.width / DPI * 25.4
        mm_h = im.height / DPI * 25.4
        print(f"{name:<38} {im.width}x{im.height}px = {mm_w:.1f}x{mm_h:.1f}mm")
