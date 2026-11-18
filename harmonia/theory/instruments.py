# harmonia/theory/instruments.py
"""Поради по інструментах на основі акорду (усі типи) + тональності."""
from harmonia.dsp.chords import NOTE_NAMES as NN, parse_full, chord_intervals, MINORISH, SEVENTH
from harmonia.theory.circle import neighbors, role_in_key, circle_highlight, base_minor


def _notes(root, ivs):
    return [NN[(root + i) % 12] for i in ivs]


# ===================== Гітара =====================
OPEN = {  # 6-я -> 1-а струна, None = не грає
    "C": [None, 3, 2, 0, 1, 0], "A": [None, 0, 2, 2, 2, 0], "G": [3, 2, 0, 0, 0, 3],
    "E": [0, 2, 2, 1, 0, 0], "D": [None, None, 0, 2, 3, 2],
    "Am": [None, 0, 2, 2, 1, 0], "Em": [0, 2, 2, 0, 0, 0], "Dm": [None, None, 0, 2, 3, 1],
    "C7": [None, 3, 2, 3, 1, 0], "A7": [None, 0, 2, 0, 2, 0], "G7": [3, 2, 0, 0, 0, 1],
    "E7": [0, 2, 0, 1, 0, 0], "D7": [None, None, 0, 2, 1, 2],
    "Am7": [None, 0, 2, 0, 1, 0], "Em7": [0, 2, 0, 0, 0, 0], "Dm7": [None, None, 0, 2, 1, 1],
    "Cmaj7": [None, 3, 2, 0, 0, 0], "Fmaj7": [None, None, 3, 2, 1, 0],
    "Dsus2": [None, None, 0, 2, 3, 0], "Dsus4": [None, None, 0, 2, 3, 3],
}
MOVABLE = {  # тип -> форма від E (корінь на 6-й) та від A (корінь на 5-й); значення додаються до ладу
    "":     {"E": [0, 2, 2, 1, 0, 0], "A": [None, 0, 2, 2, 2, 0]},
    "m":    {"E": [0, 2, 2, 0, 0, 0], "A": [None, 0, 2, 2, 1, 0]},
    "7":    {"E": [0, 2, 0, 1, 0, 0], "A": [None, 0, 2, 0, 2, 0]},
    "maj7": {"E": [0, 2, 1, 1, 0, 0], "A": [None, 0, 2, 1, 2, 0]},
    "m7":   {"E": [0, 2, 0, 0, 0, 0], "A": [None, 0, 2, 0, 1, 0]},
    "sus2": {"E": None, "A": [None, 0, 2, 2, 0, 0]},
    "sus4": {"E": [0, 2, 2, 2, 0, 0], "A": [None, 0, 2, 2, 3, 0]},
    "dim":  {"E": None, "A": [None, 0, 1, 2, 1, None]},
    "dim7": {"E": None, "A": [None, 0, 1, 2, 1, 2]},
    "aug":  {"E": None, "A": [None, 0, 3, 2, 2, 1]},
    "5":    {"E": [0, 2, 2, None, None, None], "A": [None, 0, 2, 2, None, None]},
}


def _guitar_board(frets, r, q, barre=False):
    """Акорд на 6-струнному грифі (формат як у баса): точки з ролями + заглушені струни."""
    fretted = [x for x in frets if x]
    mn, mx = min(fretted), max(fretted)
    first, last = (1, 4) if mx <= 4 else (mn, max(mn + 3, mx))
    fifth = (r + _FIFTH.get(q, 7)) % 12
    sev = (r + SEVENTH[q]) % 12 if q in SEVENTH else None
    dots, muted = [], []
    for i, x in enumerate(frets):                     # i: 0 = низька E ... 5 = висока e
        if x is None:
            muted.append(i)
            continue
        pc = (GT[i] + x) % 12
        role = "root" if pc == r else "fifth" if pc == fifth else "seventh" if pc == sev else "tone"
        dots.append({"string": i, "fret": x, "role": role, "note": NN[pc]})
    b = _board(6, 0 if first == 1 else first, last, dots)
    b["muted"] = muted
    if barre:                                         # планка: найнижчий лад, затиснутий ≥2 струнами
        idx = [i for i, x in enumerate(frets) if x == mn]
        if mn > 0 and len(idx) >= 2:
            b["barre"] = {"fret": mn, "from": min(idx), "to": max(idx)}
    return b


