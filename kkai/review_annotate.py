"""Browser review after gate 3: one image at a time, model codes pre-selected, corrections by clicking.

`kkai review --annotate --coder-id PB` starts a local server (127.0.0.1 only)
with the images of the review plan (the same plan as `kkai review`). For each
image the page shows only the variables to review, pre-selected with the model
code, and the variables to code by hand (gate 3: manual_all), left empty.
Each saved image is appended to data/human/review_annotate_<coder>.jsonl (the
latest record per image counts, nothing is overwritten). "Zapisz arkusz" writes
a new review sheet, ready for `kkai review --ingest`.

Blinding as in the review sheet: model codes and flags are shown, never the
condition, generator or prompt.
"""

from __future__ import annotations

import re
from pathlib import Path

from .annotate import HINTS, LABELS, PAGE, UI_ORDER, Session, serve
from .codebook import SHEET_COLUMNS, allowed_values, load_schema
from .config import Config
from .review import AUX, _reasons, plan_variables, review_plan, write_review_sheet
from .util import KkaiError, append_jsonl, read_jsonl, utc_now


class ReviewSession(Session):
    """Same HTTP interface as annotate.Session, over the review plan."""

    def __init__(self, cfg: Config, coder_id: str):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,20}", coder_id):
            raise KkaiError("coder-id: tylko litery, cyfry, '-' i '_' (np. PB)")
        self.cfg, self.set_name, self.coder_id = cfg, "review", coder_id
        self.plan = {p["image_id"]: p for p in review_plan(cfg)}
        if not self.plan:
            raise KkaiError("Plan przeglądu jest pusty: żadna zmienna nie wymaga przeglądu.")
        self.ids = list(self.plan)
        self.fields = plan_variables(list(self.plan.values()))
        self.allowed = allowed_values(load_schema(str(cfg.path(cfg.raw["coder"]["schema"]))))
        self.log = cfg.dir("human") / f"review_annotate_{coder_id}.jsonl"
        self.images = {}
        for i in self.ids:
            hits = list((cfg.data_dir / "blinded").glob(f"*/{i}.png"))
            if len(hits) != 1:
                raise KkaiError(f"Nie znajduję pliku {i}.png w blinded/")
            self.images[i] = hits[0]

    def variables(self) -> list[dict]:
        return [{"name": v, "label": LABELS[v], "multi": SHEET_COLUMNS[v][1],
                 "values": [{"code": c, "hint": HINTS.get(c, "")} for c in self.allowed[v]]}
                for v in UI_ORDER if v in self.fields]

    def items(self) -> dict[str, dict]:
        # Model codes of every shown variable, plus those the consistency rules and the frame hint read,
        # so the page works with the effective code also where a variable is not reviewed.
        shown = set(self.fields) | {"people_count", "place", "contemporary_cue_types", "historical_cue_types"}
        out = {}
        for iid, p in self.plan.items():
            m = p["model"]
            out[iid] = {"review": p["review"], "manual": p["manual"],
                        "model": {v: ("" if v in p["manual"] else m.get(v, "")) for v in sorted(shown)},
                        "reasons": _reasons(m),
                        "aux": {a: m.get(a, "") for a in AUX} if p["flagged"] else {}}
        return out

    def state(self) -> dict:
        return {"set": self.set_name, "coder_id": self.coder_id, "ids": self.ids, "review_mode": True,
                "multi": {v: multi for v, (_, multi) in SHEET_COLUMNS.items()},
                "variables": self.variables(), "items": self.items(), "answers": self.answers()}

    def save(self, payload: dict) -> dict:
        iid = payload.get("image_id")
        p = self.plan.get(iid)
        if p is None:
            raise KkaiError(f"image_id {iid!r} nie należy do przeglądu")
        rec, errors = {"image_id": iid}, []
        for v in p["review"] + p["manual"]:
            raw = payload.get(v, "")
            if SHEET_COLUMNS[v][1]:
                codes = raw if isinstance(raw, list) else [c for c in str(raw).split(";") if c]
                bad = [c for c in codes if c not in self.allowed[v]]
                rec[v] = ";".join(sorted(dict.fromkeys(codes)))
            else:
                rec[v] = str(raw or "")
                bad = [rec[v]] if rec[v] and rec[v] not in self.allowed[v] else []
                if not rec[v]:
                    errors.append(f"{LABELS[v]}: brak wyboru")
            if bad:
                errors.append(f"{LABELS[v]}: niedozwolone {bad}")
        m = p["model"]
        people = rec.get("people_count", m.get("people_count", ""))
        if people == "none" and rec.get("roles"):
            errors.append("Liczba osób = none, a role nie są puste")
        place = rec.get("place", m.get("place", ""))
        if place and place != "landmark" and rec.get("landmarks"):
            errors.append("Zabytki zaznaczone, a miejsce ≠ landmark")
        if errors:
            return {"ok": False, "errors": errors}
        rec.update(comment=str(payload.get("notes", "")).strip(), coder_id=self.coder_id, set=self.set_name,
                   coded_at=utc_now(), seconds=payload.get("seconds"))
        append_jsonl(self.log, rec)
        return {"ok": True, "record": rec}

    def answers(self) -> dict[str, dict]:
        latest = {}
        if self.log.exists():
            for r in read_jsonl(self.log):
                r.setdefault("notes", r.get("comment", ""))
                latest[r["image_id"]] = r
        return latest

    def export(self) -> Path:
        answers = self.answers()
        missing = [i for i in self.ids if i not in answers]
        if missing:
            raise KkaiError(f"Brakuje {len(missing)} z {len(self.ids)} obrazów (pierwszy: {missing[0]}). "
                            "Arkusz zapiszesz po przejrzeniu wszystkich; zapisane kody są w "
                            f"{self.log.name}.")
        stamp = utc_now()[:19].replace(":", "").replace("-", "")
        path = self.cfg.dir("human") / f"review_sheet_{self.coder_id}_{stamp}.xlsx"
        if path.exists():
            raise KkaiError(f"{path.name} już istnieje")
        write_review_sheet(path, list(self.plan.values()), self.fields, answers)
        return path

    def ingest_command(self, path: Path) -> str:
        return f'kkai review --ingest "{path}"'


