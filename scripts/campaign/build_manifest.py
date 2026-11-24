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
(final_closure_pkg_network.FALLBACK_RULE): the modelled arrangement, the network the
decoupling chain derives k_eq on. Review round 3 (the authors' decision of 2026-11-22):
derived.bga_reclose ADOPTS the provisioned 48-V count of each architecture -- the smallest
legal count per rail meeting the feasibility target (2 A per ball, Kuan et al. 2015; 1.5 A
reported as a sensitivity) by ONE rule for every integration, the DC peak x k_eq at the k the
campaign's chain derived, within the site budget (75 % of the package's own sites; Z2's ring:
at most 198 per rail) and at most 220 per rail -- solves the network there
(package_network_adopted.json, which the BGA-fed ledgers, the Z2 ring feed and the feasibility
stage take) and records Z1's worst-ball RMS of the port model as an idealized bound and the
change of each production case's BGA feed terms (coupled_effect). The per-ball check reads the
production cases' own 48-V current, so the production cases on another count are re-run after
the re-closure and the re-closure confirms the count (a second pass; README 4c). The
feasibility stage applies the same target per TCPMT_BGA_POLICY ('requirement' by default,
'hard' a filter; both policies' verdicts are stored).
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
    ("mech_revision", "the mechanics revision in the production state: v2 local model (law band, "
                      "critical joints, checks), interconnect layers, reflow, board / mounting / "
                      "clamp, encapsulant and cooling-B mechanics-only variants"),
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


def mem_for(n_elems_k, rung="r21", design=None):
    """Requested memory (GB) of an ETM job: its peak estimate -- the element count (thousands)
    x the measured peak per element of its mesh rung, or a measured peak of the same mesh when
    that is larger -- x MEM_MARGIN, at least 6 GB (m36: r11/r12 6 GB, r21 11 GB at 120 kel,
    r31 52 GB at 270 kel; m49 r21 17 GB)."""
    peak = max(MEM_GB_PER_KEL[rung] * n_elems_k, MEM_PEAK_GB.get((design, rung), 0.0))
    return max(6, int(math.ceil(peak * MEM_MARGIN)))


#: peak RSS per 1000 mesh elements of an ETM job (python + CalculiX, E-T + mechanics), by mesh
#: rung, measured in campaign_v3 (status maxrss over the case's thermal.n_elems, m36,
#: 2026-11-19/20): r11 0.019-0.022 GB (24-28 kel), r12 0.017 (56-57 kel), r21 0.057-0.058
#: (79-126 kel, every r21 mesh of m36 / m36t5 / m36thin / m25), r31 0.127 (Z1 / Z2 / Z3,
#: 215-255 kel: 27.3-32.3 GB). The coefficient grows with refinement (structural fill-in): the
#: earlier flat 0.023 GB/kel x 2.5 asked 16 GB for r31, and PBS killed every r31 rung at 16 GB.
MEM_GB_PER_KEL = {"r11": 0.022, "r12": 0.022, "r21": 0.058, "r31": 0.127}
#: measured peaks (GB) of meshes above their rung's coefficient: the 49-cell production mesh
#: (144.5 kel at r21, 0.078 GB/kel: 11.3 GB, m49.prod.Z1.S0.A local; 7 GB asked, so its SDEC
#: jobs were killed at 7.2 GB on califone)
MEM_PEAK_GB = {("m49", "r21"): 11.3}
#: request = estimated peak x this margin (the spread within a rung is under 3 %; the element
#: counts of the jobs are estimates)
MEM_MARGIN = 1.5

#: the local solder-harness chain (time / cycle / mesh studies, local responses, the solder
#: studies) runs on the local host only: it is the critical path to the solder stage and the
#: robustness map's local responses, its solves are short (the m36 time and cycle studies took
#: 9 min each), and califone's cpu_only memory can be fully assigned for hours (2026-11-20: 1800
#: of 1800 GB), which left local.mesh_study queued there ahead of every job it gates
LOCAL_SOLVE_BACKENDS = ("local",)


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
            speed=1.0, notes=None, est_fallback_h=1.8, design=None, rung="r21"):
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
               ncpus=ncpus, mem_gb=mem_for(n_el_k, rung, design), est_h=est,
               evidence=ev or "no evidence",
               blocked=blocked, notes=notes, design=design)


