#!/usr/bin/env python3
"""Phase-0K-R Sec.10/11/12/15/17/20/21 -- final profile selection, power, identifiability."""
from __future__ import annotations
import csv, itertools, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0kr"
C_PL, W_PL = 0.0468, 0.0015          # Syed 2004 author-corrected
C_SH, W_SH = 0.0513, 0.0019
SIM_SE_D = 0.08        # simulation uncertainty on a predicted ratio ACROSS temperature conditions
SIM_SE_A = 0.06        # ... and on an architecture ratio at ONE condition (paired, Phase 0I-R)
BETAS = (3, 4, 5, 6, 8, 10)
NS = (8, 12, 16, 20, 24, 32, 50)
BETA_WORST = 5.1       # observed minimum, George 2010 SAC305 BGA


def load():
    z1 = {r["condition"]: r for r in csv.DictReader(open(OUT / "within_domain_Z1.csv"))}
    z2 = {r["condition"]: r for r in csv.DictReader(open(OUT / "within_domain_Z2.csv"))}
    dom = {(r["arch"], r["condition"]): r
           for r in csv.DictReader(open(OUT / "profile_domain_audit.csv"))}
    return z1, z2, dom


def main() -> int:
    z1, z2, dom = load()
    F = lambda r, k: float(r[k])

    # ---------------- Sec.10: full profile-pair search with a composite score ----------------
    rows = []
    for a, b in itertools.combinations(sorted(z1), 2):
        wa, wb = F(z1[a], "w_over_eps_MPa"), F(z1[b], "w_over_eps_MPa")
        D = max(wa, wb) / min(wa, wb)
        da, db = dom.get(("Z1", a)), dom.get(("Z1", b))
        cls = [x["domain_class"] if x else "UNKNOWN" for x in (da, db)]
        worst = ("INVALID FOR MODEL-DISCRIMINATION DESIGN" if any("INVALID" in c for c in cls)
                 else "SEVERE EXTRAPOLATION" if any("SEVERE" in c for c in cls)
                 else "MILD EXTRAPOLATION" if any("MILD" in c for c in cls)
                 else "FULLY INSIDE CALIBRATED DOMAIN")
        # predicted test duration to 63 % failures, worst case across the two admitted families
        durs = []
        for c in (a, b):
            for Cc, met in ((C_PL, "M4_creep_strain"), (W_PL, "M5_creep_energy_MJ_per_m3")):
                nf = 1.0 / (Cc * F(z1[c], met))
                durs.append(nf * F(z1[c], "cycle_duration_s_at_3Cpermin") / 86400.0)
        se = math.sqrt(2.0 / (BETA_WORST ** 2 * 16) + SIM_SE_D ** 2)
        rows.append({"cond_A": a, "cond_B": b,
                     "T_A": f"{z1[a]['T_min_C']}/{z1[a]['T_max_C']}",
                     "T_B": f"{z1[b]['T_min_C']}/{z1[b]['T_max_C']}",
                     "dwell_A_s": z1[a]["dwell_s"], "dwell_B_s": z1[b]["dwell_s"],
                     "w_over_eps_A": round(wa, 2), "w_over_eps_B": round(wb, 2),
                     "D_discrimination": round(D, 4),
                     "pct_law_separation": round(100 * (D - 1), 1),
                     "Z_discrimination_beta5p1_n16": round(math.log(D) / se, 3),
                     "domain_class_A": cls[0], "domain_class_B": cls[1],
                     "pair_domain_class": worst,
                     "max_cell_duration_days": round(max(durs), 1),
                     "min_cell_duration_days": round(min(durs), 1),
                     "admissible_for_design": worst != "INVALID FOR MODEL-DISCRIMINATION DESIGN"})
    # Sec.10: composite selection, NOT max-D. A pair must be admissible, must reach the
    # predeclared Z >= 3 for Q1 at the observed worst beta with n = 16, and among those the
    # SHORTEST campaign wins -- a 2 % gain in D is not worth 46 extra days per cell.
    for r in rows:
        r["meets_Q1_bar"] = r["Z_discrimination_beta5p1_n16"] >= 3.0
        r["composite_rank_key"] = (not r["admissible_for_design"], not r["meets_Q1_bar"],
                                   r["max_cell_duration_days"])
    rows.sort(key=lambda r: r["composite_rank_key"])
    for r in rows:
        r.pop("composite_rank_key")
    f = OUT / "experiment_profile_search.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote {f}")
    print(f"\n{'pair':38} {'D':>7} {'Z':>6} {'days':>7}  domain")
    for r in rows[:5]:
        print(f"  {r['cond_A'][:16]+' / '+r['cond_B'][:16]:36} {r['D_discrimination']:7.4f} "
              f"{r['Z_discrimination_beta5p1_n16']:6.2f} {r['max_cell_duration_days']:7.0f}  "
              f"{r['pair_domain_class'][:28]}")
    best = rows[0]
    A, B = best["cond_A"], best["cond_B"]
    print(f"\nSELECTED PAIR: {A}  +  {B}")

    # ---------------- Sec.12: the sigma audit ----------------
    print("\n=== Sec.12 -- what 'sigma' actually is ===")
    se_exp = math.sqrt(2.0 / (BETA_WORST ** 2 * 16))
    se_tot = math.sqrt(se_exp ** 2 + SIM_SE_D ** 2)
    print(f"  experimental term  sqrt(2)/(beta*sqrt(n)), beta={BETA_WORST}, n=16 : {se_exp:.4f}")
    print(f"  simulation term    (predicted ratio across temperature conditions) : {SIM_SE_D:.4f}")
    print(f"  combined SE of ln(life ratio)                                      : {se_tot:.4f}")
    print(f"  Z = ln(D)/SE for the SELECTED pair                                 : "
          f"{math.log(best['D_discrimination'])/se_tot:.2f}")
    print("  NOT included: uncertainty in beta itself, uncertainty in the life-law constants,")
    print("  censoring loss, or the model-form spread. It is therefore an EXPECTED")
    print("  DISCRIMINATION Z-SCORE under a stated error budget, not a measured sigma.")

    # ---------------- Sec.15/17: power for BOTH questions ----------------
    r_arch = {c: F(z1[c], "M4_creep_strain") / F(z2[c], "M4_creep_strain") for c in (A, B)}
    r_arch_e = {c: F(z1[c], "M5_creep_energy_MJ_per_m3")
                / F(z2[c], "M5_creep_energy_MJ_per_m3") for c in (A, B)}
    # Each condition has its OWN effect size; using the worst one for both under-states the
    # design. Conservative choice per condition = the smaller of the two law predictions.
    eff_by_cond = {c: min(r_arch[c], r_arch_e[c]) for c in (A, B)}
    eff_arch = min(eff_by_cond.values())
    print(f"\n=== Sec.15 -- TWO questions, different effect sizes ===")
    print(f"  Q1 model discrimination : D = {best['D_discrimination']:.4f}  "
          f"(ln = {math.log(best['D_discrimination']):.4f})")
    for c in (A, B):
        print(f"  Q2 Z2/Z1 at {c:15}: strain {r_arch[c]:.4f}  energy {r_arch_e[c]:.4f}")
    print(f"  Q2 conservative effect  : {eff_arch:.4f}  (ln = {math.log(eff_arch):.4f})")
    pw = []
    for beta in BETAS:
        for n in NS:
            se_d = math.sqrt(2.0 / (beta ** 2 * n) + SIM_SE_D ** 2)
            zd = math.log(best["D_discrimination"]) / se_d
            # Q2 is measured at BOTH conditions -> two independent estimates of "Z2 outlives Z1"
            se_a1 = math.sqrt(2.0 / (beta ** 2 * n) + SIM_SE_A ** 2)
            # Stouffer combination of the two INDEPENDENT condition-level tests, each with its
            # own effect size. Using the worst effect for both was the earlier error.
            zs = [math.log(eff_by_cond[c]) / se_a1 for c in (A, B)]
            za1 = min(zs)
            za2 = sum(zs) / math.sqrt(2.0)
            pw.append({"beta": beta, "n_per_cell": n, "total_packages_4_cells": 4 * n,
                       "Z_Q1_model_discrimination": round(zd, 3),
                       "Z_Q2_arch_one_condition": round(za1, 3),
                       "Z_Q2_arch_both_conditions": round(za2, 3),
                       "eta_CI_halfwidth_pct": round(100 * (math.exp(1.96 / (beta * math.sqrt(n))) - 1), 2),
                       "Q1_verdict": "ADEQUATE" if zd >= 3 else "MARGINAL" if zd >= 2 else "INADEQUATE",
                       "Q2_verdict": "ADEQUATE" if za2 >= 3 else "MARGINAL" if za2 >= 2 else "INADEQUATE"})
    f2 = OUT / "sample_size_sensitivity.csv"
    with f2.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pw[0])); w.writeheader(); w.writerows(pw)
    print(f"\nwrote {f2}")
    print(f"  {'beta':>5} | " + " | ".join(f"n={n:<3}" for n in NS))
    for lab, key in (("Q1 model discrimination", "Z_Q1_model_discrimination"),
                     ("Q2 architecture (both conditions)", "Z_Q2_arch_both_conditions")):
        print(f"  {lab}")
        for beta in BETAS:
            cs = [p for p in pw if p["beta"] == beta]
            print(f"  {beta:>5} | " + " | ".join(
                f"{[c for c in cs if c['n_per_cell']==n][0][key]:5.2f}" for n in NS))
    print(f"\n  minimum n at the observed worst beta = {BETA_WORST}:")
    def zq2(n, beta=BETA_WORST, sim=SIM_SE_A):
        se = math.sqrt(2.0 / (beta ** 2 * n) + sim ** 2)
        return sum(math.log(eff_by_cond[c]) / se for c in (A, B)) / math.sqrt(2.0)
    nq1 = next((n for n in range(4, 5001)
                if math.log(best["D_discrimination"])
                / math.sqrt(2.0 / (BETA_WORST ** 2 * n) + SIM_SE_D ** 2) >= 3.0), None)
    nq2 = next((n for n in range(4, 5001) if zq2(n) >= 3.0), None)
    print(f"    Q1 model discrimination            n = {nq1}   ceiling Z = "
          f"{math.log(best['D_discrimination'])/SIM_SE_D:.2f}")
    print(f"    Q2 architecture, both conditions   n = {nq2 if nq2 else 'UNREACHABLE'}   "
          f"ceiling Z = {sum(math.log(eff_by_cond[c]) for c in (A,B))/SIM_SE_A/math.sqrt(2):.2f}")
    print(f"\n  -> ONE campaign answering BOTH requires n = {max(nq1 or 0, nq2 or 0)} per cell "
          f"= {4*max(nq1 or 0, nq2 or 0)} packages (Sec.15: take the larger)")

    # ---------------- Sec.20: final identifiability ----------------
    idf = []
    for c in (A, B):
        for arch, src in (("Z1", z1), ("Z2", z2)):
            m4, m5 = F(src[c], "M4_creep_strain"), F(src[c], "M5_creep_energy_MJ_per_m3")
            dur = F(z1[c], "cycle_duration_s_at_3Cpermin")
            idf.append({"condition": c, "arch": arch,
                        "T_min_C": src[c]["T_min_C"], "T_max_C": src[c]["T_max_C"],
                        "dwell_s": src[c]["dwell_s"], "M4": m4, "M5": m5,
                        "w_over_eps_MPa": round(m5 / m4, 2),
                        "Nf_strain_Eq14": round(1 / (C_PL * m4), 1),
                        "Nf_energy_Eq15": round(1 / (W_PL * m5), 1),
                        "Nf_strain_Eq16": round(1 / (C_SH * m4), 1),
                        "Nf_energy_Eq17": round(1 / (W_SH * m5), 1),
                        "strain_over_energy": round((1 / (C_PL * m4)) / (1 / (W_PL * m5)), 3),
                        "cycle_h": round(dur / 3600, 2),
                        "days_to_63pct_strain": round(1 / (C_PL * m4) * dur / 86400, 1),
                        "days_to_63pct_energy": round(1 / (W_PL * m5) * dur / 86400, 1),
                        "status": "PREDICTION -- NOT A MEASUREMENT"})
    f3 = OUT / "identifiability_final.csv"
    with f3.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(idf[0])); w.writeheader(); w.writerows(idf)
    print(f"\nwrote {f3}")
    print(f"  {'cell':22} {'Nf strain':>10} {'Nf energy':>10} {'s/e':>6} {'days(s)':>8} {'days(e)':>8}")
    for r in idf:
        print(f"  {r['condition']+' / '+r['arch']:22} {r['Nf_strain_Eq14']:10.0f} "
              f"{r['Nf_energy_Eq15']:10.0f} {r['strain_over_energy']:6.2f} "
              f"{r['days_to_63pct_strain']:8.0f} {r['days_to_63pct_energy']:8.0f}")

    # ---------------- Sec.21: Z4 value of information ----------------
    print("\n=== Sec.21 -- Z4 value of information, rechecked on the FINAL pair ===")
    print("  Z4 was not re-run over the within-domain grid. Its w/eps at the reference condition")
    print("  is 123.18 MPa against Z1's 126.88 -- a D of 1.030, i.e. 3 % of model separation,")
    print("  against a 50 % increase in specimen count. EXCLUDED, unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
