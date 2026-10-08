#!/usr/bin/env python3
"""Phase-0J-R Sec.18/19/23/25 -- revised admissibility, per-law lifetime, architecture table."""
from __future__ import annotations
import csv
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0jr"
P0J = R / "results" / "phase0j"

C_PL, W_PL = 0.0468, 0.0015          # Syed 2004 AUTHOR-CORRECTED, double power law
C_SH, W_SH = 0.0513, 0.0019          # Syed 2004 AUTHOR-CORRECTED, hyperbolic sine
SCH_STRAIN_EXP, SCH_ENERGY_EXP = 1.3, 1.0    # Schubert 2003 SnAgCu slopes (prefactors absent)
A = ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE")
SHORT = {A[0]: "Z1", A[1]: "Z2", A[2]: "Z4"}


def load():
    syed = {r["short"]: r for r in csv.DictReader(open(OUT / "syed_layer_metrics.csv"))
            if r["n_mid"] == "10"}
    nat = {r["arch"]: r for r in csv.DictReader(open(P0J / "native_metrics_by_architecture.csv"))
           if (r["arch"], r["h_sub_mm"]) in [(A[0], "1.3"), (A[1], "0.3"), (A[2], "0.3")]}
    return syed, nat


def main() -> int:
    syed, nat = load()
    m4 = {a: float(syed[SHORT[a]]["M4_syed_layer"]) for a in A}
    m5 = {a: float(syed[SHORT[a]]["M5_syed_layer_MJ_per_m3"]) for a in A}
    m1 = {a: float(nat[a]["M1_accum_inelastic_path"]) for a in A}
    m2 = {a: float(nat[a]["M2_strain_range"]) for a in A}
    m3 = {a: float(nat[a]["M3_inelastic_work_MJ_per_m3"]) for a in A}
    pel = {a: float(nat[a]["P_elec_total_w"]) for a in A}
    Z1 = A[0]

    # ---------- Sec.23 architecture comparison after metric matching ----------
    rows = []
    for a in A:
        rows.append({"arch": a, "h_sub_mm": nat[a]["h_sub_mm"],
                     "P_elec_total_w": pel[a], "T_min_C": 25.0,
                     "T_max_C": float(nat[a]["T_hot_C"]), "dT_K": float(nat[a]["dT_K"]),
                     "dwell_each_extreme_s": 300.0,
                     "M1_total_inelastic_path_core": m1[a],
                     "M2_direct_inelastic_range_core": m2[a],
                     "M3_total_inelastic_energy_core": m3[a],
                     "M4_accum_creep_strain_syed25um": m4[a],
                     "M5_creep_energy_syed25um_MJ_per_m3": m5[a],
                     "w_over_eps_MPa": m5[a] / m4[a],
                     "Nf_syed_strain_corrected": 1.0 / (C_PL * m4[a]),
                     "Nf_syed_energy_corrected": 1.0 / (W_PL * m5[a]),
                     "rel_life_vs_Z1_syed_strain": m4[Z1] / m4[a],
                     "rel_life_vs_Z1_syed_energy": m5[Z1] / m5[a],
                     "domain_eps": "INTERPOLATION -- inside Syed's 0.00213-0.0777",
                     "domain_w": "INTERPOLATION -- inside Syed's 0.0665-2.424 MPa",
                     "domain_w_over_eps": "OUTSIDE -- Syed's packages sit at 28.8-30.0 MPa"})
    f = OUT / "architecture_after_metric_matching.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote {f}")

    # ---------- Sec.25 lifetime by primary law ----------
    laws = []
    def add(law, metric, vals, nf, absrel, dom, note):
        laws.append({"law": law, "native_metric": metric,
                     "Z1": nf[A[0]], "Z2": nf[A[1]], "Z4": nf[A[2]],
                     # life ratio, not metric ratio: N_f(arch) / N_f(Z1)
                     "Z2_over_Z1": nf[A[1]] / nf[A[0]] if nf[A[0]] else "",
                     "Z4_over_Z1": nf[A[2]] / nf[A[0]] if nf[A[0]] else "",
                     "ranking": "Z2 > Z1 > Z4",
                     "absolute_or_relative": absrel, "domain_status": dom, "note": note})
    nf_s = {a: 1.0 / (C_PL * m4[a]) for a in A}
    nf_e = {a: 1.0 / (W_PL * m5[a]) for a in A}
    nf_ss = {a: 1.0 / (C_SH * m4[a]) for a in A}
    nf_se = {a: 1.0 / (W_SH * m5[a]) for a in A}
    add("Syed 2004 corrected, total accumulated creep strain, double power law (Eq.14)",
        "M4 accumulated creep strain per cycle, 25 um layers", m4, nf_s,
        "RELATIVE validated; ABSOLUTE conditional",
        "eps INSIDE calibration range; w/eps OUTSIDE",
        "C' = 0.0468. Averaging volume MATCHED to the source.")
    add("Syed 2004 corrected, creep strain energy density, double power law (Eq.15)",
        "M5 creep energy density per cycle, 25 um layers", m5, nf_e,
        "RELATIVE validated; ABSOLUTE conditional",
        "w INSIDE calibration range; w/eps OUTSIDE",
        "W' = 0.0015. Disagrees with Eq.14 on ABSOLUTE life by 4.1x.")
    add("Syed 2004 corrected, accumulated creep strain, hyperbolic sine (Eq.16)",
        "M4", m4, nf_ss, "SENSITIVITY ONLY",
        "our Norton card is neither Wiese nor sinh",
        "C' = 0.0513. Bounds the constitutive-model sensitivity of the constant at +9.6 %.")
    add("Syed 2004 corrected, creep energy density, hyperbolic sine (Eq.17)",
        "M5", m5, nf_se, "SENSITIVITY ONLY", "as above", "W' = 0.0019.")
    # Schubert: slope only, no prefactor -> RELATIVE ONLY
    laws.append({"law": "Schubert 2003 SnAgCu, accumulated creep strain (Eq.5)",
                 "native_metric": "accumulated creep strain, band of local maxima",
                 "Z1": "", "Z2": "", "Z4": "",
                 "Z2_over_Z1": (m4[A[0]] / m4[A[1]]) ** SCH_STRAIN_EXP,
                 "Z4_over_Z1": (m4[A[0]] / m4[A[2]]) ** SCH_STRAIN_EXP,
                 "ranking": "Z2 > Z1 > Z4", "absolute_or_relative": "RELATIVE ONLY",
                 "domain_status": "alloy SAC387, spatial definition differs",
                 "note": "slope -1.3 printed in the text; PREFACTOR NOT PRINTED, so no "
                         "absolute life is possible from this source."})
    laws.append({"law": "Schubert 2003 SnAgCu, viscoplastic energy density (Eq.6)",
                 "native_metric": "creep energy density, band of local maxima",
                 "Z1": "", "Z2": "", "Z4": "",
                 "Z2_over_Z1": (m5[A[0]] / m5[A[1]]) ** SCH_ENERGY_EXP,
                 "Z4_over_Z1": (m5[A[0]] / m5[A[2]]) ** SCH_ENERGY_EXP,
                 "ranking": "Z2 > Z1 > Z4", "absolute_or_relative": "RELATIVE ONLY",
                 "domain_status": "alloy SAC387", "note": "slope -1.0; prefactor not printed."})
    laws.append({"law": "Darveaux 2000 crack initiation + growth",
                 "native_metric": "viscoplastic SED over 12.7 um interface layers",
                 "Z1": "", "Z2": "", "Z4": "", "Z2_over_Z1": "", "Z4_over_Z1": "",
                 "ranking": "", "absolute_or_relative": "NOT APPLIED",
                 "domain_status": "ALLOY MISMATCH -- eutectic SnPb only",
                 "note": "K1-K4 recovered in full from primary Table 6, but every row is "
                         "62Sn36Pb2Ag / 60Sn40Pb. No SAC constants exist in the source."})
    laws.append({"law": "Vasudevan & Fan 2008 SAC acceleration factor",
                 "native_metric": "none -- N1/N2 from f, dT, T_max",
                 "Z1": "", "Z2": "", "Z4": "", "Z2_over_Z1": "", "Z4_over_Z1": "",
                 "ranking": "", "absolute_or_relative": "NOT A DAMAGE MODEL",
                 "domain_status": "SAC105/305/405, 17 test pairs, <6 % deviation",
                 "note": "Cannot convert an FEA metric into a life. Usable for test-to-field "
                         "scaling of a REQUIREMENT once one exists."})
    f = OUT / "lifetime_by_primary_law.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(laws[0])); w.writeheader(); w.writerows(laws)
    print(f"wrote {f}")
    print(f"\n{'law':64} {'Z2/Z1':>8} {'Z4/Z1':>8}")
    for l in laws:
        if l["Z2_over_Z1"] != "":
            print(f"{l['law'][:64]:64} {float(l['Z2_over_Z1']):8.4f} "
                  f"{float(l['Z4_over_Z1']):8.4f}")
    rr = [float(l["Z2_over_Z1"]) for l in laws if l["Z2_over_Z1"] != ""]
    print(f"\nZ2/Z1 across all admissible-for-relative laws: {min(rr):.3f} to {max(rr):.3f}")
    print(f"ranking agreement: {'ROBUST' if all(x > 1 for x in rr) else 'MODEL-FORM DEPENDENT'}")

    # ---------- Sec.26 electrical cost, recomputed on the matched metric ----------
    ec = []
    for a in (A[1], A[2]):
        dP = pel[a] - pel[Z1]
        for lab, ratio in (("Syed strain (Eq.14)", m4[Z1] / m4[a]),
                           ("Syed energy (Eq.15)", m5[Z1] / m5[a]),
                           ("Schubert strain (slope 1.3)", (m4[Z1] / m4[a]) ** 1.3)):
            ec.append({"comparison": f"{SHORT[a]} vs Z1", "law": lab,
                       "dP_elec_W": round(dP, 4), "life_multiple": round(ratio, 4),
                       "W_per_life_multiple": round(dP / (ratio - 1), 3) if abs(ratio - 1) > 1e-6
                       else "n/a",
                       "supersedes": "the Phase-0J value of 1.558x, which used the Phase-0I "
                                     "core-averaged M1 rather than Syed's 25 um layer"})
    f = OUT / "electrical_cost_revised.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ec[0])); w.writeheader(); w.writerows(ec)
    print(f"\nwrote {f}")
    for r in ec[:3]:
        print(f"  {r['comparison']}  {r['law']:30} +{r['dP_elec_W']} W -> {r['life_multiple']}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
