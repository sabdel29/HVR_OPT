"""FINAL CLOSURE --- the production package HV network, at the count it will use.

Supersedes research/phase0nak for the paper lineage. Two things changed:

1. The sheet is solved on the aligned, graded finite-volume grid
   (pkg_rdl_refined), which converges where the uniform grid could not.
2. The cell terminal is the converter's own traced 0.2 mm VIN pad
   (routing.tile_layout), not the untraced full 2.3685 mm tile.

Both change the per-ball current fractions, so the exhaustive count screen is
re-run on this model rather than reused: a count closure computed on a model
the paper no longer uses would be a stale number with a current label.

Two analyses are kept apart, as the scope requires:
  A. ARCHITECTURE COMPARISON at one MATCHED count, legal and passing HV-S0 for
     both architectures, so count optimisation is not confounded with
     architecture.
  B. PROVISIONING SENSITIVITY: architecture-specific minima, non-monotonicity,
     and the dependence on the unsourced 1.5 A/ball engineering criterion.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
import pkg_rdl_refined as RF                                         # noqa: E402
import pkg_rdl_network as K                                          # noqa: E402
import physical_coords as PCO                                        # noqa: E402

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"   # campaign hook
OUT.mkdir(parents=True, exist_ok=True)
I_CRIT_A = 1.5
SCREEN_LEVEL, VERIFY_LEVEL, FINAL_LEVELS = 1, 2, (1, 2, 3)
#: TCPMT review round 2: HV_SDEC is the PRODUCTION waveform (implemented input decoupling,
#: package-network k_eq = 1.65); the count is closed, and the two architectures matched, at it.
#: TCPMT_BGA_MATCH_SCEN=HV_S0 reproduces the committed S0 closure (54 per rail).
PRODUCTION_SCEN = "HV_SDEC"
MATCH_SCEN = os.environ.get("TCPMT_BGA_MATCH_SCEN", PRODUCTION_SCEN)
SCEN = ("DC_AVERAGE", "HV_S0", "HV_SDEC", "HV_S1", "HV_S2")
WORKERS = int(os.environ.get("FC_WORKERS", "32"))
PRODUCTION_OUT = OUT / "bga_count_production.json"
#: REVIEW ROUND 3 (declared): the 48-V BGA uses AT MOST this many balls per rail; the legal
#: counts, the screen and every closure are restricted to it
N_MAX_PER_RAIL = 220
#: The NETWORK BUILD's count rule (main): the DC peak x k_eq rule (the screen's peak fraction x
#: the production RMS current, verified on the resolved level) at I_CRIT_A, at most 220 balls
#: per rail; when no legal count closes, the FALLBACK_RULE count (220 per rail at m36). That
#: count is the MODELLED ARRANGEMENT every production case carries. Review round 3 (the authors'
#: decision of 2026-11-19) keeps it, with no reallocation, and takes the per-ball verdict in the
#: re-closure (reclose, RECLOSE_RULE below: one rule for every integration, the verified DC peak
#: x k_eq against the feasibility stage's 2-A target, 1.5 A as a sensitivity; Z1's worst-ball
#: RMS of the harmonic port model an idealized bound, reported).
CLOSURE_RULE = ("network count: DC peak x k_eq <= 1.5 A per ball, at most 220 balls per rail, "
                "else the fallback count (the modelled arrangement); the per-ball verdict is "
                "the re-closure's (one rule, DC peak x k_eq, against the 2-A target)")
#: REVIEW ROUND 3, the authors' decision of 2026-11-19 (round3_worklog): the re-closure
#: (reclose) checks the per-ball current against the FEASIBILITY STAGE'S target
#: (tcpmt_feasibility.LIMITS bga_A_per_ball: 2 A, Kuan et al. ASQED 2015; bga_A_per_ball_
#: sensitivity: 1.5 A, a conservative sensitivity), with ONE rule for every integration (the
#: verified DC peak x k_eq), at the ball count of the MODELLED arrangement (the package
#: network's count): no reallocation. Z1's worst-ball RMS of the port model is reported as an
#: idealized bound. The network build (main) keeps I_CRIT_A, the criterion it chose its count
#: with (CLOSURE_RULE, recorded in package_network.json).
RECLOSE_RULE = ("per-ball current = verified DC peak x k_eq (one rule for every integration) "
                "against the feasibility stage's per-ball target (tcpmt_feasibility.LIMITS "
                "bga_A_per_ball; the conservative sensitivity bga_A_per_ball_sensitivity is "
                "reported), at the ball count of the modelled arrangement (package_network.json, "
                "at most 220 per rail; no reallocation); Z1's worst-ball RMS of the port model "
                "is an idealized bound, reported")
#: set by reclose(): the per-ball criterion of the screen / verification pass flags (None: the
#: network build's I_CRIT_A)
_CRIT_A = None


def crit_a():
    """The per-ball criterion (A) of the pass flags in force: the re-closure's target while
    reclose() runs, else I_CRIT_A (the network build)."""
    return I_CRIT_A if _CRIT_A is None else float(_CRIT_A)


def bga_target():
    """(target A, sensitivity A, source, BGA policy in force) of the per-ball check, from the
    feasibility stage (tcpmt_feasibility.LIMITS / LIMIT_SOURCES / BGA_POLICY)."""
    import tcpmt_feasibility as FEAS
    return (float(FEAS.LIMITS["bga_A_per_ball"]),
            float(FEAS.LIMITS["bga_A_per_ball_sensitivity"]),
            FEAS.LIMIT_SOURCES["bga_A_per_ball"], FEAS.BGA_POLICY)


#: set by reclose(): the re-closure takes the k the results root's own decoupling chain
#: derived (chain_k) before the record's committed k
_K_FROM_CHAIN = False


def chain_k():
    """(k_eq, band) the decoupling chain of the results root derived (input_decoupling.json
    summary.recommended), when that record is of the design in force; else None. In a campaign
    this is the production-mesh k of the campaign's own Z1 S0 case."""
    import design_record as DR
    f = (Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"
         / "input_decoupling.json")
    try:
        d = json.loads(f.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    des = (d.get("circuit") or {}).get("design") or {}
    rec = (d.get("summary") or {}).get("recommended") or {}
    if (des.get("design_record") == DR.name() and des.get("n_cell") == DR.n_vr()
            and rec.get("k_eq")):
        return float(rec["k_eq"]), [float(x) for x in rec["k_eq_band"]]
    return None


def production_k():
    """k_eq of the implemented decoupling the count is closed at: the design record's
    `decoupling` block (TCPMT round 3: the committed production k of the design in force; the
    campaign's decoupling chain re-derives it, tcpmt_design_comparison.py kcheck), else the
    summary of input_decoupling.json (the round-2 source). Nominal and the loop-inductance
    band. Review round 3: in the re-closure (_K_FROM_CHAIN) the k the root's own decoupling
    chain derived comes first, so the BGA verdict is at the k of the production cases."""
    import design_record as DR
    if _K_FROM_CHAIN:
        ck = chain_k()
        if ck:
            return ck
    dec = DR.get().get("decoupling") or {}
    if dec.get("k_eq"):
        return float(dec["k_eq"]), [float(x) for x in dec.get("k_eq_band") or
                                    (dec["k_eq"], dec["k_eq"])]
    d = json.loads((Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "input_decoupling.json").read_text())
    rec = d["summary"]["recommended"]
    return float(rec["k_eq"]), [float(x) for x in rec["k_eq_band"]]


def production_i_avg(arch):
    """The 48-V average current of the production state: the largest over the
    implemented-decoupling case files of the architecture (both coolings; 'Z2' here is the
    BGA-fed network, i.e. Z2's feed, which carries Z2's input current). None if none exists."""
    import tcpmt_cases as TC
    a = "Z1" if arch == "Z1" else "Z2"
    vals = []
    for t in TC.TIERS:
        p = TC.case_path(TC.PRODUCTION_STATE, t, a)
        if p is not None:
            c = json.loads(p.read_text())
            vals.append(float(c.get("i_hv_avg_a") or (1000.0 + c["P_loss_w"]) / 48.0))
    return max(vals) if vals else None


def scenarios(arch):
    import interconnect_loss as IL
    rb = IL.rms_scenarios(arch)
    k, _band = production_k()
    i_prod = production_i_avg(arch) or rb["hv_avg_a"]
    return {"DC_AVERAGE": rb["hv_avg_a"], "HV_S0": rb["hv_S0_a"],
            "HV_SDEC": k * i_prod,
            "HV_S1": rb["hv_S1_a"], "HV_S2": rb["hv_S2_a"]}


def legal_counts(arch, n_max=N_MAX_PER_RAIL):
    cells = PCO.physical_cell_coordinates()
    cand = PCO.bga_lattice_sites(K.architecture_cutout_mm(arch))
    ok = []
    for n in range(2, n_max + 1, 2):
        if 2 * n > len(cand):
            break
        try:
            s = PCO.select_power_sites(cand, cells, n, n, "nearest_symmetric")
        except Exception:
            continue
        if len(s["supply"]) == n and len(s["return"]) == n:
            ok.append(n)
    return ok


def _job(args):
    arch, rail, n, level, kw = args
    r = RF.solve_rail(arch, rail, n, level, **kw)
    return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in r.items()
            if k not in ("cell_drop_v",)}


