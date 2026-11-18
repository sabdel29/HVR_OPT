"""The compared cases of the TCPMT revision (review round 2): ONE registry.

Every producer of a compared number (macros and Table V, platform-inclusive loss, feed
crossover, uncertainty, cooling balance, layer temperatures, omitted losses, feasibility,
supplement) takes its case files from here, so a superseded case cannot survive in one table
after the others have moved on.

INPUT STATES
  SDEC  PRODUCTION. The implemented input decoupling (tcpmt_decap_framework): seven
        interleaved clock phases and a ring of 56 x 1206 100-V capacitors outside the cell
        grid; the package 48-V network at its loss-equivalent k_eq = 1.65 (49-cell port model),
        the cell-internal VIN -> HS runs at the bare pulse (the hot loop, common to every
        integration), the ring ESR as a ledger row (Z1). Every integration, both coolings.
  S0    REFERENCE: ideal input smoothing (k = 1).
  S1    REFERENCE: no decoupling (square pulse at the buck duty, k = 4).
COOLING
  A     one top cold plate (the chain's production boundary for Z1/Z2)
  B     the same top plate plus an identical bottom plate behind a 50-um TIM
Z3 is ALWAYS the coupled land-side case (land side 40 um, board planes 2 x 35 um per rail,
FV-map deposit; tcpmt_z3land_variants). The uncoupled Z3 cases are SUPERSEDED (SUPERSEDED).

File names: production cases etm_<arch>_<scen>_h1.1_r21.json (research/final_closure),
every other case etm_<arch>_<scen>__<variant>.json (research/final_closure/sensitivity), with
<variant> = sdec_<tier> for the production state and the cooling-tier base otherwise.
"""
from __future__ import annotations

import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
FC = R / "research" / "final_closure"
SENS = FC / "sensitivity"
TR = R / "research" / "tcpmt_revision"

PRODUCTION_STATE = "SDEC"
STATES = ("SDEC", "S0", "S1")
SCEN = {"SDEC": "HV_SDEC", "S0": "HV_S0", "S1": "HV_S1"}
STATE_LABEL = {"SDEC": "implemented decoupling (k_eq = 1.65)", "S0": "S0 (ideal smoothing)",
               "S1": "S1 (no decoupling)"}
TIERS = ("A", "B")
ARCHS = ("Z1", "Z2", "Z3")
#: the coupled land-side base of Z3 under each cooling
Z3_LAND = {"A": "z3_land_t40_A_fvmap", "B": "z3_land_t40_B_fvmap"}
#: the cooling-tier base variant of every integration (None = the chain's production boundary)
COOLING_BASE = {("Z1", "A"): None, ("Z2", "A"): None, ("Z3", "A"): Z3_LAND["A"],
                ("Z1", "B"): "z1_bottom_plate_tim", ("Z2", "B"): "z2_cooled_tim",
                ("Z3", "B"): Z3_LAND["B"]}


def _candidates(state, tier, arch):
    """Case files (relative to research/final_closure), first existing wins."""
    scen = SCEN[state]
    base = COOLING_BASE[(arch, tier)]
    if state == PRODUCTION_STATE:
        c = [f"sensitivity/etm_{arch}_{scen}__sdec_{tier}.json"]
        if (arch, tier) == ("Z1", "A"):       # the first implemented-decoupling run, same hooks
            c.append(f"sensitivity/etm_Z1_{scen}__z1_input_decoupling.json")
        return c
    if base is None:
        return [f"etm_{arch}_{scen}_h1.1_r21.json"]
    return [f"sensitivity/etm_{arch}_{scen}__{base}.json"]


def case_path(state, tier, arch):
    """The case file of one integration in one state and cooling; None when not run yet."""
    for rel in _candidates(state, tier, arch):
        p = FC / rel
        if p.is_file():
            return p
    return None


def expected_path(state, tier, arch):
    """The file the campaign must produce (the first candidate), whether it exists or not."""
    return FC / _candidates(state, tier, arch)[0]


