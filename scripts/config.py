"""Configuration discovery and normalization for wechat-sticker-album."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PROJECT_CONFIG_DIR = ".wechat-sticker-album"
PROJECT_CONFIG_NAME = "config.json"
ENV_CONFIG_PATH = "WECHAT_STICKER_CONFIG"
ENV_BASE_URL = "WECHAT_STICKER_IMAGE_BASE_URL"
ENV_MODEL = "WECHAT_STICKER_IMAGE_MODEL"
ENV_API_KEY = "WECHAT_STICKER_IMAGE_API_KEY"
ENV_PROFILE = "WECHAT_STICKER_PROFILE"


class ConfigError(RuntimeError):
    """A user-correctable configuration error."""


@dataclass
class ProviderProfile:
    name: str
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    api_key_env: str | None = None
    generation_endpoint: str = "/images/generations"
    edit_endpoint: str = "/images/edits"
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer "
    image_field: str = "image"
    timeout_seconds: int = 300
    capabilities: dict[str, Any] = field(default_factory=dict)
    extra_headers: dict[str, str] = field(default_factory=dict)
    extra_generation: dict[str, Any] = field(default_factory=dict)
    extra_edit: dict[str, Any] = field(default_factory=dict)
    fallback_profiles: list[str] = field(default_factory=list)
    custom_request: dict[str, Any] | None = None
    custom_response: dict[str, Any] | None = None

    @property
    def supports_reference_images(self) -> bool:
        return bool(self.capabilities.get("supports_reference_images", True))

    @property
    def supports_transparent_background(self) -> bool:
        return bool(self.capabilities.get("supports_transparent_background", False))


@dataclass
class AppSettings:
    config_path: Path | None
    default_profile: str
    profiles: dict[str, ProviderProfile]

    def selected_profile(self, name: str | None = None) -> ProviderProfile:
        selected = name or os.environ.get(ENV_PROFILE) or self.default_profile
        if selected not in self.profiles:
            raise ConfigError(
                f"Unknown profile {selected!r}. Available: "
                + ", ".join(sorted(self.profiles))
            )
        return self.profiles[selected]


def user_config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "wechat-sticker-album" / "config.json"


def project_config_path(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / PROJECT_CONFIG_DIR / PROJECT_CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def discover_config(explicit: str | Path | None = None) -> Path | None:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if not candidate.is_file():
            raise ConfigError(f"Config file does not exist: {candidate}")
        return candidate
    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if not candidate.is_file():
            raise ConfigError(f"Config file from {ENV_CONFIG_PATH} does not exist: {candidate}")
        return candidate
    return project_config_path() or (
        user_config_path() if user_config_path().is_file() else None
    )


def _resolve_api_key(raw: dict[str, Any], env_name: str | None) -> str | None:
    if env_name:
        value = os.environ.get(env_name)
        if value:
            return value
    env_value = os.environ.get(ENV_API_KEY)
    if env_value:
        return env_value
    value = raw.get("api_key")
    return str(value) if value else None


def _build_profile(name: str, raw: dict[str, Any]) -> ProviderProfile:
    base_url = str(raw.get("base_url") or "").strip()
    model = str(raw.get("model") or "").strip()
    provider = str(raw.get("provider") or "openai-compatible").strip()
    if not base_url:
        raise ConfigError(f"Profile {name!r} is missing base_url")
    if not model:
        raise ConfigError(f"Profile {name!r} is missing model")
    capabilities = raw.get("capabilities") or {}
    if not isinstance(capabilities, dict):
        raise ConfigError(f"Profile {name!r} capabilities must be an object")
    return ProviderProfile(
        name=name,
        provider=provider,
        base_url=base_url.rstrip("/"),
        model=model,
        api_key=_resolve_api_key(raw, raw.get("api_key_env")),
        api_key_env=str(raw["api_key_env"]) if raw.get("api_key_env") else None,
        generation_endpoint=str(raw.get("generation_endpoint") or "/images/generations"),
        edit_endpoint=str(raw.get("edit_endpoint") or "/images/edits"),
        api_key_header=str(raw.get("api_key_header") or "Authorization"),
        api_key_prefix=str(raw.get("api_key_prefix", "Bearer ")),
        image_field=str(raw.get("image_field") or "image"),
        timeout_seconds=int(raw.get("timeout_seconds") or 300),
        capabilities=capabilities,
        extra_headers={
            str(key): str(value)
            for key, value in (raw.get("extra_headers") or {}).items()
        },
        extra_generation=dict(raw.get("extra_generation") or {}),
        extra_edit=dict(raw.get("extra_edit") or {}),
        fallback_profiles=[
            str(value) for value in (raw.get("fallback_profiles") or [])
        ],
        custom_request=raw.get("custom_request"),
        custom_response=raw.get("custom_response"),
    )


def _settings_from_env() -> AppSettings | None:
    base_url = os.environ.get(ENV_BASE_URL)
    model = os.environ.get(ENV_MODEL)
    if not base_url and not model:
        return None
    if not base_url or not model:
        raise ConfigError(
            f"Both {ENV_BASE_URL} and {ENV_MODEL} are required for environment-only setup"
        )
    profile = _build_profile(
        "env",
        {
            "provider": "openai-compatible",
            "base_url": base_url,
            "model": model,
            "api_key_env": ENV_API_KEY,
        },
    )
    return AppSettings(config_path=None, default_profile="env", profiles={"env": profile})


def load_settings(
    explicit_path: str | Path | None = None,
    profile_override: str | None = None,
) -> tuple[AppSettings, ProviderProfile]:
    path = discover_config(explicit_path)
    if path is None:
        settings = _settings_from_env()
        if settings is None:
            raise ConfigError(
                "No image API configuration found. Run `python scripts/cli.py init --project-root <project>`, "
                "or set WECHAT_STICKER_IMAGE_BASE_URL and WECHAT_STICKER_IMAGE_MODEL."
            )
    else:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON config: {path}") from exc
        if not isinstance(raw, dict):
            raise ConfigError("Config root must be a JSON object")
        profiles_raw = raw.get("profiles")
        if not isinstance(profiles_raw, dict) or not profiles_raw:
            raise ConfigError("Config must contain a non-empty profiles object")
        profiles = {
            str(name): _build_profile(str(name), value)
            for name, value in profiles_raw.items()
            if isinstance(value, dict)
        }
        if not profiles:
            raise ConfigError("Config contains no valid provider profiles")
        default_profile = str(raw.get("default_profile") or next(iter(profiles)))
        settings = AppSettings(path, default_profile, profiles)

    return settings, settings.selected_profile(profile_override)


def sanitized_profile(profile: ProviderProfile) -> dict[str, Any]:
    return {
        "name": profile.name,
        "provider": profile.provider,
        "base_url": profile.base_url,
        "model": profile.model,
        "api_key_present": bool(profile.api_key),
        "capabilities": profile.capabilities,
        "fallback_profiles": profile.fallback_profiles,
    }
