# harmonia/io/mic_source.py
"""Живий мікрофон: sounddevice callback -> кільцевий буфер -> кадри N з кроком HOP."""
import time
import numpy as np
from math import gcd

from harmonia.dsp.chroma import FS, N, HOP


class RingBuffer:
    """SPSC-буфер: callback пише, потік аналізу читає. Без блокувань.

    `written` — загальний лічильник записаних відліків; читач сам тримає
    свою позицію і ніколи не змушує callback чекати.
    """

    def __init__(self, capacity):
        self.cap = int(capacity)
        self.buf = np.zeros(self.cap, dtype=np.float32)
        self.written = 0

    def write(self, x):
        n = len(x)
        if n > self.cap:                      # дані довші за буфер: лишаємо хвіст
            x = x[-self.cap:]
        pos = (self.written + n - len(x)) % self.cap
        first = min(len(x), self.cap - pos)
        self.buf[pos:pos + first] = x[:first]
        self.buf[:len(x) - first] = x[first:]
        self.written += n                     # оновлюємо ПІСЛЯ копіювання

    def read(self, end, n):
        """Відліки [end-n, end) або None, якщо дані вже перезаписані/ще не прийшли."""
        start = end - n
        if start < 0 or end > self.written:
            return None
        out = self.buf[np.arange(start, end) % self.cap].copy()
        if self.written - start > self.cap:   # callback встиг перезаписати
            return None
        return out


class MicSource:
    def __init__(self, device=None, n=N, hop=HOP, fs_target=FS):
        import sounddevice as sd              # lazy: щоб тести працювали без PortAudio
        self._sd = sd
        self.device, self.n, self.hop, self.fs_target = device, n, hop, fs_target
        try:                                  # просимо 16 кГц напряму
            sd.check_input_settings(device=device, channels=1, samplerate=fs_target)
            self.fs_in = fs_target
        except Exception:                     # інакше — рідна частота пристрою
            self.fs_in = int(sd.query_devices(device, 'input')['default_samplerate'])
        g = gcd(self.fs_in, fs_target)
        self.up, self.down = fs_target // g, self.fs_in // g
        self.n_in = int(np.ceil(n * self.fs_in / fs_target))
        self.hop_in = int(round(hop * self.fs_in / fs_target))
        self.ring = RingBuffer(self.n_in * 4)
        self.status_flags = 0                 # лічильник xrun-ів PortAudio
        self.dropped = 0                      # кадрів пропущено, бо аналіз відставав
        self.stream = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            self.status_flags += 1
        self.ring.write(indata[:, 0])         # мінімум роботи в callback

    def start(self):
        self.stream = self._sd.InputStream(
            device=self.device, channels=1, samplerate=self.fs_in, dtype='float32',
            blocksize=self.hop_in // 2, latency='low', callback=self._callback)
        self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop(); self.stream.close(); self.stream = None

    def __enter__(self):
        self.start(); return self

    def __exit__(self, *exc):
        self.stop()

    def _prepare(self, win):
        if self.fs_in != self.fs_target:
            from scipy.signal import resample_poly   # ліниво
            win = resample_poly(win, self.up, self.down)
        win = win[:self.n].astype(np.float32)
        if len(win) < self.n:
            win = np.pad(win, (0, self.n - len(win)))
        return win

    def frames(self, stop=lambda: False):
        """Нескінченний генератор кадрів (N відліків @ FS), крок HOP."""
        pos = None
        while not stop():
            w = self.ring.written
            if pos is None:
                if w < self.n_in:
                    time.sleep(0.005); continue
                pos = w
            if w < pos:
                time.sleep(0.005); continue
            if w - pos > 3 * self.hop_in:     # відстали: перестрибуємо до «зараз»
                self.dropped += 1
                pos = w
            win = self.ring.read(pos, self.n_in)
            pos += self.hop_in
            if win is not None:
                yield self._prepare(win)