def run_pool(jobs):
    with Pool(min(WORKERS, len(jobs))) as p:
        return p.map(_job, jobs, chunksize=1)


def peak_rows(results):
    """Combine supply/return solves into one row per (arch, n, level)."""
    by = {}
    for r in results:
        key = (r["arch"], r["n_per_rail"], r["level"], r["terminal_mode"])
        by.setdefault(key, {})[r["rail"]] = r
    rows = []
    for (arch, n, lv, mode), d in sorted(by.items()):
        if set(d) != {"supply", "return"}:
            continue
        sc = scenarios(arch)
        row = {"arch": arch, "n_per_rail": n, "level": lv, "terminal_mode": mode}
        for rail in ("supply", "return"):
            x = d[rail]
            row[f"{rail}_peak_fraction"] = x["i_ball_max_a"]
            row[f"{rail}_r_eff_ohm"] = x["r_eff_ohm"]
            row[f"{rail}_imax_over_imean"] = x["ball_imax_over_imean"]
            row[f"{rail}_max_drop_per_A"] = x["max_cell_drop_v"]
        pk = max(row["supply_peak_fraction"], row["return_peak_fraction"])
        row["peak_fraction"] = pk
        for s, i in sc.items():
            row[f"i_ball_max_A__{s}"] = pk * i
            row[f"pass__{s}"] = bool(pk * i <= crit_a())
        rows.append(row)
    return rows


