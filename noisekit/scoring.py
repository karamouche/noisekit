from __future__ import annotations

import numpy as np


def compute_snr_db(ref: np.ndarray, deg: np.ndarray) -> float:
    min_len = min(len(ref), len(deg))
    ref = ref[:min_len].astype(np.float64)
    deg = deg[:min_len].astype(np.float64)
    noise = deg - ref
    signal_power = float(np.mean(ref ** 2))
    noise_power = float(np.mean(noise ** 2))
    if noise_power < 1e-10:
        return 99.0
    return float(10.0 * np.log10(signal_power / noise_power))


def compute_pesq(ref: np.ndarray, deg: np.ndarray, sr: int) -> float | None:
    """Compute PESQ MOS.

    Uses narrowband mode (8 kHz) when sr == 8000, wideband (16 kHz) otherwise.
    When the pipeline passes pre-scored 8 kHz audio (captured before the final
    restoration Resample), this gives proper stratification across presets.
    """
    try:
        from pesq import pesq
    except ImportError:
        return None

    try:
        min_len = min(len(ref), len(deg))
        ref_aligned = ref[:min_len].astype(np.float32)
        deg_aligned = deg[:min_len].astype(np.float32)

        if sr == 8000:
            return float(pesq(8000, ref_aligned, deg_aligned, "nb"))

        # Wideband at 16 kHz (or resample to 16 kHz first)
        if sr != 16000:
            import librosa
            ref_aligned = librosa.resample(ref_aligned, orig_sr=sr, target_sr=16000)
            deg_aligned = librosa.resample(deg_aligned, orig_sr=sr, target_sr=16000)
            min_len = min(len(ref_aligned), len(deg_aligned))
            ref_aligned = ref_aligned[:min_len]
            deg_aligned = deg_aligned[:min_len]
        return float(pesq(16000, ref_aligned, deg_aligned, "wb"))
    except Exception:
        return None


def audio_stats(audio: np.ndarray, sr: int) -> dict:
    duration = len(audio) / sr
    rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    rms_dbfs = float(20.0 * np.log10(rms + 1e-10))
    peak = float(np.max(np.abs(audio)))
    peak_dbfs = float(20.0 * np.log10(peak + 1e-10))
    return {
        "duration_s": round(duration, 3),
        "sample_rate": sr,
        "rms_dbfs": round(rms_dbfs, 2),
        "peak_dbfs": round(peak_dbfs, 2),
    }
