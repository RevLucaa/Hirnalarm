"""Kulissen (Hintergrund, Ring-Seile). Neue Arenen (bahn, fussball) kommen hierher."""
import random

import numpy as np
from PIL import Image, ImageDraw

from render.figuren import font

W, H = 1080, 1920
FLOOR = 1300


def make_bg(EP):
    if EP.get("arena") == "bahn":
        return make_bahn(EP)
    if EP.get("arena") == "fussball":
        return make_fussball(EP)
    a = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(EP.get("bg_top", [60, 20, 110])), np.array([15, 10, 40])
    arr = (top * (1 - a) + bot * a).repeat(W, 1).astype(np.uint8)
    bg = Image.fromarray(arr); d = ImageDraw.Draw(bg, "RGBA")
    for _ in range(420):
        x, y = random.randint(0, W), random.randint(380, 900); r_ = random.randint(14, 26)
        d.ellipse([x - r_, y - r_, x + r_, y + r_], fill=(random.randint(30, 80), random.randint(20, 60), random.randint(70, 130), 255))
    for sx in (200, 880):
        d.polygon([(sx - 40, 260), (sx + 40, 260), (sx + 330, FLOOR + 120), (sx - 330, FLOOR + 120)], fill=(255, 255, 220, 22))
    d.polygon([(130, FLOOR - 200), (950, FLOOR - 200), (1080, FLOOR + 260), (0, FLOOR + 260)], fill=tuple(EP.get("mat", [70, 120, 200])) + (255,))
    d.polygon([(0, FLOOR + 260), (1080, FLOOR + 260), (1080, FLOOR + 380), (0, FLOOR + 380)], fill=(40, 70, 140, 255))
    d.ellipse([340, FLOOR - 120, 740, FLOOR + 40], outline=(255, 255, 255, 90), width=8)
    for x in (130, 950):
        d.rectangle([x - 14, FLOOR - 520, x + 14, FLOOR - 190], fill=(200, 200, 210, 255), outline=(30, 30, 40, 255), width=4)
    for i, c in enumerate([(230, 40, 60), (245, 245, 245), (230, 40, 60)]):
        d.line([(130, FLOOR - 480 + i * 95), (950, FLOOR - 480 + i * 95)], fill=c + (255,), width=10)
    d.rectangle([0, FLOOR + 380, W, H], fill=(12, 8, 30, 255))
    return bg.convert("RGBA")

def front_ropes(d, sag=0.0):
    for i, c in enumerate([(230, 40, 60), (245, 245, 245), (230, 40, 60)]):
        y = FLOOR + 100 + i * 85
        if sag:
            d.line([(0, y), (540, y + sag), (1080, y)], fill=c, width=14)
        else:
            d.line([(0, y), (1080, y)], fill=c, width=14)
    for x in (30, 1050):
        d.rectangle([x - 22, FLOOR - 40, x + 22, FLOOR + 330], fill=(210, 210, 220), outline=(30, 30, 40), width=5)


# ============ Arena „bahn“ (Laufbahn, ab F12) ============
BAHN_LINIEN = (FLOOR - 230, FLOOR + 20, FLOOR + 270)


