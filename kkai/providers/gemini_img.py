"""Gemini API image generation via google-genai (models.generate_content).

Verified on 21.10.2026 against google-genai 2.32 (ImageConfig.aspect_ratio /
image_size, FinishReason and BlockedReason values) and the
gemini-nano-banana-2.1 model page. Note: the current Google image guide shows
the newer Interactions API; generate_content remains in the SDK. To check in
the 26.10 API test: that generate_content works for this model, which
finish_reason a refusal returns, and the cost per 1K image.
"""

from __future__ import annotations

from . import ERROR, NO_IMAGE, OK, REFUSED, TECHNICAL, FatalProviderError, GenResult

SAFETY_REASONS = {"SAFETY", "IMAGE_SAFETY", "PROHIBITED_CONTENT", "IMAGE_PROHIBITED_CONTENT",
                  "BLOCKLIST", "SPII", "RECITATION", "IMAGE_RECITATION", "MODEL_ARMOR", "JAILBREAK"}


def _enum_name(v) -> str | None:
    if v is None:
        return None
    return getattr(v, "name", None) or str(v)


class GeminiImageProvider:
    def __init__(self, model: str, params: dict, api_key: str | None, timeout: float):
        from google import genai
        from google.genai import types
        self.types = types
        self.model = model
        self.params = dict(params)
        # HttpOptions.timeout is in milliseconds; no retry_options, so the SDK does not retry.
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout * 1000)))

    def _config(self):
        t = self.types
        p = dict(self.params)
        image_cfg = {k: p.pop(k) for k in ("aspect_ratio", "image_size") if k in p}
        modalities = p.pop("response_modalities", ["TEXT", "IMAGE"])
        return t.GenerateContentConfig(response_modalities=modalities,
                                       image_config=t.ImageConfig(**image_cfg) if image_cfg else None,
                                       **p)

    def generate(self, prompt: str, label: str = "") -> GenResult:
        from google.genai import errors

        try:
            resp = self.client.models.generate_content(model=self.model, contents=prompt, config=self._config())
        except errors.APIError as e:
            return self._api_error(e)
        except Exception as e:  # httpx timeouts and connection errors
            name = type(e).__name__.lower()
            if "timeout" in name or "connect" in name or "network" in name:
                return GenResult(status=TECHNICAL, error_code=type(e).__name__, error_message=str(e))
            raise

        from ..util import sha256_bytes
        raw = resp.model_dump(mode="json", exclude_none=True)
        headers = (raw.pop("sdk_http_response", None) or {}).get("headers") or {}
        headers = {k: v for k, v in headers.items() if k.lower().startswith(("x-", "server-timing", "date"))
                   and "key" not in k.lower()}
        images, mimes, texts = [], [], []
        finish = None
        for ci, cand in enumerate(resp.candidates or []):
            finish = finish or _enum_name(cand.finish_reason)
            for pi, part in enumerate((cand.content.parts if cand.content else None) or []):
                if part.inline_data is not None and part.inline_data.data:
                    images.append(part.inline_data.data)
                    mimes.append(part.inline_data.mime_type)
                    # Replace the bytes in the stored raw copy by a reference to the saved file.
                    rp = raw["candidates"][ci]["content"]["parts"][pi]
                    rp["inline_data"]["data"] = (f"<omitted: {len(part.inline_data.data)} bytes saved as image file, "
                                                 f"sha256={sha256_bytes(part.inline_data.data)}>")
                elif part.text and not part.thought:
                    texts.append(part.text)
        block = _enum_name(resp.prompt_feedback.block_reason) if resp.prompt_feedback else None
        res = GenResult(status=OK, raw={"headers": headers, "body": raw}, model_returned=resp.model_version,
                        response_id=resp.response_id, request_id=resp.response_id,
                        usage=raw.get("usage_metadata"), text_parts=texts, finish_reason=finish,
                        n_images_returned=len(images), http_status=200)
        if images:
            res.image, res.image_mime = images[0], mimes[0]
            return res
        if block or (finish in SAFETY_REASONS):
            res.status = REFUSED
            res.error_code = block or finish
            res.error_message = (resp.prompt_feedback.block_reason_message if resp.prompt_feedback else None) or " ".join(texts) or None
        else:
            res.status = NO_IMAGE
            res.error_code = finish or "no_image"
            res.error_message = " ".join(texts) or None
        return res

    def _api_error(self, e) -> GenResult:
        status = getattr(e, "code", None)
        message = getattr(e, "message", None) or str(e)
        st = getattr(e, "status", None)
        res = GenResult(status=ERROR, error_code=str(st or status), error_message=message, http_status=status,
                        raw={"error": getattr(e, "details", None)})
        low = message.lower()
        if status in (401, 403) or (status == 400 and "api key" in low):
            raise FatalProviderError(f"Gemini odrzuca klucz albo dostęp (HTTP {status}): {message}")
        if status == 404:
            raise FatalProviderError(f"Gemini: model {self.model} niedostępny (HTTP 404): {message}")
        if status == 400 and ("location" in low or "region" in low or "billing" in low):
            raise FatalProviderError(f"Gemini: {message}")
        if "safety" in low or "prohibited" in low or "blocked" in low:
            res.status = REFUSED
        elif status in (408, 429) or (status is not None and status >= 500):
            res.status = TECHNICAL
        return res