def run_review_annotate(cfg: Config, coder_id: str, port: int = 8765) -> None:
    server = serve(ReviewSession(cfg, coder_id), port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nZakończono. Arkusz zapiszesz przyciskiem „Zapisz arkusz” po ponownym uruchomieniu.")
    finally:
        server.server_close()


# The annotate page, with a review layer: per image only its variables, model codes pre-selected.
_REVIEW_JS = r"""
function reviewSetup() {
  if (!S.review_mode) return;
  document.querySelector("header h1").textContent = "kkai: przegląd";
  document.title = "kkai: przegląd";
  const info = document.createElement("div"); info.id = "revinfo"; $("imgbox").appendChild(info);
}
function reviewRender(iid) {
  if (!S.review_mode) return;
  const it = S.items[iid], a = S.answers[iid];
  const split = x => (x || "").split(";").filter(Boolean);
  for (const [k, m] of Object.entries(it.model)) {
    const inPlan = it.review.includes(k) || it.manual.includes(k);
    if (inPlan && a) continue;  // saved answer, already loaded by render()
    cur[k] = S.multi[k] ? split(m) : m;
  }
  // Same consistency rules as in annotate; the field is disabled, so a model code against them is cleared.
  if (cur.people_count === "none" && cur.roles) cur.roles = [];
  if (cur.place !== "landmark" && cur.landmarks) cur.landmarks = [];
  for (const v of S.variables) {
    const fs = $("fs_" + v.name), inPlan = it.review.includes(v.name) || it.manual.includes(v.name);
    fs.style.display = inPlan ? "" : "none";
    if (!inPlan) continue;
    const tag = document.createElement("small"); tag.className = "revtag";
    if (it.manual.includes(v.name)) tag.textContent = " kodujesz ręcznie";
    else { tag.textContent = " model: " + (it.model[v.name] || "brak"); tag.dataset.model = it.model[v.name] || ""; }
    fs.querySelector("legend").appendChild(tag);
  }
  const aux = Object.entries(it.aux).filter(([k, x]) => x).map(([k, x]) => k + ": " + x).join("<br>");
  $("revinfo").innerHTML = (it.reasons ? "<p><b>Flagi:</b> " + it.reasons + "</p>" : "") + (aux ? "<p>" + aux + "</p>" : "");
}
function reviewPaint() {
  if (!S.review_mode) return;
  for (const v of S.variables) {
    const tag = document.querySelector("#fs_" + v.name + " .revtag");
    if (!tag || tag.dataset.model === undefined) continue;
    const now = v.multi ? [...cur[v.name]].sort().join(";") : cur[v.name];
    tag.classList.toggle("changed", now !== tag.dataset.model);
  }
}
"""

REVIEW_PAGE = (PAGE
    .replace("#hint {", ".revtag { font-weight:400; color:var(--muted); } .revtag.changed { color:var(--err); font-weight:600; }\n"
             ".revtag.changed::after { content:\" → zmienione\"; }\n#revinfo { font-size:13px; color:var(--muted); margin-top:6px; }\n#hint {")
    .replace("<legend>Uwagi (wątpliwości do kodeksu)</legend>", "<legend>Uwagi</legend>")
    .replace("<script>\n", "<script>\n" + _REVIEW_JS)
    .replace("  paint(); progress(); t0 = Date.now();", "  reviewRender(iid); paint(); progress(); t0 = Date.now();")
    .replace("  const r = $(\"fs_roles\");", "  reviewPaint();\n  const r = $(\"fs_roles\");")
    .replace("api(\"/api/state\").then(s => { S = s;", "api(\"/api/state\").then(s => { S = s; reviewSetup();"))
for _needle in ("reviewRender(iid)", "reviewPaint();", "reviewSetup();", ".revtag {", "<legend>Uwagi</legend>"):
    assert _needle in REVIEW_PAGE, _needle  # the annotate page changed: update the replacements above
ReviewSession.page = REVIEW_PAGE