def load(state, tier, arch):
    """(path, record) of a compared case, guarded: a Z3 record without the coupled land side
    is refused (it would be a superseded, uncoupled case)."""
    p = case_path(state, tier, arch)
    if p is None:
        return None, None
    c = json.loads(p.read_text())
    guard(arch, c, p)
    return p, c


def guard(arch, case, path=None):
    if arch == "Z3" and not is_coupled_z3(case):
        raise RuntimeError(f"{Path(path).name if path else 'a Z3 case'} carries no coupled "
                           f"land side (z3_land block / P_sub_land_1V_spreading row > 0): it is "
                           f"a superseded uncoupled Z3 case")


def is_coupled_z3(case) -> bool:
    if case.get("z3_land"):
        return True
    rows = {r["term"]: r for r in case.get("ledger_rows") or []}
    land = rows.get("P_sub_land_1V_spreading")
    return bool(land and (land.get("P_w") or 0.0) > 0.0)


def table(state=PRODUCTION_STATE):
    """{tier: {arch: Path or None}} of one state."""
    return {t: {a: case_path(state, t, a) for a in ARCHS} for t in TIERS}


#: uncoupled Z3 records the revision no longer compares (each still exists on disk)
SUPERSEDED = {
    "sensitivity/etm_Z3_HV_S0__z3_top_only.json":
        "Z3 under cooling A without the land-side and board-plane redistribution (199.6 W)",
    "sensitivity/etm_Z3_HV_S0__z3_plate_tim.json":
        "Z3 under cooling B without the land-side and board-plane redistribution (124.5 W)",
    "etm_Z3_HV_S0_h1.1_r21.json":
        "Z3 interface-free bottom plate, uncoupled land side (120.3 W; also its S1/S2/r31)",
    "etm_Z3_HV_S1_h1.1_r21.json": "as above, S1", "etm_Z3_HV_S2_h1.1_r21.json": "as above, S2",
    "etm_Z3_HV_S0_h1.1_r31.json": "as above, r31 mesh",
    "sensitivity/etm_Z3_HV_S0__plate_local_h_A.json": "built on z3_top_only",
    "sensitivity/etm_Z3_HV_S0__plate_local_h_B.json": "built on z3_plate_tim",
    "sensitivity/etm_Z3_HV_S0__die_hotspot_B.json": "built on z3_plate_tim",
    "sensitivity/etm_Z3_HV_S0__tim_warp_fb_A.json": "built on z3_top_only",
    "sensitivity/etm_Z3_HV_S0__tim_warp_fb_B.json": "built on z3_plate_tim",
}


def is_superseded(path) -> bool:
    p = Path(path)
    try:
        rel = p.resolve().relative_to(FC.resolve()).as_posix()
    except ValueError:
        return False
    return rel in SUPERSEDED


# ------------------------------------------------------------------ converged fields on disk
def scratch_roots():
    """Roots that may hold solver work trees (fc_etm, fc_sens, fc_fb) or collected fields:
    $HVR_SCRATCH, $HVR_SCRATCH_ROOTS (os.pathsep list), the hvr_scratch default and the
    project's scratch* directories (each agent of the revision ran under its own)."""
    import glob
    import os
    out = []
    for v in (os.environ.get("HVR_SCRATCH"), *(os.environ.get("HVR_SCRATCH_ROOTS", "")
                                             .split(os.pathsep))):
        if v:
            out.append(Path(v))
    out.append(Path.home() / "claude_scratch" / "hvr_work")
    for up in list(R.parents)[:5]:        # the project directory (a worktree sits deeper)
        out += sorted(Path(p) for p in glob.glob(str(up / "scratch*")))
    seen, uniq = set(), []
    for p in out:
        k = str(p.resolve()) if p.exists() else str(p)
        if k not in seen and p.is_dir():
            seen.add(k)
            uniq.append(p)
    return uniq


