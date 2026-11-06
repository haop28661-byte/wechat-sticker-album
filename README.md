# WeChat Sticker Album

A backend-flexible Codex skill for turning one character reference image into a complete, upload-ready WeChat sticker album.

The skill owns the planning, prompt contracts, asset validation, transparency processing, metadata checks, and packaging. Image generation can use native Codex/ChatGPT image generation or a provider configured by the current user.

## Features

- Variable sticker count: full 3 x 2 sheets for groups of six, single generation for the remainder
- Artist cover, chat-list icon, banner, appreciation guide, and thank-you reward image
- Native Codex/ChatGPT image generation with no separate API configuration
- OpenAI-compatible `images/generations` and `images/edits` support
- Configurable custom JSON HTTP provider
- Configurable model profiles and fallback profiles
- Project-local output folder by default
- Optional ZIP output with `--zip`
- Transparent PNG cleanup, chroma-key removal, edge despill, exact-size conversion, and file-size limits
- Metadata, preview, and manifest generation
- Full project or global installation
- Vendored GPT-Image2 Style Library and MemeSticker, so no separate skill installation is needed

## Requirements

- Python 3.10+
- Codex skill support
- Either native image generation in the current Codex session, or an image API exposing OpenAI-compatible generation/editing

```powershell
python -m pip install -r requirements.txt
```

## Install

### Project-local

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Scope Project -ProjectRoot "D:\your-project"
```

The full skill directory is installed to:

```text
<project>/.agents/skills/wechat-sticker-album
```

### Global

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Scope Global
```

The full skill directory is installed to:

```text
$CODEX_HOME/skills/wechat-sticker-album
```

When `CODEX_HOME` is unset, `~/.codex/skills/wechat-sticker-album` is used.

macOS/Linux:

```sh
./install.sh --scope project --project-root /path/to/project
./install.sh --scope global
```

Both modes copy the complete runtime directory. They do not copy only `SKILL.md`.

## Generation backends

The skill chooses the backend in this order:

1. explicit user or project instruction
2. native Codex/ChatGPT image generation when available
3. configured HTTP image provider
4. ask the user only when no backend is available

If the user has a subscription-backed native image tool, no API setup is needed.

This project follows any explicit `AGENTS.md` provider policy first. A project that requires a specific provider will continue using that provider.

See [references/backend-selection.md](references/backend-selection.md).

## Plan-first workflow

A request to create a sticker album starts planning, not paid generation.

The skill creates `plan.json`, presents every caption and action, and waits for explicit approval. It starts generating only after:

```powershell
python scripts/cli.py validate-plan `
  --plan-file "<plan.json>" `
  --require-approved
```

passes. Approved plans make retries and single-asset fixes easier without repeatedly asking the same album-level questions.

See [references/plan-first.md](references/plan-first.md).

## Configure an optional image API

The following setup is only needed when using the HTTP backend. Create a project config:

```powershell
python scripts/cli.py init --scope project --project-root .
```

Edit `.wechat-sticker-album/config.json` and set:

- `base_url`
- `model`
- `api_key_env` or an environment-only setup
- optional `api_key_file` and `api_key_json_path` for a local shared credential file
- capability flags

Recommended secret environment variable:

```powershell
$env:WECHAT_STICKER_IMAGE_API_KEY = "your-api-key"
```

Environment-only setup:

```powershell
$env:WECHAT_STICKER_IMAGE_BASE_URL = "https://provider.example/v1"
$env:WECHAT_STICKER_IMAGE_MODEL = "your-image-model"
$env:WECHAT_STICKER_IMAGE_API_KEY = "your-api-key"
```

Check configuration without generating an image:

```powershell
python scripts/cli.py doctor
```

See [docs/providers.md](docs/providers.md) and [references/provider-config.md](references/provider-config.md).

## Usage

Ask Codex to create the sticker album. It responds with an album plan and waits for approval.

With native generation, no API key is requested.

With the HTTP backend, generate one source image:

```powershell
python scripts/cli.py generate `
  --reference character.png `
  --prompt-file prompts/sheet-01.txt `
  --size 1536x1024 `
  --output .wechat-sticker-album/work/run/source/sheet-01.png
```

Finalize the album:

```powershell
python scripts/finalize_album.py `
  --sheet .wechat-sticker-album/work/run/source/sheet-01.png `
  --sheet .wechat-sticker-album/work/run/source/sheet-02.png `
  --cover-source .wechat-sticker-album/work/run/source/cover.png `
  --chat-icon-source .wechat-sticker-album/work/run/source/icon.png `
  --banner-source .wechat-sticker-album/work/run/source/banner.png `
  --output-dir outputs/wechat-sticker-album/run `
  --expected-count 12
```

Add `--zip` to create an archive beside the final folder.

See [docs/usage.md](docs/usage.md).

## Output

```text
<project>/outputs/wechat-sticker-album/<timestamp>-sticker-album/
├── stickers/
│   ├── 01.png
│   └── ...
├── artist-cover.png
├── chat-icon.png
├── banner.png
├── appreciation-guide-clean.jpg
├── appreciation-guide.jpg
├── thank-you-clean.jpg
├── thank-you.jpg
├── preview.jpg
└── manifest.json
```

Optional:

```text
wechat-sticker-album.zip
```

## Repository layout

```text
.
├── SKILL.md
├── agents/
├── references/
├── scripts/
├── templates/
├── vendor/
├── docs/
├── tests/
├── install.ps1
├── install.sh
└── .github/workflows/ci.yml
```

## Security

- Never commit `.wechat-sticker-album/`, `.env`, or generated `outputs/`.
- Prefer `api_key_env` over storing a literal key.
- Run `doctor --probe` only against a trusted provider.
- Review generated images before publishing an album.

## Development

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
python "<skill-creator-directory>\scripts\quick_validate.py" .
```

See [docs/development.md](docs/development.md).

## Third-party components

- GPT-Image2 Style Library by freestylefly, MIT License
- MemeSticker by shanliuling, MIT License

Original license files and source references are retained under `vendor/`. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

MIT License. See [LICENSE](LICENSE).
