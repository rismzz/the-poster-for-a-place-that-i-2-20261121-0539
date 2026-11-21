#!/usr/bin/env python3
"""LUMINARA - a travel poster for a place that does not exist.

Renders one 1024x1024 travel poster PNG to entry.png.
Pure Python 3.13 standard library only (os, math, struct, zlib):
a small raster canvas, a built-in 5x7 bitmap font, and a hand-written
PNG encoder. No third-party imports, no network, no randomness.

The place is invented: LUMINARA, an archipelago of floating islands
above a glowing lagoon, crowned by a single crystal spire. No real
destination is depicted, no quotes, no star ratings, no other copy.
"""
import math
import os
import struct
import zlib

OUT = os.path.join(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"),
                   "entry.png")
W, H = 1024, 1024

# ---------------------------------------------------------------- font
# 5x7 bitmap glyphs, authored for this poster. '#' is ink, '.' is blank.
_G = {
"A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
"B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
"C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
"D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
"E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
"F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
"G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
"H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
"I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
"J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
"K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
"L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
"M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
"N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
"O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
"P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
"Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
"R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
"S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
"T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
"U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
"V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
"W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
"X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
"Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
"Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
" ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
"-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
"'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
"\u00b7": (".....", ".....", ".##..", ".##..", ".....", ".....", "....."),
}


def text_width(s, sx):
    return int(round(len(s) * 6 * sx - sx))


def draw_text(cv, x, y, s, sx, sy, colour, align="left"):
    """Draw string s with its top-left at (x, y)."""
    w = text_width(s, sx)
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    cx = x
    for ch in s:
        glyph = _G.get(ch, _G["?"] if "?" in _G else _G[" "])
        for gy in range(7):
            row = glyph[gy]
            y0 = int(round(y + gy * sy))
            y1 = int(round(y + (gy + 1) * sy))
            for gx in range(5):
                if row[gx] != "#":
                    continue
                x0 = int(round(cx + gx * sx))
                x1 = int(round(cx + (gx + 1) * sx))
                cv.fill_rect(x0, y0, x1, y1, colour)
        cx += 6 * sx


def draw_text_outline(cv, x, y, s, sx, sy, colour, outline, align="left",
                      ow=3):
    """Text with a dark outline halo so it stays legible on any ground."""
    for dx, dy in ((-ow, 0), (ow, 0), (0, -ow), (0, ow),
                   (-ow, -ow), (ow, -ow), (-ow, ow), (ow, ow)):
        draw_text(cv, x + dx, y + dy, s, sx, sy, outline, align)
    draw_text(cv, x, y, s, sx, sy, colour, align)


# ---------------------------------------------------------------- canvas
def _lerp(a, b, t):
    return int(round(a + (b - a) * t))


