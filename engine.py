"""Hirnalarm Duell-Engine: rendert ein Obst-Duell aus einer Episoden-JSON + Stimme.
Usage: python3 engine.py episode.json voice.mp3 out.mp4 [preview t1,t2,...]
"""
import sys, math, random, subprocess, re, json, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
from render.figuren import *  # noqa: F401,F403  Figuren, Easing, font()
from render.figuren import FONT, font, sprite, KINDS, BASE_SC, PEEL, CROWN, OC
from render.ton import sfx_track as _sfx_track

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
if EP.get("bounds"):  # manuell gesetzte Phrasengrenzen (Pausen-Mitten), ueberschreibt die Automatik
    assert len(EP["bounds"]) == N - 1, f"bounds: {len(EP['bounds'])} statt {N - 1}"
    ends = list(EP["bounds"])
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
        WORDS.append((w_, t, t + dd, NCH, si)); t += dd
        if wi % 2 == 1 or wi == len(ws) - 1: NCH += 1
# Lautstärke pro Bild (für Mundbewegung der sprechenden Figur)
_pcm = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", AUDIO, "-ac", "1", "-ar", "6000", "-f", "s16le", "-"],
                                    capture_output=True).stdout, dtype=np.int16).astype(np.float32)
_hop = 6000 // FPS
ENV = np.array([np.sqrt(np.mean(_pcm[i:i + _hop] ** 2)) for i in range(0, max(1, len(_pcm) - _hop), _hop)]) if len(_pcm) > _hop else np.zeros(1)
ENV = ENV / (np.percentile(ENV, 95) + 1e-6)
# Mundstufen 0/1/2: leicht geglättet und relativ zur Umgebung, damit Silben sichtbar werden (kein Dauer-offen)
_slow = np.convolve(ENV, np.ones(9) / 9, mode="same")
MUND = []
for _i in range(len(ENV)):
    _g = 0.5 * (ENV[_i] + ENV[max(0, _i - 1)])
    MUND.append(0 if _g < 0.15 else (2 if (_g > 0.45 and _g > 0.95 * _slow[_i]) else 1))
for _i in range(1, len(MUND) - 1):  # einzelne Ausreißer-Bilder entfernen
    if MUND[_i - 1] == MUND[_i + 1] != MUND[_i]:
        MUND[_i] = MUND[_i - 1]
def mund_stufe(t):
    i = int(t * FPS)
    return MUND[i] if 0 <= i < len(MUND) else 0
if "preview" in sys.argv:
    for (si, p), (a_, b_) in zip(PHR, PH_T):
        print(f"{a_:6.2f}-{b_:6.2f} {SEGS[si]['scene']:8s} {p}", file=sys.stderr)


BELT = None

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
        if EP.get("belt"):
            global BELT
            if BELT is None: BELT = spr_belt()
            by = lerp(-200, ch["y"] - nh * 0.32, ease_out(cu / 0.3))
            bw = int(BELT.size[0] * clamp(nw / 420, 0.8, 1.15)); bh = int(BELT.size[1] * bw / BELT.size[0])
            b_ = BELT.resize((bw, bh), Image.BICUBIC)
            img.alpha_composite(b_, (int(ch["x"] - bw / 2), int(by - bh / 2)))
        else:
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
    sp = SEGS[WORDS[i][4]].get("speaker")  # Figurenstimme: Namensschild über dem Untertitel
    f_sp = next((f for f in EP["fighters"] if f.get("short") == sp), None) if sp else None
    if f_sp:
        lab = f_sp["short"].upper() + ":"
        lw = d.textlength(lab, font=font(58))
        d.rounded_rectangle([W / 2 - lw / 2 - 26, 1655, W / 2 + lw / 2 + 26, 1725], 22, fill=tuple(f_sp.get("color", [255, 255, 255])), outline=(0, 0, 0), width=6)
        d.text((W / 2, 1690), lab, font=font(58), fill=(20, 20, 20), anchor="mm")
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
                rot=0, expr="happy" if i == 0 else "angry", look=(1, 0) if i == 0 else (-1, 0), show=True, crack=(True if (f.get("crack") == "plaster" and t >= PLASTER_T) else f.get("crack", False)))

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
        if p.get("plaster_off"): ex.append(("plaster_fly", hV, FLOOR - 700, clamp((u - hit) / 0.5)))
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
    if p.get("peel"):
        pk = lerp(hV, postx, 0.45)
        if p.get("peel_u", 0) <= u < h: ex.append(("peel", pk, FLOOR, 0))
    return [(0.1, "whoosh"), (h, "boom_s")]

