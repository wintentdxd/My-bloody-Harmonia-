# harmonia/server.py  —  python -m harmonia.server [--device N] [--port 8000]
import argparse
import asyncio
import json
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from harmonia.dsp.chords import parse_full
from harmonia.engine import RealtimeEngine
from harmonia.theory.instruments import advise

UI_FILE = Path(__file__).parent / "ui" / "index.html"


def create_app(device=None, gate=None, thresh=0.75, coverage=0.40, ext=0.40):
    st = {"clients": set(), "history": [], "chord": None, "advice": None, "rev": 0, "hn": 0,
          "idle": True, "push": lambda m: None}
    engine = RealtimeEngine(gate=gate, detect_kwargs={"silence_thresh": thresh, "min_coverage": coverage, "min_ext": ext})
    stop = threading.Event()

    def chord_msg():
        return {"type": "chord", "chord": st["chord"], "advice": st["advice"], "history": st["history"],
                "rev": st["rev"], "hn": st["hn"], "idle": st["idle"]}

    def on_event(ev):                                   # викликається з потоку аналізу
        st["push"]({"type": "level", "rms": ev["rms"], "gate": engine.gate, "raw": ev["raw"],
                    "stable": ev["stable"], "calibrating": ev["calibrating"], "open": engine.gate_open})
        if not ev["changed"]:
            return
        c = ev["stable"]
        if c is None:                                   # акорд затих: лише приглушити UI
            st["idle"] = True
            st["push"]({"type": "idle"})
        elif c == st["chord"]:                          # той самий акорд знову: нічого не перемальовуємо
            st["idle"] = False
            st["push"]({"type": "resume"})
        else:                                           # справді новий акорд
            st.update(chord=c, advice=ev["advice"], idle=False, rev=st["rev"] + 1, hn=st["hn"] + 1)
            st["history"] = (st["history"] + [c])[-500:]
            st["push"](chord_msg())

    engine.on_event = on_event

    def worker():
        try:
            from harmonia.io.mic_source import MicSource
            with MicSource(device=device) as mic:
                st["push"]({"type": "status", "msg": f"Мікрофон {mic.fs_in} Гц"})
                engine.run(mic.frames(stop=stop.is_set))
        except Exception as e:
            st["push"]({"type": "error", "msg": f"{type(e).__name__}: {e}"})

    @asynccontextmanager
    async def lifespan(app):
        loop, queue = asyncio.get_running_loop(), asyncio.Queue(maxsize=300)

        def put(m):
            if not queue.full():
                queue.put_nowait(m)
        st["push"] = lambda m: loop.call_soon_threadsafe(put, m)

        async def broadcaster():
            while True:
                data = json.dumps(await queue.get(), ensure_ascii=False)
                for ws in list(st["clients"]):
                    try:
                        await ws.send_text(data)
                    except Exception:
                        st["clients"].discard(ws)

        task = asyncio.create_task(broadcaster())
        threading.Thread(target=worker, daemon=True).start()
        yield
        stop.set()
        task.cancel()

    app = FastAPI(lifespan=lifespan)
    app.state.engine, app.state.st = engine, st      # для тестів

    @app.get("/")
    def index():
        return FileResponse(UI_FILE)

    @app.get("/api/advice")
    def advice(chord: str):
        """Поради для довільного акорду (клік по сектору кола) у поточній тональності."""
        try:
            parse_full(chord)
        except ValueError:
            raise HTTPException(status_code=400, detail="unknown chord")
        key = st["advice"]["key"] if st["advice"] else None
        return advise(chord, key, engine.avoid_fret)

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        st["clients"].add(ws)
        await ws.send_text(json.dumps(chord_msg(), ensure_ascii=False))
        try:
            while True:
                m = json.loads(await ws.receive_text())
                if m.get("type") == "avoid_fret":        # позиція першої гітари
                    f = m.get("fret")
                    engine.avoid_fret = int(f) if f not in (None, "") else None
                    if st["chord"]:
                        key = st["advice"]["key"] if st["advice"] else None
                        st["advice"] = advise(st["chord"], key, engine.avoid_fret)
                        st["rev"] += 1
                        st["push"](chord_msg())
        except WebSocketDisconnect:
            pass
        finally:
            st["clients"].discard(ws)

    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", type=int, default=None)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--gate", type=float, default=None)
    ap.add_argument("--thresh", type=float, default=0.75)
    ap.add_argument("--coverage", type=float, default=0.40)
    ap.add_argument("--ext", type=float, default=0.40)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    import uvicorn
    if not a.no_browser:
        threading.Timer(1.5, webbrowser.open, [f"http://127.0.0.1:{a.port}"]).start()
    uvicorn.run(create_app(a.device, a.gate, a.thresh, a.coverage, a.ext), host="127.0.0.1", port=a.port)


if __name__ == "__main__":
    main()
