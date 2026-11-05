# Development

## Setup

```powershell
python -m pip install -r requirements-dev.txt
```

## Tests

```powershell
python -m pytest
```

## Skill validation

```powershell
python "<skill-creator-directory>\scripts\quick_validate.py" .
```

## Architecture

- `scripts/config.py`: config discovery and profile normalization
- `scripts/cli.py`: doctor, generate, install, and finalize entrypoint
- `scripts/providers/`: provider adapters
- `scripts/finalize_album.py`: deterministic matte, sizing, validation, preview, manifest, and optional ZIP
- `vendor/gpt-image-2-style-library/`: vendored style reference
- `vendor/meme-sticker/`: vendored matte and packaging helpers

## Provider adapter contract

An adapter implements:

```text
generate(prompt, size, output_format, background)
edit(prompt, images, size, output_format, background)
```

Both return `ProviderResult` with encoded image bytes and metadata.

## Release checks

1. Run the test suite.
2. Run `quick_validate.py`.
3. Run project and global installation tests in temporary directories.
4. Confirm no `.env`, `.wechat-sticker-album/config.json`, `outputs/`, API keys, or generated albums are tracked.
5. Confirm both vendored licenses and source notices are present.