def post(id, stage, script, outputs, *, args=(), deps=(), est_h=0.05, evidence="cheap "
         "post-processing (reads JSON / fields; seconds to minutes)", validate=None, mem_gb=4,
         ncpus=1, prefer="local", env=None, blocked=None, notes=None, design=None,
         backends=("local", "pbs")):
    return job(id, stage, [f"scripts/{script}", *args], outputs, deps=deps, est_h=est_h,
               evidence=evidence, validate=validate or [
                   {"file": o, "kind": "json" if o.endswith(".json") else
                    ("csv" if o.endswith(".csv") else "exists")} for o in outputs],
               mem_gb=mem_gb, ncpus=ncpus, prefer=prefer, env=env, blocked=blocked,
               notes=notes, design=design, backends=backends)


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
              "(match_fallback): the modelled arrangement, on which the decoupling chain "
              "derives k_eq; the provisioned count (the smallest legal count meeting the 2-A "
              "target by the DC peak x k_eq rule within the site budget) and the per-ball "
              "verdict follow in derived.bga_reclose (package_network_adopted.json)")
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
             deps=[z1_s0, network], design=d, prefer="local", est_h=0.1,
             validate=[{"file": f, "kind": "json", "keys": ["circuit"]}])
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
    # several jobs write sections of the same file: each validates ITS OWN section, so an
    # existing file never marks a job 'valid' that has not run
    led = post(f"{pre}derived.decap_ledger", "derived", "tcpmt_decap_framework.py", [f],
               args=["ledger"], deps=[place, z1_s0] + ([z1_s1] if z1_s1 else []), design=d,
               validate=[{"file": f, "kind": "json", "keys": ["framework"]}])
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
                      "decoupling chain derives (derived.decap_placement); a BGA-fed ledger "
                      "(Z1) takes the 48-V balls at the re-closure's adopted count when "
                      "package_network_adopted.json exists (second pass after "
                      "derived.bga_reclose)")
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
                deps=loc_deps, ncpus=16, workers=16, mem_gb=16, backends=LOCAL_SOLVE_BACKENDS,
                env={"FC_POOL_MAX": 16, "LOCAL_THREADS": 1}, est_h=2.0,
                evidence="local_time_study.json: 72 ccx solves, sum 85,058 s, max 1,643 s "
                         "(followup_local.log 3 h 12 min on 8 x 6 threads)",
                # a study in which no policy case converged fixes no first increment: every
                # later local solve needs one (campaign_v3: 72 failed solves once passed)
                validate=[{"file": fc("local_time_study.json"), "kind": "json",
                           "nonempty": ["production_dt0_s"]}])
    loc_c = job("local.cycles", "production", ["scripts/final_closure_local_mesh.py", "--cycles"],
                [fc("local_cycle_study.json")], deps=[loc_t], ncpus=9, workers=9, mem_gb=12,
                backends=LOCAL_SOLVE_BACKENDS,
                env={"FC_POOL_MAX": 9, "LOCAL_THREADS": 1}, est_h=1.6,
                evidence="9 solves x 16 cycles, 5,160-5,370 s each (followup_local.log 1 h 55 min)",
                validate=[{"file": fc("local_cycle_study.json"), "kind": "json"}])
    loc_m = job("local.mesh_study", "production", ["scripts/final_closure_local_mesh.py"],
                [fc("local_mesh_study.json")], deps=[loc_c], ncpus=16, workers=16, mem_gb=24,
                backends=LOCAL_SOLVE_BACKENDS,
                env={"FC_POOL_MAX": 16, "LOCAL_THREADS": 1}, est_h=1.0,
                evidence="33 solves L0-L3, sum 23,330 s, max 2,623 s (followup_local.log 1 h 21 min)",
                validate=[{"file": fc("local_mesh_study.json"), "kind": "json",
                           "keys": ["cases"]}])
    loc_s = {}
    for s, st, est in (("HV_S0", "S0", 1.5), ("HV_S1", "S1", 0.3), ("HV_S2", "S2", 0.2)):
        loc_s[s] = job(f"local.solder.{s}", "production",
                       ["scripts/final_closure_local_solder.py", s], [fc(f"local_solder_{s}.json")],
                       deps=[loc_m] + [prod[(a, st, "A")] for a in ARCHS], ncpus=6,
                       mem_gb=12, est_h=est, backends=LOCAL_SOLVE_BACKENDS,
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
         [fc("bga_count_production.json"), fc("package_network_adopted.json")],
         args=["reclose"],
         deps=[prep["network"], dsum] + [prod[(a, "SDEC", t)] for a in ("Z1", "Z2")
                                        for t in TIERS],
         ncpus=4, env={"FC_WORKERS": 4}, est_h=0.3,
         notes="the 48-V count ADOPTED per architecture (review round 3, the authors' decision "
               "of 2026-11-22): the smallest legal count meeting the feasibility target (2 A "
               "per ball, Kuan et al. 2015) by one rule for every integration, the verified "
               "DC peak x k_eq at the production cases' 48-V currents and the k this "
               "campaign's decoupling chain derives, within the site budget (Z2's ring: at "
               "most 198 per rail) and at most 220 per rail; the network solved there "
               "(package_network_adopted.json), the 1.5-A sensitivity (the count it needs), "
               "Z1's worst-ball RMS of the port model as an idealized bound, and the change of "
               "each production case's BGA feed terms (above 0.1 W: the production cases on "
               "another count are re-run and this job confirms the count)")
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
                                  n_el_k=n_k, ncpus=thr, speed=(0.8 if r == "r31" else 1.0),
                                  rung=r)
    # the production state at the coarse and fine rungs (rung token): r11 is also the smoke test
    for a in D["archs"]:
        for t in TIERS:
            for r, thr, n_k in (("r11", 2, 30), ("r31", 4, 270)):
                argv, out, env = state_spec(a, "SDEC", t, refine=r)
                lad[(a, f"sdec_{t}", r)] = etm_job(
                    f"ladder.{a}.sdec_{t}.{r}", "refinement_ladders", argv, out,
                    deps=[prep["network"], dplace] + (land_deps if a == "Z3" else []),
                    analog=case("Z1", "HV_S0", r), n_el_k=n_k, ncpus=thr, env=env,
                    speed=(0.8 if r == "r31" else 1.0), rung=r,
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
            backends=LOCAL_SOLVE_BACKENDS,
            validate=[{"file": sens(a, v), "kind": "etm", "local": True} for a in archs.split()],
            notes="adds the L0 local solder response at the variant's own critical joint")
    for (a, t) in TIER_BASE:
        etm_job(f"robust.caloric.{a}.{t}", "robustness_map",
                ["scripts/tcpmt_review_variants.py", "caloric", a, t, "HV_SDEC"],
                sens(a, f"plate_caloric_legacy_{t}", "HV_SDEC"),
                deps=[prod[(a, "SDEC", t)], dplace])

    # ------------------------------------------------------------------ mechanics revision
    mech = mech_jobs(prod, vfields, lad, prep, class_b)
    for v in {k[1] for k in rb}:                 # a variant's local response: the production card
        jl = next(j for j in JOBS if j["id"] == f"robust.local.{v}")
        jl["deps"].append(mech["band"])
    # gap closing (MC7, MC8, robustness): the count neighbours' joints, the reference-state
    # critical-joint search, the averaging-band study of the v2 model
    mech["count"] = count_mech_jobs(alt)
    # the design comparison reads the neighbours' joints (each design's own law band)
    jd = next(j for j in JOBS if j["id"] == "derived.design_comparison")
    jd["deps"] += [mech["count"][k] for k in sorted(mech["count"])] + ["derived.uncertainty"]
    mech["s0"] = s0_reference_jobs(prod)
    mech["screen"] = joint_screen_jobs(mech)
    mech["band_study"] = job(
        "mech.band_study", "mech_revision",
        ["bash", "-c", "set -e; cd {repo}; {python} scripts/tcpmt_mech_band_study.py --run; "
         "{python} scripts/tcpmt_mech_band_study.py --summarize"],
        [tr("solder_band_study_v2.json")], deps=[mech["band"]], ncpus=18, workers=18,
        mem_gb=24, est_h=0.4, prefer="pbs", env={"LOCAL_THREADS": 1, "TCPMT_SOLDER_SLOTS": 18},
        evidence="36 solves: 6 joints x 3 bands x L0 / L2 (campaign_v3 local checks: L0 ~60 s, "
                 "L2 176-323 s on 2 threads)",
        validate=[{"file": tr("solder_band_study_v2.json"), "kind": "json",
                   "nonempty": ["joints", "complete"], "fresh": True}],
        notes="MC8: the averaging band (side/8, side/6, side/4, as the round-2 study) of the v2 "
              "local model at the production critical joints, production law at its window")

    # ------------------------------------------------------------------ the rest
    rest(prod, fields, vfields, land, land_rep, fb, hs, rb, loc_t, loc_m, loc_s, lad, prep,
         dsum, mech)
    return {"jobs": JOBS, "static": sorted(STATIC)}


#: the v2 local model's solver jobs: SLOTS concurrent CalculiX solves x THREADS each
#: (tcpmt_mech_submodel: TCPMT_SOLDER_SLOTS, LOCAL_THREADS); a ~500-element joint, 4 cycles,
#: takes 60-110 s on 2 threads (campaign_v3 robustness-map local responses: 77-134 s)
MECH_LOCAL_THREADS = 2
#: the cooling-B mechanics-only rows the merged code supports (scripts/tcpmt_mech_runlist.sh 4c):
#: every mechanics-revision variant on all three integrations, the attach-card variants on Z2,
#: the converter-medium E / CTE range on Z1 and Z2
COOLB_ROWS = {"Z1": ("conv_E80_a4", "conv_E80_a10", "conv_E160_a4", "conv_E160_a10"),
              "Z2": ("attach_stiff", "attach_uf_soft", "attach_uf_stiff", "conv_E80_a4",
                     "conv_E80_a10", "conv_E160_a4", "conv_E160_a10"),
              "Z3": ()}


