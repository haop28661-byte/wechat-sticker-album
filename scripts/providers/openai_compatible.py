"""OpenAI-compatible images/generations and images/edits adapter."""

from __future__ import annotations

import base64
import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from config import ProviderProfile
from providers.base import ProviderImage, ProviderResult


class ProviderRequestError(RuntimeError):
    pass


def _endpoint(base_url: str, value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme and parsed.netloc:
        return value
    return base_url.rstrip("/") + "/" + value.lstrip("/")


def _guess_content_type(data: bytes, url: str = "") -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    guessed = mimetypes.guess_type(url)[0] if url else None
    return guessed or "application/octet-stream"


class OpenAICompatibleProvider:
    def __init__(self, profile: ProviderProfile):
        self.profile = profile
        self.base_origin = urllib.parse.urlparse(profile.base_url).netloc.lower()

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "wechat-sticker-album/2.0"}
        headers.update(self.profile.extra_headers)
        if self.profile.api_key:
            headers[self.profile.api_key_header] = (
                self.profile.api_key_prefix + self.profile.api_key
            )
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _open_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.profile.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise ProviderRequestError(
                f"Image API returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderRequestError(f"Image API request failed: {exc.reason}") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("Image API returned non-JSON content") from exc
        if not isinstance(payload, dict):
            raise ProviderRequestError("Image API response root must be a JSON object")
        return payload

    def _extract_image(self, payload: dict[str, Any]) -> tuple[bytes, str, dict]:
        candidates = []
        if payload.get("b64_json"):
            candidates.append((payload["b64_json"], None))
        data = payload.get("data")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            candidates.append((data[0].get("b64_json"), data[0].get("url")))
        if not candidates:
            raise ProviderRequestError("Image API response did not contain b64_json or url")
        encoded, image_url = candidates[0]
        if encoded:
            if isinstance(encoded, str) and encoded.startswith("data:") and "," in encoded:
                encoded = encoded.split(",", 1)[1]
            try:
                image_bytes = base64.b64decode(encoded)
            except Exception as exc:
                raise ProviderRequestError("Could not decode b64_json image data") from exc
            return image_bytes, _guess_content_type(image_bytes), {}
        if not image_url:
            raise ProviderRequestError("Image API response contained neither image data nor URL")
        return self._download(image_url), _guess_content_type(b"", image_url), {
            "source_url": image_url
        }

    def _download(self, url: str) -> bytes:
        headers = {"User-Agent": "wechat-sticker-album/2.0"}
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc.lower() == self.base_origin:
            headers.update(self._headers())
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.profile.timeout_seconds) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise ProviderRequestError(
                f"Generated image download failed with HTTP {exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderRequestError(f"Generated image download failed: {exc.reason}") from exc

    def _base_payload(
        self,
        prompt: str,
        size: str,
        output_format: str,
        background: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.profile.model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "output_format": output_format,
        }
        if background and self.profile.supports_transparent_background:
            payload["background"] = background
        return payload

    def generate(
        self,
        prompt: str,
        size: str,
        output_format: str,
        background: str | None = None,
    ) -> ProviderResult:
        payload = self._base_payload(prompt, size, output_format, background)
        payload.update(self.profile.extra_generation)
        request = urllib.request.Request(
            _endpoint(self.profile.base_url, self.profile.generation_endpoint),
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers("application/json"),
            method="POST",
        )
        response = self._open_json(request)
        data, content_type, metadata = self._extract_image(response)
        return ProviderResult(ProviderImage(data, content_type), metadata)

    def edit(
        self,
        prompt: str,
        images: list[tuple[str, bytes, str]],
        size: str,
        output_format: str,
        background: str | None = None,
    ) -> ProviderResult:
        fields = self._base_payload(prompt, size, output_format, background)
        fields.update(self.profile.extra_edit)
        boundary = f"----wechat-sticker-{uuid.uuid4().hex}"
        chunks: list[bytes] = []
        for key, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                    str(value).encode(),
                    b"\r\n",
                ]
            )
        for index, (filename, data, content_type) in enumerate(images):
            safe_name = Path(filename).name.replace('"', "") or f"image-{index}"
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    (
                        f'Content-Disposition: form-data; name="{self.profile.image_field}"; '
                        f'filename="{safe_name}"\r\n'
                    ).encode(),
                    f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n".encode(),
                    data,
                    b"\r\n",
                ]
            )
        chunks.append(f"--{boundary}--\r\n".encode())
        request = urllib.request.Request(
            _endpoint(self.profile.base_url, self.profile.edit_endpoint),
            data=b"".join(chunks),
            headers=self._headers(f"multipart/form-data; boundary={boundary}"),
            method="POST",
        )
        response = self._open_json(request)
        data, content_type, metadata = self._extract_image(response)
        return ProviderResult(ProviderImage(data, content_type), metadata)
