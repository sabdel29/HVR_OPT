#!/usr/bin/env python3
"""Phase-0J Sec.5/6 -- SAC305 life-law candidate database and admissibility gate.

EVERY field is either read from a source that was actually retrieved in this phase, or marked
NOT_AVAILABLE. Nothing is filled in from recollection. Where a constant reaches us through a
review rather than the calibration paper, provenance is recorded as SECONDARY and the
retrieval status of the primary is recorded alongside it.
"""
from __future__ import annotations
import csv
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0j"
NA = "NOT_AVAILABLE"

# Provenance of every retrieved source, probed in this phase.
SRC = {
 "SYED2004":    ("Syed A, 'Accumulated creep strain and energy density based thermal fatigue "
                 "life prediction models for SnAgCu solder joints', Proc. 54th ECTC, 2004, "
                 "pp.737-746", "10.1109/ectc.2004.1319419",
                 "PRIMARY NOT RETRIEVABLE -- IEEE Xplore HTTP 202/paywall; Unpaywall is_oa=False; "
                 "Semantic Scholar openAccessPdf=null"),
 "SCHUBERT2003":("Schubert A, Dudek R, Auerswald E, Gollhardt A, Michel B, Reichl H, 'Fatigue "
                 "life models for SnAgCu and SnPb solder joints evaluated by experiments and "
                 "simulation', Proc. 53rd ECTC, 2003, pp.603-610", "10.1109/ectc.2003.1216343",
                 "PRIMARY NOT RETRIEVABLE -- IEEE Xplore paywall; Unpaywall is_oa=False"),
 "DARVEAUX2002":("Darveaux R, 'Effect of Simulation Methodology on Solder Joint Crack Growth "
                 "Correlation and Fatigue Life Prediction', J. Electron. Packag. 124(3):147, "
                 "2002", "10.1115/1.1413764",
                 "PRIMARY NOT RETRIEVABLE -- ASME HTTP 403; Unpaywall is_oa=False"),
 "YU2026":      ("Yu A et al., 'Review of main life prediction models for solder joints in "
                 "electronic devices', Eng. Res. Express 8:132401, 2026",
                 "10.1088/2631-8695/ae7ce6", "RETRIEVED IN FULL (open access PDF)"),
 "GEORGE2010":  ("George E, 'Thermal cycling reliability of lead-free solders (SAC305 and "
                 "Sn3.5Ag) for high temperature applications', MS thesis, Univ. Maryland, 2010",
                 "hdl:1903/10970", "RETRIEVED IN FULL (DRUM repository PDF)"),
 "IMAPS2008":   ("Ghaffarian R et al. / IMAPS 2008 41st Int. Symp. Microelectronics, "
                 "'Modification to Darveaux Solder Joint Fatigue Life Prediction Method for "
                 "Flip-Chip'", "imapsource.org/article/164109", "RETRIEVED IN FULL"),
 "PHM2026":     ("'PHM Framework for Discrete IGBTs in EV Applications: A PoF-Based Approach', "
                 "Eur. Conf. PHM Society 2026", "papers.phmsociety.org/4920", "RETRIEVED IN FULL"),
}