def act_spin(u, t, A, V, ai, p, ex):
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    if u < 0.45:
        A["x"] = lerp(hA, hV - dr * 230, ease_in(u / 0.45)); A["rot"] = u * 2400; A["expr"] = "grin"
    else:
        A["x"] = hV - dr * 230; A["rot"] = 0; A["expr"] = "grin"
        q = clamp((u - 0.45) / 0.45)
        V["y"] = FLOOR - math.sin(q * math.pi) * 450; V["x"] = lerp(hV, hV + dr * 120, q); V["expr"] = "shock"; V["rot"] = dr * -20 * math.sin(q * math.pi)
        ex.append(("burst", hV, 760, 170, p.get("word", "AUA!"), clamp((u - 0.45) / 0.5)))
        if p.get("leaves"): lu = p.get("leaves_u", 0.4); ex.append(("leaves", clamp((u - lu) / (1 - lu))))
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
        ex.append(("burst", (hV + edge) / 2, 780, 170, p.get("word", "KNALL!"), clamp((u - 0.38) / 0.45)))
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

def act_throw(u, t, A, V, ai, p, ex):
    # A spuckt/spritzt Projektile auf V (proj: seed | juice)
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    kind = p.get("proj", "seed"); n = 12; evs = []
    A["expr"] = "grin"; A["x"] = hA + dr * 40
    if kind == "juice": A["sx"] = 1 - 0.12 * abs(math.sin(u * 40)) * (0.1 < u < 0.6); A["sy"] = 1 + 0.08 * abs(math.sin(u * 40)) * (0.1 < u < 0.6)
    rnd = random.Random(42)
    first = 0.12 + 0.12
    for k in range(n):
        u0 = 0.12 + k * 0.035; q = (u - u0) / 0.12
        oy = rnd.uniform(-120, 120)
        if 0 <= q <= 1:
            x = lerp(hA + dr * 150, hV - dr * 40, q); y = lerp(FLOOR - 320, FLOOR - 280 + oy, q) - math.sin(q * math.pi) * 80
            ex.append(("proj", x, y, kind))
        if k % 3 == 0: evs.append((u0 + 0.12, "pop"))
    if u > first:
        jit = 14 * math.sin(t * 60) * (u < 0.6)
        V["x"] = hV + jit; V["expr"] = "shock" if u < 0.6 else ("sad" if kind == "juice" else "dizzy")
        V["rot"] = dr * 8 * math.sin(t * 25) * (u < 0.6)
        ex.append(("burst", 540, 760, 200, p.get("word", "RATATA!"), clamp((u - first) / 0.5)))
        if kind in ("slice", "cream"): ex.append(("stuck", V["x"], int(clamp((u - first) / 0.4) * 9), kind))
        ck = p.get("cherry", 0.62)
        if kind == "cream" and u > ck: ex.append(("cherry", V["x"], lerp(-100, FLOOR - 470, ease_out((u - ck) / 0.1))))
    return [(0.1, "whoosh")] + evs

def act_miss(u, t, A, V, ai, p, ex):
    # V springt auf A, A rollt weg, V steckt kopfueber im Ring. A = Gewinner
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    land = p.get("hit", 0.5); j0 = p.get("j0", 0.12)
    if u < j0:
        V["sy"] = 1 - 0.12 * ease_out(u / j0); V["expr"] = "angry"; A["expr"] = "shock"
    elif u < land:
        q = (u - j0) / (land - j0)
        V["x"] = lerp(hV, hA, q); V["y"] = FLOOR - 820 * math.sin(q * math.pi) + (220 * q * q if q > 0.7 else 0); V["rot"] = dr * 180 * ease_in(q); V["expr"] = "angry"
        r = clamp((u - j0 - 0.12) / (land - j0 - 0.17))
        A["x"] = lerp(hA, hV, ease_out(r)); A["rot"] = dr * 360 * r * 1.5; A["expr"] = "grin" if r > 0.3 else "shock"
    else:
        A["x"] = hV; A["expr"] = "grin"
        V["x"] = hA; V["y"] = FLOOR + 230; V["rot"] = dr * 180 + 7 * math.sin(t * 22); V["expr"] = "dizzy"
        if u < land + 0.08: ex.append(("shake", 24))
        ex.append(("burst", 540, 760, 230, p.get("word", "PLOPP!"), clamp((u - land) / 0.45)))
    return [(0.12, "whoosh"), (0.3, "whoosh"), (land, "boom")]


