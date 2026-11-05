"""Provider interfaces shared by image backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ProviderImage:
    data: bytes
    content_type: str = "image/png"


@dataclass
class ProviderResult:
    image: ProviderImage
    metadata: dict = field(default_factory=dict)


class ImageProvider(Protocol):
    def generate(
        self,
        prompt: str,
        size: str,
        output_format: str,
        background: str | None = None,
    ) -> ProviderResult: ...

    def edit(
        self,
        prompt: str,
        images: list[tuple[str, bytes, str]],
        size: str,
        output_format: str,
        background: str | None = None,
    ) -> ProviderResult: ...
