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
    assert len(presets) == 10
    names = {p["name"] for p in presets}
    assert "clean_reference" in names
    assert "telecom" in names
    assert "low_bitrate" in names
    assert "noisy_environment" in names
    assert "clipping_distortion" in names
    assert "transmission_dropout" in names
    assert "reverb_far_field" in names
    assert "noisy_telecom" in names
    assert "reverb_noisy" in names
    assert "clipping_telecom" in names


def test_load_compound_preset_scoring_split(tmp_path) -> None:
    import numpy as np
    import soundfile as sf

    from noisekit.transforms import load_preset

    # AddBackgroundNoise scans sounds_path at construction — write a minimal WAV.
    sf.write(tmp_path / "noise.wav", np.zeros(16000, dtype=np.float32), 16000)

    # noisy_telecom chains noisy_environment → telecom.
    # The concatenated transform list ends with Resample(16000), so the NB 8 kHz
    # scoring split should be detected automatically.
    pt = load_preset("noisy_telecom", noise_dir=tmp_path)
    assert pt.scoring is not None, "noisy_telecom should inherit telecom's NB scoring split"
    assert pt.scoring_sr == 8000, "scoring_sr should be 8000 from telecom's Resample"