def act_roots(u, t, A, V, ai, p, ex):
    # A laesst Wurzeln aus dem Boden wachsen, die V festhalten
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    A["expr"] = "angry" if u < 0.2 else "grin"; A["sy"] = 1 - 0.06 * math.sin(clamp(u / 0.2) * math.pi)
    g = ease_out(clamp((u - 0.15) / 0.3))
    if u < 0.15:
        V["x"] = lerp(hV, hV - dr * 80, u / 0.15); V["expr"] = "angry"
    else:
        V["x"] = hV - dr * 80 + 12 * math.sin(t * 30) * (u > 0.4); V["expr"] = "shock" if u < 0.6 else "sad"
        V["rot"] = 6 * math.sin(t * 18) * (u > 0.4)
    ex.append(("roots", hV - dr * 80, g))
    if u > 0.3: ex.append(("burst", 540, 760, 200, p.get("word", "PACK!"), clamp((u - 0.3) / 0.5)))
    if 0.15 < u < 0.3: ex.append(("shake", 14))
    return [(0.15, "thud"), (0.3, "boom_s")]

def act_drop(u, t, A, V, ai, p, ex):
    # V nimmt Anlauf, A schuettelt sich, ein Ast faellt V auf den Kopf
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    hit = p.get("hit", 0.6)
    V["x"] = lerp(hV, hV + dr * 120, ease_out(clamp(u / 0.2)))
    if u < 0.2: V["expr"] = "angry"
    else: V["expr"] = "angry"; V["x"] = hV + dr * 120 - dr * 30 * math.sin(t * 20) * (u < hit)
    A["rot"] = 7 * math.sin(t * 45) * (0.22 < u < hit - 0.05); A["expr"] = "grin" if u > hit else "angry"
    vx = V["x"]
    if u < hit:
        q = clamp((u - (hit - 0.18)) / 0.18)
        if q > 0: ex.append(("branch", vx, lerp(-150, FLOOR - 520, ease_in(q)), 20 + 200 * q))
    else:
        V["sy"] = 0.7 + 0.3 * clamp((u - hit) / 0.4); V["sx"] = 1.25 - 0.25 * clamp((u - hit) / 0.4); V["expr"] = "dizzy"
        ex.append(("branch", vx - dr * 40, FLOOR - 30, 8 * dr))
        if u < hit + 0.08: ex.append(("shake", 24))
        ex.append(("burst", 540, 760, 230, p.get("word", "KLONK!"), clamp((u - hit) / 0.45)))
    return [(0.05, "whoosh"), (hit - 0.15, "whoosh"), (hit, "boom")]

def act_kickback(u, t, A, V, ai, p, ex):
    # V (Bananen) wirft Schale, A kickt sie zurueck, V rutscht selbst aus. A = Punktgewinner
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    k = p.get("kick", 0.4); slip = p.get("hit", 0.62)
    if u < k:
        q = clamp(u / k); px = lerp(hV, hA + dr * 120, q); py = FLOOR - 60 - math.sin(q * math.pi) * 380
        ex.append(("peel", px, py, q * 540)); V["expr"] = "grin"; A["expr"] = "shock" if q < 0.6 else "angry"
    elif u < slip:
        q = clamp((u - k) / (slip - k)); px = lerp(hA + dr * 120, hV, q); py = FLOOR - 60 - math.sin(q * math.pi) * 200
        ex.append(("peel", px, py if q < 1 else FLOOR, -q * 540)); A["expr"] = "grin"; A["rot"] = -dr * 20 * math.sin(clamp((u - k) / 0.1) * math.pi)
        V["expr"] = "shock"
        if u - k < 0.12: ex.append(("burst", hA + dr * 60, 900, 120, "KICK!", clamp((u - k) / 0.2)))
    else:
        q = clamp((u - slip) / 0.15); A["expr"] = "grin"
        V["rot"] = dr * 95 * ease_out(q); V["y"] = FLOOR - math.sin(q * math.pi) * 250 + 40 * q; V["expr"] = "dizzy"
        ex.append(("peel", hV + dr * 60, FLOOR, 0))
        if u < slip + 0.08: ex.append(("shake", 18))
        ex.append(("burst", 540, 760, 220, p.get("word", "RUTSCH!"), clamp((u - slip) / 0.4)))
    return [(0.03, "whoosh"), (k, "pop"), (slip, "thud")]

