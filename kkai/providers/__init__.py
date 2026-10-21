"""Image generation providers.

Each provider turns one prompt into one GenResult. Providers never retry and
never decide what to do next: generate.py does that from GenResult.status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Status values written to generation_log.jsonl.
OK = "ok"                    # an image was returned
REFUSED = "refused"          # refusal or content block: a result, never retried
NO_IMAGE = "no_image"        # the API answered but returned no image, without a safety reason
TECHNICAL = "error_technical"  # timeout, 5xx, 429 rate limit: retried
CORRUPT = "corrupt_file"     # image bytes cannot be decoded: retried once
ERROR = "error"              # other client error (bad parameter etc.): not retried


class FatalProviderError(Exception):
    """Stops the whole run (wrong key, no access, model not found, no credits)."""


@dataclass
class GenResult:
    status: str
    image: bytes | None = None
    image_mime: str | None = None
    raw: Any = None                  # raw API response (dict), image payload replaced by a reference
    model_returned: str | None = None
    request_id: str | None = None
    response_id: str | None = None
    usage: Any = None
    text_parts: list[str] = field(default_factory=list)
    finish_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    http_status: int | None = None
    n_images_returned: int = 0


def make_provider(provider: str, model: str, params: dict, api_key: str | None, timeout: float):
    if provider == "openai":
        from .openai_img import OpenAIImageProvider
        return OpenAIImageProvider(model, params, api_key, timeout)
    if provider == "gemini":
        from .gemini_img import GeminiImageProvider
        return GeminiImageProvider(model, params, api_key, timeout)
    if provider == "fake":
        from .fake import FakeProvider
        return FakeProvider(model, params)
    raise ValueError(f"unknown provider {provider!r}")
