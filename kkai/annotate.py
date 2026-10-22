"""Browser coding tool: one image at a time, codes by clicking, answers into a sheet.

`kkai annotate --set pilot --coder-id PB` starts a local server (127.0.0.1 only)
and opens the browser. Each saved image is appended to
data/human/<set>_annotate_<coder>.jsonl (the latest record per image counts,
nothing is overwritten). "Zapisz arkusz" writes a new XLSX in the format of
`kkai sheet`, ready for `kkai ingest`.

Blinding as in the sheets: the page shows only image_id, never the condition,
generator, prompt or model codes.
"""

from __future__ import annotations

import json
import re
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .codebook import SHEET_COLUMNS, allowed_values, expected_temporal_frame, load_schema
from .config import Config
from .sheets import SHEET_SETS, _write_xlsx, sheet_fields, sheet_ids
from .util import KkaiError, append_jsonl, read_jsonl, utc_now

# Labels and short hints in Polish, from 02_kodeks.md 0.9.2.
LABELS = {
    "medium": "Medium",
    "people_count": "Liczba osób",
    "contemporary_cue_types": "Wskaźniki współczesne (typy)",
    "historical_cue_types": "Wskaźniki historyczne (typy)",
    "temporal_frame": "Rama czasowa",
    "mode_dominant": "Tryb kultury: dominujący",
    "mode_secondary": "Tryb kultury: pomocnicze",
    "roles": "Role postaci",
    "religion_form": "Religia: postać (najwyższy widoczny poziom)",
    "religion_traditions": "Religia: tradycja (tylko z przedmiotu lub budynku)",
    "scripts": "Pismo",
    "place": "Miejsce (tylko z zabudowy i krajobrazu)",
    "landmarks": "Zabytki (gdy miejsce = landmark, min. 2 cechy)",
}
HINTS = {
    "photo_colour": "fotografia w naturalnych kolorach",
    "photo_aged": "cz.-b./sepia/jeden ton albo ≥2 cechy postarzenia, w tym ≥1 ślad odbitki (rysy, plamy, zagięcia, pożółkły papier); samo ziarno lub przygaszone kolory to photo_colour",
    "illustration": "widoczne cechy niefotograficzne: pociągnięcia pędzla lub pióra, płaskie plamy, kontury, faktura płótna; gładki obraz = photo_colour",
    "none": "brak",
    "1_5": "1–5 osób",
    "6_20": "6–20 osób",
    "crowd": "tłum, ponad 20",
    "mobile_device": "telefon, tablet, selfie stick",
    "modern_motor_vehicle": "auto, autobus, motocykl z ostatnich dekad",
    "modern_tram": "tramwaj niskopodłogowy lub współczesny",
    "micromobility": "hulajnoga elektryczna, rower miejski",
    "modern_clothing": "puchówka, sportowe buty, czapka z daszkiem, plecak",
    "screen_or_led": "ekran, wyświetlacz, neon LED",
    "modern_signage_or_branding": "współczesne szyldy, logotypy, piktogramy; parasole tylko z nadrukiem (logo, tekst, pseudotekst)",
    "other_contemporary_object": "słuchawki, składany wózek współczesny, kubek na wynos, plastikowa butelka, współczesny statek; inne tylko z opisem",
    "period_clothing_all_figures": "wszystkie postacie w strojach z epoki",
    "period_motor_vehicle": "auto lub autobus sprzed ok. 1970",
    "aged_photographic_look": "medium photo_aged",
    "other_period_object": "inny jednoznacznie dawny, używany (opisz)",
    "contemporary": "krok 2: ≥2 typy współczesne, brak historycznych (poza postarzeniem)",
    "historical": "krok 3: brak współczesnych, ≥1 historyczny",
    "staged_historical": "krok 1: ≥1 postać w kostiumie i ≥1 typ współczesny (pojedynczy element ludowy ani cylinder dorożkarza to nie kostium)",
    "everyday": "zwykłe czynności: dojazd, zakupy, praca, rozmowa",
    "heritage": "tematem zabytek, pomnik; pusta ulica staromiejska. Ludzie na pierwszym planie ≥1/3 kadru → decyduje ich czynność",
    "spectacle": "występ, festiwal, taniec, kostium, inscenizacja",
    "consumption": "restauracje, ogródki, kawiarnie, sklepy, stragany",
    "everyday_activity": "zakupy, praca, obsługa, rozmowa, odpoczynek",
    "sightseeing": "aparat, mapa, przewodnik z grupą, oglądanie",
    "performer_or_costumed": "scena, instrument, taniec, kostium",
    "religious_practice": "modlitwa, obrzęd, procesja",
    "building": "z widocznym symbolem (krzyż, gwiazda, tablice) albo zabytek sakralny z listy (≥2 cechy); sama sylweta = none",
    "symbol_or_object": "gwiazda Dawida, menora, krzyż, kipa, tałes, habit…",
    "practice": "modlitwa, obrzęd, procesja, nabożeństwo",
    "jewish": "żydowska",
    "christian": "chrześcijańska (krzyż łaciński)",
    "christian_orthodox": "prawosławna",
    "muslim": "muzułmańska",
    "latin": "litery łacińskie, także pseudotekst",
    "hebrew": "hebrajski z ≥1 poprawnym słowem",
    "hebrew_like": "znaki podobne do hebrajskich, bez czytelnego słowa",
    "cyrillic": "cyrylica",
    "landmark": "zabytek z listy, min. 2 zgodne cechy",
    "generic_historic_townscape": "zabudowa historyczna bez rozpoznawalnego obiektu",
    "generic_modern_townscape": "współczesna zabudowa bez rozpoznawalnego obiektu",
    "inconsistent_with_krakow": "góry, morze, palmy, architektura spoza Europy",
    "wawel": "Wawel", "cloth_hall": "Sukiennice", "st_marys": "Bazylika Mariacka",
    "town_hall_tower": "Wieża Ratuszowa", "barbican_florian_gate": "Barbakan i Brama Floriańska",
    "sts_peter_paul": "św. Piotra i Pawła", "old_synagogue": "Synagoga Stara", "remuh": "Remuh i cmentarz",
    "tempel": "Synagoga Tempel", "plac_nowy": "Plac Nowy", "szeroka_street": "ul. Szeroka",
    "corpus_christi": "Bożego Ciała", "skalka": "Skałka", "bernatek_footbridge": "Kładka Bernatka",
    "other_krakow_landmark": "inny zabytek Krakowa (nazwa w uwagach)",
    "indeterminate": "nie da się rozstrzygnąć",
    "other": "inne",
}
# Order on the page: cues before the frame, so the step rule can be shown.
UI_ORDER = ["medium", "people_count", "contemporary_cue_types", "historical_cue_types", "temporal_frame",
            "mode_dominant", "mode_secondary", "roles", "religion_form", "religion_traditions", "scripts",
            "place", "landmarks"]


