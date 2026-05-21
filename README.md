# Musikplus

Transcrição automática de música para partitura PDF.

Detecta os instrumentos presentes numa música, isola o stem escolhido e gera uma partitura em PDF — tudo dentro de containers Docker, orquestrado por uma TUI interactiva.

## Pipeline

```
TUI (pipeline container)
  │
  ├─► detector        Demucs htdemucs_6s → mede energia por stem
  │                   → mostra tabela: quais instrumentos estão presentes
  │
  ├─► demucs          isola o stem escolhido → chosen.wav
  │
  ├─► analyzer        BeatNet + librosa  (bateria)
  │   analyzer-pitch  Basic Pitch/Spotify (baixo, guitarra, piano, voz)
  │
  └─► sheet           LilyPond → PDF
```

## Ferramentas

| Etapa | Ferramenta |
|---|---|
| Separação de stems | [Demucs](https://github.com/adefossez/demucs) `htdemucs_6s` (6 stems) |
| Beat tracking | [BeatNet](https://github.com/mjhydri/BeatNet) (ISMIR 2021) |
| Pitch polifónico | [Basic Pitch](https://github.com/spotify/basic-pitch) (Spotify) |
| Notação | [LilyPond](https://lilypond.org/) + [music21](https://web.mit.edu/music21/) |
| TUI | [Rich](https://github.com/Textualize/rich) + [questionary](https://github.com/tmbo/questionary) |

## Requisitos

- Docker + Docker Compose
- Ficheiros de audio em `./audio/` (`.flac`, `.mp3`, `.wav`, `.ogg`, `.m4a`)

## Uso

```bash
# 1. Build de todas as imagens (só na primeira vez)
docker compose build

# 2. Lançar a TUI
docker compose run --rm -it pipeline
```

A TUI:
1. Lista os ficheiros em `./audio/`
2. Pede o título e duração máxima a analisar
3. Corre o detector — mostra uma tabela com os instrumentos detectados e os seus níveis de energia
4. Pergunta qual instrumento transcrever
5. Isola o stem, analisa e gera o PDF
6. O PDF aparece em `./output/`

## Estrutura

```
services/
├── pipeline/        TUI orquestrador (Rich + questionary + Docker CLI)
├── detector/        Demucs 6s + RMS → instruments.json
├── demucs/          Copia stem escolhido → chosen.wav
├── analyzer/        BeatNet + librosa → analysis.json       (bateria)
├── analyzer-pitch/  Basic Pitch → analysis.mid + .json      (outros)
└── sheet/           LilyPond / music21+LilyPond → sheet.pdf

audio/               coloque aqui os ficheiros de audio
output/              PDFs gerados
```

## Formatos de audio suportados

`.flac` `.mp3` `.wav` `.ogg` `.m4a` `.aiff`

> FLAC e WAV dão melhores resultados por serem sem perda.

## Instrumentos suportados

| Instrumento | Análise | Notação |
|---|---|---|
| Bateria | BeatNet + librosa (kick/snare/hihat) | LilyPond drum notation |
| Baixo | Basic Pitch | Clave de fá |
| Guitarra | Basic Pitch | Clave de sol |
| Piano | Basic Pitch | Grand staff |
| Voz | Basic Pitch | Clave de sol |

## Configuração

Copiar `.env.example` para `.env` e ajustar:

```env
DEMUCS_MODEL=htdemucs_6s        # htdemucs (4 stems) ou htdemucs_6s (6 stems)
MAX_DURATION=300                 # segundos máximos a analisar
DETECTOR_THRESHOLD_DB=-40        # stems abaixo deste RMS = não presente
```