LAWS = [
 dict(id="L1_COFFIN_MANSON", family="A_STRAIN_RANGE", law="Coffin-Manson",
      src="YU2026", equation="N_f = (1/2)*(d_eps_p / (2*eps_f'))^(1/c)",
      native_metric="PLASTIC strain RANGE (not total inelastic)", metric_units="dimensionless",
      alloy=NA, joint_type="generic LCF", coefficients=NA,
      averaging=NA, failure_def="low-cycle fatigue failure",
      note="Generic form only. No SAC305 eps_f' or c was obtainable from any retrieved source. "
           "Native metric is PLASTIC strain range; our M2 is TOTAL inelastic (plastic+creep) "
           "and CalculiX cannot separate them."),
 dict(id="L2_ENGELMAIER", family="A_STRAIN_RANGE", law="Engelmaier (lead-free constants)",
      src="GEORGE2010", equation="N = (1/2)*(d_gamma/(2*eps_f))^(1/c);  "
           "c = c0 + c1*T_sj + c2*ln(1 + 360/t_dwell)",
      native_metric="total SHEAR strain range d_gamma from a CLOSED-FORM DNP expression "
                    "d_gamma = F*Ld*d_alpha*dT/h, NOT from FEA",
      metric_units="dimensionless", alloy="lead-free (calibration alloy not stated in the "
                   "retrieved text)", joint_type="leadless / BGA",
      coefficients="FORM GIVEN, NUMBERS NOT: eps_f, c0, c1, c2 live in calcePWA and ref [42], "
                   "neither retrievable", averaging="n/a -- algebraic, no FEA field",
      failure_def="50 % population failure",
      note="DECISIVE INCOMPATIBILITY: c depends on t_dwell as ln(1+360/t_dwell). Our cycle has "
           "ZERO dwell, so c diverges and the law is undefined for it. Source also states the "
           "constants were validated only up to 125 C."),
 dict(id="L3_SYED_CREEP_1MECH", family="C_CREEP_DAMAGE",
      law="Syed 2004 cumulative creep strain, single mechanism", src="SYED2004",
      equation="N_f = (C' * eps_acc)^-1,  C' = 1/eps_f (creep ductility)",
      native_metric="ACCUMULATED CREEP strain per cycle", metric_units="dimensionless",
      alloy="SnAgCu (specific SAC composition not stated in the secondary source)",
      joint_type="PBGA", coefficients="C' NOT_AVAILABLE -- requires the creep ductility eps_f, "
                 "not given in any retrieved source",
      averaging=NA, failure_def="thermal fatigue failure",
      note="Closest FORM to our M1. Constant not obtainable."),
 dict(id="L4_SYED_CREEP_2MECH", family="C_CREEP_DAMAGE",
      law="Syed 2004 cumulative creep strain, two mechanisms", src="SYED2004",
      equation="N_f = (C_I*eps_acc_I + C_II*eps_acc_II)^-1",
      native_metric="ACCUMULATED CREEP strain per cycle, PARTITIONED between two creep "
                    "mechanisms by a DOUBLE POWER LAW constitutive model",
      metric_units="dimensionless", alloy="SnAgCu", joint_type="PBGA",
      coefficients="C_I = 0.013, C_II = 0.036  [SECONDARY provenance: YU2026 p.14]",
      averaging=NA, failure_def="thermal fatigue failure",
      note="The only SnAgCu life-law constants obtainable in this phase. BLOCKER: the model "
           "requires eps_acc to be SPLIT between mechanism I and mechanism II. Our Norton card "
           "is a SINGLE power law and cannot produce that partition; the source's partition "
           "rule is in the unretrievable primary."),
 dict(id="L5_SYED_ENERGY", family="B_ENERGY",
      law="Syed 2004 creep strain energy density", src="SYED2004",
      equation="N_f = (W_I*w_acc_I + W_II*w_acc_II)^-1",
      native_metric="accumulated CREEP strain ENERGY DENSITY per cycle, partitioned by mechanism",
      metric_units="energy density (units not stated in the secondary source)",
      alloy="SnAgCu", joint_type="PBGA",
      coefficients="W_I, W_II NOT_AVAILABLE -- YU2026 states the model form but gives no values",
      averaging=NA, failure_def="thermal fatigue failure",
      note="Same mechanism-partition blocker as L4, plus no constants at all."),
 dict(id="L6_DARVEAUX", family="B_ENERGY",
      law="Darveaux crack initiation + propagation", src="DARVEAUX2002",
      equation="N_0 = K1*dW_ave^K2 ; da/dN = K3*dW_ave^K4 ; N_f = N_0 + a/(da/dN)",
      native_metric="volume-averaged VISCOPLASTIC strain energy density per cycle, extracted "
                    "from THREE ELEMENT LAYERS EACH 0.0005 in (12.7 um) THICK at the pad "
                    "interface",
      metric_units="psi or MPa (energy density)", alloy="the widely quoted K1-K4 are for "
                   "EUTECTIC SnPb; no SAC305 set was obtainable",
      joint_type="BGA (explicitly NOT transferable to finer-pitch flip-chip without correction)",
      coefficients="NOT_AVAILABLE for SAC305", averaging="3 layers x 12.7 um at the interface",
      failure_def="crack initiation + growth through the joint",
      note="IMAPS2008 states verbatim that a modelling procedure consistent with Darveaux "
           "theory MUST be used, that relative predictions are +/-25 %, and that ABSOLUTE "
           "predictions 'could be off by a factor of 7' under inconsistent methodology. Our M3 "
           "averages the WHOLE solder core, and our finest element is 37.5 um -- 3x the "
           "required extraction layer. Re-extraction is not possible at this mesh."),
 dict(id="L7_SCHUBERT_STRAIN", family="A_STRAIN_RANGE",
      law="Schubert 2003 SnAgCu strain-based", src="SCHUBERT2003",
      equation=NA, native_metric="accumulated inelastic strain per cycle (per citing works)",
      metric_units="dimensionless", alloy="SnAgCu / SnPb", joint_type="flip-chip BGA w/ underfill",
      coefficients=NA, averaging=NA, failure_def=NA,
      note="Cited by 8 of the retrieved sources; NONE reprints its coefficients. Primary "
           "paywalled. Cannot be evaluated."),
 dict(id="L8_SCHUBERT_ENERGY", family="B_ENERGY", law="Schubert 2003 SnAgCu energy-based",
      src="SCHUBERT2003", equation=NA, native_metric="inelastic strain energy density per cycle",
      metric_units=NA, alloy="SnAgCu", joint_type="flip-chip BGA w/ underfill",
      coefficients=NA, averaging=NA, failure_def=NA,
      note="Same as L7 -- no retrieved source reprints the constants."),
 dict(id="L9_HAMASHA_VIB", family="B_ENERGY", law="Hamasha variable-amplitude plastic work",
      src="YU2026", equation="N_f,i = 7758.3 * W_corr,i^-1.036",
      native_metric="steady-state cyclic PLASTIC WORK per cycle under VIBRATION loading",
      metric_units="not stated", alloy="SnAgCu", joint_type="solder joint",
      coefficients="7758.3, -1.036 [SECONDARY: YU2026]", averaging=NA,
      failure_def="vibration fatigue failure",
      note="LOADING REGIME MISMATCH: calibrated for variable-amplitude mechanical VIBRATION, "
           "not thermal cycling. Sec.4 forbids grouping laws merely because both use energy."),
 dict(id="L10_PHM_DARVEAUX", family="B_ENERGY", law="Darveaux-form, re-calibrated for a "
      "high-lead die-attach", src="PHM2026",
      equation="N_f = a / (0.05321 * dW_ave^2.012),  a = 4 mm",
      native_metric="volume-averaged viscoplastic strain energy density per power cycle",
      metric_units="not stated", alloy="92.5Pb5Sn2.5Ag  -- HIGH-LEAD, NOT SAC305",
      joint_type="IGBT die-attach layer", coefficients="K3 = 0.05321, K4 = 2.012 [PRIMARY]",
      averaging="whole die-attach solder layer", failure_def="loss of switching function (EOL)",
      note="Fully documented and experimentally calibrated on 20 devices -- but a DIFFERENT "
           "ALLOY and a die-attach layer, not a BGA. Rejected under the project's standing "
           "no-alloy-mixing rule, the same rule that rejected SAC405 and SnAgCuCe in Phase 0I."),
]