def _mix(c1, c2, t):
    return (_lerp(c1[0], c2[0], t), _lerp(c1[1], c2[1], t),
            _lerp(c1[2], c2[2], t))


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = 3 * (y * self.w + x)
            self.px[i], self.px[i + 1], self.px[i + 2] = colour

    def fill_rect(self, x0, y0, x1, y1, colour):
        x0 = max(0, int(x0)); y0 = max(0, int(y0))
        x1 = min(self.w, int(x1)); y1 = min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(colour) * (x1 - x0)
        for y in range(y0, y1):
            base = 3 * (y * self.w + x0)
            self.px[base:base + 3 * (x1 - x0)] = row

    def vgrad(self, x0, y0, x1, y1, top, bottom):
        """Vertical gradient over a rectangle, one row at a time."""
        x0 = max(0, int(x0)); y0 = max(0, int(y0))
        x1 = min(self.w, int(x1)); y1 = min(self.h, int(y1))
        span = max(1, y1 - y0 - 1)
        for y in range(y0, y1):
            c = _mix(top, bottom, (y - y0) / span)
            row = bytes(c) * (x1 - x0)
            base = 3 * (y * self.w + x0)
            self.px[base:base + 3 * (x1 - x0)] = row

    def rect(self, x0, y0, x1, y1, colour, width=1):
        for k in range(width):
            self.fill_rect(x0 + k, y0 + k, x1 - k, y0 + k + 1, colour)
            self.fill_rect(x0 + k, y1 - k - 1, x1 - k, y1 - k, colour)
            self.fill_rect(x0 + k, y0 + k, x0 + k + 1, y1 - k, colour)
            self.fill_rect(x1 - k - 1, y0 + k, x1 - k, y1 - k, colour)

    def line(self, x0, y0, x1, y1, colour, width=1):
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        r = width // 2
        for i in range(steps + 1):
            t = i / steps
            x = int(round(x0 + dx * t))
            y = int(round(y0 + dy * t))
            self.fill_rect(x - r, y - r, x + r + 1, y + r + 1, colour)

    def fill_circle(self, cx, cy, r, colour):
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.fill_rect(cx - dx, y, cx + dx + 1, y + 1, colour)

    def circle(self, cx, cy, r, colour, width=1):
        for k in range(width):
            rr = r - k
            if rr <= 0:
                break
            n = max(24, int(2 * math.pi * rr))
            for i in range(n):
                a = 2 * math.pi * i / n
                self.set(int(round(cx + rr * math.cos(a))),
                         int(round(cy + rr * math.sin(a))), colour)

    def fill_ellipse(self, cx, cy, rx, ry, colour):
        for y in range(cy - ry, cy + ry + 1):
            dy = (y - cy) / ry
            dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
            self.fill_rect(cx - dx, y, cx + dx + 1, y + 1, colour)

    def polygon(self, pts, colour):
        """Scanline-filled polygon."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(round(xs[i])), y,
                               int(round(xs[i + 1])) + 1, y + 1, colour)


# ---------------------------------------------------------------- PNG
def write_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- palette
CREAM = (246, 236, 212)
CREAM_BRIGHT = (252, 244, 222)
GOLD = (198, 150, 70)
NAVY = (18, 44, 66)
SKY_TOP = (22, 56, 102)
SKY_MID = (56, 116, 150)
SKY_LOW = (244, 178, 104)
SUN = (255, 228, 152)
SUN_GLOW = (255, 204, 122)
CLOUD = (255, 222, 182)
ISLE_GREEN = (46, 110, 74)
ISLE_DARK = (28, 76, 50)
ROCK = (96, 70, 58)
ROCK_DARK = (72, 52, 44)
SPIRE = (150, 230, 235)
SPIRE_CORE = (226, 252, 252)
SEA_TOP = (66, 168, 168)
SEA_BOT = (14, 66, 94)
GLITTER = (255, 208, 132)
SILHOUETTE = (18, 38, 50)
HOUSE = (250, 226, 180)
WINDOW = (255, 190, 90)


# ---------------------------------------------------------------- scene
def draw_sky(img):
    img.vgrad(24, 24, 1000, 604, SKY_TOP, SKY_LOW)


def draw_sun(img):
    cx, cy = 712, 452
    for r, col in ((150, (255, 196, 110)), (118, (255, 208, 124)),
                   (92, SUN_GLOW)):
        img.fill_circle(cx, cy, r, col)
    img.fill_circle(cx, cy, 64, SUN)
    # thin bright rim
    img.circle(cx, cy, 64, (255, 244, 200), 2)


def draw_clouds(img):
    # kept below the tagline so no cloud ever crosses the name
    for (cx, cy, rx, ry, col) in (
            (230, 252, 140, 14, CLOUD),
            (330, 274, 100, 11, (252, 210, 168)),
            (820, 242, 120, 13, CLOUD),
            (180, 332, 110, 11, (250, 204, 160)),
            (880, 332, 95, 10, (250, 204, 160)),
            (600, 306, 80, 9, (252, 214, 172))):
        img.fill_ellipse(cx, cy, rx, ry, col)


def draw_birds(img):
    for (bx, by, s) in ((280, 240, 12), (340, 214, 9), (640, 252, 11),
                        (700, 222, 8), (430, 262, 8)):
        img.line(bx - s, by, bx, by - 6, NAVY, 2)
        img.line(bx, by - 6, bx + s, by, NAVY, 2)


def draw_sea(img):
    img.vgrad(24, 604, 1000, 1000, SEA_TOP, SEA_BOT)
    # sun glitter: a path of light under the sun, ending well above
    # the footer line so the bottom text sits on clean water
    for k in range(32):
        y = 622 + k * 8
        t = (y - 622) / 360.0
        w = int(26 + 130 * t + 26 * math.sin(k * 1.7))
        cx = 712 + int(14 * math.sin(k * 0.9))
        col = GLITTER if k % 2 == 0 else (244, 196, 118)
        img.fill_rect(cx - w, y, cx + w, y + 2, col)


def draw_island(img, cx, cy, rx, ry, tip_y, scale, with_spire=False):
    """One floating isle: green crown, rocky tapering underside."""
    # crown
    img.fill_ellipse(cx, cy, rx, ry, ISLE_GREEN)
    img.fill_ellipse(cx, cy - 3, int(rx * 0.86), int(ry * 0.7), ISLE_DARK)
    # rocky underside tapering to a point
    img.polygon([(cx - rx, cy + 2), (cx + rx, cy + 2),
                 (cx + int(rx * 0.30), tip_y - 26), (cx, tip_y),
                 (cx - int(rx * 0.30), tip_y - 26)], ROCK)
    img.polygon([(cx - int(rx * 0.55), cy + 2), (cx + int(rx * 0.55), cy + 2),
                 (cx + int(rx * 0.16), tip_y - 14), (cx, tip_y),
                 (cx - int(rx * 0.16), tip_y - 14)], ROCK_DARK)
    # little trees on the crown
    for tx in (-int(rx * 0.55), int(rx * 0.1), int(rx * 0.6)):
        img.line(cx + tx, cy - 4, cx + tx, cy - int(26 * scale),
                 (30, 70, 44), max(2, int(3 * scale)))
        img.fill_circle(cx + tx, cy - int(30 * scale), int(9 * scale),
                        ISLE_DARK)
    if with_spire:
        # the crystal spire: the landmark of Luminara
        base = cy - 2
        img.polygon([(cx - 26, base), (cx + 26, base), (cx + 9, 372),
                     (cx, 348), (cx - 9, 372)], SPIRE)
        img.polygon([(cx - 8, base), (cx + 8, base), (cx + 3, 380),
                     (cx, 362), (cx - 3, 380)], SPIRE_CORE)
        img.fill_circle(cx, 348, 7, SPIRE_CORE)
        # glow ring at the spire tip
        img.circle(cx, 348, 16, (200, 244, 244), 2)
        # tiny houses with warm windows at the spire's foot
        for hx, hw in ((-86, 34), (64, 30)):
            img.fill_rect(cx + hx, base - 22, cx + hx + hw, base, HOUSE)
            img.polygon([(cx + hx - 3, base - 22), (cx + hx + hw + 3,
                         base - 22), (cx + hx + hw // 2, base - 34)],
                        (178, 96, 60))
            img.fill_rect(cx + hx + hw // 2 - 4, base - 14,
                          cx + hx + hw // 2 + 4, base - 4, WINDOW)


def draw_waterfall(img):
    # a thread of light falling from the great isle into the lagoon
    x = 512
    img.polygon([(x - 5, 742), (x + 5, 742), (x + 9, 880), (x - 9, 880)],
                (190, 236, 240))
    img.polygon([(x - 2, 742), (x + 2, 742), (x + 4, 880), (x - 4, 880)],
                (240, 250, 250))
    img.fill_ellipse(x, 884, 34, 7, (200, 238, 240))
    img.fill_ellipse(x, 884, 20, 4, (240, 250, 250))


def draw_boat(img):
    # a small lateen sailboat crossing the glitter path
    bx, by = 648, 838
    img.polygon([(bx - 34, by), (bx + 34, by), (bx + 22, by + 16),
                 (bx - 22, by + 16)], (24, 40, 54))
    img.line(bx, by - 2, bx, by - 52, (24, 40, 54), 3)
    img.polygon([(bx + 3, by - 50), (bx + 3, by - 4), (bx + 34, by - 4)],
                CREAM_BRIGHT)
    img.polygon([(bx - 3, by - 44), (bx - 3, by - 4), (bx - 26, by - 4)],
                (232, 196, 140))


def draw_foreground(img):
    # dark headland, bottom-left, with one windswept tree
    img.polygon([(24, 1000), (24, 892), (150, 928), (300, 972),
                 (340, 1000)], SILHOUETTE)
    img.line(120, 1000, 128, 892, (12, 28, 38), 7)
    for dx, dy, ln in ((-34, -26, 46), (30, -30, 44), (0, -40, 40),
                       (-18, -44, 34)):
        img.line(124, 900, 124 + dx, 900 + dy, (12, 28, 38), 5)
    # a small windswept canopy crowning the trunk
    img.fill_circle(124, 872, 18, (12, 28, 38))
    img.fill_circle(142, 884, 12, (12, 28, 38))


def draw_frame(img):
    img.fill_rect(0, 0, W, 24, CREAM)
    img.fill_rect(0, H - 24, W, H, CREAM)
    img.fill_rect(0, 0, 24, H, CREAM)
    img.fill_rect(W - 24, 0, W, H, CREAM)
    img.rect(24, 24, 1000, 1000, GOLD, 3)
    img.rect(30, 30, 994, 994, GOLD, 1)


def main():
    img = Canvas(W, H, CREAM)
    draw_sky(img)
    draw_sun(img)
    draw_clouds(img)
    draw_birds(img)
    draw_sea(img)
    # far isles first, great isle last so it leads the eye
    draw_island(img, 262, 512, 104, 20, 616, 0.8)
    draw_island(img, 782, 496, 88, 17, 592, 0.7)
    draw_island(img, 512, 586, 208, 32, 742, 1.0, with_spire=True)
    draw_waterfall(img)
    draw_boat(img)
    draw_foreground(img)
    draw_frame(img)
    # type: name first, then the promise, then the quiet footer line
    draw_text_outline(img, 512, 66, "LUMINARA", 12.5, 13.5, CREAM_BRIGHT,
                      NAVY, "center", ow=4)
    draw_text_outline(img, 512, 178, "WHERE THE ISLANDS FLOAT ON LIGHT",
                      2.5, 3.1, CREAM_BRIGHT, NAVY, "center", ow=2)
    draw_text(img, 512, 952, "THE FLOATING ISLES", 2.1, 2.7,
              CREAM_BRIGHT, "center")
    img.line(330, 962, 390, 962, GOLD, 2)
    img.line(634, 962, 694, 962, GOLD, 2)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    write_png(img, OUT)
    print("wrote", OUT, (W, H), os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
