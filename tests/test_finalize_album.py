from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
FINALIZER = ROOT / "scripts" / "finalize_album.py"
sys.path.insert(0, str(ROOT / "scripts"))

from finalize_album import default_output_dir  # noqa: E402


def make_transparent_source(path: Path, size: tuple[int, int], color: str):
    image = Image.new("RGB", size, "#00ffff")
    draw = ImageDraw.Draw(image)
    width, height = size
    draw.ellipse(
        (width // 4, height // 6, width * 3 // 4, height * 5 // 6),
        fill=color,
        outline="#5b2a16",
        width=max(4, min(width, height) // 30),
    )
    image.save(path)


def make_sheet(path: Path):
    image = Image.new("RGB", (1536, 1024), "#00ffff")
    draw = ImageDraw.Draw(image)
    colors = ["#f44336", "#ff9800", "#ffc107", "#4caf50", "#2196f3", "#9c27b0"]
    for row in range(2):
        for col in range(3):
            index = row * 3 + col
            left = col * 512
            top = row * 512
            draw.ellipse(
                (left + 120, top + 100, left + 392, top + 412),
                fill=colors[index],
                outline="#5b2a16",
                width=12,
            )
    image.save(path)


def test_finalizer_builds_folder_and_optional_zip(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    make_sheet(source / "sheet.png")
    make_transparent_source(source / "cover.png", (768, 768), "#e53b2f")
    make_transparent_source(source / "icon.png", (384, 384), "#e53b2f")
    Image.new("RGB", (1500, 800), "#ff5a36").save(source / "banner.png")
    Image.new("RGB", (1500, 1120), "#ff6b45").save(source / "appreciation.png")
    Image.new("RGB", (1200, 1200), "#d93425").save(source / "thank-you.png")
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "name": "测试拜年",
                "intro": "测试角色穿新装陪大家过年。",
                "styles": ["日常", "软萌可爱"],
                "theme": "节日",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "output"
    command = [
        sys.executable,
        str(FINALIZER),
        "--sheet",
        str(source / "sheet.png"),
        "--cover-source",
        str(source / "cover.png"),
        "--chat-icon-source",
        str(source / "icon.png"),
        "--banner-source",
        str(source / "banner.png"),
        "--appreciation-source",
        str(source / "appreciation.png"),
        "--thank-you-source",
        str(source / "thank-you.png"),
        "--output-dir",
        str(output),
        "--expected-count",
        "6",
        "--metadata-json",
        str(metadata),
    ]
    completed = subprocess.run(
        command, encoding="utf-8", capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
    assert len(list((output / "stickers").glob("*.png"))) == 6
    assert not (output / "wechat-sticker-album.zip").exists()
    for path in (output / "stickers").glob("*.png"):
        with Image.open(path) as image:
            assert image.size == (240, 240)
            assert image.mode == "RGBA"
    with Image.open(output / "artist-cover.png") as image:
        assert image.size == (240, 240)
    with Image.open(output / "chat-icon.png") as image:
        assert image.size == (50, 50)
    with Image.open(output / "banner.png") as image:
        assert image.size == (750, 400)
    with Image.open(output / "appreciation-guide-clean.jpg") as image:
        assert image.size == (750, 560)
    with Image.open(output / "thank-you-clean.jpg") as image:
        assert image.size == (750, 750)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sticker_count"] == 6

    zipped = tmp_path / "output-zip"
    command[command.index(str(output))] = str(zipped)
    command.append("--zip")
    completed = subprocess.run(
        command, encoding="utf-8", capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
    assert (zipped / "wechat-sticker-album.zip").is_file()


def test_default_output_lives_under_project_root(tmp_path, monkeypatch):
    project = tmp_path / "project"
    nested = project / "work" / "nested"
    nested.mkdir(parents=True)
    (project / ".wechat-sticker-album").mkdir()
    monkeypatch.chdir(nested)
    output = default_output_dir()
    assert output.parent == project / "outputs" / "wechat-sticker-album"
