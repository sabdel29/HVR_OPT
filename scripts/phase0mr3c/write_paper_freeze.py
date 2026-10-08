#!/usr/bin/env python3
"""Phase-0M-R3C Sections 9-11 --- the paper-freeze decision, claim matrix and figure plan."""
from __future__ import annotations
import csv, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
RES = R / "results"
C3 = RES / "phase0mr3c"


def rd(n, base=C3):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


CLAIMS = [
 dict(claim="A physically audited ETM co-design framework for distributed vertical power "
      "delivery couples converter synthesis, rail-aware interconnect loss, a physical "
      "cooler and a convergent local solder response metric in one self-consistent loop.",
      evidence="results/ETM_DVPD_FULL_TECHNICAL_REPORT.pdf; 22 falsification gates",
      source_status="SOURCE_BACKED", numerical_status="VALIDATED",
      permitted="a physically audited framework; twenty-two falsification gates",
      forbidden="a validated design tool; an optimizer",
      section="Abstract, Sec. I, Sec. III"),
 dict(claim="Vertical placement of the converter changes the local solder fatigue-relevant "
      "inelastic RESPONSE by 16.3 %, and the backside architecture carries the lower "
      "response (D_driver = 1.1947).",
      evidence="results/phase0mr3c/final_etm_replay.csv",
      source_status="MODEL", numerical_status="ROBUST ORDERING, CONDITIONAL MAGNITUDE",
      permitted="lower local fatigue-relevant inelastic response; robust ordering",
      forbidden="less damage; longer life; Z2 outlives Z1; validated relative life",
      section="Sec. V, Fig. 7"),
 dict(claim="Ranking architectures by package T_max is not equivalent to ranking them by "
      "the local solder response: the hotter architecture carries the lower response "
      "(+8.14 K, -16.3 %).",
      evidence="results/phase0mr3c/final_etm_replay.csv",
      source_status="MODEL", numerical_status="ROBUST",
      permitted="T_max ranking is not the response ranking",
      forbidden="temperature is irrelevant to fatigue",
      section="Sec. V"),
 dict(claim="Global package warpage is a poor proxy for the local solder response: it "
      "tracks the direction but not the magnitude.",
      evidence="results/phase0i, results/phase0l; mechanical_layer_status",
      source_status="MODEL", numerical_status="ROBUST",
      permitted="warpage is a poor proxy for local response",
      forbidden="warpage predicts life",
      section="Sec. IV"),
 dict(claim="Rail-aware vertical current paths change intra-VR interconnect loss by orders "
      "of magnitude: a template that puts the 16 V intermediate rail across the tier "
      "boundary instead of the 1 V rail collapses its vertical loss by three orders.",
      evidence="results/phase0mr2, routing_production.template_loss",
      source_status="MODEL", numerical_status="ROBUST",
      permitted="rail-aware path selection changes vertical loss by orders of magnitude",
      forbidden="interconnect loss is common mode",
      section="Sec. III-B"),
 dict(claim="Interconnect and assembly realizability can invalidate a numerically "
      "attractive architecture: three successive corrections (TSV range misapplied, "
      "mid-plane spans, material-layer via counting) each changed the realizability "
      "verdict without changing the response ordering.",
      evidence="DEFECTS #58, #62, #63, #64",
      source_status="SOURCE_BACKED", numerical_status="ROBUST",
      permitted="realizability can invalidate an architecture that looks best numerically",
      forbidden="the architecture is manufacturable",
      section="Sec. VI"),
 dict(claim="A repartition of the existing components makes the 20.408 A switch node an "
      "adjacent-tier RDL transition, dropping the worst build-up aspect ratio from 5.05 "
      "to 0.83, at identical component set, per-tier area and stack height.",
      evidence="results/phase0mr3c/repartition_candidates.csv, routing_feasibility.csv",
      source_status="SOURCE_BOUNDED", numerical_status="GEOMETRY CLOSES",
      permitted="geometrically realizable, process-conditional",
      forbidden="PROVEN_REALIZABLE; manufacturable; process-qualified",
      section="Sec. VI, Fig. 6"),
 dict(claim="The number of regulators is mechanically inert over the swept range.",
      evidence="results/phase0g", source_status="MODEL", numerical_status="ROBUST",
      permitted="regulator count is mechanically inert in this model",
      forbidden="regulator count never matters",
      section="Sec. IV"),
 dict(claim="The HVR footprint/mechanics opposition reported for a free package "
      "disappears once the assembly is mounted; the sign is assembly-state dependent.",
      evidence="results/phase0e, results/phase0f", source_status="MODEL",
      numerical_status="ROBUST", permitted="assembly state can reverse the sign",
      forbidden="footprint opposes reliability",
      section="Sec. IV"),
 dict(claim="Direct 1 V lateral delivery in the evaluated stack is prohibitively lossy; "
      "higher-voltage or vertical distribution is required.",
      evidence="results/phase0b, results/phase0m", source_status="MODEL",
      numerical_status="ROBUST",
      permitted="prohibitively lossy in the evaluated stack",
      forbidden="1000 A cannot be fed laterally",
      section="Sec. I"),
 dict(claim="Under minimum-capability provisioning the TSV conductor cross-section cancels "
      "out of the field resistance: enlarging a via changes the COUNT and essentially "
      "nothing else.",
      evidence="results/phase0mr3a/z2_tsv_diameter_sweep.csv",
      source_status="MODEL", numerical_status="EXACT",
      permitted="phi_Cu = I/(J_design A_field) is radius-independent",
      forbidden="a larger via costs more vias",
      section="Sec. III-B"),
 dict(claim="Absolute solder life for this package.",
      evidence="none", source_status="OPEN", numerical_status="NOT AVAILABLE",
      permitted="(do not state)",
      forbidden="N cycles; qualified lifetime; meets a mission requirement",
      section="explicitly excluded; Sec. VII limitations"),
]

