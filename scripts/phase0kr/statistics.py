#!/usr/bin/env python3
"""Phase-0K-R Sec.12-17 -- Weibull beta database, sigma audit, and statistical power.

Sec.12 requires the Phase-0K "6.19 sigma" to be audited rather than repeated. Sec.13 forbids
freezing beta = 6 without evidence. Sec.17 requires n = 16 to be TESTED, not defended.
"""
from __future__ import annotations
import csv, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0kr"

# ---- PRIMARY Weibull slopes, transcribed from tables in papers held in this repository.
BETA = [
    # Syed 2004 author-corrected, Table 2b, SnAgCu column. 12 board-level BGA/CSP cells.
    ("Syed 2004 Table 2b", "SnAgCu 4.0Ag0.5Cu / 3.9Ag0.5Cu", "CABGA 15x15 208", "BGA ball",
     "TC1 -40/125", 8.92, 3717, "300 ohm + 10 confirmations", "HIGH"),
    ("Syed 2004 Table 2b", "SnAgCu", "CABGA 15x15 256", "BGA ball", "TC2 -55/125", 15.4, 4096,
     "300 ohm + 10 confirmations", "HIGH"),
    ("Syed 2004 Table 2b", "SnAgCu", "CABGA 8x8 64", "BGA ball", "TC1 -40/125", 8.36, 4843,
     "300 ohm + 10 confirmations", "HIGH"),
    ("Syed 2004 Table 2b", "SnAgCu", "CABGA 8x8 64", "BGA ball", "TC2 -55/125", 9.81, 3263,
     "300 ohm + 10 confirmations", "HIGH"),
    ("Syed 2004 Table 2b", "SnAgCu", "Ceramic BGA 8x8 64", "BGA ball", "TC1 -40/125", 7.08, 445,
     "300 ohm + 10 confirmations", "MEDIUM -- ceramic substrate"),
    ("Syed 2004 Table 2b", "SnAgCu", "Ceramic BGA 8x8 64", "BGA ball", "TC3 0/100", 9.55, 1103,
     "300 ohm + 10 confirmations", "MEDIUM -- ceramic substrate"),
    ("Syed 2004 Table 2b", "SnAgCu", "CVBGA 12x12 288", "BGA ball", "TC1 -40/125", 5.81, 2005,
     "300 ohm + 10 confirmations", "HIGH -- 0.5 mm pitch"),
    ("Syed 2004 Table 2b", "SnAgCu", "fleXBGA 12x12 144", "BGA ball", "TC1 -40/125", 19.06, 2948,
     "300 ohm + 10 confirmations", "MEDIUM -- tape substrate"),
    ("Syed 2004 Table 2b", "SnAgCu", "fleXBGA 12x12 144", "BGA ball", "TC2 -55/125", 20.4, 2792,
     "300 ohm + 10 confirmations", "MEDIUM -- tape substrate"),
    ("Syed 2004 Table 2b", "SnAgCu", "fleXBGA 12x12 144", "BGA ball", "TC3 0/100", 15.7, 10370,
     "300 ohm + 10 confirmations", "MEDIUM -- tape substrate"),
    ("Syed 2004 Table 2b", "SnAgCu", "PBGA 27x27 256", "BGA ball", "TC2 -55/125", 7.2, 6812,
     "300 ohm + 10 confirmations", "HIGH -- 1.27 mm pitch"),
    ("Syed 2004 Table 2b", "SnAgCu", "TSCSP 12x12 288", "BGA ball", "TC2 -55/125", 6.0, 296,
     "300 ohm + 10 confirmations", "HIGH -- 0.5 mm pitch"),
    # George 2010 (UMD MS thesis), Tables 4 and 6. SAC305 specifically.
    ("George 2010 Table 4", "SAC305", "BGA 256 I/O, Sn-based finish", "BGA ball",
     "-40/185", 5.1, 1245, "daisy-chain continuity", "HIGH -- SAC305, 16/16 failures"),
    ("George 2010 Table 4", "SAC305", "BGA 256 I/O, ENIG finish", "BGA ball",
     "-40/185", 5.4, 1390, "daisy-chain continuity", "HIGH -- SAC305, 16/16 failures"),
    ("George 2010 Table 6", "SAC305", "BGA 144 I/O, Sn-based finish", "BGA ball",
     "-40/185", 10.1, 1130, "daisy-chain continuity", "HIGH -- SAC305, 16/16 failures"),
    ("George 2010 Table 6", "SAC305", "BGA 144 I/O, ENIG finish", "BGA ball",
     "-40/185", 5.6, 1844, "daisy-chain continuity",
     "HIGH -- SAC305, but 10/16 CENSORED"),
]
NS = (8, 12, 16, 20, 24, 32)
BETAS = (3, 4, 5, 6, 8, 10)
SIM_SE = 0.08                 # simulation uncertainty on a predicted metric ratio


