"""Hirnalarm Duell-Engine: rendert ein Obst-Duell aus einer Episoden-JSON + Stimme.
Usage: python3 engine.py episode.json voice.mp3 out.mp4 [preview t1,t2,...]
"""
import sys, math, random, subprocess, re, json, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
_fc = {}
def font(sz):
    sz = max(10, int(sz))
    if sz not in _fc: _fc[sz] = ImageFont.truetype(FONT, sz)
    return _fc[sz]

EP = json.load(open(sys.argv[1]))
AUDIO, OUT = sys.argv[2], sys.argv[3]
random.seed(EP.get("seed", 7))

# ============ timing (phrase/pause alignment) ============
def duration(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout.strip())

def syl(text):
    t = text.lower()
    return max(1, len(re.findall(r"[aeiouäöüy]+", t)) + 2 * t.count("gaaanz"))

DUR = duration(AUDIO)
r = subprocess.run(["ffmpeg", "-i", AUDIO, "-af", "silencedetect=noise=-35dB:d=0.12", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.\-e]+)", r)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
pairs = list(zip(st, en))
lead = pairs[0][1] if pairs and pairs[0][0] <= 0.05 else 0.0
tail = pairs[-1][0] if pairs and pairs[-1][1] >= DUR - 0.05 else DUR
cands = [((a + b) / 2, b - a) for a, b in pairs if a > lead + 0.1 and b < tail - 0.1]

SEGS = EP["segments"]  # list of dicts: {scene, text, ...}
PHR = []
for si, s in enumerate(SEGS):
    for p in [p.strip() for p in re.split(r"(?<=[.!?:])\s+", s["text"]) if p.strip()]:
        PHR.append((si, p))
S = [syl(p) + (4 if "[laugh]" in p else 0) for _, p in PHR]
PHR = [(si, p.replace("[laugh]", "").strip()) for si, p in PHR]
N, M = len(PHR), len(cands)
rate = (tail - lead) / sum(S)
pos = [c[0] for c in cands]
INF = 1e18
def cost(d, s, g):
    e = rate * s
    return ((d - e) / e) ** 2 - 0.6 * g
dp = [[INF] * M for _ in range(N)]; bk = [[-1] * M for _ in range(N)]
for j in range(M): dp[0][j] = cost(pos[j] - lead, S[0], cands[j][1])
for i in range(1, N - 1):
    for j in range(M):
        for k in range(j):
            if dp[i - 1][k] >= INF: continue
            v = dp[i - 1][k] + cost(pos[j] - pos[k], S[i], cands[j][1])
            if v < dp[i][j]: dp[i][j], bk[i][j] = v, k
fin, fj = INF, -1
for j in range(M):
    if dp[N - 2][j] < INF:
        v = dp[N - 2][j] + cost(tail - pos[j], S[N - 1], 0)
        if v < fin: fin, fj = v, j
ends = [0.0] * (N - 1); j = fj
for i in range(N - 2, -1, -1): ends[i] = pos[j]; j = bk[i][j]
PH_T, prev = [], lead
for i in range(N):
    e = ends[i] if i < N - 1 else tail
    PH_T.append((prev, e)); prev = e
TOTAL = DUR + EP.get("tail", 2.4)
starts = []
for si in range(len(SEGS)):
    ts = [PH_T[i] for i, (s2, _) in enumerate(PHR) if s2 == si]
    starts.append(ts[0][0])
starts[0] = 0.0
SEG = [(SEGS[i], starts[i], starts[i + 1] if i + 1 < len(SEGS) else TOTAL) for i in range(len(SEGS))]
WORDS, NCH = [], 0
for (si, p), (a_, b_) in zip(PHR, PH_T):
    ws = p.replace("...", " ").split()
    L = sum(syl(w_) + 0.6 for w_ in ws); t = a_ + 0.03; span = max(0.3, b_ - a_ - 0.12)
    for wi, w_ in enumerate(ws):
        dd = span * (syl(w_) + 0.6) / L
        WORDS.append((w_, t, t + dd, NCH)); t += dd
        if wi % 2 == 1 or wi == len(ws) - 1: NCH += 1
if "preview" in sys.argv:
    for (si, p), (a_, b_) in zip(PHR, PH_T):
        print(f"{a_:6.2f}-{b_:6.2f} {SEGS[si]['scene']:8s} {p}", file=sys.stderr)

# ============ easing ============
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x); return x ** 3
def back_out(x): x = clamp(x); c = 1.9; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def lerp(a, b, x): return a + (b - a) * x

