#!/usr/bin/env python3
"""Command-line entrypoint for wechat-sticker-album."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

from config import (
    ENV_API_KEY,
    ConfigError,
    discover_config,
    load_settings,
    sanitized_profile,
    user_config_path,
)
from providers import CustomHttpProvider, OpenAICompatibleProvider
from providers.openai_compatible import ProviderRequestError
from validate_album_plan import PlanError, load_and_validate


ROOT = Path(__file__).resolve().parents[1]


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def _provider_for(profile):
    if profile.provider in {"openai-compatible", "openai", "openai-images"}:
        return OpenAICompatibleProvider(profile)
    if profile.provider in {"custom-http", "custom"}:
        return CustomHttpProvider(profile)
    raise ConfigError(f"Unsupported provider type: {profile.provider}")


def _write_image(data: bytes, output: Path, output_format: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(BytesIO(data)) as image:
        image.load()
        if output_format.lower() in {"jpg", "jpeg"}:
            image.convert("RGB").save(output, format="JPEG", quality=95, subsampling=0)
        elif output_format.lower() == "webp":
            image.convert("RGBA").save(output, format="WEBP", quality=95, method=6)
        else:
            image.convert("RGBA").save(output, format="PNG", optimize=True)


def command_doctor(args: argparse.Namespace) -> int:
    settings, profile = load_settings(args.config, args.profile)
    result = {
        "config": str(settings.config_path) if settings.config_path else "environment",
        "default_profile": settings.default_profile,
        "profile": sanitized_profile(profile),
        "api_key_environment_variable": profile.api_key_env or ENV_API_KEY,
    }
    if args.probe:
        if not profile.api_key:
            result["probe"] = {"ok": False, "error": "API key is not configured"}
        else:
            headers = {profile.api_key_header: profile.api_key_prefix + profile.api_key}
            headers.update(profile.extra_headers)
            url = profile.base_url.rstrip("/") + "/models"
            request = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(request, timeout=min(profile.timeout_seconds, 30)) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                result["probe"] = {
                    "ok": True,
                    "status": response.status,
                    "response_bytes": len(raw.encode("utf-8")),
                }
            except urllib.error.HTTPError as exc:
                result["probe"] = {
                    "ok": False,
                    "status": exc.code,
                    "error": exc.read().decode("utf-8", errors="replace")[:500],
                }
            except Exception as exc:
                result["probe"] = {"ok": False, "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("probe", {}).get("ok", True) else 1


def command_init(args: argparse.Namespace) -> int:
    scope = args.scope
    if scope == "project":
        destination = Path(args.project_root).expanduser().resolve() / ".wechat-sticker-album" / "config.json"
        template = ROOT / "templates" / "project-config.json"
    else:
        destination = user_config_path()
        template = ROOT / "templates" / "user-config.json"
    if destination.exists() and not args.force:
        raise ConfigError(f"Config already exists: {destination}. Use --force to replace it.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, destination)
    print(json.dumps({"ok": True, "config": str(destination)}, ensure_ascii=False))
    return 0


def command_validate_plan(args: argparse.Namespace) -> int:
    result = load_and_validate(
        args.plan_file,
        require_approved=args.require_approved,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt and args.prompt_file:
        raise ConfigError("Use either --prompt or --prompt-file, not both")
    if args.prompt_file:
        prompt = Path(args.prompt_file).expanduser().read_text(encoding="utf-8").strip()
    else:
        prompt = (args.prompt or "").strip()
    if not prompt:
        raise ConfigError("A non-empty prompt is required")
    return prompt


def _reference_files(paths: list[str]) -> list[tuple[str, bytes, str]]:
    files = []
    for value in paths:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise ConfigError(f"Reference image does not exist: {path}")
        content_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        files.append((path.name, path.read_bytes(), content_type))
    return files


def command_generate(args: argparse.Namespace) -> int:
    prompt = _read_prompt(args)
    output = Path(args.output).expanduser().resolve()
    if output.exists() and not args.force:
        raise ConfigError(f"Output already exists: {output}. Use --force to replace it.")
    settings, primary = load_settings(args.config, args.profile)
    profile_names = [primary.name, *primary.fallback_profiles[:2]]
    references = _reference_files(args.reference)
    if references and not primary.supports_reference_images and not args.text_only:
        raise ConfigError(
            f"Profile {primary.name!r} is marked as text-to-image only. "
            "Use --text-only to proceed without reference-image editing."
        )

    attempts = []
    last_error = None
    for profile_name in profile_names:
        profile = settings.selected_profile(profile_name)
        try:
            provider = _provider_for(profile)
            mode = "edit" if references and profile.supports_reference_images else "generate"
            if mode == "edit":
                result = provider.edit(
                    prompt,
                    references,
                    args.size,
                    args.format,
                    "transparent" if args.transparent else None,
                )
            else:
                result = provider.generate(
                    prompt,
                    args.size,
                    args.format,
                    "transparent" if args.transparent else None,
                )
            _write_image(result.image.data, output, args.format)
            warning = None
            if args.transparent and not profile.supports_transparent_background:
                warning = (
                    "The provider is not marked as transparency-capable. "
                    "Use the bundled finalizer with a chroma-key source for transparent delivery."
                )
            print(
                json.dumps(
                    {
                        "ok": True,
                        "profile": profile.name,
                        "provider": profile.provider,
                        "model": profile.model,
                        "mode": mode,
                        "output": str(output),
                        "warning": warning,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        except (ConfigError, ProviderRequestError) as exc:
            last_error = exc
            attempts.append(
                {"profile": profile_name, "error": str(exc)}
            )
    print(
        json.dumps(
            {
                "ok": False,
                "attempts": attempts,
                "error": str(last_error) if last_error else "Generation failed",
            },
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )
    return 1


def command_finalize(args: argparse.Namespace) -> int:
    command = [sys.executable, str(ROOT / "scripts" / "finalize_album.py"), *args.finalize_args]
    completed = subprocess.run(command, cwd=Path.cwd())
    return completed.returncode


def command_install(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "install_skill.py"),
        "--scope",
        args.scope,
        "--project-root",
        str(Path(args.project_root).expanduser().resolve()),
    ]
    if args.force:
        command.append("--force")
    if args.link:
        command.append("--link")
    completed = subprocess.run(command, cwd=Path.cwd())
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and finalize a complete WeChat sticker album.")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Inspect provider configuration without generating an image.")
    doctor.add_argument("--config")
    doctor.add_argument("--profile")
    doctor.add_argument("--probe", action="store_true", help="Try GET <base_url>/models.")
    doctor.set_defaults(func=command_doctor)

    init = sub.add_parser("init", help="Create a project or user config from the bundled template.")
    init.add_argument("--scope", choices=("project", "user"), default="project")
    init.add_argument("--project-root", default=".")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    validate_plan = sub.add_parser(
        "validate-plan",
        help="Validate the album plan before any image generation.",
    )
    validate_plan.add_argument("--plan-file", required=True)
    validate_plan.add_argument("--require-approved", action="store_true")
    validate_plan.set_defaults(func=command_validate_plan)

    generate = sub.add_parser("generate", help="Generate one image using a configured provider profile.")
    generate.add_argument("--config")
    generate.add_argument("--profile")
    generate.add_argument("--prompt")
    generate.add_argument("--prompt-file")
    generate.add_argument("--reference", action="append", default=[])
    generate.add_argument("--size", required=True)
    generate.add_argument("--format", choices=("png", "jpg", "jpeg", "webp"), default="png")
    generate.add_argument("--output", required=True)
    generate.add_argument("--transparent", action="store_true")
    generate.add_argument(
        "--text-only",
        action="store_true",
        help="Allow text-only generation when the selected provider cannot use references.",
    )
    generate.add_argument("--force", action="store_true")
    generate.set_defaults(func=command_generate)

    finalize = sub.add_parser("finalize", help="Run the deterministic album finalizer and validator.")
    finalize.add_argument("finalize_args", nargs=argparse.REMAINDER)
    finalize.set_defaults(func=command_finalize)

    install = sub.add_parser("install", help="Install this complete skill project or globally.")
    install.add_argument("--scope", choices=("project", "global"), default="project")
    install.add_argument("--project-root", default=".")
    install.add_argument("--force", action="store_true")
    install.add_argument("--link", action="store_true")
    install.set_defaults(func=command_install)
    return parser


def main() -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except ProviderRequestError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        return 1
    except PlanError as exc:
        print(f"Plan validation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
