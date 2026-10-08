#!/usr/bin/env python3
"""Phase-0L-R Part 29 -- splice Phase 0L-R into the chronological full technical report."""
from __future__ import annotations
import csv, math, re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
LR = R / "results" / "phase0lr"
G = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0lr"
F = lambda r, k: float(r[k])
rows = lambda n: list(csv.DictReader(open(LR / n)))


def place(s, name, frag, before):
    pat = re.compile(rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n", re.S)
    if pat.search(s):
        print(f"  ok  {name}: refreshed"); return pat.sub(lambda _: frag, s, count=1)
    assert before in s, f"anchor missing for {name}"
    print(f"  ok  {name}: inserted"); return s.replace(before, frag + before, 1)


def sub(s, old, new, what):
    if new in s and old not in s:
        print(f"  ok  {what} (already applied)"); return s
    assert s.count(old) == 1, f"anchor problem for {what}"
    print(f"  ok  {what}"); return s.replace(old, new, 1)


def narrative() -> str:
    mf = rows("model_form_robustness.csv")
    gate = rows("model_form_gate_result.csv")[0]
    dist = {r["arch"]: r for r in rows("damage_weighted_stress_distribution.csv")}
    frac = rows("high_stress_damage_fraction.csv")
    strain = [F(r, "r_strain") for r in mf]
    allr = [F(r, k) for r in mf for k in ("r_strain", "r_energy", "r_range")]
    inside = {r["arch"]: 100*F(r, "damage_fraction") for r in frac if r["stress_bin_MPa"] == "<16"}
    z1, z2 = dist["Z1"], dist["Z2"]
    L = ["<!-- BEGIN GENERATED: phase0lr_narrative -->", "", r"\newpage", "",
         "# Phase 0L-R --- Constitutive Robustness, Report Propagation and Auditor-Dossier "
         "Closure (current authoritative)", ""]
    A = L.append
    A("**Verdict: C --- Z2 > Z1 ORDERING ROBUST, RELATIVE-LIFE MAGNITUDE REMAINS CONDITIONAL.** "
      "Three defects confirmed, one of them found inside the framework's own post-processing, "
      "and one Phase-0L conclusion reversed.")
    A("")
    A("## The ordering is robust for a structural reason")
    A("")
    A(f"All {len(allr)} architecture ratios exceed unity, the smallest being {min(allr):.4f}. More "
      "importantly, the ordering originates **upstream of the solder model**: the global "
      "thermoelastic model imposes a corner shear of 2.7486 um on Z1 against 2.0796 um on Z2 --- "
      "32 % larger, because Z1's substrate is 1.30 mm against Z2's 0.30 mm --- and that model "
      "contains no solder constitutive law at all. The local model only compresses 1.322 to "
      "1.197. Any law monotone in imposed cyclic displacement must rank Z1 worse.")
    A("")
    A(f"The magnitude is a **conditional envelope of {min(strain):.2f} to {max(strain):.2f}** on "
      f"the strain family, widening to {min(allr):.2f}--{max(allr):.2f} if the ranking-only "
      "energy family is included. *Validated relative life* is WITHDRAWN as wording.")
    A("")
    A("## Where the damage is --- correcting Phase 0L")
    A("")
    A("| damage-weighted sigma_vm | Z1 | Z2 |")
    A("|---|---|---|")
    for k in ("p10", "p25", "median", "p75", "p90", "p95", "max"):
        A(f"| {k} | {F(z1, f'sigma_vm_{k}_MPa'):.1f} | {F(z2, f'sigma_vm_{k}_MPa'):.1f} |")
    A("")
    A(f"Only {inside.get('Z1',0):.2f} % (Z1) and {inside.get('Z2',0):.2f} % (Z2) of per-cycle "
      "damage falls inside the 7.51--15.92 MPa calibration window. Phase 0L reported medians of "
      "78 and 72 MPa and concluded the architectures extrapolate differently; weighted properly, "
      f"element by element, they are **{F(z1,'sigma_vm_median_MPa'):.1f}** and "
      f"**{F(z2,'sigma_vm_median_MPa'):.1f} MPa, 1.5 % apart**. That earlier separation was an "
      "artifact of weighting a layer-averaged stress, and is WITHDRAWN. What differs is the "
      "peak: 151.6 MPa against 128.7, and 8.3 % of the cycle above 100 MPa against 5.5 %.")
    A("")
    A(f"![FIG-0LR-A]({G}/FIG_0LR_A_histories.png)")
    A("")
    A("## Numerics versus physics")
    A("")
    A("| quantity | NUMERICS alone | CONSTITUTIVE model alone |")
    A("|---|---|---|")
    A("| D (law discrimination) | **+16.5 %** | -0.2 % |")
    A("| Z2/Z1 strain ratio | +0.2 % | **-6.5 %** |")
    A("| strain metric magnitude | +0.3 % | **+32.2 %** |")
    A("| energy metric magnitude | **+17.8 %** | +10.5 % |")
    A("")
    A("Of the move in D from the Phase-0K-R value of 1.4395, **102 % is energy-integration "
      "resolution and -2 % is the material model.** D is a numerics story; the architecture "
      "ratio is a physics story.")
    A("")
    A(f"![FIG-0LR-D]({G}/FIG_0LR_D_decomposition.png)")
    A("")
    A("## DEFECT #46 --- found by independent reimplementation")
    A("")
    A("`parse_temperature` kept the FIRST temperature block at a given printed time while "
      "`parse_tensors` keeps the LAST. CalculiX prints the same rounded time on both sides of a "
      "step boundary, so tensors and temperature came from opposite sides of all 11 boundaries, "
      "with the parsed temperature wrong by about 55 K. The thermal strain is hydrostatic, so "
      "this injected a spurious VOLUMETRIC inelastic strain into a quantity that must be "
      "isochoric --- trace 8.7e-4 against 2.9e-6 --- and inflated every inelastic-energy number "
      "by **18.5 %**. PEEQ was unaffected, because it is read from the solver rather than "
      "reconstructed. Fixed; agreement with the independent implementation improves from 18.5 % "
      "to 0.76 %.")
    A("")
    A("## The Anand family is re-admitted")
    A("")
    A("Phase 0L rejected the Anand FORM on the strength of the Yuan 2023 EINN+BI parameter set, "
      "which misses the only available creep data by a median factor of 1240. An open-access "
      "source retrieved in this phase (Yamin et al. 2025, doi:10.11113/jurnalteknologi.v87.23172) "
      "gives a different Anand set for SAC305, fitted to the SAME Motalab data, which lands "
      "within a median factor of **1.76** of those measurements after a four-to-six-decade "
      "extrapolation in rate. Both failures were properties of the parameter set, not the form. "
      "The rejection is reversed.")
    A("")
    A("It still cannot be integrated at package stresses. Reduced to the Norton form CalculiX "
      "accepts, the Anand law needs n = 12--19 over the package's stress window, and this solver "
      "has an **integrability ceiling at n = 9--10**: the joint converges at n = 8.13 and 8.97 "
      "and fails at n = 10.04 and 11.86.")
    A("")
    A(f"> **Predeclared model-form gate: {gate['gate_classification']}** --- only two model "
      "families could be parameterised AND integrated where the package operates, and the gate "
      "requires three. No model-form robustness claim is made from the replay; the structural "
      "argument above is separate and stands on its own.")
    A("")
    A(f"![FIG-0LR-E]({G}/FIG_0LR_E_ratios.png)")
    A("")
    A("## DEFECT #44 --- report propagation, and DEFECT #45 --- experiment priority")
    A("")
    A("21 stale current-facing claims were found across the two reports. In this report they "
      "clustered in three generated blocks, chief among them an Executive Summary that "
      "contained no mention of Phase 0L at all. They are repaired at source.")
    A("")
    A("The board-level campaign is **re-sequenced behind material characterisation**. Its "
      "specimen count is set by the simulation-uncertainty floor, not by Weibull scatter: the "
      "ceiling on the discrimination Z-score is 3.61 against a target of 3.0, and halving that "
      "floor takes the campaign from 48 specimens per cell to 18. Worse, fitting an "
      "absolute-life constant on top of an extrapolated constitutive model buries the "
      "constitutive error inside the fitted constant.")
    A("")
    A(f"![FIG-0LR-G]({G}/FIG_0LR_G_ladder.png)")
    A("")
    A("## Literature")
    A("")
    A("**HIGH-STRESS SAC305 DATA IDENTIFIED BUT ACCESS-GATED.** 632 works screened on axes other "
      "than the word *creep*; four P0 and five P1 primary sources sit behind institutional "
      "access, two of them reported open by Unpaywall but refused to scripted fetches. One "
      "retrieval already reversed a Phase-0L conclusion. See "
      "`results/phase0lr/HIGH_STRESS_PAPER_DOWNLOAD_REQUEST.md`.")
    A("")
    A("<!-- END GENERATED: phase0lr_narrative -->")
    return "\n".join(L) + "\n"


def main() -> int:
    s = REP.read_text()
    s = sub(s, "# Phase 0L --- High-Stress SAC305 Constitutive Closure (current authoritative)",
            "# Phase 0L --- High-Stress SAC305 Constitutive Closure (extended by Phase 0L-R)",
            "demote Phase 0L")
    s = place(s, "phase0lr_narrative", narrative(),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
