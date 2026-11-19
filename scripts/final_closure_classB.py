"""Resolve every open Class-B gate: classify, then run or bound it, then judge the ordering.

Subtypes (declared in the brief, applied here per gate):
  B1  ORDERING-RELEVANT  could move a Z1/Z2 ordering; must be run or quantitatively
                         bounded before PAPER_READY
  B2  MAGNITUDE-ONLY     moves magnitudes but provably not an ordering; proved or bounded
  B3  RECLASSIFY -> C    a qualification quantity that limits claims, not comparisons

A run-based gate is judged on the sensitivity cases written by final_closure_sensitivity.py
(production mesh, HV-S0): for every observable the variant's Z1/Z2 verdict is formed with
THE comparison rule of the revision (TCPMT round 3, scripts/tcpmt_resolution.py; the same rule
as Table IV): resolved when |D + beta_D| > U95(D), D = Z2 - Z1. The production verdict is that
rule on the production pair's own nested ladders; a variant pair has no ladder of its own, so
the production pair's beta and discretization U are transferred PROVISIONALLY when both cases
pass the transfer check (solved on the production mesh), else the verdict is PENDING; the
variant's own E-T stop and reference terms enter U95. The local response is judged on each
joint's numerical U (production joints', provisional) under the production law (the law band is
solved for the tier joints only). The verdict of the superseded rule (gap > 2 x the r21 -> r31
step, ordering.json) is kept beside it (legacy_verdict) and the changes are counted
(summary.rule_change). A gate is RESOLVED when every case it needs exists and has a verdict;
whether the ordering survives is reported, never assumed. A declared B2 gate whose runs DO move
an ordering is promoted to B1 automatically.

Writes research/final_closure/classB_resolution.{csv,json} and classB_sensitivity_rows.csv
(every robustness row, including the newer cooling-A decisions of Fig. 11).
"""
from __future__ import annotations

import csv
import json
import os
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"   # campaign hook
SENS = D / "sensitivity"
sys.path.insert(0, str(R / "scripts"))

OBS = {"P_loss_package_internal_w": "package-internal loss",
       "P_loss_platform_inclusive_w": "platform-inclusive loss", "T_max_C": "peak temperature",
       "die_warpage_pv_um": "die warpage", "du_c_um": "joint displacement driver",
       "d_eps_in_per_cycle": "local inelastic response"}
GLOBAL = ("P_loss_package_internal_w", "T_max_C", "die_warpage_pv_um", "du_c_um",
          "d_eps_in_per_cycle")
THERMAL = ("P_loss_package_internal_w", "T_max_C")
MECH = ("die_warpage_pv_um", "du_c_um", "d_eps_in_per_cycle")
SCEN = "HV_S0"
H01 = ["board_h1", "board_h0_h1grid"]
#: variants that exist only for Z2 (no PCB opening, no backside converter in Z1): Z1 keeps
#: its production values
Z2_ONLY = ("z2_cooled", "z2_cooled_tim", "f1_sidewall_filled", "attach_h20", "attach_h40",
           "attach_sn", "attach_stiff", "attach_uf_soft", "attach_uf_stiff",
           "feed_heat_at_crossover", "bga_depop", "attach_dense", "attach_sparse",
           "attach_sparse_stiff", "attach_eng_p34", "attach_eng_p37", "attach_eng_p41")
#: ... and the variants that exist only for Z1 (TCPMT revision): Z2 keeps its production values
Z1_ONLY = ("z1_tier_reference",)
CONV = ["conv_k_tenth", "conv_E80_a4", "conv_E80_a10", "conv_E160_a4", "conv_E160_a10"]
WAVE = ("named 48 V scenarios HV-S0 / HV-S1 / HV-S2 (rms_currents definitions): each "
        "scenario solved through the full lineage")