# ---- Sec.6 admissibility: ten predeclared criteria, applied identically to every candidate.
CRIT = ["1_alloy_SAC305_or_transferable", "2_metric_reproducible_by_our_solver",
        "3_metric_definition_unambiguous", "4_loading_regime_overlaps",
        "5_joint_type_relevant", "6_defined_fatigue_endpoint",
        "7_coefficients_available", "8_units_reconcilable",
        "9_source_experimental_or_calibrated", "10_no_undocumented_conversion"]

VERDICT = {
 "L1_COFFIN_MANSON":  ([0,0,1,1,1,1,0,1,1,0], "INADMISSIBLE",
    "No SAC305 constants; native metric is plastic-only and our solver cannot separate plastic "
    "from creep."),
 "L2_ENGELMAIER":     ([0,0,1,0,1,1,0,1,1,0], "INADMISSIBLE",
    "Fatigue exponent diverges at zero dwell, which is our cycle; strain is defined by a "
    "closed-form DNP expression, not an FEA field; constants unretrievable."),
 "L3_SYED_CREEP_1MECH":([1,0,0,0,1,1,0,1,1,0], "INADMISSIBLE",
    "Correct FORM for our M1, but C' requires a creep ductility that no retrieved source gives."),
 "L4_SYED_CREEP_2MECH":([1,0,0,0,1,1,1,1,0,0], "CONDITIONALLY TRANSFERABLE",
    "The only candidate with SnAgCu constants. Fails on the mechanism partition (our Norton is "
    "a single power law), on the unstated averaging volume, on unknown calibration ATC "
    "conditions, and on SECONDARY-only provenance."),
 "L5_SYED_ENERGY":    ([1,0,0,0,1,1,0,0,0,0], "INADMISSIBLE", "No constants at all."),
 "L6_DARVEAUX":       ([0,0,1,1,1,1,0,1,1,0], "INADMISSIBLE",
    "Quoted constants are eutectic SnPb; requires a 12.7 um interface-layer extraction our "
    "37.5 um mesh cannot resolve; source warns of a factor-7 absolute error under inconsistent "
    "methodology."),
 "L7_SCHUBERT_STRAIN":([1,0,0,0,1,0,0,0,1,0], "INADMISSIBLE", "No equation, no constants."),
 "L8_SCHUBERT_ENERGY":([1,0,0,0,1,0,0,0,1,0], "INADMISSIBLE", "No equation, no constants."),
 "L9_HAMASHA_VIB":    ([1,1,1,0,1,1,1,0,1,1], "INADMISSIBLE",
    "Vibration loading, not thermal cycling. Criterion 4 fails outright."),
 "L10_PHM_DARVEAUX":  ([0,1,1,0,0,1,1,1,1,1], "INADMISSIBLE",
    "High-lead die-attach alloy and joint. Criterion 1 fails outright."),
}


