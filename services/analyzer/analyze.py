"""
analyze.py — Drum analysis: BeatNet (beat tracking) + librosa (onset detection).

Reads the isolated drum stem from /stems/chosen.wav and the original mix
from /audio/<filename> (for section detection via chroma).

Usage:
    python analyze.py <drum_stem_wav> <original_audio> <output_json> [duration_s]
"""
import sys
import json
import numpy as np
import librosa
from scipy.signal import find_peaks



DRUM_BANDS = {
    "kick":  (40,    120),
    "snare": (150,   500),
    "hihat": (5000, 16000),
}
THRESHOLDS = {"kick": 88, "snare": 88, "hihat": 83}


def _beat_times(stem_path: str) -> np.ndarray:
    print("[analyzer] Beat tracking (librosa)…", flush=True)
    y, sr = librosa.load(stem_path)
    _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    return librosa.frames_to_time(beat_frames, sr=sr)


def _detect_hits(stem_path: str, duration: float) -> dict[str, list[float]]:
    print("[analyzer] Onset detection (librosa)…", flush=True)
    y, sr = librosa.load(stem_path, duration=duration)
    hop = 512
    stft = np.abs(librosa.stft(y, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr)

    min_dist = {
        "kick":  int(sr / hop / 4),
        "snare": int(sr / hop / 4),
        "hihat": int(sr / hop / 6),
    }

    hits: dict[str, list[float]] = {}
    for name, (lo, hi) in DRUM_BANDS.items():
        mask = (freqs >= lo) & (freqs <= hi)
        energy = stft[mask, :].mean(axis=0)
        if energy.max() > 0:
            energy = energy / energy.max()
        peaks, _ = find_peaks(
            energy,
            height=float(np.percentile(energy, THRESHOLDS[name])),
            distance=min_dist[name],
        )
        hits[name] = librosa.frames_to_time(peaks, sr=sr, hop_length=hop).tolist()
        print(f"[analyzer]   {name:5s}: {len(hits[name])} hits", flush=True)

    return hits


def _detect_sections(audio_path: str, beat_times: np.ndarray, n_measures: int, duration: float) -> dict[int, str]:
    if n_measures < 8:
        return {0: "Intro"}

    hop = 512
    n_seg = min(5, max(2, n_measures // 8))
    y, sr = librosa.load(audio_path, duration=duration)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    frames = np.clip(librosa.time_to_frames(beat_times, sr=sr, hop_length=hop), 0, chroma.shape[1] - 1)
    beat_chroma = librosa.util.sync(chroma, frames, aggregate=np.median)
    bounds = librosa.segment.agglomerative(beat_chroma, n_seg)

    names = ["Intro", "Verse 1", "Chorus", "Bridge", "Final Chorus"]
    sections: dict[int, str] = {0: names[0]}
    for i, b in enumerate(sorted(bounds)[1:], 1):
        m = int(b) // 4
        if 0 < m < n_measures and i < len(names):
            sections[m] = names[i]
    return sections


def analyze(stem_path: str, audio_path: str, duration: float = 300.0) -> dict:
    beat_times = _beat_times(stem_path)
    beat_times = beat_times[beat_times <= duration]
    if len(beat_times) < 2:
        print("[analyzer] Not enough beats detected.", file=sys.stderr)
        sys.exit(1)

    beat_interval = float(np.median(np.diff(beat_times)))
    tempo = 60.0 / beat_interval
    sub_dur = beat_interval / 4
    print(f"[analyzer] Tempo: {tempo:.1f} BPM", flush=True)

    hits = _detect_hits(stem_path, duration)

    grid: dict[int, dict] = {}
    for name, times in hits.items():
        for t in times:
            if t > duration:
                continue
            beat_idx = int(np.argmin(np.abs(beat_times - t)))
            m = beat_idx // 4
            mb = m * 4
            if mb >= len(beat_times):
                continue
            offset = t - float(beat_times[mb])
            slot = int(round(offset / sub_dur)) % 16
            grid.setdefault(m, {"kick": [], "snare": [], "hihat": []})
            if slot not in grid[m][name]:
                grid[m][name].append(slot)

    for m in grid:
        for inst in grid[m]:
            grid[m][inst] = sorted(grid[m][inst])

    n_measures = max(grid.keys()) + 1 if grid else 0
    print(f"[analyzer] Measures: {n_measures}", flush=True)

    print("[analyzer] Section detection…", flush=True)
    sections = _detect_sections(audio_path, beat_times, n_measures, duration)
    print(f"[analyzer] Sections: {list(sections.values())}", flush=True)

    return {
        "instrument": "drums",
        "tempo": round(tempo, 1),
        "beat_interval": round(beat_interval, 4),
        "n_measures": n_measures,
        "grid": {str(k): v for k, v in grid.items()},
        "sections": {str(k): v for k, v in sections.items()},
    }


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python analyze.py <drum_stem> <original_audio> <output_json> [duration]")
        sys.exit(1)

    dur = float(sys.argv[4]) if len(sys.argv) > 4 else 300.0
    result = analyze(sys.argv[1], sys.argv[2], duration=dur)
    with open(sys.argv[3], "w") as f:
        json.dump(result, f, indent=2)
    print(f"[analyzer] Saved: {sys.argv[3]}", flush=True)