# ============ sprites ============
OC = (40, 25, 20)
def face(d, cx, cy, expr, s=1.0, look=(0, 0)):
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
    face(d, c, c - 20, expr, 1.05, look)
    return im, 0

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

KINDS = {"banana": spr_banana, "melon": spr_melon, "pineapple": spr_pineapple, "coconut": spr_coconut,
         "strawberry": spr_strawberry, "lemon": spr_lemon, "cucumber": spr_cucumber}
BASE_SC = {"banana": 1.0, "melon": 1.02, "pineapple": 0.92, "coconut": 1.0, "strawberry": 0.95, "lemon": 0.95, "cucumber": 0.9}
_sc = {}
def sprite(kind, expr, look, crack=False):
    k = (kind, expr, look, crack)
    if k not in _sc: _sc[k] = KINDS[kind](expr, look, crack)
    return _sc[k]
PEEL, CROWN = spr_peel(), spr_crown()

# ============ background ============
FLOOR = 1300
def make_bg():
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
BG = make_bg()

def front_ropes(d, sag=0.0):
    for i, c in enumerate([(230, 40, 60), (245, 245, 245), (230, 40, 60)]):
        y = FLOOR + 100 + i * 85
        if sag:
            d.line([(0, y), (540, y + sag), (1080, y)], fill=c, width=14)
        else:
            d.line([(0, y), (1080, y)], fill=c, width=14)
    for x in (30, 1050):
        d.rectangle([x - 22, FLOOR - 40, x + 22, FLOOR + 330], fill=(210, 210, 220), outline=(30, 30, 40), width=5)

# ============ draw helpers ============
def paste_char(img, ch):
    if not ch["show"]: return
    spr, headx = sprite(ch["kind"], ch["expr"], ch["look"], ch.get("crack", False))
    sc = ch["sc"]
    nw, nh = max(1, int(spr.size[0] * sc * ch["sx"])), max(1, int(spr.size[1] * sc * ch["sy"]))
    s = spr.resize((nw, nh), Image.BICUBIC)
    if ch.get("flip"): s = s.transpose(Image.FLIP_LEFT_RIGHT); headx = -headx
    if ch["rot"]: s = s.rotate(ch["rot"], expand=True, resample=Image.BICUBIC)
    if ch["y"] >= FLOOR - 400:
        sw = nw * 0.42 * clamp(1 - (FLOOR - ch["y"]) / 500)
        ImageDraw.Draw(img, "RGBA").ellipse([ch["x"] - sw, FLOOR - 16, ch["x"] + sw, FLOOR + 16], fill=(0, 0, 0, 70))
    img.alpha_composite(s, (int(ch["x"] - s.size[0] / 2), int(ch["y"] - s.size[1])))
    if ch.get("crown", 0) > 0:
        cu = ch["crown"]
        top_y = ch["y"] - nh
        cy = lerp(-200, top_y - 110, ease_out(cu / 0.3))
        c = CROWN.rotate(-8, expand=True)
        img.alpha_composite(c, (int(ch["x"] + headx * sc - c.size[0] / 2), int(cy)))

def text_c(d, xy, txt, f, fill="white", stroke=10, sc=(0, 0, 0)):
    d.text(xy, txt, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sc)

