"""Unit tests for settings parsing from environment variables."""

from src.infrastructure.config.settings import APISettings


class TestAPISettings:
    """Tests for APISettings.from_env()."""

    def test_uv_allow_prerelease_defaults_to_false(self, monkeypatch):
        monkeypatch.delenv("UV_ALLOW_PRERELEASE", raising=False)
        settings = APISettings.from_env()
        assert settings.uv_allow_prerelease is False

    def test_uv_allow_prerelease_true_values(self, monkeypatch):
        for value in ("1", "true", "TRUE", "yes", "on"):
            monkeypatch.setenv("UV_ALLOW_PRERELEASE", value)
            settings = APISettings.from_env()
            assert settings.uv_allow_prerelease is True
