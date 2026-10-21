"""Stand-in generator for --dry-run: grey images with the run number, no network."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

from . import OK, REFUSED, GenResult

# Every N-th call is a refusal so that the refusal path is exercised in dry runs.
REFUSE_EVERY = 13


class FakeProvider:
    def __init__(self, model: str, params: dict):
        self.model = model
        self.params = params
        self.calls = 0

    def generate(self, prompt: str, label: str = "") -> GenResult:
        self.calls += 1
        if self.calls % REFUSE_EVERY == 0:
            return GenResult(status=REFUSED, raw={"fake": True, "refused": True},
                             model_returned=f"fake/{self.model}", error_code="fake_refusal",
                             error_message="Dry-run refusal", finish_reason="SAFETY")
        img = Image.new("RGB", (1024, 1024), (128, 128, 128))
        draw = ImageDraw.Draw(img)
        draw.text((40, 40), f"DRY RUN {label}", fill=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return GenResult(status=OK, image=buf.getvalue(), image_mime="image/png",
                         raw={"fake": True}, model_returned=f"fake/{self.model}",
                         response_id=f"fake-{self.calls}", usage={"fake": True},
                         n_images_returned=1, finish_reason="STOP")
