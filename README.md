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
  ├─► analyzer        librosa (bateria)
  │   analyzer-pitch  Basic Pitch/Spotify (baixo, guitarra, piano, voz)
  │
  └─► sheet           LilyPond → sheet_<instrumento>.pdf
```

## Ferramentas

| Etapa | Ferramenta |
|---|---|
| Separação de stems | [Demucs](https://github.com/adefossez/demucs) `htdemucs_6s` (6 stems) |
| Beat tracking | [librosa](https://librosa.org/) `beat_track` |
| Pitch polifónico | [Basic Pitch](https://github.com/spotify/basic-pitch) (Spotify) |
| Notação | [LilyPond](https://lilypond.org/) + [music21](https://web.mit.edu/music21/) |
| TUI | [Rich](https://github.com/Textualize/rich) + [questionary](https://github.com/tmbo/questionary) |
| Cache | [Redis](https://redis.io/) 7 |

## Requisitos

- Docker + Docker Compose
- Ficheiros de audio em `./audio/` (`.flac`, `.mp3`, `.wav`, `.ogg`, `.m4a`, `.aiff`)

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
5. Pergunta se quer exportar o stem isolado como WAV
6. Pergunta se quer gerar a partitura em PDF
7. Isola o stem, analisa, e gera os outputs escolhidos em `./output/`

## Cache (Redis)

Os resultados de cada etapa são guardados em Redis, indexados por ficheiro de audio. Na segunda execução do mesmo ficheiro, as etapas já concluídas são saltadas.

### Limpar a cache

**Tudo:**
```bash
docker compose exec redis redis-cli FLUSHALL
```

**Ver as chaves existentes:**
```bash
docker compose exec redis redis-cli KEYS "musikplus:*"
```

**Apagar um ficheiro específico:**
```bash
docker compose exec redis redis-cli DEL "musikplus:<fingerprint>"
```

A fingerprint é o SHA-256 dos primeiros 64 KB do ficheiro de audio (mostrada em debug se necessário).

## Estrutura

```
services/
├── pipeline/        TUI orquestrador (Rich + questionary + Docker CLI)
├── detector/        Demucs 6s + RMS → instruments.json
├── demucs/          Copia stem escolhido → chosen.wav
├── analyzer/        librosa → analysis.json                    (bateria)
├── analyzer-pitch/  Basic Pitch → analysis.mid + .json         (outros)
└── sheet/           LilyPond / music21+LilyPond → sheet_<instrumento>.pdf

audio/               coloque aqui os ficheiros de audio
output/              PDFs e WAVs gerados
```

## Formatos de audio suportados

`.flac` `.mp3` `.wav` `.ogg` `.m4a` `.aiff`

> FLAC e WAV dão melhores resultados por serem sem perda.

## Instrumentos suportados

| Instrumento | Análise | Notação |
|---|---|---|
| Bateria | librosa (kick/snare/hihat) | LilyPond drum notation |
| Baixo | Basic Pitch | Clave de fá |
| Guitarra | Basic Pitch | Clave de sol |
| Piano | Basic Pitch | Grand staff |
| Voz | Basic Pitch | Clave de sol |
