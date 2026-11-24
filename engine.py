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

from render.kulissen import FLOOR, make_bg, front_ropes, bahn_vorne, ziellinie, netz_davor, fussball
BAHN_ARENA = EP.get("arena") == "bahn"
FUSS_ARENA = EP.get("arena") == "fussball"
BG = make_bg(EP)

# ============ draw helpers ============
def paste_char(img, ch):
    if not ch["show"]: return
    spr, headx = sprite(ch["kind"], ch["expr"], ch["look"], ch.get("crack", False))
    sc = ch["sc"]
    nw, nh = max(1, int(spr.size[0] * sc * ch["sx"])), max(1, int(spr.size[1] * sc * ch["sy"]))
    s = spr.resize((nw, nh), Image.BICUBIC)
    if ch.get("flip"): s = s.transpose(Image.FLIP_LEFT_RIGHT); headx = -headx
    if ch["rot"]: s = s.rotate(ch["rot"], expand=True, resample=Image.BICUBIC)
    boden = ch.get("boden", FLOOR)
    if ch["y"] >= boden - 400:
        sw = nw * 0.42 * clamp(1 - (boden - ch["y"]) / 500)
        ImageDraw.Draw(img, "RGBA").ellipse([ch["x"] - sw, boden - 16, ch["x"] + sw, boden + 16], fill=(0, 0, 0, 70))
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
def splash(d, cx, cy, u, farbe=(250, 250, 245)):
    if u <= 0 or u > 1: return
    for vx, vy, r_ in SPLASH:
        x = cx + vx * 700 * u; y = cy + vy * 700 * u + 1400 * u * u
        d.ellipse([x - r_, y - r_, x + r_, y + r_], fill=tuple(farbe), outline=tuple(int(c * 0.8) for c in farbe))

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
    f_sp = next((f for f in EP["fighters"] + EP.get("nebenrollen", []) if f.get("short") == sp), None) if sp else None
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
SFX = []  # (time, kind)

from render import aktionen as _akt
from render.aktionen import ACTIONS, HOME, base_state  # noqa: F401


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
_akt.einrichten(FIGHTERS, PLASTER_T)
BALD_T = next((a + (s.get("leaves_u", 0.4) + 0.1) * (b - a) for s, a, b in SEG if s.get("leaves")), TOTAL)
LEAVES = [(random.uniform(-200, 200), random.uniform(-80, 60), random.uniform(0.5, 1.4), random.uniform(0, 6)) for _ in range(40)]

def draw_guest(img, x, ybot, sc, bald, expr="happy", rot=0):
    spr, _ = sprite(GUEST["kind"], expr, (0, 0), bald)
    nw, nh = int(spr.size[0] * sc), int(spr.size[1] * sc)
    s = spr.resize((nw, nh), Image.BICUBIC)
    if rot: s = s.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(s, (int(x - s.size[0] / 2), int(ybot - s.size[1])))

# ============ Kamera und Übergänge ============
def _weich(x):
    x = clamp(x); return x * x * (3 - 2 * x)

# Aktionen direkt nach einem „FINALE“-Banner bekommen den stärkeren Ruck
FINALE_IDS = {id(SEGS[i + 1]) for i, s_ in enumerate(SEGS[:-1]) if s_["scene"] == "banner" and "FINAL" in str(s_.get("label", "")).upper()}

def kamera(img, t, s, u, a, b, F, evs):
    """Zoom auf die sprechende Figur bzw. den Sieger, Ruck bei Treffern im Finale, Wackeln bei Treffern."""
    dauer = max(0.3, b - a); z, fx, fy = 1.0, W / 2, FLOOR - 300
    rein = _weich((t - a) / 0.35) * _weich((b - t) / 0.3)  # weich rein und raus
    sp_ = s.get("speaker")
    ziel = next((i for i, f in enumerate(FIGHTERS) if f.get("short") == sp_), None) if sp_ else None
    if ziel is not None and F[ziel].get("show", True) and 120 < F[ziel]["x"] < W - 120 and F[ziel]["y"] < FLOOR + 60:
        z, fx, fy = 1 + 0.12 * rein, F[ziel]["x"], F[ziel]["y"] - 260
    elif s["scene"] == "win":
        w = s.get("side", 0)
        z, fx, fy = 1 + 0.16 * _weich((t - a) / 1.2), F[w]["x"], F[w]["y"] - 280
    dx = dy = 0.0
    for uu, kind in evs:  # Treffer: kurzer Zoom-Ruck + Wackeln, abklingend
        dt = (u - uu) * dauer
        if 0 <= dt < 0.35 and kind in ("boom", "boom_s", "thud"):
            k = (1 - dt / 0.35) ** 2 * (1.0 if kind == "boom" else 0.5)
            finale = 1.6 if id(s) in FINALE_IDS else 1.0
            z += 0.06 * k * finale
            dx += math.sin(t * 90) * 16 * k * finale; dy += math.cos(t * 77) * 12 * k * finale
    if z <= 1.001 and not dx and not dy:
        return img
    fx = clamp(fx, W / 2 / z + 1, W - W / 2 / z - 1) if z > 1 else W / 2
    cy = clamp(fy, H / 2 / z, H - H / 2 / z)
    # Bild so transformieren, dass (fx, cy) in die Mitte rückt und um z vergrößert wird
    ox, oy = fx - W / (2 * z), cy - H / (2 * z)
    ox = clamp(ox, 0, W - W / z); oy = clamp(oy, 0, H - H / z)
    return img.transform(img.size, Image.AFFINE, (1 / z, 0, ox + dx / z, 0, 1 / z, oy + dy / z), resample=Image.BILINEAR)

