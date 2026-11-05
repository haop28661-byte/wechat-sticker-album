# Installation

## Project-local installation

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Scope Project -ProjectRoot "D:\your-project"
```

Installs:

```text
<project>/.agents/skills/wechat-sticker-album/
```

The current project receives the complete runtime directory:

- `SKILL.md`
- `agents/`
- `scripts/`
- `references/`
- `templates/`
- `vendor/`
- `docs/`
- license and notices

## Global installation

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Scope Global
```

Installs:

```text
$CODEX_HOME/skills/wechat-sticker-album/
```

If `CODEX_HOME` is not set:

```text
~/.codex/skills/wechat-sticker-album/
```

## Replace an existing installation

```powershell
.\install.ps1 -Scope Project -Force
```

`-Force` replaces the installation directory. It does not touch project outputs or configuration because those live outside the skill folder.

## Developer link mode

```powershell
.\install.ps1 -Scope Project -Link
```

Symlink installation requires operating-system permission. Use normal copy installation when links are unavailable.

## Python dependencies

```powershell
python -m pip install -r requirements.txt
```

No separate installation of GPT-Image2 Style Library or MemeSticker is required.