def matched_count(screen, counts, kw, scen=None):
    """Smallest legal count passing `scen` (default MATCH_SCEN) for both architectures on the
    screen AND on the verification level."""
    scen = scen or MATCH_SCEN
    common = sorted(set(counts["Z1"]) & set(counts["Z2"]))
    cand = [n for n in common
            if all(next((r[f"pass__{scen}"] for r in screen
                         if r["arch"] == a and r["n_per_rail"] == n), False)
                   for a in ("Z1", "Z2"))]
    for n in cand:
        vj = [(a, rail, n, VERIFY_LEVEL, kw) for a in ("Z1", "Z2")
              for rail in ("supply", "return")]
        v = {r["arch"]: r for r in peak_rows(run_pool(vj))}
        if all(v[a][f"pass__{scen}"] for a in ("Z1", "Z2")):
            return n
    return None


#: declared before use (TCPMT round 3): when no legal count closes the production state for
#: both architectures, the network is built at the count of least worst production ball
#: current (minimax over Z1/Z2 on the level-1 screen; k_eq scales every count alike, so the
#: count does not depend on it), verified on the resolved level and flagged NOT_CLOSED.
FALLBACK_RULE = ("no legal count closes the production state for both architectures: the "
                 "count of least worst (Z1, Z2) production ball current on the screen, "
                 "verified on the resolved level; the ball criterion is VIOLATED there")


def fallback_count(screen, counts, kw, scen=None):
    """The FALLBACK_RULE count and its record."""
    scen = scen or MATCH_SCEN
    common = sorted(set(counts["Z1"]) & set(counts["Z2"]))
    by = {(r["arch"], r["n_per_rail"]): r for r in screen}

    def worst(n):
        return max(by[(a, n)][f"i_ball_max_A__{scen}"] for a in ("Z1", "Z2"))
    n = min((m for m in common if ("Z1", m) in by and ("Z2", m) in by),
            key=lambda m: (worst(m), m))
    vj = [(a, rail, n, VERIFY_LEVEL, kw) for a in ("Z1", "Z2") for rail in ("supply", "return")]
    v = {r["arch"]: r for r in peak_rows(run_pool(vj))}
    return n, {"status": "NOT_CLOSED", "rule": FALLBACK_RULE, "scenario": scen,
               "n_per_rail": n, "criterion_A": crit_a(),
               "screen_peak_A": {a: by[(a, n)][f"i_ball_max_A__{scen}"] for a in ("Z1", "Z2")},
               "verified_peak_A": {a: v[a][f"i_ball_max_A__{scen}"] for a in v},
               "verified_level": VERIFY_LEVEL,
               "k_eq_that_closes_at_n": {a: production_k()[0] * crit_a()
                                         / v[a][f"i_ball_max_A__{scen}"] for a in v}}


def verified_peaks(n, kw):
    """{arch: verified (level-2) production ball current at n per rail} (DC peak x k_eq)."""
    vj = [(a, rail, n, VERIFY_LEVEL, kw) for a in ("Z1", "Z2") for rail in ("supply", "return")]
    return {r["arch"]: r[f"i_ball_max_A__{PRODUCTION_SCEN}"] for r in peak_rows(run_pool(vj))}


