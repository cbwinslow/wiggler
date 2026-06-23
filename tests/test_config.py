from crawltop.config import get_settings


def test_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("CRAWLTOP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CRAWLTOP_DB_PATH", str(tmp_path / "data" / "crawltop.db"))
    settings = get_settings()
    assert settings.data_dir.exists()
    assert settings.db_path.parent.exists()
