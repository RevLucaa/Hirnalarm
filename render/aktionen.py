"""Figuren-Ausgangszustand und alle Aktionen (Schlag, Wurf, Rennen …).
Episodenabhängige Werte setzt engine.py über einrichten(), bevor das erste Bild gerechnet wird."""
import math
import random

from render.figuren import BASE_SC, clamp, ease_in, ease_out, lerp
from render.kulissen import FLOOR, W

HOME = [300, 790]
FIGHTERS = []           # aus der Episode
PLASTER_T = float("inf")  # Zeitpunkt, ab dem Kalles Pflaster ab ist


def einrichten(fighters, plaster_t):
    global FIGHTERS, PLASTER_T
    FIGHTERS = fighters
    PLASTER_T = plaster_t


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
