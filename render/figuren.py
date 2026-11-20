"""Figuren und Zeichen-Helfer der Hirnalarm-Engine (rein, ohne Episoden-Zustand)."""
import math
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_HIER = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(_HIER, "..", "fonts", "Poppins-Bold.ttf")
if not os.path.exists(FONT):
    FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
_fc = {}
def font(sz):
    sz = max(10, int(sz))
    if sz not in _fc: _fc[sz] = ImageFont.truetype(FONT, sz)
    return _fc[sz]

# ============ easing ============
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x); return x ** 3
def back_out(x): x = clamp(x); c = 1.9; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def lerp(a, b, x): return a + (b - a) * x

# ============ sprites ============
OC = (40, 25, 20)
def face(d, cx, cy, expr, s=1.0, look=(0, 0)):
    talk = 0  # Sprech-Varianten: "<expr>_t1" = halb offen, "<expr>_t2" = weit offen
    if "_t" in expr:
        expr, stufe = expr.rsplit("_t", 1)
        talk = int(stufe or 2)
    er, pr = int(34 * s), int(16 * s)
    for ex in (-1, 1):
        x, y = cx + ex * int(48 * s), cy
        if expr == "dizzy":
            k = int(22 * s)
            d.line([x - k, y - k, x + k, y + k], fill=OC, width=int(10 * s)); d.line([x - k, y + k, x + k, y - k], fill=OC, width=int(10 * s))
            continue
        d.ellipse([x - er, y - er, x + er, y + er], fill="white", outline=OC, width=int(6 * s))
        p = pr if expr not in ("shock",) else int(9 * s)
        px, py = x + look[0] * 12 * s, y + look[1] * 10 * s
        d.ellipse([px - p, py - p, px + p, py + p], fill=OC)
        if expr == "angry":
            d.line([x - er, y - er - 4 * s + (ex < 0) * -18 * s, x + er, y - er - 4 * s + (ex > 0) * -18 * s], fill=OC, width=int(11 * s))
        if expr == "sad":
            d.line([x - er, y - er - 4 * s + (ex > 0) * -14 * s, x + er, y - er - 4 * s + (ex < 0) * -14 * s], fill=OC, width=int(9 * s))
    my = cy + int(62 * s)
    if talk:
        h = (20 if talk == 1 else 34) * s  # Mundöffnung
        bw = (28 if talk == 1 else 36) * s
        d.ellipse([cx - bw, my - 6 * s - h * 0.45, cx + bw, my + h], fill=(120, 20, 30), outline=OC, width=int(8 * s))
        if talk == 2:
            d.chord([cx - 20 * s, my + h * 0.25, cx + 20 * s, my + h], 180, 360, fill=(235, 90, 110))
        return
    if expr == "happy":
        d.arc([cx - 50 * s, my - 40 * s, cx + 50 * s, my + 30 * s], 15, 165, fill=OC, width=int(10 * s))
    elif expr in ("angry", "sad"):
        d.arc([cx - 40 * s, my + 5 * s, cx + 40 * s, my + 55 * s], 200, 340, fill=OC, width=int(10 * s))
        if expr == "sad":
            d.ellipse([cx + 70 * s, cy + 30 * s, cx + 90 * s, cy + 60 * s], fill=(90, 170, 255))
    elif expr == "shock":
        d.ellipse([cx - 22 * s, my - 18 * s, cx + 22 * s, my + 30 * s], fill=(120, 20, 30), outline=OC, width=int(7 * s))
    elif expr == "dizzy":
        d.line([(cx - 50 * s + i * 10 * s, my + 8 * s * math.sin(i * 1.4)) for i in range(11)], fill=OC, width=int(9 * s))
    elif expr == "grin":
        d.chord([cx - 55 * s, my - 35 * s, cx + 55 * s, my + 40 * s], 0, 180, fill="white", outline=OC, width=int(8 * s))

