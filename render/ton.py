"""Soundeffekte und Beat der Hirnalarm-Engine."""
import wave
import numpy as np


def sfx_track(path, TOTAL, SEG, SFX):
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

