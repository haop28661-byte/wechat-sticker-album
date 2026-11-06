# Changelog

## 2.2.0 - 2026-11-06

- Added a plan-first approval gate before any image generation.
- Added a validated `plan.json` with backend, captions, actions, theme coverage, assets, and approval status.
- Added `validate-plan` and `--require-approved`.
- Separated hidden working sources from the clean project-local final folder.

## 2.1.0 - 2026-11-06

- Added a native Codex/ChatGPT image-generation backend that requires no separate image API key.
- Native generation is preferred unless the user or project policy chooses an HTTP provider.
- Added backend selection guidance and documented the no-API subscription workflow.

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
