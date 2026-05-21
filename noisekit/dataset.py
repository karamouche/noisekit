from __future__ import annotations

import io
import itertools

import numpy as np
import soundfile as sf


def load_samples(
    dataset_name: str,
    n: int,
    seed: int,
    split: str = "train",
    config: str | None = None,
) -> list[dict]:
    from datasets import Audio, load_dataset

    kwargs: dict = dict(split=split, streaming=True)
    ds = load_dataset(dataset_name, config, **kwargs) if config is not None else load_dataset(dataset_name, **kwargs)

    # Disable auto-decoding so we can decode with soundfile ourselves,
    # avoiding the torchcodec requirement introduced in datasets 4.x.
    ds = ds.cast_column("audio", Audio(decode=False))
    ds = ds.shuffle(seed=seed, buffer_size=min(1000, n * 10))
    return list(itertools.islice(ds, n))


def extract_audio_and_text(sample: dict) -> tuple[np.ndarray, int, str]:
    audio_field = sample["audio"]

    raw_bytes = audio_field.get("bytes")
    path = audio_field.get("path")

    if raw_bytes:
        with sf.SoundFile(io.BytesIO(raw_bytes)) as f:
            array = f.read(dtype="float32", always_2d=False)
            sr = f.samplerate
    elif path:
        array, sr = sf.read(path, dtype="float32", always_2d=False)
    else:
        raise ValueError("Audio sample has neither 'bytes' nor 'path'.")

    text = (
        sample.get("text")
        or sample.get("sentence")
        or sample.get("transcription")
        or sample.get("normalized_text")
        or ""
    )
    return np.asarray(array, dtype=np.float32), int(sr), str(text).strip()
