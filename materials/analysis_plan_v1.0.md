# Analysis plan and codebook freeze

Version 1.0, frozen on 24 October 2026 and tagged `v1.0-freeze` in this repository before the main data collection. Study: *Multiculturalism in the past tense? Heritage, religion and generative images of Kraków and Kazimierz.* Author: [anonymised for review].

## 1. Data status

At the time of tagging, only the API test (16 images), pilot 1 (32 images, earlier wording ‘Fotografia przedstawiająca… / A photograph of…’) and pilot 2 (32 images, final wording) had been generated. None of them enters the analysis. The prompt wording was changed after pilot 1, in which 31 of 32 images had a contemporary frame and all were colour photographs; pilot-1 prompts, codes and results go to the supplementary materials. The 640 images of the main study are generated after this tag.

## 2. Hypotheses

All confirmatory hypotheses are directional.

| Code | Hypothesis | Comparison | Indicator |
|---|---|---|---|
| H1 | The word ‘multicultural’ increases the share of historical or staged historical frames | W vs B | `temporal_frame` ∈ {historical, staged_historical} |
| H2 | The H1 effect persists when the prompt adds ‘today’ | WT vs T | as in H1 |
| H3 | The word ‘multicultural’ increases the share of the heritage or spectacle mode | W vs B | `mode_of_culture.dominant` ∈ {heritage, spectacle} |
| H4 | With ‘today’, a non-contemporary frame is more frequent for Kazimierz than for Kraków | T-Z vs T-K | `temporal_frame` ≠ contemporary |
| P5 | In what form religion appears (building, symbol or object, practice) | all conditions | `religion.form`; exploratory |
| P6 | Whether ‘multicultural’ changes the medium of the image (aged photograph, illustration) | W vs B, Polish and English separately | `medium` ∈ {photo_aged, illustration}; exploratory |

H1 and H3 are not independent: a costumed figure can produce both `staged_historical` and `spectacle`.

## 3. Design and prompts

4 framings (B, W, T, WT) × 2 scales (Kraków, Kazimierz) × 2 languages (Polish, English) × 2 systems × 20 repetitions = 640 images. Prompts verbatim:

| Code | Polish | English |
|---|---|---|
| B-K | `Obraz przedstawiający Kraków.` | `An image of Kraków.` |
| W-K | `Obraz przedstawiający wielokulturowy Kraków.` | `An image of multicultural Kraków.` |
| T-K | `Obraz przedstawiający Kraków dzisiaj.` | `An image of Kraków today.` |
| WT-K | `Obraz przedstawiający wielokulturowy Kraków dzisiaj.` | `An image of multicultural Kraków today.` |
| B-Z | `Obraz przedstawiający Kazimierz w Krakowie.` | `An image of Kazimierz in Kraków.` |
| W-Z | `Obraz przedstawiający wielokulturowy Kazimierz w Krakowie.` | `An image of multicultural Kazimierz in Kraków.` |
| T-Z | `Obraz przedstawiający Kazimierz w Krakowie dzisiaj.` | `An image of Kazimierz in Kraków today.` |
| WT-Z | `Obraz przedstawiający wielokulturowy Kazimierz w Krakowie dzisiaj.` | `An image of multicultural Kazimierz in Kraków today.` |

Systems: OpenAI GPT Image 2.5 Flare (`gpt-image-2.5-flare-2026-09-08`, Images API) and Google Gemini Nano Banana 2.1 (`gemini-nano-banana-2.1`, Gemini API); the model name returned by the API is logged for every request where the API provides one (the OpenAI Images API returns none, so for GPT Image the requested dated version is the record), via API, 1024 × 1024, 1 image per request, no system instruction, no conversation context. Requests are shuffled with a recorded seed and run in 1 day.

## 4. Sample size

80 images per group in each H1–H3 comparison (per system, pooled over languages and scales) and 40 per group in H4 (per system, pooled over languages). With 80 per group, a difference of about 20 percentage points is detectable at about 80% power; with 40 per group, about 30 points.

## 5. Coding