def mech_jobs(prod, vfields, lad, prep, class_b):
    """TCPMT round 3, the mechanics revision (configs/tcpmt_mech, scripts/tcpmt_mech_*) in the
    PRODUCTION state of the design in force: every job reads the compared cases (implemented
    decoupling, HV_SDEC; Z1/Z2/Z3 x cooling A/B) or their converged fields, so each depends on
    the production job of its case -- a re-run of a production case re-runs what it feeds
    (the records carry the sha1 of their inputs; validators `fresh`).

      (c) site kinematics + interconnect-layer search of each compared case (from its case file),
          the per-layer drivers and their mesh ladder;
      (a) the v2 local model: the self-consistent production law and the law band at each case's
          critical joint (full cut-boundary displacement, ramped loads), in two passes around
      (b) the critical-joint check under the new boundary conditions (every candidate of the
          full-lattice search, monotonicity over the Pareto sites), then the local-model checks
          (mesh, cycles, dwell, ramp, element, attribution chain, fine-pitch joints) and the law
          record;
      (d) reflow / bonding warpage of each integration (production cards and the two Tg-class
          encapsulants), production mesh;
      (e) board size, mounting and clamp, and the encapsulant / BGA-card variants, mechanics only
          on the production fields under cooling A and B, with their local responses;
      (f) the cooling-B mechanics-only robustness rows of the reference (NAME@B on the cooling-B
          fields) and their local responses;
      (g) the robustness judgements of (e) and (f) (they need the production pairs' U95 of the
          campaign's uncertainty record)."""
    out, kin = {}, {}
    T = MECH_LOCAL_THREADS
    for a in ARCHS:
        for t in TIERS:
            lab = f"SDEC_{t}_{a}"
            kin[(a, t)] = post(
                f"mech.kin.{a}.{t}", "mech_revision", "tcpmt_mech_production.py",
                [tr(f"site_kinematics/{lab}.json")], args=["kin", lab],
                deps=[prod[(a, "SDEC", t)]], est_h=0.02,
                evidence="reads one case file (seconds)",
                validate=[{"file": tr(f"site_kinematics/{lab}.json"), "kind": "json",
                           "keys": ["interconnects", "site_coverage"], "fresh": True}],
                notes="the case's stored interconnect search (every layer; BGA candidates with "
                      "their full cut-boundary kinematics) and its site coverage; refuses a case "
                      "whose BGA counts are not in force (tcpmt_mech_production.input_issue)")
    kins = [kin[k] for k in sorted(kin)]
    out["drivers"] = post("mech.interconnects", "mech_revision", "tcpmt_mech_production.py",
                          [tr("interconnect_drivers.json")], args=["drivers"], deps=kins,
                          validate=[{"file": tr("interconnect_drivers.json"), "kind": "json",
                                     "nonempty": ["cases"], "fresh": True}],
                          notes="finding 4: driver and layer shear strain of every interconnect "
                                "layer (Z1 microbumps, Z2 Cu-pillar attach, Z3 SAC attach, BGA); "
                                "finding 9: the du split of the BGA driver")
    out["ladder"] = post("mech.interconnect_ladder", "mech_revision", "tcpmt_mech_production.py",
                         [tr("interconnect_mesh_ladder.json")], args=["ladder"],
                         deps=kins + [lad[(a, f"sdec_{t}", r)] for a in ARCHS for t in TIERS
                                      for r in ("r11", "r31")],
                         validate=[{"file": tr("interconnect_mesh_ladder.json"), "kind": "json",
                                    "nonempty": ["cases"], "fresh": True}],
                         notes="per-layer drivers on the production-state rungs r11 / r21 / r31")
    sv = {"LOCAL_THREADS": T}
    labs = [f"SDEC_{t}_{a}" for t in TIERS for a in ARCHS]
    lat = post("mech.lattice", "mech_revision", "tcpmt_mech_production.py",
               [tr(f"site_kinematics/lattice/{x}.json") for x in labs], args=["lattice"],
               deps=kins, est_h=0.05, mem_gb=6,
               evidence="campaign_v3: 11 s per case (production mesh build + two .frd reads + "
                        "the site fits at 528-1369 lattice sites)",
               validate=[{"file": tr(f"site_kinematics/lattice/{x}.json"), "kind": "json",
                          "nonempty": ["sites"], "fresh": True} for x in labs],
               notes="finding 2: the full cut-boundary kinematics of EVERY BGA lattice site of "
                     "the compared cases from their converged structural / thermal fields (the "
                     "case files keep only the search's candidates); the recomputed candidates "
                     "must reproduce the stored ones")
    band_v = [{"file": tr("solder_law_cards.json"), "kind": "json", "keys": ["laws"]}]
    w1 = job("mech.lawband.window", "mech_revision", ["scripts/tcpmt_mech_law_band.py", "--run"],
             [tr("solder_law_cards.json"), tr("solder_law_band.json")], deps=kins,
             ncpus=6 * T, workers=6, mem_gb=12, est_h=0.8, prefer="pbs", env={**sv, "TCPMT_SOLDER_SLOTS": 6},
             evidence="v2 law band of the merged branch: 6 joints x 2 Garofalo laws x <= 6 "
                      "window iterations + 1 measured-Norton pass, 3 slots x 2 threads, ~20 min",
             validate=band_v + [{"file": tr("solder_law_band.json"), "kind": "json",
                                 "nonempty": ["band"], "fresh": True}],
             notes="pass 1: every law's Norton-surrogate window iterated to self-consistency at "
                   "the maximum-du joints of the six compared cases (production law: "
                   "configs/tcpmt_mech solder.production_law; the band over solder.band_laws)")
    import yaml
    _sc = yaml.safe_load((REPO / "configs" / "tcpmt_mech" / "mechanics_revision.yaml")
                         .read_text())["solder"]
    crits = {}
    for law in [_sc["production_law"]] + [x for x in _sc["band_laws"]
                                          if x != _sc["production_law"]]:
        is_prod = law == _sc["production_law"]
        f = tr("solder_critical_v2.json" if is_prod else f"solder_critical_v2_{law}.json")
        la = "" if is_prod else f" --law {law}"
        # placement: the production law and one band law on the local host's 35-core cap one
        # after the other (32 one-thread slots), the other band law on califone (20 slots)
        where, slots = ("local", 32) if is_prod else {
            "xa_measured_norton": ("local", 32)}.get(law, ("pbs", 20))
        crits[law] = job(
            "mech.critical" + ("" if is_prod else f".{law}"), "mech_revision",
            ["bash", "-c", "set -e; cd {repo}; {python} scripts/tcpmt_mech_critical.py --run"
             + la + "; {python} scripts/tcpmt_mech_critical.py --summarize" + la],
            [f], deps=[w1, lat], ncpus=slots, workers=slots, mem_gb=32, est_h=1.0,
            prefer=where, backends=(where,),
            env={"LOCAL_THREADS": 1, "TCPMT_SOLDER_SLOTS": slots},
            evidence="~1000 sites over the six compared cases (the 669 base candidates + the "
                     "lattice front in the screening features + the bound's additions) x ~65 s "
                     "per site on ONE thread (ccx 49 s at 1 thread vs 46 s at 2, identical "
                     "result: one thread per slot)",
            validate=[{"file": f, "kind": "json", "nonempty": ["cases", "all_closed"],
                       "fresh": True}],
            notes=f"finding 2 under law {law}: the maximum response over the BGA lattice of every "
                  "compared case -- the base candidates (top 30 by |du_xy|, tilt, eps_z and "
                  "deforming du, the (|du_xy|, T) Pareto front, the corners), the lattice's "
                  "Pareto front in (deforming du, |du_z|, T) and every site whose dominance bound "
                  "(1 + margin) R exceeds the maximum, until none does (configs/tcpmt_mech "
                  "local.critical); the law at its stored window")
    crit = crits[_sc["production_law"]]
    band = job("mech.lawband", "mech_revision", ["scripts/tcpmt_mech_law_band.py", "--run"],
               [tr("solder_law_cards.json"), tr("solder_law_band.json")],
               deps=sorted(crits.values()),
               ncpus=6 * T, workers=6, mem_gb=12, est_h=0.5,
               prefer="pbs", env={**sv, "TCPMT_SOLDER_SLOTS": 6},
               evidence="as pass 1, starting from its converged windows; an unchanged law "
                        "converges at once (its previous responses at the same card and sites)",
               validate=band_v + [{"file": tr("solder_law_band.json"), "kind": "json",
                                   "keys": ["critical_check"],
                                   "nonempty": ["band", "all_verified"], "fresh": True}],
               notes="pass 2: under every law its own maximum-response joint (that law's "
                     "critical-joint check), the window re-iterated there and the maximum "
                     "re-verified at the final card (the production joint response and its law "
                     "band: the reported uncertainty of the joint response)")
    out["band"] = band
    out["critical"] = crit
    out["checks"] = job(
        "mech.local_checks", "mech_revision",
        ["bash", "-c", "set -e; cd {repo}; {python} scripts/tcpmt_mech_local_checks.py --run; "
         "{python} scripts/tcpmt_mech_local_checks.py --summarize"],
        [tr("solder_local_checks.json")], deps=[band], ncpus=10 * T, workers=10, mem_gb=24,
        est_h=1.0, prefer="pbs", env={**sv, "TCPMT_SOLDER_SLOTS": 10},
        evidence="~90 solves (chain 6 x 6, dwell/ramp 3 x 6, element 2, mesh L1-L3 x 6, 8 cycles "
                 "x 6, fine-pitch joints 12-18); L3 and 8-cycle solves 3-10x an L0 one",
        validate=[{"file": tr("solder_local_checks.json"), "kind": "json",
                   "nonempty": ["groups"], "fresh": True}],
        notes="the numerical U of every joint (own L0 -> L3 and 4 -> 8 cycle changes), the "
              "dwell / ramp / element sensitivities, the round-2 -> v2 attribution chain and the "
              "critical fine-pitch joints (finding 4) with their own geometry")
    out["record"] = post("mech.law_record", "mech_revision", "tcpmt_mech_laws.py",
                         [tr("solder_law_record.json")], args=["--record"], deps=[band],
                         notes="per law: alloy, calibration window, visited window, extrapolation, "
                               "surrogate error (Table S10)")
    # (d) reflow / bonding warpage, production mesh
    rf = []
    for a in ARCHS:
        for v in (None,) + tuple(mech_revision_variants()[:2]):
            sfx = f"_{v}" if v else ""
            rf.append(job(f"mech.reflow.{a}" + (f".{v}" if v else ""), "mech_revision",
                          ["scripts/tcpmt_mech_reflow.py", "run", a, "--refine", "21"]
                          + (["--encap", v] if v else []),
                          [tr(f"reflow/{a}_r21{sfx}.json")],
                          deps=[prep["cards"], prep["tier_order"]], ncpus=2, mem_gb=8,
                          est_h=0.3 if v else 0.2, prefer="pbs", env={"FC_THREADS": 2},
                          evidence="merged branch, coarse r11: 30-150 s per part; r21 ~3x",
                          validate=[{"file": tr(f"reflow/{a}_r21{sfx}.json"), "kind": "json",
                                     "keys": ["checks"]}],
                          notes="finding 5: isothermal warpage of the unmounted package at the "
                                "SAC305 reflow peak / solidus against JEP95 / SPP-024, and the "
                                "fine-pitch joint's gap at its bonding temperature"
                                + (f"; encapsulant {v} (Tg class)" if v else "")))
    out["reflow"] = post("mech.reflow_summary", "mech_revision", "tcpmt_mech_reflow.py",
                         [tr("reflow_warpage.json")], args=["summarize"], deps=rf)
    # (e) board size / mounting / clamp, mechanics only on the production fields
    bd = []
    for a in ARCHS:
        for t in TIERS:
            f = tr(f"board_study/SDEC_{t}_{a}.json")
            bd.append(job(f"mech.board.{a}.{t}", "mech_revision",
                          ["scripts/tcpmt_mech_board.py", "state", a, t, "--state", "SDEC"],
                          [f], deps=[prod[(a, "SDEC", t)]], ncpus=8, workers=4,
                          mem_gb=40, est_h=1.0, prefer="pbs", env={"FC_POOL_MAX": 4, "FC_THREADS": 2},
                          evidence="11 structural solves on the production mesh (coupon 112 kel, "
                                   "larger board ~1.4x): campaign_v3 mechanics-only 340-2000 s "
                                   "on 1 thread; 4 at a time on 2 threads",
                          validate=[{"file": f, "kind": "json",
                                     "nonempty": ["mechanics", "all_solves_ok"], "fresh": True}],
                          notes="coupon: free (reproduces the case), screws, pinned screws, edge, "
                                "the 200-N clamp at the screws (hot / clamp only) and on a "
                                "backplate; a 3x board with its ring at the coupon edge "
                                "temperature or at 25 C (bounds), free, screws, clamp"))
    # the larger board's own temperature field (one E-T of the case on the 3x board, coarse
    # rung) against the case's coupon rung: where the ring sits between the two bounds
    for a in ARCHS:
        for t in TIERS:
            f = tr(f"board_study/SDEC_{t}_{a}_x3_r11.json")
            bd.append(job(f"mech.board_et.{a}.{t}", "mech_revision",
                          ["scripts/tcpmt_mech_board.py", "state-et", a, t, "--state", "SDEC"],
                          [f], deps=[prod[(a, "SDEC", t)], lad[(a, f"sdec_{t}", "r11")]],
                          ncpus=2, mem_gb=8, est_h=0.4, prefer="pbs", env={"FC_THREADS": 2},
                          evidence="the case's r11 rung: E-T 250-500 s + mechanics ~120 s; the "
                                   "3x board adds a coarse ring (+7 % elements at r21)",
                          validate=[{"file": f, "kind": "json",
                                     "nonempty": ["mechanics", "all_solves_ok"], "fresh": True}],
                          notes="the case's state hooks and cooling base, the 3x board, E-T "
                                "then free / screws / clamp mechanics (finding 6)"))
    out["board"] = job("mech.board_summary", "mech_revision",
                       ["scripts/tcpmt_mech_board.py", "state-summarize", "--state", "SDEC",
                        "--local"], [tr("board_study_SDEC.json")], deps=bd + [band],
                       ncpus=6 * T, workers=6, mem_gb=8, est_h=0.2,
                       env={**sv, "TCPMT_SOLDER_SLOTS": 6},
                       validate=[{"file": tr("board_study_SDEC.json"), "kind": "json",
                                  "nonempty": ["cases"], "fresh": True}],
                       notes="every board / mounting / clamp solve against its case, and the "
                             "clamp in the local response (v2, production card)")
    # (e) encapsulant Tg classes and the local-card BGA layer, production fields A and B
    st_jobs, st_loc = [], []
    for v in mech_revision_variants():
        vj = []
        for a in ARCHS:
            outs = [f"final_closure/sensitivity/etm_{a}_HV_SDEC__{v}.json",
                    f"final_closure/sensitivity/etm_{a}_HV_SDEC__{v}__B.json"]
            vj.append(job(f"mech.state.{a}.{v}", "mech_revision",
                          ["scripts/final_closure_sensitivity.py", "--state", "SDEC", f"{v}:{a}",
                           f"{v}@B:{a}"], outs,
                          deps=[prod[(a, "SDEC", "A")], prod[(a, "SDEC", "B")]], ncpus=4,
                          workers=2, mem_gb=16, est_h=0.6, prefer="pbs",
                          env={"FC_POOL_MAX": 2, "FC_THREADS": 2},
                          evidence="2 mechanics-only solves (campaign_v3: 340-2000 s on 1 "
                                   "thread)",
                          validate=[{"file": o, "kind": "etm", "fresh": True} for o in outs],
                          notes="mechanics only on the production fields (cooling A and B)"))
        st_jobs += vj
        outs = [f"final_closure/sensitivity/etm_{a}_HV_SDEC__{v}{x}.json" for a in ARCHS
                for x in ("", "__B")]
        st_loc.append(job(f"mech.state_local.{v}", "mech_revision",
                          ["scripts/final_closure_sensitivity.py", "--state", "SDEC", "--local",
                           v, f"{v}@B"], outs, deps=vj + [band], ncpus=6 * T, workers=6,
                          mem_gb=8, est_h=0.1, env={"LOCAL_THREADS": T, "FC_POOL_MAX": 6},
                          backends=LOCAL_SOLVE_BACKENDS + ("pbs",),
                          validate=[{"file": o, "kind": "etm", "local": True} for o in outs],
                          notes="the v2 local response at each variant's own critical joint"))
    out["state"] = st_jobs + st_loc
    # (f) the cooling-B mechanics-only rows of the robustness map (reference, cooling-B fields)
    cb, cbl = [], []
    revs = tuple(mech_revision_variants())
    for a in ARCHS:
        vs = revs + COOLB_ROWS[a]
        outs = [sens(a, f"{v}__B") for v in vs]
        j = job(f"robust.coolB.{a}", "mech_revision",
                ["scripts/final_closure_sensitivity.py"] + [f"{v}@B:{a}" for v in vs], outs,
                deps=[prod[(a, "S0", "B")], vfields[(a, "B")]], ncpus=8, workers=4,
                mem_gb=32, est_h=0.3 * len(vs) / 4 + 0.3, prefer="pbs",
                env={"FC_POOL_MAX": 4, "FC_THREADS": 2},
                evidence=f"{len(vs)} mechanics-only solves on the cooling-B field, 4 at a time",
                validate=[{"file": o, "kind": "etm", "fresh": True} for o in outs],
                notes="finding 8: NAME@B, mechanics only on the cooling-B field of the reference "
                      "(configs/tcpmt_mech cooling_B_base)")
        cb.append(j)
        cbl.append(job(f"robust.coolB_local.{a}", "mech_revision",
                       ["scripts/final_closure_sensitivity.py", "--local"]
                       + [f"{v}@B:{a}" for v in vs], outs, deps=[j, band], ncpus=4 * T,
                       workers=4,
                       mem_gb=8, est_h=0.1, env={"LOCAL_THREADS": T, "FC_POOL_MAX": 4},
                       backends=LOCAL_SOLVE_BACKENDS + ("pbs",),
                       validate=[{"file": o, "kind": "etm", "local": True} for o in outs]))
    out["coolB"] = cb + cbl
    return out