def guitar_shapes(name, avoid_fret=None):
    """Відкрита позиція (якщо є) + баре/рухомі форми E та A. avoid_fret — позиція першої
    гітари: рекомендуємо форму, найвіддаленішу від неї."""
    r, q = parse_full(name)
    cands, seen = [], set()

    def add(label, fret, frets):
        if tuple(frets) not in seen:
            seen.add(tuple(frets))
            cands.append({"shape": label, "fret": fret, "frets": frets})

    if name in OPEN:
        add("відкрита", 0, OPEN[name])
    for form, base in (("E", 4), ("A", 9)):
        tpl = MOVABLE[q][form]
        f = (r - base) % 12
        if tpl and f <= 11:
            add(f"відкрита (форма {form})" if f == 0 else f"баре, форма {form}", f,
                [None if x is None else x + f for x in tpl])
    low = [c for c in cands if c["fret"] <= 9]
    cands = low or cands                              # високі лади лише якщо інакше форм немає
    cands.sort(key=(lambda c: c["fret"]) if avoid_fret is None else (lambda c: -abs(c["fret"] - avoid_fret)))
    for i, c in enumerate(cands):
        c["recommended"] = i == 0
        c["board"] = _guitar_board(c["frets"], r, q, c["shape"].startswith("баре"))
    return cands


def guitar_advice(name, nexts, avoid_fret=None):
    return {
        "now": guitar_shapes(name, avoid_fret),
        "next": [{"chord": n["chord"], "label": n["label"],
                  "shape": guitar_shapes(n["chord"], avoid_fret)[0]} for n in nexts],
        "tip": "Другу гітару тримай на іншій позиції грифа (±5 ладів) або грай лише 3–4 тонкі струни.",
    }


# ===================== Гриф (спільна геометрія для баса й соло) =====================
BT = [4, 9, 2, 7]                 # бас: E A D G (від нижньої струни)
GT = [4, 9, 2, 7, 11, 4]          # гітара: E A D G B e


def _board(n_strings, start, last, dots):
    """first — перший відображуваний лад (відкриті струни малюються ліворуч від порожка)."""
    return {"strings": n_strings, "start": start, "first": max(start, 1), "last": last, "dots": dots}


def bass_box(name):
    """Басовий візерунок: корінь, квінта, октава (+ септима) в 5 ладах. Корінь на E-струні,
    а якщо там вище 7-го ладу — на A-струні."""
    r, q = parse_full(name)
    f_e = (r - 4) % 12
    s_idx, f = (0, f_e) if f_e <= 7 else (1, (r - 9) % 12)
    start = max(0, f - 1)
    last = start + 4
    occ = lambda pc: [(i, fr) for i in range(4) for fr in range(start, last + 1) if (BT[i] + fr) % 12 == pc]
    dots = [{"string": s_idx, "fret": f, "role": "root", "note": NN[r]}]
    taken = {(s_idx, f)}

    def put(cands, role, pc, key):
        cands = [c for c in cands if c not in taken]
        if cands:
            i, fr = min(cands, key=key)
            taken.add((i, fr))
            dots.append({"string": i, "fret": fr, "role": role, "note": NN[pc]})

    fifth_pc = (r + _FIFTH.get(q, 7)) % 12
    put([o for o in occ(fifth_pc) if o[0] >= s_idx], "fifth", fifth_pc, lambda o: (abs(o[0] - (s_idx + 1)), abs(o[1] - (f + 2))))
    put([o for o in occ(r) if o[0] >= s_idx + 1], "octave", r, lambda o: (abs(o[0] - (s_idx + 2)), abs(o[1] - (f + 2))))
    if q in SEVENTH:
        sev = (r + SEVENTH[q]) % 12
        put(occ(sev), "seventh", sev, lambda o: (abs(o[1] - f), abs(o[0] - s_idx)))
    return _board(4, start, last, dots)


def scale_box(root_pc, pcs):
    """Бокс пентатоніки/ладу на гітарному грифі: вікно з 4 ладів, що містить корінь на 6-й
    струні й дає найповніший бокс (по 2 ноти на струні)."""
    f0 = (root_pc - 4) % 12
    best = None
    for st in range(max(0, f0 - 3), f0 + 1):
        cnt = [sum(1 for fr in range(st, st + 4) if (GT[i] + fr) % 12 in pcs) for i in range(6)]
        score = (sum(min(2, c) for c in cnt), -abs(st - f0))
        if best is None or score > best[0]:
            best = (score, st)
    st = best[1]
    dots = [{"string": i, "fret": fr, "role": "root" if (GT[i] + fr) % 12 == root_pc else "scale",
             "note": NN[(GT[i] + fr) % 12]}
            for i in range(6) for fr in range(st, st + 4) if (GT[i] + fr) % 12 in pcs]
    return _board(6, st, st + 3, dots)


# ===================== Бас =====================
_FIFTH = {"dim": 6, "dim7": 6, "aug": 8}


