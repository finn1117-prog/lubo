from pathlib import Path

from app.core.runtime import paths


def test_prepare_user_data_preserves_mutable_config(monkeypatch, tmp_path: Path):
    resources = tmp_path / "resources"
    data = tmp_path / "data"
    (resources / "config").mkdir(parents=True)
    (resources / "locales").mkdir(parents=True)
    (data / "config").mkdir(parents=True)
    (resources / "config" / "cookies.json").write_text("{}", encoding="utf-8")
    (resources / "config" / "version.json").write_text('{"version":"new"}', encoding="utf-8")
    (resources / "locales" / "zh_CN.json").write_text('{"label":"new"}', encoding="utf-8")
    (data / "config" / "cookies.json").write_text('{"saved":"cookie"}', encoding="utf-8")
    (data / "config" / "version.json").write_text('{"version":"old"}', encoding="utf-8")

    monkeypatch.setattr(paths, "resource_dir", resources)
    monkeypatch.setattr(paths, "user_data_dir", data)
    monkeypatch.setattr(paths, "prepare_bundled_ffmpeg", lambda: None)
    monkeypatch.setattr(paths, "prepare_bundled_node", lambda: None)
    paths.prepare_user_data_dir()

    assert (data / "config" / "cookies.json").read_text(encoding="utf-8") == '{"saved":"cookie"}'
    assert (data / "config" / "version.json").read_text(encoding="utf-8") == '{"version":"new"}'
    assert (data / "locales" / "zh_CN.json").read_text(encoding="utf-8") == '{"label":"new"}'
