"""Image provider adapters."""

from .base import ImageProvider, ProviderImage, ProviderResult
from .custom_http import CustomHttpProvider
from .openai_compatible import OpenAICompatibleProvider

__all__ = [
    "CustomHttpProvider",
    "ImageProvider",
    "OpenAICompatibleProvider",
    "ProviderImage",
    "ProviderResult",
]
