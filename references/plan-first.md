# Plan-First Interaction

A request to make a sticker album starts the planning stage. It is not authorization to spend image-generation credits.

## Required sequence

1. Inspect the reference image and determine character identity anchors.
2. Select a provisional backend according to [backend-selection.md](backend-selection.md).
3. Create an album plan using `templates/album-plan.json`.
4. Present a concise human-readable summary containing:
   - selected backend and profile/model, or native generation
   - sticker count
   - theme
   - selected styles
   - captions policy
   - every sticker caption and action
   - supporting assets
   - output location
5. Stop and wait for explicit approval.

Do not generate source images before the approval gate closes.

## Approval

Statements such as “确认开始”, “按这个生成”, or “直接生成，不用确认” close the gate.

After approval:

1. Set `"approved": true` and record the user's confirmation in `approval_note`.
2. Run:

```powershell
python "<skill-root>\scripts\cli.py" validate-plan `
  --plan-file "<plan.json>" `
  --require-approved
```

3. Generate only after validation succeeds.

If the user requests changes, update the plan and present the revised summary. Approval of an earlier version does not approve changed captions, count, styles, backend, or supporting assets.

## Existing approved run

Do not reopen the album-level confirmation for retries, individual regenerations, finalization, or QA fixes that stay inside the approved plan.

## Direct-generation exception

Only an explicit request to skip confirmation permits immediate approved status. Record that request in `approval_note`.

## Working and final directories

Use separate folders:

```text
<project>/.wechat-sticker-album/work/<run>/plan.json
<project>/.wechat-sticker-album/work/<run>/source/
<project>/outputs/wechat-sticker-album/<run>/
```

The hidden work directory is gitignored. The visible output directory remains a clean final deliverable.
