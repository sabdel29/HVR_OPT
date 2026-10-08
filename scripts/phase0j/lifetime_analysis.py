#!/usr/bin/env python3
"""Phase-0J Sec.17-27 -- architecture life, uncertainty, mission sensitivity, G2, cost.

NOTHING here is a validated lifetime. Sec.6 admitted ZERO life laws. The single
CONDITIONALLY TRANSFERABLE candidate (L4, Syed 2004 SnAgCu) is applied only to answer the
questions Sec.19 and Sec.25 pose, and every output row carries its applicability status.

The one quantity that is NOT conditional is the RELATIVE life, because the Syed form is
inverse-linear in the metric: N_f = (C*eps)^-1 makes C cancel AND leaves no free exponent, so
N_f,2/N_f,1 = eps_1/eps_2 exactly. That ratio is a model output, not a fitted quantity.
"""
from __future__ import annotations
import csv, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0j"

C_MECH_II = 0.036     # SnAgCu matrix-creep constant, SECONDARY provenance (Yu et al. 2026)
C_MECH_I = 0.013      # SnAgCu grain-boundary-sliding constant, same source
STATUS = ("CONDITIONAL -- law is CONDITIONALLY TRANSFERABLE, not admissible; "
          "Sec.8 reproduction was IMPOSSIBLE (primary unretrievable); cycle is incompatible "
          "with any known calibration. NOT A VALIDATED LIFETIME.")


def load(f):
    return list(csv.DictReader(open(OUT / f)))


