# Prompt Recipes

Use these recipes as contracts to adapt to the user's character, theme, and chosen style. Preserve exact positive requirements; change subject details only when the album contract permits it.

## Character anchor block

Start every prompt with a compact identity lock:

```text
Use the attached character image as the canonical character reference.
Preserve its face, head silhouette, species cues, ears, hair/wool, horns,
markings, body proportions, clothing, palette, line treatment, and signature
accessories. Every result must read as the same character.
```

Then name the concrete anchors observed in the reference. Replace generic words with the actual measurements or features.

## Sticker sheet

Generate exactly six stickers per sheet, arranged 3 columns by 2 rows:

```text
Create one landscape 3:2 sticker sheet with exactly six independent stickers,
arranged in 3 columns and 2 rows. Use six invisible territories.
Keep every character, caption, prop, outline, and decoration fully inside its
own territory with clear empty gutters. Do not draw grid lines, numbers,
headers, UI, watermarks, or anything outside the six stickers.

Use a single perfectly flat #00FFFF chroma-key background from edge to edge.
Do not use #00FFFF anywhere in the artwork. Give every sticker a clean white
die-cut outline with no colored glow. Use [caption treatment]. Captions must be
short, accurate, and distinct.

Sheet content:
1. [expression] — [action and prop] — caption “[2-4 characters]”
2. ...
```

After generation, inspect the full sheet before generating the next one. Confirm exact six-cell separation, complete anatomy, identity consistency, correct captions, and a uniform key background.

## Single sticker

Use the same character and sticker contract as a sheet, but output one centered sticker with transparent final delivery. Keep sufficient clearance so the finalizer does not clip ears, horns, hands, captions, or props.

## 24-sticker New Year example plan

Adapt these meanings when the user wants a general Spring Festival album:

- 拜年吉祥: 新年快乐, 恭喜发财, 大吉大利, 平安喜乐, 万事如意, 步步高升
- 年夜饭: 开饭啦, 吃饺子, 年年有余, 团团圆圆, 甜甜蜜蜜, 干杯
- 春节年俗: 贴春联, 挂灯笼, 放烟花, 看舞狮, 收压岁钱, 守岁
- 过年日常: 回家啦, 全家福, 走亲戚, 年后开工, 新年加油, 比个心

Keep captions and meanings distinct when adapting this plan.

## Artist cover

```text
Create a 1:1 artist-profile cover using the canonical character.
Show a recognizable half-body or full-body view, not a head-only crop.
Use a clean transparent-ready silhouette and a simple pose.
Fill most of the frame while keeping horns, ears, hands, and clothing intact.
Use the character's continuous dark contour where present.
Do not add a white die-cut outline, white outer glow, square frame, scene,
props unrelated to identity, text, logo, or watermark.
```

## Chat-list icon

```text
Create a 1:1 chat-list icon using the canonical character.
Show the complete frontal head, including both ears and horns, with a clear
recognizable expression. A very small collar detail is allowed.
Center the head and fill most of the frame with tight transparent margins.
Simplify fine embroidery and texture so the face remains legible at 50 px.
Use a continuous dark contour. Do not add a white outline, white glow,
square frame, body, hands, props, text, logo, or watermark.
```

## Opaque banner

```text
Create one horizontal 15:8 opaque display banner using the canonical character.
Build a simple story related to the sticker album, such as the character making,
choosing, or sending the stickers. Keep the main character dominant and the
secondary story elements readable.
Use a lively palette that clearly differs from WeChat's pale neutral and green
interfaces. Fill the whole canvas with an opaque background.
Do not include any text, letters, numbers, logo, watermark, transparent area,
white canvas, stretched geometry, or square frame.
```

## Appreciation guide

```text
Create one opaque 75:56 appreciation guide illustration using the canonical character.
Show the character sincerely offering a glowing heart beside an open sticker album.
Include three to five representative stickers from this same album.
Keep the composition warm, celebratory, and immediately related to the sticker set.
Reserve one clean text-safe area; keep the generated image free of text.
Fill every pixel with a lively opaque coral-red festival background.
Do not use a white canvas, checkerboard, transparency grid, payment imagery,
money, QR code, unrelated product, unrelated scene, or square frame.
```

Recommended local overlay:

```text
喜欢福咩咩吗
送颗小心心吧
```

Deliver both the clean base and the text version. Use cream text with a deep-red outline.

## Thank-you reward image

```text
Create one opaque 1:1 thank-you illustration using the canonical character.
Show the character making a small grateful bow while holding a glowing heart.
Place a closed sticker album and a few representative stickers nearby.
Create a warm feeling of celebration and a natural desire to share the set.
Reserve one clean text-safe area; keep the generated image free of text.
Fill every pixel with an opaque red-gold festival background.
Do not use a white canvas, checkerboard, transparency grid, payment imagery,
money, QR code, gift product, unrelated scene, or square frame.
```

Recommended local overlay:

```text
谢谢你的喜欢
把这份福气分享给朋友
```

Deliver both the clean base and the text version. Use cream text with a deep-red outline.

## Transparent-asset prompt suffix

Use this when the image API accepts transparent output directly:

```text
Output an opaque character on a fully transparent background. Keep the alpha
edge smooth. Do not render a checkerboard, white backing, white outline,
colored fringe, shadow card, or circular backing.
```

When transparent output is rejected, switch the background contract to a single flat `#00FFFF` and finalize through `scripts/finalize_album.py`.
