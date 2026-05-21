"""
generate_sheet.py — Generate PDF sheet music from analysis.json.

Drums   → custom LilyPond drum notation
Others  → music21 parses analysis.mid → LilyPond → PDF

Usage:
    python generate_sheet.py <analysis_dir> <title> <output_dir>

    analysis_dir : directory containing analysis.json (and analysis.mid for pitch)
    title        : score title
    output_dir   : where to write the PDF
"""
import sys
import json
import subprocess
from pathlib import Path


# ── LilyPond compile helper ──────────────────────────────────────────────────

def _compile_ly(ly_path: Path, out_dir: Path) -> Path:
    result = subprocess.run(
        ["lilypond", f"--output={out_dir}", str(ly_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("[sheet] LilyPond error:\n" + result.stderr, file=sys.stderr)
        sys.exit(1)
    pdf = out_dir / f"{ly_path.stem}.pdf"
    print(f"[sheet] PDF: {pdf}", flush=True)
    return pdf


# ── Drum sheet ───────────────────────────────────────────────────────────────

def _voice_upper(grid, n_measures, tempo, sections):
    lines = [
        r"    \new DrumVoice {",
        r"      \voiceOne",
        rf"      \tempo 4 = {int(tempo)}",
        r"      \time 4/4",
        r"      \drummode {",
    ]
    prev = None
    for m in range(n_measures):
        sec = sections.get(m)
        if sec and sec != prev:
            lines.append(rf'        \mark \markup {{ \box \bold "{sec}" }}')
            prev = sec
        mdata = grid.get(str(m), {})
        hihat = set(mdata.get("hihat", []))
        crash = {0} if m in sections else set()
        tokens = ["cymc16" if i in crash else "hh16" if i in hihat else "r16" for i in range(16)]
        lines.append(f"        {' '.join(tokens)} |")
    lines += [r"      }", r"    }"]
    return "\n".join(lines)


def _voice_lower(grid, n_measures):
    lines = [r"    \new DrumVoice {", r"      \voiceTwo", r"      \drummode {"]
    for m in range(n_measures):
        mdata = grid.get(str(m), {})
        kick = set(mdata.get("kick", []))
        snare = set(mdata.get("snare", []))
        tokens = []
        for i in range(16):
            if i in kick and i in snare:
                tokens.append("<bd sn>16")
            elif i in kick:
                tokens.append("bd16")
            elif i in snare:
                tokens.append("sn16")
            else:
                tokens.append("r16")
        lines.append(f"        {' '.join(tokens)} |")
    lines += [r"      }", r"    }"]
    return "\n".join(lines)


def _drum_ly(data: dict, title: str) -> str:
    tempo = data["tempo"]
    n     = data["n_measures"]
    grid  = data["grid"]
    raw   = data.get("sections", {})
    sections = {int(k): v for k, v in raw.items()} if raw else {0: "Intro"}

    return rf"""\version "2.24.0"
\header {{
  title = "{title}"
  tagline = \markup {{ \italic "Drum transcription  —  ♩ = {int(tempo)} BPM  —  4/4" }}
}}
\paper {{
  #(set-paper-size "a4")
  top-margin = 15\mm  bottom-margin = 15\mm
  left-margin = 18\mm  right-margin = 18\mm
  indent = 24\mm
  system-system-spacing.basic-distance = #20
  ragged-last-bottom = ##f
}}
\score {{
  \new DrumStaff \with {{
    instrumentName = \markup {{ \bold "Drums" }}
    drumStyleTable = #drums-style
  }}
  <<
{_voice_upper(grid, n, tempo, sections)}

{_voice_lower(grid, n)}
  >>
  \layout {{ \context {{ \DrumStaff \consists "Bar_number_engraver" }} }}
}}
"""


def generate_drums(analysis_dir: Path, title: str, out_dir: Path) -> None:
    data = json.loads((analysis_dir / "analysis.json").read_text())
    ly = _drum_ly(data, title)
    ly_path = out_dir / "sheet.ly"
    ly_path.write_text(ly)
    print(f"[sheet] .ly written: {ly_path}", flush=True)
    _compile_ly(ly_path, out_dir)


# ── Pitch sheet (music21) ────────────────────────────────────────────────────

def generate_pitch(analysis_dir: Path, title: str, out_dir: Path) -> None:
    import music21

    midi_path = analysis_dir / "analysis.mid"
    if not midi_path.exists():
        print(f"[sheet] MIDI not found: {midi_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[sheet] Parsing MIDI with music21…", flush=True)
    score = music21.converter.parse(str(midi_path))
    score.metadata = music21.metadata.Metadata()
    score.metadata.title = title

    ly_path = out_dir / "sheet.ly"
    print(f"[sheet] Exporting LilyPond…", flush=True)
    score.write("lilypond", fp=str(ly_path))
    _compile_ly(ly_path, out_dir)


# ── Entrypoint ───────────────────────────────────────────────────────────────

def generate(analysis_dir: str, title: str, out_dir: str) -> None:
    adir = Path(analysis_dir)
    odir = Path(out_dir)
    odir.mkdir(parents=True, exist_ok=True)

    data = json.loads((adir / "analysis.json").read_text())
    instrument = data.get("instrument", "drums")

    print(f"[sheet] Instrument: {instrument}", flush=True)
    if instrument == "drums":
        generate_drums(adir, title, odir)
    else:
        generate_pitch(adir, title, odir)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python generate_sheet.py <analysis_dir> <title> <output_dir>")
        sys.exit(1)
    generate(sys.argv[1], sys.argv[2], sys.argv[3])
