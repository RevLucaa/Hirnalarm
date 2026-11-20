"""Kulissen (Hintergrund, Ring-Seile). Neue Arenen (bahn, fussball) kommen hierher."""
import random

import numpy as np
from PIL import Image, ImageDraw

W, H = 1080, 1920
FLOOR = 1300


def make_bg(EP):
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
