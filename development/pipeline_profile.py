"""
pipeline_profile.py - Inti DOMAIN konfigurasi bisnis AI-GEMPA (tanpa framework, Python >= 3.8).

Konsep:
  - Artifact : jenis data yang mengalir antar tahap (waveform, pick, cluster, arrival, event).
  - Stage    : tahap pipeline (ingest -> p_pick -> association -> locmag). Setiap tahap punya >= 1 Provider (model/algoritma).
  - Sink     : tujuan keluaran (ws_ui, webhook, kafka_export, archive); memilih artifact apa yang dikonsumsi.
  - Profile  : mode "default" (preset sistem, tanpa override) atau "custom" (tahap/provider/parameter dipilih pengguna).
  - Compile  : profil valid -> rencana routing (topic Kafka tiap tahap), rev (hash), proyeksi ke kunci config lama.
  - Pricing  : pay-per-use dalam IDR; harga per unit inference/processing + free quota per model.

Nilai default parameter di katalog ini adalah CONTOH. Ganti dengan nilai yang berlaku di sistem Anda sekarang.
Harga dalam IDR; kuota gratis per bulan.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

ARTIFACTS = ("waveform", "pick", "cluster", "arrival", "event")
LEGACY_TOPICS = {"waveform": "waveform_seedlink", "pick": "pick_topic", "cluster": "cluster_topic",
                 "arrival": "arrival_pick_topic", "event": "event_topic"}
STAGE_ORDER = ("ingest", "p_pick", "association", "locmag")
STATUS_MIN_PLAN = {"stable": "basic", "beta": "pro", "experimental": "enterprise", "deprecated": "basic"}
LEGACY_PREFIX = {"ingest": "seedlink.", "p_pick": "ai.ppick.", "association": "ai.association.", "locmag": "ai.locmag."}


# ----------------------------------------------------------------------------- katalog
@dataclass(frozen=True)
class ParamSpec:
    type: str                      # number | integer | boolean | string | enum | enum_list
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    values: Tuple[Any, ...] = ()
    required: bool = False


@dataclass(frozen=True)
class Provider:
    id: str
    stage: str
    version: str = "1.0.0"
    status: str = "stable"         # stable | beta | experimental | deprecated
    min_plan: str = "basic"
    params: Dict[str, ParamSpec] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)
    # Pricing info (IDR, pay-per-use)
    price_per_unit: Decimal = Decimal("0")      # IDR per inference/processing
    unit_name: str = "inference"                # "per 1K picks" | "per 1K events" | "per 1K waveforms"
    free_quota_monthly: int = 0                 # Unit gratis per bulan (trial quota)


@dataclass(frozen=True)
class StageSpec:
    id: str
    kind: str                      # source | transform | sink
    requires: Tuple[str, ...] = ()
    produces: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Plan:
    id: str
    rank: int
    custom_allowed: bool
    max_stations: int


PLANS = {"basic": Plan("basic", 0, False, 20), "pro": Plan("pro", 1, True, 100),
         "enterprise": Plan("enterprise", 2, True, 1000)}


class Catalog:
    def __init__(self, stages: List[StageSpec], providers: List[Provider]):
        self.stages = {s.id: s for s in stages}
        self._providers = {(p.stage, p.id): p for p in providers}

    def provider(self, stage: str, pid: str) -> Optional[Provider]:
        return self._providers.get((stage, pid))

    def providers_for(self, stage: str) -> List[Provider]:
        return [p for (s, _), p in self._providers.items() if s == stage]


def _arts(default):
    return ParamSpec("enum_list", default=list(default), values=ARTIFACTS)


def build_default_catalog() -> Catalog:
    stages = [StageSpec("ingest", "source", (), ("waveform",)),
              StageSpec("p_pick", "transform", ("waveform",), ("pick",)),
              StageSpec("association", "transform", ("pick",), ("cluster", "arrival")),
              StageSpec("locmag", "transform", ("cluster", "arrival"), ("event",)),
              StageSpec("ws_ui", "sink"), StageSpec("webhook", "sink"),
              StageSpec("kafka_export", "sink"), StageSpec("archive", "sink")]
    P, S = ParamSpec, Provider
    providers = [
        S("seedlink_v3", "ingest", params={"retry_interval": P("integer", 30, 5, 300),
                                           "buffer_size": P("integer", 1000, 100, 100000)}),
        S("fdsn_poll", "ingest", status="beta", min_plan="pro",
          params={"poll_interval": P("integer", 60, 30, 600), "window": P("integer", 120, 30, 600)}),
        S("push_api", "ingest", params={"max_rate": P("integer", 500, 1, 10000)}),
        S("file_replay", "ingest", params={"speed": P("number", 1.0, 0.1, 60)}),
        S("phasenet", "p_pick", resources={"gpu": "optional"},
          params={"weights": P("enum", "original", values=("original", "instance", "stead")),
                  "p_threshold": P("number", 0.3, 0.05, 0.99), "s_threshold": P("number", 0.3, 0.05, 0.99),
                  "batch_size": P("integer", 32, 1, 256)}),
        S("sta_lta", "p_pick", resources={"gpu": "none"},
          params={"sta": P("number", 0.5, 0.05, 5), "lta": P("number", 10, 2, 60),
                  "on": P("number", 3.5, 1.5, 10), "off": P("number", 1.5, 0.5, 5)}),
        S("eqtransformer", "p_pick", status="beta", min_plan="pro", resources={"gpu": "recommended"},
          params={"p_threshold": P("number", 0.3, 0.05, 0.99), "s_threshold": P("number", 0.3, 0.05, 0.99)}),
        S("dbscan_simple", "association",
          params={"time_threshold": P("number", 10, 1, 60), "distance_threshold": P("number", 300, 10, 3000),
                  "min_picks": P("integer", 4, 3, 50)}),
        S("gamma", "association", status="beta", min_plan="pro",
          params={"min_picks": P("integer", 5, 3, 50), "dbscan_eps": P("number", 10, 1, 60)}),
        S("pyocto", "association", status="experimental", min_plan="enterprise",
          params={"min_picks": P("integer", 5, 3, 50),
                  "velocity_model": P("enum", "iasp91", values=("iasp91", "ak135"))}),
        S("geiger", "locmag",
          params={"velocity_model": P("enum", "iasp91", values=("iasp91", "ak135")),
                  "magnitude_method": P("enum", "ML", values=("ML", "mb")),
                  "max_iterations": P("integer", 20, 5, 100)}),
        S("nonlinloc", "locmag", status="beta", min_plan="pro",
          params={"velocity_model": P("enum", "iasp91", values=("iasp91", "ak135", "custom")),
                  "grid_spacing": P("number", 2.0, 0.5, 20), "magnitude_method": P("enum", "ML", values=("ML", "mb"))}),
        S("ws_ui", "ws_ui", params={"artifacts": _arts(["event"]), "emit_interval": P("integer", 500, 0, 5000)}),
        S("webhook", "webhook", min_plan="pro",
          params={"url": P("string", required=True), "timeout": P("integer", 10, 1, 60), "artifacts": _arts(["event"])}),
        S("kafka_export", "kafka_export", min_plan="pro",
          params={"topic_prefix": P("string", "export"), "artifacts": _arts(["event"])}),
        S("archive", "archive", params={"artifacts": _arts(["waveform"]), "retention_days": P("integer", 30, 1, 3650)}),
    ]
    return Catalog(stages, providers)


# ----------------------------------------------------------------------------- profil
@dataclass
class StageCfg:
    enabled: bool = True
    provider: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Profile:
    mode: str                                   # default | custom | preset
    name: str = ""
    preset: str = "default@1"
    stages: Dict[str, StageCfg] = field(default_factory=dict)
    sinks: Dict[str, StageCfg] = field(default_factory=dict)
    external_inputs: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Profile":
        mk = lambda m: {k: StageCfg(v.get("enabled", True), v.get("provider", k if k in ("ws_ui", "webhook", "kafka_export", "archive") else ""),
                                    dict(v.get("params", {}))) for k, v in (m or {}).items()}
        return Profile(d.get("mode", ""), d.get("name", ""), d.get("preset", "default@1"),
                       mk(d.get("stages")), mk(d.get("sinks")), list(d.get("external_inputs", [])))


def _default_preset() -> Profile:
    return Profile("preset", "default@1", "default@1",
                   {"ingest": StageCfg(True, "seedlink_v3"), "p_pick": StageCfg(True, "phasenet"),
                    "association": StageCfg(True, "dbscan_simple"), "locmag": StageCfg(True, "geiger")},
                   {"ws_ui": StageCfg(True, "ws_ui"), "archive": StageCfg(True, "archive")})


PRESETS = {"default@1": _default_preset()}


@dataclass
class Issue:
    code: str
    severity: str      # error | warning
    path: str
    message: str


# ----------------------------------------------------------------------------- validasi
def _check_param(name: str, spec: ParamSpec, v: Any, path: str) -> Optional[Issue]:
    bad = lambda msg: Issue("V003", "error", path, f"parameter '{name}': {msg}")
    t = spec.type
    if t in ("number", "integer"):
        ok = isinstance(v, (int, float)) and not isinstance(v, bool) and (t == "number" or isinstance(v, int))
        if not ok:
            return bad(f"harus bertipe {t}")
        if spec.min is not None and v < spec.min or spec.max is not None and v > spec.max:
            return bad(f"di luar rentang {spec.min}..{spec.max}")
    elif t == "boolean" and not isinstance(v, bool):
        return bad("harus boolean")
    elif t == "string" and not isinstance(v, str):
        return bad("harus string")
    elif t == "enum" and v not in spec.values:
        return bad(f"harus salah satu dari {list(spec.values)}")
    elif t == "enum_list" and not (isinstance(v, list) and v and all(x in spec.values for x in v)):
        return bad(f"harus daftar tak kosong berisi {list(spec.values)}")
    return None


def fill_defaults(cfg: StageCfg, prov: Provider) -> Dict[str, Any]:
    out = {k: s.default for k, s in prov.params.items() if s.default is not None}
    out.update(cfg.params)
    return out


def resolve(profile: Profile, presets: Dict[str, Profile] = PRESETS) -> Profile:
    """Default -> salinan preset (override DIABAIKAN). Custom -> apa adanya (tahap yang tidak ditulis = nonaktif)."""
    if profile.mode == "default":
        r = copy.deepcopy(presets[profile.preset])
        r.mode, r.name = "default", profile.name or r.name
        return r
    return copy.deepcopy(profile)


def _plan_ok(prov: Provider, plan: Plan) -> bool:
    need = max(PLANS[prov.min_plan].rank, PLANS[STATUS_MIN_PLAN[prov.status]].rank)
    return plan.rank >= need


def validate(profile: Profile, catalog: Catalog, plan: Plan, presets: Dict[str, Profile] = PRESETS) -> List[Issue]:
    iss: List[Issue] = []
    if profile.mode not in ("default", "custom"):
        return [Issue("V000", "error", "mode", "mode harus 'default' atau 'custom'")]
    if profile.mode == "default" and (profile.stages or profile.sinks or profile.external_inputs):
        iss.append(Issue("V010", "error", "mode", "mode default tidak boleh membawa override tahap/sink/input eksternal"))
    if profile.mode == "custom" and not plan.custom_allowed:
        iss.append(Issue("V009", "error", "mode", f"paket '{plan.id}' tidak mengizinkan mode custom"))
    if profile.preset not in presets:
        return iss + [Issue("V012", "error", "preset", f"preset '{profile.preset}' tidak ada")]
    r = resolve(profile, presets)

    for x in r.external_inputs:
        if x not in ARTIFACTS:
            iss.append(Issue("V013", "error", f"external_inputs.{x}", "artifact tidak dikenal"))

    def check(group: str, items: Dict[str, StageCfg], want_sink: bool):
        for sid, cfg in items.items():
            path = f"{group}.{sid}"
            spec = catalog.stages.get(sid)
            if spec is None or (spec.kind == "sink") != want_sink:
                iss.append(Issue("V001", "error", path, "tahap/sink tidak dikenal"))
                continue
            if not cfg.enabled:
                continue
            prov = catalog.provider(sid, cfg.provider)
            if prov is None:
                iss.append(Issue("V002", "error", path, f"provider '{cfg.provider}' tidak ada untuk '{sid}'"))
                continue
            if not _plan_ok(prov, plan):
                iss.append(Issue("V008", "error", path, f"provider '{prov.id}' ({prov.status}, min paket {prov.min_plan}) "
                                                        f"tidak tersedia di paket '{plan.id}'"))
            for k, v in cfg.params.items():
                if k not in prov.params:
                    iss.append(Issue("V003", "error", f"{path}.params", f"parameter '{k}' tidak dikenal"))
                else:
                    i = _check_param(k, prov.params[k], v, f"{path}.params.{k}")
                    if i:
                        iss.append(i)
            for k, s in prov.params.items():
                if s.required and k not in cfg.params and s.default is None:
                    iss.append(Issue("V003", "error", f"{path}.params.{k}", f"parameter wajib '{k}' belum diisi"))

    check("stages", r.stages, False)
    check("sinks", r.sinks, True)

    enabled = {s: c for s, c in r.stages.items() if c.enabled and s in catalog.stages}
    available = set(r.external_inputs)
    for s in enabled:
        available |= set(catalog.stages[s].produces)
    if not any(catalog.stages[s].kind == "source" for s in enabled) and not r.external_inputs:
        iss.append(Issue("V005", "error", "stages", "tidak ada sumber data: aktifkan 'ingest' atau isi external_inputs"))
    for s in enabled:
        miss = [a for a in catalog.stages[s].requires if a not in available]
        if miss:
            iss.append(Issue("V004", "error", f"stages.{s}", f"membutuhkan {miss} tetapi tidak ada tahap hulu/input eksternal"))
    for a in set(r.external_inputs) & {a for s in enabled for a in catalog.stages[s].produces}:
        iss.append(Issue("W003", "warning", f"external_inputs.{a}", f"'{a}' dihasilkan tahap internal DAN input eksternal (data tercampur)"))

    sinks = {s: c for s, c in r.sinks.items() if c.enabled and s in catalog.stages}
    if not sinks:
        iss.append(Issue("V006", "error", "sinks", "minimal satu sink harus aktif"))
    consumed = set()
    for sid, cfg in sinks.items():
        prov = catalog.provider(sid, cfg.provider)
        arts = cfg.params.get("artifacts") or (prov.params["artifacts"].default if prov else [])
        for a in arts:
            if a in ARTIFACTS and a not in available:
                iss.append(Issue("V007", "error", f"sinks.{sid}", f"sink meminta '{a}' yang tidak dihasilkan pipeline"))
            consumed.add(a)
    for s in enabled:
        for a in catalog.stages[s].requires:
            consumed.add(a)
    for s in enabled:
        for a in catalog.stages[s].produces:
            if a not in consumed:
                iss.append(Issue("W001", "warning", f"stages.{s}", f"keluaran '{a}' tidak dipakai tahap/sink mana pun (boros sumber daya)"))
    return iss


# ----------------------------------------------------------------------------- kompilasi
def topic_for(workspace: str, artifact: str) -> str:
    return LEGACY_TOPICS[artifact] if workspace == "default" else f"{workspace}.{artifact}"


def compile_pipeline(profile: Profile, catalog: Catalog, plan: Plan, workspace: str = "default",
                     presets: Dict[str, Profile] = PRESETS) -> Dict[str, Any]:
    issues = validate(profile, catalog, plan, presets)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        return {"ok": False, "issues": [i.__dict__ for i in issues]}
    r = resolve(profile, presets)
    stages = []
    for sid in STAGE_ORDER:
        cfg = r.stages.get(sid)
        if not cfg or not cfg.enabled:
            continue
        prov, spec = catalog.provider(sid, cfg.provider), catalog.stages[sid]
        stages.append({"stage": sid, "provider": prov.id, "version": prov.version,
                       "params": fill_defaults(cfg, prov),
                       "consume": [topic_for(workspace, a) for a in spec.requires],
                       "produce": [topic_for(workspace, a) for a in spec.produces],
                       "consumer_group": f"{workspace}.{sid}"})
    sinks = []
    for sid in sorted(k for k, c in r.sinks.items() if c.enabled):
        cfg = r.sinks[sid]
        prov = catalog.provider(sid, cfg.provider)
        params = fill_defaults(cfg, prov)
        sinks.append({"sink": sid, "params": params, "consume": [topic_for(workspace, a) for a in params["artifacts"]],
                      "consumer_group": f"{workspace}.sink.{sid}"})
    body = {"workspace": workspace, "mode": profile.mode, "stages": stages, "sinks": sinks,
            "external_inputs": sorted(r.external_inputs)}
    rev = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]
    used = sorted({t for x in stages + sinks for t in x.get("consume", []) + x.get("produce", [])})
    return {"ok": True, "rev": rev, **body, "topics": used,
            "warnings": [i.__dict__ for i in issues if i.severity == "warning"]}


def to_legacy_keys(compiled: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Proyeksi ke format tabel config lama {name, config, type} agar modul lama tetap bisa membaca (strangler)."""
    out = []
    for st in compiled["stages"]:
        pre = LEGACY_PREFIX[st["stage"]]
        typ = "module" if st["stage"] == "ingest" else "ai"
        out.append({"name": pre + "enabled", "config": True, "type": typ})
        out.append({"name": pre + "provider", "config": st["provider"], "type": typ})
        for k, v in st["params"].items():
            out.append({"name": pre + k, "config": v, "type": typ})
    for sid in STAGE_ORDER:
        if sid not in {s["stage"] for s in compiled["stages"]}:
            out.append({"name": LEGACY_PREFIX[sid] + "enabled", "config": False,
                        "type": "module" if sid == "ingest" else "ai"})
    out.append({"name": "pipeline.rev", "config": compiled["rev"], "type": "system"})
    return out


if __name__ == "__main__":
    cat = build_default_catalog()
    d = compile_pipeline(Profile("default"), cat, PLANS["basic"])
    print("DEFAULT rev", d["rev"], [s["stage"] for s in d["stages"]], d["topics"])
    c = compile_pipeline(Profile.from_dict({
        "mode": "custom", "name": "p-pick saja",
        "stages": {"ingest": {"provider": "seedlink_v3"}, "p_pick": {"provider": "sta_lta", "params": {"on": 4.0}}},
        "sinks": {"webhook": {"params": {"url": "https://example.com/hook", "artifacts": ["pick"]}}}}),
        cat, PLANS["pro"], workspace="acme")
    print("CUSTOM ok", c["ok"], "rev", c.get("rev"), [s["stage"] for s in c.get("stages", [])], c.get("topics"))
