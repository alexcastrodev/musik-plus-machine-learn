# Musikplus — Tasks

## Pipeline

```
docker compose run --rm -it pipeline
        │
        ├─ [TUI] seleccionar ficheiro de audio
        ├─ [TUI] título + duração máxima
        │
        ├─► detector        Demucs htdemucs_6s → RMS/stem → instruments.json
        ├─ [TUI] mostra tabela de instrumentos detectados → utilizador escolhe
        │
        ├─► demucs          copia stem escolhido → /stems/chosen.wav
        │
        ├─► analyzer        BeatNet + librosa → /analysis/analysis.json   (bateria)
        │   analyzer-pitch  Basic Pitch → /analysis/analysis.mid + .json  (outros)
        │
        └─► sheet           LilyPond → /output/sheet.pdf                  (bateria)
                            music21 + LilyPond → /output/sheet.pdf        (outros)
```

## Arquitectura de serviços

| Serviço | Imagem | Responsabilidade |
|---|---|---|
| `pipeline` | musikplus-pipeline | TUI (Rich + questionary) + orquestração via Docker socket |
| `detector` | musikplus-detector | Demucs 6s full-split → RMS por stem → instruments.json |
| `demucs` | musikplus-demucs | Copia stem escolhido para chosen.wav (reutiliza stems do detector) |
| `analyzer` | musikplus-analyzer | BeatNet (beat tracking) + librosa (onsets) → analysis.json |
| `analyzer-pitch` | musikplus-analyzer-pitch | Basic Pitch (Spotify) → analysis.mid + analysis.json |
| `sheet` | musikplus-sheet | LilyPond nativo (bateria) / music21+LilyPond (melódicos) → PDF |

## Ferramentas

| Tarefa | Ferramenta | Versão |
|---|---|---|
| Separação de stems | Demucs `htdemucs_6s` | 4.0.1 |
| Beat tracking | BeatNet | 1.1.0 |
| Pitch polifónico | Basic Pitch (Spotify) | 0.4.0 |
| Notação — bateria | LilyPond nativo | via apt |
| Notação — melódicos | music21 + LilyPond | 9.7.0 |
| TUI | Rich + questionary | 13.7.1 / 2.0.1 |

---

## Estado actual

| Componente | Ficheiro | Estado |
|---|---|---|
| TUI orquestrador | `services/pipeline/pipeline.py` | ✅ |
| Detector de instrumentos | `services/detector/detect.py` | ✅ |
| Separação de stem | `services/demucs/separate.py` | ✅ |
| Análise bateria (BeatNet) | `services/analyzer/analyze.py` | ✅ |
| Análise pitch (Basic Pitch) | `services/analyzer-pitch/analyze_pitch.py` | ✅ |
| Sheet bateria (LilyPond) | `services/sheet/generate_sheet.py` | ✅ |
| Sheet melódico (music21) | `services/sheet/generate_sheet.py` | ✅ |
| docker-compose.yml | raiz | ✅ |
| Dockerfile demucs | `services/demucs/Dockerfile` | ⚠️ sem WORKDIR, versão não fixada |
| README | `README.md` | ⚠️ desactualizado (descreve monólito antigo) |

---

## Pendente

- [x] `services/sheet/` — generate_sheet.py (bateria + melódicos)
- [x] `services/detector/` — detect.py
- [x] `services/demucs/` — separate.py generalizado
- [x] `services/analyzer/` — BeatNet substituiu madmom
- [x] `services/analyzer-pitch/` — Basic Pitch
- [x] `services/pipeline/` — TUI containerizada
- [x] `docker-compose.yml` — todos os serviços
- [ ] **Corrigir `services/demucs/Dockerfile`** — WORKDIR + versão demucs fixada
- [ ] **Actualizar README.md** — arquitectura actual + instrucões de uso
- [ ] **Testar build completo** — `docker compose build` sem erros
- [ ] **Teste end-to-end** — `docker compose run --rm -it pipeline` com `Crimson Day.flac`

---

## Decisões de design

| Decisão | Escolha | Descartado |
|---|---|---|
| Arquitectura | Sincrona / TUI | FastAPI + Dramatiq + Redis (over-engineering) |
| Separação | Demucs `htdemucs_6s` | Spleeter (só 4 stems) |
| Beat tracking | BeatNet | madmom (menos preciso em ritmos complexos) |
| Pitch | Basic Pitch (Spotify) | crepe, pyin (monofónicos) |
| Notação | LilyPond (nativo bateria) + music21 (melódicos) | Abjad, MuseScore |
| Orquestrador | pipeline container + Docker socket | shell script no host |
| Detecção instrumentos | RMS dos stems Demucs | MIRFLEX / Essentia (AGPL) |