def _laws():
    """(production law, [production law, other laws of the band]) of configs/tcpmt_mech."""
    import yaml
    sc = yaml.safe_load((REPO / "configs" / "tcpmt_mech" / "mechanics_revision.yaml")
                        .read_text())["solder"]
    p = sc["production_law"]
    return p, [p] + [x for x in sc["band_laws"] if x != p]


def count_mech_jobs(alt):
    """MC7: the count neighbours m25 and m49 (their Z1 production cases under cooling A and B,
    design subroots) through the SAME mechanics as the production cases: site kinematics and
    full-lattice kinematics from their case files and converged fields, the law band's window
    iteration on their own joints (pass 1), the dominance-bounded maximum over the BGA lattice
    under every law of the band, and pass 2 at each law's own maximum (re-verified at its
    final card). TCPMT_LOCAL_ARCHS=Z1: the subroots hold no Z2 / Z3 case."""
    prod_law, laws = _laws()
    T = MECH_LOCAL_THREADS
    out = {}
    for dk in ("m25", "m49"):
        sub = f"designs/{dk}/"
        env0 = {"TCPMT_LOCAL_ARCHS": "Z1"}
        kins = []
        for t in TIERS:
            lab = f"SDEC_{t}_Z1"
            f = sub + tr(f"site_kinematics/{lab}.json")
            kins.append(post(f"{dk}.mech.kin.Z1.{t}", "count_study", "tcpmt_mech_production.py",
                             [f], args=["kin", lab], deps=[alt[(dk, "Z1", t)]], design=dk,
                             env=env0, est_h=0.02, evidence="reads one case file (seconds)",
                             validate=[{"file": f, "kind": "json",
                                        "keys": ["interconnects", "site_coverage"],
                                        "fresh": True}]))
        labs = [f"SDEC_{t}_Z1" for t in TIERS]
        lat = post(f"{dk}.mech.lattice", "count_study", "tcpmt_mech_production.py",
                   [sub + tr(f"site_kinematics/lattice/{x}.json") for x in labs],
                   args=["lattice"], deps=kins, design=dk, env=env0, est_h=0.05, mem_gb=8,
                   evidence="campaign_v3: 11 s per case + the mesh build",
                   validate=[{"file": sub + tr(f"site_kinematics/lattice/{x}.json"),
                              "kind": "json", "nonempty": ["sites"], "fresh": True}
                             for x in labs])
        band_v = [{"file": sub + tr("solder_law_cards.json"), "kind": "json", "keys": ["laws"]}]
        w1 = job(f"{dk}.mech.lawband.window", "count_study",
                 ["scripts/tcpmt_mech_law_band.py", "--run"],
                 [sub + tr("solder_law_cards.json"), sub + tr("solder_law_band.json")],
                 deps=kins, ncpus=2 * T, workers=2, mem_gb=8, est_h=0.5, design=dk,
                 env={**env0, "LOCAL_THREADS": T, "TCPMT_SOLDER_SLOTS": 2},
                 evidence="2 joints x 3 laws x <= 6 window iterations, ~60 s per solve",
                 validate=band_v + [{"file": sub + tr("solder_law_band.json"), "kind": "json",
                                     "nonempty": ["band"], "fresh": True}],
                 notes="pass 1 on the design's own joints (maximum-du sites)")
        crits = []
        for law in laws:
            is_prod = law == prod_law
            f = sub + tr("solder_critical_v2.json" if is_prod
                         else f"solder_critical_v2_{law}.json")
            la = "" if is_prod else f" --law {law}"
            crits.append(job(
                f"{dk}.mech.critical" + ("" if is_prod else f".{law}"), "count_study",
                ["bash", "-c", "set -e; cd {repo}; {python} scripts/tcpmt_mech_critical.py --run"
                 + la + "; {python} scripts/tcpmt_mech_critical.py --summarize" + la],
                [f], deps=[w1, lat], ncpus=16, workers=16, mem_gb=16, est_h=1.0,
                prefer="pbs", design=dk,
                env={**env0, "LOCAL_THREADS": 1, "TCPMT_SOLDER_SLOTS": 16},
                evidence="~350 sites over the two cases x ~65 s on one thread",
                validate=[{"file": f, "kind": "json", "nonempty": ["cases", "all_closed"],
                           "fresh": True}],
                notes=f"the maximum response over the BGA lattice under law {law} "
                      "(dominance-bounded search of tcpmt_mech_critical)"))
        out[dk] = job(f"{dk}.mech.lawband", "count_study",
                      ["scripts/tcpmt_mech_law_band.py", "--run"],
                      [sub + tr("solder_law_cards.json"), sub + tr("solder_law_band.json")],
                      deps=crits, ncpus=2 * T, workers=2, mem_gb=8, est_h=0.3, design=dk,
                      prefer="pbs", env={**env0, "LOCAL_THREADS": T, "TCPMT_SOLDER_SLOTS": 2},
                      validate=band_v + [{"file": sub + tr("solder_law_band.json"),
                                          "kind": "json", "keys": ["critical_check"],
                                          "nonempty": ["band", "all_verified"],
                                          "fresh": True}],
                      notes="pass 2: every law at its own maximum-response joint")
    return out


