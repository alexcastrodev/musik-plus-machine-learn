"""
generate_ly.py
Converte o JSON de análise em arquivo .ly (LilyPond) e compila para PDF.
"""

import sys
import json
import subprocess
import os
from pathlib import Path


def build_voice_upper(grid: dict, n_measures: int, title: str, tempo: float, sections: dict[int, str]) -> str:
    """Voz superior: hi-hat e crash cymbal."""
    lines = []
    lines.append(r"    \new DrumVoice {")
    lines.append(r"      \voiceOne")
    lines.append(rf"      \tempo 4 = {int(tempo)}")
    lines.append(r"      \time 4/4")
    lines.append(r"      \drummode {")

    prev_section = None

    for m in range(n_measures):
        section = sections.get(m)
        if section and section != prev_section:
            lines.append(rf'        \mark \markup {{ \box \bold "{section}" }}')
            prev_section = section

        mdata = grid.get(str(m), {"kick": [], "snare": [], "hihat": []})
        hihat = set(mdata.get("hihat", []))
        crash_slots = {0} if m in sections else set()

        tokens = []
        for i in range(16):
            if i in crash_slots:
                tokens.append("cymc16")
            elif i in hihat:
                tokens.append("hh16")
            else:
                tokens.append("r16")

        lines.append(f"        {' '.join(tokens)} |")

    lines.append(r"      }")
    lines.append(r"    }")
    return "\n".join(lines)


def build_voice_lower(grid: dict, n_measures: int) -> str:
    """Voz inferior: bumbo e caixa."""
    lines = []
    lines.append(r"    \new DrumVoice {")
    lines.append(r"      \voiceTwo")
    lines.append(r"      \drummode {")

    for m in range(n_measures):
        mdata = grid.get(str(m), {"kick": [], "snare": [], "hihat": []})
        kick  = set(mdata.get("kick", []))
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

    lines.append(r"      }")
    lines.append(r"    }")
    return "\n".join(lines)


def _sections_proportional(n_measures: int) -> dict[int, str]:
    if n_measures <= 0:
        return {}
    boundaries = [
        (0,                           "Intro"),
        (max(1, n_measures // 6),     "Verse 1"),
        (max(1, n_measures * 2 // 5), "Chorus"),
        (max(1, n_measures * 3 // 5), "Bridge"),
        (max(1, n_measures * 4 // 5), "Final Chorus"),
    ]
    return {start: label for start, label in boundaries}


def build_ly(data: dict, title: str = "Transcrição") -> str:
    tempo      = data["tempo"]
    n_measures = data["n_measures"]
    grid       = data["grid"]

    raw_sections = data.get("sections")
    if raw_sections:
        sections = {int(k): v for k, v in raw_sections.items()}
    else:
        sections = _sections_proportional(n_measures)

    header = rf"""
\version "2.24.0"

\header {{
  title = "{title}"
  tagline = \markup {{ \italic "Drum transcription  —  ♩ = {int(tempo)} BPM  —  4/4" }}
}}

\paper {{
  #(set-paper-size "a4")
  top-margin = 15\mm
  bottom-margin = 15\mm
  left-margin = 18\mm
  right-margin = 18\mm
  indent = 24\mm
  system-system-spacing.basic-distance = #20
  ragged-last-bottom = ##f
}}
""".strip()

    upper = build_voice_upper(grid, n_measures, title, tempo, sections)
    lower = build_voice_lower(grid, n_measures)

    score = r"""
\score {
  \new DrumStaff \with {
    instrumentName = \markup { \bold "Drums" }
    drumStyleTable = #drums-style
  }
  <<
""" + upper + "\n\n" + lower + r"""
  >>

  \layout {
    \context {
      \DrumStaff
      \consists "Bar_number_engraver"
    }
  }
}
"""
    return header + "\n\n" + score


def compile_ly(ly_path: str, output_dir: str) -> str:
    result = subprocess.run(
        ["lilypond", f"--output={output_dir}", ly_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("[sheet] LilyPond error:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    stem = Path(ly_path).stem
    return str(Path(output_dir) / f"{stem}.pdf")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python generate_ly.py <analysis.json> <title> <output_dir>")
        sys.exit(1)

    json_path  = sys.argv[1]
    title      = sys.argv[2]
    output_dir = sys.argv[3]

    with open(json_path) as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    ly_content = build_ly(data, title)
    ly_path    = os.path.join(output_dir, "drum_sheet.ly")

    with open(ly_path, "w") as f:
        f.write(ly_content)
    print(f"[sheet] .ly saved: {ly_path}")

    pdf_path = compile_ly(ly_path, output_dir)
    print(f"[sheet] PDF generated: {pdf_path}")
