# harmonia/theory/circle.py
"""Кварто-квінтове коло, оцінка тональності, рухи з акорду (з підтримкою розширених типів)."""
from harmonia.dsp.chords import NOTE_NAMES, parse_full, MINORISH, AMBIG

CIRCLE_ORDER = [(i * 7) % 12 for i in range(12)]      # C G D A E B F# C# G# D# A# F


def circle_pos(pc):
    return (pc * 7) % 12


def parse_chord(name):
    """(корінь, minor?) — «базовий тризвук»: Am7, Bdim -> мінорні; G7, Gsus4 -> мажорні."""
    r, q = parse_full(name)
    return r, q in MINORISH


def chord_name(root, minor):
    return NOTE_NAMES[root % 12] + ("m" if minor else "")


# ---------- функція акорду в тональності ----------
_ROMAN_MAJOR = {0: "I", 2: "ii", 4: "iii", 5: "IV", 7: "V", 9: "vi"}
_MINOR_MAP = {"vi": "i", "I": "III", "ii": "iv", "iii": "v", "IV": "VI", "V": "VII"}
_SFX = {"7": "7", "maj7": "maj7", "m7": "7", "dim7": "7"}


def _role(name, key):
    """(римська цифра, суфікс) або None. key: {major_tonic, mode}."""
    root, q = parse_full(name)
    iv = (root - key["major_tonic"]) % 12
    minor_key = key["mode"] == "minor"
    sfx = _SFX.get(q, "")
    if q in ("dim", "dim7"):
        if iv == 11:
            return ("ii°" if minor_key else "vii°"), sfx
        if minor_key and iv == 8:
            return "vii° (harm.)", sfx
        return None
    minor, amb = q in MINORISH, q in AMBIG
    if minor_key and iv == 4 and not minor and not amb:       # V гармонічного мінору (E у Am)
        return "V (harm.)", sfx
    if iv in _ROMAN_MAJOR and (amb or (iv in (2, 4, 9)) == minor):
        r = _ROMAN_MAJOR[iv]
        return (_MINOR_MAP[r] if minor_key else r), sfx
    return None


def _fmt(r, sfx):
    if " (" in r:
        a, b = r.split(" ", 1)
        return f"{a}{sfx} {b}"
    return r + sfx


def role_in_key(name, key):
    if not key:
        return None
    rr = _role(name, key)
    return _fmt(*rr) if rr else None


def base_minor(name, key=None):
    r, q = parse_full(name)
    if q in MINORISH:
        return True
    if q in AMBIG and key:
        rr = _role(name, key)
        return bool(rr) and rr[0][0].islower()
    return False


def chord_ring_pos(name, key=None):
    """(кільце, позиція): мажорний базис — зовнішнє, мінорний — внутрішнє."""
    r, _ = parse_full(name)
    return ("inner", circle_pos((r + 3) % 12)) if base_minor(name, key) else ("outer", circle_pos(r))


# ---------- тональність ----------
def estimate_key(history, decay=0.85):
    if not history:
        return None
    best, best_score = None, -1e9
    n = len(history)
    for tonic in range(12):
        for mode in ("major", "minor"):
            key = {"tonic": tonic, "mode": mode, "major_tonic": tonic if mode == "major" else (tonic + 3) % 12}
            tonic_roman = "I" if mode == "major" else "i"
            s = 0.0
            for i, ch in enumerate(history):
                w = decay ** (n - 1 - i)
                rr = _role(ch, key)
                if rr is None:
                    s -= 0.5 * w
                elif "harm" in rr[0]:
                    s += 0.8 * w
                else:
                    s += w
                    if rr[0] == tonic_roman:
                        s += 0.6 * w
            if mode == "major":
                s += 0.4                                    # апріорі мажор частіший
            rr = _role(history[-1], key)
            if rr and rr[0] == tonic_roman:
                s += 0.5
            if s > best_score:
                best, best_score = key, s
    best["name"] = NOTE_NAMES[best["tonic"]] + (" major" if best["mode"] == "major" else " minor")
    best["score"] = round(best_score, 2)
    return best


# ---------- рухи по колу ----------
def neighbors(name, key=None):
    """Куди йти далі. Для домінанти/aug/dim/sus першим стоїть РОЗВ'ЯЗАННЯ (priority=True)."""
    r, q = parse_full(name)
    minor = base_minor(name, key)
    cand, seen = [], set()

    def add(chord, label, pri=False):
        if chord not in seen:
            seen.add(chord)
            cand.append((chord, label, pri))

    def resolve_to(t, label_default):
        mn = bool(key) and key["mode"] == "minor" and key["tonic"] == t
        target = chord_name(t, mn)
        rr = _role(target, key) if key else None
        add(target, "розв'язання в тоніку (I)" if rr and rr[0] in ("I", "i") else label_default, True)

    if q in ("7", "aug"):
        resolve_to((r + 5) % 12, "розв'язання (V→I)")
    elif q in ("dim", "dim7"):
        resolve_to((r + 1) % 12, "розв'язання (vii°→I)")
    elif q in ("sus2", "sus4"):
        add(chord_name(r, minor), f"розв'язання {q} → {chord_name(r, minor)}", True)

    if not minor:
        add(chord_name(r + 5, False), "субдомінанта (IV)")
        add(chord_name(r + 7, False), "домінанта (V)")
        add(chord_name(r + 9, True), "паралельний мінор (vi)")
    else:
        add(chord_name(r + 5, True), "субдомінанта (iv)")
        add(chord_name(r + 7, True), "домінанта (v)")
        add(chord_name(r + 7, False), "домінанта гармонічна (V)")
        add(chord_name(r + 3, False), "паралельний мажор (III)")

    out = [{"chord": c, "label": l, "priority": p,
            "diatonic": (role_in_key(c, key) is not None) if key else None,
            "pos": chord_ring_pos(c)} for c, l, p in cand]
    out.sort(key=lambda d: (not d["priority"], not d["diatonic"] if key else 0))   # стабільне сортування
    return out


def circle_highlight(name, key=None):
    ring, pos = chord_ring_pos(name, key)
    return {"current": {"ring": ring, "pos": pos},
            "neighbors": [{"chord": n["chord"], "ring": n["pos"][0], "pos": n["pos"][1],
                           "diatonic": n["diatonic"], "priority": n["priority"]}
                          for n in neighbors(name, key)]}
