from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_skill.py"


def run_install(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(INSTALLER), *args],
        encoding="utf-8",
        capture_output=True,
        env=env,
        check=False,
    )


def assert_complete_install(destination: Path):
    assert (destination / "SKILL.md").is_file()
    assert (destination / "scripts" / "cli.py").is_file()
    assert (destination / "scripts" / "finalize_album.py").is_file()
    assert (destination / "vendor" / "meme-sticker" / "scripts" / "sticker_sheet_lib.py").is_file()
    assert (
        destination
        / "vendor"
        / "gpt-image-2-style-library"
        / "references"
        / "style-library.md"
    ).is_file()
    assert not (destination / "tests").exists()
    assert not (destination / ".git").exists()


def test_project_install_copies_complete_runtime(tmp_path):
    completed = run_install("--scope", "project", "--project-root", str(tmp_path))
    assert completed.returncode == 0, completed.stderr
    assert_complete_install(tmp_path / ".agents" / "skills" / "wechat-sticker-album")


def test_global_install_copies_complete_runtime(tmp_path):
    codex_home = tmp_path / "codex-home"
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    completed = run_install("--scope", "global", "--project-root", str(tmp_path), env=env)
    assert completed.returncode == 0, completed.stderr
    assert_complete_install(codex_home / "skills" / "wechat-sticker-album")