def s0_reference_jobs(prod):
    """The robustness map's mechanics-only variants are solved on the ideal-decoupling
    reference (S0) fields under cooling A and B; their joint-response screen needs each
    reference case's worst sites. The same dominance-bounded search as the production state,
    production law at its converged window (the production card), TCPMT_LOCAL_STATE=S0."""
    T = MECH_LOCAL_THREADS
    labs = [f"S0_{t}_{a}" for t in TIERS for a in ARCHS]
    kin = post("mech.kin_S0", "mech_revision", "tcpmt_mech_production.py",
               [tr(f"site_kinematics/{x}.json") for x in labs], args=["kin", "--state", "S0"],
               deps=[prod[(a, "S0", t)] for a in ARCHS for t in TIERS], est_h=0.05,
               validate=[{"file": tr(f"site_kinematics/{x}.json"), "kind": "json",
                          "keys": ["interconnects", "site_coverage"], "fresh": True}
                         for x in labs])
    lat = post("mech.lattice_S0", "mech_revision", "tcpmt_mech_production.py",
               [tr(f"site_kinematics/lattice/{x}.json") for x in labs],
               args=["lattice", "--state", "S0"], deps=[kin], est_h=0.1, mem_gb=8,
               validate=[{"file": tr(f"site_kinematics/lattice/{x}.json"), "kind": "json",
                          "nonempty": ["sites"], "fresh": True} for x in labs])
    f = tr("solder_critical_v2_S0.json")
    return job("mech.critical_S0", "mech_revision",
               ["bash", "-c", "set -e; cd {repo}; {python} scripts/tcpmt_mech_critical.py --run; "
                "{python} scripts/tcpmt_mech_critical.py --summarize"],
               [f], deps=[lat, "mech.lawband"], ncpus=32, workers=32, mem_gb=32, est_h=1.0,
               prefer="pbs", backends=("pbs", "local"),
               env={"TCPMT_LOCAL_STATE": "S0", "LOCAL_THREADS": 1, "TCPMT_SOLDER_SLOTS": 32},
               evidence="~1000 sites over the six reference cases x ~65 s on one thread",
               validate=[{"file": f, "kind": "json", "nonempty": ["cases", "all_closed"],
                          "fresh": True}],
               notes="the maximum response over the BGA lattice of every reference case "
                     "(S0: ideal decoupling) under the production law at the production card")


