# harmonia/tests/test_live.py  — python harmonia/tests/test_live.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
from harmonia.dsp.chroma import FS, HOP, N
from harmonia.io.mic_source import RingBuffer
from harmonia.engine import RealtimeEngine
from harmonia.theory.circle import estimate_key, neighbors, circle_pos
from harmonia.theory.instruments import advise

FREQS = {"C": [261.63, 329.63, 392.00], "G": [196.00, 246.94, 293.66],
         "Am": [220.00, 261.63, 329.63], "F": [174.61, 220.00, 261.63]}
rng = np.random.default_rng(0)


def tone(chord, sec, amp=0.25):
    t = np.arange(int(sec * FS)) / FS
    s = sum((1 / h) * np.sin(2 * np.pi * f * h * t) for f in FREQS[chord] for h in range(1, 5))
    env = np.minimum(1, t / 0.01) * np.exp(-t * 0.5)          # атака 10 мс + затухання
    return (amp * s / np.max(np.abs(s)) * env).astype(np.float32)


# --- теорія ---
assert circle_pos(0) == 0 and circle_pos(7) == 1 and circle_pos(5) == 11   # C, G, F
assert [n["chord"] for n in neighbors("C")] == ["F", "G", "Am"]
k = estimate_key(["C", "Am", "F", "G"]);  assert k["name"] == "C major", k
k = estimate_key(["Am", "F", "C", "G", "Am"]); assert k["name"] == "A minor", k
a = advise("G", estimate_key(["C", "F", "G"]))
assert a["role"] == "V" and a["instruments"]["solo"]["mode"]["name"] == "G Mixolydian"
print("theory OK")

# --- ring buffer ---
rb = RingBuffer(1000)
x = np.arange(5000, dtype=np.float32)
for i in range(0, 5000, 333):
    rb.write(x[i:i + 333])
assert np.array_equal(rb.read(5000, 700), x[4300:5000])
print("ring OK")

# --- повний конвеєр: шум кімнати -> C -> G -> Am -> F ---
sig = [rng.normal(0, 0.002, int(1.4 * FS)).astype(np.float32)]
for ch in ["C", "G", "Am", "F"]:
    sig.append(tone(ch, 2.0) + rng.normal(0, 0.002, int(2.0 * FS)).astype(np.float32))
sig = np.concatenate(sig)
rb = RingBuffer(N * 4)
eng = RealtimeEngine()
changes = []
pos = 0
while pos + HOP <= len(sig):                    # імітація callback-блоків по 512
    for j in range(0, HOP, 512):
        rb.write(sig[pos + j:pos + j + 512])
    pos += HOP
    if rb.written >= N:
        ev = eng.process_frame(rb.read(rb.written, N))
        if ev["changed"]:
            changes.append((round(pos / FS, 2), ev["stable"]))
print("gate =", round(eng.gate, 4), "changes:", changes)
seq = [c for _, c in changes if c]
assert seq == ["C", "G", "Am", "F"], seq
print("pipeline OK")