def make_bahn(EP):
    rnd = random.Random(EP.get("seed", 7))
    a = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(EP.get("bg_top", [70, 150, 230])), np.array([200, 225, 250])
    arr = (top * (1 - a) + bot * a).repeat(W, 1).astype(np.uint8)
    bg = Image.fromarray(arr); d = ImageDraw.Draw(bg, "RGBA")
    # Flutlichtmasten
    for sx in (90, 990):
        d.rectangle([sx - 10, 300, sx + 10, 520], fill=(90, 90, 100, 255))
        d.rounded_rectangle([sx - 70, 270, sx + 70, 330], 12, fill=(60, 60, 70, 255), outline=(30, 30, 40, 255), width=4)
        for k in range(4):
            d.ellipse([sx - 60 + k * 32, 282, sx - 36 + k * 32, 318], fill=(255, 255, 210, 255))
    # Tribüne mit Zuschauern
    for row in range(9):
        y = 420 + row * 56
        d.rectangle([0, y, W, y + 56], fill=(70 + row * 6, 75 + row * 6, 95 + row * 6, 255))
        d.line([(0, y), (W, y)], fill=(40, 40, 55, 255), width=4)
        for x in range(-10, W + 20, 46):
            xx = x + rnd.randint(-8, 8) + (row % 2) * 23; yy = y + 26 + rnd.randint(-5, 5)
            c = rnd.choice([(230, 60, 60), (250, 200, 40), (70, 170, 240), (110, 210, 90), (240, 130, 200), (250, 250, 250), (250, 140, 40)])
            d.ellipse([xx - 15, yy - 2, xx + 15, yy + 30], fill=c + (255,))
            d.ellipse([xx - 11, yy - 24, xx + 11, yy - 2], fill=rnd.choice([(250, 215, 170), (210, 160, 110), (150, 100, 60)]) + (255,))
    # Bande mit Werbung
    d.rectangle([0, 925, W, 1010], fill=(30, 30, 50, 255))
    for i, (txt, col) in enumerate([("OBST-LIGA", (255, 230, 0)), ("HIRNALARM", (255, 90, 90)), ("RENNEN", (120, 220, 255))]):
        x0 = 15 + i * 360
        d.rounded_rectangle([x0, 935, x0 + 330, 1000], 14, fill=col + (255,), outline=(0, 0, 0, 255), width=4)
        d.text((x0 + 165, 968), txt, font=font(44), fill=(20, 20, 30, 255), anchor="mm")
    # Kunststoffbahn mit Linien
    d.rectangle([0, 1010, W, FLOOR + 330], fill=(200, 85, 60, 255))
    for _ in range(900):
        x, y = rnd.randint(0, W), rnd.randint(1015, FLOOR + 325)
        d.point((x, y), fill=(170, 65, 45, 255))
    for y in BAHN_LINIEN:
        d.line([(0, y), (W, y)], fill=(250, 250, 250, 255), width=9)
    for k, y in enumerate((FLOOR - 105, FLOOR + 145)):
        d.text((60, y), str(k + 1), font=font(70), fill=(250, 250, 250, 200), anchor="mm")
    # Rasen
    d.rectangle([0, FLOOR + 330, W, H], fill=(40, 120, 50, 255))
    for x in range(0, W, 90):
        d.rectangle([x, FLOOR + 330, x + 45, H], fill=(48, 135, 58, 255))
    return bg.convert("RGBA")


def bahn_vorne(d, t, lauf):
    """Bewegte Bahnmarkierungen und Zaun vorn; bei Rennen (lauf) scrollt alles nach links."""
    off = (t * 1100) % 240 if lauf else 0
    for y in BAHN_LINIEN:
        for x in range(-240, W + 240, 240):
            xx = x - off
            d.rectangle([xx, y - 14, xx + 18, y + 14], fill=(255, 255, 255))
    off2 = (t * 1500) % 180 if lauf else 0
    d.rectangle([0, FLOOR + 395, W, FLOOR + 412], fill=(245, 245, 245), outline=(30, 30, 40), width=3)
    for x in range(-180, W + 180, 180):
        xx = x - off2
        d.rectangle([xx - 9, FLOOR + 360, xx + 9, FLOOR + 470], fill=(245, 245, 245), outline=(30, 30, 40), width=3)


def ziellinie(d, x, tape=1.0):
    """Schachbrett-Ziellinie über die Bahn, oben Zielband (tape 1 = gespannt, 0 = gerissen)."""
    for i, y in enumerate(range(1010, FLOOR + 330, 30)):
        for j in range(2):
            c = (20, 20, 20) if (i + j) % 2 == 0 else (250, 250, 250)
            d.rectangle([x - 30 + j * 30, y, x + j * 30, y + 30], fill=c)
    d.rectangle([x - 8, FLOOR - 560, x + 8, FLOOR + 60], fill=(230, 230, 235), outline=(30, 30, 40), width=4)
    d.text((x, FLOOR - 600), "ZIEL", font=font(70), fill=(255, 230, 0), anchor="mm", stroke_width=7, stroke_fill=(0, 0, 0))


