from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "album-plan.json"
CLI = ROOT / "scripts" / "cli.py"


def load_plan() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def write_plan(path: Path, plan: dict) -> Path:
    path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return path


def run_validate(path: Path, require_approved: bool = False) -> subprocess.CompletedProcess:
    command = [sys.executable, str(CLI), "validate-plan", "--plan-file", str(path)]
    if require_approved:
        command.append("--require-approved")
    return subprocess.run(command, text=True, capture_output=True, check=False)


def test_template_plan_validates_before_approval(tmp_path):
    path = write_plan(tmp_path / "plan.json", load_plan())
    completed = run_validate(path)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["approved"] is False
    assert result["sticker_count"] == 6


def test_require_approved_blocks_generation_plan(tmp_path):
    path = write_plan(tmp_path / "plan.json", load_plan())
    completed = run_validate(path, require_approved=True)
    assert completed.returncode == 2
    assert "not approved" in completed.stderr

    plan = load_plan()
    plan["approved"] = True
    plan["approval_note"] = "用户确认开始"
    write_plan(path, plan)
    completed = run_validate(path, require_approved=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["approved"] is True


def test_duplicate_captions_are_rejected(tmp_path):
    plan = load_plan()
    plan["sticker_items"][1]["caption"] = plan["sticker_items"][0]["caption"]
    path = write_plan(tmp_path / "plan.json", plan)
    completed = run_validate(path)
    assert completed.returncode == 2
    assert "unique" in completed.stderr


def test_theme_coverage_and_backend_are_rejected(tmp_path):
    plan = load_plan()
    for item in plan["sticker_items"]:
        item["theme_related"] = False
    path = write_plan(tmp_path / "plan.json", plan)
    completed = run_validate(path)
    assert completed.returncode == 2
    assert "theme-related" in completed.stderr

    plan = load_plan()
    plan["backend"] = {"mode": "api", "profile": "", "reason": "manual API"}
    write_plan(path, plan)
    completed = run_validate(path)
    assert completed.returncode == 2
    assert "profile" in completed.stderr