def spr_banana(expr, look, crack=False):
    w, h = 420, 600
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    N_, A, B, x0, y0, hh = 60, 230, 60, 70, 60, 470
    outer = [(x0 + A * math.sin(math.pi * (i / N_)) ** 0.9, y0 + hh * i / N_) for i in range(N_ + 1)]
    inner = [(x0 + 20 + B * math.sin(math.pi * (i / N_)), y0 + hh * i / N_) for i in range(N_, -1, -1)]
    d.polygon(outer + inner, fill=(255, 216, 40)); d.line(outer + inner + [outer[0]], fill=OC, width=9, joint="curve")
    d.line([(x0 + (A * 0.8) * math.sin(math.pi * (i / N_)), y0 + hh * i / N_) for i in range(8, N_ - 7)], fill=(232, 180, 20), width=14)
    d.rectangle([x0 - 4, y0 - 45, x0 + 30, y0 + 6], fill=(110, 80, 30), outline=OC, width=7)
    d.ellipse([x0 + 4, y0 + hh - 12, x0 + 34, y0 + hh + 14], fill=(70, 45, 20))
    face(d, x0 + 150, y0 + 200, expr, 1.0, look)
    return im, -125  # sprite, head x-offset (for crown)

def spr_melon(expr, look, crack=False):
    rr = 220; w = h = 2 * rr + 40
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = w // 2
    d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=(110, 190, 70))
    for k in (-0.85, -0.5, -0.15, 0.2, 0.55, 0.88):
        x = c + int(k * rr)
        pts = [(x + (k * rr * (math.cos(t * math.pi - math.pi / 2)) - k * rr), c - rr * math.cos(t * math.pi) * 0.97) for t in np.linspace(0, 1, 30)]
        d.line(pts, fill=(35, 110, 40), width=20, joint="curve")
    mask = Image.new("L", (w, h), 0); ImageDraw.Draw(mask).ellipse([c - rr, c - rr, c + rr, c + rr], fill=255)
    st_ = im.copy(); im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); im.paste(st_, (0, 0), mask); d = ImageDraw.Draw(im)
    d.ellipse([c - rr, c - rr, c + rr, c + rr], outline=OC, width=10)
    d.ellipse([c - rr * 0.55, c - rr * 0.8, c - rr * 0.15, c - rr * 0.5], fill=(190, 240, 150, 160))
    face(d, c, c - 30, expr, 1.15, look)
    return im, 0

def spr_pineapple(expr, look, crack=False):
    w, h = 420, 660
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, top = w // 2, 250
    # leaves
    for ang, L, col in ((-38, 200, (40, 140, 60)), (38, 200, (40, 140, 60)), (-15, 240, (60, 170, 70)), (15, 240, (60, 170, 70)), (0, 270, (80, 190, 80))):
        a = math.radians(ang - 90)
        tip = (cx + L * math.cos(a), top + 30 + L * math.sin(a))
        nrm = (math.cos(a + math.pi / 2) * 32, math.sin(a + math.pi / 2) * 32)
        poly = [(cx - nrm[0], top + 40 - nrm[1]), tip, (cx + nrm[0], top + 40 + nrm[1])]
        d.polygon(poly, fill=col, outline=OC); d.line(poly + [poly[0]], fill=OC, width=7)
    body = [cx - 165, top, cx + 165, h - 15]
    bim = Image.new("RGBA", (w, h), (0, 0, 0, 0)); bd = ImageDraw.Draw(bim)
    bd.ellipse(body, fill=(245, 175, 40))
    for k in range(-8, 9):
        bd.line([(cx + k * 55 - 300, top), (cx + k * 55 + 300, h)], fill=(200, 125, 20), width=7)
        bd.line([(cx + k * 55 + 300, top), (cx + k * 55 - 300, h)], fill=(200, 125, 20), width=7)
    mask = Image.new("L", (w, h), 0); ImageDraw.Draw(mask).ellipse(body, fill=255)
    im.paste(bim, (0, 0), mask); d = ImageDraw.Draw(im)
    d.ellipse(body, outline=OC, width=10)
    d.rounded_rectangle([cx - 120, top + 120, cx + 120, top + 330], 60, fill=(250, 200, 90))
    face(d, cx, top + 190, expr, 1.0, look)
    return im, 0

