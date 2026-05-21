from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="noisekit",
    help="Generate noise-stratified speech datasets for ASR benchmark studies.",
    add_completion=False,
)
console = Console()


@app.command()
def generate(
    dataset: Annotated[str, typer.Option(help="HuggingFace dataset name (e.g. google/fleurs)")],
    samples: Annotated[int, typer.Option(help="Number of source samples to process")] = 100,
    presets: Annotated[Optional[List[str]], typer.Option(help="Preset name(s) to apply. Repeatable.")] = None,
    output: Annotated[Optional[Path], typer.Option(help="Output directory. Omit to auto-create ./output/<timestamp>/")] = None,
    seed: Annotated[int, typer.Option(help="Random seed for dataset shuffling")] = 42,
    split: Annotated[str, typer.Option(help="Dataset split (e.g. train, validation, test)")] = "train",
    config: Annotated[Optional[str], typer.Option(help="HuggingFace dataset config name")] = None,
    preset_file: Annotated[Optional[Path], typer.Option(help="Path to a custom preset YAML file")] = None,
    noise_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--noise-dir",
            help=(
                "Directory of background-noise WAVs (e.g. MUSAN, DEMAND, FSD50K). "
                "Used by noisy_environment. If omitted, a small MUSAN music+noise "
                "subset is auto-downloaded to ~/.cache/noisekit/ on first use."
            ),
        ),
    ] = None,
) -> None:
    """Generate a degraded speech dataset by applying audio presets to a clean source dataset."""
    from .pipeline import run_generate

    resolved_output = output if output is not None else Path("./output") / datetime.now().strftime("%Y-%m-%d_%H%M%S")

    run_generate(
        dataset=dataset,
        samples=samples,
        presets=list(presets) if presets else [],
        output=resolved_output,
        seed=seed,
        split=split,
        config=config,
        preset_file=preset_file,
        noise_dir=noise_dir,
    )


@app.command()
def score(
    input_dir: Annotated[Path, typer.Argument(help="Directory containing WAV files to score")],
    reference_dir: Annotated[
        Optional[Path],
        typer.Option(help="Directory with matching reference WAVs (enables PESQ + SNR scoring)"),
    ] = None,
    output: Annotated[Path, typer.Option(help="Output JSON path for scores")] = Path("./scores.json"),
) -> None:
    """Compute quality scores (PESQ, SNR) for an existing audio folder."""
    from .pipeline import run_score

    if not input_dir.exists():
        console.print(f"[red]Input directory not found: {input_dir}[/red]")
        raise typer.Exit(1)

    run_score(input_dir=input_dir, reference_dir=reference_dir, output=output)


@app.command("list-presets")
def list_presets(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show full transform list for each preset")] = False,
) -> None:
    """Print all available built-in presets and their transform stacks."""
    from .transforms import list_builtin_presets

    presets = list_builtin_presets()

    table = Table(title="Built-in Presets", show_lines=True)
    table.add_column("Name", style="bold cyan", no_wrap=True)
    table.add_column("Description")
    if verbose:
        table.add_column("Transforms")

    for p in presets:
        transforms_str = " → ".join(
            f"{t['type']}(p={t.get('p', 1.0)})" for t in p.get("transforms", [])
        )
        if verbose:
            table.add_row(p["name"], p["description"], transforms_str)
        else:
            table.add_row(p["name"], p["description"])

    console.print(table)
    console.print(f"\n[dim]{len(presets)} built-in presets. Pass a custom preset with --preset-file ./my.yaml[/dim]")
