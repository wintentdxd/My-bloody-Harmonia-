# python -m harmonia.run_live [--list] [--device N] [--avoid-fret F]
import argparse
import sys
from harmonia.engine import RealtimeEngine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="показати аудіопристрої")
    ap.add_argument("--device", type=int, default=None)
    ap.add_argument("--avoid-fret", type=int, default=None, help="позиція першої гітари")
    ap.add_argument("--gate", type=float, default=None, help="фіксований RMS-поріг (інакше автокалібрування)")
    ap.add_argument("--thresh", type=float, default=0.75, help="мін. схожість із шаблоном акорду")
    ap.add_argument("--coverage", type=float, default=0.40, help="мін. покриття нот акорду (відсікає голос)")
    ap.add_argument("--ext", type=float, default=0.40, help="мін. присутність 7-ї/характерної ноти")
    ap.add_argument("--debug", action="store_true", help="друкувати схожість/покриття кожного кадру")
    a = ap.parse_args()

    import sounddevice as sd
    if a.list:
        print(sd.query_devices()); return

    from harmonia.io.mic_source import MicSource

    def show(ev):
        if ev["calibrating"]:
            print("\rКалібрування шуму кімнати... мовчіть", end="", flush=True); return
        if a.debug and ev["debug"]:
            d = ev["debug"]
            print(f"\n  [{d['best']:6s}] sim={d['sim']:.2f} gap={d['gap']:.2f} cov={d['cov']:.2f} "
                  f"ext={d['ext']:.2f} rms={ev['rms']:.3f}", end="")
        bar = "#" * min(40, int(ev["rms"] * 400))
        print(f"\rrms={ev['rms']:.3f} gate={ev['gate']:.3f} raw={str(ev['raw']):4s} "
              f"stable={str(ev['stable']):4s} {bar:<40}", end="", flush=True)
        adv = ev["advice"]
        if adv:
            nxt = ", ".join(f"{n['chord']} ({n['label']})" for n in adv["next"])
            k = adv["key"]["name"] if adv["key"] else "?"
            print(f"\n>> {adv['chord']}  тональність≈{k}  далі: {nxt}")
            print(f"   бас: {adv['instruments']['bass']['root']}/{adv['instruments']['bass']['fifth']}"
                  f"  соло: {adv['instruments']['solo'].get('key_pentatonic', {}).get('name', '-')}")

    eng = RealtimeEngine(gate=a.gate, avoid_fret=a.avoid_fret, on_event=show,
                         detect_kwargs={"silence_thresh": a.thresh, "min_coverage": a.coverage, "min_ext": a.ext})
    with MicSource(device=a.device) as mic:
        print(f"Мікрофон {mic.fs_in} Гц, Ctrl+C для виходу")
        try:
            eng.run(mic.frames())
        except KeyboardInterrupt:
            print(f"\nxrun={mic.status_flags} dropped={mic.dropped}")


if __name__ == "__main__":
    main()