def bass_advice(name, nexts, key):
    r, q = parse_full(name)
    fifth = NN[(r + _FIFTH.get(q, 7)) % 12]
    seventh = NN[(r + SEVENTH[q]) % 12] if q in SEVENTH else None
    scale = {(key["major_tonic"] + i) % 12 for i in (0, 2, 4, 5, 7, 9, 11)} if key else None
    out = {"root": NN[r], "fifth": fifth, "seventh": seventh, "box": bass_box(name), "to_next": []}
    for n in nexts:
        t, _ = parse_full(n["chord"])
        diat = None
        if scale:
            for d in (1, 2):
                if (t - d) % 12 in scale:
                    diat = NN[(t - d) % 12]
                    break
        appr = diat or NN[(t - 1) % 12]
        # септакорд: арпеджіо корінь–квінта–септима, потім підхід і ціль
        line = [NN[r], fifth, seventh, appr, NN[t]] if seventh else [NN[r], fifth, appr, NN[t]]
        out["to_next"].append({"chord": n["chord"], "target": NN[t],
                               "chromatic_below": NN[(t - 1) % 12], "chromatic_above": NN[(t + 1) % 12],
                               "diatonic_below": diat, "line": line, "box": bass_box(n["chord"])})
    return out


# ===================== Клавішні =====================
_EXT = {"": [0, 4, 7], "m": [0, 3, 7], "maj7": [0, 4, 7, 11], "add9": [0, 4, 7, 14], "6": [0, 4, 7, 9],
        "maj9": [0, 4, 7, 11, 14], "sus2": [0, 2, 7], "sus4": [0, 5, 7], "6sus2": [0, 2, 7, 9],
        "maj7sus2": [0, 2, 7, 11], "7": [0, 4, 7, 10], "9": [0, 4, 7, 10, 14], "13": [0, 4, 7, 10, 21],
        "7sus4": [0, 5, 7, 10], "9sus4": [0, 5, 7, 10, 14], "m7": [0, 3, 7, 10], "m9": [0, 3, 7, 10, 14],
        "m11": [0, 3, 7, 10, 17], "dim7": [0, 3, 6, 9], "m7b5": [0, 3, 6, 10], "aug7": [0, 4, 8, 10],
        "maj7#5": [0, 4, 8, 11]}
_EXT_BY_TYPE = {"": ["maj7", "add9", "sus2", "sus4"], "m": ["m7", "m9", "m11"],
                "7": ["9", "13", "7sus4"], "maj7": ["maj9", "6", "add9"], "m7": ["m9", "m11"],
                "sus2": ["6sus2", "maj7sus2"], "sus4": ["7sus4", "9sus4"],
                "dim": ["dim7", "m7b5"], "dim7": ["m7b5", "dim7"], "aug": ["aug7", "maj7#5"],
                "5": ["", "m", "sus4"]}
_INV = ["основне положення", "1-ше обернення", "2-ге обернення", "3-тє обернення"]


def _voicing(root, ivs, inv, shift):
    notes = [60 + root + i for i in ivs]
    for _ in range(inv):
        notes = notes[1:] + [notes[0] + 12]
    return [x + shift for x in notes]


def _norm(notes):
    """Тримаємо голосування в межах двох октав клавіатури (до 84 = C6)."""
    while max(notes) > 84 and min(notes) - 12 >= 48:
        notes = [x - 12 for x in notes]
    return notes


def _best_inversion(cur, nxt):
    cr, cq = parse_full(cur)
    nr, nq = parse_full(nxt)
    ref = sorted(_voicing(cr, chord_intervals(cq), 0, -12 if cr > 6 else 0))
    ivs = chord_intervals(nq)
    best = min(((sum(abs(a - b) for a, b in zip(ref, sorted(_voicing(nr, ivs, inv, sh)))), inv, sh)
                for inv in range(len(ivs)) for sh in (-12, 0)))
    cost, inv, sh = best
    v = _voicing(nr, ivs, inv, sh)
    return {"inversion": _INV[inv], "notes": [NN[x % 12] for x in v], "midi": _norm(v), "rootpc": nr, "movement": cost}


def keys_advice(name, nexts, key):
    r, q = parse_full(name)
    exts = _EXT_BY_TYPE[q]
    if q == "":                                       # домінанта тональності -> септакордові розширення
        role = role_in_key(name, key)
        if role and role.startswith("V"):
            exts = ["7", "9", "7sus4"]
    ivs = chord_intervals(q)
    return {"rootpc": r,
            "voicings": [{"label": _INV[inv], "midi": _norm(_voicing(r, ivs, inv, 0))}
                         for inv in range(min(2, len(ivs)))],
            "extensions": [{"name": NN[r] + e, "notes": _notes(r, _EXT[e])} for e in exts],
            "voice_leading": [{"chord": n["chord"], **_best_inversion(name, n["chord"])} for n in nexts]}