def port_model_ball_rms(n, crit=None):
    """Z1's worst-ball RMS at n balls per rail from the harmonic port model of the recommended
    decoupling (tcpmt_decap_placement.ball_rms_at_counts, at the decoupling chain's S0
    current), scaled to the production 48-V current of Z1 (production_i_avg; the S0 current
    when no production case exists). Needs the decoupling chain of this root (placement in
    input_decoupling.json); without it the RMS is not evaluated (recorded). `crit`: the
    per-ball criterion of its passes_rms flag (default: crit_a())."""
    try:
        import tcpmt_decap_placement as PL
        if "placement" not in json.loads(PL.CI.JSON_OUT.read_text()):
            raise FileNotFoundError("no placement in input_decoupling.json")
        raw = PL.ball_rms_at_counts([n], crit_a() if crit is None else crit)[int(n)]
    except (FileNotFoundError, KeyError) as e:
        return {"I_ball_rms_max_A": None, "note": f"not evaluated: {e}"}
    i_prod = production_i_avg("Z1")
    scale = (i_prod / raw["I_total_dc_A"]) if i_prod else 1.0
    return {**raw, "I_ball_rms_max_A_at_S0_current": raw["I_ball_rms_max_A"],
            "I_ball_rms_max_A": raw["I_ball_rms_max_A"] * scale,
            "I_avg_production_A": i_prod, "scale_to_production": scale}


def screen_from_csv(path=None):
    """The committed exhaustive screen (per-ball peak fraction per ampere at every legal count),
    re-scored at the CURRENT scenario currents: the fractions do not depend on the current."""
    path = path or (OUT / "bga_count_screen.csv")
    rows = []
    cur = {a: scenarios(a) for a in ("Z1", "Z2")}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            a, n, pk = r["arch"], int(r["n_per_rail"]), float(r["peak_fraction"])
            if n > N_MAX_PER_RAIL:                    # declared cap (review round 3)
                continue
            row = {"arch": a, "n_per_rail": n, "level": int(r["level"]),
                   "terminal_mode": r["terminal_mode"], "peak_fraction": pk}
            for s, i in cur[a].items():
                row[f"i_ball_max_A__{s}"] = pk * i
                row[f"pass__{s}"] = bool(pk * i <= crit_a())
            rows.append(row)
    return rows


