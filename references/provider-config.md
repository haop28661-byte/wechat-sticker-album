# Provider Configuration

The skill is independent of any specific image provider. Configure an OpenAI-compatible image API by default, or describe a custom JSON HTTP API.

## Discovery order

The CLI loads configuration in this order:

1. `--config <path>`
2. environment variable `WECHAT_STICKER_CONFIG`
3. nearest project config at `<project>/.wechat-sticker-album/config.json`
4. user config at:
   - Windows: `%APPDATA%\wechat-sticker-album\config.json`
   - macOS/Linux: `$XDG_CONFIG_HOME/wechat-sticker-album/config.json` or `~/.config/wechat-sticker-album/config.json`
5. environment-only setup

Create a project config:

```powershell
python scripts/cli.py init --scope project --project-root .
```

Create a user config:

```powershell
python scripts/cli.py init --scope user
```

## Environment-only setup

```text
WECHAT_STICKER_IMAGE_BASE_URL=https://provider.example/v1
WECHAT_STICKER_IMAGE_MODEL=provider-image-model
WECHAT_STICKER_IMAGE_API_KEY=your-secret
WECHAT_STICKER_PROFILE=default
```

`WECHAT_STICKER_PROFILE` is optional for environment-only setup.

## Profile schema

```json
{
  "version": 1,
  "default_profile": "fast",
  "profiles": {
    "fast": {
      "provider": "openai-compatible",
      "base_url": "https://provider.example/v1",
      "model": "provider-image-model",
      "api_key_env": "WECHAT_STICKER_IMAGE_API_KEY",
      "generation_endpoint": "/images/generations",
      "edit_endpoint": "/images/edits",
      "api_key_header": "Authorization",
      "api_key_prefix": "Bearer ",
      "image_field": "image",
      "timeout_seconds": 300,
      "capabilities": {
        "supports_reference_images": true,
        "supports_transparent_background": false
      },
      "extra_headers": {},
      "extra_generation": {},
      "extra_edit": {},
      "fallback_profiles": ["quality"]
    },
    "quality": {
      "provider": "openai-compatible",
      "base_url": "https://provider.example/v1",
      "model": "provider-quality-model",
      "api_key_env": "WECHAT_STICKER_IMAGE_API_KEY",
      "capabilities": {
        "supports_reference_images": true,
        "supports_transparent_background": true
      }
    }
  }
}
```

Profiles are arbitrary. The skill never assumes a fixed model name or version.

## Capabilities

`supports_reference_images`

- `true`: use `/images/edits` or another configured reference-image flow
- `false`: use text-only generation; pass `--text-only` when a reference image was supplied

`supports_transparent_background`

- `true`: request `background=transparent`
- `false`: generate a flat `#00FFFF` chroma-key base and let `finalize_album.py` extract transparency

Set these explicitly. Do not infer capabilities from a model name.

## Fallback profiles

Accepts up to the first two fallback profile names. Useful for a fast daily model followed by a higher-quality model.

## Custom JSON HTTP API

Use `provider: "custom-http"` with:

```json
{
  "provider": "custom-http",
  "base_url": "https://provider.example",
  "model": "custom-model",
  "api_key_env": "WECHAT_STICKER_IMAGE_API_KEY",
  "custom_request": {
    "method": "POST",
    "url": "https://provider.example/generate",
    "headers": {
      "X-Client": "wechat-sticker-album"
    },
    "body": {
      "model": "{{model}}",
      "text": "{{prompt}}",
      "resolution": "{{size}}",
      "source": "{{image_base64}}"
    }
  },
  "custom_response": {
    "image_base64_path": "result.image"
  }
}
```

Supported placeholders:

- `{{prompt}}`
- `{{model}}`
- `{{size}}`
- `{{output_format}}`
- `{{background}}`
- `{{image_base64}}`
- `{{images}}` as a serializable list of filename, content type, and base64 data

Response may use `image_base64_path` or `image_url_path` with dot-separated object keys and list indexes.

For multipart or non-JSON APIs, extend `scripts/providers/custom_http.py` without changing the album workflow.

## Security

- Prefer `api_key_env` or an environment-only configuration.
- A literal `api_key` field is supported for local compatibility but is risky.
- `.wechat-sticker-album/`, `.env`, and `outputs/` are ignored by Git.
- Run `doctor` after changing configuration.
