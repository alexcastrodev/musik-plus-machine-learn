"""
analyze_pitch.py — Polyphonic pitch detection using Basic Pitch (Spotify).

Reads /stems/chosen.wav, runs Basic Pitch, writes:
  - /analysis/analysis.mid   — MIDI file
  - /analysis/analysis.json  — note events + tempo + instrument metadata

Usage:
    python analyze_pitch.py <stem_wav> <instrument> <output_dir> [duration_s]
"""
import sys
import json
from pathlib import Path

import pretty_midi
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH

CLEF = {
    "bass":   "bass",
    "guitar": "treble",
    "piano":  "grand",
    "vocals": "treble",
    "other":  "treble",
}


def _note_events(midi_path: str, tempo: float) -> list[dict]:
    pm = pretty_midi.PrettyMIDI(midi_path)
    beat_len = 60.0 / tempo
    events = []
    for inst in pm.instruments:
        for note in inst.notes:
            events.append({
                "pitch":          pretty_midi.note_number_to_name(note.pitch),
                "midi":           note.pitch,
                "start_beat":     round(note.start / beat_len, 3),
                "duration_beats": round((note.end - note.start) / beat_len, 3),
            })
    return sorted(events, key=lambda n: n["start_beat"])


def analyze(stem_path: str, instrument: str, out_dir: str, duration: float = 300.0) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[pitch] Running Basic Pitch on {stem_path}…", flush=True)
    _, midi_data, _ = predict(
        stem_path,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
        onset_threshold=0.5,
        frame_threshold=0.3,
        minimum_note_length=58,    # ms
        minimum_frequency=32.7,    # C1
        maximum_frequency=2093.0,  # C7
        melodia_trick=True,
    )

    midi_path = out / "analysis.mid"
    midi_data.write(str(midi_path))
    print(f"[pitch] MIDI saved: {midi_path}", flush=True)

    tempo = float(midi_data.estimate_tempo())
    print(f"[pitch] Tempo: {tempo:.1f} BPM", flush=True)

    notes = _note_events(str(midi_path), tempo)
    print(f"[pitch] Notes detected: {len(notes)}", flush=True)

    result = {
        "instrument": instrument,
        "tempo":      round(tempo, 1),
        "clef":       CLEF.get(instrument, "treble"),
        "notes":      notes,
    }
    json_path = out / "analysis.json"
    json_path.write_text(json.dumps(result, indent=2))
    print(f"[pitch] JSON saved: {json_path}", flush=True)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python analyze_pitch.py <stem_wav> <instrument> <output_dir> [duration]")
        sys.exit(1)

    dur = float(sys.argv[4]) if len(sys.argv) > 4 else 300.0
    analyze(sys.argv[1], sys.argv[2], sys.argv[3], duration=dur)