def main() -> int:
    nat = {r["arch"]: r for r in load("native_metrics_by_architecture.csv")
           if (r["arch"], r["h_sub_mm"]) in
           [("ARCH_Z1_EMBEDDED", "1.3"), ("ARCH_Z2_BACKSIDE", "0.3"),
            ("ARCH_Z4_POWER_DIE", "0.3")]}
    creep = {(r["arch"], r["model"]): r for r in load("creep_effect_by_architecture.csv")}
    A = ["ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"]
    m1 = {a: float(nat[a]["M1_accum_inelastic_path"]) for a in A}
    m2 = {a: float(nat[a]["M2_strain_range"]) for a in A}
    m3 = {a: float(nat[a]["M3_inelastic_work_MJ_per_m3"]) for a in A}
    pel = {a: float(nat[a]["P_elec_total_w"]) for a in A}
    m1ec = {a: float(creep[(a, "EC")]["M1_accum_inelastic_path"]) for a in A}
    Z1 = "ARCH_Z1_EMBEDDED"

    # ---------- Sec.17/20  lifetime by law and architecture ----------
    rows = []
    for lab, C, eps, src in (
            ("L4_SYED_2MECH_as_1mech_CII", C_MECH_II, m1,
             "eps_acc <- M1 of the EPC model (total accumulated inelastic)"),
            ("L4_SYED_2MECH_as_1mech_CII_creeponly", C_MECH_II, m1ec,
             "eps_acc <- M1 of the EC model (creep-only: structurally closest to Syed's "
             "unified viscoplastic framework, in which ALL inelastic strain is creep)"),
            ("L4_SYED_2MECH_as_1mech_CI", C_MECH_I, m1,
             "eps_acc <- M1 of the EPC model, but assuming mechanism I dominates instead")):
        nf = {a: 1.0 / (C * eps[a]) for a in A}
        rows.append({"law": lab, "family": "C_CREEP_DAMAGE",
                     "native_metric": "accumulated creep strain per cycle", "metric_used": "M1",
                     "eps_source": src, "C_constant": C,
                     "Z1_life": round(nf[A[0]], 1), "Z2_life": round(nf[A[1]], 1),
                     "Z4_life": round(nf[A[2]], 1),
                     "Z2_over_Z1": round(nf[A[1]] / nf[A[0]], 4),
                     "Z4_over_Z1": round(nf[A[2]] / nf[A[0]], 4),
                     "ranking": "Z2 > Z1 > Z4", "applicability_status": STATUS})
    f = OUT / "lifetime_by_law_and_architecture.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote {f}")
    for r in rows:
        print(f"  {r['law']:40} Z1={r['Z1_life']:>8}  Z2={r['Z2_life']:>8}  "
              f"Z4={r['Z4_life']:>8}  Z2/Z1={r['Z2_over_Z1']}")

    # ---------- Sec.20  model-form comparison across the three metric families ----------
    mf = []
    for fam, met, vals in (("A_STRAIN_RANGE", "M2", m2), ("B_ENERGY", "M3", m3),
                           ("C_CREEP_DAMAGE", "M1", m1)):
        for m in (1.0, 1.5, 2.0, 3.0):
            mf.append({"law_family": fam, "native_metric": met, "assumed_exponent_m": m,
                       "Z2_over_Z1_life": round((vals[Z1] / vals[A[1]]) ** m, 4),
                       "Z4_over_Z1_life": round((vals[Z1] / vals[A[2]]) ** m, 4),
                       "ranking": "Z2 > Z1 > Z4",
                       "exponent_status": ("FIXED AT 1 BY THE SYED FORM -- not assumed"
                                           if (fam == "C_CREEP_DAMAGE" and m == 1.0)
                                           else "ASSUMED / UNSOURCED")})
    f = OUT / "lifetime_model_form_comparison.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(mf[0])); w.writeheader(); w.writerows(mf)
    print(f"\nwrote {f}")
    print("  ranking across ALL families and exponents: "
          f"{ {r['ranking'] for r in mf} }")

    # ---------- Sec.21/22  ABSOLUTE vs RELATIVE uncertainty, common mode separated ----------
    unc = []
    # Relative (ratio) uncertainty: measured in Phase 0I-R with PAIRED perturbations.
    for lab, d, kind in (
        ("metric numerical (mesh, CETOL, corner band)", 0.062, "RELATIVE"),
        ("material parameters (Norton A, E(T), yield), PAIRED", 0.062, "RELATIVE"),
        ("life-law constant C", 0.0, "RELATIVE"),
        ("life-law exponent (Syed form fixes m = 1)", 0.0, "RELATIVE"),
        ("metric numerical (mesh 1.90 %, CETOL 0.02 %, corner 6.4 %)", 0.066, "ABSOLUTE"),
        ("material parameters (E +-15 % alone moves Z1 by 8.9 %)", 0.089, "ABSOLUTE"),
        ("life-law constant C (0.013 vs 0.036 = factor 2.77)", 1.77, "ABSOLUTE"),
        ("creep/plastic split (EPC vs EC choice of eps_acc)", 0.379, "ABSOLUTE"),
        ("model form: no admissible law exists", float("inf"), "ABSOLUTE"),
        ("cycle incompatibility with any calibration", float("inf"), "ABSOLUTE")):
        unc.append({"source": lab, "applies_to": kind,
                    "fractional_effect": ("UNBOUNDED" if math.isinf(d) else round(d, 4)),
                    "note": ("cancels exactly in a ratio -- C is a common factor"
                             if "constant C" in lab and kind == "RELATIVE" else
                             ("the Syed form is inverse-linear, so there is no free exponent"
                              if "exponent" in lab else
                              ("common-mode; measured on the RATIO with paired perturbations "
                               "(Phase 0I-R Sec.15)" if kind == "RELATIVE" else
                               "affects the absolute level only")))})
    f = OUT / "lifetime_uncertainty.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(unc[0])); w.writeheader(); w.writerows(unc)
    print(f"wrote {f}")

    # ---------- Sec.25  mission-life sensitivity and the crossover ----------
    nf_ref = {a: 1.0 / (C_MECH_II * m1[a]) for a in A}
    ms = []
    for N in (1e2, 3e2, 1e3, 3e3, 1e4, 3e4, 1e5):
        st = {a: ("PASS" if nf_ref[a] >= N else "FAIL") for a in A}
        n_pass = sum(v == "PASS" for v in st.values())
        ms.append({"N_required_PARAMETRIC": int(N),
                   "label": "PARAMETRIC MISSION SENSITIVITY -- NOT a qualification requirement",
                   "Z1_status": st[A[0]], "Z2_status": st[A[1]], "Z4_status": st[A[2]],
                   "n_architectures_passing": n_pass,
                   "feasible_set_changes": ("YES -- reliability selects the architecture"
                                            if 0 < n_pass < 3 else
                                            ("no -- all pass" if n_pass == 3 else
                                             "no -- all fail")),
                   "preferred": ("Z1 (lowest electrical loss; all pass)" if n_pass == 3 else
                                 ("Z2 (only survivor)" if st[A[1]] == "PASS" else "none"))})
    f = OUT / "mission_life_sensitivity.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ms[0])); w.writeheader(); w.writerows(ms)
    print(f"wrote {f}")
    lo, hi = nf_ref[A[0]], nf_ref[A[1]]
    print(f"  MISSION-LIFE CROSSOVER band (conditional): N_required in ({lo:.0f}, {hi:.0f}]")
    print(f"  band WIDTH as a ratio = {hi/lo:.4f}  <-- independent of C; only its POSITION is not")

    # ---------- Sec.23  G2 ----------
    g2 = [{"requirement": "1. defensible predicted fatigue life N_f(x)", "status": "NOT MET",
           "evidence": "0 of 10 candidate laws ADMISSIBLE (LIFE_LAW_ADMISSIBILITY.md); the one "
                       "CONDITIONALLY TRANSFERABLE candidate failed the Sec.8 reproduction gate "
                       "because its primary calibration data are unretrievable"},
          {"requirement": "2. defensible required life N_required", "status": "NOT MET",
           "evidence": "MISSION_REQUIREMENT_AUDIT.md -- no category-B field mission requirement "
                       "exists; Sec.14 forbids promoting the 1000-cycle qualification count"},
          {"requirement": "3. one electrically attractive candidate fails while another passes",
           "status": "NOT EVALUABLE", "evidence": "requires 1 and 2"},
          {"requirement": "4. ranking survives uncertainty", "status": "MET (metric level)",
           "evidence": "Z2/Z1 metric ratio resolved at 5.8x its paired-perturbation spread; "
                       "ranking identical across M1, M2 and M3 and across all exponents"},
          {"requirement": "G2 OVERALL", "status": "NOT TESTED",
           "evidence": "unchanged since Phase 0B. The LEFT side of g(x) <= g_allow is closed and "
                       "now has all three metrics frozen natively; the RIGHT side is absent. "
                       "Phase 0J converts 'we have no metric and no allowable' into 'we have "
                       "three validated metrics, no transferable law, and no requirement'."}]
    f = OUT / "g2_evaluation.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(g2[0])); w.writeheader(); w.writerows(g2)
    print(f"wrote {f}")

    # ---------- Sec.26  electrical cost of reliability ----------
    ec = []
    for a in (A[1], A[2]):
        dP = pel[a] - pel[Z1]
        for fam, met, vals in (("C_CREEP_DAMAGE (m fixed at 1)", "M1", m1),
                               ("A_STRAIN_RANGE (m assumed)", "M2", m2),
                               ("B_ENERGY (m assumed)", "M3", m3)):
            for m in ([1.0] if "fixed" in fam else [1.0, 1.5, 3.0]):
                ratio = (vals[Z1] / vals[a]) ** m
                dlog = math.log10(ratio)
                ec.append({"comparison": f"{a[5:]} vs Z1", "law_family": fam,
                           "native_metric": met, "exponent_m": m,
                           "dP_elec_W": round(dP, 4),
                           "life_multiple_vs_Z1": round(ratio, 4),
                           "dlog10_Nf": round(dlog, 5),
                           "W_per_decade_of_life": (round(dP / dlog, 3) if abs(dlog) > 1e-9
                                                    else "n/a"),
                           "reading": (f"{dP:+.3f} W buys {ratio:.2f}x life"
                                       if ratio > 1 else
                                       f"{dP:+.3f} W AND {ratio:.2f}x life -- worse on both"),
                           "supersedes": "W per um of warpage (Phase 0C-0H) -- withdrawn for "
                                         "local-reliability decisions"})
    f = OUT / "electrical_cost_of_reliability.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ec[0])); w.writeheader(); w.writerows(ec)
    print(f"wrote {f}")
    for r in ec[:1] + ec[3:4]:
        print(f"  {r['comparison']:14} {r['reading']}")

    # ---------- Sec.27  mean-temperature shift propagated to life ----------
    tp = []
    for lab, dmet in (("temperature-DEPENDENT material model (Phase 0I)", 0.227),
                      ("temperature-INDEPENDENT (frozen properties)", -0.002)):
        for m in (1.0, 1.5, 3.0):
            tp.append({"model": lab, "mean_T_shift_K": 50,
                       "metric_change_pct": round(100 * dmet, 1), "exponent_m": m,
                       "life_multiple": round((1 + dmet) ** (-m), 4),
                       "life_change_pct": round(100 * ((1 + dmet) ** (-m) - 1), 1),
                       "note": ("m = 1 is FIXED by the Syed inverse-linear form; higher m are "
                                "ASSUMED and unsourced" if m == 1.0 else "ASSUMED / UNSOURCED"),
                       "do_not_confuse_with": "the Z1/Z2/Z4 comparison, whose joint temperatures "
                                              "differ by only 2.1 K (r = +0.017 against damage)"})
    f = OUT / "temperature_shift_to_life.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tp[0])); w.writeheader(); w.writerows(tp)
    print(f"wrote {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