def reclose():
    """Re-close the 48-V BGA at the production waveform WITHOUT regenerating the network: the
    committed level-1 screen re-scored at the HV_SDEC current, the candidate minima verified on
    the resolved level (n0 - 2, n0, n0 + 2, for both architectures), the count at the upper end
    of the k_eq band, and the verdict at the network's count.

    REVIEW ROUND 3 (the authors' decision of 2026-11-19; RECLOSE_RULE): the per-ball target is
    the feasibility stage's (tcpmt_feasibility.LIMITS: bga_A_per_ball, with the conservative
    bga_A_per_ball_sensitivity reported), ONE rule applies to every integration (the verified
    level-2 DC peak x k_eq), and the ball count stays at the MODELLED arrangement -- the
    package network's count (at most N_MAX_PER_RAIL per rail), no reallocation: the verdict
    (ball_currents_at_count, matched_count = that count) is taken there, under the target and
    under the sensitivity. Z1's worst-ball RMS of the harmonic port model is reported as an
    idealized bound (all balls tied to an ideal board node), not used for the verdict. The
    count minima at the target (closure, matched_count_dc_rule, matched_count_S0) are a
    provisioning sensitivity, not adopted. Writes bga_count_production.json."""
    global _K_FROM_CHAIN, _CRIT_A
    import design_record as DR
    t0 = time.time()
    _K_FROM_CHAIN = True
    target, sens, target_src, policy = bga_target()
    _CRIT_A = target                        # the pass flags of the screen and verification
    pn = json.loads((OUT / "package_network.json").read_text())
    if ((pn.get("meta") or {}).get("design") or {}).get("design") != DR.name():
        raise SystemExit(f"package_network.json is not of the design in force ({DR.name()}): "
                         f"rebuild it (final_closure_pkg_network.py) before the re-closure")
    n_model = int(pn["matched_count"])      # the modelled arrangement (no reallocation)
    screen = screen_from_csv()
    counts = {a: sorted(r["n_per_rail"] for r in screen if r["arch"] == a) for a in ("Z1", "Z2")}
    if not all(n_model in counts[a] for a in counts):
        raise SystemExit(f"the network's count ({n_model} per rail) is not a legal count of "
                         f"bga_count_screen.csv: rebuild the network and its screen")
    kw = {"mode": "VIN_PAD"}
    k, band = production_k()
    out = {"criterion_A_per_ball": target, "criterion_sensitivity_A_per_ball": sens,
           "criterion_source": f"tcpmt_feasibility.LIMITS bga_A_per_ball: {target_src}",
           "bga_policy_in_force": policy,
           "k_eq": k, "k_eq_band": band,
           "k_source": ("the results root's decoupling chain (input_decoupling.json)"
                        if chain_k() else "the design record's committed k"),
           "currents_A": {a: scenarios(a) for a in ("Z1", "Z2")},
           "i_avg_production_A": {a: production_i_avg(a) for a in ("Z1", "Z2")},
           "screen": "bga_count_screen.csv (level %d), re-scored" % SCREEN_LEVEL,
           "verify_level": VERIFY_LEVEL, "closure": {}, "closure_sensitivity": {}}
    for a in ("Z1", "Z2"):
        for s in ("HV_S0", PRODUCTION_SCEN):
            ok = [r["n_per_rail"] for r in screen if r["arch"] == a and r[f"pass__{s}"]]
            if not ok:
                out["closure"][f"{a}__{s}"] = {"status": "NOT_SATISFIABLE_AT_ANY_LEGAL_COUNT"}
                continue
            n0 = min(ok)
            vj = [(a, rail, n, VERIFY_LEVEL, kw) for n in (n0 - 2, n0, n0 + 2)
                  if n in counts[a] for rail in ("supply", "return")]
            ver = {r["n_per_rail"]: r for r in peak_rows(run_pool(vj))}
            fail_above = [r["n_per_rail"] for r in screen if r["arch"] == a
                          and r["n_per_rail"] > n0 and not r[f"pass__{s}"]]
            v0, lo = ver.get(n0), ver.get(n0 - 2)
            out["closure"][f"{a}__{s}"] = {
                "status": ("CLOSED" if v0 and v0[f"pass__{s}"] and (lo is None or not
                                                                     lo[f"pass__{s}"])
                           else "SCREEN_ONLY_NOT_VERIFIED" if not (v0 and v0[f"pass__{s}"])
                           else "NOT_MINIMAL_LOWER_COUNT_ALSO_PASSES"),
                "n_min": n0, "peak_at_n_min_A": v0[f"i_ball_max_A__{s}"] if v0 else None,
                "peak_at_lower_A": lo[f"i_ball_max_A__{s}"] if lo else None,
                "verified": {str(n): {"peak_A": r[f"i_ball_max_A__{s}"],
                                      "peak_fraction": r["peak_fraction"],
                                      "r_loop_ohm": r["supply_r_eff_ohm"] + r["return_r_eff_ohm"],
                                      "pass": r[f"pass__{s}"]} for n, r in ver.items()},
                "larger_counts_that_FAIL_on_screen": fail_above}
        # the upper end of the loop-inductance band
        i_prod = out["currents_A"][a][PRODUCTION_SCEN]
        i_hi = band[1] / k * i_prod
        ok = [r["n_per_rail"] for r in screen if r["arch"] == a and r["peak_fraction"] * i_hi
              <= target]
        out["closure"][f"{a}__{PRODUCTION_SCEN}__k_hi"] = {"k": band[1],
                                                         "n_min_screen": min(ok) if ok else None}
        # the conservative sensitivity of the target, on the screen (no verification solves)
        ok = [r["n_per_rail"] for r in screen if r["arch"] == a and r["peak_fraction"] * i_prod
              <= sens]
        out["closure_sensitivity"][f"{a}__{PRODUCTION_SCEN}"] = {
            "criterion_A": sens, "n_min_screen": min(ok) if ok else None,
            "status": "SCREEN_ONLY_NOT_VERIFIED" if ok else "NOT_SATISFIABLE_AT_ANY_LEGAL_COUNT"}
    # provisioning sensitivity (not adopted): the smallest common count passing the DC peak x
    # k_eq rule at the target for both architectures (screen + level-2 verification)
    n_dc = matched_count(screen, counts, kw, PRODUCTION_SCEN)
    out["closure_rule"] = RECLOSE_RULE
    out["n_max_per_rail"] = N_MAX_PER_RAIL
    out["count_rule"] = ("fixed at the modelled arrangement: the package network's count "
                         "(package_network.json matched_count), no reallocation (review round 3)")
    out["matched_count_dc_rule"] = n_dc
    # THE VERDICT at the modelled arrangement: verified DC peak x k_eq, one rule for all
    n = n_model
    out["matched_count"] = n
    v = verified_peaks(n, kw)
    r_ = port_model_ball_rms(n, target)
    by = {(r["arch"], r["n_per_rail"]): r for r in screen}
    cur = {}
    for a in ("Z1", "Z2"):
        i_rms = r_.get("I_ball_rms_max_A") if a == "Z1" else None
        cur[a] = {"I_ball_closure_rule_A": v[a], "I_ball_rms_max_A": i_rms, "I_ball_A": v[a],
                  "passes": bool(v[a] <= target), "passes_sensitivity": bool(v[a] <= sens),
                  "rms_bound_within_target": None if i_rms is None else bool(i_rms <= target),
                  "screen_peak_A": (by.get((a, n)) or {}).get(f"i_ball_max_A__{PRODUCTION_SCEN}"),
                  "k_eq_max_at_target": k * target / v[a],
                  "k_eq_max_at_sensitivity": k * sens / v[a],
                  "basis": ("verified DC peak x k_eq (one rule for every integration); the port "
                            "model's worst-ball RMS is an idealized bound (all balls tied to an "
                            "ideal board node), reported, not the verdict"
                            if a == "Z1" else "verified DC peak x k_eq (one rule for every "
                                              "integration; no port model of Z2's feed)")}
    closed = all(c["passes"] for c in cur.values())
    out["ball_currents_at_count"] = {
        "n_per_rail": n, "criterion_A": target, "criterion_sensitivity_A": sens,
        "per_arch": cur, "port_model": r_,
        "status": "CLOSED" if closed else "NOT_CLOSED",
        "status_at_sensitivity": ("CLOSED" if all(c["passes_sensitivity"] for c in cur.values())
                                  else "NOT_CLOSED"),
        "rule": RECLOSE_RULE}
    out["match_fallback"] = None if closed else {
        "status": "NOT_CLOSED",
        "rule": ("the count is fixed at the modelled arrangement (no reallocation): the "
                 "per-ball target is VIOLATED there"),
        "scenario": PRODUCTION_SCEN, "n_per_rail": n, "criterion_A": target,
        "screen_peak_A": {a: cur[a]["screen_peak_A"] for a in cur},
        "verified_peak_A": dict(v), "verified_level": VERIFY_LEVEL,
        "k_eq_that_closes_at_n": {a: cur[a]["k_eq_max_at_target"] for a in cur},
        "rms_port_model_A": {"Z1": cur["Z1"]["I_ball_rms_max_A"]}}
    out["matched_count_S0"] = matched_count(screen, counts, kw, "HV_S0")
    out["wall_s"] = round(time.time() - t0, 1)
    out["design"] = DR.design_identity()
    PRODUCTION_OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps({k_: v for k_, v in out.items() if k_ != "closure"}, indent=1, default=float))
    for k_, v in out["closure"].items():
        print(k_, {x: v[x] for x in ("status", "n_min", "peak_at_n_min_A", "n_min_screen")
                   if x in v})
    return out