#: the full searches that validate the joint-response screen (tcpmt_mech_joint_screen.VALIDATE)
SCREEN_VALIDATE = ("SDEC_A_Z2__board_screws_pinned", "SDEC_A_Z1__encap_emc_lowcte",
                   "S0_A_Z2__conv_E160_a10", "S0_A_Z2__conv_k_tenth")


def joint_screen_jobs(mech):
    """The joint response of every mechanical robustness variant (tcpmt_mech_joint_screen):
    the clamp-only states the clamps need as their cold half-cycle, every variant's full
    lattice kinematics recomputed from its converged structural field (verified against its
    stored candidates), the screen at the reference case's K worst sites (production law),
    full dominance-bounded searches on variants of different kinds, and the summary."""
    T = MECH_LOCAL_THREADS
    cold = []
    for a in ARCHS:
        for t in TIERS:
            f = tr(f"board_study/SDEC_{t}_{a}_cold.json")
            cold.append(job(f"mech.board_cold.{a}.{t}", "mech_revision",
                            ["scripts/tcpmt_mech_board.py", "state", a, t, "--state", "SDEC",
                             "--cold"], [f], deps=[f"mech.board.{a}.{t}"], ncpus=4, workers=2,
                            mem_gb=40, est_h=0.6, prefer="pbs",
                            env={"FC_POOL_MAX": 2, "FC_THREADS": 2},
                            evidence="2 structural solves (coupon, 3x board) as mech.board",
                            validate=[{"file": f, "kind": "json",
                                       "nonempty": ["mechanics", "all_solves_ok"],
                                       "fresh": True}],
                            notes="the clamp-only states of the backplate clamp and of the "
                                  "3x board's screw clamp (no thermal load)"))
    producers = sorted(j["id"] for j in JOBS if j["id"].startswith((
        "robust.", "mech.state.", "hotspot.", "feedback.", "mech.board.")) and
        not j["id"].startswith(("robust.local.", "robust.coolB_local.", "robust.caloric.")))
    lat = job("mech.screen.lattice", "mech_revision",
              ["scripts/tcpmt_mech_joint_screen.py", "lattice"],
              [tr("robustness_joint_lattice.json")],
              deps=producers + ["mech.lattice", "mech.lattice_S0"], ncpus=8, workers=8,
              mem_gb=48, est_h=0.5, prefer="pbs", env={"FC_POOL_MAX": 8},
              evidence="~10 s per variant (mesh build, two .frd reads, 528-1369 site fits)",
              validate=[{"file": tr("robustness_joint_lattice.json"), "kind": "json",
                         "keys": ["errors"]}],
              notes="every variant's full-lattice kinematics from its converged structural "
                    "field on its own mesh, verified against its stored candidates")
    latc = job("mech.screen.lattice_cold", "mech_revision",
               ["scripts/tcpmt_mech_joint_screen.py", "lattice", "--cold"],
               [tr("robustness_joint_lattice_cold.json")], deps=cold + [lat], ncpus=4,
               workers=4, mem_gb=24, est_h=0.2, prefer="pbs", env={"FC_POOL_MAX": 4},
               validate=[{"file": tr("robustness_joint_lattice_cold.json"), "kind": "json",
                          "keys": ["errors"]}])
    # califone's cpu_only queue runs at most 56 cpus per user at a time: two halves of 24
    env = {"LOCAL_THREADS": 1, "TCPMT_SOLDER_SLOTS": 24}
    runs_a = []
    for half, groups in (("a1", "S0_A,S0_B"),
                         ("a2", "SDEC_new_A,SDEC_new_B,SDEC_mech_A,SDEC_mech_B,board_A,board_B")):
        runs_a.append(job(
            f"mech.screen.run_{half}", "mech_revision",
            ["scripts/tcpmt_mech_joint_screen.py", "run", "--log", f"run_{half}", "--groups",
             groups], [tr(f"robustness_joint_runs/run_{half}.json")],
            deps=[lat, mech["critical"], mech["s0"]], ncpus=24, workers=24, mem_gb=32,
            est_h=1.2, prefer="pbs", backends=("pbs", "local"), env=env,
            evidence="~1700 solves (the variants of the groups x K = 20 sites) x ~30 s on one "
                     "thread (califone)",
            notes=f"the variants of {groups} at their reference case's K worst sites "
                  "(production law); the clamps wait for their clamp-only lattices (run_b)"))
    # a helper from the other end of the production-state task list (the board solves are the
    # slowest): solve() skips every record the forward job has already written
    runs_a.append(job(
        "mech.screen.run_a2r", "mech_revision",
        ["scripts/tcpmt_mech_joint_screen.py", "run", "--log", "run_a2r", "--groups",
         "SDEC_new_A,SDEC_new_B,SDEC_mech_A,SDEC_mech_B,board_A,board_B", "--reverse"],
        [tr("robustness_joint_runs/run_a2r.json")],
        deps=[lat, mech["critical"], mech["s0"]], ncpus=24, workers=24, mem_gb=32, est_h=0.6,
        prefer="pbs", backends=("pbs", "local"), env=env,
        notes="the same variants as run_a2, in reverse order"))
    run_a = runs_a[0]
    run_b = job("mech.screen.run_b", "mech_revision",
                ["scripts/tcpmt_mech_joint_screen.py", "run", "--log", "run_b"],
                [tr("robustness_joint_runs/run_b.json")], deps=runs_a + [latc], ncpus=32,
                workers=32, mem_gb=32, est_h=0.3, prefer="pbs", backends=("pbs", "local"),
                env={"LOCAL_THREADS": 1, "TCPMT_SOLDER_SLOTS": 32},
                evidence="the clamps' solves (36 variants x 20 sites at most)")
    # the validation rule (tcpmt_mech_joint_screen.pick): in each kind of mechanical variant,
    # the variant whose screened maximum lies deepest among the K sites gets a full search
    pk = post("mech.screen.pick", "mech_revision", "tcpmt_mech_joint_screen.py",
              [tr("robustness_joint_validation_picks.json")], args=["pick"],
              deps=[run_b, "mech.screen.summarize_pre"], est_h=0.02)
    post("mech.screen.summarize_pre", "mech_revision", "tcpmt_mech_joint_screen.py",
         [tr("robustness_joint.json")], args=["summarize"], deps=[run_b, "derived.uncertainty"],
         est_h=0.05, validate=[{"file": tr("robustness_joint.json"), "kind": "json",
                                "nonempty": ["variants"]}],
         notes="the screen's summary before the validation (the picks read it)")
    vals = []
    for slug in ("mounting", "encapsulant", "mechcard", "thermal"):
        f = tr(f"robustness_joint_validation_by_kind/{slug}.json")
        vals.append(job(f"mech.screen.validate.{slug}", "mech_revision",
                        ["scripts/tcpmt_mech_joint_screen.py", "validate", "--kind", slug], [f],
                        deps=[pk], ncpus=16, workers=16, mem_gb=24, est_h=1.0,
                        prefer="pbs", backends=("pbs", "local"),
                        env={"LOCAL_THREADS": 1, "TCPMT_SOLDER_SLOTS": 16},
                        evidence="a dominance-bounded search: ~150-350 sites x ~60 s",
                        validate=[{"file": f, "kind": "json", "nonempty": ["closed"]}],
                        notes="full dominance-bounded search on the variant's own lattice "
                              "(production law): is its worst site inside the reference's "
                              "top K?"))
    # escalation: every variant whose screened maximum lies beyond the first K/4 sites of its
    # reference is searched in full (tcpmt_mech_joint_screen.escalate), in three parallel parts
    esc = []
    for part in range(3):
        f = tr(f"robustness_joint_runs/escalate_{part}.json")
        esc.append(job(f"mech.screen.escalate.{part}", "mech_revision",
                       ["scripts/tcpmt_mech_joint_screen.py", "escalate", "--part", str(part),
                        "--nparts", "3"], [f], deps=[pk] + vals, ncpus=16, workers=16,
                       mem_gb=24, est_h=1.0, prefer="pbs", backends=("pbs", "local"),
                       env={"LOCAL_THREADS": 1, "TCPMT_SOLDER_SLOTS": 16},
                       evidence="~8 dominance-bounded searches of ~100-300 sites each",
                       validate=[{"file": f, "kind": "json", "nonempty": ["keys"]}],
                       notes="full searches of the variants whose screened maximum lies deep "
                             "among the K sites (a validated variant reuses its search)"))
    return post("mech.screen.summary", "mech_revision", "tcpmt_mech_joint_screen.py",
                [tr("robustness_joint.json")], args=["summarize"],
                deps=[run_b, "derived.uncertainty"] + vals + esc, est_h=0.05,
                validate=[{"file": tr("robustness_joint.json"), "kind": "json",
                           "nonempty": ["variants", "complete"], "fresh": True}],
                notes="per variant: the screened response, its site and rank among the K, the "
                      "change against its reference, the orderings under the rule; the "
                      "validation")


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
         dsum, mech=None):
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
    p2sum = post("derived.dse_phase2_summary", "derived", "tcpmt_dse_phase2_summary.py",
         [tr("dse_phase2_summary.json")],
         deps=[dse["etm35_p2_t4"], dse["etm35_p2_t5"], dse["etm35_p2_tinf"]],
         env={"HVR_DSE_ENGINE": "{scratch}/dse_engine"},
         notes="the screen the design record entries reproduce (configs/design_points.yaml); "
               "reads the sweeps under the root, records the md5 of the campaign's engine")
    # MC7: the screen on a nested 16x finer f_sw grid under the full rules (private engine copy)
    job("dse.fsw785_t4", "dse_sweeps",
        ["scripts/tcpmt_dse_fsw_grid.py", "all", "--npts", "785", "--workers", "27"],
        [tr("dse_fsw_fine.json"), "tcpmt_revision/dse_j35/data/case_D_f785_t4.csv"],
        deps=[eng, dse["etm35_p2_t4"]], ncpus=27, workers=27, mem_gb=32, est_h=0.8,
        prefer="pbs", env={"HVR_DSE_ENGINE": "{scratch}/dse_engine"},
        evidence="dse.etm35_p2_t4: 3.6-185 s per count at 50 points (both sizing modes); the "
                 "discrete library alone at 785 points, one process per count",
        validate=[{"file": tr("dse_fsw_fine.json"), "kind": "json",
                   "nonempty": ["counts", "optimum_fine"]},
                  {"file": "tcpmt_revision/dse_j35/data/case_D_f785_t4.csv", "kind": "csv"}],
        notes="the 50-point grid split 16x (785 points, nested), case D only; the private copy "
              "first reproduces the committed screen at 50 points (check stage)")

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
    # the omitted converter terms on the compared cases and on the round-3 screens (the case-D
    # screen under the corrected capacitor rule, the phase-2 sweeps at each tier limit, the
    # enumeration the screen was picked from); the feasibility stage reads its high bundle
    omit = post("derived.omitted_losses", "derived", "tcpmt_omitted_losses.py",
                [tr("omitted_losses.json")],
                deps=[dse["etm35_caprule_full"], dse["etm35_p2_t4"], dse["etm35_p2_t5"],
                      dse["etm35_p2_tinf"], p2sum] + tier_cases,
                env={"HVR_DSE_ENGINE": "{scratch}/dse_engine"},
                est_h=0.1, notes="the f_sw-grid section needs tcpmt_omitted_losses_fsw_grid.py, "
                "which cannot run at HEAD (engine md5 check, stale patch patterns): written "
                "available:false; the DSE routing score of the re-selection check imports "
                "paper_routing.py from outside the repository (the engine snapshot's record)")
    # the platform's Z2 BGA-ring feed is at the re-closure's adopted count
    plat = post("derived.platform", "derived", "tcpmt_platform.py",
                [tr("platform_inclusive.json")],
                deps=[cool, land_rep, "derived.bga_reclose"] + tier_cases)
    # the feasibility stage reads the Z2 BGA-ring feed of the platform accounting and the
    # re-closure's adopted counts (package_network_adopted.json, bga_count_production.json)
    post("derived.feasibility", "derived", "tcpmt_feasibility.py", [tr("feasibility.json")],
         deps=flds + [fields[("Z1", "HV_S1")], fields[("Z2", "HV_S1")]] + tier_cases +
         [prod[(a, "S1", t)] for a in ARCHS for t in TIERS] + [omit, plat,
                                                                "derived.bga_reclose"],
         est_h=0.15, mem_gb=8, evidence="mesh builds + frd reads (minutes)")
    solder = solder_jobs(prod, land, loc_t, loc_m, mech)
    # the joint term: the v2 law band and its checks (the production local model; the legacy
    # solder studies stay a dependency for TCPMT_LOCAL_HARNESS=legacy)
    unc = post("derived.uncertainty", "derived", "tcpmt_uncertainty.py",
               [tr("uncertainty.json"), "manuscript_v2/tab_uncertainty.tex"],
               deps=[lad[k] for k in lad] + tier_cases + [loc_m, solder["studies"],
                                                          solder["z3land"]]
               + ([mech["band"], mech["checks"]] if mech else []))
    if mech:
        # (g) the robustness judgements need the production pairs' U95 of the uncertainty record
        post("mech.judge_state", "derived", "tcpmt_mech_variants.py",
             [tr("robustness_mech_SDEC.json")], args=["judge-state", "SDEC"],
             deps=mech["state"] + [unc],
             validate=[{"file": tr("robustness_mech_SDEC.json"), "kind": "json",
                        "nonempty": ["variants"], "fresh": True}],
             notes="the encapsulant / BGA-card variants on the production fields against their "
                   "own cases; orderings under the rule with the production pairs' U95")
        post("mech.judgeB", "derived", "tcpmt_mech_variants.py", [tr("robustness_B.json")],
             args=["judgeB"], deps=mech["coolB"] + [unc],
             validate=[{"file": tr("robustness_B.json"), "kind": "json",
                        "nonempty": ["variants"], "fresh": True}],
             notes="finding 8: the cooling-B rows of the robustness map (NAME@B against the "
                   "cooling-B base)")

    # ------------------------------------------------------------ manuscript
    manuscript()