def blitz(img, t, s, a):
    """Kurzer weißer Blitz als Übergang beim Rundenbanner und beim Sieg."""
    if s["scene"] in ("banner", "win") and 0 <= t - a < 0.16:
        al = int(170 * (1 - (t - a) / 0.16))
        img.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, al)))

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
        evs = ACTIONS[s["type"]](u, t, A, V, ai, s, ex) or []
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
        if e[0] == "ziel": ziellinie(d, e[1])
        elif e[0] == "puddle":
            rnd_ = random.Random(5)
            for _ in range(9):
                px_ = e[1] + rnd_.uniform(-e[2], e[2]); w_ = rnd_.uniform(50, 95)
                d.ellipse([px_ - w_, FLOOR - 18, px_ + w_, FLOOR + 22], fill=(255, 255, 255), outline=(200, 200, 210), width=4)
    for e in ex:
        if e[0] == "peel":
            p_ = PEEL.rotate(e[3], expand=True); img.alpha_composite(p_, (int(e[1] - p_.size[0] / 2), int(e[2] - p_.size[1] + 40)))
    if GUEST and GUEST_T <= t < TEASE_T and not (BAHN_ARENA and sc_ == "action" and s.get("type") in ("propeller", "surf", "huepf")):
        bob = abs(math.sin(t * 9)) * 25 if sc_ == "point" else 0
        gex = "grin" if sc_ == "point" else ("shock" if sc_ == "action" else "happy")
        draw_guest(img, GUEST.get("x", 540), FLOOR - 170 - bob, 0.55, (t >= BALD_T) or GUEST.get("crack", False), gex, 4 * math.sin(t * 2))
    # draw lower (airborne) last
    sp_ = s.get("speaker")
    if sp_:
        for i_, f_ in enumerate(FIGHTERS):
            st_ = mund_stufe(t)
            if f_.get("short") == sp_ and F[i_]["expr"] not in ("dizzy",) and st_:
                F[i_]["expr"] = f"{F[i_]['expr']}_t{st_}"
                F[i_]["sy"] *= 1 + 0.025 * st_  # leichtes Mitwippen beim Sprechen
    for i_ in range(2):  # Blinzeln: etwa alle 3–4 s für 0,12 s, beide Figuren versetzt
        if F[i_]["expr"].split("_")[0] in ("happy", "angry", "grin", "sad") and (t + 1.7 * i_) % (3.3 + 0.6 * i_) < 0.12:
            F[i_]["expr"] += "_b"
    for ch in sorted(F, key=lambda c: c.get("z", -c["y"])): paste_char(img, ch)
    d = ImageDraw.Draw(img)
    for e in ex:
        if e[0] == "netz": netz_davor(d, e[1], e[2], e[3])
        elif e[0] == "ball": fussball(d, e[1], e[2], e[3], e[4])
        elif e[0] == "fetzen":
            q = e[3]; rnd_ = random.Random(9)
            for _ in range(12):
                ang = rnd_.uniform(0, 2 * math.pi); v = rnd_.uniform(150, 380)
                fx_, fy_ = e[1] + math.cos(ang) * v * q, e[2] + math.sin(ang) * v * q + 500 * q * q
                if q < 1: d.polygon([(fx_ - 16, fy_ - 10), (fx_ + 14, fy_ - 14), (fx_ + 10, fy_ + 12)], fill=(250, 250, 250) if rnd_.random() < 0.6 else (25, 25, 30), outline=(20, 20, 25))
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
        elif e[0] == "tuch":  # Handtuch (ab 1.7.0): fliegend (e[4]=0) oder im Gesicht (e[4]=1)
            tw_ = Image.new("RGBA", (240, 170), (0, 0, 0, 0)); td_ = ImageDraw.Draw(tw_)
            td_.rounded_rectangle([8, 8, 232, 162], 22, fill=(250, 250, 248), outline=OC, width=7)
            for yy in (40, 130): td_.line([(14, yy), (226, yy)], fill=(80, 150, 230), width=10)
            if e[4]: tw_ = tw_.resize((280, 200), Image.BICUBIC)
            tw_ = tw_.rotate(e[3], expand=True, resample=Image.BICUBIC)
            img.alpha_composite(tw_, (int(e[1] - tw_.size[0] / 2), int(e[2] - tw_.size[1] / 2))); d = ImageDraw.Draw(img)
        elif e[0] == "stuck":
            rnd = random.Random(77)
            for _ in range(e[2]):
                x, y = e[1] + rnd.uniform(-140, 140), rnd.uniform(FLOOR - 560, FLOOR - 120)
                if len(e) > 3 and e[3] == "seed":
                    for k_ in range(3):
                        sx_, sy_ = x + rnd.uniform(-40, 40), y + rnd.uniform(-40, 40)
                        d.ellipse([sx_ - 8, sy_ - 12, sx_ + 8, sy_ + 12], fill=(250, 220, 60), outline=OC, width=3)
                    continue
                if len(e) > 3 and e[3] == "cream":
                    d.ellipse([x - 48, y - 36, x + 48, y + 36], fill=(255, 255, 255), outline=(190, 190, 200), width=4)
                    d.ellipse([x - 22, y - 58, x + 26, y - 14], fill=(255, 255, 255), outline=(190, 190, 200), width=3)
                    continue
                d.ellipse([x - 26, y - 26, x + 26, y + 26], fill=(70, 150, 60), outline=OC, width=4)
                d.ellipse([x - 18, y - 18, x + 18, y + 18], fill=(190, 230, 150))
        elif e[0] == "klecks":  # Sahne-Klecks im Gesicht (ab 1.8.0)
            x, y, r_ = e[1], e[2], e[3]; rnd_ = random.Random(31)
            for _ in range(6):
                ox, oy, rr = rnd_.uniform(-0.6, 0.6) * r_, rnd_.uniform(-0.4, 0.5) * r_, rnd_.uniform(0.35, 0.55) * r_
                d.ellipse([x + ox - rr, y + oy - rr, x + ox + rr, y + oy + rr], fill=(255, 255, 255), outline=(195, 195, 205), width=4)
            d.ellipse([x - 0.5 * r_, y - 0.35 * r_, x + 0.5 * r_, y + 0.35 * r_], fill=(255, 255, 255))
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
    if BAHN_ARENA: bahn_vorne(d, t, any(e[0] == "lauf" for e in ex))
    elif not FUSS_ARENA: front_ropes(d, sag)
    img = kamera(img, t, s, u, a, b, F, evs if sc_ == "action" else [])
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
        elif k == "zielfoto":
            dd = ImageDraw.Draw(img, "RGBA")
            if e[1] < 0.12: img.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, int(220 * (1 - e[1] / 0.12))))); dd = ImageDraw.Draw(img, "RGBA")
            dd.rectangle([24, 345, W - 24, H - 290], outline=(255, 255, 255), width=8)
            text_c(dd, (540, 420), "ZIELFOTO", font(80), fill=(255, 230, 0), stroke=8)
        elif k == "splash": splash(ImageDraw.Draw(img), e[1], e[2], e[3], *(e[4:5]))
        elif k == "big" and e[2] > 0:
            text_c(ImageDraw.Draw(img), (540, 560), e[1], font(190 * back_out(e[2] / 0.4)), fill=(255, 230, 0), stroke=14)
        elif k == "cta":
            uu = e[1]; dd = ImageDraw.Draw(img); s_ = back_out(uu / 0.25)
            dd.rounded_rectangle([90, 470, 990, 700], 40, fill=(230, 30, 50), outline=(0, 0, 0), width=10)
            text_c(dd, (540, 540), e[2], font(min(80, 1500 / max(10, len(e[2]))) * s_), stroke=8)
            text_c(dd, (540, 635), e[3], font(min(96, 1500 / max(8, len(e[3]))) * s_), fill=(255, 230, 0), stroke=8)
            ay = 790 + 25 * math.sin(t * 8)
            dd.polygon([(500, ay), (580, ay), (580, ay + 70), (630, ay + 70), (540, ay + 150), (450, ay + 70), (500, ay + 70)], fill=(255, 230, 0), outline=(0, 0, 0))
    blitz(img, t, s, a)
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