#: gate -> (subtype, observables, range / source, method, cases, rationale)
GATES = {
    "board.h1_meshed": ("B1", GLOBAL, "PCB-H1: the 18-layer schedule as five depth blocks "
                        "(pcb_h1.py), against H0 on the same z grid", "runs", H01,
                        "the board is the bottom heat path and the mechanical support"),
    "board.h1_thermal_validated": ("B1", THERMAL, "H1 vs H0 on the H1 z grid", "runs", H01,
                                   "thermal half of the H0 model-form check"),
    "therm.h0_h1_compared": ("B1", THERMAL, "H1 vs H0 on the H1 z grid", "runs", H01,
                             "thermal half of the H0 model-form check"),
    "board.eta_sensitivity_run": ("B1", GLOBAL, "copper coverage eta 0.25 / 0.50 / 0.75 "
                                  "(config eta_sensitivity)", "runs",
                                  ["board_eta025", "board_eta075"],
                                  "board k_xy spans 34-98 W/mK and E 23-38 GPa over eta"),
    "board.t_only_comparison_run": ("B1", THERMAL, "PCB 2.4 vs 3.2 mm, one material dict",
                                    "runs", ["board_t3p2"], "board thickness, thermal"),
    "mech.t_only_mechanical": ("B1", MECH, "PCB 2.4 vs 3.2 mm, one material dict", "runs",
                               ["board_t3p2"], "board thickness, mechanical"),
    "tsv.density_sensitivity_run": ("B1", GLOBAL, "TSV sizing study: 64 / 729 / 1444 vias "
                                    "per cell, in the FE substrate AND the ledger", "runs",
                                    ["tsv_min", "tsv_mid"],
                                    "the adopted field is the maximum-density end"),
    "mech.f1_f2_bracket_run": ("B1", GLOBAL, "out-of-cell converter volume encapsulated "
                               "between the cells (F1, production, 1.0 mm clearance void) vs "
                               "void (F2), and F1 filled to the PCB sidewall (DEFECT #66 "
                               "construction)", "runs", ["f2_void", "f1_sidewall_filled"],
                               "the fill carries heat and load between the cells"),
    "geom.sidewall_clearance": ("B1", GLOBAL, "1.0 mm sidewall clearance void (production) "
                                "vs encapsulant filled to the PCB sidewall", "runs",
                                ["f1_sidewall_filled"],
                                "a bonded sidewall is an extra heat and load path"),
    "geom.vr_attach_height": ("B1", GLOBAL, "VR attach joint 20 / 40 um (production 30 um; "
                              "Na et al. 2022 CLOSE_ANALOG)", "runs",
                              ["attach_h20", "attach_h40"],
                              "the attach carries 1 kA and sits in the converter heat path"),
    "geom.vr_attach_density": ("B1", GLOBAL, "VR attach pitch/count: the published dense "
                               "15/30 um (Au et al. 2016) and sparse 30/80 um (Na et al. 2023) "
                               "constructions on the real lattice, production material and "
                               "height held; underfill-dominated and column-stiffened "
                               "mechanical bounds", "runs",
                               ["attach_dense", "attach_sparse", "attach_sparse_stiff"],
                               "attach resistance, vertical conduction and stiffness all scale "
                               "with the metal fraction"),
    "mat.vr_attach_material": ("B1", GLOBAL, "Cu pillar + solder cap (production) vs an all-"
                               "solder column at the Na et al. density (a resistive bound: Na "
                               "et al. report a Sn cap on a Cu post), and the column-stiffened "
                               "card", "runs", ["attach_sn", "attach_stiff"],
                               "attach conductivity, resistance and stiffness"),
    "mat.vr_attach_underfill": ("B1", MECH, "attach underfill E 4 / 12 GPa, CTE 40 / 20 ppm/K "
                                "(declared stress corners)", "runs",
                                ["attach_uf_soft", "attach_uf_stiff"],
                                "the attach couples the converter to the substrate"),
    "elec.direct_feed_loop_resistance": ("B1", ("P_loss_platform_inclusive_w",), "R_Z2_direct_feed_loop swept "
                                         "0.01-100 mOhm (direct_feed_crossover.json)",
                                         "direct_feed", [],
                                         "the external feed is unsourced: no value assumed"),
    "elec.direct_feed_heat_location": ("B1", GLOBAL, "feed loss at the largest admissible "
                                       "loop resistance (largest R*), at the HV-S0 current, "
                                       "deposited in the deepest converter tier", "runs",
                                       ["feed_heat_at_crossover"],
                                       "where the feed's heat lands is unknown"),
    "therm.cooling_model_form": ("B1", GLOBAL, "ICEPAK_EQUIVALENT_COOLING_SENSITIVITY: top "
                                 "coefficient x dT_compact/dT_CFD of the matched Icepak case",
                                 "runs", ["icepak_equivalent"],
                                 "with the short-wall-adiabatic H1 Nu the compact model "
                                 "reproduces the CFD mean base rise to 0.3 % (the superseded "
                                 "table was 16.5 % conservative)"),
    "therm.backside_interface": ("B1", GLOBAL, "Z2-COOLED through a 50 um TIM (k 3 W/mK)",
                                 "runs", ["z2_cooled_tim"],
                                 "a backside interface weakens the extra Z2 heat path"),
    "mech.bga_population": ("B1", GLOBAL, "Z2 BGA field populated at 420/528 (the 48 V balls "
                            "of the BGA-fed design removed), smeared", "runs", ["bga_depop"],
                            "the mechanical field need not carry the 48 V balls"),
    "therm.z2_cooled": ("B1", GLOBAL, "bounding Z2-COOLED: a top-type cold plate on the Z2 "
                        "converter underside; Z1 unchanged", "runs", ["z2_cooled"],
                        "an extra Z2 heat path could move any thermal ordering"),
    "board.bottom_boundary": ("B1", GLOBAL, "board-bottom film 100 / 500 W/m2K (production "
                              "10: a 30-mm coupon in natural convection) standing in for the "
                              "lateral spreading of a full server board", "runs",
                              ["board_hbot100", "board_hbot500"],
                              "the board is the second heat path of every joint"),
    "geom.tier_order": ("B1", GLOBAL, "Z1 converter tiers in the reference order HS-LS-Cf-L "
                        "(production: the repartitioned HS-Cf-LS-L of the realizability "
                        "check); components, heights unchanged; Z2 unchanged", "runs",
                        ["z1_tier_reference"],
                        "tier order sets where each device sits in the heat path"),
    "mat.gan_bounded": ("B1", GLOBAL, "GaN tiers at half the Si carrier conductivity "
                        "(stress bound on the unresolved epi)", "runs", ["gan_k_half"],
                        "the device tiers sit in the converter heat path"),
    "mat.mlcc_bounded": ("B1", GLOBAL, "converter medium k/10, and the card's own E 80-160 "
                         "GPa x CTE 4-10 ppm/K corners", "runs", CONV,
                         "flying-cap tier on a generic PROVISIONAL card"),
    "mat.inductor_tier_bounded": ("B1", GLOBAL, "converter medium k/10, and the card's own "
                                  "E 80-160 GPa x CTE 4-10 ppm/K corners", "runs", CONV,
                                  "inductor/Cout tier on the same generic card"),
    "elec.contact_resistance_bounded": ("B1", ("P_loss_package_internal_w",), "rho_c 1e-6 / 1e-5 / 1e-4 "
                                        "ohm mm^2 on the package 48 V RDL (package_network "
                                        "sensitivity; Z1 only: the direct-fed Z2 has no package "
                                        "48 V RDL)", "network", ["rho_c"],
                                        "unsourced contact resistance in the 48 V path"),
    "elec.rdl10um_electrical_model": ("B1", ("P_loss_package_internal_w",), "package 48 V RDL t_Cu 2 / 5 / 10 "
                                      "um x occupancy 0.3 / 0.8 (package_network "
                                      "sensitivity; Z1 only)", "network", ["t_cu", "occupancy"],
                                      "the 10 um tier's sheet resistance is undefined"),
    "elec.hv_input_waveform": ("B1", tuple(OBS), WAVE, "scenarios", [],
                               "the 48 V waveform is not derivable from the pinned model"),
    "elec.hv_waveform_determination": ("B1", tuple(OBS), WAVE, "scenarios", [],
                                       "determined unresolvable from available sources"),
    "elec.z1_hv_rms_current": ("B1", tuple(OBS), WAVE, "scenarios", [],
                               "the 48 V RMS follows the scenario"),
    "elec.bga_rms_current": ("B1", tuple(OBS), WAVE, "scenarios", [],
                             "the BGA RMS follows the scenario"),
    "elec.individual_branch_waveforms": ("B2", ("P_loss_package_internal_w",), "converter-internal branch "
                                         "RMS: identical converter model in both "
                                         "architectures", "common_mode", [],
                                         "the converter terms depend on T_conv only"),
    "elec.pad_count_criterion": ("B2", GLOBAL, "pad sweep end: the voltage-drop floor, 4 "
                                 "pads per rail per cell (vs 2040)", "runs", ["pad_drop"],
                                 "same pad field and current in both architectures"),
    "elec.pad_loss_closed": ("B2", GLOBAL, "pad sweep end: the voltage-drop floor, 4 pads "
                             "per rail per cell (vs 2040)", "runs", ["pad_drop"],
                             "same pad field and current in both architectures"),
}


