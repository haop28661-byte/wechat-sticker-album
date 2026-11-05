# Production Specification

Use this reference for album planning, metadata validation, recovery decisions, and final acceptance.

## Output contract

| Asset | Default | Required properties |
| --- | --- | --- |
| Sticker | 240 x 240 PNG | RGBA, transparent, no white die-cut outline, sequential filenames |
| Artist cover | 240 x 240 PNG | RGBA, transparent, at most 500 KB, recognizable half/full body |
| Chat-list icon | 50 x 50 PNG | RGBA, transparent, at most 100 KB, head-focused, no square frame |
| Banner | 750 x 400 PNG | RGB, fully opaque, no text, exact 15:8 ratio |
| Appreciation guide | 750 x 560 JPG/PNG | Clean and text variants, RGB, fully opaque, each at most 500 KB, exact 75:56 ratio |
| Thank-you image | 750 x 750 JPG/PNG | Clean and text variants, RGB, fully opaque, each at most 500 KB, exact 1:1 ratio |
| Preview | JPG | Shows all stickers and available supporting assets |
| Package | Project folder | Contains all final assets and `manifest.json`; ZIP is optional with `--zip` |

The default album size is 24 stickers. Any positive sticker count is valid. Generate full 3 x 2 sheets for groups of six and individual stickers for the remainder.

Always place output below the current project:

```text
<project>/outputs/wechat-sticker-album/<timestamp>-sticker-album/
```

## Planning and metadata

Name:

- Chinese only
- 1 to 8 characters
- prefer 5 characters or fewer
- no punctuation and no spaces
- run a practical duplicate check; the publishing platform remains authoritative

Introduction:

- 80 characters or fewer
- convey the character's visual identity or an album story

Style:

- select 1 or 2 from 日常, 软萌可爱, 二次元, 长辈风, 搞笑, 丧/佛系, 魔性鬼畜, 恶搞, 简笔画, 赛博朋克, 蒸汽波, 像素, 暗黑, 复古

Theme:

- select 1 from 万能通用, 网络热点, 节日, 考试/学习, 工作/职场, 情侣, 毕业, 刷屏, 红包相关, 游戏, 运动/健身, 怼人/斗图, 群聊必备, 节气, 邀约/约起来, 励志鼓舞
- keep at least half of the sticker meanings aligned with that theme

Optional metadata JSON:

```json
{
  "name": "福咩咩拜年",
  "intro": "福咩咩穿红金唐装陪你拜年，用一组热闹表情记录团圆、年俗和过年日常。",
  "styles": ["日常", "软萌可爱"],
  "theme": "节日"
}
```

## Prompt acceptance

Every sticker prompt must lock:

- non-negotiable character identity anchors
- exact caption and action when captions are in scope
- a 3 x 2 sheet with six invisible territories and generous gutters
- one flat chroma-key background for sheet extraction
- a clear sticker outline strategy
- a prohibition on unintended text, watermarks, UI, and cropped anatomy

Appreciation and thank-you prompts must lock:

- a text-free opaque base with a clean region for exact local text overlay
- only the character, this album's stickers or album, and minimal related decoration
- the requested aspect ratio and final size
- no payment imagery, money, QR codes, unrelated products, or unrelated scenes
- no checkerboard, transparency preview pattern, white canvas, or hard frame

Supporting-asset prompts must lock their aspect ratio, composition role, text policy, opacity, and edge policy in addition to character identity.

## Recovery rules

Apply the smallest repair:

| Failure | Action |
| --- | --- |
| Transient API failure | Retry once, then use the profile's configured fallback profiles |
| One sheet fails | Regenerate only that sheet |
| Transparent-background parameter rejected | Generate on flat `#00FFFF`, then run the bundled matte finalizer |
| Caption wrong or extra text appears | Regenerate the affected sheet or use a focused edit |
| Subject touches a cell edge | Regenerate with smaller subjects and wider gutters |
| Output dimensions differ slightly | Crop excess edges symmetrically to the exact ratio, then proportional resize; never stretch |
| Icon/cover has a white outline or square frame | Regenerate that asset with the corrected edge contract |
| Checkerboard appears in an opaque image | Describe a fully painted festival-poster background and regenerate; use the configured quality profile if available |
| Appreciation/thank-you text is inaccurate | Regenerate the base without text and overlay exact Chinese copy locally |
| More than two substantive failures on one asset | Stop and report the exact unresolved problem instead of looping |

## Final acceptance

Reject a pack unless all conditions hold:

- expected sticker count is present and filenames are sequential
- every sticker is exactly 240 x 240 RGBA with meaningful transparency
- cover and icon meet their dimensions, transparency, and size limits
- banner is exactly 750 x 400 with no alpha channel and is not a near-white blank
- appreciation guide, when present, is exactly 750 x 560 RGB and at most 500 KB
- thank-you image, when present, is exactly 750 x 750 RGB and at most 500 KB
- appreciation and thank-you images are fully opaque and contain only sticker-related content
- when both are available, clean and text variants are both packaged
- all rounded shapes and the character remain proportionate
- no sticker has a hard square background or unwanted border
- captions and meanings are distinct when captions are enabled
- at least half of the meanings match the selected theme
- manual visual inspection finds consistent identity and no unintended text
- `manifest.json` matches the packaged files
