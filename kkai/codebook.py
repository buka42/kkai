"""Codebook rules shared by the AI coder, the human sheets and validation.

Allowed values come from the JSON schema (03b), so the sheet, the model output
and the checks cannot drift apart.
"""

from __future__ import annotations

import json
import random
import re
from functools import lru_cache
from pathlib import Path

import jsonschema

# Human sheet layout (02_kodeks.md, "Arkusz kodowania dla człowieka").
# column -> (path in the schema to the enum, multi-select?)
SHEET_COLUMNS = {
    "medium": (("medium", "value"), False),
    # Control column (kodeks 0.9.1): no agreement reported; with 'none' the roles must be empty.
    "people_count": (("people", "count_band"), False),
    "temporal_frame": (("temporal_frame", "value"), False),
    "contemporary_cue_types": (("temporal_frame", "contemporary_cue_types", "[]"), True),
    "historical_cue_types": (("temporal_frame", "historical_cue_types", "[]"), True),
    "mode_dominant": (("mode_of_culture", "dominant"), False),
    "mode_secondary": (("mode_of_culture", "secondary", "[]"), True),
    "roles": (("figure_roles", "[]", "role"), True),
    "religion_form": (("religion", "form"), False),
    "religion_traditions": (("religion", "traditions_by_object", "[]"), True),
    "scripts": (("script_markers", "[]", "type"), True),
    "place": (("place", "value"), False),
    "landmarks": (("place", "landmarks", "[]"), True),
}
SHEET_FIELDS = ["image_id", *SHEET_COLUMNS, "notes", "coder_id", "coded_at"]
# Variables coded by the optional second coder (protocol: 3 main variables).
SECOND_CODER_COLUMNS = ["temporal_frame", "mode_dominant", "religion_form"]

# Words that must not appear in observations (03_instrukcja_kodera.md, pilot check 3).
IDENTITY_TERMS = ["jewish man", "jewish woman", "jewish people", "jews", "hasid", "hasidic", "orthodox jew",
                  "muslim", "ukrainian", "migrant", "immigrant", "refugee", "tourist from", "arab", "roma",
                  "african", "asian", "skin"]