def J(p):
    return json.loads(Path(p).read_text()) if Path(p).exists() else None


def _vals(case):
    if case is None or "mechanics" not in case:
        return None
    m, c = case["mechanics"], case["mechanics"]["joint_search"]["critical"]
    return {"P_loss_package_internal_w": case["P_loss_w"], "T_max_C": case["thermal"]["T_max_C"],
            "die_warpage_pv_um": m["die_warpage_pv_um"], "du_c_um": c["du_um"],
            "T_joint_C": c["T_C"], "d_eps_in_per_cycle": (case.get("local") or {}).get(
                "d_peeq_per_cycle")}


def _verdict(a, b, u):
    """SUPERSEDED rule (kept for the legacy column): gap > 2 x the relative r21 -> r31 step."""
    if a is None or b is None:
        return "not rankable", None
    gap = abs(a - b) / max(abs(a), abs(b))
    if u is None:
        return "unresolved", gap
    return ("Z1 lower" if a < b else "Z2 lower") if gap > 2 * u else "unresolved", gap


# ------------------------------------------------------------------ the unified rule
#: observable -> tcpmt_uncertainty output key
UKEY = {"P_loss_package_internal_w": "P", "P_loss_platform_inclusive_w": "P",
        "T_max_C": "T", "die_warpage_pv_um": "warp", "du_c_um": "du"}
_RULE_CACHE: dict = {}


def _rule():
    """(tcpmt_uncertainty, tcpmt_resolution, reference pairs), loaded once."""
    if not _RULE_CACHE:
        import tcpmt_resolution as RULE
        import tcpmt_uncertainty as TU
        _RULE_CACHE.update(TU=TU, RULE=RULE, pairs=TU.reference_pairs())
    return _RULE_CACHE["TU"], _RULE_CACHE["RULE"], _RULE_CACHE["pairs"]


def _mesh(case):
    import tcpmt_uncertainty as TU
    return TU.mesh_signature(case)


def _local_u():
    """Relative numerical U of the production local response of each integration (round-2
    local mesh study at the variants' level and settings)."""
    lm = (J(D / "local_mesh_study.json") or {}).get("cases", {})
    return {a: (lm.get(f"{a}_{SCEN}") or {}).get("U") for a in ("Z1", "Z2")}


def rule_verdict(k, va, vb, mesh_a=None, mesh_b=None):
    """Z1/Z2 verdict of one observable under the unified rule. Returns (verdict, record)."""
    TU, RULE, pairs = _rule()
    if va is None or vb is None:
        return "not rankable", {"resolved": None}
    if k == "d_eps_in_per_cycle":
        u = _local_u()
        if u.get("Z1") is None or u.get("Z2") is None:
            return RULE.PENDING, {"resolved": None}
        u95 = RULE.quad(u["Z1"] * va, u["Z2"] * vb)
        j = RULE.judge(vb - va, 0.0, u95)
        j.update({"provisional": True, "law_band": "not evaluated for this case (the band is "
                                                   "solved on the tier joints)",
                  "basis": "production joints' local numerical U"})
        return RULE.verdict_label(j["resolved"], j["D_corrected"], "Z1", "Z2"), j
    rec = TU.variant_judgement("Z1", "Z2", UKEY[k], va, vb, mesh_a, mesh_b, pairs)
    return rec["verdict"], rec


def production_rule_verdicts(base):
    """The production Z1/Z2 verdict of every observable under the unified rule: the pair's
    own nested ladders (tcpmt_uncertainty.compare on the S0 production cases)."""
    TU, RULE, _pairs = _rule()
    out = {}
    for k in GLOBAL:
        va, vb = (base.get("Z1") or {}).get(k), (base.get("Z2") or {}).get(k)
        if va is None or vb is None:
            continue
        if k == "d_eps_in_per_cycle":
            out[k] = rule_verdict(k, va, vb)
            continue
        r = TU.compare("A", "Z1", "Z2", UKEY[k], TU.reference_path("Z1"),
                       TU.reference_path("Z2"), va, vb)
        out[k] = (RULE.verdict_label(r["resolved"], r["D_corrected"], "Z1", "Z2"), r)
    return out


def _uncertainty(od):
    return {k: (o.get("uncertainty_rel") or {}).get(SCEN) for k, o in od.items()}


def base_case(arch):
    import final_closure_physical_etm as E
    return J(E.case_path(arch, SCEN))