FIGS = [
 ("Fig. 1", "figure", "What does the framework couple, and in what order?",
  "results/phase0m/FIG_0M_*, phase0f diagrams", "CURRENT",
  "the framework is a closed E<->T loop with one-way T->M, at ETM-L1"),
 ("Fig. 2", "figure", "What is the physical stack and where does each rail run?",
  "results/phase0mr3c/FIG_0MR3C_* and the 0M-R3B cross-section", "CURRENT",
  "rail-aware vertical paths; the converter cell resolved into tiers"),
 ("Fig. 3", "figure", "Which assumptions were falsified, and did the answer move?",
  "results/phase0g generated_status_sections (defect register)", "CURRENT",
  "22 gates, 64 registered defects, ordering unchanged throughout"),
 ("Fig. 4", "figure", "Does assembly state change the mechanical conclusion?",
  "results/phase0f, results/phase0e", "CURRENT",
  "the footprint opposition reverses between free and mounted"),
 ("Fig. 5", "figure", "Is the local solder response metric convergent and verified?",
  "results/phase0i, results/phase0ir", "CURRENT",
  "PEEQ is the inelastic path length; mesh- and cycle-converged"),
 ("Fig. 6", "figure", "What does physical routing do to a numerically good architecture?",
  "results/phase0mr3b/FIG_0MR3B_ls_to_L_cross_section.png + 0M-R3C repartition",
  "CURRENT", "worst AR 5.05 -> 0.83 by permutation alone"),
 ("Fig. 7", "figure", "Final Z1 vs Z2 on the frozen repartitioned pair.",
  "results/phase0mr3c/final_etm_replay.csv", "CURRENT",
  "D_driver = 1.1947; Z2 lower response and hotter"),
 ("Fig. 8", "figure", "What is claimed, what is conditional, what is excluded?",
  "results/PAPER_CLAIM_MATRIX.csv", "CURRENT",
  "the claim ladder: response -> damage -> life -> failure, with the cut line"),
 ("Tab. I", "table", "The system specification and the converter design point.",
  "configs/phase0mr3c/frozen_pair_*.yaml", "CURRENT", "1 kW, 48->1 V, 49 cells, N3K3"),
 ("Tab. II", "table", "Governing-equation status: current form, superseded form.",
  "results/phase0h/generated_current_facing.md", "CURRENT",
  "each equation's current form and what it replaced"),
 ("Tab. III", "table", "Realizability contract and where each candidate stands.",
  "results/phase0mr3c/final_pair_status.csv", "CURRENT",
  "geometry closes; four process inputs OPEN"),
 ("Tab. IV", "table", "Open items and their effect on the claims.",
  "results/phase0mr3c/final_open_items or phase0mr3b", "CURRENT",
  "none of the open items blocks the response-ordering claim"),
]


