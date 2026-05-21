"""
separate.py
Exposes the already-separated stem produced by the detector.
Copies /stems/htdemucs_6s/<song>/<instrument>.wav → /stems/chosen.wav
so downstream services always read from the same fixed path.

If the stem doesn't exist yet (detector was skipped), falls back to
running Demucs with --two-stems to produce just that one stem.

Usage:
    python separate.py <audio_filename> <instrument>

    audio_filename : filename inside /audio/
    instrument     : drums | bass | guitar | piano | vocals | other
"""
import sys
import shutil
import subprocess
from pathlib import Path

DEMUCS_MODEL = "htdemucs_6s"
STEMS_ROOT   = Path("/stems")
AUDIO_ROOT   = Path("/audio")


def separate(audio_filename: str, instrument: str) -> None:
    audio_path = Path(audio_filename) if Path(audio_filename).is_absolute() else AUDIO_ROOT / audio_filename
    song_stem  = audio_path.stem
    source_wav = STEMS_ROOT / DEMUCS_MODEL / song_stem / f"{instrument}.wav"
    dest_wav   = STEMS_ROOT / "chosen.wav"

    if source_wav.exists():
        print(f"[separator] Reusing stem: {source_wav}", flush=True)
        shutil.copy2(source_wav, dest_wav)
    else:
        # Detector was skipped — run Demucs for this stem only
        print(f"[separator] Stem not found, running Demucs ({instrument})…", flush=True)
        result = subprocess.run(
            [
                "python", "-m", "demucs",
                "--two-stems", instrument,
                "-n", DEMUCS_MODEL,
                "-o", str(STEMS_ROOT),
                str(audio_path),
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("[separator] Demucs error:\n" + result.stderr, file=sys.stderr)
            sys.exit(1)

        if not source_wav.exists():
            candidates = list(STEMS_ROOT.rglob(f"{instrument}.wav"))
            if not candidates:
                print(f"[separator] {instrument}.wav not found after Demucs run.", file=sys.stderr)
                sys.exit(1)
            source_wav = candidates[0]

        shutil.copy2(source_wav, dest_wav)

    print(f"[separator] Stem ready: {dest_wav}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python separate.py <audio_filename> <instrument>")
        sys.exit(1)
    separate(sys.argv[1], sys.argv[2])