def judge_runs(cases, observables, od, unc):
    """Variant verdicts against the production verdicts, per observable."""
    import final_closure_physical_etm as E                         # noqa: F401
    base = {a: _vals(base_case(a)) for a in ("Z1", "Z2")}
    lm = (J(D / "local_mesh_study.json") or {}).get("cases", {})
    for a in base:      # production local response at the variants' level and settings
        if base[a] is not None:
            base[a]["d_eps_in_per_cycle"] = (((lm.get(f"{a}_{SCEN}") or {}).get("levels")
                                              or {}).get("L0") or {}).get("d_peeq_per_cycle")
    prod_rule = production_rule_verdicts(base)
    base_mesh = {a: _mesh(base_case(a)) for a in ("Z1", "Z2")}
    rows, missing = [], []
    for v in cases:
        var, mesh = {}, {}
        for a in ("Z1", "Z2"):
            f = SENS / f"etm_{a}_{SCEN}__{v}.json"
            c = J(f)
            if c is None and v in Z2_ONLY and a == "Z1":
                var[a], mesh[a] = base[a], "reference"   # Z1 is unchanged by definition
                continue
            if c is None and v in Z1_ONLY and a == "Z2":
                var[a], mesh[a] = base[a], "reference"   # Z2 is unchanged by definition
                continue
            var[a], mesh[a] = _vals(c), _mesh(c)
            if var[a] is None:
                missing.append(f.name)
        for k in observables:
            if any(var[a] is None for a in var):
                continue
            va, vb = var["Z1"].get(k), var["Z2"].get(k)
            if k == "d_eps_in_per_cycle" and (va is None or vb is None):
                continue
            u = unc.get(k)
            legacy, gap = _verdict(va, vb, u)
            verdict, rec = rule_verdict(k, va, vb, mesh["Z1"], mesh["Z2"])
            prod = (prod_rule.get(k) or (None,))[0]
            legacy_prod = (od.get(k) or {}).get("per_scenario", {}).get(SCEN)
            ch = {a: ((var[a][k] - base[a][k]) / base[a][k]
                      if base[a] and base[a].get(k) else None) for a in ("Z1", "Z2")}
            rows.append({"case": v, "observable": k, "Z1": va, "Z2": vb,
                         "change_rel": ch, "gap_rel": gap,
                         "D": vb - va, "bias": rec.get("bias"),
                         "D_corrected": rec.get("D_corrected"), "U95": rec.get("U95"),
                         "provisional": rec.get("provisional"),
                         "transfer_checks": rec.get("transfer_checks"),
                         "uncertainty_rel": (rec["U95"] / max(abs(va), abs(vb))
                                             if rec.get("U95") is not None else None),
                         "verdict": verdict, "production_verdict": prod,
                         "robust": (verdict == prod) if verdict != "pending" else None,
                         "legacy_verdict": legacy, "legacy_production_verdict": legacy_prod,
                         "legacy_uncertainty_rel": u})
    return rows, missing


def h1_vs_control(observables):
    """PCB-H1 against the H0 card on the SAME five-block z grid: the material
    representation alone. (Against production, H1 also differs by its z resolution, and in
    Z2 the block boundaries re-slice the converter tiers that share the board's z range.)"""
    out = []
    for k in observables:
        ch = {}
        for a in ("Z1", "Z2"):
            h1, h0 = (_vals(J(SENS / f"etm_{a}_{SCEN}__{v}.json")) for v in H01)
            ch[a] = ((h1[k] - h0[k]) / h0[k]) if (h1 and h0 and h0.get(k)) else None
        if any(v is None for v in ch.values()):
            continue
        out.append({"case": "board_h1 vs board_h0_h1grid", "observable": k,
                    "change_rel": ch, "verdict": "material effect only",
                    "within_mesh_tolerance": all(abs(v) < 0.02 for v in ch.values()),
                    "robust": None})
    return out


def judge_network(params, od):
    """Package 48 V RDL loss over the package-network sensitivity rows, at HV-S0."""
    pn = J(D / "package_network.json")
    led = (J(D / "electrical_ledger.json") or {}).get("rows", [])
    fin = {(r["arch"], r["scenario"]): r for r in J(D / "final_results.json") or []}
    prod = {"rho_c_ohm_mm2": 1e-5, "t_cu_mm": 0.005, "occupancy": 0.3}
    key = {"rho_c": "rho_c_ohm_mm2", "t_cu": "t_cu_mm", "occupancy": "occupancy"}
    rows = []
    import final_closure_ledger as FL
    # only a BGA-FED architecture has a package 48 V network to perturb; the direct-fed
    # Z2's 48 V never enters the package, so its loss does not move here (dp = 0)
    fed = [a for a in ("Z1", "Z2") if FL.HV_FEED[a] == "BGA_FED"]
    p_hv = {a: sum(r["P_w"] for r in led if r["arch"] == a and r["scenario"] == SCEN
                   and r["term"].startswith("P_pkg_RDL_HV")) for a in ("Z1", "Z2")}
    r0 = {a: pn["loop"][FL.NETWORK_KEY[a]]["r_loop_ohm"] for a in fed}
    sens = [s for s in pn["sensitivity"] if s["terminal_mode"] == "VIN_PAD"]
    combos = sorted({tuple(s[key[p]] for p in params) for s in sens
                     if all(s[k] == prod[k] for k in prod if k not in [key[p] for p in params])})
    for combo in combos:
        sel = {s["arch"]: s for s in sens
               if tuple(s[key[p]] for p in params) == combo
               and all(s[k] == prod[k] for k in prod if k not in [key[p] for p in params])}
        if not all(FL.NETWORK_KEY[a] in sel for a in fed):
            continue
        dp = {a: (p_hv[a] * (sel[FL.NETWORK_KEY[a]]["r_loop_ohm"] / r0[a] - 1.0)
                  if a in fed else 0.0) for a in ("Z1", "Z2")}
        loss = {a: fin[(a, SCEN)]["P_loss_w"] + dp[a] for a in ("Z1", "Z2")}
        u = (od.get("P_loss_package_internal_w") or {}).get("uncertainty_rel", {}).get(SCEN)
        legacy, gap = _verdict(loss["Z1"], loss["Z2"], u)
        # the production solve, adjusted: the production meshes (transfer check passes)
        verdict, rec = rule_verdict("P_loss_package_internal_w", loss["Z1"], loss["Z2"],
                                    *(_mesh(base_case(a)) for a in ("Z1", "Z2")))
        prod_v = production_rule_verdicts({a: _vals(base_case(a)) for a in ("Z1", "Z2")}).get(
            "P_loss_package_internal_w", (None,))[0]
        rows.append({"case": ", ".join(f"{p}={c:g}" for p, c in zip(params, combo)),
                     "observable": "P_loss_package_internal_w", "Z1": loss["Z1"],
                     "Z2": loss["Z2"],
                     "change_rel": {a: dp[a] / fin[(a, SCEN)]["P_loss_w"] for a in dp},
                     "delta_W": dp, "gap_rel": gap, "D_corrected": rec.get("D_corrected"),
                     "U95": rec.get("U95"), "provisional": rec.get("provisional"),
                     "uncertainty_rel": (rec["U95"] / max(loss.values())
                                         if rec.get("U95") is not None else None),
                     "verdict": verdict, "production_verdict": prod_v,
                     "robust": verdict == prod_v,
                     "legacy_verdict": legacy, "legacy_uncertainty_rel": u,
                     "legacy_production_verdict": (od.get("P_loss_package_internal_w") or {})
                     .get("per_scenario", {}).get(SCEN),
                     "method": "first order: the 48 V RDL rows scale with the swept loop "
                               "resistance at the solved HV-S0 current; the thermal "
                               "feedback of a <= 2 W change is second order"})
    return rows