def act_bowl(u, t, A, V, ai, p, ex):
    # A rollt wie eine Bowlingkugel und raeumt V ab (Strike). A = Punktgewinner
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    hit = p.get("hit", 0.45)
    if u < 0.12:
        A["x"] = lerp(hA, hA - dr * 100, ease_out(u / 0.12)); A["expr"] = "angry"; A["sy"] = 0.9
    elif u < hit:
        q = (u - 0.12) / (hit - 0.12); A["x"] = lerp(hA - dr * 100, hV - dr * 60, ease_in(q)); A["rot"] = -dr * 1080 * q; A["expr"] = "grin"
        ex.append(("speed",))
    else:
        q = clamp((u - hit) / 0.3); A["x"] = lerp(hV - dr * 60, hV - dr * 160, ease_out(q)); A["rot"] = -dr * (1080 + 200 * q); A["expr"] = "grin"
        if u > hit + 0.3: A["rot"] = 0
        f = clamp((u - hit) / 0.4)
        V["x"] = lerp(hV, hV + dr * 140, f); V["y"] = FLOOR - math.sin(f * math.pi) * 650; V["rot"] = dr * 450 * ease_out(f) if f < 1 else dr * 90
        V["expr"] = "shock" if f < 1 else "dizzy"
        if f >= 1: V["y"] = FLOOR + 60
        if u < hit + 0.08: ex.append(("shake", 22))
        ex.append(("burst", 540, 760, 240, p.get("word", "STRIKE!"), clamp((u - hit) / 0.45)))
    return [(0.1, "whoosh"), (hit, "boom"), (hit + 0.4, "thud")]

def act_catapult(u, t, A, V, ai, p, ex):
    # V rennt auf A zu, A duckt sich, V fliegt in die Seile und wird aus der Halle geschleudert. A = Gewinner
    dr = 1 if ai == 0 else -1; hA, hV = HOME[ai], HOME[1 - ai]
    edge = 70 if ai == 0 else 1010; duck = p.get("duck", 0.3); rope = p.get("hit", 0.55)
    if u < rope - 0.1:
        q = u / (rope - 0.1); V["x"] = lerp(hV, edge, ease_in(q)); V["expr"] = "angry"; V["rot"] = dr * 15
        if q > 0.6: ex.append(("speed",))
    elif u < rope:
        q = (u - rope + 0.1) / 0.1; V["x"] = edge - dr * 40 * math.sin(q * math.pi); V["sx"] = 1 - 0.3 * math.sin(q * math.pi); V["expr"] = "shock"
        ex.append(("sag", 90 * math.sin(q * math.pi)))
    else:
        q = clamp((u - rope) / 0.3); V["x"] = lerp(edge, 540 - dr * 300, q); V["y"] = lerp(FLOOR, -700, ease_in(q)) - 400 * math.sin(q * math.pi)
        V["rot"] = -dr * 1000 * q; V["sc"] *= 1 - 0.5 * q; V["expr"] = "dizzy"
        if q >= 1: V["show"] = False
        ex.append(("burst", 540, 760, 230, p.get("word", "TSCHÜSS!"), clamp((u - rope - 0.1) / 0.45)))
    near = duck - 0.12 < u < rope
    A["sy"] = 0.55 if near else 1; A["expr"] = "grin" if (u > rope or near) else "shock"; A["y"] = FLOOR
    return [(0.05, "whoosh"), (rope - 0.08, "boing"), (rope + 0.05, "whoosh")]

