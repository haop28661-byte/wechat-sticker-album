"""Configurable JSON HTTP adapter for non-OpenAI image APIs."""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from config import ConfigError, ProviderProfile
from providers.base import ProviderImage, ProviderResult
from providers.openai_compatible import ProviderRequestError, _guess_content_type


PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _render(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _render(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_render(item, context) for item in value]
    if isinstance(value, str):
        exact = PLACEHOLDER_RE.fullmatch(value)
        if exact:
            return context.get(exact.group(1), value)
        return PLACEHOLDER_RE.sub(
            lambda match: str(context.get(match.group(1), match.group(0))), value
        )
    return value


def _path_get(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(path)
    return current


class CustomHttpProvider:
    def __init__(self, profile: ProviderProfile):
        if not profile.custom_request or not profile.custom_response:
            raise ConfigError(
                "custom-http profiles require custom_request and custom_response objects"
            )
        self.profile = profile

    def _request(
        self,
        prompt: str,
        images: list[tuple[str, bytes, str]],
        size: str,
        output_format: str,
        background: str | None,
    ) -> ProviderResult:
        request_config = self.profile.custom_request or {}
        response_config = self.profile.custom_response or {}
        encoded_images = [
            {
                "filename": filename,
                "content_type": content_type,
                "base64": base64.b64encode(data).decode("ascii"),
            }
            for filename, data, content_type in images
        ]
        context = {
            "prompt": prompt,
            "model": self.profile.model,
            "size": size,
            "output_format": output_format,
            "background": background or "",
            "images": encoded_images,
            "image_base64": encoded_images[0]["base64"] if encoded_images else "",
        }
        method = str(request_config.get("method") or "POST").upper()
        url = str(request_config.get("url") or "")
        if not url:
            raise ConfigError("custom_request.url is required")
        headers = {"User-Agent": "wechat-sticker-album/2.0"}
        headers.update(
            {str(key): str(value) for key, value in (request_config.get("headers") or {}).items()}
        )
        if self.profile.api_key:
            headers[self.profile.api_key_header] = (
                self.profile.api_key_prefix + self.profile.api_key
            )
        body = _render(request_config.get("body") or {}, context)
        if request_config.get("body_type", "json") == "form":
            raise ConfigError("custom-http body_type=form is not supported; use JSON or extend the adapter")
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.profile.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise ProviderRequestError(f"Custom image API returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderRequestError(f"Custom image API request failed: {exc.reason}") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("Custom image API returned non-JSON content") from exc
        b64_path = response_config.get("image_base64_path")
        url_path = response_config.get("image_url_path")
        if b64_path:
            encoded = _path_get(payload, str(b64_path))
            if isinstance(encoded, str) and encoded.startswith("data:") and "," in encoded:
                encoded = encoded.split(",", 1)[1]
            image_bytes = base64.b64decode(encoded)
            return ProviderResult(ProviderImage(image_bytes, _guess_content_type(image_bytes)), {})
        if url_path:
            image_url = str(_path_get(payload, str(url_path)))
            download_headers = {"User-Agent": "wechat-sticker-album/2.0"}
            request_url = str(request_config.get("url") or "")
            if urllib.parse.urlparse(request_url).netloc.lower() == urllib.parse.urlparse(image_url).netloc.lower():
                download_headers.update(
                    {
                        str(key): str(value)
                        for key, value in (request_config.get("headers") or {}).items()
                    }
                )
                if self.profile.api_key:
                    download_headers[self.profile.api_key_header] = (
                        self.profile.api_key_prefix + self.profile.api_key
                    )
            image_request = urllib.request.Request(
                image_url, headers=download_headers, method="GET"
            )
            try:
                with urllib.request.urlopen(
                    image_request, timeout=self.profile.timeout_seconds
                ) as response:
                    image_bytes = response.read()
            except urllib.error.HTTPError as exc:
                raise ProviderRequestError(
                    f"Custom generated image download failed with HTTP {exc.code}"
                ) from exc
            except urllib.error.URLError as exc:
                raise ProviderRequestError(
                    f"Custom generated image download failed: {exc.reason}"
                ) from exc
            return ProviderResult(
                ProviderImage(image_bytes, _guess_content_type(image_bytes, image_url)),
                {"source_url": image_url},
            )
        raise ConfigError("custom_response requires image_base64_path or image_url_path")

    def generate(
        self,
        prompt: str,
        size: str,
        output_format: str,
        background: str | None = None,
    ) -> ProviderResult:
        return self._request(prompt, [], size, output_format, background)

    def edit(
        self,
        prompt: str,
        images: list[tuple[str, bytes, str]],
        size: str,
        output_format: str,
        background: str | None = None,
    ) -> ProviderResult:
        return self._request(prompt, images, size, output_format, background)