# ===================== Соло / духові =====================
_MODES = {0: ("Ionian (мажор)", [0, 2, 4, 5, 7, 9, 11]), 2: ("Dorian", [0, 2, 3, 5, 7, 9, 10]),
          4: ("Phrygian", [0, 1, 3, 5, 7, 8, 10]), 5: ("Lydian", [0, 2, 4, 6, 7, 9, 11]),
          7: ("Mixolydian", [0, 2, 4, 5, 7, 9, 10]), 9: ("Aeolian (мінор)", [0, 2, 3, 5, 7, 8, 10])}
_MAJ_PENT, _MIN_PENT = [0, 2, 4, 7, 9], [0, 3, 5, 7, 10]


def chord_pentatonic(name, key=None):
    r, _ = parse_full(name)
    mn = base_minor(name, key)
    return {"name": NN[r] + (" minor" if mn else " major") + " pentatonic", "notes": _notes(r, _MIN_PENT if mn else _MAJ_PENT)}


def _pent_pcs(name, key=None):
    return {NN.index(n) for n in chord_pentatonic(name, key)["notes"]}


def solo_advice(name, key):
    r, q = parse_full(name)
    out = {"chord_tones": _notes(r, chord_intervals(q)), "chord_pentatonic": chord_pentatonic(name, key)}
    mode = None
    if q in ("dim", "dim7"):
        mode = ("whole-half diminished", [0, 2, 3, 5, 6, 8, 9, 11])
    elif q == "aug":
        mode = ("whole tone", [0, 2, 4, 6, 8, 10])
    elif q == "7":
        mode = ("Mixolydian", _MODES[7][1])
        out["blues"] = {"name": f"{NN[r]} blues", "notes": _notes(r, [0, 3, 5, 6, 7, 10])}
    if key:
        t = key["tonic"]
        out["key_pentatonic"] = {"name": NN[t] + (" major" if key["mode"] == "major" else " minor") + " pentatonic",
                                 "notes": _notes(t, _MAJ_PENT if key["mode"] == "major" else _MIN_PENT)}
        if key["mode"] == "minor":
            out["blues_note"] = NN[(t + 6) % 12]
        role = role_in_key(name, key)
        if mode is None and role and role.startswith("V") and "harm" in role:
            mode = ("Phrygian dominant", [0, 1, 4, 5, 7, 8, 10])
        elif mode is None:
            iv = (r - key["major_tonic"]) % 12
            if iv in _MODES:
                mode = _MODES[iv]
    if mode is None:                                  # тональність невідома: за якістю акорду
        mode = {"": _MODES[0], "maj7": _MODES[5], "m": _MODES[2], "m7": _MODES[2],
                "sus2": ("Mixolydian", _MODES[7][1]), "sus4": ("Mixolydian", _MODES[7][1]),
                "5": ("pentatonic-only", _MIN_PENT)}[q]
    if q == "maj7" and key is None:
        mode = _MODES[5]
    out["mode"] = {"name": f"{NN[r]} {mode[0]}", "notes": _notes(r, mode[1])}
    if key:
        t = key["tonic"]
        pcs = {(t + i) % 12 for i in (_MAJ_PENT if key["mode"] == "major" else _MIN_PENT)}
        box, title = scale_box(t, pcs), out["key_pentatonic"]["name"]
    else:
        box, title = scale_box(r, _pent_pcs(name, None)), out["chord_pentatonic"]["name"]
    box["title"] = title
    out["box"] = box
    return out


# ===================== Усе разом =====================
def advise(name, key, avoid_fret=None):
    """JSON-сумісний словник порад для всіх інструментів."""
    r, q = parse_full(name)
    nexts = neighbors(name, key)
    return {
        "chord": name, "root": NN[r], "type": q, "key": key,
        "role": role_in_key(name, key),
        "circle": circle_highlight(name, key),
        "next": [{"chord": n["chord"], "label": n["label"], "diatonic": n["diatonic"], "priority": n["priority"],
                  "tones": _notes(parse_full(n["chord"])[0], chord_intervals(parse_full(n["chord"])[1])),
                  "pent": chord_pentatonic(n["chord"], key)["notes"],
                  "box": scale_box(parse_full(n["chord"])[0], _pent_pcs(n["chord"], key))} for n in nexts],
        "instruments": {
            "guitar": guitar_advice(name, nexts, avoid_fret),
            "bass": bass_advice(name, nexts, key),
            "keys": keys_advice(name, nexts, key),
            "solo": solo_advice(name, key),
        },
    }