def spr_coconut(expr, look, crack=False):
    rr = 200; w = h = 2 * rr + 40
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = w // 2
    d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=(125, 80, 45))
    rnd = random.Random(3)
    for _ in range(170):
        a = rnd.uniform(0, 2 * math.pi); rad = rnd.uniform(0.2, 1.0) * rr
        x, y = c + rad * math.cos(a), c + rad * math.sin(a)
        L = rnd.uniform(14, 30); b = a + rnd.uniform(-0.6, 0.6)
        d.line([x, y, x + L * math.cos(b), y + L * math.sin(b)], fill=(90, 55, 30), width=4)
    d.ellipse([c - rr, c - rr, c + rr, c + rr], outline=OC, width=10)
    d.rounded_rectangle([c - 115, c - 85, c + 115, c + 120], 70, fill=(150, 100, 60))
    if crack:
        pts = [(c - 30, c - rr + 5), (c - 5, c - 120), (c - 40, c - 70), (c + 10, c - 20)]
        d.line(pts, fill=(255, 255, 255), width=16); d.line(pts, fill=OC, width=8)
        if crack == "plaster":
            pl = spr_plaster(); im.alpha_composite(pl, (c - 15 - pl.size[0] // 2, c - 110 - pl.size[1] // 2))
    face(d, c, c - 20, expr, 1.05, look)
    return im, 0

def spr_plaster():
    pl = Image.new("RGBA", (200, 90), (0, 0, 0, 0)); pd = ImageDraw.Draw(pl)
    pd.rounded_rectangle([4, 14, 196, 76], 26, fill=(240, 195, 150), outline=OC, width=6)
    pd.rectangle([70, 20, 130, 70], fill=(250, 225, 195))
    for xx in (25, 45, 155, 175): pd.ellipse([xx - 4, 40, xx + 4, 48], fill=(200, 150, 110))
    return pl.rotate(-30, expand=True, resample=Image.BICUBIC)

def spr_peel():
    im = Image.new("RGBA", (300, 140), (0, 0, 0, 0))
    for ang, dx in ((-35, -60), (0, 0), (35, 60)):
        leaf = Image.new("RGBA", (300, 140), (0, 0, 0, 0)); ld = ImageDraw.Draw(leaf)
        ld.ellipse([110, 10, 190, 130], fill=(255, 210, 40), outline=OC, width=7)
        im.alpha_composite(leaf.rotate(ang, center=(150, 125)), (dx // 3, 0))
    ImageDraw.Draw(im).ellipse([125, 100, 175, 135], fill=(240, 200, 40), outline=OC, width=6)
    return im

def spr_crown():
    im = Image.new("RGBA", (240, 160), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(10, 150), (10, 40), (65, 95), (120, 10), (175, 95), (230, 40), (230, 150)]
    d.polygon(pts, fill=(255, 200, 30)); d.line(pts + [pts[0]], fill=OC, width=8)
    for x in (60, 120, 180): d.ellipse([x - 13, 110, x + 13, 136], fill=(220, 40, 60), outline=OC, width=4)
    return im

def spr_strawberry(expr, look, crack=False):
    w, h = 440, 520
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx = w // 2
    body = [(cx + 200 * math.sin(a) * (0.55 + 0.45 * (1 - (a / math.pi))) , 120 + 380 * (1 - math.cos(a / 2 * 1.0)) ) for a in []]
    pts = []
    for i in range(61):
        t = i / 60 * 2 * math.pi
        x = math.sin(t); y = -math.cos(t)
        wid = 190 * (0.62 + 0.38 * (-y + 1) / 2) if y > -0.2 else 190
        pts.append((cx + x * wid, 300 + y * 200 * (1.0 if y > 0 else 0.75)))
    d.polygon(pts, fill=(230, 50, 60)); d.line(pts + [pts[0]], fill=OC, width=10, joint="curve")
    rnd = random.Random(5)
    for _ in range(40):
        x, y = rnd.uniform(cx - 140, cx + 140), rnd.uniform(180, 470)
        if d.im.getpixel((int(x), int(y)))[0] > 200:
            d.ellipse([x - 7, y - 10, x + 7, y + 10], fill=(255, 225, 120))
    for ang in range(-80, 81, 32):
        a = math.radians(ang - 90); L = 110
        tip = (cx + L * math.cos(a), 160 + L * math.sin(a) * 0.7)
        n = (math.cos(a + math.pi / 2) * 26, math.sin(a + math.pi / 2) * 26)
        poly = [(cx - n[0], 165 - n[1]), tip, (cx + n[0], 165 + n[1])]
        d.polygon(poly, fill=(60, 170, 70)); d.line(poly + [poly[0]], fill=OC, width=6)
    d.rectangle([cx - 10, 60, cx + 10, 130], fill=(60, 140, 60), outline=OC, width=5)
    face(d, cx, 300, expr, 1.0, look)
    return im, 0

def spr_lemon(expr, look, crack=False):
    w, h = 500, 420
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx, cy = w // 2, 230
    d.ellipse([60, 60, 440, 400], fill=(255, 235, 60), outline=OC, width=10)
    d.polygon([(55, 230), (20, 215), (20, 245)], fill=(255, 235, 60), outline=OC)
    d.polygon([(445, 230), (480, 215), (480, 245)], fill=(255, 235, 60), outline=OC)
    d.line([(20, 215), (20, 245)], fill=OC, width=8); d.line([(480, 215), (480, 245)], fill=OC, width=8)
    d.ellipse([130, 100, 220, 150], fill=(255, 250, 180))
    d.polygon([(250, 62), (300, 10), (330, 40)], fill=(70, 170, 70), outline=OC)
    face(d, cx, cy - 10, expr, 1.0, look)
    return im, 0

def spr_cucumber(expr, look, crack=False):
    w, h = 300, 700
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx = w // 2
    d.rounded_rectangle([cx - 110, 30, cx + 110, h - 10], 110, fill=(70, 150, 60), outline=OC, width=10)
    rnd = random.Random(9)
    for _ in range(36):
        x, y = rnd.uniform(cx - 85, cx + 85), rnd.uniform(70, h - 60)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(40, 105, 40))
    d.rounded_rectangle([cx - 85, 150, cx + 85, 400], 60, fill=(150, 210, 120))
    face(d, cx, 240, expr, 0.95, look)
    return im, 0

def spr_birch(expr, look, crack=False):
    # Birken-Baum (Gast). crack=True -> kahl (Blaetter weg)
    w, h = 560, 900
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx = w // 2
    # branches/arms
    d.line([(cx - 70, 520), (cx - 210, 430), (cx - 250, 360)], fill=(235, 235, 225), width=34, joint="curve")
    d.line([(cx + 70, 500), (cx + 200, 420), (cx + 235, 340)], fill=(235, 235, 225), width=34, joint="curve")
    d.line([(cx - 70, 520), (cx - 210, 430), (cx - 250, 360)], fill=OC, width=6)
    d.line([(cx + 70, 500), (cx + 200, 420), (cx + 235, 340)], fill=OC, width=6)
    if crack == "half":
        for a_ in (-50, -20):
            r = math.radians(a_ - 90)
            d.line([(cx, 330), (cx + 150 * math.cos(r), 330 + 170 * math.sin(r))], fill=(110, 80, 50), width=14)
        rnd = random.Random(11)
        for _ in range(12):
            x, y = cx + rnd.uniform(10, 190), rnd.uniform(90, 330); r = rnd.uniform(55, 85)
            d.ellipse([x - r, y - r, x + r, y + r], fill=rnd.choice([(120, 200, 70), (150, 215, 80), (95, 175, 60)]), outline=(50, 110, 40), width=5)
    elif crack:
        for a_ in (-50, -20, 15, 45):
            r = math.radians(a_ - 90)
            d.line([(cx, 330), (cx + 150 * math.cos(r), 330 + 170 * math.sin(r))], fill=(110, 80, 50), width=14)
        d.ellipse([cx + 90, 170, cx + 130, 215], fill=(150, 210, 70), outline=OC, width=4)
    else:
        rnd = random.Random(11)
        for _ in range(26):
            x, y = cx + rnd.uniform(-190, 190), rnd.uniform(60, 330); r = rnd.uniform(60, 95)
            d.ellipse([x - r, y - r, x + r, y + r], fill=rnd.choice([(120, 200, 70), (150, 215, 80), (95, 175, 60)]), outline=(50, 110, 40), width=5)
    d.rounded_rectangle([cx - 95, 300, cx + 95, h - 10], 50, fill=(245, 245, 238), outline=OC, width=10)
    rnd = random.Random(4)
    for _ in range(14):
        y = rnd.uniform(560, h - 50); x = cx + rnd.uniform(-80, 40)
        d.rounded_rectangle([x, y, x + rnd.uniform(25, 60), y + 12], 6, fill=(40, 35, 35))
    face(d, cx, 420, expr, 0.9, look)
    return im, 0

def spr_kiwi(expr, look, crack=False):
    w, h = 460, 520
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx, cy = w // 2, 280
    d.ellipse([cx - 200, cy - 230, cx + 200, cy + 230], fill=(140, 100, 55), outline=OC, width=10)
    rnd = random.Random(21)
    for _ in range(260):
        a = rnd.uniform(0, 2 * math.pi); rad = rnd.uniform(0.3, 1.0)
        x, y = cx + 190 * rad * math.cos(a), cy + 220 * rad * math.sin(a)
        d.line([x, y, x + rnd.uniform(-9, 9), y + rnd.uniform(-12, 12)], fill=(105, 72, 38), width=3)
    d.ellipse([cx - 135, cy - 150, cx + 135, cy + 170], fill=(120, 190, 50), outline=(80, 140, 30), width=8)
    d.ellipse([cx - 70, cy - 60, cx + 70, cy + 90], fill=(235, 245, 200))
    for k in range(18):
        a = k / 18 * 2 * math.pi; x, y = cx + 95 * math.cos(a), cy + 15 + 110 * math.sin(a)
        d.ellipse([x - 7, y - 11, x + 7, y + 11], fill=(30, 25, 20))
    face(d, cx, cy - 30, expr, 0.9, look)
    return im, 0

def spr_belt():
    im = Image.new("RGBA", (420, 170), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 55, 420, 115], 18, fill=(30, 30, 35), outline=OC, width=6)
    d.ellipse([110, 0, 310, 170], fill=(255, 200, 30), outline=OC, width=8)
    d.ellipse([145, 35, 275, 135], fill=(255, 230, 110), outline=(200, 140, 20), width=5)
    d.text((210, 85), "1", font=font(80), fill=(220, 40, 60), anchor="mm", stroke_width=4, stroke_fill=OC)
    return im

def spr_cat(expr, look, crack=False):
    # Katze (Gast, z. B. Schiri-Prinzessin Belen) mit Krönchen
    w, h = 460, 620
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx = w // 2
    fur, inner = (245, 160, 70), (255, 205, 150)
    # Schwanz
    d.line([(cx + 120, h - 60), (cx + 210, h - 180), (cx + 190, h - 300)], fill=OC, width=44, joint="curve")
    d.line([(cx + 120, h - 60), (cx + 210, h - 180), (cx + 190, h - 300)], fill=fur, width=30, joint="curve")
    # Körper
    d.ellipse([cx - 150, 300, cx + 150, h - 10], fill=fur, outline=OC, width=10)
    d.ellipse([cx - 85, 360, cx + 85, h - 40], fill=inner)
    # Ohren
    for sx in (-1, 1):
        ear = [(cx + sx * 150, 150), (cx + sx * 165, 20), (cx + sx * 60, 95)]
        d.polygon(ear, fill=fur); d.line(ear + [ear[0]], fill=OC, width=9)
        ein = [(cx + sx * 140, 135), (cx + sx * 152, 55), (cx + sx * 85, 100)]
        d.polygon(ein, fill=(255, 150, 170))
    # Kopf
    d.ellipse([cx - 175, 70, cx + 175, 370], fill=fur, outline=OC, width=10)
    for k in (-1, 0, 1):
        d.line([(cx + k * 40, 78), (cx + k * 30, 125)], fill=(215, 120, 40), width=12)
    # Schnurrhaare + Nase
    for sx in (-1, 1):
        for dy in (-12, 12):
            d.line([(cx + sx * 70, 300 + dy), (cx + sx * 190, 290 + dy * 2.2)], fill=OC, width=5)
    d.polygon([(cx - 16, 278), (cx + 16, 278), (cx, 294)], fill=(240, 110, 140), outline=OC)
    face(d, cx, 215, expr, 0.85, look)
    # Krönchen (Prinzessin)
    cr = [(cx - 70, 95), (cx - 70, 30), (cx - 35, 65), (cx, 5), (cx + 35, 65), (cx + 70, 30), (cx + 70, 95)]
    d.polygon(cr, fill=(255, 200, 30)); d.line(cr + [cr[0]], fill=OC, width=7)
    for x in (cx - 40, cx, cx + 40): d.ellipse([x - 10, 68, x + 10, 88], fill=(240, 90, 180), outline=OC, width=3)
    return im, 0

def spr_apple(expr, look, crack=False):
    # Apfel (Gast, z. B. Schiri Ron) mit Trillerpfeife
    w, h = 480, 540
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); cx = w // 2
    d.line([(cx, 120), (cx - 10, 30)], fill=(110, 70, 30), width=20)
    leaf = [(cx, 70), (cx + 70, 25), (cx + 140, 45), (cx + 70, 95)]
    d.polygon(leaf, fill=(80, 180, 70)); d.line(leaf + [leaf[0]], fill=OC, width=7)
    d.ellipse([cx - 210, 110, cx + 5, 520], fill=(225, 40, 50), outline=OC, width=10)
    d.ellipse([cx - 5, 110, cx + 210, 520], fill=(225, 40, 50), outline=OC, width=10)
    d.ellipse([cx - 195, 125, cx + 195, 510], fill=(225, 40, 50))
    d.arc([cx - 60, 95, cx + 60, 175], 200, 340, fill=OC, width=9)
    d.ellipse([cx - 150, 170, cx - 90, 260], fill=(255, 150, 150))
    face(d, cx, 300, expr, 1.0, look)
    # Trillerpfeife an der Kordel
    d.line([(cx - 120, 160), (cx + 90, 430)], fill=(30, 30, 30), width=6)
    d.rounded_rectangle([cx + 60, 410, cx + 150, 460], 18, fill=(200, 200, 215), outline=OC, width=6)
    return im, 0

KINDS = {"kiwi": spr_kiwi, "banana": spr_banana, "melon": spr_melon, "pineapple": spr_pineapple, "coconut": spr_coconut,
         "strawberry": spr_strawberry, "lemon": spr_lemon, "cucumber": spr_cucumber, "birch": spr_birch, "cat": spr_cat, "apple": spr_apple}
BASE_SC = {"banana": 1.0, "melon": 1.02, "pineapple": 0.92, "coconut": 1.0, "strawberry": 0.95, "lemon": 0.95, "cucumber": 0.9, "birch": 0.7, "kiwi": 0.95, "cat": 0.9, "apple": 0.95}
_sc = {}
def sprite(kind, expr, look, crack=False):
    k = (kind, expr, look, crack)
    if k not in _sc: _sc[k] = KINDS[kind](expr, look, crack)
    return _sc[k]
PEEL, CROWN = spr_peel(), spr_crown()