def _work_dirs(path, case):
    """Candidate work-tree directories of a case (newest layout first)."""
    stem = Path(path).stem
    arch, scen = case["arch"], case["scenario"]
    h = f"h{case.get('h_xy_mm', 1.1)}"
    ref = case.get("refine") or [2, 1]
    rt = "" if tuple(ref) == (1, 1) else f"_r{ref[0]}{ref[1]}"
    out = []
    for root in scratch_roots():
        if "__" in stem:
            name = stem.split("__", 1)[1]
            out.append(root / "fc_sens" / name / f"{arch}_{scen}_{h}{rt}")
            if name.startswith("tim_warp_fb_"):
                tier = name.rsplit("_", 1)[-1]
                its = sorted((root / "fc_fb" / f"{arch}_{tier}").glob("it*"),
                             key=lambda p: int(p.name[2:]) if p.name[2:].isdigit() else -1)
                out += [it / f"{arch}_{scen}_{h}{rt}" for it in reversed(its)]
        else:
            tag = stem[len(f"etm_{arch}"):].split(f"_{scen}_")[0]   # design tag ('' or _<tag>)
            out.append(root / "fc_etm" / f"{arch}{tag}_{scen}_{h}{rt}")
    return out


def converged_field(path, case=None, check_tol_K=1e-3):
    """{'thermal': frd, 'inp': its deck or None, 'structural': frd or None, 'source': dir} of
    the case's CONVERGED thermal solution, checked against the case's T_max; None if no copy
    on disk matches."""
    import numpy as np
    case = case or json.loads(Path(path).read_text())
    t_max = (case.get("thermal") or {}).get("T_max_C")
    if t_max is None:
        return None
    n_it = len(case.get("et_history") or [])
    for wd in _work_dirs(path, case):
        if not wd.is_dir():
            continue
        ets = sorted(wd.glob("et*"), key=lambda p: int(p.name[2:]) if p.name[2:].isdigit()
                     else -1)
        if not ets:
            continue
        want = wd / f"et{n_it - 1}"
        cand = [want] if want in ets else [ets[-1]]
        for et in cand:
            th = sorted(et.glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))
            if not th:
                continue
            if abs(_frd_tmax(th[-1]) - t_max) > check_tol_K:
                continue
            inp = th[-1].with_suffix(".inp")
            st = wd / "structural.frd"
            return {"thermal": th[-1], "inp": inp if inp.is_file() else None,
                    "structural": st if st.is_file() else None, "source": str(wd)}
    return None


def _frd_tmax(frd):
    """Peak nodal temperature of a thermal .frd (NDTEMP block), read without the full parse."""
    t = -1e300
    on = False
    with open(frd) as fh:
        for line in fh:
            k = line[:4].strip()
            if k == "-4":
                on = line[5:17].strip() == "NDTEMP"
            elif k == "-3":
                if on:
                    break
            elif on and k == "-1":
                t = max(t, float(line[13:25]))
    return t


def run_list():
    """Every compared case the campaign must (re)produce, with its run command."""
    out = []
    for state in STATES:
        for t in TIERS:
            for a in ARCHS:
                p = expected_path(state, t, a)
                if state == PRODUCTION_STATE:
                    cmd = f"python scripts/tcpmt_review_variants.py sdec {a} {t}"
                elif COOLING_BASE[(a, t)] is None:
                    cmd = f"python scripts/final_closure_physical_etm.py {a}:{SCEN[state]}"
                else:
                    cmd = f"python scripts/tcpmt_review_variants.py state {a} {t} {SCEN[state]}"
                out.append({"state": state, "tier": t, "arch": a,
                            "file": p.relative_to(R).as_posix(), "exists": p.is_file(),
                            "command": cmd})
    return out


if __name__ == "__main__":
    for r in run_list():
        print(f"{r['state']:5s} {r['tier']} {r['arch']}  {'have' if r['exists'] else 'RUN '}  "
              f"{r['file']}   <- {r['command']}")
