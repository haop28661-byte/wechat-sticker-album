# Usage

## 1. Initialize

```powershell
python scripts/cli.py init --scope project --project-root .
```

Edit `.wechat-sticker-album/config.json`, then:

```powershell
python scripts/cli.py doctor
```

## 2. Plan

The skill reads the reference image and plans every sticker's caption, action, expression, and theme relevance.

No image generation should happen until the plan is accepted or the user explicitly requests generation.

## 3. Generate source assets

Example:

```powershell
python scripts/cli.py generate `
  --reference character.png `
  --prompt-file prompts/sheet-01.txt `
  --size 1536x1024 `
  --output outputs/wechat-sticker-album/run/source/sheet-01.png
```

The CLI chooses reference editing when the selected profile supports it. Use `--text-only` only when working without reference-image support.

## 4. Finalize

```powershell
python scripts/finalize_album.py `
  --sheet outputs/wechat-sticker-album/run/source/sheet-01.png `
  --cover-source outputs/wechat-sticker-album/run/source/cover.png `
  --chat-icon-source outputs/wechat-sticker-album/run/source/icon.png `
  --banner-source outputs/wechat-sticker-album/run/source/banner.png `
  --appreciation-source outputs/wechat-sticker-album/run/source/appreciation-clean.png `
  --appreciation-text-source outputs/wechat-sticker-album/run/source/appreciation-text.png `
  --thank-you-source outputs/wechat-sticker-album/run/source/thank-you-clean.png `
  --thank-you-text-source outputs/wechat-sticker-album/run/source/thank-you-text.png `
  --output-dir outputs/wechat-sticker-album/run `
  --expected-count 6
```

Output is a complete folder by default. Add:

```powershell
--zip
```

when an archive is also required.

## 5. Check delivery

Open `preview.jpg`, then verify:

- expected sticker count
- character identity
- caption uniqueness and theme alignment
- transparent sticker and icon edges
- supporting asset dimensions and file sizes
- `manifest.json`
