# Changelog

## 2.0.1 - 2026-11-06

- Added `api_key_file` and `api_key_json_path` so a profile can reuse a local JSON credential file without copying the secret.
- Environment variables continue to take precedence over file-based credentials.
- Added regression coverage for nested credential paths.

## 2.0.0 - 2026-11-06

- Removed the fixed DaiTu provider, base URL, and model names.
- Added configurable OpenAI-compatible image generation and editing.
- Added configurable custom JSON HTTP provider mapping.
- Added provider profiles and ordered fallback profiles.
- Added project-local and global complete-directory installation.
- Changed generated output to a project-relative album folder.
- Made ZIP creation optional with `--zip`.
- Vendored GPT-Image2 Style Library and MemeSticker under their MIT licenses.
- Added appreciation guide and thank-you image delivery with clean and text variants.
- Added automated tests and GitHub Actions CI.
