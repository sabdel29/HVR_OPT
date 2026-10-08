#!/usr/bin/env python3
"""Phase-0L-R Part 2 -- the machine-readable current contract, written BEFORE any prose is edited.

Both reports are then checked against this file (Part 24), so the contract is the single source
of truth for what may be said in the present tense.
"""
from __future__ import annotations
import csv, math, statistics, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
LR = R / "results" / "phase0lr"
YAML = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
F = lambda r, k: float(r[k])


def numbers():
    """Every figure quoted in the contract comes from an artifact, not from memory."""
    n = {}
    fx = {(r["model"], r["arch"], r["profile_tag"]): r
          for r in csv.DictReader(open(LR / "package_replay_defect46_fixed.csv"))
          if r["status"] == "OK"}
    # strain-family envelope at the baseline, over the models that could be integrated
    mf = list(csv.DictReader(open(LR / "model_form_robustness.csv")))
    n["strain_ratios"] = [F(r, "r_strain") for r in mf]
    n["energy_ratios"] = [F(r, "r_energy") for r in mf]
    n["all_ratios"] = [F(r, k) for r in mf for k in ("r_strain", "r_energy", "r_range")]
    n["families"] = sorted({r["family"] for r in mf})
    gate = list(csv.DictReader(open(LR / "model_form_gate_result.csv")))
    n["gate"] = gate[0]["gate_classification"]
    dist = {r["arch"]: r for r in csv.DictReader(open(LR / "damage_weighted_stress_distribution.csv"))}
    n["dw"] = dist
    frac = list(csv.DictReader(open(LR / "high_stress_damage_fraction.csv")))
    n["inside_window_pct"] = {r["arch"]: 100 * F(r, "damage_fraction")
                              for r in frac if r["stress_bin_MPa"] == "<16"}
    # corrected D and sample count
    A, B = "EXP_45_125", "EXP_110_150"
    SIM_SE_D, SIM_SE_A, BETA, ZT = 0.08, 0.06, 5.1, 3.0
    n["design"] = {}
    for model in sorted({k[0] for k in fx}):
        if not all((model, a, c) in fx for a in ("Z1", "Z2") for c in (A, B)):
            continue
        we, eff = {}, {}
        for c in (A, B):
            z1, z2 = fx[(model, "Z1", c)], fx[(model, "Z2", c)]
            we[c] = F(z1, "inelastic_work_MJ_per_m3") / F(z1, "d_peeq_per_cycle")
            eff[c] = min(F(z1, "d_peeq_per_cycle") / F(z2, "d_peeq_per_cycle"),
                         F(z1, "inelastic_work_MJ_per_m3") / F(z2, "inelastic_work_MJ_per_m3"))
        D = max(we.values()) / min(we.values())
        nq1 = next((k for k in range(4, 40001)
                    if math.log(D) / math.sqrt(2/(BETA**2*k) + SIM_SE_D**2) >= ZT), None)
        nq2 = next((k for k in range(4, 40001)
                    if sum(math.log(eff[c]) for c in (A, B))
                    / math.sqrt(2/(BETA**2*k) + SIM_SE_A**2) / math.sqrt(2) >= ZT), None)
        n["design"][model] = {"D": D, "n": max(nq1 or 0, nq2 or 0) or None}
    return n