def main() -> int:
    rows = [{"source": s, "alloy": al, "package": pk, "joint": jt, "cycle": cy,
             "beta": b, "eta_cycles": e, "failure_criterion": fc, "relevance": rel,
             "sample_size": ("16" if "George" in s else "not stated per cell")}
            for s, al, pk, jt, cy, b, e, fc, rel in BETA]
    f = OUT / "SAC305_WEIBULL_BETA_DATABASE.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    bs = sorted(r["beta"] for r in rows)
    sac = sorted(r["beta"] for r in rows if r["alloy"] == "SAC305")
    print(f"wrote {f}  ({len(rows)} primary cells)")
    print(f"\nALL SnAgCu/SAC305 beta: n={len(bs)}  min={bs[0]}  p25={bs[len(bs)//4]:.2f}  "
          f"median={bs[len(bs)//2]:.2f}  max={bs[-1]}")
    print(f"SAC305 ONLY            : n={len(sac)}  {sac}")
    below6 = sum(1 for b in bs if b < 6)
    print(f"\ncells with beta < 6    : {below6} of {len(bs)}  ({100*below6/len(bs):.0f} %)")
    print(f"observed MINIMUM       : {bs[0]}")
    print(f"-> beta = 6 is the {100*sum(1 for b in bs if b < 6)/len(bs):.0f}th percentile of the "
          f"observed distribution. It is NOT a conservative bound.")

    # ---------------- Sec.12 sigma audit + Sec.14/17 power ----------------
    # Discrimination statistic: measured ln(life ratio between two conditions) compared with
    # two predicted ln-ratios that differ by ln(D). Z = ln(D) / SE(difference).
    #   SE^2 = 2/(beta^2 n)                      experimental, two cells of n
    #        + SIM_SE^2                          simulation uncertainty on the predicted ratio
    D_ORIG, D_NEW = 1.849, 1.440
    # Architecture validation: measured ln(N_Z2/N_Z1) against a predicted band; the quantity of
    # interest is whether the ratio is resolvably > 1. Effect size ln(1.24) at the reference.
    R_ARCH = 1.24
    pw = []
    for D, lab in ((D_ORIG, "ORIGINAL -40/+25 vs +55/+125 (WITHDRAWN, out of domain)"),
                   (D_NEW, "REVISED +45/+125 vs +110/+150 (within temperature domain)")):
        for beta in BETAS:
            for n in NS:
                se_exp = math.sqrt(2.0 / (beta * beta * n))
                se_tot = math.sqrt(se_exp ** 2 + SIM_SE ** 2)
                z_disc = math.log(D) / se_tot
                # architecture test uses the SAME two cells per architecture at one condition;
                # simulation error largely cancels (same mesh, same material, paired), so only
                # the Phase-0I-R paired-perturbation residual of 6 % is carried
                se_arch = math.sqrt(2.0 / (beta * beta * n) + 0.06 ** 2)
                z_arch = math.log(R_ARCH) / se_arch
                pw.append({"design": lab, "D_discrimination": D, "beta": beta, "n_per_cell": n,
                           "SE_experimental_lnratio": round(se_exp, 5),
                           "SE_simulation_lnratio": SIM_SE,
                           "SE_total_lnratio": round(se_tot, 5),
                           "Z_model_discrimination": round(z_disc, 3),
                           "Z_architecture_validation": round(z_arch, 3),
                           "eta_CI_halfwidth_pct": round(100 * (math.exp(1.96 / (beta * math.sqrt(n))) - 1), 2),
                           "discrimination_verdict": ("ADEQUATE" if z_disc >= 3 else
                                                      "MARGINAL" if z_disc >= 2 else "INADEQUATE"),
                           "architecture_verdict": ("ADEQUATE" if z_arch >= 3 else
                                                    "MARGINAL" if z_arch >= 2 else "INADEQUATE")})
    f2 = OUT / "statistical_power_analysis.csv"
    with f2.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pw[0])); w.writeheader(); w.writerows(pw)
    print(f"\nwrote {f2}")

    print("\n=== Sec.17: TEST n = 16, do not defend it.  REVISED design, D = 1.440 ===")
    print(f"  {'beta':>5} | " + " | ".join(f"n={n:<3}" for n in NS))
    print("  Z for MODEL DISCRIMINATION")
    for beta in BETAS:
        cells = [p for p in pw if p["design"].startswith("REVISED") and p["beta"] == beta]
        print(f"  {beta:>5} | " + " | ".join(
            f"{[c for c in cells if c['n_per_cell']==n][0]['Z_model_discrimination']:5.2f}"
            for n in NS))
    print("  Z for Z2/Z1 ARCHITECTURE VALIDATION")
    for beta in BETAS:
        cells = [p for p in pw if p["design"].startswith("REVISED") and p["beta"] == beta]
        print(f"  {beta:>5} | " + " | ".join(
            f"{[c for c in cells if c['n_per_cell']==n][0]['Z_architecture_validation']:5.2f}"
            for n in NS))

    # Sec.15: the two questions need different n. Find the minimum n reaching Z >= 3 at the
    # WORST source-backed beta.
    beta_worst = min(bs)
    print(f"\n=== Sec.15: minimum n at the OBSERVED WORST beta = {beta_worst} ===")
    for lab, D, se_sim in (("model discrimination", D_NEW, SIM_SE),
                           ("Z2/Z1 architecture validation", R_ARCH, 0.06)):
        eff = math.log(D)
        need = None
        for n in range(4, 4001):
            se = math.sqrt(2.0 / (beta_worst ** 2 * n) + se_sim ** 2)
            if eff / se >= 3.0:
                need = n; break
        ceiling = eff / se_sim
        print(f"  {lab:32} min n = {need if need else 'UNREACHABLE'}   "
              f"(ceiling from simulation uncertainty alone: Z = {ceiling:.2f})")
    rows2 = []
    for beta in BETAS:
        for n in NS:
            c = [p for p in pw if p["design"].startswith("REVISED") and p["beta"] == beta
                 and p["n_per_cell"] == n][0]
            rows2.append({"beta": beta, "n_per_cell": n, "total_packages_4_cells": 4 * n,
                          "Z_model_discrimination": c["Z_model_discrimination"],
                          "Z_architecture_validation": c["Z_architecture_validation"],
                          "eta_CI_halfwidth_pct": c["eta_CI_halfwidth_pct"],
                          "n16_classification": ""})
    f3 = OUT / "sample_size_sensitivity.csv"
    with f3.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows2[0])); w.writeheader(); w.writerows(rows2)
    print(f"wrote {f3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
