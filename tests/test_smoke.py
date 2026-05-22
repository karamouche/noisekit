from __future__ import annotations


def test_import_noisekit() -> None:
    import noisekit

    assert isinstance(noisekit.__version__, str)


def test_cli_app_exists() -> None:
    from noisekit.cli import app

    assert app is not None


def test_list_builtin_presets() -> None:
    from noisekit.transforms import list_builtin_presets

    presets = list_builtin_presets()
    assert len(presets) == 9
    names = {p["name"] for p in presets}
    assert "clean_reference" in names
    assert "telecom" in names
    assert "low_bitrate" in names
    assert "noise" in names
    assert "clipping" in names
    assert "reverb" in names
    assert "noise_telecom" in names
    assert "noise_reverb" in names
    assert "clipping_telecom" in names


def test_load_compound_preset_scoring_split(tmp_path) -> None:
    import numpy as np
    import soundfile as sf

    from noisekit.transforms import load_preset

    # AddBackgroundNoise scans sounds_path at construction — write a minimal WAV.
    sf.write(tmp_path / "noise.wav", np.zeros(16000, dtype=np.float32), 16000)

    # noise_telecom chains noise → telecom.
    # The concatenated transform list ends with Resample(16000), so the NB 8 kHz
    # scoring split should be detected automatically.
    pt = load_preset("noise_telecom", noise_dir=tmp_path)
    assert pt.scoring is not None, "noise_telecom should inherit telecom's NB scoring split"
    assert pt.scoring_sr == 8000, "scoring_sr should be 8000 from telecom's Resample"
