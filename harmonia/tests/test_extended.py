# harmonia/tests/test_extended.py  —  python harmonia/tests/test_extended.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
from harmonia.dsp.chroma import FS, N, analyze_frame
from harmonia.dsp.chords import TYPES, NOTE_NAMES, detect_chord, chord_intervals, CANON
from harmonia.dsp.smoother import ChordSmoother

rng = np.random.default_rng(3)
t = np.arange(N) / FS


def synth(root, ivs, weights=None, nh=8, base=130.81, noise=0.002):
    sig = np.zeros(N)
    for k, iv in enumerate(ivs):
        a = 1.0 if weights is None else weights[k]
        f = base * 2 ** (((root + iv) % 12 + (12 if (root + iv) % 12 < root else 0)) / 12) * (1 if k else 1)
        f = base * 2 ** ((root + iv) / 12)
        while f > 400: f /= 2
        for h in range(1, nh + 1):
            sig += a * (1 / h) * np.sin(2 * np.pi * f * h * t + rng.uniform(0, 6.28))
    sig = sig / np.max(np.abs(sig)) * 0.2 + rng.normal(0, noise, N)
    return sig.astype(np.float32)


def detect(x):
    return detect_chord(analyze_frame(x)[0])[0]


# 1) всі типи × кілька коренів
bad = 0
for suf in TYPES:
    for root in (0, 2, 4, 7, 9, 10):
        if suf in CANON and root >= 0:
            pass
        got = detect(synth(root, chord_intervals(suf)))
        exp = NOTE_NAMES[root] + suf
        ok = got == exp
        if not ok and suf in ("dim7", "aug", "sus2"):      # еквівалентні набори нот
            from harmonia.dsp.chords import pcset
            ok = got is not None and pcset(got) == pcset(exp)
        if not ok:
            bad += 1; print("FAIL", exp, "->", got)
print(f"типи: {66 - bad}/66")

# 2) тризвук із 'протіканням' гармонік НЕ має ставати септакордом
for root in (0, 5, 7, 9):
    for suf in ("", "m"):
        got = detect(synth(root, chord_intervals(suf), nh=14))
        assert got == NOTE_NAMES[root] + suf, (root, suf, got)
print("тризвуки з багатими гармоніками: OK")

# 3) септакорд зі слабкою 7-ю (0.3) -> тризвук, з нормальною (0.8) -> септакорд
w_weak, w_ok = [1, 1, .8, .3], [1, 1, .8, .8]
assert detect(synth(7, [0, 4, 7, 10], w_weak)) == "G", detect(synth(7, [0, 4, 7, 10], w_weak))
assert detect(synth(7, [0, 4, 7, 10], w_ok)) == "G7"
print("штраф/поріг септими: OK")

# 4) пауер-акорд vs тризвук
assert detect(synth(4, [0, 7])) == "E5"
print("пауер-акорд: OK")

# 5) стабільність: C <-> Cmaj7 мерехтіння не змінює акорд
sm = ChordSmoother()
out = [sm.update(c) for c in ["C"] * 6 + ["Cmaj7", "C", "Cmaj7", "C", "Cmaj7", "Cmaj7", "C"]]
assert set(out) - {None} == {"C"}, out
sm = ChordSmoother()
out = [sm.update(c) for c in ["C"] * 6 + ["Cmaj7"] * 8]
assert out[-1] == "Cmaj7"
print("smoother (споріднені): OK")

# 6) теорія кола для розширених акордів
from harmonia.theory.circle import estimate_key, neighbors, role_in_key, chord_ring_pos
from harmonia.theory.instruments import advise, guitar_shapes, bass_advice
k = estimate_key(["C", "F", "G7"])
n = neighbors("G7", k)
assert n[0]["chord"] == "C" and n[0]["priority"] and "тоніку" in n[0]["label"], n[0]       # G7 -> C найвищий пріоритет
assert chord_ring_pos("G7") == chord_ring_pos("G") == chord_ring_pos("Gsus4")               # той самий сектор
assert chord_ring_pos("Am7") == chord_ring_pos("Am")
km = estimate_key(["Am", "Dm", "E7", "Am"])
assert km["name"] == "A minor" and role_in_key("E7", km).startswith("V7")                   # гармонічна домінанта
assert role_in_key("Bdim", estimate_key(["C", "G", "Bdim"])) == "vii°"
b = bass_advice("G7", n, k)
assert b["seventh"] == "F" and "F" in b["to_next"][0]["line"]                               # септима в басовій лінії
for name in ("C7", "A7", "G7", "E7", "D7", "Am7", "Em7", "Dm7", "Cmaj7", "Fmaj7"):
    assert guitar_shapes(name)[0]["shape"] == "відкрита", name                              # відкриті позиції
for name in ("Csus4", "Bdim", "Caug", "F#sus2", "Bdim7", "G5"):
    assert guitar_shapes(name), name                                                        # баре/рухомі форми
print("теорія/інструменти (розширені акорди): OK")
