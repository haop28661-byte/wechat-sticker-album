# Usage

## 1. Initialize

This step is only for the HTTP backend. If the current Codex session has native image generation, skip API initialization and continue with planning.

```powershell
python scripts/cli.py init --scope project --project-root .
```

Edit `.wechat-sticker-album/config.json`, then:

```powershell
python scripts/cli.py doctor
```

## 2. Plan

Create an album plan from `templates/album-plan.json`:

```powershell
python scripts/cli.py validate-plan --plan-file path/to/plan.json
```

The skill presents the backend, count, theme, styles, every sticker, supporting assets, and output path. No image generation should happen until the user explicitly approves the plan.

After approval:

```powershell
python scripts/cli.py validate-plan `
  --plan-file path/to/plan.json `
  --require-approved
```

## 3. Generate source assets

### Native Codex/ChatGPT backend

Ask Codex to generate each planned sheet or asset directly. The skill saves results under:

```text
<project>/.wechat-sticker-album/work/<run>/source/
```

It does not request an API key.

### HTTP backend

Example:

```powershell
python scripts/cli.py generate `
  --reference character.png `
  --prompt-file prompts/sheet-01.txt `
  --size 1536x1024 `
  --output .wechat-sticker-album/work/run/source/sheet-01.png
```

The CLI chooses reference editing when the selected profile supports it. Use `--text-only` only when working without reference-image support.

## 4. Finalize

```powershell
python scripts/finalize_album.py `
  --sheet .wechat-sticker-album/work/run/source/sheet-01.png `
  --cover-source .wechat-sticker-album/work/run/source/cover.png `
  --chat-icon-source .wechat-sticker-album/work/run/source/icon.png `
  --banner-source .wechat-sticker-album/work/run/source/banner.png `
  --appreciation-source .wechat-sticker-album/work/run/source/appreciation-clean.png `
  --appreciation-text-source .wechat-sticker-album/work/run/source/appreciation-text.png `
  --thank-you-source .wechat-sticker-album/work/run/source/thank-you-clean.png `
  --thank-you-text-source .wechat-sticker-album/work/run/source/thank-you-text.png `
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