def main():
    if sys.argv[1:2] == ["reclose"]:
        return reclose()
    t0 = time.time()
    counts = {a: legal_counts(a) for a in ("Z1", "Z2")}
    kw = {"mode": "VIN_PAD"}
    # ---- 1. exhaustive screen ------------------------------------------
    # TCPMT round 3: --reuse-screen re-scores the committed level-1 screen of THIS cell grid
    # (bga_count_screen.csv; the per-ball fractions do not depend on the current) at the
    # scenario currents in force -- a new production k needs no new screen. The screen's
    # counts must be the legal counts of the grid in force (checked).
    if "--reuse-screen" in sys.argv[1:]:
        screen = screen_from_csv()
        have = {a: sorted(r["n_per_rail"] for r in screen if r["arch"] == a) for a in counts}
        if have != {a: sorted(counts[a]) for a in counts}:
            raise SystemExit("bga_count_screen.csv was screened on another cell grid: rerun "
                             "the screen (no --reuse-screen)")
        print(f"screen: {len(screen)} rows re-scored from bga_count_screen.csv", flush=True)
    else:
        jobs = [(a, rail, n, SCREEN_LEVEL, kw) for a in counts for n in counts[a]
                for rail in ("supply", "return")]
        screen = peak_rows(run_pool(jobs))
        print(f"screen: {len(screen)} rows in {time.time()-t0:.0f}s", flush=True)

    # ---- 2. verify candidate minima on the resolved level ---------------
    closure, verify_jobs = {}, set()
    for a in counts:
        for s in SCEN:
            ok = [r["n_per_rail"] for r in screen if r["arch"] == a and r[f"pass__{s}"]]
            if ok:
                n0 = min(ok)
                for n in (n0 - 2, n0, n0 + 2):
                    if n in counts[a]:
                        verify_jobs.add((a, n))
    vj = [(a, rail, n, VERIFY_LEVEL, kw) for a, n in sorted(verify_jobs)
          for rail in ("supply", "return")]
    verify = peak_rows(run_pool(vj)) if vj else []
    vby = {(r["arch"], r["n_per_rail"]): r for r in verify}
    for a in counts:
        for s in SCEN:
            ok = [r["n_per_rail"] for r in screen if r["arch"] == a and r[f"pass__{s}"]]
            if not ok:
                best = min(screen, key=lambda r: r[f"i_ball_max_A__{s}"]
                           if r["arch"] == a else 1e99)
                closure[f"{a}__{s}"] = {
                    "status": "NOT_SATISFIABLE_AT_ANY_LEGAL_COUNT",
                    "best_peak_A": best[f"i_ball_max_A__{s}"],
                    "best_at_n": best["n_per_rail"],
                    "largest_legal_count": counts[a][-1], "criterion_A": I_CRIT_A}
                continue
            n0 = min(ok)
            v = vby.get((a, n0))
            lo = vby.get((a, n0 - 2))
            passes = bool(v and v[f"pass__{s}"])
            lower_fails = (lo is None) or (not lo[f"pass__{s}"])
            fail_above = [r["n_per_rail"] for r in screen
                          if r["arch"] == a and r["n_per_rail"] > n0
                          and not r[f"pass__{s}"]]
            closure[f"{a}__{s}"] = {
                "status": ("CLOSED" if passes and lower_fails else
                           "SCREEN_ONLY_NOT_VERIFIED" if not passes else
                           "NOT_MINIMAL_LOWER_COUNT_ALSO_PASSES"),
                "n_min": n0, "verified_level": VERIFY_LEVEL,
                "peak_at_n_min_A": v[f"i_ball_max_A__{s}"] if v else None,
                "peak_at_lower_A": lo[f"i_ball_max_A__{s}"] if lo else None,
                "larger_counts_that_FAIL": fail_above,
                "criterion_A": I_CRIT_A}
    print("closure:", {k: (v["status"], v.get("n_min")) for k, v in closure.items()},
          flush=True)

    # ---- 3. matched count: smallest N passing the PRODUCTION waveform (MATCH_SCEN; review
    # round 2: the implemented decoupling, k_eq = 1.65) for BOTH, verified ---
    n_match = matched_count(screen, counts, kw)
    print(f"matched count at {MATCH_SCEN}:", n_match, flush=True)
    fallback = None
    if n_match is None:
        n_match, fallback = fallback_count(screen, counts, kw)
        print(f"NOT CLOSED at {MATCH_SCEN}: network built at the fallback count {n_match} "
              f"({fallback['verified_peak_A']} A per ball vs {I_CRIT_A} A)", flush=True)

    # ---- 4. converged networks at the matched count ----------------------
    fj = [(a, rail, n_match, lv, kw) for a in ("Z1", "Z2")
          for rail in ("supply", "return") for lv in FINAL_LEVELS]
    fres = run_pool(fj)
    conv = {}
    for a in ("Z1", "Z2"):
        for rail in ("supply", "return"):
            rr = sorted([r for r in fres if r["arch"] == a and r["rail"] == rail],
                        key=lambda r: r["level"])
            fine, mid = rr[-1], rr[-2]
            d = {m: abs(fine[m] - mid[m]) / abs(fine[m]) for m in RF.CONV_METRICS}
            conv[f"{a}_{rail}"] = {
                "deltas": d, "worst_metric": max(d, key=d.get),
                "worst_delta": max(d.values()), "converged": max(d.values()) < RF.CONV_THRESH,
                "levels": [{k: v for k, v in r.items() if k not in ("i_ball_a",
                                                                     "ball_xy")}
                           for r in rr],
                "final": {k: fine[k] for k in ("r_eff_ohm", "max_cell_drop_v",
                                               "i_ball_max_a", "ball_imax_over_imean",
                                               "n_cv", "energy_residual_rel")},
                "i_ball_frac": fine["i_ball_a"], "ball_xy": fine["ball_xy"]}
    loop = {}
    for a in ("Z1", "Z2"):
        rs = conv[f"{a}_supply"]["final"]["r_eff_ohm"]
        rr = conv[f"{a}_return"]["final"]["r_eff_ohm"]
        sc = scenarios(a)
        loop[a] = {"n_per_rail": n_match, "r_supply_ohm": rs, "r_return_ohm": rr,
                   "r_loop_ohm": rs + rr,
                   "converged": conv[f"{a}_supply"]["converged"]
                                and conv[f"{a}_return"]["converged"],
                   "loss_w": {s: i ** 2 * (rs + rr) for s, i in sc.items()},
                   "i_scenario_a": sc}

    # ---- 5. controlled cutout experiment at the matched count -----------
    full, cut = PCO.bga_lattice_sites(), PCO.bga_lattice_sites(23.36)
    cj = []
    for tag, c, rule in (("CTRL_FULL", full, "nearest_symmetric"),
                         ("CTRL_CUTOUT", cut, "nearest_symmetric"),
                         ("CTRL_CUTOUT_OUTER", cut, "outer_perimeter")):
        for rail in ("supply", "return"):
            cj.append(("CTRL", rail, n_match, VERIFY_LEVEL,
                       dict(kw, candidate_override=c, allocation_rule=rule)))
    K.register_architecture("CTRL", None)
    cres = run_pool(cj)
    ctrl = {}
    for (tag, _, rule), i in zip((("CTRL_FULL", 0, 0), ("CTRL_CUTOUT", 0, 0),
                                  ("CTRL_CUTOUT_OUTER", 0, 0)), range(3)):
        s_, r_ = cres[2 * i], cres[2 * i + 1]
        ctrl[tag] = {"r_supply_ohm": s_["r_eff_ohm"], "r_return_ohm": r_["r_eff_ohm"],
                     "r_loop_ohm": s_["r_eff_ohm"] + r_["r_eff_ohm"]}
    ctrl["delta_R_cutout_ohm"] = (ctrl["CTRL_CUTOUT"]["r_loop_ohm"]
                                  - ctrl["CTRL_FULL"]["r_loop_ohm"])
    ctrl["delta_R_placement_ohm"] = (ctrl["CTRL_CUTOUT_OUTER"]["r_loop_ohm"]
                                     - ctrl["CTRL_CUTOUT"]["r_loop_ohm"])

    # ---- 6. sensitivities at the matched count --------------------------
    sens_jobs = []
    for a in ("Z1", "Z2"):
        for mode in ("HALF_TILE", "FULL_TILE"):
            for rail in ("supply", "return"):
                sens_jobs.append((a, rail, n_match, VERIFY_LEVEL, {"mode": mode}))
        for cname, rho in K.RHO_C_CASES.items():
            for rail in ("supply", "return"):
                sens_jobs.append((a, rail, n_match, VERIFY_LEVEL,
                                  {"mode": "VIN_PAD", "rho_c": rho}))
        for tc, oc in ((2e-3, 0.30), (5e-3, 0.80), (10e-3, 0.30), (10e-3, 0.80)):
            for rail in ("supply", "return"):
                sens_jobs.append((a, rail, n_match, VERIFY_LEVEL,
                                  {"mode": "VIN_PAD", "t_cu_mm": tc, "occupancy": oc}))
    sres = run_pool(sens_jobs)
    sens = {}
    for r in sres:
        key = (r["arch"], r["terminal_mode"], r["rho_c_ohm_mm2"], r["t_cu_mm"],
               r["occupancy"])
        sens.setdefault(key, {})[r["rail"]] = r["r_eff_ohm"]
    sens_rows = [{"arch": k[0], "terminal_mode": k[1], "rho_c_ohm_mm2": k[2],
                  "t_cu_mm": k[3], "occupancy": k[4],
                  "r_loop_ohm": v["supply"] + v["return"]}
                 for k, v in sorted(sens.items()) if len(v) == 2]

    res = {"meta": {"model": "pkg_rdl_refined aligned graded FV, traced VIN pad",
                    "terminal_status": RF.TERMINAL_MODES["VIN_PAD"],
                    "criterion_A_per_ball": I_CRIT_A,
                    "criterion_classification": "ENGINEERING_CRITERION",
                    "screen_level": SCREEN_LEVEL, "verify_level": VERIFY_LEVEL,
                    "final_levels": list(FINAL_LEVELS),
                    "levels_mm": {str(k): v for k, v in RF.LEVELS.items()},
                    "conv_threshold": RF.CONV_THRESH,
                    "conv_metrics": list(RF.CONV_METRICS),
                    "exhaustive": True, "monotonicity_assumed": False,
                    "match_scenario": MATCH_SCEN, "production_k_eq": production_k()[0],
                    "wall_s": round(time.time() - t0, 1)},
           "counts_legal": {a: len(v) for a, v in counts.items()},
           "closure": closure, "matched_count": n_match, "match_fallback": fallback,
           "convergence": conv, "loop": loop, "controlled": ctrl,
           "sensitivity": sens_rows}
    res["meta"]["screen_reused"] = "--reuse-screen" in sys.argv[1:]
    res["meta"]["n_max_per_rail"] = N_MAX_PER_RAIL
    res["meta"]["closure_rule"] = CLOSURE_RULE
    res["meta"]["reclose_rule"] = RECLOSE_RULE              # the per-ball verdict (reclose)
    import design_record as DR
    res["meta"]["design"] = DR.design_identity()          # the cell grid it was closed on
    (OUT / "package_network.json").write_text(json.dumps(res, indent=1))
    if not res["meta"]["screen_reused"]:     # a re-scored screen keeps the committed CSV
        with (OUT / "bga_count_screen.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(screen[0]))
            w.writeheader(); w.writerows(screen)
    print("done in %.0fs" % (time.time() - t0))
    for a, L in loop.items():
        print(a, "N=%d R_loop=%.4f mOhm conv=%s" % (L["n_per_rail"],
              L["r_loop_ohm"] * 1e3, L["converged"]))


if __name__ == "__main__":
    main()
