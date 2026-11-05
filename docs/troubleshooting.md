# Troubleshooting

## No configuration found

Run:

```powershell
python scripts/cli.py init --scope project --project-root .
```

Or set:

```text
WECHAT_STICKER_IMAGE_BASE_URL
WECHAT_STICKER_IMAGE_MODEL
WECHAT_STICKER_IMAGE_API_KEY
```

## `doctor` reports no API key

Check the environment variable named by `api_key_env`. The default lower-priority fallback is `WECHAT_STICKER_IMAGE_API_KEY`.

## `/images/edits` returns 404 or 405

The provider may support text-to-image only. Set:

```json
"capabilities": { "supports_reference_images": false }
```

Then use `--text-only`. Character consistency will be weaker.

## Provider returns an unsupported `1:1` or sheet size

Set the provider-supported size in the generation command and in `sheet_size`/`single_size`. The finalizer performs proportional conversion to final delivery sizes.

## Generated image is not transparent

Set `supports_transparent_background` truthfully. When false, request a flat `#00FFFF` source and let the finalizer extract alpha.

## A sheet cannot be split

Regenerate only that sheet with:

- more gutter spacing
- slightly smaller sticker subjects
- a perfectly flat `#00FFFF` background
- all captions inside each sticker territory

## A supporting image is too large

The finalizer compresses 500 KB-limited assets with JPEG quality reduction. If the image contains excessive noise, regenerate a cleaner source.

## Installation rejects an existing skill

Use `--force` to replace it. Project outputs and project configuration live outside the skill directory and are not removed.
