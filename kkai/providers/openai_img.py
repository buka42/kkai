"""OpenAI Images API (/v1/images/generations).

Verified on 21.10.2026 against the openai SDK (images.generate parameters,
ImagesResponse fields) and the gpt-image-2.5-flare model page. To check in the
26.10 API test: the exact error code of a moderation refusal (assumed:
HTTP 400 with code 'moderation_blocked' or 'content_policy_violation').
"""

from __future__ import annotations

import base64
import json

from . import CORRUPT, ERROR, OK, REFUSED, TECHNICAL, FatalProviderError, GenResult

REFUSAL_CODES = {"moderation_blocked", "content_policy_violation", "content_filter", "safety_violation"}
# Header names kept in the log (never the Authorization header, which is a request header anyway).
KEEP_HEADERS = ("x-request-id", "openai-processing-ms", "openai-version", "openai-organization",
                "openai-model", "date")


def _strip_images(raw: dict, sha_by_index: dict[int, str]) -> dict:
    """Copy of the response with base64 image data replaced by a reference to the saved file."""
    out = json.loads(json.dumps(raw))
    for i, item in enumerate(out.get("data") or []):
        if isinstance(item, dict) and item.get("b64_json"):
            n = len(item["b64_json"])
            item["b64_json"] = f"<omitted: {n} base64 chars, decoded bytes saved as image file, sha256={sha_by_index.get(i)}>"
    return out


class OpenAIImageProvider:
    def __init__(self, model: str, params: dict, api_key: str | None, timeout: float):
        from openai import OpenAI
        self.model = model
        self.params = dict(params)
        # max_retries=0: retries are decided and logged by generate.py, not hidden in the SDK.
        self.client = OpenAI(api_key=api_key, timeout=timeout, max_retries=0)

    def generate(self, prompt: str, label: str = "") -> GenResult:
        import openai

        try:
            resp = self.client.images.with_raw_response.generate(model=self.model, prompt=prompt, **self.params)
        except openai.APITimeoutError as e:
            return GenResult(status=TECHNICAL, error_code="timeout", error_message=str(e))
        except openai.APIConnectionError as e:
            return GenResult(status=TECHNICAL, error_code="connection_error", error_message=str(e))
        except openai.APIStatusError as e:
            return self._status_error(e)

        headers = {k: resp.headers.get(k) for k in KEEP_HEADERS if resp.headers.get(k) is not None}
        try:
            raw = json.loads(resp.text)
        except ValueError as e:
            return GenResult(status=TECHNICAL, error_code="invalid_json", error_message=str(e),
                             http_status=resp.status_code)
        data = raw.get("data") or []
        images = []
        for item in data:
            b64 = item.get("b64_json") if isinstance(item, dict) else None
            if b64:
                try:
                    images.append(base64.b64decode(b64, validate=True))
                except ValueError:
                    images.append(None)
        from ..util import sha256_bytes
        sha = {i: sha256_bytes(b) for i, b in enumerate(images) if b}
        result = GenResult(
            status=OK,
            raw={"headers": headers, "body": _strip_images(raw, sha)},
            model_returned=raw.get("model") or headers.get("openai-model"),
            request_id=headers.get("x-request-id") or getattr(resp, "request_id", None),
            response_id=raw.get("id"),
            usage=raw.get("usage"),
            http_status=resp.status_code,
            n_images_returned=len(data),
        )
        if not data:
            result.status = ERROR
            result.error_code = "no_data"
            result.error_message = "Response contained no image data"
        elif images[0] is None:
            result.status = CORRUPT
            result.error_code = "invalid_base64"
        else:
            result.image = images[0]
            fmt = raw.get("output_format") or self.params.get("output_format") or "png"
            result.image_mime = f"image/{fmt}"
        return result

    def _status_error(self, e) -> GenResult:
        status = getattr(e, "status_code", None)
        body = e.body if isinstance(getattr(e, "body", None), dict) else {}
        err = body.get("error", body) if isinstance(body, dict) else {}
        code = (err.get("code") or err.get("type") or "") if isinstance(err, dict) else ""
        message = (err.get("message") if isinstance(err, dict) else None) or str(e)
        request_id = getattr(e, "request_id", None)
        res = GenResult(status=ERROR, error_code=str(code) or f"http_{status}", error_message=message,
                        http_status=status, request_id=request_id, raw={"error_body": body})
        low = f"{code} {message}".lower()
        if status in (401, 403):
            raise FatalProviderError(f"OpenAI odrzuca klucz albo dostęp (HTTP {status}): {message}. "
                                     "Sprawdź klucz i weryfikację organizacji.")
        if status == 404:
            raise FatalProviderError(f"OpenAI: model {self.model} niedostępny (HTTP 404): {message}")
        if status == 429 and ("insufficient_quota" in low or "billing" in low):
            raise FatalProviderError(f"OpenAI: brak środków lub limit konta: {message}")
        if code in REFUSAL_CODES or "safety system" in low or "moderation" in low:
            res.status = REFUSED
        elif status == 429 or (status is not None and status >= 500) or status == 408:
            res.status = TECHNICAL
        return res
