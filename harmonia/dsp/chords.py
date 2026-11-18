# harmonia/dsp/chords.py
"""Класифікація акордів: 11 типів × 12 коренів, зважені шаблони + штрафне зіставлення."""
import numpy as np

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# w    — ваги напівтонових інтервалів (тоніка й характерний інтервал найважчі);
# core — ноти, що МУСЯТЬ бути в спектрі; ext — нота-розширення (7-ма), перевіряється окремо;
# pen  — штраф «складності»: септакорд обирається лише якщо виграє у тризвука з запасом;
# forbid — (інтервали, поріг): ці ноти НЕ мають звучати (пауер-акорд без терції тощо).
TYPES = {
    "":     dict(w={0: 1.0, 4: 1.0, 7: 0.8}, core=(0, 4, 7), ext=None, pen=0.00),
    "m":    dict(w={0: 1.0, 3: 1.0, 7: 0.8}, core=(0, 3, 7), ext=None, pen=0.00),
    "7":    dict(w={0: 1.0, 4: 0.9, 7: 0.6, 10: 1.0}, core=(0, 4), ext=10, pen=0.03),
    "maj7": dict(w={0: 1.0, 4: 0.9, 7: 0.6, 11: 1.0}, core=(0, 4), ext=11, pen=0.03),
    "m7":   dict(w={0: 1.0, 3: 0.9, 7: 0.6, 10: 1.0}, core=(0, 3), ext=10, pen=0.03),
    "sus2": dict(w={0: 1.0, 2: 1.0, 7: 0.8}, core=(0, 2, 7), ext=None, pen=0.03, forbid=((3, 4), 0.45)),
    "sus4": dict(w={0: 1.0, 5: 1.0, 7: 0.8}, core=(0, 5, 7), ext=None, pen=0.02, forbid=((3, 4), 0.45)),
    "dim":  dict(w={0: 1.0, 3: 1.0, 6: 1.0}, core=(0, 3, 6), ext=None, pen=0.03),
    "dim7": dict(w={0: 1.0, 3: 1.0, 6: 1.0, 9: 1.0}, core=(0, 3, 6), ext=9, pen=0.04),
    "aug":  dict(w={0: 1.0, 4: 1.0, 8: 1.0}, core=(0, 4, 8), ext=None, pen=0.04),
    "5":    dict(w={0: 1.0, 7: 1.0}, core=(0, 7), ext=None, pen=0.02, forbid=((3, 4), 0.35)),
}
CANON = {"dim7": 3, "aug": 4}       # симетричні акорди: однакові ноти в 3–4 коренях -> лише канонічні
SUFFIXES = sorted(TYPES, key=len, reverse=True)
MINORISH = {"m", "m7", "dim", "dim7"}           # живуть у внутрішньому (мінорному) кільці
AMBIG = {"5", "sus2", "sus4", "aug"}            # якість (мажор/мінор) невизначена
SEVENTH = {"7": 10, "m7": 10, "maj7": 11, "dim7": 9}


def parse_full(name):
    """'G#m7' -> (8, 'm7'). ValueError для невідомого запису."""
    for suf in SUFFIXES + [""]:
        if name.endswith(suf) and name[:len(name) - len(suf)] in NOTE_NAMES:
            return NOTE_NAMES.index(name[:len(name) - len(suf)]), suf
    raise ValueError(f"невідомий акорд: {name}")


def chord_intervals(q):
    return sorted(TYPES[q]["w"])


def pcset(name):
    r, q = parse_full(name)
    return frozenset((r + i) % 12 for i in TYPES[q]["w"])


def related(a, b):
    """Споріднені акорди (одна множина нот вкладена в іншу): C ~ Cmaj7 ~ Em, Csus4 ~ Fsus2."""
    sa, sb = pcset(a), pcset(b)
    return sa <= sb or sb <= sa


def _build():
    metas, rows = [], []
    for suf, spec in TYPES.items():
        for root in range(CANON.get(suf, 12)):
            t = np.zeros(12, dtype=np.float32)
            for iv, w in spec["w"].items():
                t[(root + iv) % 12] = w
            rows.append(t / np.linalg.norm(t))
            metas.append((root, suf))
    names = [NOTE_NAMES[r] + s for r, s in metas]
    return names, np.stack(rows), metas


CHORD_NAMES, TEMPLATES, METAS = _build()
PEN = np.array([TYPES[s]["pen"] for _, s in METAS], dtype=np.float32)
PCSETS = [frozenset((r + i) % 12 for i in TYPES[s]["w"]) for r, s in METAS]


def _check(i, chroma, mx, min_cov, min_ext):
    root, suf = METAS[i]
    spec = TYPES[suf]
    ratio = lambda iv: float(chroma[(root + iv) % 12]) / mx
    cov = min(ratio(iv) for iv in spec["core"])
    ext = ratio(spec["ext"]) if spec["ext"] is not None else 1.0
    ok = cov >= min_cov and ext >= min_ext
    if ok and "forbid" in spec:
        ivs, thr = spec["forbid"]
        ok = all(ratio(iv) < thr for iv in ivs)
    return ok, cov, ext


def classify(chroma: np.ndarray, min_coverage=0.40, min_ext=0.40):
    """Двоетапно: кандидати за (схожість − штраф), потім ПЕРШИЙ, у якого присутні всі
    потрібні ноти (в т.ч. характерна). Септакорд без 7-ї ноти -> падаємо на тризвук.
    gap — відрив від найкращого ІНШОГО за нотним складом валідного кандидата."""
    mx = float(chroma.max())
    if mx < 1e-9:
        return None
    sims = TEMPLATES @ chroma
    adj = sims - PEN
    order = np.argsort(adj)[::-1]
    valid, top = [], int(order[0])
    for i in order:
        i = int(i)
        if _check(i, chroma, mx, min_coverage, min_ext)[0]:
            if not valid or PCSETS[i] != PCSETS[valid[0]]:
                valid.append(i)
            if len(valid) == 2:
                break
    if not valid:
        _, cov, ext = _check(top, chroma, mx, min_coverage, min_ext)
        return {"name": None, "best": CHORD_NAMES[top], "sim": float(sims[top]), "gap": 0.0, "cov": cov, "ext": ext}
    c = valid[0]
    _, cov, ext = _check(c, chroma, mx, min_coverage, min_ext)
    gap = float(adj[c] - adj[valid[1]]) if len(valid) > 1 else 1.0
    return {"name": CHORD_NAMES[c], "best": CHORD_NAMES[c], "sim": float(sims[c]), "gap": gap, "cov": cov, "ext": ext}


def explain(chroma, min_coverage=0.40, min_ext=0.40, **_):
    return classify(chroma, min_coverage, min_ext)


def detect_chord(chroma: np.ndarray, silence_thresh=0.75, margin=0.02, min_coverage=0.40, min_ext=0.40):
    """(назва, схожість) або (None, схожість)."""
    r = classify(chroma, min_coverage, min_ext)
    if r is None:
        return None, 0.0
    if r["name"] is None or r["sim"] < silence_thresh or r["gap"] < margin:
        return None, r["sim"]
    return r["name"], r["sim"]