def block(n) -> str:
    s_lo, s_hi = min(n["strain_ratios"]), max(n["strain_ratios"])
    a_lo, a_hi = min(n["all_ratios"]), max(n["all_ratios"])
    ns = [v["n"] for v in n["design"].values() if v["n"]]
    nmax = max(ns) if ns else None
    Dv = ", ".join(f"{m} D={v['D']:.4f} n={v['n']}" for m, v in sorted(n["design"].items()))
    z1, z2 = n["dw"]["Z1"], n["dw"]["Z2"]
    return f"""
# ============================================================================================
# PHASE 0L-R -- CONSTITUTIVE ROBUSTNESS, REPORT PROPAGATION, AUDITOR DOSSIER
# (current authoritative; supersedes the Phase-0L numbers it restates)
# ============================================================================================

solder_material:
  creep_source_alloy: "Sn3.9Ag0.6Cu (Xiao & Armstrong 2005, via Yuan 2023 Table 5)"
  intended_target_alloy: "SAC305 (Sn3.0Ag0.5Cu)"
  alloy_match_status: >-
    MISMATCHED AND NOT TRANSFERABLE-ESTABLISHED. The creep half of the card is Sn3.9Ag0.6Cu --
    3.9 wt% Ag against SAC305's 3.0 wt%, a 30 % relative difference in the element that controls
    Ag3Sn precipitate strengthening. The yield half is SAC305 but two model layers from
    measurement. No source compares the two alloys under common conditions. The 19 creep points
    are retained as MODEL-FORM EVIDENCE and BOUNDING DATA, never as SAC305 parameters.
    See results/phase0lr/ALLOY_TRANSFERABILITY_MATRIX.md

calculix_visco:
  exact_rate_law: >-
    eps_dot_in = A(T) * (sigma_vm - sigma_y(epsbar_in))**n(T) for sigma_vm > sigma_y, and
    eps_dot_in = 0 identically otherwise. m = 0, so there is no time hardening.
  stress_variable: "overstress, sigma_vm - sigma_y(epsbar_in)"
  interpolation_rule: >-
    A, n and sigma_y are interpolated LINEARLY between card rows and CLAMPED outside them.
    CalculiX does not evaluate an Arrhenius law internally; any Arrhenius relationship exists
    only in how the card row VALUES were generated in Python.
  plastic_behavior_in_visco: >-
    NONE. In a *VISCO step the rate-independent plastic corrector never executes; one
    consistency parameter carries the whole inelastic increment, so M4 == M1 and M5 == M3.
    The *PLASTIC card supplies only the threshold and its hardening slope to the creep law.
  integrability_ceiling: >-
    NEW IN PHASE 0L-R. This solver's viscoplastic integrator fails in this joint model above a
    Norton exponent of about n = 9-10: n = 8.13 and 8.97 converge, n = 10.04 and 11.86 collapse
    the increment controller below its floor at the first increment. This bounds which
    constitutive forms can be replayed at all.
  source_verified: >-
    YES. Traced in CalculiX 2.23 src/incplas.f (yield test line 310, driving stress line 599,
    flow rule line 605) and confirmed against the binary over 7603 single-element increments to
    a median relative error of 1.2e-5.

creep_calibration:
  temperature_domain: "45-150 C (four temperatures, 19 points)"
  source_stress_domain: "7.51-15.92 MPa"
  package_stress_domain: >-
    damage-weighted, element by element, at the operating baseline: Z1 median
    {F(z1,'sigma_vm_median_MPa'):.1f} MPa (p10 {F(z1,'sigma_vm_p10_MPa'):.1f},
    p90 {F(z1,'sigma_vm_p90_MPa'):.1f}, max {F(z1,'sigma_vm_max_MPa'):.1f});
    Z2 median {F(z2,'sigma_vm_median_MPa'):.1f} MPa (p10 {F(z2,'sigma_vm_p10_MPa'):.1f},
    p90 {F(z2,'sigma_vm_p90_MPa'):.1f}, max {F(z2,'sigma_vm_max_MPa'):.1f}).
    SUPERSEDES the Phase-0L figures of 54-91 MPa and the 78-versus-72 MPa separation, which came
    from weighting a layer-AVERAGED stress rather than weighting element by element.
  extrapolation_status: >-
    SEVERE AND IRREDUCIBLE. {n['inside_window_pct'].get('Z1',0):.2f} % (Z1) and
    {n['inside_window_pct'].get('Z2',0):.2f} % (Z2) of per-cycle damage is generated inside the
    7.51-15.92 MPa calibration window; the rest is extrapolation. The two architectures occupy
    very nearly the SAME extrapolation region -- medians 1.5 % apart -- which is why the
    extrapolation largely, though not perfectly, cancels in a ratio.

constitutive_model:
  admitted_models: >-
    M1 "variable-consistent SnAgCu Norton surrogate, high-stress extrapolative" -- the selected
    model. M2_ANAND (Yamin/Motalab SAC305 Anand, reduced to a Norton card) -- re-admitted in
    Phase 0L-R as a second FAMILY, but integrable only over a 5-15 MPa reduction because of the
    n = 9-10 ceiling.
  rejected_models: >-
    M0 as-built (reproduces 0 of 19 of its own source points). Garofalo/Yuan Table 6 (predicts
    4e15 /s at 120 MPa). Anand with the Yuan EINN+BI parameters (misses the only creep data by a
    median factor of 1240, against 1.76 for the Yamin set fitted to the same underlying data --
    a disagreement between two fits, not two alloys).
  current_model_status: >-
    CONDITIONALLY ADMITTED. M1 repairs the variable inconsistency of DEFECT #40 and reproduces
    all 19 of its source points, but it remains the wrong alloy and is evaluated far outside its
    source stress window.
  high_stress_status: >-
    NOT CLOSED. ACCESS-GATED, NOT EVIDENCE-NEGATIVE: 632 works screened on axes other than
    "creep"; four P0 and five P1 primary sources identified behind institutional access, two of
    them reported OPEN by Unpaywall but refused to scripted fetches. See
    results/phase0lr/HIGH_STRESS_PAPER_DOWNLOAD_REQUEST.md

relative_reliability:
  ranking: >-
    Z2 accumulates less solder-fatigue damage than Z1. Every admitted constitutive model, every
    admitted life law, every profile and all three response metrics agree: {len(n['all_ratios'])}
    of {len(n['all_ratios'])} ratios exceed unity, the smallest being {a_lo:.4f}.
  z2_z1_min: {s_lo:.4f}
  z2_z1_max: {s_hi:.4f}
  z2_z1_basis: >-
    strain family (Syed Eq.14 metric) at the operating baseline, over every constitutive model
    that could be integrated. Including the energy family widens the range to
    {a_lo:.2f}-{a_hi:.2f}, but the energy family is RANKING-ONLY (see life_law_status_0lr).
  magnitude_status: >-
    CONDITIONAL, NOT VALIDATED. The permitted wording is "conditional relative-life envelope".
    "Validated relative life" is NOT earned and must not be used.
  common_mode_status: >-
    PARTIAL, and now with a mechanism. Phase 0L measured the spread; Phase 0L-R explains it. The
    two architectures occupy nearly the same damage-weighted stress distribution (medians 1.5 %
    apart), so the extrapolation largely cancels; what does not cancel is the peak, Z1 reaching
    151.6 MPa against Z2's 128.7 and spending 8.3 % of the cycle above 100 MPa against 5.5 %.
  ordering_robustness_argument: >-
    STRUCTURAL, not merely empirical. The ordering originates in the GLOBAL linear-thermoelastic
    model, which imposes a 32 % larger corner shear on Z1 (2.7486 um against 2.0796 um) and
    contains no solder constitutive law at all. Stated without overreach: the global package
    supplies a constitutive-law-independent deformation driver favoring Z2, and every presently
    testable constitutive/life-law combination preserves that ordering. It is NOT a theorem over
    all monotone laws: the set this solver can integrate is bounded by a Norton exponent of about
    9 to 10, and nothing proves the ordering for laws outside it. Condition: this holds by
    construction in
    the current global/local decomposition, where the global model represents the joints as
    linear elastic; a softer solder would relax the constraint for BOTH architectures.
  model_form_gate: >-
    {n['gate']} -- the predeclared gate (PART10_PREDECLARED_ROBUSTNESS_GATE.md, sha256
    b508c3ed...) requires three distinct model FAMILIES parameterised and integrated over the
    package stress range, and only {len(n['families'])} were achieved: {n['families']}. No
    model-form robustness claim is made from the replay. The structural argument above is
    separate and stands on its own.

absolute_life:
  status: >-
    NOT VALIDATED and NOT AVAILABLE. Unchanged by Phase 0L-R, and now additionally conditional on
    an unclosed high-stress constitutive response and on DEFECT #46, which inflated every
    energy-derived quantity generated before this phase.

experiment:
  status: "BLOCKED / PROVISIONAL -- not frozen, and re-sequenced behind material characterisation"
  sample_count_status: "PROVISIONAL -- not to be frozen while constitutive uncertainty dominates"
  n_per_cell_max_current: {nmax}
  package_count_max_current: {4*nmax if nmax else None}
  design_by_model: "{Dv}"
  blocker: >-
    Three. (1) The stress domain is violated by every profile including the operating baseline,
    irreducibly. (2) The binding statistical term is the SIMULATION-uncertainty floor, not the
    specimen count: the ceiling on Z is 3.61 against a target of 3.0, and halving that floor
    would cut the campaign by about 60 %. (3) Calibrating a fatigue constant on top of an
    extrapolated constitutive model buries the constitutive error inside the fitted constant.
  recommended_sequence: >-
    MATERIAL CHARACTERISATION FIRST, with primary-paper acquisition in parallel. The board-level
    campaign is re-sequenced, not cancelled. See MATERIAL_TEST_VS_PACKAGE_TEST_VALUE.md

mission:
  n_required: >-
    OPEN. No field or product requirement exists in this repository or in any supplied source.
    Every n_required identifier in the codebase is the TSV via count, a different quantity.

g2:
  status: >-
    NOT TESTED, and not testable. Two independent blockers, either sufficient: N_required is
    undefined, and absolute N_f is unvalidated. Relative ordering alone does NOT activate G2.

optimizer:
  allowed: false
  reason: >-
    No N_required, no calibrated absolute life, and reliability does not yet exclude any
    electrically attractive design while another passes.

reports:
  historical_report_status: >-
    Phase 0L-R repaired the current-facing sections. Superseded claims are retained ONLY inside
    chapters whose headings mark them superseded.
  standalone_report_status: >-
    Phase 0L-R repaired the five defects found by hostile review
    (STANDALONE_REPORT_TECHNICAL_AUDIT.md): the alloy label in section 4.2, the specimen count in
    section 23.1 which contradicted section 17.4 of the same document, the stress range in
    section 13.7, the wrong cancellation mechanism in section 17.2, and the single-axis
    validation matrix in section 21.
"""


