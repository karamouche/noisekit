"""Auto-download and cache MUSAN noise-only clips for noise.

Only the `noise` class (wind, rain, traffic, machinery…) is downloaded.
Speech and music are both excluded: speech pollutes ASR/PESQ scoring;
music sounds artificial as a background and can be mistaken for white noise.
"""

from __future__ import annotations

import random
from pathlib import Path

import soundfile as sf
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

DEFAULT_NOISE_HF_DATASET = "Aynursusuz/musan-audio-dataset"
DEFAULT_NOISE_NUM_SAMPLES = 20  # ~120 MB at ~6 MB/file
_NOISE_LABEL = 2  # ClassLabel order: speech (0), music (1), noise (2)
_N_SHARDS = 45  # total parquet shards in Aynursusuz/musan-audio-dataset
_FIRST_AMBIENT_SHARD = _N_SHARDS // 2  # speech occupies shards 0-21; music+noise start at 22

console = Console()


def get_default_noise_cache_dir() -> Path:
    return Path.home() / ".cache" / "noisekit" / "noise" / "musan_ambient"


def ensure_default_noise_dir(num_samples: int = DEFAULT_NOISE_NUM_SAMPLES) -> Path:
    """Return a directory of MUSAN noise-only WAVs, downloading on first use."""
    cache_dir = get_default_noise_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(cache_dir.glob("*.wav"))
    if len(existing) >= num_samples:
        return cache_dir

    needed = num_samples - len(existing)
    console.print(
        f"[cyan]No --noise-dir provided. Fetching {needed} MUSAN noise sample(s) "
        f"(wind/rain/traffic/machinery, no speech or music) from "
        f"[bold]{DEFAULT_NOISE_HF_DATASET}[/bold] "
        f"→ {cache_dir} (one-time, ~{needed * 6} MB)…[/cyan]"
    )

    from datasets import load_dataset

    # Load only music+noise shards by URL — speech shards (0-21) are never fetched.
    # Within shards 22-44 the dataset is sorted music-first then noise; shuffle the
    # shard list so we hit noise-heavy shards early and don't exhaust the quota on music.
    data_files = [
        f"hf://datasets/{DEFAULT_NOISE_HF_DATASET}/data/train-{i:05d}-of-{_N_SHARDS:05d}.parquet"
        for i in range(_FIRST_AMBIENT_SHARD, _N_SHARDS)
    ]
    random.shuffle(data_files)
    ds = load_dataset("parquet", data_files={"train": data_files}, split="train", streaming=True)
    ds = ds.filter(lambda x: x["label"] == _NOISE_LABEL)
    ds = ds.shuffle(buffer_size=200)
    saved = len(existing)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Waiting for first shard…", total=needed)
        for row in ds:
            if saved >= num_samples:
                break
            audio = row["audio"]
            out_path = cache_dir / f"musan_noise_{saved:04d}.wav"
            sf.write(out_path, audio["array"], audio["sampling_rate"], subtype="PCM_16")
            saved += 1
            progress.update(task, advance=1, description=f"Saved {out_path.name}")

    if saved < num_samples:
        console.print(
            f"[yellow]Warning:[/yellow] obtained {saved}/{num_samples} noise samples "
            f"from {DEFAULT_NOISE_HF_DATASET}. AddBackgroundNoise will still work."
        )
    else:
        console.print(f"[green]Cached {saved} MUSAN noise WAVs.[/green]")

    return cache_dir
