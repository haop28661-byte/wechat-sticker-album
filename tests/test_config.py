from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from config import ConfigError, load_settings, project_config_path  # noqa: E402


def write_config(project: Path) -> Path:
    path = project / ".wechat-sticker-album" / "config.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "default_profile": "fast",
                "profiles": {
                    "fast": {
                        "provider": "openai-compatible",
                        "base_url": "https://example.test/v1/",
                        "model": "test-fast",
                        "api_key_env": "TEST_IMAGE_KEY",
                        "fallback_profiles": ["quality"],
                    },
                    "quality": {
                        "provider": "openai-compatible",
                        "base_url": "https://example.test/v1",
                        "model": "test-quality",
                        "api_key_env": "TEST_IMAGE_KEY",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_project_config_is_found_from_nested_directory(tmp_path, monkeypatch):
    expected = write_config(tmp_path)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    monkeypatch.setenv("TEST_IMAGE_KEY", "secret")
    assert project_config_path() == expected
    settings, profile = load_settings()
    assert settings.config_path == expected
    assert settings.default_profile == "fast"
    assert profile.model == "test-fast"
    assert profile.api_key == "secret"
    assert profile.fallback_profiles == ["quality"]


def test_profile_override_and_env_only(tmp_path, tmp_path_factory, monkeypatch):
    write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TEST_IMAGE_KEY", "secret")
    _, profile = load_settings(profile_override="quality")
    assert profile.model == "test-quality"

    empty = tmp_path_factory.mktemp("outside-project")
    monkeypatch.chdir(empty)
    monkeypatch.setenv("WECHAT_STICKER_IMAGE_BASE_URL", "https://env.test/v1")
    monkeypatch.setenv("WECHAT_STICKER_IMAGE_MODEL", "env-model")
    monkeypatch.setenv("WECHAT_STICKER_IMAGE_API_KEY", "env-key")
    settings, profile = load_settings()
    assert settings.config_path is None
    assert profile.model == "env-model"
    assert profile.api_key == "env-key"


def test_missing_config_has_actionable_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WECHAT_STICKER_CONFIG", raising=False)
    monkeypatch.delenv("WECHAT_STICKER_IMAGE_BASE_URL", raising=False)
    monkeypatch.delenv("WECHAT_STICKER_IMAGE_MODEL", raising=False)
    try:
        load_settings()
    except ConfigError as exc:
        assert "cli.py init" in str(exc)
    else:
        raise AssertionError("Expected ConfigError")


def test_api_key_can_be_loaded_from_json_file(tmp_path, monkeypatch):
    monkeypatch.delenv("WECHAT_STICKER_IMAGE_API_KEY", raising=False)
    credentials = tmp_path / "credentials.json"
    credentials.write_text(
        json.dumps({"nested": {"key": "file-secret"}}),
        encoding="utf-8",
    )
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "default_profile": "main",
                "profiles": {
                    "main": {
                        "base_url": "https://example.test/v1",
                        "model": "test-model",
                        "api_key_file": str(credentials),
                        "api_key_json_path": "nested.key",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    _, profile = load_settings(config)
    assert profile.api_key == "file-secret"
    assert profile.api_key_file == str(credentials)
