#!/usr/bin/env python3
"""Finalize and validate a complete WeChat sticker album.

The generator phase creates 3x2 sheets and optional single stickers. This script
performs the deterministic work: split sheets, extract transparency, normalize
sizes, validate supporting assets, build a preview, write a manifest, and ZIP
the final package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError as exc:
    raise SystemExit(
        "Missing finalizer dependencies. Run: python -m pip install numpy Pillow"
    ) from exc


SKILL_ROOT = Path(__file__).resolve().parents[1]
MEME_SCRIPTS = SKILL_ROOT / "vendor" / "meme-sticker" / "scripts"
if not MEME_SCRIPTS.exists():
    raise SystemExit(f"Missing sibling MemeSticker helpers: {MEME_SCRIPTS}")
sys.path.insert(0, str(MEME_SCRIPTS))

try:
    from sticker_sheet_lib import (  # type: ignore[import-not-found]
        bbox_from_mask,
        edge_contact_fraction,
        extract_alpha,
        find_boundaries,
        foreground_mask,
        normalize_sticker,
        validate_geometry,
    )
except ImportError as exc:
    raise SystemExit(f"Could not import MemeSticker helpers: {exc}") from exc

from album_spec import CJK_RE, STYLE_OPTIONS, THEME_OPTIONS


class AlbumError(RuntimeError):
    """A user-correctable finalization error."""


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def require_file(path_value: str | Path, label: str) -> Path:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise AlbumError(f"{label} does not exist or is not a file: {path}")
    return path


def prepare_output_dir(path_value: str | Path) -> Path:
    output_dir = Path(path_value).expanduser().resolve()
    if output_dir.exists():
        if not output_dir.is_dir():
            raise AlbumError(f"Output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise AlbumError(
                f"Output directory must be new or empty to avoid overwriting data: {output_dir}"
            )
    else:
        output_dir.mkdir(parents=True)
    return output_dir


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if (directory / ".wechat-sticker-album").exists() or (directory / ".git").exists():
            return directory
    return current


def default_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return (
        find_project_root()
        / "outputs"
        / "wechat-sticker-album"
        / f"{stamp}-sticker-album"
    )


def image_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_rgba(path: Path, width: int, height: int, max_bytes: int | None = None) -> dict:
    if max_bytes is not None and path.stat().st_size > max_bytes:
        raise AlbumError(
            f"{path.name} is {path.stat().st_size} bytes; limit is {max_bytes} bytes"
        )
    with Image.open(path) as image:
        image.load()
        if image.size != (width, height):
            raise AlbumError(f"{path.name} is {image.size}; expected {(width, height)}")
        if image.mode != "RGBA":
            raise AlbumError(f"{path.name} mode is {image.mode}; expected RGBA")
        alpha = image.getchannel("A")
        alpha_values = np.asarray(alpha).ravel()
        if min(alpha_values) == 255:
            raise AlbumError(f"{path.name} has no transparent pixels")
        corners = (
            alpha.getpixel((0, 0)),
            alpha.getpixel((width - 1, 0)),
            alpha.getpixel((0, height - 1)),
            alpha.getpixel((width - 1, height - 1)),
        )
        if max(corners) != 0:
            raise AlbumError(f"{path.name} has opaque corners: {corners}")
        transparent_ratio = float(np.mean(alpha_values == 0))
    return {
        "path": str(path),
        "size": [width, height],
        "mode": "RGBA",
        "bytes": path.stat().st_size,
        "transparent_ratio": round(transparent_ratio, 4),
        "sha256": image_sha256(path),
    }


def process_transparent_source(
    source_value: str | Path,
    destination: Path,
    size: int,
    content_fraction: float,
    background_tolerance: float,
    max_bytes: int | None,
) -> tuple[dict, dict]:
    source = require_file(source_value, "Transparent source")
    with Image.open(source) as image:
        image.load()
        extracted, method = extract_alpha(
            image.convert("RGBA"),
            bg_tolerance=background_tolerance,
            white_fallback_threshold=40.0,
            white_border_radius=max(3, round(size * 0.04)),
        )
    if method == "white-background-fallback":
        raise AlbumError(
            f"{source.name} has a near-white background. Regenerate it on #00FFFF "
            "or with native transparency before finalizing."
        )
    normalized, bbox = normalize_sticker(extracted, size, content_fraction)
    destination.parent.mkdir(parents=True, exist_ok=True)
    normalized.save(destination, format="PNG", optimize=True)
    validation = check_rgba(destination, size, size, max_bytes)
    validation["method"] = method
    validation["content_bbox"] = list(bbox) if bbox else None
    return validation, {"source": str(source), "method": method, "bbox": bbox}


def split_sheet(
    source_value: str | Path,
    stickers_dir: Path,
    start_index: int,
    canvas_size: int,
    content_fraction: float,
    background_tolerance: float,
) -> tuple[list[dict], dict]:
    source = require_file(source_value, "Sticker sheet")
    with Image.open(source) as opened:
        opened.load()
        image = opened.convert("RGBA")

    array = np.asarray(image)
    mask, background = foreground_mask(array, 30.0)
    height, width = mask.shape
    if width < 240 or height < 160:
        raise AlbumError(f"{source.name} is too small for a 3x2 sticker sheet")

    x_diags, y_diags = find_boundaries(mask, rows=2, cols=3, search_fraction=0.24)
    geometry_errors = validate_geometry(
        x_diags,
        y_diags,
        width,
        height,
        rows=2,
        cols=3,
        max_gutter_density=0.075,
    )
    if geometry_errors:
        raise AlbumError(
            f"{source.name} is unsafe to split: " + "; ".join(geometry_errors)
        )

    xs = [0] + [diag.chosen for diag in x_diags] + [width]
    ys = [0] + [diag.chosen for diag in y_diags] + [height]
    records: list[dict] = []
    cell_diagnostics: list[dict] = []
    index = start_index

    for row in range(2):
        for col in range(3):
            left, top, right, bottom = xs[col], ys[row], xs[col + 1], ys[row + 1]
            cell_mask = mask[top:bottom, left:right]
            bbox = bbox_from_mask(cell_mask)
            foreground_ratio = float(cell_mask.mean()) if cell_mask.size else 0.0
            edge_contact = edge_contact_fraction(cell_mask)
            if bbox is None or foreground_ratio < 0.01:
                raise AlbumError(f"{source.name} sticker {index:02d} appears empty")
            if edge_contact > 0.22:
                raise AlbumError(
                    f"{source.name} sticker {index:02d} touches a cell edge "
                    f"(edge_contact={edge_contact:.3f})"
                )

            cell = image.crop((left, top, right, bottom))
            extracted, method = extract_alpha(
                cell,
                bg_tolerance=background_tolerance,
                white_fallback_threshold=40.0,
                white_border_radius=max(3, round(min(cell.size) * 0.026)),
            )
            if method == "white-background-fallback":
                raise AlbumError(
                    f"{source.name} uses a near-white background; regenerate on #00FFFF"
                )
            normalized, normalized_bbox = normalize_sticker(
                extracted, canvas_size, content_fraction
            )
            destination = stickers_dir / f"{index:02d}.png"
            normalized.save(destination, format="PNG", optimize=True)
            validation = check_rgba(destination, canvas_size, canvas_size)
            validation["method"] = method
            records.append(validation)
            cell_diagnostics.append(
                {
                    "index": index,
                    "cell": [left, top, right, bottom],
                    "source_bbox": list(bbox),
                    "foreground_ratio": round(foreground_ratio, 4),
                    "edge_contact": round(edge_contact, 4),
                    "normalized_bbox": list(normalized_bbox)
                    if normalized_bbox
                    else None,
                    "method": method,
                }
            )
            index += 1

    report = {
        "source": str(source),
        "image_size": [width, height],
        "background_rgb": [round(float(value), 2) for value in background],
        "cuts": {"x": xs[1:-1], "y": ys[1:-1]},
        "cells": cell_diagnostics,
    }
    return records, report


def process_single_sticker(
    source_value: str | Path,
    destination: Path,
    canvas_size: int,
    content_fraction: float,
    background_tolerance: float,
) -> tuple[dict, dict]:
    validation, report = process_transparent_source(
        source_value,
        destination,
        size=canvas_size,
        content_fraction=content_fraction,
        background_tolerance=background_tolerance,
        max_bytes=None,
    )
    return validation, report


def process_opaque_asset(
    source_value: str | Path,
    destination: Path,
    target_size: tuple[int, int],
    max_bytes: int | None,
    label: str,
    output_format: str = "PNG",
) -> dict:
    source = require_file(source_value, f"{label} source")
    target_ratio = target_size[0] / target_size[1]
    with Image.open(source) as opened:
        opened.load()
        if opened.mode in {"RGBA", "LA"} or "transparency" in opened.info:
            alpha = opened.convert("RGBA").getchannel("A")
            if int(np.asarray(alpha).min()) < 255:
                raise AlbumError(
                    f"{label} source contains transparency; expected opaque RGB"
                )
        image = opened.convert("RGB")

    width, height = image.size
    source_ratio = width / height
    if source_ratio > target_ratio:
        crop_width = round(height * target_ratio)
        loss = 1.0 - crop_width / width
        image = image.crop(
            ((width - crop_width) // 2, 0, (width + crop_width) // 2, height)
        )
    elif source_ratio < target_ratio:
        crop_height = round(width / target_ratio)
        loss = 1.0 - crop_height / height
        image = image.crop(
            (0, (height - crop_height) // 2, width, (height + crop_height) // 2)
        )
    else:
        loss = 0.0
    if loss > 0.05:
        raise AlbumError(
            f"{label} aspect ratio requires {loss:.1%} crop; regenerate at "
            f"{target_size[0]}:{target_size[1]}"
        )

    image = image.resize(target_size, Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "JPEG":
        for quality in range(94, 69, -1):
            image.save(
                destination,
                format="JPEG",
                quality=quality,
                subsampling=0,
                optimize=True,
            )
            if max_bytes is None or destination.stat().st_size <= max_bytes:
                break
    else:
        image.save(destination, format="PNG", optimize=True)

    if max_bytes is not None and destination.stat().st_size > max_bytes:
        raise AlbumError(
            f"{label} is {destination.stat().st_size} bytes; limit is {max_bytes} bytes"
        )
    with Image.open(destination) as check:
        check.load()
        if check.size != target_size or check.mode != "RGB":
            raise AlbumError(
                f"{label} finalization failed: {check.size}, {check.mode}"
            )
        pixels = np.asarray(check)
        near_white = float(np.mean(np.all(pixels > 245, axis=2)))
        if near_white > 0.5:
            raise AlbumError(
                f"{label} is {near_white:.1%} near-white; use a livelier opaque background"
            )
    return {
        "label": label,
        "path": str(destination),
        "size": list(target_size),
        "mode": "RGB",
        "bytes": destination.stat().st_size,
        "output_format": output_format,
        "near_white_ratio": round(near_white, 4),
        "crop_loss": round(loss, 4),
        "sha256": image_sha256(destination),
    }


def crop_and_resize_banner(source_value: str | Path, destination: Path) -> dict:
    return process_opaque_asset(
        source_value,
        destination,
        target_size=(750, 400),
        max_bytes=None,
        label="Banner",
        output_format="PNG",
    )


def load_metadata(path_value: str | None) -> tuple[dict | None, list[str]]:
    if not path_value:
        return None, []
    path = require_file(path_value, "Metadata JSON")
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AlbumError(f"Invalid metadata JSON: {path}") from exc
    if not isinstance(metadata, dict):
        raise AlbumError("Metadata JSON must be an object")

    warnings: list[str] = []
    name = metadata.get("name")
    if not isinstance(name, str) or not CJK_RE.fullmatch(name):
        raise AlbumError("Metadata name must contain only Chinese characters")
    if len(name) > 8:
        raise AlbumError("Metadata name must be at most 8 Chinese characters")
    if len(name) > 5:
        warnings.append("Metadata name is over 5 characters; display may be cramped")

    intro = metadata.get("intro")
    if not isinstance(intro, str) or not intro.strip():
        raise AlbumError("Metadata intro must be a non-empty string")
    if len(intro.strip()) > 80:
        raise AlbumError("Metadata intro must be at most 80 characters")

    styles = metadata.get("styles")
    if (
        not isinstance(styles, list)
        or not 1 <= len(styles) <= 2
        or any(style not in STYLE_OPTIONS for style in styles)
    ):
        raise AlbumError("Metadata styles must contain 1 or 2 approved style values")

    theme = metadata.get("theme")
    if theme not in THEME_OPTIONS:
        raise AlbumError("Metadata theme must contain one approved theme value")

    metadata["source_file"] = str(path)
    return metadata, warnings


def build_preview(
    sticker_paths: list[Path],
    cover_path: Path | None,
    icon_path: Path | None,
    banner_path: Path | None,
    appreciation_path: Path | None,
    thank_you_path: Path | None,
    destination: Path,
    columns: int,
) -> tuple[int, int]:
    tile = 240
    gap = 16
    margin = 24
    rows = math.ceil(len(sticker_paths) / columns)
    grid_width = margin * 2 + columns * tile + (columns - 1) * gap
    grid_height = margin * 2 + rows * tile + (rows - 1) * gap
    extra_width = max(grid_width, 750 + margin * 2)
    bottom = grid_height

    has_extras = cover_path is not None or icon_path is not None
    if has_extras:
        bottom += gap + margin + tile
    has_guides = appreciation_path is not None or thank_you_path is not None
    guide_tile = (extra_width - margin * 2 - gap) // 2
    if has_guides:
        bottom += gap + margin + guide_tile
    if banner_path is not None:
        banner_width = extra_width - margin * 2
        banner_height = round(banner_width * 400 / 750)
        bottom += gap + margin + banner_height

    canvas = Image.new("RGB", (extra_width, bottom), (247, 240, 228))
    for index, path in enumerate(sticker_paths):
        with Image.open(path) as opened:
            sticker = opened.convert("RGBA")
            row, col = divmod(index, columns)
            x = margin + col * (tile + gap)
            y = margin + row * (tile + gap)
            canvas.paste(sticker, (x, y), sticker)

    current_y = grid_height
    if has_extras:
        current_y += gap
        x = margin
        for path, resampling in (
            (cover_path, Image.Resampling.LANCZOS),
            (icon_path, Image.Resampling.NEAREST),
        ):
            if path is None:
                continue
            with Image.open(path) as opened:
                asset = opened.convert("RGBA").resize(
                    (tile, tile), resampling
                )
            canvas.paste(asset, (x, current_y), asset)
            x += tile + gap
        current_y += tile + margin

    if has_guides:
        current_y += gap
        x = margin
        for path in (appreciation_path, thank_you_path):
            if path is None:
                continue
            with Image.open(path) as opened:
                asset = opened.convert("RGB")
                scale = min(guide_tile / asset.width, guide_tile / asset.height)
                display_size = (
                    max(1, round(asset.width * scale)),
                    max(1, round(asset.height * scale)),
                )
                asset = asset.resize(display_size, Image.Resampling.LANCZOS)
            y = current_y + (guide_tile - asset.height) // 2
            canvas.paste(asset, (x, y))
            x += guide_tile + gap
        current_y += guide_tile + margin

    if banner_path is not None:
        with Image.open(banner_path) as opened:
            banner = opened.convert("RGB")
            banner_width = extra_width - margin * 2
            banner_height = round(banner_width * 400 / 750)
            banner = banner.resize(
                (banner_width, banner_height), Image.Resampling.LANCZOS
            )
        canvas.paste(banner, (margin, current_y + gap // 2))

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="JPEG", quality=95, subsampling=0)
    return canvas.size


def build_zip(
    zip_path: Path,
    files: list[tuple[Path, str]],
) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Finalize WeChat sticker sheets, singles, cover, chat icon, banner, "
            "preview, manifest, and ZIP."
        )
    )
    parser.add_argument("--sheet", action="append", default=[], help="3x2 sheet PNG. Repeatable.")
    parser.add_argument("--single", action="append", default=[], help="Single sticker PNG. Repeatable.")
    parser.add_argument("--cover-source", help="High-resolution transparent artist cover.")
    parser.add_argument("--chat-icon-source", help="High-resolution transparent chat icon.")
    parser.add_argument("--banner-source", help="Opaque 15:8 banner source.")
    parser.add_argument("--appreciation-source", help="Opaque 75:56 text-free appreciation base.")
    parser.add_argument("--appreciation-text-source", help="Opaque 75:56 appreciation text version.")
    parser.add_argument("--thank-you-source", help="Opaque 1:1 text-free thank-you base.")
    parser.add_argument("--thank-you-text-source", help="Opaque 1:1 thank-you text version.")
    parser.add_argument(
        "--output-dir",
        help=(
            "New or empty final output directory. Defaults to "
            "<project>/outputs/wechat-sticker-album/<timestamp>-sticker-album."
        ),
    )
    parser.add_argument("--expected-count", type=int, help="Fail if the inferred sticker count differs.")
    parser.add_argument("--metadata-json", help="Optional name/intro/styles/theme JSON.")
    parser.add_argument("--canvas-size", type=int, default=240, help="Sticker canvas size.")
    parser.add_argument("--content-fraction", type=float, default=0.82)
    parser.add_argument("--background-tolerance", type=float, default=42.0)
    parser.add_argument("--max-cover-kb", type=int, default=500)
    parser.add_argument("--max-icon-kb", type=int, default=100)
    parser.add_argument("--preview-columns", type=int, default=4)
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Also create wechat-sticker-album.zip. Folder output is always generated.",
    )
    return parser.parse_args()


def main() -> int:
    configure_stdio()
    args = parse_args()
    if not args.sheet and not args.single:
        raise AlbumError("At least one --sheet or --single input is required")
    if args.canvas_size <= 0:
        raise AlbumError("--canvas-size must be positive")
    if not 0.1 <= args.content_fraction <= 1.0:
        raise AlbumError("--content-fraction must be between 0.1 and 1.0")

    output_dir = prepare_output_dir(args.output_dir or default_output_dir())
    stickers_dir = output_dir / "stickers"
    stickers_dir.mkdir()
    metadata, warnings = load_metadata(args.metadata_json)

    sticker_records: list[dict] = []
    sheet_reports: list[dict] = []
    next_index = 1
    for sheet in args.sheet:
        records, report = split_sheet(
            sheet,
            stickers_dir,
            next_index,
            args.canvas_size,
            args.content_fraction,
            args.background_tolerance,
        )
        sticker_records.extend(records)
        sheet_reports.append(report)
        next_index += len(records)

    single_reports: list[dict] = []
    for single in args.single:
        destination = stickers_dir / f"{next_index:02d}.png"
        record, report = process_single_sticker(
            single,
            destination,
            args.canvas_size,
            args.content_fraction,
            args.background_tolerance,
        )
        sticker_records.append(record)
        single_reports.append(report)
        next_index += 1

    inferred_count = len(sticker_records)
    if args.expected_count is not None and inferred_count != args.expected_count:
        raise AlbumError(
            f"Expected {args.expected_count} stickers but built {inferred_count}"
        )

    cover_path = None
    icon_path = None
    banner_path = None
    appreciation_clean_path = None
    appreciation_path = None
    thank_you_clean_path = None
    thank_you_path = None
    cover_record = None
    icon_record = None
    banner_record = None
    appreciation_clean_record = None
    appreciation_record = None
    thank_you_clean_record = None
    thank_you_record = None

    if args.cover_source:
        cover_path = output_dir / "artist-cover.png"
        cover_record, _ = process_transparent_source(
            args.cover_source,
            cover_path,
            size=240,
            content_fraction=0.88,
            background_tolerance=args.background_tolerance,
            max_bytes=args.max_cover_kb * 1024,
        )
    if args.chat_icon_source:
        icon_path = output_dir / "chat-icon.png"
        icon_record, _ = process_transparent_source(
            args.chat_icon_source,
            icon_path,
            size=50,
            content_fraction=0.92,
            background_tolerance=args.background_tolerance,
            max_bytes=args.max_icon_kb * 1024,
        )
    if args.banner_source:
        banner_path = output_dir / "banner.png"
        banner_record = crop_and_resize_banner(args.banner_source, banner_path)
    if args.appreciation_source:
        appreciation_clean_path = output_dir / "appreciation-guide-clean.jpg"
        appreciation_clean_record = process_opaque_asset(
            args.appreciation_source,
            appreciation_clean_path,
            target_size=(750, 560),
            max_bytes=500 * 1024,
            label="Appreciation guide clean",
            output_format="JPEG",
        )
    if args.appreciation_text_source:
        appreciation_path = output_dir / "appreciation-guide.jpg"
        appreciation_record = process_opaque_asset(
            args.appreciation_text_source,
            appreciation_path,
            target_size=(750, 560),
            max_bytes=500 * 1024,
            label="Appreciation guide text version",
            output_format="JPEG",
        )
    if args.thank_you_source:
        thank_you_clean_path = output_dir / "thank-you-clean.jpg"
        thank_you_clean_record = process_opaque_asset(
            args.thank_you_source,
            thank_you_clean_path,
            target_size=(750, 750),
            max_bytes=500 * 1024,
            label="Thank-you image clean",
            output_format="JPEG",
        )
    if args.thank_you_text_source:
        thank_you_path = output_dir / "thank-you.jpg"
        thank_you_record = process_opaque_asset(
            args.thank_you_text_source,
            thank_you_path,
            target_size=(750, 750),
            max_bytes=500 * 1024,
            label="Thank-you image text version",
            output_format="JPEG",
        )

    preview_path = output_dir / "preview.jpg"
    preview_size = build_preview(
        [Path(record["path"]) for record in sticker_records],
        cover_path,
        icon_path,
        banner_path,
        appreciation_path or appreciation_clean_path,
        thank_you_path or thank_you_clean_path,
        preview_path,
        max(1, args.preview_columns),
    )

    manifest = {
        "skill": "wechat-sticker-album",
        "created_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "sticker_count": inferred_count,
        "canvas_size": [args.canvas_size, args.canvas_size],
        "metadata": metadata,
        "warnings": warnings,
        "stickers": sticker_records,
        "sheets": sheet_reports,
        "singles": single_reports,
        "artist_cover": cover_record,
        "chat_icon": icon_record,
        "banner": banner_record,
        "appreciation_guide_clean": appreciation_clean_record,
        "appreciation_guide": appreciation_record,
        "thank_you_image_clean": thank_you_clean_record,
        "thank_you_image": thank_you_record,
        "preview": {
            "path": str(preview_path),
            "size": list(preview_size),
            "sha256": image_sha256(preview_path),
        },
        "manual_review_required": [
            "character identity and expression consistency",
            "caption correctness, uniqueness, and theme alignment",
            "absence of unintended text, white halos, and hard square borders",
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    zip_path = None
    if args.zip:
        zip_path = output_dir / "wechat-sticker-album.zip"
        zip_files: list[tuple[Path, str]] = [
            (path, f"stickers/{path.name}")
            for path in sorted(stickers_dir.glob("*.png"))
        ]
        for path, archive_name in (
            (cover_path, "artist-cover.png"),
            (icon_path, "chat-icon.png"),
            (banner_path, "banner.png"),
            (appreciation_clean_path, "appreciation-guide-clean.jpg"),
            (appreciation_path, "appreciation-guide.jpg"),
            (thank_you_clean_path, "thank-you-clean.jpg"),
            (thank_you_path, "thank-you.jpg"),
            (preview_path, "preview.jpg"),
            (manifest_path, "manifest.json"),
        ):
            if path is not None:
                zip_files.append((path, archive_name))
        build_zip(zip_path, zip_files)

    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(output_dir),
                "sticker_count": inferred_count,
                "preview": str(preview_path),
                "manifest": str(manifest_path),
                "zip": str(zip_path) if zip_path else None,
                "warnings": warnings,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AlbumError as exc:
        print(f"Album finalization failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
