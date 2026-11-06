# Generation Backend Selection

Use one of two backends. Do not ask for API configuration when native image generation is available.

## Selection order

1. Explicit user request:
   - “use my API” selects HTTP.
   - “use ChatGPT/Codex image generation” selects native.
2. Project policy:
   - Follow `AGENTS.md` or equivalent project instructions when they require a specific provider.
3. Native capability:
   - If the current Codex session exposes an image-generation tool or the available `imagegen` skill, use native generation.
4. HTTP provider:
   - If native generation is unavailable, use the configured OpenAI-compatible or custom HTTP profile.
5. No backend:
   - Ask the user to choose native generation or configure an HTTP provider.

Backend selection is included in the album plan confirmation. Do not open a separate API dialog when the selected backend already works.

## Native backend

Use when the current session can generate images itself, including a ChatGPT Plus or similar subscription-backed Codex image tool.

Requirements:

- No separate image API key.
- No `doctor` call.
- No API connection prompt.
- Save generated source images under:
  `<project>/.wechat-sticker-album/work/<run>/source/`
- Continue using the bundled finalizer, metadata validation, and project-local output rules.

Native generation may have different output dimensions. The deterministic finalizer still converts final assets to the required sizes.

## HTTP backend

Use when native generation is unavailable, the user chooses a third-party API, or project policy requires one.

Requirements:

- Read [provider-config.md](provider-config.md).
- Run `scripts/cli.py doctor`.
- Generate through `scripts/cli.py generate`.
- Never expose or commit credentials.

## Mixed preference

Do not silently mix backends across one album. Choose one backend for the album unless the user explicitly asks to regenerate a specific asset elsewhere.