def log_path(cfg: Config, set_name: str, coder_id: str) -> Path:
    return cfg.dir("human") / f"{set_name}_annotate_{coder_id}.jsonl"


class Session:
    """State of one coding session; the HTTP handler only calls these methods."""

    def __init__(self, cfg: Config, set_name: str, coder_id: str):
        if set_name not in SHEET_SETS:
            raise KkaiError(f"Nieznany zbiór {set_name!r}; dozwolone: {', '.join(SHEET_SETS)}")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,20}", coder_id):
            raise KkaiError("coder-id: tylko litery, cyfry, '-' i '_' (np. PB)")
        self.cfg, self.set_name, self.coder_id = cfg, set_name, coder_id
        self.ids = sheet_ids(cfg, set_name)
        self.fields = sheet_fields(set_name)
        self.allowed = allowed_values(load_schema(str(cfg.path(cfg.raw["coder"]["schema"]))))
        self.log = log_path(cfg, set_name, coder_id)
        self.images = {}
        for i in self.ids:
            hits = list((cfg.data_dir / "blinded").glob(f"*/{i}.png"))
            if len(hits) != 1:
                raise KkaiError(f"Nie znajduję pliku {i}.png w blinded/")
            self.images[i] = hits[0]

    def variables(self) -> list[dict]:
        out = []
        for v in UI_ORDER:
            if v not in self.fields:
                continue
            out.append({"name": v, "label": LABELS[v], "multi": SHEET_COLUMNS[v][1],
                        "values": [{"code": c, "hint": HINTS.get(c, "")} for c in self.allowed[v]]})
        return out

    def answers(self) -> dict[str, dict]:
        latest = {}
        if self.log.exists():
            for r in read_jsonl(self.log):
                latest[r["image_id"]] = r
        return latest

    def state(self) -> dict:
        return {"set": self.set_name, "coder_id": self.coder_id, "ids": self.ids,
                "variables": self.variables(), "answers": self.answers()}

    def check(self, rec: dict) -> list[str]:
        errors = []
        for v in self.fields:
            if v not in SHEET_COLUMNS:
                continue
            val = rec.get(v, "")
            if SHEET_COLUMNS[v][1]:
                bad = [c for c in val.split(";") if c and c not in self.allowed[v]]
                if bad:
                    errors.append(f"{LABELS[v]}: niedozwolone {bad}")
            elif not val:
                errors.append(f"{LABELS[v]}: brak wyboru")
            elif val not in self.allowed[v]:
                errors.append(f"{LABELS[v]}: niedozwolone {val!r}")
        if rec.get("people_count") == "none" and rec.get("roles"):
            errors.append("Liczba osób = none, a role nie są puste")
        if rec.get("place") and rec.get("place") != "landmark" and rec.get("landmarks"):
            errors.append("Zabytki zaznaczone, a miejsce ≠ landmark")
        return errors

    def save(self, payload: dict) -> dict:
        iid = payload.get("image_id")
        if iid not in self.images:
            raise KkaiError(f"image_id {iid!r} nie należy do zbioru {self.set_name}")
        rec = {"image_id": iid}
        for v in self.fields:
            if v in SHEET_COLUMNS:
                raw = payload.get(v, "")
                if SHEET_COLUMNS[v][1]:
                    codes = raw if isinstance(raw, list) else [c for c in str(raw).split(";") if c]
                    rec[v] = ";".join(sorted(dict.fromkeys(codes)))
                else:
                    rec[v] = str(raw or "")
        rec["notes"] = str(payload.get("notes", "")).strip()
        errors = self.check(rec)
        if errors:
            return {"ok": False, "errors": errors}
        rec.update(coder_id=self.coder_id, set=self.set_name, coded_at=utc_now(),
                   seconds=payload.get("seconds"))
        append_jsonl(self.log, rec)
        return {"ok": True, "record": rec}

    def export(self) -> Path:
        answers = self.answers()
        stamp = utc_now()[:19].replace(":", "").replace("-", "")
        path = self.cfg.dir("human") / f"{self.set_name}_sheet_{self.coder_id}_{stamp}.xlsx"
        if path.exists():
            raise KkaiError(f"{path.name} już istnieje")
        _write_xlsx(path, self.ids, self.fields, self.allowed, values=answers)
        return path

    def temporal_hint(self, rec: dict) -> str | None:
        """Frame by steps 2–4 of the codebook rule (step 1 needs costume, not a cue type)."""
        out = {"temporal_frame": {"value": "", "contemporary_cue_types": [c for c in rec.get("contemporary_cue_types", []) if c],
                                  "historical_cue_types": [c for c in rec.get("historical_cue_types", []) if c]}}
        return expected_temporal_frame(out)