def solder_jobs(prod, land, loc_t, loc_m, mech=None):
    deps = [prod[(a, s, t)] for a in ARCHS for s in ("S0", "SDEC") for t in TIERS] + \
        [prod[("Z1", "S1", "A")], prod[("Z2", "S1", "A")], loc_t, loc_m]
    runs = "; ".join("{python} scripts/tcpmt_solder_%s.py --run" % x
                     for x in ("critical", "cycles", "band", "units_check", "constitutive"))
    st = job("solder.studies", "solder_submodels",
             ["bash", "-c", "set -e; cd {repo}; " + runs + "; {python} scripts/tcpmt_solder_collect.py"],
             [tr("solder_studies.json")], deps=deps, ncpus=12, workers=6, mem_gb=24, est_h=2.5,
             backends=LOCAL_SOLVE_BACKENDS,
             env={"LOCAL_THREADS": 2, "TCPMT_SOLDER_SLOTS": 6},
             evidence="scratch_solder records: critical 219 solves 16.5 ks, cycles 12 solves "
                      "7.5 ks, band 12 solves 3.6 ks, units/constitutive 94 records 8.3 ks; "
                      "6 slots x 2 threads; record mtimes 14:52-16:51 (about 2 h)",
             validate=[{"file": tr("solder_studies.json"), "kind": "json"}],
             notes="the five drivers share 6 global solve slots (tcpmt_solder_common), so one "
                   "job runs them in sequence; ~35 GB of solver scratch")
    # the v2 production local model's parameter table (Table S6 source: law, window, band)
    par = post("solder.parameters", "solder_submodels", "tcpmt_solder_parameters.py",
               [tr("solder_parameters.json")], deps=[st, prod[("Z1", "S0", "A")]] +
               ([mech["band"], mech["record"]] if mech else []),
               env={"LOCAL_THREADS": 2}, backends=LOCAL_SOLVE_BACKENDS)
    z3 = job("solder.z3land", "solder_submodels", ["scripts/tcpmt_solder_z3land.py"],
             [tr("solder_z3land.json")], deps=[st, land["z3_land_t40_A_fvmap"],
                                               land["z3_land_t40_B_fvmap"]],
             ncpus=4, workers=2, mem_gb=8, est_h=0.35, env={"LOCAL_THREADS": 2},
             backends=LOCAL_SOLVE_BACKENDS,
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
        job(f"manuscript.{f}", "manuscript", [f"{f}.py"],          # cwd is fig_scripts (below)
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