def judge_common_mode():
    """The converter terms are one architecture-independent model evaluated at each
    architecture's own converter temperature, so any common rescaling k of them (which is
    what an unknown branch waveform does) keeps the sign of their Z1 - Z2 difference."""
    led = (J(D / "electrical_ledger.json") or {}).get("rows", [])
    conv = ("P_conv_hs", "P_conv_ls", "P_conv_inductor_dcr", "P_conv_cap_esr",
            "P_intraVR_metal", "P_intraVR_vertical")
    tot = {a: sum(r["P_w"] for r in led if r["arch"] == a and r["scenario"] == SCEN)
           for a in ("Z1", "Z2")}
    c = {a: sum(r["P_w"] for r in led if r["arch"] == a and r["scenario"] == SCEN
                and r["term"] in conv) for a in ("Z1", "Z2")}
    d_conv, d_rest = c["Z1"] - c["Z2"], (tot["Z1"] - c["Z1"]) - (tot["Z2"] - c["Z2"])
    k_flip = (-d_rest / d_conv) if d_conv and (d_rest / d_conv) < 0 else None
    # Z1 - Z2 = d_rest + k d_conv is linear in k, so the sign it has at the modelled k = 1
    # holds on ONE side of k_flip: above it when the converter difference has that sign,
    # below it otherwise. (The text used to assume d_conv > 0 and printed 'k > 91.230' for
    # an ordering that holds for every k BELOW 91.230.)
    lead = "Z2" if d_rest + d_conv > 0 else "Z1"
    side = ">" if (d_conv > 0) == (lead == "Z2") else "<"
    return [{"case": "common rescaling k of the converter terms",
             "observable": "P_loss_package_internal_w",
             "converter_terms_W": c, "delta_converter_W": d_conv, "delta_rest_W": d_rest,
             "k_at_which_order_flips": k_flip,
             "verdict": (f"{lead} lower for every k {side} {k_flip:.3f}" if k_flip
                         else f"{lead} lower for every k > 0"),
             "robust": k_flip is None or (side == ">" and k_flip < 0.5),
             "method": "ledger rows at the converged HV-S0 temperatures: the converter "
                       "and intra-VR rows are the same functions of T_conv in Z1 and Z2"}]


def judge_direct_feed(od):
    """The unsourced external feed of the direct-fed Z2, judged on the crossover sweep by
    the ordering rule: at 0.1 R*, R* and 10 R* where Z2 is ahead at zero feed (above R* the
    loss ordering reverses BY CONSTRUCTION; resolved as a design requirement), or at 0.1, 1
    and 10 mOhm where it is not (R* = 0: every feed resistance only adds to Z2's loss)."""
    cx = J(D / "direct_feed_crossover.json") or {}
    sc = (cx.get("scenarios") or {}).get(SCEN)
    if not sc or sc.get("R_star_mohm") is None or not sc.get("sweep"):
        return []
    # judged against the package-internal verdict (the zero-feed reference); the variant is
    # the PLATFORM-INCLUSIVE loss at a named loop resistance
    u = (od.get("P_loss_package_internal_w") or {}).get("uncertainty_rel", {}).get(SCEN)
    prod = (od.get("P_loss_package_internal_w") or {}).get("per_scenario", {}).get(SCEN)
    sw = [q for q in sc["sweep"] if q.get("feasible", True)]     # no point above R_max
    rows = []
    # around R* where Z2 is ahead at zero feed; at declared loop resistances (0.1, 1 and
    # 10 mOhm, inside the sweep) where it is not (R* = 0)
    pts = ([(f"{fac:g} R*", sc["R_star_mohm"] * fac) for fac in (0.1, 1.0, 10.0)]
           if sc["R_star_mohm"] else [(f"{r:g} mOhm", r) for r in (0.1, 1.0, 10.0)])
    prod_legacy = prod
    prod = production_rule_verdicts({a: _vals(base_case(a)) for a in ("Z1", "Z2")}).get(
        "P_loss_package_internal_w", (None,))[0]
    for lab, r in pts:
        pt = min(sw, key=lambda q: abs(math.log(q["R_mohm"] / r)) if q["R_mohm"] > 0 else 9e9)
        legacy, gap = _verdict(sc["P_Z1_w"], pt["P_total_w"], u)
        verdict, rec = rule_verdict("P_loss_platform_inclusive_w", sc["P_Z1_w"],
                                    pt["P_total_w"],
                                    *(_mesh(base_case(a)) for a in ("Z1", "Z2")))
        rows.append({"case": f"R_feed = {lab} = {r:.4g} mOhm",
                     "observable": "P_loss_platform_inclusive_w",
                     "Z1": sc["P_Z1_w"], "Z2": pt["P_total_w"],
                     "change_rel": {"Z1": 0.0, "Z2": (pt["P_total_w"] - sc["P_Z2_internal_w"])
                                    / sc["P_Z2_internal_w"]},
                     "gap_rel": gap, "D_corrected": rec.get("D_corrected"),
                     "U95": rec.get("U95"), "provisional": rec.get("provisional"),
                     "uncertainty_rel": (rec["U95"] / max(sc["P_Z1_w"], pt["P_total_w"])
                                         if rec.get("U95") is not None else None),
                     "verdict": verdict, "production_verdict": prod, "robust": verdict == prod,
                     "legacy_verdict": legacy, "legacy_uncertainty_rel": u,
                     "legacy_production_verdict": prod_legacy,
                     "R_star_mohm": sc["R_star_mohm"],
                     "method": "self-consistent I_48 with the feed loss; sweep point nearest"})
    return rows


