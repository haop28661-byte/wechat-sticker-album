#!/usr/bin/env python3
"""Validate an album plan before image generation starts."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from album_spec import STYLE_OPTIONS, THEME_OPTIONS


CAPTION_RE = re.compile(r"^[\u3400-\u9fff]{2,4}$")


class PlanError(RuntimeError):
    pass


def _require_bool(container: dict, key: str, label: str) -> bool:
    value = container.get(key)
    if not isinstance(value, bool):
        raise PlanError(f"{label}.{key} must be true or false")
    return value


def validate_plan(plan: dict, require_approved: bool = False) -> dict:
    if not isinstance(plan, dict):
        raise PlanError("Plan root must be a JSON object")
    if plan.get("version") != 1:
        raise PlanError("Plan version must be 1")

    album_name = plan.get("album_name")
    if not isinstance(album_name, str) or not album_name.strip():
        raise PlanError("album_name must be a non-empty string")
    theme = plan.get("theme")
    if theme not in THEME_OPTIONS:
        raise PlanError("theme must be an approved theme value")
    styles = plan.get("styles")
    if (
        not isinstance(styles, list)
        or not 1 <= len(styles) <= 2
        or any(style not in STYLE_OPTIONS for style in styles)
    ):
        raise PlanError("styles must contain 1 or 2 approved style values")

    count = plan.get("sticker_count")
    if not isinstance(count, int) or count <= 0:
        raise PlanError("sticker_count must be a positive integer")
    items = plan.get("sticker_items")
    if not isinstance(items, list) or len(items) != count:
        raise PlanError("sticker_items length must equal sticker_count")

    captions_enabled = plan.get("captions_enabled")
    if not isinstance(captions_enabled, bool):
        raise PlanError("captions_enabled must be true or false")
    captions = []
    theme_related = 0
    for expected_index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise PlanError(f"sticker_items[{expected_index - 1}] must be an object")
        if item.get("index") != expected_index:
            raise PlanError(f"sticker_items[{expected_index - 1}].index must be {expected_index}")
        action = item.get("action")
        if not isinstance(action, str) or not action.strip():
            raise PlanError(f"sticker {expected_index}: action is required")
        related = item.get("theme_related")
        if not isinstance(related, bool):
            raise PlanError(f"sticker {expected_index}: theme_related must be true or false")
        if related:
            theme_related += 1
        caption = item.get("caption")
        if captions_enabled:
            if not isinstance(caption, str) or not CAPTION_RE.fullmatch(caption):
                raise PlanError(
                    f"sticker {expected_index}: caption must contain 2-4 Chinese characters"
                )
            captions.append(caption)
    if captions and len(set(captions)) != len(captions):
        raise PlanError("captions must be unique")
    minimum_related = math.ceil(count / 2)
    if theme_related < minimum_related:
        raise PlanError(
            f"at least {minimum_related} stickers must be theme-related; got {theme_related}"
        )

    backend = plan.get("backend")
    if not isinstance(backend, dict) or backend.get("mode") not in {"native", "api"}:
        raise PlanError("backend.mode must be native or api")
    if backend["mode"] == "api":
        profile = backend.get("profile")
        if not isinstance(profile, str) or not profile.strip():
            raise PlanError("API backend requires a non-empty profile")
    reason = backend.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise PlanError("backend.reason is required")

    assets = plan.get("supporting_assets")
    if not isinstance(assets, dict):
        raise PlanError("supporting_assets must be an object")
    for key in (
        "artist_cover",
        "chat_icon",
        "banner",
        "appreciation_guide",
        "thank_you_image",
    ):
        _require_bool(assets, key, "supporting_assets")

    approved = plan.get("approved")
    if not isinstance(approved, bool):
        raise PlanError("approved must be true or false")
    approval_note = plan.get("approval_note")
    if not isinstance(approval_note, str):
        raise PlanError("approval_note must be a string")
    if approved and not approval_note.strip():
        raise PlanError("approval_note is required when approved is true")
    if require_approved and not approved:
        raise PlanError("Plan is not approved; stop before image generation")

    return {
        "ok": True,
        "album_name": album_name,
        "sticker_count": count,
        "theme": theme,
        "styles": styles,
        "backend": backend,
        "theme_related": theme_related,
        "minimum_theme_related": minimum_related,
        "approved": approved,
        "supporting_assets": assets,
    }


def load_and_validate(path_value: str | Path, require_approved: bool = False) -> dict:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise PlanError(f"Plan file does not exist: {path}")
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanError(f"Plan file is not valid JSON: {path}") from exc
    result = validate_plan(plan, require_approved=require_approved)
    result["plan_file"] = str(path)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an album plan before generation.")
    parser.add_argument("plan_file")
    parser.add_argument("--require-approved", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(
        json.dumps(
            load_and_validate(args.plan_file, require_approved=args.require_approved),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PlanError as exc:
        print(f"Plan validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