# ============ Arena „fussball“ (Elfmeter, ab F14) ============
TOR_L, TOR_R = 200, 880          # Pfosten
TOR_OBEN = FLOOR - 660           # Latte
TORLINIE = FLOOR - 150           # Fußlinie des Torwarts
ELFER = (470, FLOOR + 235)       # Elfmeterpunkt (Ball), Schütze steht vorn links


def make_fussball(EP):
    rnd = random.Random(EP.get("seed", 7))
    a = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(EP.get("bg_top", [40, 70, 150])), np.array([120, 160, 220])
    arr = (top * (1 - a) + bot * a).repeat(W, 1).astype(np.uint8)
    bg = Image.fromarray(arr); d = ImageDraw.Draw(bg, "RGBA")
    # Flutlicht
    for sx in (110, 970):
        d.rectangle([sx - 10, 300, sx + 10, 470], fill=(90, 90, 100, 255))
        d.rounded_rectangle([sx - 80, 270, sx + 80, 330], 12, fill=(60, 60, 70, 255), outline=(30, 30, 40, 255), width=4)
        for k in range(5):
            d.ellipse([sx - 72 + k * 30, 284, sx - 50 + k * 30, 316], fill=(255, 255, 215, 255))
        d.polygon([(sx - 60, 330), (sx + 60, 330), (sx + 420, 1250), (sx - 420, 1250)], fill=(255, 255, 230, 18))
    # Tribüne mit Fans in Vereinsfarben
    for row in range(8):
        y = 400 + row * 50
        d.rectangle([0, y, W, y + 50], fill=(50 + row * 5, 55 + row * 5, 80 + row * 6, 255))
        d.line([(0, y), (W, y)], fill=(30, 30, 45, 255), width=4)
        for x in range(-10, W + 20, 44):
            xx = x + rnd.randint(-7, 7) + (row % 2) * 22; yy = y + 22 + rnd.randint(-4, 4)
            c = rnd.choice([(250, 200, 40), (250, 200, 40), (140, 90, 50), (140, 90, 50), (250, 250, 250), (230, 60, 60)])
            d.ellipse([xx - 14, yy - 2, xx + 14, yy + 28], fill=c + (255,))
            d.ellipse([xx - 10, yy - 22, xx + 10, yy - 2], fill=rnd.choice([(250, 215, 170), (210, 160, 110), (150, 100, 60)]) + (255,))
            if rnd.random() < 0.12:  # Schal hoch
                d.line([(xx - 18, yy - 30), (xx + 18, yy - 38)], fill=rnd.choice([(250, 200, 40), (140, 90, 50)]) + (255,), width=8)
    # Werbebande
    d.rectangle([0, 800, W, 880], fill=(25, 25, 45, 255))
    for i, (txt, col) in enumerate([("OBST-LIGA", (255, 230, 0)), ("HIRNALARM", (255, 90, 90)), ("ELFMETER", (120, 220, 255))]):
        x0 = 15 + i * 360
        d.rounded_rectangle([x0, 810, x0 + 330, 870], 14, fill=col + (255,), outline=(0, 0, 0, 255), width=4)
        d.text((x0 + 165, 840), txt, font=font(42), fill=(20, 20, 30, 255), anchor="mm")
    # Rasen mit Mähstreifen
    d.rectangle([0, 880, W, H], fill=(46, 140, 60, 255))
    for k, y in enumerate(range(880, H, 110)):
        if k % 2 == 0:
            d.rectangle([0, y, W, y + 110], fill=(56, 158, 70, 255))
    # Strafraum-Linien (perspektivisch) und Elfmeterpunkt
    wl = (250, 250, 250, 255)
    d.line([(0, TORLINIE), (W, TORLINIE)], fill=wl, width=8)
    d.line([(60, TORLINIE), (-60, FLOOR + 420)], fill=wl, width=8)
    d.line([(1020, TORLINIE), (1140, FLOOR + 420)], fill=wl, width=8)
    d.line([(-60, FLOOR + 420), (1140, FLOOR + 420)], fill=wl, width=8)
    d.ellipse([ELFER[0] - 22, ELFER[1] - 9, ELFER[0] + 22, ELFER[1] + 9], fill=wl)
    # Tor: Netz hinten, Pfosten und Latte
    hint = 70
    d.polygon([(TOR_L + 30, TOR_OBEN + hint), (TOR_R - 30, TOR_OBEN + hint), (TOR_R - 30, TORLINIE - 40), (TOR_L + 30, TORLINIE - 40)], fill=(235, 240, 245, 40))
    for x in range(TOR_L, TOR_R + 1, 34):
        d.line([(x, TOR_OBEN), (TOR_L + 30 + (x - TOR_L) * (TOR_R - TOR_L - 60) / (TOR_R - TOR_L), TOR_OBEN + hint), (TOR_L + 30 + (x - TOR_L) * (TOR_R - TOR_L - 60) / (TOR_R - TOR_L), TORLINIE - 40)], fill=(240, 240, 245, 150), width=3)
    for y in range(TOR_OBEN + hint, TORLINIE - 30, 34):
        d.line([(TOR_L + 30, y), (TOR_R - 30, y)], fill=(240, 240, 245, 150), width=3)
    for x0, x1 in ((TOR_L, TOR_L + 30), (TOR_R, TOR_R - 30)):
        for y in range(TOR_OBEN, TORLINIE, 34):
            d.line([(x0, y), (x1, y + hint * (1 - (y - TOR_OBEN) / (TORLINIE - TOR_OBEN)))], fill=(240, 240, 245, 150), width=3)
    torrahmen(d)
    return bg.convert("RGBA")