def main() -> int:
    st = yaml.safe_load((RES / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
    fp = {r["case"]: r for r in rd("final_pair_status.csv")}
    d = float(fp["Z1"]["D_driver_final"])

    with (RES / "PAPER_CLAIM_MATRIX.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["claim", "evidence", "source_status",
                                           "numerical_status", "permitted_wording",
                                           "forbidden_wording", "manuscript_section"])
        w.writeheader()
        for c in CLAIMS:
            w.writerow({"claim": c["claim"], "evidence": c["evidence"],
                        "source_status": c["source_status"],
                        "numerical_status": c["numerical_status"],
                        "permitted_wording": c["permitted"],
                        "forbidden_wording": c["forbidden"],
                        "manuscript_section": c["section"]})
    print(f"  wrote PAPER_CLAIM_MATRIX.csv ({len(CLAIMS)} claims)")

    L = ["# PAPER-FREEZE DECISION", "",
         "Decided at the close of Phase 0M-R3C, the last planned technical gate.", "",
         "## 1. The one-sentence contribution", "",
         "> A physically audited electrothermal-mechanical co-design framework for "
         "distributed vertical power delivery that exposes architecture-dependent "
         "reliability RESPONSE, interconnect and assembly realizability constraints, and "
         "identifies when mechanics is design-relevant but not yet an active synthesis "
         "constraint.", "",
         "## 2. The five strongest current claims", "",
         "1. **The framework itself**, audited across twenty-two falsification gates with "
         "sixty-four registered defects, each corrected at source and negative-tested.",
         f"2. **Vertical placement changes the local solder response by 16.3 %**, backside "
         f"lower, D_driver = {d:.4f} on a frozen repartitioned pair with one production "
         f"ETM solve per architecture.",
         "3. **T_max ranking is not the response ranking** --- the hotter architecture "
         "carries the lower response, +8.14 K against -16.3 %.",
         "4. **Rail-aware vertical current paths change intra-VR interconnect loss by "
         "orders of magnitude**, so interconnect is not common mode across partitions.",
         "5. **Routing and assembly realizability can invalidate a numerically attractive "
         "architecture** --- and a pure permutation of the existing components drops the "
         "worst build-up aspect ratio from 5.05 to 0.83.", "",
         "## 3. Conditional claims", "",
         "| claim | conditional on |", "|---|---|",
         "| the 16.3 % MAGNITUDE | a variable-consistent SnAgCu Norton surrogate evaluated "
         "far outside its 7.51-15.92 MPa fitted window. The ORDERING is robust; the "
         "magnitude is an envelope |",
         "| geometric realizability of the frozen pair | a source-BOUNDED microvia pitch; "
         "the diameter, capture pad, current allowable and vendor rule are OPEN |",
         "| the relative-life envelope 1.19-1.22 | two sourced Coffin-Manson exponents; C "
         "cancels in the ratio |",
         "| ARCH_Z4 ordering | an unsourced power-die construction |",
         "| absolute temperatures | a cooler validated only at its laminar production "
         "point; conjugate CFD NOT COMPLETED |", "",
         "## 4. Withdrawn historical claims", "",
         "* the 35.8 % / 12.4 % separation as a CURRENT architecture result (it is the "
         "Phase-0I figure for a different, non-realizable set)",
         "* \"validated relative life\"",
         "* \"Z2 outlives Z1\" and every damage/life wording for the FE response",
         "* the 1.558 relative-life ratio, the 1.25-9.18 parametric span, 16.2 W/um and "
         "2.03 W/um exchange rates, the 188.8 % placement spread",
         "* \"the sourced 34 um via\"; \"22.8 % more vias\" (it is 22.8 % fewer)",
         "* the 673 um `ls_to_L` span, and the three-stacked-microvia count",
         "* \"1000 A cannot be fed laterally\"",
         "* the Phase-0M-R3 pair as a \"current repaired realizable pair\"", "",
         "## 5. What must NOT be claimed", "",
         "* any absolute lifetime, cycle count or margin against a requirement",
         "* that either architecture is manufacturable, qualified or PROVEN_REALIZABLE",
         "* that mechanics CHANGES the optimal DVPD architecture --- it has not been shown "
         "to be an active synthesis constraint",
         "* that the FE output is damage, or that a damage law, life model or allowable "
         "exists",
         "* that the framework is an optimizer, or that G2 has been tested", "",
         "## 6. Open items that block publication", "",
         "**None.** Every open item bears on absolute magnitude or on manufacturability, "
         "neither of which the paper claims.", "",
         "## 7. Future work only", "",
         "high-stress SAC305 characterisation; N_required; an admissible mechanical "
         "allowable and G2; conjugate CFD; cohesive delamination and crack growth; "
         "moisture; full process qualification of the package rules; the microvia current "
         "allowable and vendor design rule; the two remaining package clearances.", "",
         "## 8. Is another technical phase scientifically necessary before submission?", "",
         "**No.** Phase 0M-R3C found no fundamental model contradiction. The deciding "
         f"ordering survived the entire interconnect correction at {100*(d-1.1943)/1.1943:+.2f} %, "
         "which is the strongest evidence available that the result does not depend on the "
         "assumptions that were wrong. Framework development stops here.", "",
         "## Scope statement for the manuscript", "",
         "The paper is **not** framed as \"mechanics changes the optimal DVPD "
         "architecture\". It is framed as a framework paper whose negative results are "
         "part of the contribution:", "",
         "* regulator count is mechanically inert over the swept range;",
         "* the footprint/mechanics opposition disappears in a mounted assembly;",
         "* global warpage is a poor proxy for local solder response;",
         "* physical architecture and assembly state can reverse apparent conclusions;",
         "* rail-aware current paths change interconnect loss by orders of magnitude;",
         "* routing and process realizability can invalidate a numerically attractive "
         "architecture;",
         "* T_max ranking need not equal local mechanical-response ranking."]
    (RES / "PAPER_FREEZE_DECISION.md").write_text("\n".join(L) + "\n")
    print(f"  wrote PAPER_FREEZE_DECISION.md ({len(L)} lines)")

    P = ["# PAPER FIGURE AND TABLE PLAN", "",
         f"Frozen at the close of Phase 0M-R3C. "
         f"{sum(1 for f in FIGS if f[1]=='figure')} main figures, "
         f"{sum(1 for f in FIGS if f[1]=='table')} main tables. No new decorative figures.",
         "", "| id | scientific question | source artifact | status | exact claim it "
         "supports |", "|---|---|---|---|---|"]
    for fid, kind, q, src, stat, claim in FIGS:
        P.append(f"| **{fid}** | {q} | `{src}` | {stat} | {claim} |")
    P += ["", "## Story order", "",
          "1. framework, architecture and coupling flow (Fig. 1, Tab. I)",
          "2. rail-aware electrical path and the physical stack (Fig. 2)",
          "3. the falsification ladder and the major corrected assumptions (Fig. 3, Tab. II)",
          "4. assembly state and the mechanical-response result (Fig. 4)",
          "5. the local solder-response model and its verification (Fig. 5)",
          "6. the physical routing and realizability correction (Fig. 6, Tab. III)",
          "7. the final Z1/Z2 comparison on the frozen repartitioned pair (Fig. 7)",
          "8. claims, conditionals and limitations (Fig. 8, Tab. IV)", "",
          "## Excluded from the manuscript", "",
          "Every absolute-life figure, the withdrawn 35.8 %/12.4 % architecture "
          "comparison, the retired calibrated cooling boundary, the 50 g/s cooler point "
          "(OUT_OF_MODEL_DOMAIN), and all ARCH_Z4 rankings, which remain conditional on an "
          "unsourced power-die construction."]
    (RES / "PAPER_FIGURE_TABLE_PLAN.md").write_text("\n".join(P) + "\n")
    print(f"  wrote PAPER_FIGURE_TABLE_PLAN.md ({len(P)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
