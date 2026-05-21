#!/usr/bin/env python3
"""
Musikplus TUI — runs inside the pipeline container.

Volumes mounted at runtime:
  /audio        → ./audio       (ro) — source audio files
  /stems        → stems volume  (rw) — detector output + chosen.wav
  /analysis     → analysis vol  (rw) — analyzer output
  /output       → output volume (rw) — final PDFs
  /host-output  → ./output      (rw) — copies outputs to host

Calls sibling containers via Docker socket + COMPOSE_FILE/PROJECT env vars.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table
    from rich import box
    from rich.text import Text
except ImportError:
    print("rich / questionary missing — rebuild the pipeline image.")
    sys.exit(1)

console = Console()

AUDIO_DIR    = Path("/audio")
STEMS_DIR    = Path("/stems")
STEMS_AUDIO  = STEMS_DIR / "audio"   # audio files staged here for sibling containers
ANALYSIS_DIR = Path("/analysis")
OUTPUT_DIR   = Path("/output")
HOST_OUTPUT  = Path("/host-output")

COMPOSE_FILE    = os.getenv("COMPOSE_FILE", "/project/docker-compose.yml")
COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT_NAME", "musikplus")

STEMS = ["drums", "bass", "guitar", "piano", "vocals", "other"]
CLEF_LABEL = {
    "drums":  "Percussion",
    "bass":   "Bass clef",
    "guitar": "Treble clef",
    "piano":  "Grand staff",
    "vocals": "Treble clef",
    "other":  "Treble clef",
}


# ── Docker helpers ────────────────────────────────────────────────────────────

def _compose_run(service: str, *args: str, label: str = "") -> None:
    cmd = [
        "docker", "compose",
        "-p", COMPOSE_PROJECT,
        "-f", COMPOSE_FILE,
        "run", "--rm", service,
        *args,
    ]
    log_lines: list[str] = []
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[bold cyan]{label or service}[/]  [dim]{{task.description}}[/]"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("starting…")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            line = line.rstrip()
            log_lines.append(line)
            if line.strip():
                progress.update(task, description=line[:90])
        proc.wait()

    if proc.returncode != 0:
        console.print(f"\n[bold red]✗ {service} failed (exit {proc.returncode})[/]")
        console.print("\n[dim]--- service output ---[/]")
        for line in log_lines[-50:]:
            console.print(f"[dim]{line}[/]")
        sys.exit(proc.returncode)

    console.print(f"[green]✓[/] {label or service}")


# ── Steps ─────────────────────────────────────────────────────────────────────

def step_detect(audio_file: str) -> dict:
    console.rule("[bold]Step 1 — Instrument Detection[/]")
    _compose_run("detector", f"/stems/audio/{audio_file}", "/stems", label="Demucs 6s + RMS")
    instruments_path = STEMS_DIR / "instruments.json"
    if not instruments_path.exists():
        console.print("[red]instruments.json not found after detection.[/]")
        sys.exit(1)
    return json.loads(instruments_path.read_text())


def step_choose(instruments: dict) -> str:
    console.print()
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Instrument", style="cyan")
    table.add_column("Present", justify="center")
    table.add_column("Level (dBFS)", justify="right")
    table.add_column("Notation")

    present = []
    for stem in STEMS:
        info = instruments.get(stem, {})
        detected = info.get("present", False)
        db = info.get("rms_db", -99)
        icon = "[green]✓[/]" if detected else "[dim]✗[/]"
        table.add_row(stem, icon, f"{db:+.1f}", CLEF_LABEL.get(stem, ""))
        if detected:
            present.append(stem)

    console.print(table)

    if not present:
        console.print("[bold red]No instruments detected. Try a different file.[/]")
        sys.exit(1)

    console.print()
    return questionary.select(
        "Which instrument do you want to transcribe?",
        choices=present,
    ).ask()


def step_separate(audio_file: str, instrument: str) -> None:
    console.rule("[bold]Step 2 — Stem Isolation[/]")
    _compose_run("demucs", f"/stems/audio/{audio_file}", instrument, label=f"Isolate {instrument}")


def step_analyze(audio_file: str, instrument: str, duration: str) -> None:
    console.rule("[bold]Step 3 — Analysis[/]")
    if instrument == "drums":
        _compose_run(
            "analyzer",
            "/stems/chosen.wav", f"/stems/audio/{audio_file}",
            "/analysis/analysis.json", duration,
            label="librosa",
        )
    else:
        _compose_run(
            "analyzer-pitch",
            "/stems/chosen.wav", instrument, "/analysis", duration,
            label="Basic Pitch",
        )


def step_sheet(title: str, instrument: str) -> None:
    console.rule("[bold]Step 4 — Sheet Music[/]")
    # Remove stale PDFs before generating
    if OUTPUT_DIR.exists():
        for old in OUTPUT_DIR.glob("sheet_*.pdf"):
            old.unlink()
        for old in OUTPUT_DIR.glob("sheet_*.ly"):
            old.unlink()
    _compose_run("sheet", "/analysis", title, "/output", label="LilyPond → PDF")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    console.print(Panel(
        Text("Musikplus", style="bold magenta", justify="center"),
        subtitle="music transcription pipeline",
        border_style="magenta",
    ))
    console.print()

    audio_files = sorted(
        f.name for f in AUDIO_DIR.iterdir()
        if f.suffix.lower() in {".flac", ".mp3", ".wav", ".ogg", ".m4a", ".aiff"}
    ) if AUDIO_DIR.exists() else []

    if not audio_files:
        console.print(f"[red]No audio files found in {AUDIO_DIR}[/]")
        sys.exit(1)

    audio_file = questionary.select("Select audio file:", choices=audio_files).ask()
    title = questionary.text("Score title:", default=Path(audio_file).stem).ask()
    duration = questionary.text("Max duration to analyse (seconds):", default="300").ask()
    export_stem = questionary.confirm(
        f"Export isolated stem as WAV?", default=False
    ).ask()
    gen_sheet = questionary.confirm(
        "Generate sheet music (PDF)?", default=True
    ).ask()
    console.print()

    # Stage audio into stems volume (sibling containers can't use the host bind on Mac)
    STEMS_AUDIO.mkdir(parents=True, exist_ok=True)
    src = AUDIO_DIR / audio_file
    dst = STEMS_AUDIO / audio_file
    if not dst.exists() or dst.stat().st_size != src.stat().st_size:
        console.print(f"[dim]Copying {audio_file} into stems volume…[/]")
        shutil.copy2(src, dst)

    instruments = step_detect(audio_file)
    instrument  = step_choose(instruments)

    step_separate(audio_file, instrument)
    step_analyze(audio_file, instrument, duration)
    if gen_sheet:
        step_sheet(title, instrument)

    # Copy outputs from the volumes to the host bind mount
    outputs: list[str] = []
    if HOST_OUTPUT.exists():
        if gen_sheet:
            expected_pdf = OUTPUT_DIR / f"sheet_{instrument}.pdf"
            if expected_pdf.exists():
                shutil.copy2(expected_pdf, HOST_OUTPUT / expected_pdf.name)
                outputs.append(expected_pdf.name)
            else:
                console.print(f"[yellow]Expected {expected_pdf.name} not found in output volume.[/]")

        if export_stem:
            chosen_wav = STEMS_DIR / "chosen.wav"
            if chosen_wav.exists():
                stem_name = f"{Path(audio_file).stem}_{instrument}.wav"
                shutil.copy2(chosen_wav, HOST_OUTPUT / stem_name)
                outputs.append(stem_name)
            else:
                console.print("[yellow]chosen.wav not found — stem not exported.[/]")

    console.print()
    if outputs:
        console.print(Panel(
            f"[bold green]Done![/]\n\n" + "\n".join(f"[cyan]{f}[/]" for f in outputs),
            title="Output — saved to ./output/",
            border_style="green",
        ))
    else:
        console.print("[yellow]Pipeline completed — no output files selected.[/]")


if __name__ == "__main__":
    main()