def torrahmen(d):
    for x in (TOR_L, TOR_R):
        d.rectangle([x - 16, TOR_OBEN - 16, x + 16, TORLINIE + 8], fill=(250, 250, 250, 255), outline=(30, 30, 40, 255), width=5)
    d.rectangle([TOR_L - 16, TOR_OBEN - 16, TOR_R + 16, TOR_OBEN + 16], fill=(250, 250, 250, 255), outline=(30, 30, 40, 255), width=5)


def netz_davor(d, x, y, r):
    """Netzmaschen über einer Figur, die im Tor hängt (Beule im Netz)."""
    for k in range(-r, r + 1, 34):
        d.line([(x + k, y - r), (x + k * 1.15, y + r)], fill=(245, 245, 250), width=3)
        d.line([(x - r, y + k), (x + r, y + k * 1.1)], fill=(245, 245, 250), width=3)


def fussball(d, x, y, r, rot=0.0):
    """Klassischer Fußball (weiß mit schwarzen Fünfecken)."""
    import math
    d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 250, 250), outline=(20, 20, 25), width=max(3, int(r / 9)))
    for k in range(5):
        a_ = rot + k * 2 * math.pi / 5
        cx, cy = x + 0.62 * r * math.cos(a_), y + 0.62 * r * math.sin(a_)
        rr = 0.24 * r
        d.polygon([(cx + rr * math.cos(a_ + j * 2 * math.pi / 5), cy + rr * math.sin(a_ + j * 2 * math.pi / 5)) for j in range(5)], fill=(25, 25, 30))
    rr = 0.27 * r
    d.polygon([(x + rr * math.cos(rot + math.pi + j * 2 * math.pi / 5), y + rr * math.sin(rot + math.pi + j * 2 * math.pi / 5)) for j in range(5)], fill=(25, 25, 30))
