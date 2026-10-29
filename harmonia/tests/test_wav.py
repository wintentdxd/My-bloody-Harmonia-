# harmonia/tests/test_wav.py
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from collections import Counter
from harmonia.io.wav_source import load_wav, frames
from harmonia.dsp.chroma import chroma_from_frame, frame_rms
from harmonia.dsp.chords import detect_chord

RMS_GATE = 0.02

path = sys.argv[1]
sig = load_wav(path)
print(f"Тривалість: {len(sig) / 16000:.1f} с")

from harmonia.dsp.smoother import ChordSmoother

smoother = ChordSmoother(k=7)
votes = Counter()
for i, fr in enumerate(frames(sig)):
    if frame_rms(fr) < RMS_GATE:
        raw = None
    else:
        raw, _ = detect_chord(chroma_from_frame(fr))
    smooth = smoother.update(raw)
    votes[smooth] += 1
    print(f"кадр {i:3d}: raw={raw!s:5} smooth={smooth!s}")

print("\nПідсумок:", votes.most_common())