def judge_scenarios(od, sc):
    rows = []
    for k, o in od.items():
        # scenario dependence is REPORTED per scenario, not a sensitivity moving an
        # ordering: robust is not applicable here
        rows.append({"case": "per scenario", "observable": k,
                     "per_scenario": o.get("per_scenario"),
                     "scenario_classes": {s: c["class"] for s, c in sc.items()},
                     "verdict": o.get("statement"),
                     "robust_across_scenarios": o.get("robust_across_scenarios"),
                     "robust": None})
    return rows


#: ENGINEERING_SENSITIVITY between the published attach endpoints (geom.vr_attach_density),
#: judged with the same rule; never a gate case and never a manufacturing geometry
ATTACH_SWEEP = ("attach_dense", "attach_eng_p34", "attach_eng_p37", "attach_eng_p41",
                "attach_sparse")
ATTACH_OBS = ["P_loss_package_internal_w", "T_max_C", "die_warpage_pv_um", "du_c_um"]


def _interp_zero(pts):
    """First sign change of (x, margin) pairs ordered from dense to sparse: the x at which
    the margin crosses zero (linear), with the bracketing pair, or None."""
    for (x0, m0), (x1, m1) in zip(pts, pts[1:]):
        if m0 > 0 >= m1:
            return x0 + (x1 - x0) * m0 / (m0 - m1), (x0, x1)
    return None


def attach_density_crossover(od, unc):
    """Where, between the published attach densities, does each ordering stop holding? Each
    sweep point is the Z2 variant against the unchanged Z1, judged with the ordering rule;
    the signed margin (gap - 2U, positive while the production verdict holds) is
    interpolated linearly in the attach's real-lattice metal fraction (and, inside the
    15 um-pillar family, in pitch). Because the ledger's equal-sharing attach model bounds
    the coupled network's loss from above but understates its DENSITY PENALTY
    (vr_attach_density_study.json, equal_sharing_assessment), the loss crossover is also
    formed with Z2 raised by the network-minus-block penalty at each point."""
    import final_closure_vr_attach as VA
    st = J(D / "vr_attach_density_study.json") or {}
    pen = (st.get("equal_sharing_assessment") or {}).get("density_penalty_vs_dense") or {}
    rows, missing = judge_runs(list(ATTACH_SWEEP), ATTACH_OBS, od, unc)
    if missing:
        return {"status": "PENDING -- missing " + ", ".join(sorted(set(missing)))}
    pts = []
    for v in ATTACH_SWEEP:
        case = VA.CASES[v.removeprefix("attach_")]
        L = VA.lattice(case)
        p = pen.get(v.removeprefix("attach_")) or {}
        pts.append({"case": v, "class": case["class"], "d_um": case["d_um"],
                    "pitch_um": case["pitch_um"], "area_fraction": L["area_fraction"],
                    "n_vdd": L["n_vdd"], "n_gnd": L["n_gnd"],
                    "network_minus_block_penalty_w": (p.get("network_w", 0.0)
                                                      - p.get("block_w", 0.0)),
                    "obs": {r["observable"]: {k: r.get(k) for k in ("Z1", "Z2", "gap_rel",
                                                                    "verdict", "bias", "U95")}
                            for r in rows if r["case"] == v}})
    cross = {}
    base = {a: _vals(base_case(a)) for a in ("Z1", "Z2")}
    prod_rule = production_rule_verdicts(base)
    for k in ATTACH_OBS:
        prod = (prod_rule.get(k) or (None,))[0]
        u = unc.get(k)
        if prod not in ("Z1 lower", "Z2 lower") or any(
                x["obs"].get(k, {}).get("U95") is None for x in pts):
            cross[k] = {"production_verdict": prod, "status": "no resolved production verdict "
                        "to lose (or a point without a transferable U); verdicts per point "
                        "listed"}
            continue
        sgn = 1.0 if prod == "Z2 lower" else -1.0

        def margin(o, dz2=0.0):
            # the unified rule: signed corrected gap toward the production verdict minus U95
            d_star = (o["Z2"] + dz2 - o["Z1"]) + (o.get("bias") or 0.0)
            return -sgn * d_star - o["U95"]
        for x in pts:
            o = x["obs"][k]
            o["margin"] = margin(o)
            if k == "P_loss_package_internal_w":
                o["margin_network_penalty"] = margin(o, x["network_minus_block_penalty_w"])
        f_m = [(x["area_fraction"], x["obs"][k]["margin"]) for x in pts]
        d15 = [(x["pitch_um"], x["obs"][k]["margin"]) for x in pts if x["d_um"] == 15.0]
        zf, zp = _interp_zero(f_m), _interp_zero(d15)
        c = {"production_verdict": prod, "uncertainty_rel": u,
             "f_star": zf[0] if zf else None, "f_bracket": zf[1] if zf else None,
             "pitch_star_um_d15": zp[0] if zp else None,
             "status": ("holds at every point down to the sparse published geometry"
                        if all(m > 0 for _, m in f_m) else
                        "lost at every point including the dense one" if all(
                            m <= 0 for _, m in f_m) else
                        "lost below the crossover metal fraction")}
        if k == "P_loss_package_internal_w":
            zn = _interp_zero([(x["area_fraction"], x["obs"][k]["margin_network_penalty"])
                               for x in pts])
            zpn = _interp_zero([(x["pitch_um"], x["obs"][k]["margin_network_penalty"])
                                for x in pts if x["d_um"] == 15.0])
            c["f_star_network_penalty"] = zn[0] if zn else None
            c["pitch_star_um_d15_network_penalty"] = zpn[0] if zpn else None
            c["reversal"] = any(x["obs"][k]["verdict"] not in (prod, "unresolved")
                                for x in pts)
        cross[k] = c
    return {"class": "ENGINEERING_SENSITIVITY",
            "rule": "each point judged with the unified rule (|D + beta| > U95, the production "
                    "pair's beta and discretization U transferred provisionally); margin = the "
                    "corrected gap toward the production verdict - U95 (W, K or um), "
                    "interpolated linearly between points",
            "points": pts, "crossover": cross}


def _outcome(pv, av):
    """preserved / reversed / withdrawn (unresolved) / created / changed."""
    if pv == av:
        return "preserved"
    if str(pv).endswith("lower") and str(av).endswith("lower"):
        return "reversed"
    if str(pv).endswith("lower"):
        return "withdrawn (unresolved)"
    return "created" if str(av).endswith("lower") else "changed"


