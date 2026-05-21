# noisekit — Claude Instructions

**Always update this file when making notable changes** (new commands, new presets, architectural decisions, scoring changes, dependency additions).

## Project

`noisekit` is a `uvx`-compatible Python CLI that generates degraded speech datasets from clean HuggingFace corpora. It simulates three real-world audio degradation scenarios — telecommunication (G.711 calls), bad audio encoding (low-bitrate codecs), and noisy environments (real ambient noise) — for ASR noise-robustness benchmarking. A `clean_reference` control completes the catalog.

## Package Management

Use **UV** for everything: `uv add`, `uv run`, `uv sync`. Never use pip directly.

Key runtime dependencies: `audiomentations>=0.38`, `lameenc>=1.4` (pure-Python MP3 encoder used by `Mp3Compression` in `telecommunication` and `bad_audio_encoding`; no system ffmpeg needed).

## Architecture

```
noisekit/
├── cli.py          # Typer app — 3 commands: generate, score, list-presets
├── pipeline.py     # generate + score logic
├── dataset.py      # HuggingFace dataset loading (soundfile decoder, no torchcodec)
├── transforms.py   # Preset loading; returns PresetTransforms(full, scoring, scoring_sr)
├── scoring.py      # PESQ + SNR; PESQ NB at 8 kHz for telephony presets
└── presets/        # YAML preset files bundled with the package
```

## CLI

```bash
noisekit generate --dataset <hf-name> --samples N --presets P1 P2 --output ./out --seed 42
noisekit generate ... --presets noisy_environment --noise-dir /path/to/noise_wavs
noisekit score ./audio_dir [--reference-dir ./ref] [--output scores.json]
noisekit list-presets [--verbose]
```

Custom presets: `--preset-file ./my_preset.yaml`

The `noisy_environment` preset requires `--noise-dir` pointing at a directory of background-noise WAVs (e.g. MUSAN, DEMAND, FSD50K). Inside a preset YAML, use the literal string `${NOISE_DIR}` as a parameter value and `transforms.load_preset` substitutes the CLI value at load time.

## Preset YAML Format

```yaml
name: my_preset
description: "..."
transforms:
  - type: <audiomentations class>
    parameters:
      key: value
    p: 1.0
```

Built-in presets:

| Preset               | Scenario                                     | Bandwidth           | PESQ mode | Target MOS |
| -------------------- | -------------------------------------------- | ------------------- | --------- | ---------- |
| `clean_reference`    | Minimal gain normalization (PESQ ceiling)    | full                | WB 16 kHz | 4.0-4.5    |
| `telecommunication`  | G.711 call + low-bitrate MP3 codec artifacts | 300-3400 Hz @ 8 kHz | NB 8 kHz  | 2.0-3.5    |
| `bad_audio_encoding` | Aggressive low-bitrate MP3 (16-32 kbps)      | 80-7500 Hz @ 16 kHz | WB 16 kHz | 1.5-2.5    |
| `noisy_environment`  | Real ambient noise via `AddBackgroundNoise`  | up to 8-12 kHz      | WB 16 kHz | 1.0-2.5    |

`telecommunication` uses the 8 kHz PESQ NB scoring split (see below). All other presets score in PESQ WB at 16 kHz.

### Why no white noise

The catalog deliberately avoids `AddGaussianSNR` — white Gaussian noise sounds artificial and doesn't reflect real production audio. Instead:

- `telecommunication` and `bad_audio_encoding` rely on `Mp3Compression` at 16-32 kbps for realistic codec smearing/pre-echo.
- `noisy_environment` uses `AddBackgroundNoise` over a user-supplied WAV corpus (MUSAN/DEMAND/FSD50K), so the noise floor matches the real environment you care about.

## PESQ Scoring — Important Design Decision

For `telecommunication`, PESQ is computed at **8 kHz narrowband** on the audio **before** the final `Resample(16000)` restoration step. Output WAV files are still saved at 16 kHz.

**Why:** Computing PESQ NB by downsampling the 16 kHz output (8k→16k→8k round-trip) collapses all telephony scores to ~1.1 regardless of noise level. Scoring at the 8 kHz intermediate stage gives proper stratification.

**BitCrush + Normalize:** `telecommunication` inserts `Normalize(p=1.0)` immediately before `BitCrush`. HuggingFace speech datasets (e.g., FLEURS) often have very low peak amplitude (~0.001-0.02). At 8-bit depth the quantization step is 0.0078 — a peak below one step rounds the entire signal to zero. Normalizing to ±1 before quantization ensures all 256 levels are used.

`transforms.py` auto-detects this split: if the last transform is `Resample(16000)`, it creates a `scoring` Compose (all-but-last) alongside the `full` Compose.

## Dataset Loading

Uses `datasets` with `Audio(decode=False)` + manual `soundfile` decoding — avoids the `torchcodec` requirement introduced in `datasets` 4.x.

## Output Format

`manifest.jsonl` — one JSON object per generated file:

```json
{
  "audio": "sample_0000_telecommunication.wav",
  "transcript": "...",
  "preset": "telecommunication",
  "snr_db": 1.8,
  "pesq_mos": 2.86
}
```

NISQA fields (`nisqa_mos`, `nisqa_noisiness`, `nisqa_discontinuity`) are deferred to v2.

## Verification

```bash
uv run noisekit list-presets --verbose

# Codec-only presets (no noise dir needed)
uv run noisekit generate \
  --dataset google/fleurs \
  --config en_us --split test \
  --samples 3 --presets clean_reference telecommunication bad_audio_encoding \
  --output ./test_out --seed 42
cat test_out/manifest.jsonl

# noisy_environment with a real noise corpus
uv run noisekit generate \
  --dataset google/fleurs --config en_us --split test \
  --samples 3 --presets noisy_environment \
  --noise-dir ~/datasets/musan/noise \
  --output ./test_noise --seed 42
```

Expected PESQ spread: clean ~4.6, telecommunication ~2.5-3.5 (NB), bad_audio_encoding ~1.5-2.5 (WB), noisy_environment ~1.0-2.5 (WB).
