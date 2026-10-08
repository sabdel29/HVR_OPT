#!/usr/bin/env python3
"""Phase-0K Sec.16/20 -- WHAT-IF / EXPERIMENT-DESIGN ANALYSIS. No measurements exist.

Sweeps a hypothetical measured Z1 life and asks what each admitted law would then predict, and
how the G2 decision would depend jointly on that measurement and on N_required.

NOTHING here is a measurement. Every row is labelled WHAT-IF.
"""
from __future__ import annotations
import csv, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0k"
ARCH = ("Z1", "Z2", "Z4")


def metrics(cond="OP_BASELINE"):
    rows = list(csv.DictReader(open(OUT / "experiment_condition_metrics.csv")))
    by = {(r["arch"], r["condition"]): r for r in rows}
    m4 = {a: float(by[(a, cond)]["M4_creep_strain"]) for a in ("Z1", "Z2") if (a, cond) in by}
    m5 = {a: float(by[(a, cond)]["M5_creep_energy_MJ_per_m3"]) for a in ("Z1", "Z2")
          if (a, cond) in by}
    # Z4 was not re-run over the condition sweep; take it from the Phase-0J-R matched extraction
    jr = {r["short"]: r for r in
          csv.DictReader(open(R / "results/phase0jr/syed_layer_metrics.csv"))
          if r["n_mid"] == "10"}
    # rescale Z4 onto the same graded/6-cycle basis using Z1 as the transfer standard
    k4 = float(jr["Z4"]["M4_syed_layer"]) / float(jr["Z1"]["M4_syed_layer"])
    k5 = float(jr["Z4"]["M5_syed_layer_MJ_per_m3"]) / float(jr["Z1"]["M5_syed_layer_MJ_per_m3"])
    m4["Z4"] = m4["Z1"] * k4
    m5["Z4"] = m5["Z1"] * k5
    return m4, m5


def main() -> int:
    m4, m5 = metrics()
    print("metrics at the operating condition (graded mesh, Syed 25 um layers, cycle 5 of 6):")
    for a in ARCH:
        print(f"  {a}: M4 = {m4[a]:.4e}   M5 = {m5[a]:.4f}   w/eps = {m5[a]/m4[a]:7.2f} MPa")

    rs = {a: m4["Z1"] / m4[a] for a in ARCH}       # strain-law life ratio vs Z1
    re_ = {a: m5["Z1"] / m5[a] for a in ARCH}      # energy-law life ratio vs Z1
    print("\nlife ratio vs Z1 after ANY single-point calibration at this condition:")
    for a in ARCH:
        print(f"  {a}: strain {rs[a]:.4f}   energy {re_[a]:.4f}   "
              f"spread {100*abs(rs[a]-re_[a])/min(rs[a],re_[a]):.1f} %")

    # ---------- Sec.20: measured-life x required-life decision map ----------
    rows = []
    for X in [10 ** (2 + 3 * k / 60) for k in range(61)]:          # hypothetical measured Z1 life
        for N in [10 ** (2 + 3 * k / 60) for k in range(61)]:      # hypothetical N_required
            nf = {a: {"strain": X * rs[a], "energy": X * re_[a]} for a in ARCH}
            st = {}
            for a in ARCH:
                v = [nf[a][k] >= N for k in ("strain", "energy")]
                st[a] = "PASS" if all(v) else ("FAIL" if not any(v) else "AMBIGUOUS")
            if st["Z1"] == "PASS" and st["Z2"] == "PASS":
                dec = "ALL PASS -- G2 NOT ACTIVE"
            elif st["Z1"] == "FAIL" and st["Z2"] == "FAIL":
                dec = "ALL FAIL -- architecture does not solve it"
            elif st["Z1"] == "FAIL" and st["Z2"] == "PASS":
                dec = "G2 PASSED -- Z1 fails, Z2 passes"
            elif "AMBIGUOUS" in st.values():
                dec = "MODEL-FORM AMBIGUOUS"
            else:
                dec = "MIXED"
            rows.append({"label": "WHAT-IF / EXPERIMENT-DESIGN ANALYSIS -- NOT A MEASUREMENT",
                         "hypothetical_measured_Z1_life": round(X, 1),
                         "N_required": round(N, 1),
                         **{f"{a}_strain": round(nf[a]["strain"], 1) for a in ARCH},
                         **{f"{a}_energy": round(nf[a]["energy"], 1) for a in ARCH},
                         **{f"{a}_status": st[a] for a in ARCH},
                         "decision": dec})
    f = OUT / "mission_vs_calibration_decision_map.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}  ({len(rows)} cells)")
    from collections import Counter
    c = Counter(r["decision"] for r in rows)
    for k, v in c.most_common():
        print(f"   {k:46} {v:5}  ({100*v/len(rows):5.1f} %)")

    # ---------- Sec.16: what one calibration buys, and what it does not ----------
    rows2 = []
    for X in (500, 1000, 2000, 4000, 8000):
        Cc, Wc = 1.0 / (X * m4["Z1"]), 1.0 / (X * m5["Z1"])
        rows2.append({"label": "WHAT-IF -- NOT A MEASUREMENT",
                      "hypothetical_measured_Z1_life": X,
                      "fitted_C_strain": round(Cc, 6), "fitted_W_energy": round(Wc, 8),
                      "Z1_strain": X, "Z1_energy": X,
                      "Z2_strain": round(X * rs["Z2"], 1), "Z2_energy": round(X * re_["Z2"], 1),
                      "Z4_strain": round(X * rs["Z4"], 1), "Z4_energy": round(X * re_["Z4"], 1),
                      "abs_life_spread_Z1_pct": 0.0,
                      "abs_life_spread_Z2_pct": round(100 * abs(rs["Z2"] - re_["Z2"])
                                                      / min(rs["Z2"], re_["Z2"]), 2),
                      "model_form_resolved": "NO -- both laws fit this point exactly",
                      "extrapolation_to_a_DIFFERENT_cycle":
                          "UNRESOLVED -- the two laws diverge by up to 85 % between the cold "
                          "and hot test ranges"})
    f2 = OUT / "synthetic_calibration_sensitivity.csv"
    with f2.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows2[0])); w.writeheader(); w.writerows(rows2)
    print(f"wrote {f2}")
    print("\n=== THE KEY ASYMMETRY ===")
    print(f"  ONE calibration at the OPERATING condition collapses the absolute-life spread")
    print(f"  from 5.2x to {100*abs(rs['Z2']-re_['Z2'])/min(rs['Z2'],re_['Z2']):.1f} % for Z2 "
          f"and to ZERO for Z1 -- because the three architectures sit within 6 % of each other")
    print("  in w/eps, so BOTH laws extrapolate between them almost identically.")
    print("  It does NOT identify which law is right, and therefore does NOT license")
    print("  extrapolation to a cycle different from the one tested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
