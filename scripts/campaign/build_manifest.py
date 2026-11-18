#!/usr/bin/env python3
"""Generate scripts/campaign/manifest.yaml -- every job that regenerates a computed result of
the TCPMT paper: command, environment, dependencies, outputs, validation, resources, cost.

    python scripts/campaign/build_manifest.py [--design m49|m36] [--campaign NAME] [--out PATH]

COSTS are evidence, not guesses, wherever the artifact exists: each ETM job is costed from
the frozen case file it regenerates (et_wall_s + mechanics.wall_s [+ local.wall_s]; the
feedback jobs from the wall_s of every review_variants/*_itN.json pass), or from a named
analog for a job that has no frozen artifact yet; post-processing and the other solver
families from the production logs (see `EVIDENCE` per job). The frozen runs used 2 threads
per CalculiX solve on a host loaded to ~85 of 96 cores, so the estimates are conservative.

DESIGN POINT (regulator count M and the synthesized design) is a parameter, `--design`:
  m49  the production design, kw1.design_1kw(): N3K3K_A2, 49 cells of 5.61 mm2 (default)
  m36  N4K4K_A2 at M = 36: kw1.design_1kw(m_vr=36, topology=(4,4,2)) compiles (EPC2057 high
       and low side, 480.11 kHz, 7.20 mm2 cell, 91.39 W at 25 C) but the chain cannot run it
       yet; every job that cannot is emitted BLOCKED with the reason (README, "Design point")
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
DESIGNS = {
    "m49": dict(M=49, label="N3K3K_A2, 49 x 5.61 mm2 (production, kw1.design_1kw())", tag="",
                z1_config=None, blocked={}),
    "m36": dict(
        M=36, label="N4K4K_A2, 36 x 7.20 mm2 (kw1.design_1kw(m_vr=36, topology=(4,4,2)))",
        tag="M36N4K4KA2", z1_config="configs/phase0nx/z1_physical_m36.yaml",
        blocked={
            "Z1": "no configs/phase0nx/z1_physical_m36.yaml (design block, tier list with a "
                  "gan_hs_EPC2057 tier, cells 36 / 7.20 mm2 / 2.6833 mm, package_network, "
                  "results.dir); physical_cell.py tier order not derived for the 2.68-mm cell",
            "Z2": "no Z2 design selector: Z2_CFG fixed (physical_coords.py:34, "
                  "final_closure_ledger.py:216/608); production_et.build_global meshes "
                  "N_VR=49 x HVR_AREA_MM2/49 tiles whatever converter.cells says "
                  "(production_et.py:45-46,134); ledger N_VR=49, routing RT.DESIGN, "
                  "PAD.size_for_cell(5.61 mm2), SCEN_RATIO HV_S1 duty 1/16, LAYERS Z2 tier names "
                  "(gan_hs_EPC2014C) fixed (final_closure_ledger.py:37-60,145,318); "
                  "TSV_N_PER_CELL=1444 (final_closure_physical_etm.py:119); conversion loss from "
                  "the production design (replay_production.compiled_design); "
                  "z1_design.require_z1 refuses Z2 when HVR_Z1_CONFIG is set",
            "Z3": "as Z2, plus load_z3_package_config requires the deepest tier to be "
                  "gan_hs_EPC2014C and cells/area/side equal to the FIXED Z2 config "
                  "(physical_package.py:474-487); Z3_CFG fixed (final_closure_ledger.py:87)",
            "consumers": "sensitivity / review / z3land drivers write untagged case names and "
                         "the macro and figure scripts read the production names "
                         "(etm_Z1_HV_S0_h1.1_r21.json); a non-default design lands in "
                         "results.dir with its tag (final_closure_physical_etm.py:66-70)",
        }),
}

# ============================================================================ stages
STAGES = [
    ("prep", "regenerable inputs of the solver chain (network, attach lattices, rules)"),
    ("production", "the production E-T + mechanics cases (r21), cooling tiers A and B, the "
                   "converged fields and the production local solder response"),
    ("z3_landside", "Z3 land-side spreading: FV sheets and the 11 coupled land-side cases"),
    ("interface_feedback", "TIM-warpage interface feedback, Z1/Z2/Z3 x cooling A/B"),
    ("hotspots", "non-uniform die power map, Z1/Z2/Z3 x cooling A/B"),
    ("count_study", "count-optimal M = 64 candidates (synthesized and 4.0-mm2 cells)"),
    ("a1", "case A1: rated flying capacitors (1030-um tier), both tier orders"),
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
SCENS = ("HV_S0", "HV_S1", "HV_S2")
#: cooling tier -> sensitivity variant that realizes it (None = the production case)
TIER_BASE = {("Z1", "A"): None, ("Z2", "A"): None, ("Z3", "A"): "z3_top_only",
             ("Z1", "B"): "z1_bottom_plate_tim", ("Z2", "B"): "z2_cooled_tim",
             ("Z3", "B"): "z3_plate_tim"}


# ============================================================================ cost evidence
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
        workers=1, cwd=".", blocked=None, notes=None):
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
    JOBS.append(j)
    return id


def etm_job(id, stage, argv, out, *, deps=(), analog=None, n_el_k=145, ncpus=2, env=None,
            mechanics=True, local=False, kind="etm", blocked=None, extra_outputs=(),
            speed=1.0, notes=None, est_fallback_h=1.8):
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
               blocked=blocked, notes=notes)


def post(id, stage, script, outputs, *, args=(), deps=(), est_h=0.05, evidence="cheap "
         "post-processing (reads JSON / fields; seconds to minutes)", validate=None, mem_gb=4,
         ncpus=1, prefer="local", env=None, blocked=None, notes=None):
    return job(id, stage, [f"scripts/{script}", *args], outputs, deps=deps, est_h=est_h,
               evidence=evidence, validate=validate or [
                   {"file": o, "kind": "json" if o.endswith(".json") else
                    ("csv" if o.endswith(".csv") else "exists")} for o in outputs],
               mem_gb=mem_gb, ncpus=ncpus, prefer=prefer, env=env, blocked=blocked,
               notes=notes)


def fc(name):
    return f"final_closure/{name}"


def tr(name):
    return f"tcpmt_revision/{name}"


def sens(arch, variant, scen="HV_S0"):
    return f"final_closure/sensitivity/etm_{arch}_{scen}__{variant}.json"


def case(arch, scen, refine="r21"):
    return fc(f"etm_{arch}_{scen}_h1.1{'' if refine == 'r11' else '_' + refine}.json")


# ============================================================================ the manifest
def build(design):
    D = DESIGNS[design]
    blk = D["blocked"]
    nondefault = design != "m49"
    JOBS.clear()
    static = set()

    # ------------------------------------------------------------------ prep
    prep = {}
    prep["literature"] = post("prep.literature_rules", "prep", "final_closure_literature_rules.py",
                              [fc("literature_rules.json")])
    prep["network"] = job(
        "prep.package_network", "prep", ["scripts/final_closure_pkg_network.py"],
        [fc("package_network.json")], env={"FC_WORKERS": 8}, ncpus=8, workers=8,
        est_h=0.5, mem_gb=16, evidence="final_closure_pkg_network.py (FC_WORKERS pool): "
        "RDL network solves, minutes", validate=[{"file": fc("package_network.json"),
                                                 "kind": "json"}])
    prep["attach"] = post("prep.vr_attach", "prep", "final_closure_vr_attach.py",
                          [fc("vr_attach_density_study.json"), fc("vr_attach_density_study.csv")])
    prep["geometry"] = post("prep.architecture_spec", "prep", "final_closure_architecture_spec.py",
                            [fc("architecture_geometry.json")], est_h=0.1,
                            evidence="meshes the three packages once (minutes)")

    # ------------------------------------------------------------------ production (r21)
    prod = {}
    for a in ARCHS + ("Z2BF",):
        for s in (SCENS if a != "Z2BF" else ("HV_S0",)):
            base_a = "Z2" if a == "Z2BF" else a
            b = blk.get(base_a) if nondefault else None
            out = case(a, s)
            if nondefault and a == "Z1" and not b:
                out = f"tcpmt_revision/countopt/etm_Z1_{D['tag']}_{s}_h1.1_r21.json"
            prod[(a, s)] = etm_job(
                f"prod.{a}.{s}", "production",
                ["scripts/final_closure_physical_etm.py", f"{a}:{s}:1.1:r21:ITERATIVE CHOLESKY:1"],
                out, deps=[prep["network"]], n_el_k=145 if a != "Z3" else 127,
                env=({"HVR_Z1_CONFIG": "{repo}/" + D["z1_config"]} if nondefault and a == "Z1"
                     else None), blocked=b)
    # converged fields (copied out of the work tree; read by mech variants, figures, feedback)
    fields = {}
    for (a, s) in (("Z1", "HV_S0"), ("Z2", "HV_S0"), ("Z1", "HV_S1"), ("Z2", "HV_S1"),
                   ("Z3", "HV_S0")):
        fields[(a, s)] = job(
            f"fields.{a}.{s}", "production", ["scripts/final_closure_collect_fields.py", f"{a}:{s}"],
            [f"@fields/etm_{a}_{s}_r21/thermal_converged.frd",
             f"@fields/etm_{a}_{s}_r21/structural.frd"], deps=[prod[(a, s)]], est_h=0.03,
            evidence="file copy + peak check", prefer="any",
            validate=[{"file": f"@fields/etm_{a}_{s}_r21/thermal_converged.frd", "kind": "frd"},
                      {"file": f"@fields/etm_{a}_{s}_r21/structural.frd", "kind": "frd"}],
            blocked=blk.get(a) if nondefault else None)
    # cooling-tier bases: Z3 under A (top plate only) and every architecture under B
    tier = {}
    for (a, t), v in TIER_BASE.items():
        if v is None:
            tier[(a, t)] = prod[(a, "HV_S0")]
            continue
        tier[(a, t)] = etm_job(f"tier.{a}.{t}.{v}", "production",
                               ["scripts/final_closure_sensitivity.py", f"{v}:{a}"], sens(a, v),
                               deps=[prod[(a, "HV_S0")]], n_el_k=145 if a != "Z3" else 127,
                               blocked=blk.get(a) if nondefault else None)
    vfields = {}
    for (a, t), v in TIER_BASE.items():
        if v is None:
            vfields[(a, t)] = fields[(a, "HV_S0")]
            continue
        vfields[(a, t)] = job(
            f"fields.{a}.{v}", "production", ["scripts/tcpmt_collect_variant_fields.py", f"{a}:{v}"],
            [f"@fields/etm_{a}_HV_S0__{v}/thermal_converged.frd",
             f"@fields/etm_{a}_HV_S0__{v}/structural.frd"], deps=[tier[(a, t)]], est_h=0.03,
            evidence="file copy + peak check",
            validate=[{"file": f"@fields/etm_{a}_HV_S0__{v}/thermal_converged.frd", "kind": "frd"}],
            blocked=blk.get(a) if nondefault else None)
    # production local solder response (post_production lane 1 / followup local chain)
    # the local studies pool their L0-L3 joint solves (488-3104 elements): one thread per
    # solve (LOCAL_THREADS, default 6) and the pool width set by FC_POOL_MAX (default 24)
    loc_deps = [prod[k] for k in (("Z1", "HV_S0"), ("Z2", "HV_S0"), ("Z3", "HV_S0"),
                                  ("Z1", "HV_S1"), ("Z2", "HV_S1"), ("Z3", "HV_S1"),
                                  ("Z2", "HV_S2"), ("Z3", "HV_S2"))]
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
    for s, est in (("HV_S0", 1.5), ("HV_S1", 0.3), ("HV_S2", 0.2)):
        loc_s[s] = job(f"local.solder.{s}", "production",
                       ["scripts/final_closure_local_solder.py", s], [fc(f"local_solder_{s}.json")],
                       deps=[loc_m] + [prod[(a, s)] for a in ARCHS], ncpus=6,
                       mem_gb=12, est_h=est,
                       evidence="local_solder_*.json wall_s 5,252 / 993 / 688 s (7 sequential "
                                "solves, 6 threads hard-coded in run_final_local_response.py)",
                       validate=[{"file": fc(f"local_solder_{s}.json"), "kind": "json"}])

    # ------------------------------------------------------------------ Z3 land side
    land_est = post("z3land.estimate", "z3_landside", "tcpmt_z3_landside_estimate.py",
                    [tr("z3_landside_spreading.json")], est_h=0.1,
                    evidence="2-D FV sheet, minutes")
    land_fv = post("z3land.fv", "z3_landside", "tcpmt_z3land_fv.py",
                   [tr("z3_board_plane_spreading.json")], deps=[land_est], est_h=0.2,
                   evidence="2-D FV board planes, minutes")
    land = {}
    for v, tier_ in (("z3_land_t10_B", "B"), ("z3_land_t20_B", "B"), ("z3_land_t40_B", "B"),
                     ("z3_land_t40_A", "A"), ("z3_land_t40_B_noplane", "B"),
                     ("z3_land_t100_B", "B"), ("z3_land_t10_B_fvmap", "B"),
                     ("z3_land_t40_B_fvmap", "B"), ("z3_land_t20_B_fvmap", "B"),
                     ("z3_land_t100_B_fvmap", "B"), ("z3_land_t40_A_fvmap", "A")):
        land[v] = etm_job(f"z3land.{v}", "z3_landside",
                          ["scripts/tcpmt_z3land_variants.py", "run", v], sens("Z3", v),
                          deps=[prod[("Z3", "HV_S0")], tier[("Z3", tier_)], land_est, land_fv],
                          n_el_k=127, blocked=blk.get("Z3") if nondefault else None)
    land_rep = post("z3land.report", "z3_landside", "tcpmt_z3land_report.py",
                    [tr("z3_land_coupled.json")], deps=list(land.values()))

    # ------------------------------------------------------------------ interface feedback
    fb = {}
    for (a, t) in TIER_BASE:
        s, ev = feedback_wall_s(a, t)
        if s is None:
            s, ev = feedback_wall_s(a, "A" if t == "B" else "B")
            ev = f"analog {ev}"
        out = sens(a, f"tim_warp_fb_{t}")
        fb[(a, t)] = job(
            f"feedback.{a}.{t}", "interface_feedback",
            ["scripts/tcpmt_review_variants.py", "feedback", a, t],
            [out], deps=[tier[(a, t)], vfields[(a, t)]],
            env={"FC_THREADS": 2}, ncpus=2, mem_gb=mem_for(145), est_h=(s or 9000) / 3600,
            evidence=ev, validate=[{"file": out, "kind": "feedback"}],
            notes="iterates E-T + mechanics until die warpage < 1 % and loss < 0.05 W "
                  "(<= 5 passes); writes review_variants/*_itN.json per pass",
            blocked=blk.get(a) if nondefault else None)

    # ------------------------------------------------------------------ hot spots
    hs = {}
    for (a, t) in TIER_BASE:
        hs[(a, t)] = etm_job(f"hotspot.{a}.{t}", "hotspots",
                             ["scripts/tcpmt_review_variants.py", "hotspot", a, t],
                             sens(a, f"die_hotspot_{t}"), deps=[tier[(a, t)]],
                             analog=sens(a if a != "Z3" else "Z2", f"die_hotspot_{t}"),
                             n_el_k=145 if a != "Z3" else 127,
                             blocked=blk.get(a) if nondefault else None)

    # ------------------------------------------------------------------ count study (M = 64)
    cnt = {}
    for cfg, tag in (("configs/phase0nx/z1_physical_m64.yaml", "M64N2K2KA1"),
                     ("configs/phase0nx/z1_physical_m64_cell4p0.yaml", "M64N2K2KA1C4")):
        cdir = "tcpmt_revision/countopt"
        net = job(f"count.{tag}.net", "count_study",
                  ["scripts/final_closure_countopt.py", "--z1-config", cfg, "net"],
                  [f"{cdir}/package_network_{tag}.json"], deps=[prep["network"]], ncpus=4,
                  workers=4, est_h=0.3, mem_gb=8, evidence="scratch_countopt/net_m64.log",
                  validate=[{"file": f"{cdir}/package_network_{tag}.json", "kind": "json"}])
        out = f"{cdir}/etm_Z1_{tag}_HV_S0_h1.1_r21.json"
        cnt[(tag, "Z1", "A")] = etm_job(
            f"count.{tag}.Z1.A", "count_study",
            ["scripts/final_closure_countopt.py", "--z1-config", cfg, "etm", "--threads", "2"],
            out, deps=[net], n_el_k=124)
        cnt[(tag, "Z1", "A", "local")] = job(
            f"count.{tag}.Z1.A.local", "count_study",
            ["scripts/final_closure_countopt.py", "--z1-config", cfg, "local"],
            [out], deps=[cnt[(tag, "Z1", "A")], loc_m], est_h=0.05, ncpus=2,
            env={"LOCAL_THREADS": 2},
            evidence="scratch_countopt/local_m64.log (one L0 solve)",
            validate=[{"file": out, "kind": "etm", "local": True}],
            notes="adds the L0 local solder response to the candidate case file")
        job(f"count.{tag}.compare", "count_study",
            ["scripts/final_closure_countopt.py", "--z1-config", cfg, "compare"],
            [f"{cdir}/etm_compare_{tag}_vs_49.json"],
            deps=[cnt[(tag, "Z1", "A", "local")], prod[("Z1", "HV_S0")]], est_h=0.02,
            evidence="post-processing", prefer="local")
        for a, t in (("Z1", "B"), ("Z2", "A"), ("Z2", "B"), ("Z3", "B")):
            cnt[(tag, a, t)] = etm_job(
                f"count.{tag}.{a}.{t}", "count_study",
                ["scripts/final_closure_countopt.py", "--z1-config", cfg, "etm"],
                f"{cdir}/etm_{a}_{tag}_HV_S0_h1.1_r21__tier{t}.json", deps=[net],
                analog=f"{cdir}/etm_Z1_{tag}_HV_S0_h1.1_r21.json", n_el_k=124,
                blocked=("the count study under cooling B needs the tier-B variant applied to a "
                         "non-default design (final_closure_countopt.py runs cooling A only)"
                         if a == "Z1" else
                         f"{a} at M = 64: " + DESIGNS["m36"]["blocked"][a]))
    job("count.control49.local", "count_study",
        ["scripts/final_closure_countopt.py", "--z1-config",
         "configs/phase0nx/z1_physical_m64.yaml", "control"],
        ["tcpmt_revision/countopt/local_control_49.json"], deps=[prod[("Z1", "HV_S0")], loc_m],
        est_h=0.05, evidence="scratch_countopt/local_control.log",
        validate=[{"file": "tcpmt_revision/countopt/local_control_49.json", "kind": "json"}])

    # ------------------------------------------------------------------ A1 rated flying caps
    a1 = {}
    for mode, order, cap in (("ratedcfmax", "rep", "cfmax"), ("ratedcfmaxref", "ref", "cfmax"),
                             ("ratedcf", "rep", "cf"), ("ratedcfref", "ref", "cf")):
        for t in ("A", "B"):
            v = f"z1_rated_{cap}_{order}_{t}"
            a1[v] = etm_job(f"a1.Z1.{mode}.{t}", "a1",
                            ["scripts/tcpmt_review_variants.py", mode, "Z1", t], sens("Z1", v),
                            deps=[tier[("Z1", t)]], analog=sens("Z1", f"z1_rated_{cap}_rep_A"),
                            blocked=blk.get("Z1") if nondefault else None)
    for a in ("Z2", "Z3"):
        for t in ("A", "B"):
            etm_job(f"a1.{a}.ratedcfmax.{t}", "a1", ["scripts/tcpmt_review_variants.py",
                                                     "ratedcfmax", a, t],
                    sens(a, f"{a.lower()}_rated_cfmax_rep_{t}"), deps=[tier[(a, t)]],
                    analog=sens("Z1", "z1_rated_cfmax_rep_A"),
                    blocked=f"case A1 is implemented for Z1 only (tcpmt_review_variants."
                            f"v_z1_rated_cf / run_ratedcf hard-wire Z1); {a} needs a rated "
                            f"1030-um flying-cap tier in its own config")

    # ------------------------------------------------------------------ refinement ladders
    lad = {}
    for a in ARCHS:
        for r, thr, sol_thr, n_k in (("r11", 2, 1, 36), ("r12", 2, 1, 72), ("r31", 4, 2, 326)):
            out = case(a, "HV_S0", r)
            lad[(a, r)] = etm_job(
                f"ladder.{a}.{r}", "refinement_ladders",
                ["scripts/final_closure_physical_etm.py",
                 f"{a}:HV_S0:1.1:{r}:ITERATIVE CHOLESKY:{sol_thr}"], out, deps=[prep["network"]],
                analog=case("Z1" if a != "Z3" else "Z1", "HV_S0", r), n_el_k=n_k, ncpus=thr,
                speed=(0.8 if r == "r31" else 1.0),
                blocked=blk.get(a) if nondefault else None,
                notes=("no frozen Z3 r12 rung (tcpmt_uncertainty probes it)" if
                       (a, r) == ("Z3", "r12") else None))
    lad_cnt = etm_job("ladder.count.M64N2K2KA1.r31", "refinement_ladders",
                      ["scripts/final_closure_countopt.py", "--z1-config",
                       "configs/phase0nx/z1_physical_m64.yaml", "etm", "--refine", "31",
                       "--thermal-only", "--threads", "4"],
                      "tcpmt_revision/countopt/etm_Z1_M64N2K2KA1_HV_S0_h1.1_r31.json",
                      deps=[cnt[("M64N2K2KA1", "Z1", "A")]], mechanics=False, n_el_k=279,
                      ncpus=4, speed=0.8)
    ladder_gap = ("a sensitivity variant solves only at E.PRODUCTION_REFINE "
                  "(final_closure_sensitivity.run_full, tcpmt_z3land_variants.run); a rung needs "
                  "a refine parameter (e.g. FC_REFINE) and its own case name -- not in the code")
    for a, v in (("Z1", "z1_bottom_plate_tim"), ("Z2", "z2_cooled_tim"), ("Z3", "z3_plate_tim"),
                 ("Z3", "z3_land_t40_A_fvmap"), ("Z3", "z3_land_t40_B_fvmap")):
        for r, n_k in (("r11", 36), ("r31", 326)):
            etm_job(f"ladder.{a}.{v}.{r}", "refinement_ladders",
                    ["scripts/final_closure_sensitivity.py", f"{v}:{a}"],
                    f"final_closure/sensitivity/ladder/etm_{a}_HV_S0__{v}_{r}.json",
                    analog=case(a, "HV_S0", r), n_el_k=n_k, ncpus=4 if r == "r31" else 2,
                    deps=[tier.get((a, "B"), prod[(a, "HV_S0")])], blocked=ladder_gap)

    # ------------------------------------------------------------------ robustness map
    class_b = [  # (variant, archs, kind)  -- final_closure_sensitivity.VARIANTS
        ("board_t3p2", "Z1 Z2", "full"), ("board_eta025", "Z1 Z2", "full"),
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
        ("z1_tier_reference", "Z1", "full"), ("board_hbot100", "Z1 Z2", "full"),
        ("board_hbot500", "Z1 Z2", "full"), ("z2_cooled", "Z2", "full"),
        ("pad_drop", "Z1 Z2", "full"), ("gan_k_half", "Z1 Z2", "full"),
        ("conv_k_tenth", "Z1 Z2", "full"), ("conv_E80_a4", "Z1 Z2", "mech"),
        ("conv_E80_a10", "Z1 Z2", "mech"), ("conv_E160_a4", "Z1 Z2", "mech"),
        ("conv_E160_a10", "Z1 Z2", "mech")]
    rb = {}
    for v, archs, kind in class_b:
        for a in archs.split():
            deps = [prod[(a, "HV_S0")]] + ([fields[(a, "HV_S0")]] if kind == "mech" else [])
            if v == "feed_heat_at_crossover":
                deps.append("derived.direct_feed")
            rb[(a, v)] = etm_job(f"robust.{a}.{v}", "robustness_map",
                                 ["scripts/final_closure_sensitivity.py", f"{v}:{a}"],
                                 sens(a, v), deps=deps, blocked=blk.get(a) if nondefault else None)
        job(f"robust.local.{v}", "robustness_map", ["scripts/final_closure_sensitivity.py",
                                                    "--local", v],
            [sens(a, v) for a in archs.split()],
            deps=[rb[(a, v)] for a in archs.split()] + [loc_t, loc_m], est_h=0.05,
            ncpus=2 * len(archs.split()), workers=len(archs.split()),
            env={"LOCAL_THREADS": 2, "FC_POOL_MAX": len(archs.split())},
            evidence="local.wall_s of the frozen variant cases: 77-134 s per architecture",
            validate=[{"file": sens(a, v), "kind": "etm", "local": True} for a in archs.split()],
            blocked=blk.get("Z1") if nondefault else None,
            notes="adds the L0 local solder response at the variant's own critical joint")
    # the newer cooling-model and implemented-decoupling rows of the map
    for (a, t) in TIER_BASE:
        etm_job(f"robust.caloric.{a}.{t}", "robustness_map",
                ["scripts/tcpmt_review_variants.py", "caloric", a, t],
                sens(a, f"plate_local_h_{t}"), deps=[tier[(a, t)]],
                blocked=blk.get(a) if nondefault else None)
    for a, t in (("Z1", "B"), ("Z2", "A"), ("Z2", "B"), ("Z3", "A"), ("Z3", "B")):
        etm_job(f"robust.sdec.{a}.{t}", "robustness_map",
                ["scripts/tcpmt_review_variants.py", "sdec", a, t],
                sens(a, f"sdec_{t}", "HV_SDEC"), deps=[tier[(a, t)], "derived.decap_framework"],
                analog=sens("Z2", "sdec_B", "HV_SDEC"),
                blocked=blk.get(a) if nondefault else None)

    # ------------------------------------------------------------------ the rest
    rest(prod, fields, tier, vfields, land, land_est, land_fv, land_rep, fb, hs, rb, loc_t, loc_m,
         loc_s, lad, cnt, prep, blk if nondefault else {})
    return {"jobs": JOBS, "static": sorted(STATIC)}


#: artifacts the pipeline reads that NO job produces (hand-written, ANSYS-only, web or PDF
#: derived, or from an earlier lineage): `run.py seed` copies them from research/ into the
#: campaign root before the first job, so hooked readers find them there
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


def rest(prod, fields, tier, vfields, land, land_est, land_fv, land_rep, fb, hs, rb, loc_t,
         loc_m, loc_s, lad, cnt, prep, blk):
    P = lambda a, s="HV_S0": prod[(a, s)]                                  # noqa: E731
    r21 = [prod[(a, s)] for a in ARCHS for s in SCENS]
    tierB = [tier[(a, "B")] for a in ARCHS]
    land_AB = [land["z3_land_t40_A_fvmap"], land["z3_land_t40_B_fvmap"]]
    tier_cases = [P("Z1"), P("Z2"), tier[("Z1", "B")], tier[("Z2", "B")]] + land_AB

    # ------------------------------------------------------------ DSE sweeps (local, 1 core)
    eng = job("prep.dse_engine", "prep", ["scripts/campaign/build_dse_engine.py",
                                          "{scratch}/dse_engine"],
              ["@scratch/dse_engine/ENGINE.json"], est_h=0.01, prefer="local",
              evidence="file copy", validate=[{"file": "@scratch/dse_engine/ENGINE.json",
                                               "kind": "json", "keys": ["files"]}])
    counts = "36,40,42,45,48,49,50,52,56,60,64,70,76,84,92,100,120"
    dse = {}
    for tag, env, est, ev in (
            ("etm35", {"HVR_CAP_RULE": "legacy"}, 0.10,
             "sweep.log: per-count total 195 s; HEAD engine + legacy rule reproduces etm35"),
            ("etm35_legacycheck", {"HVR_CAP_RULE": "legacy"}, 0.10, "dse_legacy.log 98 s"),
            ("etm35_legacycheck2", {"HVR_CAP_RULE": "legacy"}, 0.10, "dse_legacy2.log 184 s"),
            ("etm35_caprule", {"HVR_CAP_RULE": "stress", "HVR_CAP_RIPPLE": 0, "HVR_CAP_ESR_F": 0},
             0.15, "dse_caprule.log 219 s (7feaba2 engine; HEAD + ripple/ESR off assumed equal)"),
            ("etm35_caprule_ripple", {"HVR_CAP_RULE": "stress", "HVR_CAP_RIPPLE": 1,
                                      "HVR_CAP_ESR_F": 0}, 0.15, "dse_ripple.log 382 s"),
            ("etm35_caprule_full", {"HVR_CAP_RULE": "stress", "HVR_CAP_RIPPLE": 1,
                                    "HVR_CAP_ESR_F": 1}, 0.15, "dse_full.log 393 s"),
            ("etm35_caprule_full125", {"HVR_CAP_RULE": "stress", "HVR_CAP_RIPPLE": 1,
                                       "HVR_CAP_ESR_F": 1, "HVR_CAP_T_DESIGN": 125}, 0.15,
             "dse_full125.log 370 s")):
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
    cap = post("derived.dse_caprule_summary", "derived", "tcpmt_dse_caprule_summary.py",
               [tr("dse_caprule.json"), tr("cap49_comparison.json")],
               deps=[dse[t] for t in ("etm35", "etm35_legacycheck2", "etm35_caprule",
                                      "etm35_caprule_ripple", "etm35_caprule_full",
                                      "etm35_caprule_full125")])
    cdse = job("count.candidate_dse", "count_study",
               ["bash", "-c", "set -e; cd {repo}; {python} -B research/tcpmt_revision/countopt/"
                "candidate_dse.py --counts 49,64,72,76,81; {python} -B research/tcpmt_revision/"
                "countopt/candidate_dse.py --counts 49,64,72,76,81 --hs-stress 2vin_over_n"],
               [tr("countopt/candidate_dse.json"), tr("countopt/candidate_dse_hs_2vin_over_n.json")],
               deps=[eng], env={"HVR_DSE_ENGINE": "{scratch}/dse_engine", "HVR_CAP_RULE": "legacy"},
               est_h=0.05, evidence="about 6 s per count (scratch_countopt sweep_countopt.log)",
               prefer="local", validate=[{"file": tr("countopt/candidate_dse.json"), "kind": "json"}])

    # ------------------------------------------------------------ decoupling and capacitors
    fcaps = post("derived.flying_caps", "derived", "tcpmt_decap_flying_caps.py",
                 [tr("flying_caps.json")], deps=[P("Z1")])
    post("derived.capacitor_evidence", "derived", "tcpmt_capacitor_evidence.py",
         [tr("capacitor_evidence.json"), "manuscript_v2/supplement/tab_capacitor_evidence.tex"],
         deps=[fcaps])
    job("count.physical_cell", "count_study",
        ["research/tcpmt_revision/countopt/physical_cell.py"], [tr("countopt/physical_cell.json")],
        deps=[cdse, fcaps], est_h=0.02, prefer="local", evidence="cheap",
        validate=[{"file": tr("countopt/physical_cell.json"), "kind": "json"}])
    dcirc = post("derived.decap_circuit", "derived", "tcpmt_decap_circuit.py",
                 [tr("input_decoupling.json")], deps=[P("Z1"), prep["network"]])
    dplace = post("derived.decap_placement", "derived", "tcpmt_decap_placement.py",
                  [tr("input_decoupling.json")], deps=[dcirc], est_h=0.2,
                  validate=[{"file": tr("input_decoupling.json"), "kind": "json",
                             "keys": ["placement"]}])
    dled = post("derived.decap_ledger", "derived", "tcpmt_decap_framework.py",
                [tr("input_decoupling.json")], args=["ledger"],
                deps=[dplace, P("Z1"), P("Z1", "HV_S1"), "derived.direct_feed"])
    drun = etm_job("robust.decap.Z1.run", "robustness_map",
                   ["scripts/tcpmt_decap_framework.py", "run"],
                   sens("Z1", "z1_input_decoupling", "HV_SDEC"), deps=[dled])
    dcol = post("derived.decap_collect", "derived", "tcpmt_decap_framework.py",
                [tr("input_decoupling.json")], args=["collect"], deps=[drun])
    job("derived.decap_framework", "derived",
        ["scripts/tcpmt_decap_framework.py", "summary"], [tr("input_decoupling.json")],
        deps=[dcol], est_h=0.05, prefer="local", evidence="cheap",
        validate=[{"file": tr("input_decoupling.json"), "kind": "json"}],
        notes="circuit -> placement -> ledger -> run -> collect -> summary each read-modify-"
              "write input_decoupling.json, hence one chain")

    # ------------------------------------------------------------ results and class B
    dfeed = job("derived.direct_feed", "derived", ["scripts/final_closure_direct_feed.py"],
                [fc("direct_feed_crossover.json")],
                deps=r21 + [rb[("Z2", "attach_dense")], rb[("Z2", "attach_sparse")]],
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
                          notes="re-solves the structure on ladder.Z1.r11's converged field "
                                "(campaign scratch fc_etm/Z1_HV_S0_h1.1)")
    res = job("derived.results", "derived", ["scripts/final_closure_results.py"],
              [fc(x) for x in ("final_results.json", "electrical_ledger.json",
                               "electrical_ledger.csv", "energy_audit.json",
                               "mesh_convergence.json", "ordering.json", "coupling_checks.json",
                               "control_results.json")],
              deps=r21 + [P("Z2BF"), dfeed, loc_m] + list(loc_s.values()) +
              [lad[(a, r)] for a in ("Z1", "Z2") for r in ("r11", "r12", "r31")] +
              list(solver.values()), est_h=0.2, prefer="local",
              evidence="JSON work + 12 ledger points; rebuilds the Z2 mesh once when the "
                       "coupling_checks cache is absent (fresh root)",
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
         [tr("layer_temperatures.json")], deps=flds, est_h=0.1)
    post("derived.tier_feed", "derived", "tcpmt_tier_feed.py", [tr("tier_feed_crossover.json")],
         deps=tier_cases, notes="INCONSISTENT on rerun: Z3 tiers now name the land-coupled "
         "cases but the Z3 ledger here is unpatched (inventory); only RstarTierBZtwo is quoted")
    cool = post("derived.cooling_spec", "derived", "tcpmt_cooling_spec.py",
                [tr("cooling_spec.json")], deps=tier_cases)
    post("derived.feasibility", "derived", "tcpmt_feasibility.py", [tr("feasibility.json")],
         deps=flds + [fields[("Z3", "HV_S0")], fields[("Z1", "HV_S1")], fields[("Z2", "HV_S1")],
                      P("Z3"), P("Z1", "HV_S1"), P("Z2", "HV_S1")] + tierB +
         [tier[("Z3", "A")]], est_h=0.15, mem_gb=8,
         evidence="9 mesh builds + 9 frd reads (minutes)")
    post("derived.platform", "derived", "tcpmt_platform.py", [tr("platform_inclusive.json")],
         deps=[cool, P("Z2BF"), land_rep] + tier_cases)
    solder = solder_jobs(prod, tier, land, loc_t, loc_m)
    post("derived.uncertainty", "derived", "tcpmt_uncertainty.py",
         [tr("uncertainty.json"), "manuscript_v2/tab_uncertainty.tex"],
         deps=[lad[(a, r)] for a in ARCHS for r in ("r11", "r12", "r31")] +
         [P(a) for a in ARCHS] + tier_cases + [loc_m, solder["studies"], solder["z3land"]])
    post("derived.omitted_losses", "derived", "tcpmt_omitted_losses.py", [tr("omitted_losses.json")],
         deps=[dse["etm35"], P("Z1"), P("Z2"), P("Z3")] + tierB + [tier[("Z3", "A")]],
         est_h=0.1, notes="the f_sw-grid section needs tcpmt_omitted_losses_fsw_grid.py, which "
         "cannot run at HEAD (engine md5 check, stale patch patterns): written available:false")

    # ------------------------------------------------------------ manuscript
    manuscript()


def solder_jobs(prod, tier, land, loc_t, loc_m):
    deps = [prod[(a, "HV_S0")] for a in ARCHS] + [prod[("Z1", "HV_S1")], prod[("Z2", "HV_S1")],
                                                  tier[("Z3", "A")], tier[("Z1", "B")],
                                                  tier[("Z2", "B")], tier[("Z3", "B")], loc_t, loc_m]
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
               [tr("solder_parameters.json")], deps=[st, prod[("Z1", "HV_S0")]],
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
               ["bash", "-c", "set -e; cd {repo}; {python} %s Z1 Z3; {python} %s Z1 --ladder 3; "
                "{python} %s Z1 --split 2,2,1 1,1,2 1,1,4 3,3,1 4,4,1; {python} %s Z3 --split "
                "2,2,1 1,1,2 3,3,1 4,4,1; {python} %s --side" % (v, v, v, v, v)],
               [tr("fullpkg_verification.json")],
               deps=[prod[("Z1", "HV_S0")], prod[("Z3", "HV_S0")], fields[("Z2", "HV_S0")]],
               ncpus=8, mem_gb=64, est_h=1.5, backends=("local",), prefer="local",
               evidence="scratch_fullpkg: ccx 8 thr median 94/101 s x4, MOOSE 8 ranks; x3 "
                        "refinement 3.9 M hex 276 s, rank-0 peak 6.5 GB (x8 replicated); "
                        "~1 h on 8 cores under load",
               validate=[{"file": tr("fullpkg_verification.json"), "kind": "json"}],
               notes="main -> ladder -> split -> side: one sequence (read-modify-write JSON; "
                     "main deletes EVID/<ARCH>)")
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
    ap.add_argument("--design", default="m49", choices=sorted(DESIGNS))
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
            "design_point": {"name": a.design, "M": D["M"], "design": D["label"],
                             "tag": D["tag"], "z1_config": D["z1_config"],
                             "blocked": D["blocked"]},
        },
        "local": {"max_cores": 30, "nice": 10},
        "pbs": {"host": "pioneer", "qsub": "/opt/pbs/bin/qsub", "qstat": "/opt/pbs/bin/qstat",
                "qdel": "/opt/pbs/bin/qdel", "queue": "cpu_only", "select_extra": "host=califone",
                "max_running": 8, "max_queued": 50, "max_walltime_h": 96, "max_ncpus": 112,
                "max_mem_gb": 512, "resubmit_failed": 1, "hybrid_buffer": 4,
                "jobs_dir": "/home/beams/SABDELZAHER/pbs_jobs/etm/{campaign}"},
        "stages": [{"name": s, "what": w} for s, w in STAGES],
        "static_inputs": res["static"],
        "jobs": jobs,
    }
    hdr = ("# GENERATED by scripts/campaign/build_manifest.py -- edit the generator, not this "
           "file.\n# Campaign manifest of the TCPMT paper results; see scripts/campaign/README.md\n")
    Path(a.out).write_text(hdr + yaml.safe_dump(doc, sort_keys=False, width=100))
    nb = sum(1 for j in jobs if j.get("blocked"))
    print(f"wrote {a.out}: {len(jobs)} jobs ({nb} blocked), design {a.design}")


if __name__ == "__main__":
    main()