def _handler(session: Session):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the console quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self._json(session.state())
            elif m := re.fullmatch(r"/img/(img_[0-9a-f]+)\.png", self.path):
                p = session.images.get(m.group(1))
                if p is None:
                    self._send(404, b"not found", "text/plain")
                else:
                    self._send(200, p.read_bytes(), "image/png")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if self.path == "/api/save":
                    self._json(session.save(payload))
                elif self.path == "/api/hint":
                    self._json({"frame": session.temporal_hint(payload)})
                elif self.path == "/api/export":
                    path = session.export()
                    self._json({"ok": True, "path": str(path), "command":
                                f'kkai ingest --sheet "{path}" --set {session.set_name} --coder-id {session.coder_id}'})
                else:
                    self._send(404, b"not found", "text/plain")
            except KkaiError as e:
                self._json({"ok": False, "errors": [str(e)]}, 400)

    return Handler


def serve(session: Session, port: int = 8765, open_browser: bool = True) -> ThreadingHTTPServer:
    for p in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), _handler(session))
            break
        except OSError:
            continue
    else:
        raise KkaiError(f"Porty {port}–{port + 19} są zajęte")
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    done = len(session.answers())
    print(f"Kodowanie {session.set_name} ({len(session.ids)} obrazów, zapisanych {done}), koder {session.coder_id}.")
    print(f"Otwórz {url}  (Ctrl+C kończy; zapisane kody zostają w {session.log.name})")
    if open_browser:
        webbrowser.open(url)
    return server


