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
    assert len(presets) == 4
    names = {p["name"] for p in presets}
    assert "clean_reference" in names
    assert "telecommunication" in names
    assert "bad_audio_encoding" in names
    assert "noisy_environment" in names