def main() -> int:
    rows = []
    for L in LAWS:
        cite, doi, retr = SRC[L["src"]]
        flags, verdict, why = VERDICT[L["id"]]
        r = {"id": L["id"], "family": L["family"], "law": L["law"], "citation": cite,
             "doi": doi, "primary_retrieval_status": retr,
             "constants_provenance": ("SECONDARY (review reprint)" if "SECONDARY" in
                                      L["coefficients"] else
                                      ("PRIMARY" if L["coefficients"] != NA and
                                       "NOT_AVAILABLE" not in L["coefficients"] else NA)),
             "equation": L["equation"], "native_metric": L["native_metric"],
             "metric_units": L["metric_units"], "alloy": L["alloy"],
             "joint_type": L["joint_type"], "coefficients": L["coefficients"],
             "averaging_method": L["averaging"], "failure_definition": L["failure_def"],
             # -- calibration metadata: NOT fabricated where the primary was unreachable
             "joint_dimensions": NA, "package_type": L["joint_type"],
             "T_min_C": NA, "T_max_C": NA, "dT_K": NA, "ramp_rate": NA, "dwell": NA,
             "cycling_frequency": NA, "constitutive_model_used": (
                 "double power law / hyperbolic sine (unified creep)" if "SYED" in L["id"]
                 else ("Anand" if "DARVEAUX" in L["id"] else NA)),
             "sample_count": ("20 DUTs" if L["id"] == "L10_PHM_DARVEAUX" else NA),
             "calibration_range": NA, "validation_range": NA, "reported_fit_error": (
                 "<10 % single mechanism, <30 % two mechanisms [SECONDARY: YU2026]"
                 if "SYED_CREEP" in L["id"] else
                 ("+/-25 % relative, up to factor 7 absolute [IMAPS2008]"
                  if L["id"] == "L6_DARVEAUX" else NA)),
             "predicts": L["failure_def"],
             "which_of_our_metrics": ("M1" if "CREEP_1MECH" in L["id"] or "2MECH" in L["id"]
                                      else ("M2" if L["family"] == "A_STRAIN_RANGE" else "M3")),
             "note": L["note"], "admissibility": verdict, "reason": why}
        for c, f in zip(CRIT, flags):
            r[c] = "PASS" if f else "FAIL"
        r["criteria_passed"] = f"{sum(flags)}/10"
        rows.append(r)
    f = OUT / "SAC305_LIFE_LAW_DATABASE.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote {f}  ({len(rows)} candidates)")
    for r in rows:
        print(f"  {r['id']:22} {r['criteria_passed']:>5}  {r['admissibility']}")
    n_adm = sum(r["admissibility"] == "ADMISSIBLE" for r in rows)
    n_con = sum(r["admissibility"] == "CONDITIONALLY TRANSFERABLE" for r in rows)
    print(f"\nADMISSIBLE: {n_adm}   CONDITIONALLY TRANSFERABLE: {n_con}   "
          f"INADMISSIBLE: {len(rows)-n_adm-n_con}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
