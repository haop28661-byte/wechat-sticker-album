# Security

## Secrets

- Prefer `api_key_env`.
- Never commit `.env`, `.wechat-sticker-album/config.json`, logs containing credentials, or generated source prompts containing private character data unless intended.
- Rotate any key that appears in a commit, issue, log, screenshot, or public chat.

## Provider access

Use only image APIs trusted by the current user. The skill sends the complete prompt and any supplied reference images to the configured provider.

## Generated files

Generated images and source sheets may be sensitive. `outputs/` is excluded from Git by default.

## Vulnerabilities

Do not publish a real API key in a vulnerability report. Provide a minimal reproduction and redact credentials.