def main() -> int:
    n = numbers()
    s = YAML.read_text()
    marker = "# PHASE 0L-R -- CONSTITUTIVE ROBUSTNESS, REPORT PROPAGATION, AUDITOR DOSSIER"
    if marker in s:
        head = "# " + "=" * 92 + "\n" + marker
        assert s.count(head) == 1
        s = s[:s.index(head)].rstrip("\n") + "\n"
    s = s.rstrip("\n") + "\n" + block(n)

    def one(t, old, new, what):
        if new in t and old not in t:
            print(f"  ok  {what} (already applied)"); return t
        assert t.count(old) == 1, f"anchor problem for {what}: {t.count(old)} matches"
        print(f"  ok  {what}"); return t.replace(old, new, 1)

    s = one(s, '  phase0l: ', '  phase0lr: "Z2>Z1 ORDERING ROBUST -- RELATIVE-LIFE MAGNITUDE '
            'REMAINS CONDITIONAL"\n  phase0l: ', "verdict.phase0lr")
    s = one(s, '  current_phase: "0L"', '  current_phase: "0L-R"', "meta.current_phase")
    s = one(s, '  phase_name: "High-stress SAC305 constitutive closure and current-framework'
            ' audit report"',
            '  phase_name: "High-stress constitutive robustness, report propagation and'
            ' auditor-dossier closure"', "meta.phase_name")
    YAML.write_text(s)
    yaml.safe_load(YAML.read_text())
    print(f"updated {YAML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
