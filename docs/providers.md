# Image Providers

The skill calls the user's configured provider. It does not contain a default vendor, base URL, API key, or model name.

## OpenAI-compatible API

Supported endpoints:

```text
POST {base_url}/images/generations
POST {base_url}/images/edits
```

Typical JSON generation body:

```json
{
  "model": "user-selected-model",
  "prompt": "image prompt",
  "n": 1,
  "size": "1024x1024",
  "output_format": "png"
}
```

Reference-image edits use multipart form data with the configured `image_field`.

The adapter accepts image responses containing:

```text
b64_json
data[0].b64_json
data[0].url
```

## Profiles

Profiles allow different providers or models:

```json
{
  "default_profile": "fast",
  "profiles": {
    "fast": {
      "base_url": "https://provider.example/v1",
      "model": "fast-model",
      "api_key_env": "WECHAT_STICKER_IMAGE_API_KEY"
    },
    "quality": {
      "base_url": "https://provider.example/v1",
      "model": "quality-model",
      "api_key_env": "WECHAT_STICKER_IMAGE_API_KEY"
    }
  }
}
```

Select a profile:

```powershell
python scripts/cli.py generate --profile quality ...
```

Fallback profiles are retried in order after provider failure.

## Reference image support

Set `capabilities.supports_reference_images` explicitly.

- `true`: the skill can use `images/edits`
- `false`: use text-only generation; the CLI requires `--text-only`

## Transparent output support

Set `capabilities.supports_transparent_background`.

- `true`: request transparent output from the API
- `false`: use a flat `#00FFFF` source and let the finalizer extract alpha

## Custom JSON API

See [references/provider-config.md](../references/provider-config.md) for placeholder mapping and response-path configuration.

For multipart or unusual authentication, add a provider adapter under `scripts/providers/` without changing album planning or finalization.