#: the newer cooling-A decisions of the robustness map (Fig. 11), judged with the same rule
NEWER = ("die_hotspot_A", "plate_local_h_A", "tim_warp_fb_A")
NEWER_GATE = "robustness.newer_decisions_A"
#: the SUPERSEDED rule Fig. 11 applied to them: twice the paired estimate U_D_paired of the
#: cooling-A Z1/Z2 comparison of research/tcpmt_revision/uncertainty.json at 31a846c
LEGACY_NEWER_UPAIR = {"P_loss_package_internal_w": 0.5087008910215145,
                      "T_max_C": 1.5943253297846707,
                      "die_warpage_pv_um": 0.969029215012697, "du_c_um": 0.07492434332368746}


def judge_newer(od, unc):
    """The newer decisions with the unified rule; their legacy verdict is Fig. 11's old one
    (|D| > 2 U_D_paired), against the ordering.json production verdict."""
    obs = ("P_loss_package_internal_w", "T_max_C", "die_warpage_pv_um", "du_c_um")
    rows, missing = judge_runs(list(NEWER), obs, od, unc)
    for r in rows:
        up = LEGACY_NEWER_UPAIR.get(r["observable"])
        d = r["Z2"] - r["Z1"]
        r["legacy_verdict"] = (("Z1 lower" if d > 0 else "Z2 lower") if abs(d) > 2 * up
                               else "unresolved")
        r["legacy_rule"] = "|D| > 2 U_D_paired (Fig. 11, newer rows)"
    return rows, missing


def rule_change(out, newer):
    """How many robustness verdicts the unified rule changes against the superseded ones."""
    rows = [(g["gate"], r) for g in out for r in g["rows"]] + [(NEWER_GATE, r) for r in newer]
    seen, n, ch_v, ch_o, pend, changes = set(), 0, 0, 0, 0, []
    for gate, r in rows:
        if not r.get("legacy_verdict") or r.get("verdict") in (None, "not rankable"):
            continue
        key = (r["case"], r["observable"])
        if key in seen:                           # a case can serve several gates
            continue
        seen.add(key)
        n += 1
        lo = _outcome(r.get("legacy_production_verdict"), r["legacy_verdict"])
        no = "pending" if r["verdict"] == "pending" else _outcome(r.get("production_verdict"),
                                                                 r["verdict"])
        pend += r["verdict"] == "pending"
        if r["verdict"] != r["legacy_verdict"] or lo != no:
            ch_v += r["verdict"] != r["legacy_verdict"]
            ch_o += lo != no
            changes.append({"case": r["case"], "observable": r["observable"],
                            "legacy": f"{r['legacy_verdict']} ({lo})",
                            "unified": f"{r['verdict']} ({no})",
                            "D": r.get("D", (r.get("Z2") or 0) - (r.get("Z1") or 0)),
                            "U95": r.get("U95"), "D_corrected": r.get("D_corrected")})
    return {"rows_judged": n, "verdicts_changed": ch_v, "outcomes_changed": ch_o,
            "now_pending": pend, "changes": changes,
            "note": "unique (case, observable) robustness rows; legacy = gap > 2 x the r21 -> "
                    "r31 step (old rows) or |D| > 2 U_D_paired (newer rows); unified = "
                    "tcpmt_resolution.RULE; all variant verdicts are provisional (production "
                    "pair's U transferred on the identical mesh, r11 check runs pending)"}


def robustness_ladder_runs(out, newer):
    """The rungs the campaign must add before the robustness verdicts stop being provisional:
    the r11 check rung of every variant case solved on the production mesh, and an own ladder
    (r11 + r31) for a case whose mesh differs from the production pair's."""
    need = {}
    rows = [r for g in out for r in g["rows"]] + list(newer)
    for r in rows:
        for a, st in (r.get("transfer_checks") or {}).items():
            if st.startswith("refused: mesh differs"):
                rungs = ("r11", "r31")
            elif "r11 step check pending" in st:
                rungs = ("r11",)
            else:
                continue
            for rg in rungs:
                need[(r["case"], a, rg)] = st
    cmds = []
    for (v, a, rg), st in sorted(need.items()):
        if v.startswith("die_hotspot_"):
            cmd = (f"python scripts/tcpmt_review_variants.py hotspot {a} {v.rsplit('_', 1)[1]} "
                   f"{SCEN} {rg}")
        elif v.startswith(("tim_warp_fb_", "plate_local_h_")):
            cmd = None                       # production-mesh-only / superseded variants
        else:
            cmd = f"python scripts/final_closure_sensitivity.py --refine {rg} {v}:{a}"
        cmds.append({"case": v, "arch": a, "rung": rg, "reason": st,
                     "file": f"research/final_closure/sensitivity/ladder/etm_{a}_{SCEN}__{v}_"
                             f"{rg}.json",
                     "command": cmd or "no rung: the variant runs on the production mesh only "
                                       "(its verdict stays provisional)"})
    return cmds