ACTIONS = {"bowl": act_bowl, "catapult": act_catapult, "roots": act_roots, "drop": act_drop, "kickback": act_kickback, "race": act_race, "slam": act_slam, "post": act_post, "spin": act_spin, "headbutt": act_headbutt, "clash": act_clash, "throw": act_throw, "miss": act_miss}

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
GUEST = EP.get("guest")  # {kind, name, thanks}
GUEST_T = next((b for s, a, b in SEG if s["scene"] == "guest"), TOTAL)
TEASE_T = next((a for s, a, b in SEG if s["scene"] in ("win", "tease")), TOTAL)
PLASTER_T = next((a + (s.get("hit", 0.42) + 0.02) * (b - a) for s, a, b in SEG if s.get("plaster_off")), TOTAL)
BALD_T = next((a + (s.get("leaves_u", 0.4) + 0.1) * (b - a) for s, a, b in SEG if s.get("leaves")), TOTAL)
LEAVES = [(random.uniform(-200, 200), random.uniform(-80, 60), random.uniform(0.5, 1.4), random.uniform(0, 6)) for _ in range(40)]

def draw_guest(img, x, ybot, sc, bald, expr="happy", rot=0):
    spr, _ = sprite(GUEST["kind"], expr, (0, 0), bald)
    nw, nh = int(spr.size[0] * sc), int(spr.size[1] * sc)
    s = spr.resize((nw, nh), Image.BICUBIC)
    if rot: s = s.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(s, (int(x - s.size[0] / 2), int(ybot - s.size[1])))

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
    elif sc_ == "guest":
        for i_, xx in ((0, 120), (1, 960)):
            F[i_]["x"] = lerp(HOME[i_], xx, ease_out(u / 0.2)); F[i_]["sc"] *= 0.7; F[i_]["expr"] = "shock"; F[i_]["look"] = (0, -1)
        ex.append(("guest_front", u))
    elif sc_ == "table":
        F[0]["expr"] = F[1]["expr"] = "angry"; F[0]["look"] = (1, 0); F[1]["look"] = (-1, 0)
        ex.append(("table", s.get("title", "TABELLE"), s["rows"], u))
    elif sc_ == "banner":
        ex.append(("banner", s["label"], s.get("color", [255, 80, 80]), u))
        F[0]["expr"] = F[1]["expr"] = "angry"
        if s.get("shake"): ex.append(("shake", 6))
    elif sc_ == "action":
        ai = s["actor"]; A, V = F[ai], F[1 - ai]
        evs = ACTIONS[s["type"]](u, t, A, V, ai, s, ex)
        if s.get("replay"): ex.append(("replay", u))
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
            if s.get("card"): ex.append(("card", s["card"], u))
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

    if s.get("belt_on") is not None:  # Figur traegt (z. B. geklaut) den Guertel schon vor dem Sieg
        F[s["belt_on"]]["crown"] = 1
    shake = (0, 0)
    for e in ex:
        if e[0] == "shake": shake = (random.randint(-e[1], e[1]), random.randint(-e[1], e[1]))
    if any(e[0] == "speed" for e in ex): speed_lines(d, t)
    for e in ex:
        if e[0] == "peel":
            p_ = PEEL.rotate(e[3], expand=True); img.alpha_composite(p_, (int(e[1] - p_.size[0] / 2), int(e[2] - p_.size[1] + 40)))
    if GUEST and GUEST_T <= t < TEASE_T:
        bob = abs(math.sin(t * 9)) * 25 if sc_ == "point" else 0
        gex = "grin" if sc_ == "point" else ("shock" if sc_ == "action" else "happy")
        draw_guest(img, 540, FLOOR - 170 - bob, 0.55, (t >= BALD_T) or GUEST.get("crack", False), gex, 4 * math.sin(t * 2))
    # draw lower (airborne) last
    sp_ = s.get("speaker")
    if sp_:
        for i_, f_ in enumerate(FIGHTERS):
            st_ = mund_stufe(t)
            if f_.get("short") == sp_ and F[i_]["expr"] not in ("dizzy",) and st_:
                F[i_]["expr"] = f"{F[i_]['expr']}_t{st_}"
    for ch in sorted(F, key=lambda c: -c["y"]): paste_char(img, ch)
    d = ImageDraw.Draw(img)
    for e in ex:
        if e[0] == "proj":
            x, y = e[1], e[2]
            if e[3] == "slice":
                a_ = t * 25 + x * 0.05
                d.ellipse([x - 30, y - 30, x + 30, y + 30], fill=(70, 150, 60), outline=OC, width=4)
                d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(190, 230, 150))
                for kk in range(5):
                    b_ = a_ + kk * 2 * math.pi / 5; d.ellipse([x + 11 * math.cos(b_) - 3, y + 11 * math.sin(b_) - 4, x + 11 * math.cos(b_) + 3, y + 11 * math.sin(b_) + 4], fill=(240, 250, 210), outline=(90, 140, 60))
            elif e[3] == "cream":
                d.ellipse([x - 30, y - 22, x + 30, y + 22], fill=(255, 255, 255), outline=(200, 200, 210), width=4)
                d.ellipse([x - 12, y - 34, x + 14, y - 8], fill=(255, 255, 255), outline=(200, 200, 210), width=3)
            elif e[3] == "juice":
                d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(255, 240, 80), outline=(200, 170, 20), width=4)
            else:
                d.ellipse([x - 11, y - 17, x + 11, y + 17], fill=(35, 25, 20), outline=(255, 255, 255), width=3)
        elif e[0] == "roots":
            rx, g = e[1], e[2]
            for k_, off in enumerate((-150, -80, 0, 80, 150)):
                L = g * (420 - abs(off) * 0.9); pts = []
                for j in range(14):
                    q = j / 13; pts.append((rx + off + 40 * math.sin(q * 6 + k_ + t * 3) * q - off * 0.5 * q, FLOOR + 20 - L * q))
                if L > 5:
                    d.line(pts, fill=OC, width=34, joint="curve"); d.line(pts, fill=(120, 80, 45), width=24, joint="curve")
            d.ellipse([rx - 230, FLOOR - 20, rx + 230, FLOOR + 30], fill=(90, 60, 30))
        elif e[0] == "branch":
            bx, by, ang = e[1], e[2], e[3]
            br = Image.new("RGBA", (420, 120), (0, 0, 0, 0)); bd_ = ImageDraw.Draw(br)
            bd_.rounded_rectangle([10, 35, 410, 85], 25, fill=(245, 245, 238), outline=OC, width=7)
            for xx in (80, 170, 290, 350): bd_.rounded_rectangle([xx, 50, xx + 35, 62], 5, fill=(40, 35, 35))
            bd_.line([(300, 40), (360, 5)], fill=OC, width=10)
            br = br.rotate(ang, expand=True, resample=Image.BICUBIC)
            img.alpha_composite(br, (int(bx - br.size[0] / 2), int(by - br.size[1] / 2))); d = ImageDraw.Draw(img)
        elif e[0] == "stuck":
            rnd = random.Random(77)
            for _ in range(e[2]):
                x, y = e[1] + rnd.uniform(-140, 140), rnd.uniform(FLOOR - 560, FLOOR - 120)
                if len(e) > 3 and e[3] == "cream":
                    d.ellipse([x - 48, y - 36, x + 48, y + 36], fill=(255, 255, 255), outline=(190, 190, 200), width=4)
                    d.ellipse([x - 22, y - 58, x + 26, y - 14], fill=(255, 255, 255), outline=(190, 190, 200), width=3)
                    continue
                d.ellipse([x - 26, y - 26, x + 26, y + 26], fill=(70, 150, 60), outline=OC, width=4)
                d.ellipse([x - 18, y - 18, x + 18, y + 18], fill=(190, 230, 150))
        elif e[0] == "cherry":
            x, y = e[1], e[2]
            d.line([(x, y - 40), (x + 30, y - 95)], fill=(60, 120, 40), width=8)
            d.ellipse([x - 38, y - 40, x + 38, y + 36], fill=(220, 20, 40), outline=OC, width=6)
            d.ellipse([x - 20, y - 26, x - 4, y - 10], fill=(255, 160, 170))
        elif e[0] == "plaster_fly":
            q = e[3]
            if 0 < q < 1:
                pl = spr_plaster().rotate(q * 900, expand=True)
                img.alpha_composite(pl, (int(e[1] + 500 * q - pl.size[0] / 2), int(e[2] - 500 * math.sin(q * math.pi) + 600 * q * q - pl.size[1] / 2))); d = ImageDraw.Draw(img)
        elif e[0] == "leaves":
            for lx, ly, v, ph in LEAVES:
                q = e[1]; yy = FLOOR - 170 - 0.55 * 700 + ly + v * 900 * q; xx = 540 + lx * (1 + q) + 40 * math.sin(t * 6 + ph)
                if q > 0 and yy < FLOOR + 300:
                    d.ellipse([xx - 18, yy - 10, xx + 18, yy + 10], fill=(140, 210, 70), outline=(50, 110, 40), width=3)
        elif e[0] == "guest_front":
            uu = e[1]
            draw_guest(img, 540, lerp(H + 200, FLOOR + 160, back_out(uu / 0.3)), 0.95, GUEST.get("crack", False), "grin", 5 * math.sin(t * 5))
            dd = ImageDraw.Draw(img)
            text_c(dd, (540, 420), GUEST["name"].upper(), font(min(100, 1700 / max(8, len(GUEST["name"]))) * back_out(uu / 0.25)), fill=(150, 230, 90), stroke=12)
            if GUEST.get("thanks") and uu > 0.3:
                k = back_out((uu - 0.3) / 0.2)
                l1, l2 = (GUEST["thanks"].split("|") + [""])[:2]
                dd.rounded_rectangle([90, 490, 990, 680], 34, fill=(255, 255, 255), outline=(0, 0, 0), width=8)
                fs = 70
                while dd.textlength(l1, font=font(fs)) > 840: fs -= 2
                text_c(dd, (540, 545), l1, font(fs * k), fill=(30, 30, 40), stroke=0)
                text_c(dd, (540, 625), l2, font(64 * k), fill=(230, 30, 50), stroke=0)
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
        elif k == "table":
            title, rows, uu = e[1], e[2], e[3]; k_ = back_out(clamp(uu / 0.2))
            lay = Image.new("RGBA", (920, 150 + 92 * len(rows)), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
            dl.rounded_rectangle([0, 0, lay.size[0] - 1, lay.size[1] - 1], 36, fill=(20, 12, 45, 235), outline=(255, 255, 255), width=7)
            text_c(dl, (460, 70), title, font(66), fill=(255, 230, 0), stroke=6)
            for ri, row in enumerate(rows):
                y = 165 + ri * 92; hl = row[0] in [f["short"] for f in FIGHTERS]
                if hl: dl.rounded_rectangle([20, y - 40, 900, y + 40], 20, fill=(230, 30, 50, 255))
                text_c(dl, (80, y), f"{ri + 1}.", font(52), stroke=5)
                dl.text((150, y), row[0].upper(), font=font(52), fill="white", anchor="lm", stroke_width=5, stroke_fill=(0, 0, 0))
                text_c(dl, (760, y), f"{row[1]} - {row[2]}", font(52), fill=(255, 230, 0) if hl else "white", stroke=5)
            if k_ < 0.999 or k_ > 1.001:
                ns = (max(1, int(lay.size[0] * k_)), max(1, int(lay.size[1] * k_))); lay = lay.resize(ns, Image.BICUBIC)
            img.alpha_composite(lay, (W // 2 - lay.size[0] // 2, 360))
        elif k == "card":
            lines, uu = e[1], e[2]; k_ = back_out(clamp(uu / 0.2)); dd = ImageDraw.Draw(img)
            hgt = 110 + 78 * (len(lines) - 1)
            dd.rounded_rectangle([60, 380, 1020, 380 + hgt], 34, fill=(255, 255, 255), outline=(0, 0, 0), width=8)
            text_c(dd, (540, 430), lines[0], font(60 * k_), fill=(230, 30, 50), stroke=0)
            for li_, ln in enumerate(lines[1:]):
                fs = 52
                while dd.textlength(ln, font=font(fs)) > 900: fs -= 2
                text_c(dd, (540, 510 + 78 * li_), ln, font(fs * k_), fill=(30, 30, 40), stroke=0)
        elif k == "replay":
            dd = ImageDraw.Draw(img, "RGBA")
            dd.rectangle([24, 345, W - 24, H - 290], outline=(255, 255, 255), width=6)
            if int(t * 3) % 2 == 0: dd.ellipse([70, 365, 115, 410], fill=(230, 30, 50, 255))
            dd.text((135, 388), "ZEITLUPE", font=font(58), fill=(255, 255, 255), anchor="lm", stroke_width=6, stroke_fill=(0, 0, 0))
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
    _sfx_track(path, TOTAL, SEG, SFX)

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
