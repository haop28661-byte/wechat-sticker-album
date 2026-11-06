#!/usr/bin/env python3
"""Install the complete skill into a project or Codex user skills directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "wechat-sticker-album"
IGNORE = shutil.ignore_patterns(
    ".git",
    ".github",
    ".venv",
    "venv",
    "__pycache__",
    "*.pyc",
    "outputs",
    ".pytest_cache",
    ".wechat-sticker-album",
    "tests",
)


class InstallError(RuntimeError):
    pass


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def global_skills_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return (Path(codex_home).expanduser() if codex_home else Path.home() / ".codex") / "skills"


def destination_for(scope: str, project_root: Path) -> Path:
    if scope == "project":
        return project_root.resolve() / ".agents" / "skills" / SKILL_NAME
    return global_skills_root().resolve() / SKILL_NAME


def validate_source() -> None:
    required = [
        SOURCE_ROOT / "SKILL.md",
        SOURCE_ROOT / "scripts" / "cli.py",
        SOURCE_ROOT / "scripts" / "finalize_album.py",
        SOURCE_ROOT / "vendor" / "meme-sticker",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise InstallError("Skill source is incomplete: " + "; ".join(missing))


def install_copy(destination: Path, force: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        raise InstallError(
            f"Destination already exists: {destination}. Use --force to replace it."
        )
    staging = destination.parent / f".{SKILL_NAME}.install-{uuid.uuid4().hex}"
    try:
        shutil.copytree(SOURCE_ROOT, staging, ignore=IGNORE)
        if destination.exists():
            shutil.rmtree(destination)
        staging.replace(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def install_link(destination: Path, force: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        if not force:
            raise InstallError(
                f"Destination already exists: {destination}. Use --force to replace it."
            )
        if destination.is_symlink():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    try:
        destination.symlink_to(SOURCE_ROOT, target_is_directory=True)
    except OSError as exc:
        raise InstallError(
            "--link requires operating-system symlink support. "
            f"Use normal copy installation instead. Details: {exc}"
        ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the complete wechat-sticker-album skill.")
    parser.add_argument("--scope", choices=("project", "global"), default="project")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--link", action="store_true")
    return parser.parse_args()


def main() -> int:
    configure_stdio()
    args = parse_args()
    validate_source()
    project_root = Path(args.project_root).expanduser().resolve()
    destination = destination_for(args.scope, project_root)
    if args.link:
        install_link(destination, args.force)
    else:
        install_copy(destination, args.force)
    print(
        json.dumps(
            {
                "ok": True,
                "scope": args.scope,
                "source": str(SOURCE_ROOT),
                "destination": str(destination),
                "mode": "link" if args.link else "copy",
                "next": [
                    f"python {destination / 'scripts' / 'cli.py'} doctor",
                    f"python {destination / 'scripts' / 'cli.py'} init --scope project --project-root {project_root}",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InstallError as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