def main():
    oj = J(D / "ordering.json") or {}
    od, sc = oj.get("orderings", {}), oj.get("scenario_classes", {})
    unc = _uncertainty(od)
    out = []
    for gid, (sub, obs, rng, method, cases, why) in GATES.items():
        missing = []
        if method == "runs":
            rows, missing = judge_runs(cases, obs, od, unc)
            if cases == H01:
                rows += h1_vs_control(obs)
        elif method == "network":
            rows = judge_network(cases, od)
        elif method == "common_mode":
            rows = judge_common_mode()
        elif method == "direct_feed":
            rows = judge_direct_feed(od)
        else:
            rows = judge_scenarios(od, sc)
        complete = (not missing) and bool(rows)
        moved = [r for r in rows if r.get("robust") is False]
        pend = [r for r in rows if r.get("verdict") == "pending"]
        new_sub = sub
        if sub == "B2" and moved:
            new_sub = "B1"                           # the B2 assumption failed: promote
        if not complete:
            status = "PENDING -- " + (f"missing {', '.join(sorted(set(missing)))}"
                                      if missing else "no evidence rows")
        elif method == "scenarios":
            status = ("RESOLVED -- scenario-conditioned: every named scenario is solved and "
                      "each ordering is stated per scenario")
        elif not moved:
            status = (("RESOLVED -- ordering robust" + (" where judged" if pend else ""))
                      if new_sub == "B1" else "BOUNDED -- magnitude only")
        else:
            status = ("RESOLVED -- ordering changes in: " + "; ".join(
                f"{r['observable']} under {r['case']} ("
                + (f"{r['production_verdict']} -> " if r.get("production_verdict") else "")
                + f"{r['verdict']})" for r in moved) + " -- the claim is narrowed accordingly")
        if complete and pend:
            status += (" -- verdict pending (no transferable U: the case's mesh differs from "
                       "the laddered production pair; own ladder needed) for: " + "; ".join(
                           sorted({f"{r['observable']} under {r['case']}" for r in pend})))
        mx = max((abs(x) for r in rows for x in (r.get("change_rel") or {}).values()
                  if isinstance(x, (int, float))), default=None)
        gaps = [r["gap_rel"] for r in rows if isinstance(r.get("gap_rel"), (int, float))]
        out.append({"gate": gid, "old_class": "B", "new_subtype": new_sub,
                    "declared_subtype": sub, "observable": ", ".join(obs),
                    "range_source": rng, "rationale": why, "method": method,
                    "cases_run": cases, "max_change_rel": mx,
                    "architecture_gap_rel_min": min(gaps) if gaps else None,
                    "ordering_robust": complete and not moved and not pend,
                    "final_status": status,
                    "resolved": complete,
                    "evidence_path": ("research/final_closure/sensitivity/" if method == "runs"
                                      else "research/final_closure/package_network.json"
                                      if method == "network" else
                                      "research/final_closure/direct_feed_crossover.json"
                                      if method == "direct_feed" else
                                      "research/final_closure/electrical_ledger.json"
                                      if method == "common_mode" else
                                      "research/final_closure/ordering.json"),
                    "rows": rows})
    b1 = [g for g in out if g["new_subtype"] == "B1"]
    newer, newer_missing = judge_newer(od, unc)
    summary = {"n_gates": len(out),
               "subtypes": {s: sum(g["new_subtype"] == s for g in out) for s in ("B1", "B2", "B3")},
               "b1_resolved": sum(g["resolved"] for g in b1), "b1_total": len(b1),
               "all_b1_resolved": all(g["resolved"] for g in b1),
               "orderings_that_move": sorted({f"{r['observable']} under {r['case']}"
                                             for g in out for r in g["rows"]
                                             if r.get("robust") is False}),
               "rule_change": rule_change(out, newer)}
    _tu, RULE, _p = _rule()
    (D / "classB_resolution.json").write_text(json.dumps(
        {"rule": "a B1 gate is resolved when every case it needs exists and carries a "
                 "verdict; every verdict is formed with the unified comparison rule of the "
                 "revision (" + RULE.RULE + "); PAPER_READY requires every B1 gate resolved",
         "summary": summary, "gates": out,
         "newer_decisions": {"what": "the newer cooling-A decisions of the robustness map "
                                     "(Fig. 11), judged with the same rule; not gates",
                             "rows": newer, "missing": newer_missing},
         "ladder_runs_needed": robustness_ladder_runs(out, newer),
         "attach_density_crossover": attach_density_crossover(od, unc)},
        indent=1, default=float))
    cols = ["gate", "old_class", "new_subtype", "observable", "range_source", "cases_run",
            "max_change_rel", "architecture_gap_rel_min", "ordering_robust", "final_status",
            "evidence_path"]
    with (D / "classB_resolution.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for g in out:
            w.writerow(dict(g, cases_run="; ".join(g["cases_run"])))
    # every evidence row, as Part 15 asks: nominal, alternate, change, gap, uncertainty,
    # and whether the ordering is preserved, reversed, created or withdrawn
    rcols = ["gate", "case", "observable", "nominal_Z1", "nominal_Z2", "alternate_Z1",
             "alternate_Z2", "change_Z1_rel", "change_Z2_rel", "architecture_gap_rel",
             "uncertainty_rel", "bias", "U95", "provisional", "production_verdict",
             "alternate_verdict", "outcome", "legacy_production_verdict", "legacy_verdict",
             "legacy_outcome"]
    with (D / "classB_sensitivity_rows.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rcols)
        w.writeheader()
        groups = [(g["gate"], g["rows"]) for g in out] + [(NEWER_GATE, newer)]
        for gate, grows in groups:
            for r in grows:
                if "observable" not in r or "verdict" not in r:
                    continue
                ch = r.get("change_rel") or {}
                pv, av = r.get("production_verdict"), r.get("verdict")
                outcome = ("pending" if av == "pending" else
                           "n/a" if r.get("robust") is None else _outcome(pv, av))
                lo = (_outcome(r.get("legacy_production_verdict"), r.get("legacy_verdict"))
                      if r.get("legacy_verdict") else "")
                nz = {a: ((r.get(a) / (1 + ch[a])) if isinstance(r.get(a), (int, float))
                          and isinstance(ch.get(a), (int, float)) and ch[a] != -1 else None)
                      for a in ("Z1", "Z2")}
                w.writerow({"gate": gate, "case": r["case"], "observable": r["observable"],
                            "nominal_Z1": nz["Z1"], "nominal_Z2": nz["Z2"],
                            "alternate_Z1": r.get("Z1"), "alternate_Z2": r.get("Z2"),
                            "change_Z1_rel": ch.get("Z1"), "change_Z2_rel": ch.get("Z2"),
                            "architecture_gap_rel": r.get("gap_rel"),
                            "uncertainty_rel": r.get("uncertainty_rel"),
                            "bias": r.get("bias"), "U95": r.get("U95"),
                            "provisional": r.get("provisional"),
                            "production_verdict": pv, "alternate_verdict": av,
                            "outcome": outcome,
                            "legacy_production_verdict": r.get("legacy_production_verdict"),
                            "legacy_verdict": r.get("legacy_verdict"), "legacy_outcome": lo})
    print(json.dumps(summary, indent=1))
    for g in out:
        print(f"{g['gate']:36s} {g['new_subtype']} {g['final_status'][:110]}")


if __name__ == "__main__":
    main()
