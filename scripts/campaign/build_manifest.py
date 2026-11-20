#!/usr/bin/env python3
"""Generate scripts/campaign/manifest.yaml -- every job that regenerates a computed result of
the TCPMT paper: command, environment, dependencies, outputs, validation, resources, cost.

    python scripts/campaign/build_manifest.py [--design m36] [--campaign NAME] [--out PATH]

COSTS are evidence, not guesses, wherever the artifact exists: each ETM job is costed from
the frozen case file it regenerates (et_wall_s + mechanics.wall_s [+ local.wall_s]; the
feedback jobs from the wall_s of every review_variants/*_itN.json pass), or from a named
analog for a job that has no frozen artifact yet; post-processing and the other solver
families from the production logs (see `EVIDENCE` per job). The frozen runs used 2 threads
per CalculiX solve on a host loaded to ~85 of 96 cores, so the estimates are conservative;
the round-3 meshes (36 cells, four mixed tiers) are smaller than the 49-cell ones.

DESIGN POINT (TCPMT round 3). The campaign runs THE design record (configs/design_points.yaml,
scripts/phase0nw/design_record.py): `--design` names its production entry (m36: M = 36,
N3K3K_A2, EPC2014C/EPC2055, 805 kHz, rated 0603 flying capacitors, four mixed tiers). Every
job exports HVR_DESIGN. The other entries run THROUGH THE SAME CHAIN in design SUBROOTS
(<root>/designs/<key>, own scratch; the runner sets ETM_RESULTS_ROOT/HVR_SCRATCH/HVR_DESIGN for
a job carrying `design: <key>`): the 5-tier co-design comparison m36t5 (Z1/Z2/Z3 x A/B), the
thin-capacitor sensitivity m36thin (Z1/Z2/Z3 x A/B) and the count neighbours m25 and m49
(Z1 x A/B) that confirm the screen's ranking; each design closes its own package network,
synthesizes its own decoupling (k_eq) and runs its production state.

PRODUCTION STATE = the implemented input decoupling (HV_SDEC, tcpmt_cases); S0 and S1 are
references. Z3 runs ONLY on the coupled land-side bases (z3_land_t40_{A,B}_fvmap); the
superseded uncoupled bases (z3_top_only, z3_plate_tim, the plain production-boundary Z3
cases) are gone from the manifest. The production k the package network is closed at is the
committed one (the design record's `decoupling` block, configs/design_points.yaml, from
research/tcpmt_revision/decoupling_by_design.json); the campaign's own decoupling chain
re-derives it and derived.k_check records the difference. If no legal BGA count closes the
production state, the network is built at the declared fallback count and flagged NOT_CLOSED
(final_closure_pkg_network.FALLBACK_RULE). Review round 3: at most 220 balls per rail;
derived.bga_reclose re-closes at the k the campaign's chain derived and judges the worse of the
DC peak x k_eq rule and Z1's worst-ball RMS of the port model (both recorded); the feasibility
stage reads the 1.5-A per-ball target per TCPMT_BGA_POLICY ('requirement' by default, 'hard' a
filter; both policies' verdicts are stored).
Paths in `outputs` are relative to the campaign results root (= the stand-in for research/);
`@fields/` is $HVR_FIELDS of the campaign.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FROZEN = REPO / "research"
PY = "{python}"

# ============================================================================ design points
#: design record entries the campaign runs: key -> integrations x coolings, role
DESIGNS = {
    "m36": dict(label="M = 36, N3K3K_A2, EPC2014C/EPC2055, 805 kHz, rated 0603, 4 mixed tiers "
                      "(production design record entry)",
                archs=("Z1", "Z2", "Z3"), role="production"),
}
ALTERNATES = {
    "m36t5": dict(archs=("Z1", "Z2", "Z3"), stage="co_design",
                  role="5-tier co-design comparison (N4K4K_A2, 957 kHz, 3.73 mm)"),
    "m36thin": dict(archs=("Z1", "Z2", "Z3"), stage="thin_cap",
                    role="thin-capacitor sensitivity (former case A0: m36 at a 100-um capacitor)"),
    "m25": dict(archs=("Z1",), stage="count_study",
                role="count neighbour M = 25 (screen ranking check)"),
    "m49": dict(archs=("Z1",), stage="count_study",
                role="count neighbour M = 49 (screen ranking check)"),
}

# ============================================================================ stages
STAGES = [
    ("prep", "regenerable inputs of the solver chain (network, attach lattices, Z3 land-side "
             "sheets, tier order, converter cards, rules)"),
    ("production", "the production state (implemented decoupling) and the S0/S1 references, "
                   "Z1/Z2/Z3 x cooling A/B (r21), the converged fields and the local chain"),
    ("z3_landside", "Z3 land-side spreading sensitivities on the coupled basis, report"),
    ("interface_feedback", "TIM-warpage interface feedback, Z1/Z2/Z3 x cooling A/B"),
    ("hotspots", "non-uniform die power map, Z1/Z2/Z3 x cooling A/B"),
    ("count_study", "count neighbours M = 25 and 49 through the chain (Z1 x A/B)"),
    ("thin_cap", "thin-capacitor sensitivity (m36 with a 100-um capacitor), Z1/Z2/Z3 x A/B"),
    ("co_design", "the 5-tier co-design comparison design, Z1/Z2/Z3 x A/B"),
    ("refinement_ladders", "nested mesh ladders r11/r12/r31 around production r21"),
    ("robustness_map", "class-B sensitivity set behind the robustness map + local responses"),
    ("solder_submodels", "local viscoplastic solder studies (constitutive, band, cycles, ...)"),
    ("moose_checks", "matched MOOSE references: thermal columns, package RDL, full package"),
    ("dse_sweeps", "regulator-count design-space sweeps and their summaries"),
    ("derived", "post-processing of solver results into the paper's artifacts"),
    ("manuscript", "macros, tables and figures, written under the campaign root"),
]
STAGE_RANK = {s: i for i, (s, _) in enumerate(STAGES)}

ENV_GLOBAL = {
    "OPENBLAS_NUM_THREADS": 1, "MKL_NUM_THREADS": 1, "PYTHONDONTWRITEBYTECODE": 1,
    "SOURCE_DATE_EPOCH": 1793000000, "FORCE_SOURCE_DATE": 1,
    # amendment 5/6 of the local mesh policy: the fixed 59-um averaging band (production)
    "JOINT_BAND_FRAC": "0.16666666666666666",
}

ARCHS = ("Z1", "Z2", "Z3")
TIERS = ("A", "B")
#: input states (tcpmt_cases): the production state and the references
STATES = {"SDEC": "HV_SDEC", "S0": "HV_S0", "S1": "HV_S1"}
#: cooling tier -> base variant (None = the chain's production boundary): tcpmt_cases.
#: COOLING_BASE. Z3 is ALWAYS the coupled land-side case.
Z3_LAND = {"A": "z3_land_t40_A_fvmap", "B": "z3_land_t40_B_fvmap"}
TIER_BASE = {("Z1", "A"): None, ("Z2", "A"): None, ("Z3", "A"): Z3_LAND["A"],
             ("Z1", "B"): "z1_bottom_plate_tim", ("Z2", "B"): "z2_cooled_tim",
             ("Z3", "B"): Z3_LAND["B"]}


def _json(rel):
    f = FROZEN / rel
    try:
        return json.loads(f.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def etm_wall_s(rel, local=True):
    """(seconds, evidence) of one frozen ETM case file: E-T + mechanics (+ local)."""
    c = _json(rel)
    if not c:
        return None, None
    et = c.get("et_wall_s") or (c.get("thermal") or {}).get("wall_s") or 0.0
    me = (c.get("mechanics") or {}).get("wall_s") or 0.0
    lo = (c.get("local") or {}).get("wall_s") or 0.0 if local else 0.0
    if c.get("variant", {}).get("kind") == "mech":
        et = 0.0                                  # mechanics-only: E-T copied from production
    ev = f"{rel}: et {et:.0f} s + mech {me:.0f} s" + (f" + local {lo:.0f} s" if lo else "") + \
        f" ({c.get('threads') or 2} thr, {(c.get('thermal') or {}).get('n_elems', '?')} el)"
    return et + me + lo, ev


def feedback_wall_s(arch, tier):
    tot, n = 0.0, 0
    for it in range(1, 6):
        c = _json(f"tcpmt_revision/review_variants/etm_{arch}_HV_S0__tim_warp_fb_{tier}_it{it}.json")
        if c:
            tot += c.get("wall_s") or ((c.get("et_wall_s") or 0) +
                                       (c.get("mechanics") or {}).get("wall_s", 0))
            n += 1
    return (tot, f"review_variants {arch} {tier}: {n} passes, {tot:.0f} s") if n else (None, None)


def mem_for(n_elems_k):
    """Requested memory (GB) of an ETM job from its element count (thousands): the measured
    max RSS per element of the smoke tests x 2.5 (structural fill-in grows faster than the
    element count), at least 6 GB: r11 6 GB, r21 9 GB, r31 19 GB."""
    return max(6, int(math.ceil(MEM_GB_PER_KEL * n_elems_k * 2.5)))


#: max RSS per 1000 elements of an ETM job (python + ccx): the 2026-11-18 smoke tests,
#: 833 MB (Z1 r11, 36,128 el, local) and 832 MB (Z2 r11, 36,280 el, califone)
MEM_GB_PER_KEL = 0.023


def walltime(est_h, factor=2.5, floor=1.0):
    return float(min(96.0, max(floor, math.ceil((est_h * factor + 0.5) * 2) / 2)))


# ============================================================================ job builder
JOBS: list = []


def job(id, stage, argv, outputs, *, deps=(), env=None, validate=None, ncpus=1, mem_gb=4,
        est_h=0.05, evidence="", walltime_h=None, backends=("local", "pbs"), prefer="any",
        workers=1, cwd=".", blocked=None, notes=None, design=None):
    if prefer == "any" and est_h < 0.25:
        prefer = "local"                  # short jobs do not spend one of the 8 califone slots
    j = {"id": id, "stage": stage, "argv": list(argv), "outputs": list(outputs),
         "deps": list(deps), "ncpus": int(ncpus), "mem_gb": float(mem_gb),
         "est_wall_h": round(float(est_h), 3),
         "walltime_h": walltime_h if walltime_h is not None else walltime(est_h),
         "backends": list(backends), "prefer": prefer}
    if env:
        j["env"] = {k: str(v) for k, v in env.items()}
    if validate:
        j["validate"] = validate
    if workers != 1:
        j["workers"] = workers
    if cwd != ".":
        j["cwd"] = cwd
    if evidence:
        j["evidence"] = evidence
    if blocked:
        j["blocked"] = blocked
    if notes:
        j["notes"] = notes
    if design:
        j["design"] = design             # runs in the design subroot (run.py job_env)
    JOBS.append(j)
    return id


def etm_job(id, stage, argv, out, *, deps=(), analog=None, n_el_k=145, ncpus=2, env=None,
            mechanics=True, local=False, kind="etm", blocked=None, extra_outputs=(),
            speed=1.0, notes=None, est_fallback_h=1.8, design=None):
    s, ev = etm_wall_s(out)
    if s is None and analog:
        s, ev = etm_wall_s(analog)
        ev = f"analog {ev}" if ev else None
    est = (s / 3600.0 * speed) if s else est_fallback_h
    v = [{"file": out, "kind": kind}]
    if kind == "etm":
        v[0].update({"mechanics": mechanics, **({"local": True} if local else {})})
    return job(id, stage, argv, [out, *extra_outputs], deps=deps,
               env={"FC_THREADS": ncpus, "FC_POOL_MAX": 1, **(env or {})}, validate=v,
               ncpus=ncpus, mem_gb=mem_for(n_el_k), est_h=est, evidence=ev or "no evidence",
               blocked=blocked, notes=notes, design=design)


def post(id, stage, script, outputs, *, args=(), deps=(), est_h=0.05, evidence="cheap "
         "post-processing (reads JSON / fields; seconds to minutes)", validate=None, mem_gb=4,
         ncpus=1, prefer="local", env=None, blocked=None, notes=None, design=None):
    return job(id, stage, [f"scripts/{script}", *args], outputs, deps=deps, est_h=est_h,
               evidence=evidence, validate=validate or [
                   {"file": o, "kind": "json" if o.endswith(".json") else
                    ("csv" if o.endswith(".csv") else "exists")} for o in outputs],
               mem_gb=mem_gb, ncpus=ncpus, prefer=prefer, env=env, blocked=blocked,
               notes=notes, design=design)


def mech_revision_variants():
    """The encapsulant classes and the local-card BGA layer of configs/tcpmt_mech (the
    variants tcpmt_mech_variants.register adds), in config order."""
    import yaml
    c = yaml.safe_load((REPO / "configs" / "tcpmt_mech" / "mechanics_revision.yaml").read_text())
    return list(c["encapsulant"]["variants"]) + [c["bga_global"]["reconciled_variant"]]


def fc(name):
    return f"final_closure/{name}"


def tr(name):
    return f"tcpmt_revision/{name}"


def sens(arch, variant, scen="HV_S0"):
    return f"final_closure/sensitivity/etm_{arch}_{scen}__{variant}.json"


def case(arch, scen, refine="r21"):
    return fc(f"etm_{arch}_{scen}_h1.1{'' if refine == 'r11' else '_' + refine}.json")


# ============================================================================ the manifest

def state_spec(a, state, t, sub="", refine=None):
    """(argv, output, env) of one integration in one input state and cooling (tcpmt_cases):
    the production boundary for Z1/Z2 under A at a reference state, the implemented
    decoupling (sdec) or a tier base otherwise (Z3: the coupled land side). `refine` (e.g.
    'r11') solves it on that rung of the nested refinement: the variant drivers take the rung
    token and write sensitivity/ladder/<case>_<rung>.json (final_closure_sensitivity.
    set_refine), the production boundary its own h1.1[_rXZ] name."""
    scen = STATES[state]
    base = TIER_BASE[(a, t)]
    env = {}
    if state != "SDEC" and base is None:
        r = refine or "r21"
        argv = ["scripts/final_closure_physical_etm.py", f"{a}:{scen}:1.1:{r}:ITERATIVE CHOLESKY:1"]
        out = sub + fc(f"etm_{a}_{scen}_h1.1{'' if r == 'r11' else '_' + r}.json")
        return argv, out, env
    rung = refine if refine and refine != "r21" else None
    name = f"sdec_{t}" if state == "SDEC" else base
    argv = (["scripts/tcpmt_review_variants.py", "sdec", a, t] if state == "SDEC" else
            ["scripts/tcpmt_review_variants.py", "state", a, t, scen]) + ([rung] if rung else [])
    out = sub + fc(f"sensitivity/{'ladder/' if rung else ''}etm_{a}_{scen}__{name}"
                   f"{'_' + rung if rung else ''}.json")
    return argv, out, env


def prep_jobs(d=None, land=True):
    """The per-design inputs: the Z1 package network closed at the production state (the
    design record's committed production k) and, for a design that runs Z3 (`land`), the
    Z3 land-side sheets."""
    sub = f"designs/{d}/" if d else ""
    pre = f"{d}." if d else ""
    out = {}
    out["network"] = job(
        f"{pre}prep.package_network", "prep", ["scripts/final_closure_pkg_network.py"],
        [sub + fc("package_network.json"), sub + fc("bga_count_screen.csv")],
        env={"FC_WORKERS": 8}, ncpus=8, workers=8, est_h=0.6, mem_gb=16, design=d,
        evidence="final_closure_pkg_network.py (FC_WORKERS pool): exhaustive level-1 screen of "
                 "every legal count, level-2 verification, levels 1-3 at the matched count",
        validate=[{"file": sub + fc("package_network.json"), "kind": "json"}],
        notes="the count is closed and matched at the PRODUCTION state, at the committed "
              "production k of the design record (`decoupling`), at most 220 balls per rail; "
              "no closing count -> the declared fallback count, flagged NOT_CLOSED "
              "(match_fallback); the worst-ball RMS check follows in derived.bga_reclose")
    if not land:
        return out
    out["land_est"] = post(f"{pre}prep.z3land_estimate", "prep", "tcpmt_z3_landside_estimate.py",
                           [sub + tr("z3_landside_spreading.json")], est_h=0.1, design=d,
                           evidence="2-D FV sheet on the design's cell grid, minutes")
    out["land_fv"] = post(f"{pre}prep.z3land_fv", "prep", "tcpmt_z3land_fv.py",
                          [sub + tr("z3_board_plane_spreading.json")], deps=[out["land_est"]],
                          est_h=0.2, design=d, evidence="2-D FV board planes, minutes")
    return out


def decap_chain(z1_s0, network, d=None):
    """circuit -> placement -> ledger -> summary (each read-modify-writes
    input_decoupling.json): the decoupling of the design's own grid and cell waveform."""
    sub = f"designs/{d}/" if d else ""
    pre = f"{d}." if d else ""
    f = sub + tr("input_decoupling.json")
    c = post(f"{pre}derived.decap_circuit", "derived", "tcpmt_decap_circuit.py", [f],
             deps=[z1_s0, network], design=d, prefer="local", est_h=0.1)
    p = post(f"{pre}derived.decap_placement", "derived", "tcpmt_decap_placement.py", [f],
             deps=[c], est_h=0.3, design=d,
             validate=[{"file": f, "kind": "json", "keys": ["placement"]}],
             notes="interleaving patterns of the design's n x n grid; RECOMMENDED = the "
                   "implementable interleaving + ring option of least nominal k_eq (declared "
                   "rule: one or two n-phase clock groups; m36: dual6, 12 phases)")
    return c, p


def summary_chain(place, z1_s0, z1_s1, d=None):
    sub = f"designs/{d}/" if d else ""
    pre = f"{d}." if d else ""
    f = sub + tr("input_decoupling.json")
    led = post(f"{pre}derived.decap_ledger", "derived", "tcpmt_decap_framework.py", [f],
               args=["ledger"], deps=[place, z1_s0] + ([z1_s1] if z1_s1 else []), design=d)
    return job(f"{pre}derived.decap_framework", "derived",
               ["scripts/tcpmt_decap_framework.py", "summary"], [f], deps=[led], est_h=0.1,
               prefer="local", evidence="cheap", design=d,
               validate=[{"file": f, "kind": "json", "keys": ["summary"]}])


# ============================================================================ the manifest
def build(design):
    JOBS.clear()
    D = DESIGNS[design]

    # ------------------------------------------------------------------ prep
    prep = {}
    prep["literature"] = post("prep.literature_rules", "prep", "final_closure_literature_rules.py",
                              [fc("literature_rules.json")])
    prep.update(prep_jobs())
    # vr_attach reads the production Z2 case: it runs as derived.vr_attach (below), not in prep
    prep["geometry"] = post("prep.architecture_spec", "prep", "final_closure_architecture_spec.py",
                            [fc("architecture_geometry.json")], est_h=0.1,
                            evidence="meshes the three packages once (minutes)")
    prep["tier_order"] = post("prep.tier_order", "prep", "tcpmt_tier_order.py",
                              [tr("tier_order.json")], est_h=0.2,
                              evidence="least-routing-loss assignment of every order of the "
                                       "decided tiers + repartition search, every design: "
                                       "~4 min on one core (record generation, 2026-11-19)",
                              notes="reproduces the production order and part assignment the "
                                    "design record states: via criterion, then least intra-VR "
                                    "routing loss (ledger model, 25 C), heat path within 0.1 W")
    prep["cards"] = post("prep.converter_cards", "prep", "tcpmt_converter_cards.py",
                         [tr("converter_cards.json")], est_h=0.05,
                         notes="mixed-tier cards of every design of the record")

    # ------------------------------------------------------------------ production state
    prod, ladder_src = {}, {}
    land_deps = [prep["land_est"], prep["land_fv"]]
    for a in D["archs"]:
        for t in TIERS:
            for state in ("S0", "S1"):
                argv, out, env = state_spec(a, state, t)
                prod[(a, state, t)] = etm_job(
                    f"prod.{a}.{state}.{t}", "production", argv, out,
                    deps=[prep["network"]] + (land_deps if a == "Z3" else []),
                    n_el_k=120 if a != "Z3" else 110, env=env,
                    analog=case("Z1", STATES[state]))
    # the S2 references of the local solder study (production boundary; Z3 coupled)
    for a in D["archs"]:
        st2 = ("HV_S2", "A")
        base = TIER_BASE[(a, "A")]
        if base is None:
            argv = ["scripts/final_closure_physical_etm.py", f"{a}:HV_S2:1.1:r21:ITERATIVE CHOLESKY:1"]
            out = fc(f"etm_{a}_HV_S2_h1.1_r21.json")
        else:
            argv = ["scripts/tcpmt_review_variants.py", "state", a, "A", "HV_S2"]
            out = fc(f"sensitivity/etm_{a}_HV_S2__{base}.json")
        prod[(a, "S2", "A")] = etm_job(f"prod.{a}.S2.A", "production", argv, out,
                                       deps=[prep["network"]] + (land_deps if a == "Z3" else []),
                                       n_el_k=120, analog=case("Z1", "HV_S2"))
    dcirc, dplace = decap_chain(prod[("Z1", "S0", "A")], prep["network"])
    for a in D["archs"]:
        for t in TIERS:
            argv, out, env = state_spec(a, "SDEC", t)
            prod[(a, "SDEC", t)] = etm_job(
                f"prod.{a}.SDEC.{t}", "production", argv, out,
                deps=[prep["network"], dplace] + (land_deps if a == "Z3" else []),
                n_el_k=120 if a != "Z3" else 110, analog=sens("Z2", "sdec_B", "HV_SDEC"),
                notes="PRODUCTION STATE: implemented decoupling at the k_eq this campaign's "
                      "decoupling chain derives (derived.decap_placement)")
    dsum = summary_chain(dplace, prod[("Z1", "S0", "A")], prod[("Z1", "S1", "A")])
    # converged fields (copied out of the work tree; read by mech variants, figures, feedback)
    fields = {}
    for (a, s) in (("Z1", "HV_S0"), ("Z2", "HV_S0"), ("Z1", "HV_S1"), ("Z2", "HV_S1")):
        st = "S0" if s == "HV_S0" else "S1"
        fields[(a, s)] = job(
            f"fields.{a}.{s}", "production", ["scripts/final_closure_collect_fields.py", f"{a}:{s}"],
            [f"@fields/etm_{a}_{s}_r21/thermal_converged.frd",
             f"@fields/etm_{a}_{s}_r21/structural.frd"], deps=[prod[(a, st, "A")]], est_h=0.03,
            evidence="file copy + peak check", prefer="any",
            validate=[{"file": f"@fields/etm_{a}_{s}_r21/thermal_converged.frd", "kind": "frd"},
                      {"file": f"@fields/etm_{a}_{s}_r21/structural.frd", "kind": "frd"}])
    vfields = {}
    for (a, t), v in TIER_BASE.items():
        if v is None:
            vfields[(a, t)] = fields[(a, "HV_S0")]
            continue
        vfields[(a, t)] = job(
            f"fields.{a}.{v}", "production", ["scripts/tcpmt_collect_variant_fields.py", f"{a}:{v}"],
            [f"@fields/etm_{a}_HV_S0__{v}/thermal_converged.frd",
             f"@fields/etm_{a}_HV_S0__{v}/structural.frd"], deps=[prod[(a, "S0", t)]],
            est_h=0.03, evidence="file copy + peak check",
            validate=[{"file": f"@fields/etm_{a}_HV_S0__{v}/thermal_converged.frd",
                       "kind": "frd"}])
    # the production local solder response (Z3: its coupled cooling-A case)
    loc_deps = [prod[(a, s, "A")] for a in ARCHS for s in ("S0", "S1", "S2")]
    loc_t = job("local.temporal", "production",
                ["scripts/final_closure_local_mesh.py", "--temporal"], [fc("local_time_study.json")],
                deps=loc_deps, ncpus=16, workers=16, mem_gb=16,
                env={"FC_POOL_MAX": 16, "LOCAL_THREADS": 1}, est_h=2.0,
                evidence="local_time_study.json: 72 ccx solves, sum 85,058 s, max 1,643 s "
                         "(followup_local.log 3 h 12 min on 8 x 6 threads)",
                validate=[{"file": fc("local_time_study.json"), "kind": "json"}])
    loc_c = job("local.cycles", "production", ["scripts/final_closure_local_mesh.py", "--cycles"],
                [fc("local_cycle_study.json")], deps=[loc_t], ncpus=9, workers=9, mem_gb=12,
                env={"FC_POOL_MAX": 9, "LOCAL_THREADS": 1}, est_h=1.6,
                evidence="9 solves x 16 cycles, 5,160-5,370 s each (followup_local.log 1 h 55 min)",
                validate=[{"file": fc("local_cycle_study.json"), "kind": "json"}])
    loc_m = job("local.mesh_study", "production", ["scripts/final_closure_local_mesh.py"],
                [fc("local_mesh_study.json")], deps=[loc_c], ncpus=16, workers=16, mem_gb=24,
                env={"FC_POOL_MAX": 16, "LOCAL_THREADS": 1}, est_h=1.0,
                evidence="33 solves L0-L3, sum 23,330 s, max 2,623 s (followup_local.log 1 h 21 min)",
                validate=[{"file": fc("local_mesh_study.json"), "kind": "json",
                           "keys": ["cases"]}])
    loc_s = {}
    for s, st, est in (("HV_S0", "S0", 1.5), ("HV_S1", "S1", 0.3), ("HV_S2", "S2", 0.2)):
        loc_s[s] = job(f"local.solder.{s}", "production",
                       ["scripts/final_closure_local_solder.py", s], [fc(f"local_solder_{s}.json")],
                       deps=[loc_m] + [prod[(a, st, "A")] for a in ARCHS], ncpus=6,
                       mem_gb=12, est_h=est,
                       evidence="local_solder_*.json wall_s 5,252 / 993 / 688 s (7 sequential "
                                "solves, 6 threads hard-coded in run_final_local_response.py)",
                       validate=[{"file": fc(f"local_solder_{s}.json"), "kind": "json"}])

    # ------------------------------------------------------------------ Z3 land side
    land = {}
    for v, tier_ in (("z3_land_t10_B", "B"), ("z3_land_t20_B", "B"), ("z3_land_t40_B", "B"),
                     ("z3_land_t40_A", "A"), ("z3_land_t40_B_noplane", "B"),
                     ("z3_land_t100_B", "B"), ("z3_land_t10_B_fvmap", "B"),
                     ("z3_land_t20_B_fvmap", "B"), ("z3_land_t100_B_fvmap", "B")):
        land[v] = etm_job(f"z3land.{v}", "z3_landside",
                          ["scripts/tcpmt_z3land_variants.py", "run", v], sens("Z3", v),
                          deps=[prod[("Z3", "S0", tier_)]] + land_deps, n_el_k=110)
    land["z3_land_t40_A_fvmap"] = prod[("Z3", "S0", "A")]
    land["z3_land_t40_B_fvmap"] = prod[("Z3", "S0", "B")]
    land_rep = post("z3land.report", "z3_landside", "tcpmt_z3land_report.py",
                    [tr("z3_land_coupled.json")], deps=sorted(set(land.values())))

    # ------------------------------------------------------------------ feedback, hot spots
    fb, hs = {}, {}
    for (a, t) in TIER_BASE:
        s, ev = feedback_wall_s(a, t)
        if s is None:
            s, ev = feedback_wall_s(a, "A" if t == "B" else "B")
            ev = f"analog {ev}"
        out = sens(a, f"tim_warp_fb_{t}", "HV_SDEC")
        fb[(a, t)] = job(
            f"feedback.{a}.{t}", "interface_feedback",
            ["scripts/tcpmt_review_variants.py", "feedback", a, t, "HV_SDEC"],
            [out], deps=[prod[(a, "SDEC", t)], dplace],
            env={"FC_THREADS": 2}, ncpus=2, mem_gb=mem_for(120), est_h=(s or 9000) / 3600,
            evidence=ev, validate=[{"file": out, "kind": "feedback"}],
            notes="production state; iterates E-T + mechanics until die warpage < 1 % and loss "
                  "< 0.05 W (<= 5 passes); writes review_variants/*_itN.json per pass")
        hs[(a, t)] = etm_job(f"hotspot.{a}.{t}", "hotspots",
                             ["scripts/tcpmt_review_variants.py", "hotspot", a, t, "HV_SDEC"],
                             sens(a, f"die_hotspot_{t}", "HV_SDEC"),
                             deps=[prod[(a, "SDEC", t)], dplace],
                             analog=sens(a if a != "Z3" else "Z2", f"die_hotspot_{t}"),
                             n_el_k=120)

    # ------------------------------------------------------------------ the other designs
    alt = {}
    for dk, spec in ALTERNATES.items():
        sub = f"designs/{dk}/"
        ap = prep_jobs(dk, land="Z3" in spec["archs"])
        argv, out, env = state_spec("Z1", "S0", "A", sub)
        z1s0 = etm_job(f"{dk}.prod.Z1.S0.A", spec["stage"], argv, out, deps=[ap["network"]],
                       n_el_k=120, design=dk, analog=case("Z1", "HV_S0"))
        _c, apl = decap_chain(z1s0, ap["network"], dk)
        for a in spec["archs"]:
            for t in TIERS:
                argv, out, env = state_spec(a, "SDEC", t, sub)
                alt[(dk, a, t)] = etm_job(
                    f"{dk}.prod.{a}.SDEC.{t}", spec["stage"], argv, out,
                    deps=[ap["network"], apl] + ([ap["land_est"], ap["land_fv"]]
                                                 if a == "Z3" else []),
                    n_el_k=120, design=dk, env=env, analog=sens("Z2", "sdec_B", "HV_SDEC"),
                    notes=f"{spec['role']}; production state of design {dk}")
    cmp_deps = [prod[(a, "SDEC", t)] for a in D["archs"] for t in TIERS] + list(alt.values())
    post("derived.design_comparison", "derived", "tcpmt_design_comparison.py",
         [tr("design_comparison.json")], deps=cmp_deps,
         notes="production vs 5-tier vs thin capacitor, and the count ranking (25 / 36 / 49) "
               "through the chain against the screen's")
    post("derived.k_check", "derived", "tcpmt_design_comparison.py", [tr("k_check.json")],
         args=["kcheck"], deps=[dsum],
         notes="the k_eq the campaign's decoupling chain derives against the committed "
               "production k the package network was closed at")
    post("derived.bga_reclose", "derived", "final_closure_pkg_network.py",
         [fc("bga_count_production.json")], args=["reclose"],
         deps=[prep["network"], dsum] + [prod[(a, "SDEC", t)] for a in ("Z1", "Z2")
                                        for t in TIERS],
         ncpus=4, env={"FC_WORKERS": 4}, est_h=0.3,
         notes="re-closes the count at the production state with the production cases' "
               "48-V currents (level-2 verification), at the k this campaign's decoupling "
               "chain derives, at most 220 balls per rail; the closure current is the worse "
               "of the DC peak x k_eq rule and Z1's worst-ball RMS of the port model (both "
               "recorded)")
    post("derived.decap_limits", "derived", "tcpmt_decap_placement.py",
         [tr("decoupling_limits.json")], args=["limits"], deps=["derived.bga_reclose"],
         est_h=0.15, evidence="input_decoupling limits of the m36 development run: wall 321 s",
         notes="the alternatives of the adopted clock plan: every plan of the grid with the "
               "ring and its closure-rule ball current, the interleaving limit (optimal 6/9/12/"
               "36-phase assignments), ring bounds, and k_eq against the BGA count")

    # ------------------------------------------------------------------ refinement ladders
    lad = {}
    for a in ("Z1", "Z2"):
        for r, thr, sol_thr, n_k in (("r11", 2, 1, 30), ("r12", 2, 1, 60), ("r31", 4, 2, 270)):
            argv, out, env = state_spec(a, "S0", "A", refine=r)
            lad[(a, r)] = etm_job(f"ladder.{a}.{r}", "refinement_ladders", argv, out,
                                  deps=[prep["network"]], analog=case("Z1", "HV_S0", r),
                                  n_el_k=n_k, ncpus=thr, speed=(0.8 if r == "r31" else 1.0))
    # the production state at the coarse and fine rungs (rung token): r11 is also the smoke test
    for a in D["archs"]:
        for t in TIERS:
            for r, thr, n_k in (("r11", 2, 30), ("r31", 4, 270)):
                argv, out, env = state_spec(a, "SDEC", t, refine=r)
                lad[(a, f"sdec_{t}", r)] = etm_job(
                    f"ladder.{a}.sdec_{t}.{r}", "refinement_ladders", argv, out,
                    deps=[prep["network"], dplace] + (land_deps if a == "Z3" else []),
                    analog=case("Z1", "HV_S0", r), n_el_k=n_k, ncpus=thr, env=env,
                    speed=(0.8 if r == "r31" else 1.0),
                    notes="production state on the nested mesh rung" +
                          ("; the coarse smoke test of the campaign" if r == "r11" else ""))

    # ------------------------------------------------------------------ robustness map
    class_b = [  # (variant, archs, kind)  -- final_closure_sensitivity.VARIANTS
        ("board_t2p4", "Z1 Z2", "full"), ("board_eta025", "Z1 Z2", "full"),
        ("board_eta075", "Z1 Z2", "full"), ("board_h1", "Z1 Z2", "full"),
        ("board_h0_h1grid", "Z1 Z2", "full"), ("tsv_min", "Z1 Z2", "full"),
        ("tsv_mid", "Z1 Z2", "full"), ("f2_void", "Z1 Z2", "full"),
        ("f1_sidewall_filled", "Z2", "full"), ("attach_h20", "Z2", "full"),
        ("attach_h40", "Z2", "full"), ("attach_sn", "Z2", "full"),
        ("attach_dense", "Z2", "full"), ("attach_sparse", "Z2", "full"),
        ("attach_sparse_stiff", "Z2", "full"), ("attach_eng_p34", "Z2", "full"),
        ("attach_eng_p37", "Z2", "full"), ("attach_eng_p41", "Z2", "full"),
        ("attach_stiff", "Z2", "mech"), ("attach_uf_soft", "Z2", "mech"),
        ("attach_uf_stiff", "Z2", "mech"), ("feed_heat_at_crossover", "Z2", "full"),
        ("icepak_equivalent", "Z1 Z2", "full"), ("bga_depop", "Z2", "full"),
        ("board_hbot100", "Z1 Z2", "full"),
        ("board_hbot500", "Z1 Z2", "full"), ("z2_cooled", "Z2", "full"),
        ("pad_drop", "Z1 Z2", "full"), ("gan_k_half", "Z1 Z2", "full"),
        ("conv_k_tenth", "Z1 Z2", "full"), ("conv_E80_a4", "Z1 Z2", "mech"),
        ("conv_E80_a10", "Z1 Z2", "mech"), ("conv_E160_a4", "Z1 Z2", "mech"),
        ("conv_E160_a10", "Z1 Z2", "mech"),
        # review round 3: the range of the gap-post cards (tcpmt_converter_cards POST_BASES)
        ("conv_posts_lower", "Z1 Z2", "full"), ("conv_posts_upper", "Z1 Z2", "full")]
    # TCPMT round 3 (findings 7, 11a): the mechanics-revision variants, cases of the class-B
    # gates mat.encapsulant_card / mat.bga_card_consistency (final_closure_classB), mechanics
    # only on the production field; the list follows configs/tcpmt_mech like the gates do
    class_b += [(v, "Z1 Z2", "mech") for v in mech_revision_variants()]
    rb = {}
    for v, archs, kind in class_b:
        for a in archs.split():
            deps = [prod[(a, "S0", "A")]] + ([fields[(a, "HV_S0")]] if kind == "mech" else [])
            if v == "feed_heat_at_crossover":
                deps.append("derived.direct_feed")
            rb[(a, v)] = etm_job(f"robust.{a}.{v}", "robustness_map",
                                 ["scripts/final_closure_sensitivity.py", f"{v}:{a}"],
                                 sens(a, v), deps=deps,
                                 # a mechanics-only variant without a frozen case: costed as
                                 # the frozen mechanics-only conv_E80_a4 of the same arch
                                 analog=sens(a, "conv_E80_a4") if kind == "mech" else None)
        job(f"robust.local.{v}", "robustness_map", ["scripts/final_closure_sensitivity.py",
                                                    "--local", v],
            [sens(a, v) for a in archs.split()],
            deps=[rb[(a, v)] for a in archs.split()] + [loc_t, loc_m], est_h=0.05,
            ncpus=2 * len(archs.split()), workers=len(archs.split()),
            env={"LOCAL_THREADS": 2, "FC_POOL_MAX": len(archs.split())},
            evidence="local.wall_s of the frozen variant cases: 77-134 s per architecture",
            validate=[{"file": sens(a, v), "kind": "etm", "local": True} for a in archs.split()],
            notes="adds the L0 local solder response at the variant's own critical joint")
    for (a, t) in TIER_BASE:
        etm_job(f"robust.caloric.{a}.{t}", "robustness_map",
                ["scripts/tcpmt_review_variants.py", "caloric", a, t, "HV_SDEC"],
                sens(a, f"plate_caloric_legacy_{t}", "HV_SDEC"),
                deps=[prod[(a, "SDEC", t)], dplace])

    # ------------------------------------------------------------------ the rest
    rest(prod, fields, vfields, land, land_rep, fb, hs, rb, loc_t, loc_m, loc_s, lad, prep,
         dsum)
    return {"jobs": JOBS, "static": sorted(STATIC)}


#: artifacts the pipeline reads that NO job produces (hand-written, ANSYS-only, web or PDF
#: derived, or from an earlier lineage): `run.py seed` copies them from research/ into the
#: campaign root (and into every design subroot) before the first job
STATIC = [
    "final_closure/z2_direct_feed_architecture.json",   # hand-written, frozen before results
    "final_closure/local_mesh_policy.json",             # declared policy, hand-written
    "final_closure/reference_rve.json",                 # ANSYS AEDT Mechanical
    "final_closure/reference_rve_timing.json",          # ANSYS AEDT
    "final_closure/reference_attach_rve.json",          # ANSYS AEDT
    "final_closure/reference_thermal_column_Z1.json",   # ANSYS AEDT IcepakFEA (+ ccx)
    "final_closure/reference_thermal_column_Z2.json",   # ANSYS AEDT (2026-10-29 stack)
    "final_closure/reference_mech_bilayer.json",        # ANSYS AEDT Mechanical (+ ccx)
    "final_closure/reference_cooling_icepak.json",      # ANSYS Icepak
    "final_closure/solver_check/Z1_HV_S0_h0.8_SPOOLES_t1.json",   # needs a superseded h0.8 case
    "final_closure/tool_provenance.json",
    "final_closure/superseded_bga_fed_z2/local_mesh_study_pass3.json",  # read by local_mesh
    "phase0nw/physical_gates.json",                     # read by final_closure_results.py
    "tcpmt_revision/capacitor_datasheet_data.json",     # Murata web API (tcpmt_decap_parts --fetch)
    "tcpmt_revision/flying_cap_vendor_data.json",       # Murata web API (tcpmt_caprule_vendor)
    "tcpmt_revision/omitted_losses_inputs.json",        # digitized datasheet PDFs
    "tcpmt_revision/z3_land_isothermal.json",           # NO producer (gap)
]


def rest(prod, fields, vfields, land, land_rep, fb, hs, rb, loc_t, loc_m, loc_s, lad, prep,
         dsum):
    P = lambda a, s="S0", t="A": prod[(a, s, t)]                            # noqa: E731
    ref_A = [prod[(a, s, "A")] for a in ARCHS for s in ("S0", "S1", "S2")]
    sdec = [prod[(a, "SDEC", t)] for a in ARCHS for t in TIERS]
    tier_cases = [prod[(a, s, t)] for a in ARCHS for t in TIERS for s in ("S0", "SDEC")]

    # ------------------------------------------------------------ DSE sweeps (local, 1 core)
    eng = job("prep.dse_engine", "prep", ["scripts/campaign/build_dse_engine.py",
                                          "{scratch}/dse_engine"],
              ["@scratch/dse_engine/ENGINE.json"], est_h=0.01, prefer="local",
              evidence="file copy", validate=[{"file": "@scratch/dse_engine/ENGINE.json",
                                               "kind": "json", "keys": ["files"]}])
    c17 = "36,40,42,45,48,49,50,52,56,60,64,70,76,84,92,100,120"
    c27 = "16,20,25,28,30,32,33,34,35,36,40,42,45,48,49,50,52,56,60,64,70,76,81,84,92,100,120"
    full = {"HVR_CAP_RULE": "stress", "HVR_SW_RULE": "stress", "HVR_SW_DERATING": 0.9,
            "HVR_COSS_RULE": "corrected", "HVR_PACK_RULE": "on", "HVR_PACK_KEEPOUT_UM": 50,
            "HVR_RG_RULE": "datasheet", "HVR_FOOTPRINT_RULE": "body", "HVR_TIER_RULE": "mixed"}
    dse = {}
    for tag, counts, env, est, ev in (
            ("etm35", c17, {"HVR_CAP_RULE": "legacy"}, 0.10,
             "sweep.log: per-count total 195 s; HEAD engine + legacy rule reproduces etm35"),
            ("etm35_caprule_full", c17, {"HVR_CAP_RULE": "stress", "HVR_CAP_RIPPLE": 1,
                                         "HVR_CAP_ESR_F": 1}, 0.15, "dse_full.log 393 s"),
            # the round-3 screen the design record comes from (scripts/tcpmt_dse_phase2_runs.sh)
            ("etm35_p2_t4", c27, dict(full, HVR_MAX_TIERS=4), 0.4,
             "phase-2 sweep, 27 counts (logs_review): the production m36 and m25/m49"),
            ("etm35_p2_t5", c27, dict(full, HVR_MAX_TIERS=5), 0.4,
             "phase-2 sweep, 27 counts: the 5-tier co-design comparison m36t5"),
            ("etm35_p2_tinf", c27, dict(full, HVR_MAX_TIERS=0), 0.4,
             "phase-2 sweep, no tier limit")):
        d = "tcpmt_revision/dse_j35/data"
        outs = [f"{d}/case_{c}_{tag}.csv" for c in "ABCD"] + \
            [f"{d}/all_architectures_{tag}.csv", f"{d}/meta_{tag}.json"]
        dse[tag] = job(f"dse.{tag}", "dse_sweeps",
                       ["research/tcpmt_revision/dse_j35/sweep_etm.py", "--counts", counts,
                        "--tag", tag], outs, deps=[eng], est_h=est, evidence=ev,
                       env={"HVR_DSE_ENGINE": "{scratch}/dse_engine",
                            "DSE_OUT": "{root}/tcpmt_revision/dse_j35", **env},
                       validate=[{"file": f"{d}/case_D_{tag}.csv", "kind": "csv"},
                                 {"file": f"{d}/meta_{tag}.json", "kind": "json"}],
                       notes="single process, single thread; imports paper_routing.py from "
                             "outside the repository (Salma_Thesis/analysis/...)")
    post("derived.dse_phase2_summary", "derived", "tcpmt_dse_phase2_summary.py",
         [tr("dse_phase2_summary.json")],
         deps=[dse["etm35_p2_t4"], dse["etm35_p2_t5"], dse["etm35_p2_tinf"]],
         env={"HVR_DSE_ENGINE": "{scratch}/dse_engine"},
         notes="the screen the design record entries reproduce (configs/design_points.yaml); "
               "reads the sweeps under the root, records the md5 of the campaign's engine")

    # ------------------------------------------------------------ capacitors
    fcaps = post("derived.flying_caps", "derived", "tcpmt_decap_flying_caps.py",
                 [tr("flying_caps.json")], deps=[P("Z1"), prep["tier_order"]],
                 notes="the flying-capacitor requirement of the design in force")
    post("derived.capacitor_evidence", "derived", "tcpmt_capacitor_evidence.py",
         [tr("capacitor_evidence.json"), "manuscript_v2/supplement/tab_capacitor_evidence.tex"],
         deps=[fcaps])

    # ------------------------------------------------------------ results and class B
    dfeed = job("derived.direct_feed", "derived", ["scripts/final_closure_direct_feed.py"],
                [fc("direct_feed_crossover.json")],
                deps=ref_A + [rb[("Z2", "attach_dense")], rb[("Z2", "attach_sparse")]],
                est_h=0.35, ncpus=1, prefer="local",
                evidence="followup_local.log: 19 min 46 s, one process",
                validate=[{"file": fc("direct_feed_crossover.json"), "kind": "json"}])
    solver = {}
    for sol, thr, tag in (("SPOOLES", 1, "SPOOLES_t1"), ("ITERATIVE CHOLESKY", 10,
                                                        "ITERATIVE_CHOLESKY_t10")):
        solver[tag] = job(f"ladder.solver_check.{tag}", "refinement_ladders",
                          ["scripts/final_closure_solver_check.py", "Z1", "HV_S0", "1.1", sol,
                           str(thr)], [fc(f"solver_check/Z1_HV_S0_h1.1_{tag}.json")],
                          deps=[lad[("Z1", "r11")]], ncpus=thr, mem_gb=8,
                          est_h=0.1, evidence="solver_check JSON: SPOOLES 1 thr 229 s, "
                          "ITERATIVE CHOLESKY 10 thr 295 s",
                          validate=[{"file": fc(f"solver_check/Z1_HV_S0_h1.1_{tag}.json"),
                                     "kind": "json"}],
                          notes="re-solves the structure on ladder.Z1.r11's converged field")
    res = job("derived.results", "derived", ["scripts/final_closure_results.py"],
              [fc(x) for x in ("final_results.json", "electrical_ledger.json",
                               "electrical_ledger.csv", "energy_audit.json",
                               "mesh_convergence.json", "ordering.json", "coupling_checks.json",
                               "control_results.json")],
              deps=ref_A + [dfeed, loc_m] + list(loc_s.values()) +
              [lad[(a, r)] for a in ("Z1", "Z2") for r in ("r11", "r12", "r31")] +
              list(solver.values()), est_h=0.2, prefer="local",
              evidence="JSON work + 12 ledger points",
              validate=[{"file": fc("final_results.json"), "kind": "json"},
                        {"file": fc("mesh_convergence.json"), "kind": "json", "keys": ["cases"]},
                        {"file": fc("ordering.json"), "kind": "json"}])
    attach_vs = [rb[("Z2", v)] for v in ("attach_dense", "attach_sparse", "attach_eng_p34",
                                         "attach_eng_p37", "attach_eng_p41")]
    attach_loc = [f"robust.local.{v}" for v in ("attach_dense", "attach_sparse", "attach_eng_p34",
                                                "attach_eng_p37", "attach_eng_p41")]
    vra = post("derived.vr_attach", "derived", "final_closure_vr_attach.py",
               [fc("vr_attach_density_study.json"), fc("vr_attach_density_study.csv")],
               deps=[P("Z2"), res, loc_m] + attach_vs + attach_loc, est_h=0.1)
    classb_vs = [k for k in rb if k[0] in ("Z1", "Z2")]
    post("derived.classB", "derived", "final_closure_classB.py",
         [fc("classB_resolution.json"), fc("classB_resolution.csv"),
          fc("classB_sensitivity_rows.csv")],
         deps=[res, vra, loc_m, prep["network"], dfeed, P("Z1"), P("Z2")] +
         [rb[k] for k in classb_vs] + sorted({f"robust.local.{k[1]}" for k in classb_vs}))
    moose = moose_jobs(prod, fields, lad)
    post("derived.accuracy_matrix", "derived", "final_closure_accuracy_matrix.py",
         [fc("accuracy_speed_matrix.json"), fc("accuracy_speed_matrix.csv")],
         deps=[vra, prep["network"], res] + list(solver.values()) + moose["refs"] +
         [lad[(a, r)] for a in ("Z1", "Z2") for r in ("r11", "r12", "r31")])

    # ------------------------------------------------------------ cooling tiers, feasibility
    flds = [fields[("Z1", "HV_S0")], fields[("Z2", "HV_S0")], vfields[("Z1", "B")],
            vfields[("Z2", "B")], vfields[("Z3", "A")], vfields[("Z3", "B")]]
    post("derived.layer_temperatures", "derived", "tcpmt_layer_temperatures.py",
         [tr("layer_temperatures.json")], deps=flds + sdec, est_h=0.1)
    post("derived.tier_feed", "derived", "tcpmt_tier_feed.py", [tr("tier_feed_crossover.json")],
         deps=tier_cases)
    cool = post("derived.cooling_spec", "derived", "tcpmt_cooling_spec.py",
                [tr("cooling_spec.json")], deps=tier_cases)
    post("derived.feasibility", "derived", "tcpmt_feasibility.py", [tr("feasibility.json")],
         deps=flds + [fields[("Z1", "HV_S1")], fields[("Z2", "HV_S1")]] + tier_cases +
         [prod[(a, "S1", t)] for a in ARCHS for t in TIERS], est_h=0.15, mem_gb=8,
         evidence="mesh builds + frd reads (minutes)")
    post("derived.platform", "derived", "tcpmt_platform.py", [tr("platform_inclusive.json")],
         deps=[cool, land_rep] + tier_cases)
    solder = solder_jobs(prod, land, loc_t, loc_m)
    post("derived.uncertainty", "derived", "tcpmt_uncertainty.py",
         [tr("uncertainty.json"), "manuscript_v2/tab_uncertainty.tex"],
         deps=[lad[k] for k in lad] + tier_cases + [loc_m, solder["studies"], solder["z3land"]])
    post("derived.omitted_losses", "derived", "tcpmt_omitted_losses.py", [tr("omitted_losses.json")],
         deps=[dse["etm35"]] + tier_cases,
         est_h=0.1, notes="the f_sw-grid section needs tcpmt_omitted_losses_fsw_grid.py, which "
         "cannot run at HEAD (engine md5 check, stale patch patterns): written available:false")

    # ------------------------------------------------------------ manuscript
    manuscript()


def solder_jobs(prod, land, loc_t, loc_m):
    deps = [prod[(a, s, t)] for a in ARCHS for s in ("S0", "SDEC") for t in TIERS] + \
        [prod[("Z1", "S1", "A")], prod[("Z2", "S1", "A")], loc_t, loc_m]
    runs = "; ".join("{python} scripts/tcpmt_solder_%s.py --run" % x
                     for x in ("critical", "cycles", "band", "units_check", "constitutive"))
    st = job("solder.studies", "solder_submodels",
             ["bash", "-c", "set -e; cd {repo}; " + runs + "; {python} scripts/tcpmt_solder_collect.py"],
             [tr("solder_studies.json")], deps=deps, ncpus=12, workers=6, mem_gb=24, est_h=2.5,
             env={"LOCAL_THREADS": 2, "TCPMT_SOLDER_SLOTS": 6},
             evidence="scratch_solder records: critical 219 solves 16.5 ks, cycles 12 solves "
                      "7.5 ks, band 12 solves 3.6 ks, units/constitutive 94 records 8.3 ks; "
                      "6 slots x 2 threads; record mtimes 14:52-16:51 (about 2 h)",
             validate=[{"file": tr("solder_studies.json"), "kind": "json"}],
             notes="the five drivers share 6 global solve slots (tcpmt_solder_common), so one "
                   "job runs them in sequence; ~35 GB of solver scratch")
    par = post("solder.parameters", "solder_submodels", "tcpmt_solder_parameters.py",
               [tr("solder_parameters.json")], deps=[st, prod[("Z1", "S0", "A")]],
               env={"LOCAL_THREADS": 2})
    z3 = job("solder.z3land", "solder_submodels", ["scripts/tcpmt_solder_z3land.py"],
             [tr("solder_z3land.json")], deps=[st, land["z3_land_t40_A_fvmap"],
                                               land["z3_land_t40_B_fvmap"]],
             ncpus=4, workers=2, mem_gb=8, est_h=0.35, env={"LOCAL_THREADS": 2},
             evidence="logs_review/solder_z3land.log: 2 x 48-cycle L0 solves, 1056/1011 s, parallel",
             validate=[{"file": tr("solder_z3land.json"), "kind": "json"}])
    return {"studies": st, "parameters": par, "z3land": z3}


def moose_jobs(prod, fields, lad):
    """MOOSE references. heat_transfer-opt does NOT load on califone (RHEL 9.6 lacks
    libhdf5.so.103 / libhdf5_hl.so.100, checked by a PBS probe), so these are local-only."""
    refs = []
    for a in ("Z1", "Z2"):
        refs.append(job(f"moose.column.{a}", "moose_checks",
                        ["scripts/reference_tools/moose_thermal_column.py", a],
                        [fc(f"reference_thermal_column_moose_{a}.json")],
                        deps=[lad[(a, "r11")]], ncpus=8, mem_gb=16, est_h=0.3,
                        backends=("local",), prefer="local",
                        evidence="ccx column 8 thr 4 runs median 135/121 s + MOOSE serial "
                                 "m1/m2 4 runs each: ~17 min (Z1), ~13 min (Z2)",
                        validate=[{"file": fc(f"reference_thermal_column_moose_{a}.json"),
                                   "kind": "json"}]))
        refs.append(job(f"moose.pkg_rdl.{a}", "moose_checks",
                        ["scripts/reference_tools/moose_pkg_rdl_reference.py", a],
                        [fc(f"reference_pkg_rdl_moose_{a}.json")], ncpus=2, mem_gb=16,
                        est_h=0.15, backends=("local",), prefer="local",
                        evidence="FV L3 4x ~20 s + gmsh + MOOSE serial m3 4x ~60 s: ~6 min",
                        validate=[{"file": fc(f"reference_pkg_rdl_moose_{a}.json"),
                                   "kind": "json"}]))
    v = "scripts/tcpmt_fullpkg_verify.py"
    full = job("moose.fullpkg", "moose_checks",
               ["bash", "-c", "set -e; cd {repo}; {python} %s Z1; {python} %s Z1 --ladder 3; "
                "{python} %s Z1 --split 2,2,1 1,1,2 1,1,4 3,3,1 4,4,1; {python} %s --side"
                % (v, v, v, v)],
               [tr("fullpkg_verification.json")],
               deps=[prod[("Z1", "S0", "A")], fields[("Z2", "HV_S0")]],
               ncpus=8, mem_gb=64, est_h=1.5, backends=("local",), prefer="local",
               evidence="scratch_fullpkg: ccx 8 thr median 94/101 s x4, MOOSE 8 ranks; x3 "
                        "refinement 3.9 M hex 276 s, rank-0 peak 6.5 GB (x8 replicated); "
                        "~1 h on 8 cores under load",
               validate=[{"file": tr("fullpkg_verification.json"), "kind": "json"}],
               notes="Z1 only: the Z3 full-package check read the superseded uncoupled case")
    return {"refs": refs, "fullpkg": full}


FIGS = {  # fig script -> output pdf
    "fig_concept": "fig1_concept_framework.pdf", "fig_converter": "fig2_converter.pdf",
    "fig_stacks": "fig3_sections.pdf", "fig_realizability": "fig4_realizability.pdf",
    "fig_ledger": "fig5_loss_swap.pdf", "fig_crossover": "fig6_crossover.pdf",
    "fig_fields": "fig7_fields.pdf", "fig_scenarios": "fig8_scenarios.pdf",
    "fig_tiers": "fig8_tiers.pdf", "fig_robustness": "fig9_robustness_map.pdf",
    "fig_validation": "fig10_verification.pdf", "fig_dse": "fig_dse.pdf"}


def manuscript():
    every = [j["id"] for j in JOBS if j["stage"] != "manuscript" and not j.get("blocked")]
    mac = job("manuscript.macros", "manuscript", ["scripts/tcpmt_manuscript_macros.py"],
              ["manuscript_v2/results_macros.tex", "manuscript_v2/tab_compare.tex"], deps=every,
              est_h=0.05, prefer="local", evidence="trace run: ~1 min",
              notes="reads every result family (traced: 198 files); waits for all non-blocked jobs",
              validate=[{"file": "manuscript_v2/results_macros.tex", "kind": "exists"}])
    job("manuscript.supplement", "manuscript", ["scripts/tcpmt_supplement.py"],
        ["manuscript_v2/supplement/supp_tables.tex"], deps=[mac], est_h=0.05, prefer="local",
        evidence="trace run: ~1 min")
    for f, pdf in FIGS.items():
        job(f"manuscript.{f}", "manuscript", [f"manuscript_v2/fig_scripts/{f}.py"],
            [f"manuscript_v2/figs/{pdf}"], deps=[mac], est_h=0.05 if f != "fig_fields" else 0.15,
            prefer="local", cwd="manuscript_v2/fig_scripts", evidence="trace run: seconds",
            notes="writes the PDF (and PNG) under <root>/manuscript_v2/figs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="m36", choices=sorted(DESIGNS))
    ap.add_argument("--campaign", default="campaign_v3")
    ap.add_argument("--out", default=str(HERE / "manifest.yaml"))
    a = ap.parse_args()
    import yaml
    res = build(a.design)
    jobs = res["jobs"]
    ids = {j["id"] for j in jobs}
    for j in jobs:
        miss = [d for d in j["deps"] if d not in ids]
        if miss:
            raise SystemExit(f"{j['id']}: unknown dependencies {miss}")
    jobs.sort(key=lambda j: (STAGE_RANK[j["stage"]], -j["est_wall_h"]))
    D = DESIGNS[a.design]
    doc = {
        "campaign": {
            "name": a.campaign,
            "results_root": "research/{campaign}",
            "scratch_root": "/home/beams0/SABDELZAHER/ETM_project/scratch_campaign/{campaign}",
            "frozen_fields": "/home/beams0/SABDELZAHER/ETM_project/scratch/fields",
            "python": "/home/beams0/MGHARIB/envs/etm/bin/python",
            "path_prepend": ["/home/beams0/MGHARIB/envs/etm/bin"],
            "moose": "/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/heat_transfer-opt",
            "env": ENV_GLOBAL,
            "design_point": {"name": a.design, "design": D["label"],
                             "record": "configs/design_points.yaml",
                             "alternates": {k: v["role"] for k, v in ALTERNATES.items()}},
        },
        "local": {"max_cores": 35, "nice": 0},
        "pbs": {"host": "pioneer", "qsub": "/opt/pbs/bin/qsub", "qstat": "/opt/pbs/bin/qstat",
                "qdel": "/opt/pbs/bin/qdel", "queue": "cpu_only", "select_extra": "host=califone",
                "max_running": 8, "max_queued": 50, "max_walltime_h": 96, "max_ncpus": 112,
                "max_mem_gb": 512, "resubmit_failed": 1, "hybrid_buffer": None,
                "jobs_dir": "/home/beams/SABDELZAHER/pbs_jobs/etm/{campaign}"},
        "stages": [{"name": s, "what": w} for s, w in STAGES],
        "static_inputs": res["static"],
        "design_subroots": list(ALTERNATES),
        "jobs": jobs,
    }
    hdr = ("# GENERATED by scripts/campaign/build_manifest.py -- edit the generator, not this "
           "file.\n# Campaign manifest of the TCPMT paper results; see scripts/campaign/README.md\n")
    Path(a.out).write_text(hdr + yaml.safe_dump(doc, sort_keys=False, width=100))
    nb = sum(1 for j in jobs if j.get("blocked"))
    print(f"wrote {a.out}: {len(jobs)} jobs ({nb} blocked), design {a.design}")


if __name__ == "__main__":
    main()