@lru_cache(maxsize=8)
def load_schema(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _node(schema: dict, path: tuple) -> dict:
    node = schema
    for step in path:
        node = node["items"] if step == "[]" else node["properties"][step]
    return node["items"] if node.get("type") == "array" else node


def allowed_values(schema_doc: dict) -> dict[str, list[str]]:
    s = schema_doc["schema"]
    return {col: list(_node(s, path)["enum"]) for col, (path, _) in SHEET_COLUMNS.items()}


def validate_output(schema_doc: dict, out: dict) -> list[str]:
    """Schema errors plus evidence ids that point to missing observations."""
    errors = [f"schema: {e.message} at {'/'.join(map(str, e.path))}"
              for e in jsonschema.Draft202012Validator(schema_doc["schema"]).iter_errors(out)]
    if errors:
        return errors
    ids = {o["id"] for o in out["observations"]}
    if len(ids) != len(out["observations"]):
        errors.append("evidence: duplicate observation ids")

    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "evidence":
                    for e in v:
                        if e not in ids:
                            errors.append(f"evidence: {where} cites missing observation {e}")
                else:
                    walk(v, f"{where}.{k}" if where else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{where}[{i}]")

    walk({k: v for k, v in out.items() if k != "observations"}, "")
    return errors


def expected_review_reasons(out: dict) -> set[str]:
    """Review reasons that follow mechanically from the codes.

    time_cues_conflict, landmark_uncertain and low_confidence_primary depend on
    judgement and are not recomputed; staged/conflict cues are partly checked.
    """
    r = set()
    if out["religion"]["form"] != "none":
        r.add("religion_present")
    if any(s["type"] != "latin" for s in out["script_markers"]):
        r.add("script_marker")
    if out["temporal_frame"]["value"] == "staged_historical":
        r.add("staged_time")
    roles = {f["role"] for f in out["figure_roles"]}
    if roles & {"performer_or_costumed", "religious_practice"}:
        r.add("performer_or_religious_role")
    dress = {d["item"] for d in out["dress_items"]}
    if dress & {"kippah", "prayer_shawl", "religious_habit", "period_costume"} or \
            {"long_dark_coat", "dark_brimmed_hat"} <= dress:
        r.add("dress_item_flag")
    if out["place"]["value"] == "inconsistent_with_krakow":
        r.add("place_not_consistent")
    tf = out["temporal_frame"]
    hist_strict = [h for h in tf["historical_cue_types"] if h != "aged_photographic_look"]
    if tf["value"] == "indeterminate" and tf["contemporary_cue_types"] and hist_strict:
        r.add("time_cues_conflict")
    return r


def expected_temporal_frame(out: dict) -> str | None:
    """Temporal frame from the cue types by the 4-step rule; None when step 1 needs costume info."""
    tf = out["temporal_frame"]
    contemporary = set(tf["contemporary_cue_types"])
    historical = set(tf["historical_cue_types"])
    if tf["value"] == "staged_historical":
        return None  # costume is not a cue type, cannot be recomputed
    if len(contemporary) >= 2 and not (historical - {"aged_photographic_look"}):
        return "contemporary"
    if not contemporary and historical:
        return "historical"
    return "indeterminate"


def check_flags(out: dict) -> dict:
    """Flags computed by the program; mismatches are marked, the model output is kept."""
    expected = expected_review_reasons(out)
    given = set(out["review_reasons"])
    missing = sorted(expected - given)
    obs_text = " ".join(o["text"] for o in out["observations"]).lower()
    identity = sorted({t for t in IDENTITY_TERMS if re.search(rf"\b{re.escape(t)}\b", obs_text)})
    exp_tf = expected_temporal_frame(out)
    return {
        "flags_missing": ";".join(missing),
        "needs_review_mismatch": bool(given or expected) != bool(out["needs_human_review"]),
        "temporal_rule_mismatch": exp_tf is not None and exp_tf != out["temporal_frame"]["value"],
        "identity_terms": ";".join(identity),
        "needs_review_program": bool(given | expected) or bool(identity),
    }


def _get(out: dict, path: tuple):
    """Values at a sheet path; multi-select paths return a list."""
    vals = [out]
    for step in path:
        nxt = []
        for v in vals:
            if step == "[]":
                nxt.extend(v)
            else:
                nxt.append(v[step])
        vals = nxt
    return vals


def flatten(out: dict) -> dict:
    """Model output as one CSV row: sheet columns (lists joined with ';') plus auxiliary fields."""
    row = {}
    for col, (path, multi) in SHEET_COLUMNS.items():
        vals = _get(out, path)
        row[col] = ";".join(sorted(dict.fromkeys(vals))) if multi else vals[0]
    row.update({
        "dress_items": ";".join(sorted({d["item"] for d in out["dress_items"]})),
        "text_present": out["text_in_image"]["present"],
        "text_garbled": out["text_in_image"]["garbled"],
        "legible_strings": " | ".join(out["text_in_image"]["legible_strings"]),
        "scripts_legible": ";".join(sorted({s["type"] for s in out["script_markers"] if s["legible"]})),
        "tourism_present": out["tourism_consumption"]["present"],
        "tourism_items": ";".join(sorted(set(out["tourism_consumption"]["items"]))),
        "memory_present": out["memory_markers"]["present"],
        "review_reasons": ";".join(sorted(set(out["review_reasons"]))),
        "needs_human_review": out["needs_human_review"],
        "self_reported_confidence": out["self_reported_confidence"],
        "ambiguity_note": out["ambiguity_note"],
        "n_observations": len(out["observations"]),
    })
    return row


def random_output(schema_doc: dict, rng: random.Random) -> dict:
    """Random output that satisfies the schema and cites existing observations (dry-run coder)."""
    n_obs = rng.randint(2, 6)
    obs_ids = [f"o{i}" for i in range(1, n_obs + 1)]

    def gen(node, key=None):
        t = node.get("type")
        if key == "observations":
            return [{"id": i, "text": f"dry-run observation {i}"} for i in obs_ids]
        if key == "evidence":
            return rng.sample(obs_ids, rng.randint(1, min(2, n_obs)))
        if "enum" in node:
            return rng.choice(node["enum"])
        if t == "object":
            return {k: gen(v, k) for k, v in node["properties"].items()}
        if t == "array":
            items = node["items"]
            if "enum" in items:
                return rng.sample(items["enum"], rng.randint(0, min(2, len(items["enum"]))))
            return [gen(items) for _ in range(rng.randint(0, 2))]
        if t == "boolean":
            return rng.random() < 0.5
        if t == "string":
            return "" if key == "ambiguity_note" else "x"
        raise ValueError(f"unsupported schema node {node}")

    out = gen(schema_doc["schema"])
    if out["people"]["count_band"] == "none":
        out["figure_roles"] = []
    # Make the flags consistent, as a well-behaved model would.
    out["review_reasons"] = sorted(expected_review_reasons(out))
    out["needs_human_review"] = bool(out["review_reasons"])
    return out