def run_annotate(cfg: Config, set_name: str, coder_id: str, port: int = 8765) -> None:
    server = serve(Session(cfg, set_name, coder_id), port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nZakończono. Arkusz zapiszesz przyciskiem „Zapisz arkusz” po ponownym uruchomieniu.")
    finally:
        server.server_close()


PAGE = r"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><title>kkai: kodowanie</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root { --bg:#f6f6f4; --panel:#fff; --ink:#1d1d1b; --muted:#6b6b66; --line:#d9d9d4; --accent:#1f5f8b; --accent-ink:#fff; --ok:#2e7d32; --err:#b3261e; }
* { box-sizing: border-box; }
body { margin:0; font:15px/1.4 system-ui, sans-serif; color:var(--ink); background:var(--bg); }
header { display:flex; gap:12px; align-items:center; padding:8px 16px; border-bottom:1px solid var(--line); background:var(--panel); position:sticky; top:0; z-index:2; flex-wrap:wrap; }
header h1 { font-size:16px; margin:0; }
#progress { color:var(--muted); }
#dots { display:flex; flex-wrap:wrap; gap:3px; }
#dots button { width:14px; height:14px; padding:0; border:1px solid var(--line); border-radius:3px; background:#fff; cursor:pointer; }
#dots button.done { background:var(--ok); border-color:var(--ok); }
#dots button.cur { outline:2px solid var(--accent); outline-offset:1px; }
main { display:grid; grid-template-columns: minmax(0, 1.2fr) minmax(360px, 1fr); gap:16px; padding:16px; }
@media (max-width: 900px) { main { grid-template-columns: 1fr; } }
#imgbox { position:sticky; top:64px; align-self:start; }
#imgbox img { width:100%; border:1px solid var(--line); background:#fff; cursor:zoom-in; }
#imgid { font:600 16px monospace; margin-top:6px; }
#form { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px 16px; }
fieldset { border:0; border-bottom:1px solid var(--line); margin:0; padding:10px 0; }
fieldset.disabled { opacity:.4; pointer-events:none; }
legend { font-weight:600; padding:0; margin-bottom:6px; }
.opts { display:flex; flex-wrap:wrap; gap:6px; }
.opt { border:1px solid var(--line); background:#fff; border-radius:6px; padding:4px 8px; cursor:pointer; text-align:left; font:inherit; }
.opt small { display:block; color:var(--muted); font-size:12px; }
.opt.on { background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }
.opt.on small { color:#dbe8f2; }
.multi .opt::before { content:"☐ "; } .multi .opt.on::before { content:"☑ "; }
#hint { font-size:13px; color:var(--accent); margin-top:4px; min-height:1em; }
textarea { width:100%; min-height:60px; font:inherit; }
#bar { display:flex; gap:8px; margin-top:12px; flex-wrap:wrap; align-items:center; }
#bar button { font:inherit; padding:8px 14px; border-radius:6px; border:1px solid var(--line); background:#fff; cursor:pointer; }
#bar button.primary { background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }
#msg { margin-top:8px; }
#msg.err { color:var(--err); } #msg.ok { color:var(--ok); }
</style></head><body>
<header><h1>kkai: kodowanie</h1><span id="progress"></span><div id="dots"></div>
<span style="flex:1"></span><button id="export">Zapisz arkusz</button></header>
<main>
<div id="imgbox"><a id="imglink" target="_blank"><img id="img" alt=""></a><div id="imgid"></div></div>
<div id="form"><div id="fields"></div>
<fieldset><legend>Uwagi (wątpliwości do kodeksu)</legend><textarea id="notes"></textarea></fieldset>
<div id="bar"><button id="prev">← Poprzedni</button><button id="save" class="primary">Zapisz i dalej →</button>
<button id="skip">Pomiń →</button></div><div id="msg"></div></div>
</main>
<script>
let S, idx = 0, cur = {}, t0 = Date.now(), dirty = false;
const $ = id => document.getElementById(id);
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  return r.json();
}
function render() {
  const iid = S.ids[idx], a = S.answers[iid] || {};
  cur = {};
  for (const v of S.variables) cur[v.name] = v.multi ? (a[v.name] ? a[v.name].split(";").filter(Boolean) : []) : (a[v.name] || "");
  $("notes").value = a.notes || "";
  $("img").src = "/img/" + iid + ".png"; $("imglink").href = "/img/" + iid + ".png";
  $("imgid").textContent = iid + (a.coded_at ? "  (zapisany)" : "");
  const box = $("fields"); box.innerHTML = "";
  for (const v of S.variables) {
    const fs = document.createElement("fieldset"); fs.id = "fs_" + v.name;
    fs.innerHTML = "<legend>" + v.label + (v.multi ? " <small>(można kilka; nic = brak)</small>" : "") + "</legend>";
    const opts = document.createElement("div"); opts.className = "opts" + (v.multi ? " multi" : "");
    for (const o of v.values) {
      const b = document.createElement("button"); b.type = "button"; b.className = "opt"; b.dataset.code = o.code;
      b.innerHTML = o.code + (o.hint ? "<small>" + o.hint + "</small>" : "");
      b.onclick = () => { toggle(v, o.code); };
      opts.appendChild(b);
    }
    fs.appendChild(opts);
    if (v.name === "temporal_frame") { const h = document.createElement("div"); h.id = "hint"; fs.appendChild(h); }
    box.appendChild(fs);
  }
  paint(); progress(); t0 = Date.now(); dirty = false; $("msg").textContent = ""; window.scrollTo(0, 0);
}
function toggle(v, code) {
  if (v.multi) { const s = cur[v.name]; const i = s.indexOf(code); i < 0 ? s.push(code) : s.splice(i, 1); }
  else cur[v.name] = cur[v.name] === code ? "" : code;
  if (cur.people_count === "none" && cur.roles) cur.roles = [];
  if (cur.place !== undefined && cur.place !== "landmark" && cur.landmarks) cur.landmarks = [];
  dirty = true; paint();
}
async function paint() {
  for (const v of S.variables) {
    document.querySelectorAll("#fs_" + v.name + " .opt").forEach(b => {
      const on = v.multi ? cur[v.name].includes(b.dataset.code) : cur[v.name] === b.dataset.code;
      b.classList.toggle("on", on);
    });
  }
  const r = $("fs_roles"); if (r) r.classList.toggle("disabled", cur.people_count === "none");
  const l = $("fs_landmarks"); if (l) l.classList.toggle("disabled", cur.place !== "landmark");
  if ($("hint") && cur.contemporary_cue_types !== undefined) {
    const h = await api("/api/hint", {contemporary_cue_types: cur.contemporary_cue_types, historical_cue_types: cur.historical_cue_types});
    $("hint").textContent = h.frame ? "Według kroków 2–4: " + h.frame + " (krok 1, kostium, oceniasz sam)" : "";
  }
}
function progress() {
  const n = S.ids.filter(i => S.answers[i]).length;
  $("progress").textContent = "Obraz " + (idx + 1) + " z " + S.ids.length + " · zapisanych " + n;
  const d = $("dots"); d.innerHTML = "";
  S.ids.forEach((iid, k) => {
    const b = document.createElement("button"); b.title = iid;
    b.className = (S.answers[iid] ? "done" : "") + (k === idx ? " cur" : "");
    b.onclick = () => go(k); d.appendChild(b);
  });
}
function go(k) {
  if (dirty && !confirm("Niezapisane zmiany w tym obrazie przepadną. Przejść dalej?")) return;
  idx = Math.max(0, Math.min(S.ids.length - 1, k)); render();
}
$("prev").onclick = () => go(idx - 1);
$("skip").onclick = () => go(idx + 1);
$("save").onclick = async () => {
  const body = Object.assign({image_id: S.ids[idx], notes: $("notes").value, seconds: Math.round((Date.now() - t0) / 1000)}, cur);
  const r = await api("/api/save", body);
  if (!r.ok) { $("msg").className = "err"; $("msg").innerHTML = r.errors.join("<br>"); $("msg").scrollIntoView(); return; }
  S.answers[S.ids[idx]] = r.record; dirty = false;
  const next = S.ids.findIndex((i, k) => k > idx && !S.answers[i]);
  if (next >= 0) { idx = next; render(); }
  else if (S.ids.every(i => S.answers[i])) { progress(); $("msg").className = "ok"; $("msg").textContent = "Wszystkie obrazy zapisane. Kliknij „Zapisz arkusz”."; }
  else { go(S.ids.findIndex(i => !S.answers[i])); }
};
$("notes").oninput = () => { dirty = true; };
$("export").onclick = async () => {
  const r = await api("/api/export", {});
  $("msg").className = r.ok ? "ok" : "err";
  $("msg").innerHTML = r.ok ? "Zapisano arkusz:<br><code>" + r.path + "</code><br>Wczytaj go poleceniem:<br><code>" + r.command + "</code>" : r.errors.join("<br>");
  $("msg").scrollIntoView();
};
window.onbeforeunload = e => { if (dirty) { e.preventDefault(); return ""; } };
api("/api/state").then(s => { S = s; const f = S.ids.findIndex(i => !S.answers[i]); idx = f < 0 ? 0 : f; render(); });
</script></body></html>
"""
