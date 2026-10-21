"""Providers against simulated API responses (no network, no keys)."""

import base64
import io
import json

import pytest
from PIL import Image

from kkai import providers as P


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, format="PNG")
    return buf.getvalue()


# --- OpenAI -----------------------------------------------------------------

def openai_provider(handler):
    httpx2 = pytest.importorskip("httpx2")
    from openai import OpenAI
    from kkai.providers.openai_img import OpenAIImageProvider
    prov = OpenAIImageProvider("gpt-image-test", {"size": "1024x1024", "quality": "medium", "n": 1}, "sk-test", 10)
    prov.client = OpenAI(api_key="sk-test", max_retries=0,
                         http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
    return prov


def test_openai_ok_saves_image_and_strips_base64():
    img = png()
    sent = {}

    def handler(request):
        sent.update(json.loads(request.content))
        body = {"created": 1, "data": [{"b64_json": base64.b64encode(img).decode()}],
                "output_format": "png", "usage": {"input_tokens": 10, "output_tokens": 100, "total_tokens": 110}}
        import httpx2
        return httpx2.Response(200, json=body, headers={"x-request-id": "req_123"})

    res = openai_provider(handler).generate("A photograph of Kraków.")
    assert sent["prompt"] == "A photograph of Kraków." and sent["model"] == "gpt-image-test"
    assert "response_format" not in sent
    assert res.status == P.OK and res.image == img and res.request_id == "req_123"
    assert res.usage["output_tokens"] == 100
    assert "omitted" in res.raw["body"]["data"][0]["b64_json"]


@pytest.mark.parametrize("status,code,expected", [
    (400, "moderation_blocked", P.REFUSED),
    (400, "content_policy_violation", P.REFUSED),
    (400, "invalid_value", P.ERROR),
    (429, "rate_limit_exceeded", P.TECHNICAL),
    (500, "server_error", P.TECHNICAL),
    (503, None, P.TECHNICAL),
])
def test_openai_error_classification(status, code, expected):
    import httpx2

    def handler(request):
        return httpx2.Response(status, json={"error": {"message": f"msg {code}", "code": code, "type": "x"}})

    res = openai_provider(handler).generate("p")
    assert res.status == expected
    assert res.http_status == status


@pytest.mark.parametrize("status,body", [
    (401, {"error": {"message": "Incorrect API key", "code": "invalid_api_key"}}),
    (403, {"error": {"message": "Organization must be verified", "code": None}}),
    (404, {"error": {"message": "model not found", "code": "model_not_found"}}),
    (429, {"error": {"message": "You exceeded your current quota", "code": "insufficient_quota"}}),
])
def test_openai_fatal_errors(status, body):
    import httpx2
    prov = openai_provider(lambda r: httpx2.Response(status, json=body))
    with pytest.raises(P.FatalProviderError):
        prov.generate("p")


# --- Gemini -----------------------------------------------------------------

def gemini_provider(response=None, error=None):
    from kkai.providers.gemini_img import GeminiImageProvider
    prov = GeminiImageProvider("gemini-test", {"image_size": "1K", "aspect_ratio": "1:1"}, "k", 10)
    calls = {}

    class Models:
        def generate_content(self, model, contents, config):
            calls.update(model=model, contents=contents, config=config)
            if error:
                raise error
            return response

    class Client:
        models = Models()

    prov.client = Client()
    return prov, calls


def gresp(parts=None, finish="STOP", block=None):
    from google.genai import types
    cands = [] if parts is None else [types.Candidate(content=types.Content(role="model", parts=parts),
                                                       finish_reason=finish)]
    return types.GenerateContentResponse(
        candidates=cands, model_version="gemini-test-001", response_id="resp_1",
        prompt_feedback=types.GenerateContentResponsePromptFeedback(block_reason=block) if block else None,
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=7, candidates_token_count=1290))


def test_gemini_ok_with_text_and_thoughts():
    from google.genai import types
    img = png()
    parts = [types.Part(text="thinking...", thought=True), types.Part(text="Here is Kraków."),
             types.Part(inline_data=types.Blob(mime_type="image/png", data=img))]
    prov, calls = gemini_provider(gresp(parts))
    res = prov.generate("A photograph of Kraków.")
    assert calls["config"].image_config.image_size == "1K"
    assert calls["config"].image_config.aspect_ratio == "1:1"
    assert res.status == P.OK and res.image == img
    assert res.text_parts == ["Here is Kraków."]
    assert res.model_returned == "gemini-test-001" and res.response_id == "resp_1"
    dumped = json.dumps(res.raw)
    assert "omitted" in dumped and "thinking..." in dumped


def test_gemini_prompt_block_is_refusal():
    prov, _ = gemini_provider(gresp(None, block="PROHIBITED_CONTENT"))
    res = prov.generate("p")
    assert res.status == P.REFUSED and res.error_code == "PROHIBITED_CONTENT"


@pytest.mark.parametrize("finish,expected", [("IMAGE_SAFETY", P.REFUSED), ("SAFETY", P.REFUSED),
                                             ("NO_IMAGE", P.NO_IMAGE), ("OTHER", P.NO_IMAGE)])
def test_gemini_no_image_finish_reasons(finish, expected):
    from google.genai import types
    prov, _ = gemini_provider(gresp([types.Part(text="I can't make that.")], finish=finish))
    res = prov.generate("p")
    assert res.status == expected and res.error_code == finish
    assert res.error_message == "I can't make that."


@pytest.mark.parametrize("code,expected", [(429, P.TECHNICAL), (500, P.TECHNICAL), (503, P.TECHNICAL),
                                           (400, P.ERROR)])
def test_gemini_api_errors(code, expected):
    from google.genai import errors
    err = errors.APIError(code, {"error": {"code": code, "message": "x", "status": "S"}})
    prov, _ = gemini_provider(error=err)
    assert prov.generate("p").status == expected


def test_gemini_bad_key_is_fatal():
    from google.genai import errors
    err = errors.APIError(400, {"error": {"code": 400, "message": "API key not valid.", "status": "INVALID_ARGUMENT"}})
    prov, _ = gemini_provider(error=err)
    with pytest.raises(P.FatalProviderError):
        prov.generate("p")