def banner(img, txt, u, color):
    if u < 0 or u > 1: return
    s = back_out(u / 0.18) if u < 0.18 else 1.0
    a = 1.0 if u < 0.85 else 1 - (u - 0.85) / 0.15
    if a <= 0: return
    layer = Image.new("RGBA", (1000, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.rounded_rectangle([20, 30, 980, 230], 40, fill=tuple(color) + (255,), outline=(0, 0, 0, 255), width=10)
    fs = 118
    while d.textlength(txt, font=font(fs)) > 900: fs -= 6
    text_c(d, (500, 128), txt, font(fs), stroke=9)
    layer = layer.rotate(-4, expand=True, resample=Image.BICUBIC)
    ns = max(1, int(layer.size[0] * s)), max(1, int(layer.size[1] * s))
    layer = layer.resize(ns, Image.BICUBIC)
    if a < 1: layer.putalpha(layer.split()[3].point(lambda p: int(p * a)))
    img.alpha_composite(layer, (W // 2 - ns[0] // 2, 640 - ns[1] // 2))

def starburst(img, cx, cy, r_, txt, u, col=(255, 90, 30)):
    if u <= 0 or u >= 1: return
    s = back_out(u / 0.25) if u < 0.25 else 1.0
    a = 1.0 if u < 0.7 else 1 - (u - 0.7) / 0.3
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    pts = [(cx + r_ * s * (1 if i % 2 == 0 else 0.62) * math.cos(i * math.pi / 14), cy + r_ * s * (1 if i % 2 == 0 else 0.62) * math.sin(i * math.pi / 14)) for i in range(28)]
    d.polygon(pts, fill=(255, 220, 40, int(255 * a)))
    d.polygon([(cx + (x - cx) * 0.8, cy + (y - cy) * 0.8) for x, y in pts], fill=tuple(col) + (int(255 * a),))
    d.text((cx, cy), txt, font=font(150 * s * min(1, 5.5 / max(4, len(txt)))), fill=(255, 255, 255, int(255 * a)), anchor="mm", stroke_width=10, stroke_fill=(0, 0, 0, int(255 * a)))
    img.alpha_composite(layer)

def speed_lines(d, t):
    rnd = random.Random(int(t * 30))
    for _ in range(14):
        y = rnd.randint(900, 1250); L = rnd.randint(80, 260); x = rnd.randint(0, W)
        d.line([x, y, x + L, y], fill=(255, 255, 255), width=rnd.randint(4, 9))

CONF = [(random.randint(0, W), random.uniform(-1, 0) * 900, random.uniform(160, 420), random.uniform(-3, 3),
         random.choice([(255, 80, 80), (255, 220, 40), (80, 200, 255), (120, 255, 120), (255, 120, 255)])) for _ in range(140)]
def confetti(d, t):
    for x, y0, v, sp, c in CONF:
        y = y0 + v * t
        if 0 < y < FLOOR + 380:
            xx = x + 30 * math.sin(t * 3 + sp); a = t * 5 + sp
            d.polygon([(xx + 14 * math.cos(a), y + 8 * math.sin(a)), (xx - 14 * math.cos(a), y - 8 * math.sin(a)),
                       (xx - 14 * math.cos(a) + 6, y - 8 * math.sin(a) + 12), (xx + 14 * math.cos(a) + 6, y + 8 * math.sin(a) + 12)], fill=c)

SPLASH = [(random.uniform(-1, 1), random.uniform(-1.4, -0.4), random.uniform(10, 22)) for _ in range(60)]
def splash(d, cx, cy, u):
    if u <= 0 or u > 1: return
    for vx, vy, r_ in SPLASH:
        x = cx + vx * 700 * u; y = cy + vy * 700 * u + 1400 * u * u
        d.ellipse([x - r_, y - r_, x + r_, y + r_], fill=(250, 250, 245), outline=(200, 200, 190))

def topbar(img, sc, pulse):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 90, 1040, 250], 36, fill=(20, 12, 45), outline=(255, 255, 255), width=6)
    text_c(d, (540, 170), "VS", font(64), fill=(255, 80, 80), stroke=6)
    for i, x in ((0, 290), (1, 790)):
        f = FIGHTERS[i]; p = pulse[i]
        text_c(d, (x - 60, 170), f["short"].upper(), font(54 if len(f["short"]) <= 5 else 46), fill=tuple(f["color"]), stroke=6)
        r_ = 52 + 14 * p
        d.ellipse([x + 120 - r_, 170 - r_, x + 120 + r_, 170 + r_], fill=tuple(f["color"]), outline=(0, 0, 0), width=6)
        text_c(d, (x + 120, 172), str(sc[i]), font(70 + 18 * p), stroke=6)
    if EP.get("episode"):
        d.rounded_rectangle([40, 268, 300, 330], 20, fill=(255, 80, 80), outline=(0, 0, 0), width=5)
        text_c(d, (170, 299), f"FOLGE {EP['episode']}", font(38), stroke=4)

def captions(img, t):
    idx = [i for i, wd in enumerate(WORDS) if wd[1] <= t < wd[2]]
    if not idx:
        prev_ = [i for i, wd in enumerate(WORDS) if wd[2] <= t and t - wd[2] < 0.35]
        if not prev_: return
        i = prev_[-1]; cur_i = -1
    else:
        i = idx[0]; cur_i = i
    ch = WORDS[i][3]
    group = [(k, wd) for k, wd in enumerate(WORDS) if wd[3] == ch]
    d = ImageDraw.Draw(img)
    words = [wd[0].upper() for _, wd in group]
    gap, sz = 34, 118
    while True:
        ws = [d.textlength(w_, font=font(sz)) for w_ in words]
        if sum(ws) + gap * (len(ws) - 1) <= 1000 or sz <= 60: break
        sz -= 6
    x = W / 2 - (sum(ws) + gap * (len(ws) - 1)) / 2
    for (k, wd), w_, wl in zip(group, words, ws):
        cur = k == cur_i
        ff = font(sz * (1.0 + 0.14 * (1 - clamp((t - wd[1]) / 0.12)))) if cur else font(sz)
        d.text((x + wl / 2, 1790), w_, font=ff, fill=(255, 230, 0) if cur else (255, 255, 255), anchor="mm", stroke_width=12, stroke_fill=(0, 0, 0))
        x += wl + gap

# ============ fighters & actions ============
FIGHTERS = EP["fighters"]  # [{kind,name,short,color}, ...]  index 0 = left, 1 = right
HOME = [300, 790]
SFX = []  # (time, kind)

def base_state(i, t):
    f = FIGHTERS[i]
    return dict(kind=f["kind"], x=HOME[i], y=FLOOR, sc=BASE_SC[f["kind"]], sx=1, sy=1 + 0.03 * math.sin(t * 7 + i),
                rot=0, expr="happy" if i == 0 else "angry", look=(1, 0) if i == 0 else (-1, 0), show=True)

def act_race(u, t, A, V, ai, p, ex):
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    off = W + 260 if dr > 0 else -260; back = -260 if dr > 0 else W + 260
    A["x"] = lerp(hA, off, ease_in(u / 0.35)) if u < 0.35 else lerp(back, hA + dr * 120, ease_out((u - 0.35) / 0.3))
    A["rot"] = -12 * dr if u < 0.65 else 0; A["expr"] = "grin"
    if p.get("trip"):
        if u < 0.55: V["x"] = lerp(hV, hV + dr * 90, u / 0.55); V["expr"] = "angry"
        else:
            q = clamp((u - 0.55) / 0.15); V["x"] = hV + dr * 90; V["rot"] = -dr * 85 * ease_out(q); V["y"] = FLOOR + 40 * q; V["expr"] = "dizzy"
            ex.append(("burst", V["x"], 950, 140, "PLUMPS!", clamp((u - 0.55) / 0.4)))
    else:
        V["x"] = lerp(hV, hV + dr * 140, u); V["rot"] = -dr * u * 200; V["expr"] = "shock" if u > 0.5 else "happy"
    if 0.15 < u < 0.65: ex.append(("speed",))
    ex.append(("burst", 540, 900, 150, "ZOOM!", clamp((u - 0.05) / 0.4)))
    return [(0.1, "whoosh"), (0.4, "whoosh")] + ([(0.6, "thud")] if p.get("trip") else [])

def act_slam(u, t, A, V, ai, p, ex):
    hA, hV = HOME[ai], HOME[1 - ai]
    V["expr"] = "shock"; V["look"] = (0, -1)
    hit = p.get("hit", 0.42); jump0 = p.get("jump0", 0.0)
    if p.get("peel"):
        pu = clamp(u / 0.22)
        px = lerp(hV, 540, pu); py = FLOOR - 40 - math.sin(pu * math.pi) * 380
        ex.append(("peel", px, py if pu < 1 else FLOOR, pu * 540 if pu < 1 else 0))
        V["expr"] = "grin" if u < hit - 0.1 else "shock"
    if u < jump0:
        A["expr"] = "angry"
    elif u < hit - 0.07:
        q = (u - jump0) / (hit - 0.07 - jump0)
        A["y"] = FLOOR - 900 * ease_out(q); A["x"] = lerp(hA, hV, q); A["expr"] = "angry"
    elif u < hit:
        A["y"] = FLOOR - 900 * (1 - ease_in((u - hit + 0.07) / 0.07)); A["x"] = hV
    else:
        if p.get("bounce"):
            q = clamp((u - hit) / 0.35)
            A["x"] = lerp(hV, hA, q); A["y"] = FLOOR - math.sin(q * math.pi) * 600; A["rot"] = (1 if ai == 0 else -1) * q * 360; A["expr"] = "dizzy"
            V["expr"] = "grin" if u > hit + 0.1 else "angry"; V["sy"] = 1 - 0.08 * math.exp(-(u - hit) * 30)
            if u > hit + 0.35: A["x"] = hA; A["y"] = FLOOR; A["rot"] = 0
            ex.append(("burst", 540, 760, 230, "BOING!", clamp((u - hit) / 0.45)))
        else:
            A["x"] = hV; A["y"] = FLOOR; A["sy"] = 1 - 0.12 * math.exp(-(u - hit) * 30)
            V["sy"] = 0.28; V["sx"] = 1.5; V["expr"] = "dizzy"
            if u > 0.75: A["x"] = lerp(hV, hA, ease_out((u - 0.75) / 0.25))
            ex.append(("burst", 540, 760, 260, "BOOM!", clamp((u - hit) / 0.45)))
        if u < hit + 0.12: ex.append(("shake", 26))
    return [(hit, "boing" if p.get("bounce") else "boom")] + ([(0.03, "whoosh")] if p.get("peel") else [])

def act_post(u, t, A, V, ai, p, ex):
    # A = dodger (wins), V = roller crashes into post
    dr = 1 if (1 - ai) == 0 else -1  # roller direction
    postx = 960 if dr > 0 else 120
    hA, hV = HOME[ai], HOME[1 - ai]
    h = p.get('hit', 0.62); hop = h - 0.14
    if u < hop - 0.2:
        A["x"] = lerp(hA, postx - dr * 140, ease_out(u / (hop - 0.2))); A["expr"] = "grin"
    elif u < hop:
        q = 0; A["x"] = postx - dr * 140; A["expr"] = "shock"
    else:
        q = clamp((u - hop) / 0.12); A["x"] = lerp(postx - dr * 140, 540, ease_out(q)); A["y"] = FLOOR - math.sin(q * math.pi) * 250; A["expr"] = "grin"
    if u < h:
        V["x"] = lerp(hV, postx - dr * 160, ease_in(u / h)); V["rot"] = -dr * u * 900; V["expr"] = "angry"
    else:
        V["x"] = postx - dr * 150; V["rot"] = -dr * 558 + 6 * math.sin(t * 40) * (1 - clamp((u - h) / 0.3)); V["expr"] = "dizzy"
        if u < h + 0.08: ex.append(("shake", 16))
        ex.append(("burst", postx - dr * 120, 820, 150, "BONK!", clamp((u - h) / 0.35)))
    ex.append(("post", postx))
    return [(0.1, "whoosh"), (h, "boom_s")]

def act_spin(u, t, A, V, ai, p, ex):
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    if u < 0.45:
        A["x"] = lerp(hA, hV - dr * 230, ease_in(u / 0.45)); A["rot"] = u * 2400; A["expr"] = "grin"
    else:
        A["x"] = hV - dr * 230; A["rot"] = 0; A["expr"] = "grin"
        q = clamp((u - 0.45) / 0.45)
        V["y"] = FLOOR - math.sin(q * math.pi) * 450; V["x"] = lerp(hV, hV + dr * 120, q); V["expr"] = "shock"; V["rot"] = dr * -20 * math.sin(q * math.pi)
        ex.append(("burst", hV, 760, 170, "AUA!", clamp((u - 0.45) / 0.5)))
        if u < 0.55: ex.append(("shake", 12))
    return [(0.05, "whoosh"), (0.45, "pop"), (0.47, "boom_s")]

def act_headbutt(u, t, A, V, ai, p, ex):
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    edge = 1000 if dr > 0 else 80
    if u < 0.2:
        A["x"] = lerp(hA, hA - dr * 120, ease_out(u / 0.2)); A["expr"] = "angry"
    elif u < 0.38:
        A["x"] = lerp(hA - dr * 120, hV - dr * 200, ease_in((u - 0.2) / 0.18)); A["rot"] = -dr * 18; A["expr"] = "angry"
    else:
        A["x"] = hV - dr * 200; A["expr"] = "grin"
        q = clamp((u - 0.38) / 0.25)
        V["x"] = lerp(hV, edge, ease_out(q)); V["rot"] = dr * -30 * q; V["expr"] = "shock"; V["sx"] = 1 - 0.2 * q * (q < 1)
        sag = 0
        if u > 0.6:
            r2 = clamp((u - 0.6) / 0.3)
            V["x"] = lerp(edge, hV + dr * 60, ease_out(r2)); V["rot"] = 0; V["expr"] = "dizzy"; V["sx"] = 1
        if u < 0.45: ex.append(("shake", 18))
        ex.append(("burst", (hV + edge) / 2, 780, 170, "KNALL!", clamp((u - 0.38) / 0.45)))
        ex.append(("sag", 60 * math.sin(clamp((u - 0.45) / 0.25) * math.pi)))
    return [(0.25, "whoosh"), (0.38, "boom_s"), (0.6, "boing")]

def act_clash(u, t, A, V, ai, p, ex):
    # A = winner; both charge to centre; V cracks
    dA = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    if u < 0.2:
        A["x"] = lerp(hA, hA - dA * 120, ease_out(u / 0.2)); V["x"] = lerp(hV, hV + dA * 120, ease_out(u / 0.2))
        A["expr"] = V["expr"] = "angry"
    elif u < 0.36:
        q = ease_in((u - 0.2) / 0.16)
        A["x"] = lerp(hA - dA * 120, 540 - dA * 190, q); V["x"] = lerp(hV + dA * 120, 540 + dA * 190, q)
        A["expr"] = V["expr"] = "angry"; A["rot"] = -dA * 15; V["rot"] = dA * 15
    else:
        A["x"] = 540 - dA * 190; V["x"] = 540 + dA * 190; A["expr"] = "dizzy" if u < 0.6 else "grin"
        V["crack"] = True; V["expr"] = "dizzy" if u < 0.55 else "shock"
        if u < 0.46: ex.append(("shake", 28))
        ex.append(("burst", 540, 760, 240, "KRACH!", clamp((u - 0.36) / 0.4)))
        if p.get("splash"): ex.append(("splash", V["x"], FLOOR - 380, clamp((u - 0.5) / 0.5)))
    return [(0.2, "whoosh"), (0.36, "boom"), (0.5, "pop")]

ACTIONS = {"race": act_race, "slam": act_slam, "post": act_post, "spin": act_spin, "headbutt": act_headbutt, "clash": act_clash}

# precompute scores & sfx
order = [s for s, _, _ in SEG]
def seg_at(t):
    for s, a, b in SEG:
        if a <= t < b: return s, (t - a) / max(0.01, b - a), a, b
    s, a, b = SEG[-1]; return s, 1.0, a, b
def score_at(t):
    sc = [0, 0]
    for s, a, b in SEG:
        if s["scene"] == "point" and t >= a + 0.15 * (b - a): sc[s["side"]] += 1
    return sc
WIN_T = next((a for s, a, b in SEG if s["scene"] == "win"), TOTAL)
WINNER = next((s["side"] for s, a, b in SEG if s["scene"] == "win"), 0)

def frame(t, collect_sfx=False):
    s, u, a, b = seg_at(t)
    sc_ = s["scene"]
    img = BG.copy()
    d = ImageDraw.Draw(img)
    F = [base_state(0, t), base_state(1, t)]
    ex = []; pulse = [0, 0]
    if sc_ == "intro":
        F[0]["x"] = lerp(-300, HOME[0], back_out(u / 0.35)); F[1]["x"] = lerp(W + 300, HOME[1], back_out(u / 0.35))
        F[0]["expr"] = "grin"
        ex.append(("burst", 540, 900, 180, "VS", clamp((u - 0.25) / 0.75)))
    elif sc_ == "tag":
        i = s["side"]; o = 1 - i
        F[i]["sc"] *= 1 + 0.2 * ease_out(u / 0.2); F[i]["x"] = lerp(HOME[i], 450 if i == 0 else 610, ease_out(u / 0.2)); F[i]["expr"] = "grin"; F[i]["look"] = (0, 0)
        F[o]["x"] = lerp(HOME[o], 970 if o == 1 else 110, ease_out(u / 0.2)); F[o]["sc"] *= 0.7
        ex.append(("tag", FIGHTERS[i]["name"].upper(), FIGHTERS[i]["color"], u))
    elif sc_ == "banner":
        ex.append(("banner", s["label"], s.get("color", [255, 80, 80]), u))
        F[0]["expr"] = F[1]["expr"] = "angry"
        if s.get("shake"): ex.append(("shake", 6))
    elif sc_ == "action":
        ai = s["actor"]; A, V = F[ai], F[1 - ai]
        evs = ACTIONS[s["type"]](u, t, A, V, ai, s, ex)
        if collect_sfx:
            for uu, kind in evs: SFX.append((a + uu * (b - a), kind))
    elif sc_ == "point":
        i = s["side"]; o = 1 - i
        F[i]["y"] = FLOOR - abs(math.sin(u * 12)) * 60 * (1 - u); F[i]["expr"] = "grin"; F[o]["expr"] = s.get("loser_expr", "angry")
        pulse[i] = math.sin(math.pi * clamp((u - 0.15) / 0.3))
        ex.append(("burst", HOME[i], 600, 140, "+1", u))
        sc = score_at(b - 0.01)
        if s.get("show_score"): ex.append(("big", f"{sc[0]} : {sc[1]}", clamp((u - 0.45) / 0.55)))
    elif sc_ in ("win", "tease", "cta"):
        wi = WINNER; li = 1 - wi; W_ = F[wi]; L_ = F[li]
        tw = t - WIN_T
        if sc_ == "win":
            W_["x"] = lerp(HOME[wi], 540, ease_out(u / 0.25)); W_["sc"] *= lerp(1, 1.3, ease_out(u / 0.25))
            W_["y"] = FLOOR - abs(math.sin(t * 7)) * 50; W_["expr"] = "grin"; W_["look"] = (0, 0); W_["crown"] = u
            L_["show"] = False
            ex += [("confetti", tw), ("big", "SIEGER!", clamp(u / 0.4))]
        elif sc_ == "tease":
            W_["x"] = 540; W_["sc"] *= 1.3; W_["y"] = FLOOR - abs(math.sin(t * 7)) * 30; W_["expr"] = "grin"; W_["crown"] = 1
            ex.append(("confetti", tw))
            tk = s.get("teaser")  # kind of a teased fighter or None -> loser peeks
            if tk:
                F[li] = dict(kind=tk, x=930 if wi == 0 else 150, y=lerp(H + 200, FLOOR + 380, ease_out(u / 0.4)), sc=BASE_SC[tk] * 0.95, sx=1, sy=1,
                             rot=12 if wi == 0 else -12, expr="angry", look=(-1, -1) if wi == 0 else (1, -1), show=True)
            else:
                L_["x"] = 930 if wi == 0 else 150; L_["y"] = lerp(H + 200, FLOOR + 380, ease_out(u / 0.4)); L_["expr"] = s.get("loser_expr", "sad")
                L_["sc"] *= 0.95; L_["rot"] = 12 if wi == 0 else -12; L_["look"] = (-1, -1) if wi == 0 else (1, -1)
        else:
            W_["x"] = lerp(540, HOME[wi], ease_out(u / 0.2)); W_["sc"] *= lerp(1.3, 1, ease_out(u / 0.2))
            W_["y"] = FLOOR - abs(math.sin(t * 7)) * 30; W_["expr"] = "grin"; W_["look"] = (0, 0); W_["crown"] = 1
            ex.append(("confetti", tw))
            tk = s.get("challenger")
            if tk:
                F[li] = dict(kind=tk, x=HOME[li], y=lerp(FLOOR + 380, FLOOR, ease_out(u / 0.3)), sc=BASE_SC[tk], sx=1, sy=1, rot=0, expr="angry", look=(-1, 0) if li == 1 else (1, 0), show=True)
            else:
                L_["y"] = lerp(FLOOR + 380, FLOOR, ease_out(u / 0.3)); L_["expr"] = "angry"
            ex.append(("cta", u, s.get("line1", "WER KÄMPFT ALS"), s.get("line2", "NÄCHSTES?")))

    shake = (0, 0)
    for e in ex:
        if e[0] == "shake": shake = (random.randint(-e[1], e[1]), random.randint(-e[1], e[1]))
    if any(e[0] == "speed" for e in ex): speed_lines(d, t)
    for e in ex:
        if e[0] == "peel":
            p_ = PEEL.rotate(e[3], expand=True); img.alpha_composite(p_, (int(e[1] - p_.size[0] / 2), int(e[2] - p_.size[1] + 40)))
    # draw lower (airborne) last
    for ch in sorted(F, key=lambda c: -c["y"]): paste_char(img, ch)
    d = ImageDraw.Draw(img)
    for e in ex:
        if e[0] == "post":
            px = e[1]
            d.rectangle([px - 30, FLOOR - 560, px + 30, FLOOR + 30], fill=(210, 210, 225), outline=(30, 30, 40), width=7)
            d.rectangle([px - 40, FLOOR - 580, px + 40, FLOOR - 540], fill=(230, 40, 60), outline=(30, 30, 40), width=6)
    sag = next((e[1] for e in ex if e[0] == "sag"), 0)
    front_ropes(d, sag)
    for e in ex:
        k = e[0]
        if k == "burst": starburst(img, *e[1:])
        elif k == "banner": banner(img, e[1], e[3], e[2])
        elif k == "tag":
            text_c(ImageDraw.Draw(img), (540, 600), e[1], font(min(110, 1700 / max(8, len(e[1]))) * back_out(e[3] / 0.25)), fill=tuple(e[2]), stroke=12)
        elif k == "confetti": confetti(ImageDraw.Draw(img), e[1])
        elif k == "splash": splash(ImageDraw.Draw(img), e[1], e[2], e[3])
        elif k == "big" and e[2] > 0:
            text_c(ImageDraw.Draw(img), (540, 560), e[1], font(190 * back_out(e[2] / 0.4)), fill=(255, 230, 0), stroke=14)
        elif k == "cta":
            uu = e[1]; dd = ImageDraw.Draw(img); s_ = back_out(uu / 0.25)
            dd.rounded_rectangle([90, 470, 990, 700], 40, fill=(230, 30, 50), outline=(0, 0, 0), width=10)
            text_c(dd, (540, 540), e[2], font(min(80, 1500 / max(10, len(e[2]))) * s_), stroke=8)
            text_c(dd, (540, 635), e[3], font(min(96, 1500 / max(8, len(e[3]))) * s_), fill=(255, 230, 0), stroke=8)
            ay = 790 + 25 * math.sin(t * 8)
            dd.polygon([(500, ay), (580, ay), (580, ay + 70), (630, ay + 70), (540, ay + 150), (450, ay + 70), (500, ay + 70)], fill=(255, 230, 0), outline=(0, 0, 0))
    topbar(img, score_at(t), pulse)
    captions(img, t)
    ImageDraw.Draw(img).text((540, 1880), "@Hirnalarm", font=font(38), fill=(255, 255, 255, 120), anchor="mm")
    out = img.convert("RGB")
    if shake != (0, 0):
        out = out.transform(out.size, Image.AFFINE, (1, 0, -shake[0], 0, 1, -shake[1]), fillcolor=(12, 8, 30))
    return out

def sfx_track(path):
    sr = 44100; n = int(TOTAL * sr) + sr; tr = np.zeros(n, dtype=np.float32)
    def add(sig, t0):
        i = int(t0 * sr); j = min(n, i + len(sig))
        if i < n: tr[i:j] += sig[: j - i]
    rng = np.random.default_rng(1)
    tt = np.arange(int(0.9 * sr)) / sr
    S_ = {
        "boom": (np.sin(2 * np.pi * (90 - 50 * tt) * tt) * np.exp(-tt * 5) + 0.4 * rng.standard_normal(len(tt)) * np.exp(-tt * 12)) * 0.75,
    }
    S_["boom_s"] = S_["boom"] * 0.55
    tw = np.arange(int(0.45 * sr)) / sr; S_["whoosh"] = rng.standard_normal(len(tw)) * np.sin(np.pi * tw / tw[-1]) * 0.22
    tb = np.arange(int(1.2 * sr)) / sr; S_["bell"] = (np.sin(2 * np.pi * 1320 * tb) + 0.5 * np.sin(2 * np.pi * 2640 * tb)) * np.exp(-tb * 4) * 0.25
    tp = np.arange(int(0.25 * sr)) / sr; S_["pop"] = np.sin(2 * np.pi * (500 + 1500 * tp) * tp) * np.exp(-tp * 18) * 0.35
    to = np.arange(int(0.5 * sr)) / sr; S_["boing"] = np.sin(2 * np.pi * (180 + 120 * np.sin(2 * np.pi * 9 * to)) * to) * np.exp(-to * 5) * 0.4
    S_["thud"] = S_["boom"][: int(0.3 * sr)] * 0.5
    for s, a, b in SEG:
        if s["scene"] == "banner": add(S_["bell"], a)
        if s["scene"] == "point": add(S_["pop"], a + 0.15 * (b - a))
        if s["scene"] == "intro": add(S_["whoosh"], a + 0.05)
        if s["scene"] == "win": add(S_["bell"], a); add(S_["pop"], a + 0.1)
    for t0, kind in SFX: add(S_[kind], t0)
    beat = 60 / 128; tk = np.arange(int(0.18 * sr)) / sr
    kick = np.sin(2 * np.pi * (120 - 80 * tk / tk[-1]) * tk) * np.exp(-tk * 20) * 0.22
    hat = rng.standard_normal(int(0.04 * sr)) * np.exp(-np.arange(int(0.04 * sr)) / sr * 90) * 0.05
    x = 0.0
    while x < TOTAL: add(kick, x); add(hat, x + beat / 2); x += beat
    tr = np.clip(tr, -1, 1)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes((tr * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    if len(sys.argv) > 4 and sys.argv[4] == "preview":
        for tt in [float(x) for x in sys.argv[5].split(",")]:
            frame(tt).save(f"prev_{tt:05.1f}.png")
        sys.exit()
    nframes = int(TOTAL * FPS)
    tmp = OUT + ".tmp.mp4"; sfx = OUT + ".sfx.wav"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    seen = set()
    for i in range(nframes):
        t = i / FPS
        s, u, a, b = seg_at(t)
        key = id(s)
        p.stdin.write(frame(t, collect_sfx=(key not in seen)).tobytes()); seen.add(key)
    p.stdin.close(); p.wait()
    sfx_track(sfx)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-i", AUDIO, "-i", sfx, "-filter_complex",
                    "[1:a]apad[v];[2:a]volume=0.9[s];[v][s]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], check=True)
    import os; os.remove(tmp); os.remove(sfx)
    print("done", OUT, round(TOTAL, 2))