Codebook v1.0, coder instruction v1.0 and output schema v1.0 are in this tag (SHA-256 of the files as committed: codebook `eba3335b9b213b1dbab12bbb97d89a8699f5acdc8cdb1dc26d69d4f853277c5c`, coder instruction `8f4d48541881ef3a6addc0d91b9f842d424c69524252ae403e9f8c4a017cb486`, schema `83069d3f1f70ec33727ab5fbe691f657fad0e26800498dac672d10fac8406a81`, second-coder instruction `e5487905cd24588a2e096395b083ddb5ef98ad4c38e93213ee50c4e6406e180b`; `SHA256SUMS` in this tag lists all frozen files, and the program logs the hash of the instruction text sent with each call, which for v1.0 is `0314c5f307613337fd69a95555c5ad4727b3318bb2d26d40edaac5465867f8f5` with LF line endings). A multimodal model (`gpt-6.1-sol`, Batch API) codes all 640 images without knowledge of prompt, condition or system; no dated model snapshot is available, so the returned model name is logged for every call. I code a validation set of 160 images (5 per condition) blind, before seeing model codes. The model runs at a fixed temperature of 1.0, so its output varies between calls; it codes the validation set twice to measure this (stability). A second human coder codes 50 of the 160 images on `temporal_frame`, `mode_of_culture.dominant` and `religion.form`. I recode 50 of the 160 after at least 7 days (test–retest).

All human coding is done without AI tools, each image from scratch. Per variable, on the 160 images (Krippendorff's α, nominal):

| Result | Treatment of the other 480 images |
|---|---|
| α model–author ≥ .80, model stability ≥ .90, no differential error | review of this variable only in images carrying a flag that concerns it |
| α .67–.80 | review of this variable in all 480 |
| α < .67, or model errors more frequent in W and WT than in B and T | manual coding of this variable in all 480 |

Differential error is tested with Fisher's exact test (error rate in W/WT vs B/T, and by system).

When one category covers more than 90% of the validation images, α can be low despite high agreement. Then percent agreement and Gwet's AC1 are reported as well, and the variable meets the .80 threshold if agreement ≥ 95% and AC1 ≥ .80 (the .67 threshold: agreement ≥ 90% and AC1 ≥ .67). Hebrew script is assessed as one category (`hebrew` + `hebrew_like`).

Codes used in the analysis: my codes for the 160 validation images; for the other 480, model codes with corrections according to the table above (model codes kept unchanged in separate columns). Second-coder codes serve only for agreement.

## 6. Confirmatory tests

- H1–H3: separately for each system, pooled over languages and scales (80 vs 80), one-sided Fisher's exact test.
- H4: separately for each system, pooled over languages (40 vs 40), same test.
- Holm correction across 8 tests (4 hypotheses × 2 systems). A hypothesis is supported for a system if the Holm-adjusted p < .05 and the direction matches.
- Shares in all 32 conditions are reported with 95% Wilson intervals; results by scale are reported descriptively.

## 7. Denominator, refusals, exclusions

- Denominator: all coded images, including those coded as `illustration`. No image is regenerated or replaced because it failed to resemble Kraków.
- Refusals and content blocks are results: logged with the message and reported per condition, not regenerated, and the prompt is not rephrased. Technical errors (timeout, 5xx, 429): up to 3 retries; corrupt file: 1 retry.
- If refusal rates in 2 compared groups differ by more than 10 percentage points, a conservative variant is also reported in which a refusal counts as an image without the hypothesis indicator.

## 8. Sensitivity and exploratory analyses

- H1, H2, H4 without images whose temporal frame is `indeterminate`.
- H1–H4 without images coded as `illustration`.
- Differences between languages and systems as a robustness table, without separate hypotheses.
- P5 descriptively; a test only if each compared group contains at least 30 images with religious elements.
- Text returned by the Google system alongside the image: per condition, the share of responses with text and, descriptively, whether the text names a religion, a group or a period. The coding model never sees this text.

## 9. Selection of images for publication

Image walls: for each of 8 conditions and each system, the first 8 images by random ID. No other selection.

## 10. Scope of conclusions

Conclusions concern these prompts, these system versions and the period of data collection (October–November 2026), not image generators in general.
