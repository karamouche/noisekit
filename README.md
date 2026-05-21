# noisekit

Generate noise-stratified speech datasets for ASR benchmark studies.

Takes a clean speech-to-text dataset from HuggingFace, applies real-world degradation presets via [audiomentations](https://github.com/iver56/audiomentations), and scores each output with PESQ + SNR — producing a JSONL manifest ready for noise-robustness benchmarking.

Three scenarios are covered out of the box: **telecommunication** (G.711 + low-bitrate MP3 codec artifacts), **bad audio encoding** (aggressive low-bitrate compression), and **noisy environment** (real ambient noise from a user-supplied corpus).

## Install

No installation needed. Run directly with `uvx`:

```bash
uvx noisekit --help
```

Or install for development:

```bash
git clone ...
cd noisekit
uv sync
uv run noisekit --help
```

## Usage

### Generate a degraded dataset

```bash
uvx noisekit generate \
  --dataset google/fleurs \
  --config en_us \
  --split test \
  --samples 300 \
  --presets telecommunication bad_audio_encoding \
  --output ./benchmark_dataset \
  --seed 42
```

For `noisy_environment`, supply a directory of real noise WAVs (e.g. [MUSAN](https://www.openslr.org/17/), [DEMAND](https://zenodo.org/record/1227121), or [FSD50K](https://zenodo.org/record/4060432)):

```bash
uvx noisekit generate \
  --dataset google/fleurs --config en_us --split test \
  --samples 300 --presets noisy_environment \
  --noise-dir ~/datasets/musan/noise \
  --output ./benchmark_dataset --seed 42
```

Output:

```
benchmark_dataset/
├── manifest.jsonl          # one entry per generated file
└── audio/
    ├── sample_0000_telecommunication.wav
    ├── sample_0001_bad_audio_encoding.wav
    └── ...
```

Each manifest entry:

```json
{
  "audio": "sample_0042_telecommunication.wav",
  "transcript": "the cat sat on the mat",
  "preset": "telecommunication",
  "snr_db": 5.2,
  "pesq_mos": 2.78
}
```

### Score an existing audio folder

```bash
# File stats only (duration, RMS, peak)
uvx noisekit score ./audio_folder --output scores.json

# With PESQ + SNR (requires matching reference files)
uvx noisekit score ./audio_folder --reference-dir ./clean_audio --output scores.json
```

### List available presets

```bash
uvx noisekit list-presets
uvx noisekit list-presets --verbose   # show full transform stack
```

## Presets

Four built-in presets — three real-world scenarios plus a clean control. None use synthetic white noise; codec artifacts and real ambient recordings produce the degradation instead.

| Preset               | Description                                                              | PESQ       |
| -------------------- | ------------------------------------------------------------------------ | ---------- |
| `clean_reference`    | Minimal processing (PESQ ceiling / control)                              | 4.0-4.5    |
| `telecommunication`  | G.711-style call: 8 kHz bandpass + 8-bit BitCrush + 16-32 kbps MP3 codec | NB 2.0-3.5 |
| `bad_audio_encoding` | Wideband audio crushed by 16-32 kbps MP3 compression                     | WB 1.5-2.5 |
| `noisy_environment`  | Real ambient noise from `--noise-dir` mixed in at SNR 3-20 dB            | WB 1.0-2.5 |

`telecommunication` is scored with PESQ narrowband at 8 kHz (before the final upsample); all other presets are scored wideband at 16 kHz.

`noisy_environment` requires `--noise-dir` to point at a directory of background-noise WAVs (e.g. MUSAN, DEMAND, FSD50K). The preset uses [`AddBackgroundNoise`](https://iver56.github.io/audiomentations/waveform_transforms/add_background_noise/) under the hood.

### Custom presets

Pass your own YAML file with `--preset-file`:

```bash
uvx noisekit generate \
  --dataset google/fleurs \
  --samples 100 \
  --preset-file ./my_preset.yaml \
  --output ./output
```

Preset format:

```yaml
name: my_preset
description: "Custom telephony simulation"
transforms:
  - type: Resample
    parameters:
      min_sample_rate: 8000
      max_sample_rate: 8000
    p: 1.0
  - type: Mp3Compression
    parameters:
      min_bitrate: 16
      max_bitrate: 32
      backend: lameenc
    p: 1.0
  - type: Resample
    parameters:
      min_sample_rate: 16000
      max_sample_rate: 16000
    p: 1.0
```

Any transform from [audiomentations](https://github.com/iver56/audiomentations) is supported. If your preset ends with `Resample(16000)`, PESQ is computed at the 8 kHz intermediate stage for accurate stratification — see [CLAUDE.md](CLAUDE.md) for details.

To reference a noise-dir from a custom preset (e.g. for `AddBackgroundNoise`), use the literal placeholder `${NOISE_DIR}` — it is substituted with `--noise-dir` at load time.

## Benchmark table

Typical results on LibriSpeech:

| Preset               | PESQ (mean) |
| -------------------- | ----------- |
| `clean_reference`    | 4.4 (WB)    |
| `telecommunication`  | 2.8 (NB)    |
| `bad_audio_encoding` | 2.0 (WB)    |
| `noisy_environment`  | 1.5 (WB)    |

## Requirements

- Python ≥ 3.10
- [uv](https://docs.astral.sh/uv/) for `uvx` usage

## Roadmap

- **v2**: NISQA scoring (`nisqa_mos`, `nisqa_noisiness`, `nisqa_discontinuity`)
- **v2**: CommonVoice dataset support
