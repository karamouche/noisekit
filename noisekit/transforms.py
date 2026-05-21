from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import audiomentations
import numpy as np
import yaml


class _SRTrackingCompose:
    """Drop-in for audiomentations.Compose that propagates the effective sample
    rate between transforms.

    audiomentations.Compose passes the *original* sample_rate to every transform
    in the loop, so a Resample(8000) followed by Resample(16000) becomes a no-op
    on the second step (it sees sample_rate==target and skips). We fix this by
    detecting length changes — a length change means a Resample ran, so we update
    the effective rate from the length ratio before calling the next transform.
    """

    def __init__(self, transforms: list[audiomentations.BaseWaveformTransform]) -> None:
        self._transforms = transforms

    def __call__(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        current_sr = sample_rate
        for t in self._transforms:
            prev_len = len(samples)
            samples = t(samples, current_sr)
            if len(samples) != prev_len and prev_len > 0:
                current_sr = round(current_sr * len(samples) / prev_len)
        return samples


class PresetTransforms(NamedTuple):
    full: _SRTrackingCompose
    # Same chain but without the final "restoration" Resample, for PESQ scoring
    scoring: _SRTrackingCompose | None
    # Sample rate at which `scoring` outputs audio (None if no split)
    scoring_sr: int | None


_NOISE_DIR_PLACEHOLDER = "${NOISE_DIR}"


def _resolve_params(t: dict, noise_dir: Path | None) -> dict:
    params = dict(t.get("parameters", {}))
    for k, v in params.items():
        if v == _NOISE_DIR_PLACEHOLDER:
            if noise_dir is None:
                raise ValueError(
                    f"Transform '{t['type']}' parameter '{k}' requires --noise-dir, "
                    f"but none was provided. Point it at a directory of background "
                    f"noise WAVs (e.g. MUSAN, DEMAND, or FSD50K)."
                )
            params[k] = str(noise_dir)
    return params


def _make_transform(t: dict, noise_dir: Path | None = None) -> audiomentations.BaseWaveformTransform:
    cls_name = t["type"]
    if not hasattr(audiomentations, cls_name):
        raise ValueError(
            f"Unknown audiomentations transform: '{cls_name}'. "
            f"Check the audiomentations docs for valid transform names."
        )
    cls = getattr(audiomentations, cls_name)
    params = _resolve_params(t, noise_dir)
    p = float(t.get("p", 1.0))
    return cls(p=p, **params)


def load_preset(
    name: str,
    preset_file: Path | None = None,
    noise_dir: Path | None = None,
) -> PresetTransforms:
    if preset_file is not None:
        path = preset_file
    else:
        path = Path(__file__).parent / "presets" / f"{name}.yaml"

    if not path.exists():
        raise FileNotFoundError(
            f"Preset '{name}' not found. "
            f"Run 'noisekit list-presets' to see available presets."
        )

    cfg = yaml.safe_load(path.read_text())
    t_configs = cfg["transforms"]

    full = _SRTrackingCompose([_make_transform(t, noise_dir) for t in t_configs])

    # Detect pattern: last transform is Resample back to 16 kHz.
    # In that case we split: scoring uses all-but-last (at 8 kHz), output uses full.
    # This avoids the PESQ collapse caused by double-resampling (8k→16k→8k).
    last = t_configs[-1]
    if (
        last["type"] == "Resample"
        and last.get("parameters", {}).get("min_sample_rate") == 16000
        and len(t_configs) > 1
    ):
        scoring_configs = t_configs[:-1]
        scoring = _SRTrackingCompose([_make_transform(t, noise_dir) for t in scoring_configs])
        # Infer scoring SR from the first Resample in the scoring chain
        scoring_sr = 16000
        for t in scoring_configs:
            if t["type"] == "Resample":
                scoring_sr = int(t["parameters"].get("min_sample_rate", 16000))
                break
        return PresetTransforms(full, scoring, scoring_sr)

    return PresetTransforms(full, None, None)


def list_builtin_presets() -> list[dict]:
    presets_dir = Path(__file__).parent / "presets"
    return [
        yaml.safe_load(f.read_text())
        for f in sorted(presets_dir.glob("*.yaml"))
    ]
