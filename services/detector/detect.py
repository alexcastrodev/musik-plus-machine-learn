"""
detect.py
Runs Demucs htdemucs_6s on the original mix, measures RMS per stem,
and prints which instruments are present.

Usage:
    python detect.py <audio_path> <output_stems_dir> [threshold_db]

Output:
    /stems/instruments.json   — { "drums": { "present": true, "rms_db": -18 }, ... }
    /stems/<model>/<song>/    — all 6 stem WAVs (reused by separator)
"""
import sys
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

DEMUCS_MODEL = "htdemucs_6s"
STEMS = ["drums", "bass", "guitar", "piano", "vocals", "other"]


def rms_db(wav_path: Path) -> float:
    data, _ = sf.read(str(wav_path), always_2d=True)
    rms = float(np.sqrt(np.mean(data ** 2)))
    return round(20 * np.log10(rms + 1e-9), 1)


def detect(audio_path: str, stems_dir: str, threshold_db: float = -40.0) -> dict:
    audio = Path(audio_path)
    out = Path(stems_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[detector] Separating all stems: {audio.name}", flush=True)
    result = subprocess.run(
        ["python", "-m", "demucs", "-n", DEMUCS_MODEL, "-o", str(out), str(audio)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("[detector] Demucs error:\n" + result.stderr, file=sys.stderr)
        sys.exit(1)

    # Demucs writes: <out>/<model>/<song_stem>/<stem>.wav
    song_stem = audio.stem
    stem_dir = out / DEMUCS_MODEL / song_stem

    instruments = {}
    for stem in STEMS:
        wav = stem_dir / f"{stem}.wav"
        if wav.exists():
            db = rms_db(wav)
            instruments[stem] = {"present": bool(db > threshold_db), "rms_db": db}
        else:
            instruments[stem] = {"present": False, "rms_db": -99.0}
        flag = "✓" if instruments[stem]["present"] else "✗"
        print(f"[detector]   {flag} {stem:7s}: {instruments[stem]['rms_db']:6.1f} dBFS", flush=True)

    result_path = out / "instruments.json"
    result_path.write_text(json.dumps(instruments, indent=2))
    print(f"[detector] Saved: {result_path}", flush=True)
    return instruments


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python detect.py <audio_path> <stems_dir> [threshold_db]")
        sys.exit(1)

    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else -40.0
    detect(sys.argv[1], sys.argv[2], threshold)
