---
name: wechat-sticker-album
description: Produce a complete WeChat sticker album from a character reference image using a user-configured image API, including a variable-count sticker set, artist cover, chat-list icon, opaque banner, appreciation guide, thank-you reward image, metadata suggestions, preview, QA, transparent-PNG processing, and project-local folder output. Use when a user wants to plan or generate a multi-asset WeChat sticker album; use a general image workflow instead for a single unrelated image.
---

# WeChat Sticker Album

Turn one character reference image into a coherent WeChat sticker album and its supporting assets using the provider configured by the current user.

## Deliverables

Produce the requested sticker count plus, unless explicitly omitted:

- one artist cover
- one chat-list icon
- one opaque display banner
- one appreciation guide when appreciation is in scope
- one thank-you reward image when appreciation is in scope
- one preview image
- one complete project-local output folder
- metadata suggestions for name, introduction, style, and theme

Read [references/production-spec.md](references/production-spec.md) before planning counts, metadata, QA, retries, or delivery.

Read [references/prompt-recipes.md](references/prompt-recipes.md) before writing prompts.

Read [references/provider-config.md](references/provider-config.md) before configuring or diagnosing an image API.

## Runtime dependencies

- Use Python 3.10 or newer.
- Install `requirements.txt`.
- Use `scripts/cli.py` for provider checks, generation, finalization, and installation.
- Use `vendor/meme-sticker/scripts/sticker_sheet_lib.py` only through the bundled finalizer.
- Read the vendored style reference at `vendor/gpt-image-2-style-library/references/style-library.md` when a visual style template is needed.

Never print, store in generated metadata, or commit an API key.

## Workflow

### 1. Confirm provider readiness

Use the existing project configuration, user configuration, or environment-only configuration described in [references/provider-config.md](references/provider-config.md).

Run:

```powershell
python "<skill-root>\scripts\cli.py" doctor
```

Use `--probe` only when the configured provider exposes a compatible `GET /models` endpoint.

Completion: the selected profile has a provider type, base URL, model, credential source, and explicit capability settings.

### 2. Establish the album contract

Inspect the reference image and identify the non-negotiable identity anchors: face, silhouette, ears, hair or wool, horns, markings, clothing, accessories, palette, and line treatment.

Collect or infer:

- sticker count and theme
- captions or no-caption mode
- 1 or 2 approved visual styles
- required supporting assets
- name and introduction rules
- project-local output folder name

Completion: every required asset, count, theme, style, and character anchor is explicit.

### 3. Plan before generation

Create a numbered plan with distinct captions, actions, expressions, and prop or outfit changes. Ensure at least half of the meanings support the selected theme.

When the user has not explicitly authorized generation, stop after presenting the plan and prompt draft.

Completion: the user accepted the plan or explicitly asked to start generation.

### 4. Generate sticker batches

For `N` stickers:

- generate `floor(N / 6)` sheets, each exactly 3 columns by 2 rows
- generate the remaining `N % 6` stickers singly

Use the configured profile and preferred model:

```powershell
python "<skill-root>\scripts\cli.py" generate `
  --profile "<profile>" `
  --reference "<reference.png>" `
  --prompt-file "<sheet-prompt.txt>" `
  --size "<sheet-size-from-profile>" `
  --output "<project>/outputs/wechat-sticker-album/<run>/source/sheet-01.png"
```

If the profile supports reference-image editing, use it. If it is text-only, use `--text-only` only after warning that identity consistency will be weaker.

When a profile has `fallback_profiles`, the CLI retries those profiles in order after provider failure. Inspect each sheet before generating the next.

Completion: character identity, cell boundaries, captions, and absence of unintended text pass visual inspection.

### 5. Generate supporting assets

Use the prompt recipes for:

- artist cover: recognizable half/full body, transparent, no white die-cut outline
- chat-list icon: complete frontal head, transparent, no square frame
- banner: opaque, story-driven, no text
- appreciation guide: opaque 75:56 with text-free and text versions
- thank-you image: opaque 1:1 with text-free and text versions

Generate text-free bases for appreciation assets. Use a local font and the approved Chinese copy to create text versions.

Completion: each source image passes character, composition, relevant-content, opacity, and aspect-ratio checks.

### 6. Finalize into the project

Write output below the current project:

```text
<project>/outputs/wechat-sticker-album/<timestamp>-sticker-album/
```

Run the finalizer:

```powershell
python "<skill-root>\scripts\finalize_album.py" `
  --sheet "<sheet-01.png>" --sheet "<sheet-02.png>" `
  --single "<single-01.png>" `
  --cover-source "<cover-source.png>" `
  --chat-icon-source "<chat-icon-source.png>" `
  --banner-source "<banner-source.png>" `
  --appreciation-source "<appreciation-clean.png>" `
  --appreciation-text-source "<appreciation-text.png>" `
  --thank-you-source "<thank-you-clean.png>" `
  --thank-you-text-source "<thank-you-text.png>" `
  --output-dir "<project>/outputs/wechat-sticker-album/<run>" `
  --expected-count "<N>" `
  --metadata-json "<metadata.json>"
```

The finalizer creates the complete folder by default. Add `--zip` only when the user asks for an archive.

Completion: the command exits successfully, every expected asset appears, and `manifest.json` matches the folder.

### 7. Deliver

Present the preview first, then the output folder path and optional ZIP. Report verified counts, dimensions, opacity/transparency, file-size limits, provider profile, and unresolved warnings.

Do not present failed source images, temporary extraction output, API credentials, or debug traces unless the user asks for them.
