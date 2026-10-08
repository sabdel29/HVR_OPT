#!/usr/bin/env python3
"""Phase-0K Sec.9/10/13/15/29 -- absolute-life model identifiability.

Answers, quantitatively:
  (a) can ONE test condition discriminate the strain and energy laws?      -- provably NO
  (b) can TWO ARCHITECTURES at one profile discriminate them?
  (c) which TWO CONDITIONS discriminate best, and by how many sigma?
  (d) how many specimens does that take?

Discrimination power of a condition pair, derived in discrimination.py:

    D = (eps_B/eps_A) / (w_B/w_A) = (w/eps)_A / (w/eps)_B

Statistical model for the measurement, using the Weibull MLE large-sample result:
    SE(ln eta) ~= 1 / (beta * sqrt(n))            per condition
    SE(ln ratio) = sqrt( 1/(beta^2 n_A) + 1/(beta^2 n_B) )
Simulation uncertainty on the PREDICTED metric ratio is carried separately and stated.
"""
from __future__ import annotations
import csv, itertools, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0k"
# Phase-0I-R measured 6.2 pp spread on a 36 % architecture ratio under PAIRED perturbations.
# Across DIFFERENT TEMPERATURE conditions the material-property errors do NOT fully cancel, so
# the simulation term is taken larger than that and its sensitivity is reported.
SIM_SE_LN = 0.08            # 8 % on a predicted metric ratio -- STATED ASSUMPTION
BETAS = (6, 11)             # Syed's dataset: average ~11, range 6-20. 6 is the pessimistic end.
NSPEC = (8, 16, 32)


def main() -> int:
    rows = list(csv.DictReader(open(OUT / "experiment_condition_metrics.csv")))
    by = {(r["arch"], r["condition"]): r for r in rows}
    F = lambda r, k: float(r[k])

    # ---------- (a) one condition ----------
    print("=" * 78)
    print("(a) CAN ONE TEST CONDITION DISCRIMINATE THE TWO LAWS?")
    b = by[("Z1", "OP_BASELINE")]
    e, w = F(b, "M4_creep_strain"), F(b, "M5_creep_energy_MJ_per_m3")
    for Ntest in (800, 1500, 3000):
        print(f"   if measured life = {Ntest:5d} cycles:  C_fit = {1/(Ntest*e):.5f}   "
              f"W_fit = {1/(Ntest*w):.5f}   -> BOTH laws reproduce it EXACTLY")
    print("   NO. One condition supplies one equation and each law has one free constant.")
    print("   Residual degrees of freedom for discrimination = 0. It re-labels the")
    print("   disagreement as two different constants; it does not resolve model form.")

    # ---------- (b) two architectures, one profile ----------
    print("\n" + "=" * 78)
    print("(b) TWO ARCHITECTURES AT ONE PROFILE?")
    z1, z2 = by[("Z1", "OP_BASELINE")], by[("Z2", "OP_BASELINE")]
    rs = F(z1, "M4_creep_strain") / F(z2, "M4_creep_strain")
    re_ = F(z1, "M5_creep_energy_MJ_per_m3") / F(z2, "M5_creep_energy_MJ_per_m3")
    D_arch = rs / re_
    print(f"   strain law predicts N_Z2/N_Z1 = {rs:.4f}")
    print(f"   energy law predicts N_Z2/N_Z1 = {re_:.4f}")
    print(f"   D = {D_arch:.4f}  ->  the two laws differ by only {100*(D_arch-1):.1f} % here.")
    print("   The architectures share almost the same w/eps, so this pair is nearly blind")
    print("   to model form. It VALIDATES the relative claim; it does not discriminate.")

    # ---------- (c) condition pairs ----------
    print("\n" + "=" * 78)
    print("(c) CONDITION PAIRS, RANKED BY DISCRIMINATION POWER (architecture Z1)")
    zz = [r for r in rows if r["arch"] == "Z1"]
    pairs = []
    for a, c in itertools.combinations(zz, 2):
        wa, wc = F(a, "w_over_eps_MPa"), F(c, "w_over_eps_MPa")
        D = max(wa, wc) / min(wa, wc)
        lnD = math.log(D)
        rec = {"arch": "Z1", "cond_A": a["condition"], "cond_B": c["condition"],
               "T_A": f"{a['T_min_C']}/{a['T_max_C']}", "T_B": f"{c['T_min_C']}/{c['T_max_C']}",
               "dwell_A_s": a["dwell_s"], "dwell_B_s": c["dwell_s"],
               "w_over_eps_A": round(wa, 2), "w_over_eps_B": round(wc, 2),
               "D_discrimination": round(D, 4),
               "pct_difference_between_law_predictions": round(100 * (D - 1), 1),
               "strain_law_life_ratio_A_over_B": round(F(c, "M4_creep_strain")
                                                       / F(a, "M4_creep_strain"), 4),
               "energy_law_life_ratio_A_over_B": round(F(c, "M5_creep_energy_MJ_per_m3")
                                                       / F(a, "M5_creep_energy_MJ_per_m3"), 4)}
        for beta in BETAS:
            for n in NSPEC:
                se = math.sqrt(2.0 / (beta * beta * n) + SIM_SE_LN ** 2)
                rec[f"sigma_beta{beta}_n{n}"] = round(lnD / se, 2)
        pairs.append(rec)
    pairs.sort(key=lambda r: -r["D_discrimination"])
    f = OUT / "experiment_condition_discrimination.csv"
    with f.open("w", newline="") as fh:
        w_ = csv.DictWriter(fh, fieldnames=list(pairs[0])); w_.writeheader(); w_.writerows(pairs)
    print(f"   {'pair':34} {'w/e A':>7} {'w/e B':>7} {'D':>6} {'diff':>7} "
          f"{'sig b6n16':>10} {'sig b11n16':>11}")
    for r in pairs[:8]:
        print(f"   {r['cond_A'][:15]+' vs '+r['cond_B'][:15]:34} {r['w_over_eps_A']:7.1f} "
              f"{r['w_over_eps_B']:7.1f} {r['D_discrimination']:6.3f} "
              f"{r['pct_difference_between_law_predictions']:6.1f}% "
              f"{r['sigma_beta6_n16']:10.2f} {r['sigma_beta11_n16']:11.2f}")
    print(f"\n   wrote {f}")

    # ---------- (d) specimen count for the best pair ----------
    best = pairs[0]
    print("\n" + "=" * 78)
    print(f"(d) SPECIMEN COUNT for the best pair: {best['cond_A']} vs {best['cond_B']}")
    lnD = math.log(best["D_discrimination"])
    print(f"   {'beta':>5} " + " ".join(f"{'n=' + str(n):>9}" for n in NSPEC))
    for beta in BETAS:
        print(f"   {beta:>5} " + " ".join(
            f"{best[f'sigma_beta{beta}_n{n}']:9.2f}" for n in NSPEC))
    print("   (values are sigma of separation between the two laws' predicted life ratios)")
    # smallest n reaching 3 sigma at the pessimistic beta
    for n in range(4, 200):
        se = math.sqrt(2.0 / (36.0 * n) + SIM_SE_LN ** 2)
        if lnD / se >= 3.0:
            print(f"\n   minimum n per condition for 3 sigma at beta = 6 : {n}")
            break
    se_inf = SIM_SE_LN
    print(f"   ceiling set by SIMULATION uncertainty alone ({100*SIM_SE_LN:.0f} %): "
          f"{lnD/se_inf:.1f} sigma -- adding specimens beyond ~16 buys little")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
