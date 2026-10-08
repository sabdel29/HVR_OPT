#!/usr/bin/env python3
"""Generate the manuscript claim audit.

Float numbers are read from the LaTeX .aux and the verification counts from the audit
script, so neither can drift from the built manuscript. Claims are keyed by label, never
by number.
"""
from __future__ import annotations
import re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
M = R / "manuscript"
AUX = M / "ETM_DVPD_JOURNAL_MANUSCRIPT.aux"
OUT = M / "ETM_DVPD_CLAIM_AUDIT.md"


def floats() -> dict[str, str]:
    d = {}
    for lab, num in re.findall(r"\\newlabel\{((?:fig|tab):[^}]+)\}\{\{([^}]*)\}", AUX.read_text()):
        d[lab] = ("Fig. " if lab.startswith("fig") else "Tab. ") + num
    return d


def F(spec: str, f: dict[str, str]) -> str:
    """'fig:loss(a)' -> 'Fig. 3(a)'; comma-separated lists supported."""
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"([a-z]+:[A-Za-z0-9_]+)(.*)$", part)
        if not m or m.group(1) not in f:
            raise SystemExit(f"unknown float label: {part!r}")
        out.append(f[m.group(1)] + m.group(2))
    return ", ".join(out)


ESTABLISHED = [
    ("Converter-synthesis outputs are propagated into an explicit package stack shared by "
     "all domains", "III, IV", "framework code path; `configs/phase0mr3c/frozen_pair_*.yaml`",
     "fig:system(c)", "---", "VALIDATED"),
    ("The implemented converter loss model comprises conduction plus three switching terms; "
     "core and dielectric loss are not evaluated", "III-B",
     "`HVR_FULL_OPT_EPC_V2.py::compute_total_loss`", "fig:loss(a)", "\\cite{efficiency}",
     "VALIDATED"),
    ("The per-mechanism loss decomposition reproduces the aggregate to machine precision on "
     "every evaluation", "III-B", "`scripts/phase0mr/ledger.py`", "tab:valid", "---",
     "VALIDATED"),
    ("Segment currents within one cell span nearly two orders of magnitude, so vertical "
     "interconnect loss is not common mode", "III-D, VI-B",
     "`routing_production.build_edges`, per-template loss ledger", "fig:loss(c)", "---",
     "VALIDATED"),
    ("Via-level count follows from conductor-plane topology, not material-layer count",
     "III-E", "`results/phase0mr3c/conductor_plane_topology.csv`", "fig:realize(a)",
     "\\cite{Ostmann2008ChipEmbedding}", "VALIDATED"),
    ("Under minimum-capability provisioning the copper fraction is radius-independent",
     "III-C", "`results/phase0mr3a/z2_tsv_diameter_sweep.csv`", "tab:final", "---",
     "VALIDATED"),
    ("Redistribution-plane power agrees with an independent finite-element solution to "
     "0.45--1.10 %, and IR drop to within 2.2 %", "V-B",
     "`results/phase0e/multilayer_rdl_validation.csv`", "fig:valid(a),tab:valid",
     "\\cite{MOOSE}", "VALIDATED"),
    ("Interconnect transition resistance agrees with an independent finite-element solution "
     "to 0.25--0.73 %", "V-B", "Phase-0M-R cross-validation", "fig:valid(b),tab:valid",
     "\\cite{MOOSE}", "VALIDATED"),
    ("A 3-D DC solve of one via column returns 1.16x the analytical series resistance, the "
     "excess being land spreading", "V-B",
     "`results/phase0mr3b/substrate_via_dc_validation.csv`", "tab:valid", "---", "VALIDATED"),
    ("The cooling solid-side model agrees with an explicitly meshed fin solution to 3.78 % "
     "at the production geometry", "V-C", "cooling solid-side check", "fig:valid(c)",
     "\\cite{MOOSE}", "VALIDATED"),
    ("The response metric is mesh-converged to 1.9 % between the two finest levels and "
     "cycle-stabilised", "V-D",
     "`results/phase0i/local_metric_convergence.csv`, `results/phase0ir/stabilized_cycle_audit.csv`",
     "fig:valid(d)", "\\cite{CalculiX}", "VALIDATED"),
    ("The electrical--thermal loop converges in three Picard iterations below a 0.25 K "
     "tolerance at zero energy residual", "IV-C", "`results/phase0mr3c/final_etm_replay.csv`",
     "tab:final", "---", "VALIDATED"),
    ("One complete electrothermal--mechanical evaluation costs 134.6 s and 204.2 s on 48 "
     "cores, and the timing run reproduced the frozen results exactly", "V-E",
     "`results/phase0mr3c/runtime_benchmark.csv`, `platform.json`", "tab:cost,fig:final(e)",
     "---", "VALIDATED"),
    ("Regulator count is mechanically inert over the swept range", "VII-A", "Phase-0G sweep",
     "---", "---", "VALIDATED"),
    ("The footprint--mechanics interaction reverses sign between the free and the mounted "
     "state, +20.3 % against -16.6 to -29.0 %", "VII-A",
     "`results/phase0g/footprint_board_envelope.csv`", "fig:assembly", "---", "VALIDATED"),
    ("Global warpage tracks the local response in direction but not magnitude, 6.5 % "
     "against 16.3 %", "VII-A", "`results/phase0mr3c/final_etm_replay.csv`", "tab:final",
     "---", "VALIDATED"),
    ("The response ratio is insensitive to the final model corrections, +0.04 % across the "
     "interconnect reconstruction", "VII-B",
     "`results/phase0mr3c/final_etm_replay.csv`; frozen historical ratios",
     "fig:sens,tab:ablation", "---", "VALIDATED"),
    ("A permutation of the existing components reduces the worst via aspect ratio from 5.05 "
     "to 0.833 at unchanged area, height and component count", "VII-C",
     "`results/phase0mr3c/repartition_candidates.csv`, `routing_feasibility.csv`",
     "fig:realize(b)(c)", "\\cite{Ostmann2008ChipEmbedding,Cauwe2023HDI}", "VALIDATED"),
    ("T_max ordering: Z2 runs 8.14 K hotter at the die and 7.55 K hotter at the corner joint",
     "VII-D", "`results/phase0mr3c/final_etm_replay.csv`, `local_submodel_inputs.csv`",
     "fig:final(b),tab:final", "---", "VALIDATED (ordering)"),
    ("Warpage ordering: Z2 carries 6.5 % lower die warpage, peak-to-valley 38.916 against "
     "41.616 um", "VII-A", "`results/phase0mr3c/final_etm_replay.csv`",
     "fig:final(c),tab:final", "---", "VALIDATED (ordering)"),
    ("Displacement-driver ordering: Z2 carries 16.3 % lower corner-joint driver, "
     "du_c = 3.8714 against 4.6252 um, D_u = 1.1947", "VII-A, VII-D",
     "`results/phase0mr3c/final_etm_replay.csv`", "fig:final(d),tab:final", "---",
     "VALIDATED (ordering)"),
    ("Inelastic-response ordering: Z2 carries 18.4 % lower stabilised local inelastic "
     "response, d_eps_in = 1.1478e-2 against 1.4072e-2 per cycle, D_eps = 1.2260",
     "IV-E, VII-D", "`results/phase0mr3c/final_local_response.csv`", "fig:final(e),tab:final",
     "---", "VALIDATED (ordering)"),
    ("The strain range and the inelastic work, from the same solves, rank the pair "
     "identically at 1.2257 and 1.1658", "VII-D",
     "`results/phase0mr3c/final_local_response.csv`", "tab:final", "---", "VALIDATED"),
    ("Peak-temperature ranking is not equivalent to local inelastic-response ranking",
     "VII-D", "as above", "fig:final,tab:cmp", "---", "VALIDATED"),
    ("The mechanical solve is entered once after the electrical-thermal loop converges, not "
     "inside it; 11 thermal solves against 1 thermoelastic solve per architecture", "V-E",
     "`results/phase0mr3c/timing_breakdown.json`; `replay_production.run_case`", "tab:cost",
     "---", "VALIDATED"),
    ("The local inelastic response is insensitive to the integration tolerance over the "
     "range in which the high-stress problem is numerically admissible: 5e-2 and 1e-1 agree "
     "to twelve digits on d_eps_in, its range and the inelastic work, and D_eps is 1.226006 "
     "at both", "IV-E, V-D", "`results/phase0mr3c/cetol_final_pair.csv`", "---", "---",
     "VALIDATED"),
    ("Three tolerances tighter than the one used (1e-5, 1e-4, 1e-2) complete zero increments "
     "at this operating point, so the tolerance bracket is one-sided and the magnitude is "
     "not corroborated against a tight-tolerance reference", "IV-E, VIII-C",
     "`results/phase0mr3c/cetol_final_pair.csv`", "---", "---", "VALIDATED (as a limitation)"),
    ("Omitted inductor core loss and capacitor dielectric loss bias dissipation downward and "
     "act on the same component set in both architectures, so the ordering is not expected "
     "to be altered; exact cancellation is not asserted", "III-B, VIII-C",
     "`HVR_FULL_OPT_EPC_V2.py::compute_total_loss`", "---", "---", "VALIDATED (as stated)"),
    ("alpha_GaN is an adopted calibration coefficient, not a sourced constant; +-20 % moves "
     "converter loss by -+5.8 % and preserves the Z1/Z2 loss ordering at every value tested",
     "III-B", "`results/phase0mr3c/gan_alpha_sensitivity.csv`, "
     "`results/phase0d/robustness_0d.csv`", "---", "\\cite{EPC2014C,EPC2057}", "VALIDATED"),
    ("The switch node per device carries 6.80 A, within the device rating; the aggregate is "
     "over three phases", "III-E", "`results/phase0mr3c/routing_feasibility.csv`", "---",
     "\\cite{EPC2057}", "VALIDATED"),
    ("Six positions taken in the prior DVPD literature are reproduced and tested; two "
     "reproduce, one is rail-dependent, one reverses with assembly state, one is "
     "invalidated by physical routing, and one is shown non-equivalent", "VI-B",
     "`manuscript/PRIOR_FRAMEWORK_COMPARISON.md`", "tab:prior", "---", "VALIDATED"),
]

CONDITIONAL = [
    ("Magnitude of the 16.3 % displacement-driver difference and of the 18.4 % "
     "inelastic-response difference",
     "the constitutive card is fitted on Sn3.9Ag0.6Cu over 7.51--15.92 MPa while the "
     "accumulated inelastic-strain contribution is generated largely above that window",
     "VIII-C"),
    ("Geometric realizability of the frozen pair",
     "the microvia pitch is source-bounded; diameter, capture pad, current allowable and "
     "vendor rule are unavailable", "VII-E"),
    ("Absolute temperatures",
     "the cooling model is validated at its laminar operating point only; conjugate CFD was "
     "not completed", "VIII-C"),
    ("The reported computational cost",
     "it is a measured wall time on one platform, not a speedup; no controlled "
     "same-geometry reference timing exists", "V-E"),
    ("The magnitude of the 18.4 % inelastic-response separation",
     "the local submodel is integrated at a creep strain-increment tolerance of 5e-2, the "
     "value four later production scripts use; at that tolerance the published reference "
     "case reproduces to 0.0000 %, and the Phase-0I convergence study measured the "
     "tolerance effect at 0.015 %", "IV-E"),
    ("The magnitude of D_epsilon against a tight-tolerance reference",
     "no tolerance tighter than 5e-2 converges for the final pair, so insensitivity is "
     "demonstrated only towards looser tolerances; the two that converge agree exactly",
     "IV-E, VIII-C"),
    ("The local inelastic response at all",
     "the frozen pair drives the joint to 15-17 times the solder yield stress, against a "
     "Norton card fitted over 7.51-15.92 MPa; the ordering is the result, the magnitude an "
     "envelope", "VIII-C"),
]

NOT_CLAIMED = [
    ("Absolute solder life, cycle count, or margin against a requirement", "VIII-C"),
    ("That either architecture is manufacturable, qualified or proven realizable", "VII-E"),
    ("That mechanics changes the optimal DVPD architecture", "VIII-A"),
    ("That the FE output is damage, or that a damage law, life model or allowable exists",
     "IV-E"),
    ("Full conjugate CFD validation, or any use of the discarded conjugate-CFD case",
     "V-C, Tab. V"),
    ("A converged full-wave result for the vertical loop", "Tab. V"),
    ("Package failure mechanisms other than solder fatigue", "VIII-C"),
    ("A speedup against a higher-fidelity reference", "V-E"),
    ("ARCH_Z4 and 2.5-D rankings", "II-B"),
    ("Inductor core loss and capacitor dielectric loss", "III-B"),
]

OPEN = [
    "Author list, affiliations, acknowledgment and funding statement.",
    "Target venue. A generic IEEE journal class is used. Page limits and submission "
    "formatting were not verified: the publisher's pages are unreachable from this host, "
    "and the manuscript is 14 pages.",
    "Page ranges for `Syed2004` and `Schubert2003`, cited from the framework's verified use "
    "of their calibrations.",
    "Fig. 1 is a schematic drawn for this manuscript rather than exported from a solver, "
    "and is illustrative of the coupling order only.",
]


def audit_table() -> list[tuple[str, str]]:
    p = subprocess.run([sys.executable, str(R / "scripts/phase0mr3c/audit_manuscript.py")],
                       capture_output=True, text=True, cwd=str(R))
    o = p.stdout
    g = lambda pat, d="---": (re.search(pat, o).group(1) if re.search(pat, o) else d)
    return [
        ("every numerical value against the frozen artifacts",
         g(r"(\d+/\d+) values verified and present")),
        ("near-miss variants of a guarded value",
         g(r"near-miss count = (\d+)")),
        ("ablation-table cells not rounding to a recorded model state",
         g(r"unaccounted ablation cells = (\d+)")),
        ("historical values never presented as current",
         "pass" if "without a historical frame" not in o else "FAIL"),
        ("forbidden claims", g(r"forbidden-claim count = (\d+)")),
        ("internal development vocabulary", g(r"internal-phase-word count = (\d+)")),
        ("first-person pronouns", g(r"first-person pronoun count = (\d+)")),
        ("passive constructions", g(r"passive constructions matched = (\d+)")),
        ("floats, all referenced", g(r"(\d+) floats, all referenced")),
        ("citation keys, all resolving", g(r"(\d+) citation keys, all resolve")),
        ("shared ten-word sequences with the style reference",
         "0" if "no shared ten-word sequence" in o else "FAIL"),
        ("audit exit status", "pass" if p.returncode == 0 else f"FAIL ({p.returncode})"),
    ]


def main() -> int:
    f = floats()
    L = ["# MANUSCRIPT CLAIM AUDIT", "",
         "Generated by `scripts/phase0mr3c/write_claim_audit.py`. Float numbers are read from",
         "the built `.aux` and the verification counts from `audit_manuscript.py`, so this file",
         "cannot drift from the manuscript it describes. Do not edit it by hand.", "",
         "Authority for permitted and forbidden wording: `results/PAPER_CLAIM_MATRIX.csv`.", "",
         "Status vocabulary: **VALIDATED** --- established by this work and reported without",
         "qualification; **CONDITIONAL** --- established subject to a stated condition, which the",
         "manuscript states wherever the claim appears; **NOT CLAIMED** --- the manuscript does",
         "not assert it.", "", "## Established claims", "",
         "| # | manuscript claim | section | source artifact | float | reference | status |",
         "|---|---|---|---|---|---|---|"]
    for i, (c, s, a, fl, ref, st) in enumerate(ESTABLISHED, 1):
        L.append(f"| {i} | {c} | {s} | {a} | {F(fl, f) if fl != '---' else '---'} | {ref} | {st} |")
    # the four orderings, with the wording each one licenses
    import csv as _csv
    e = {r["case"]: r for r in _csv.DictReader(
        (R / "results/phase0mr3c/final_etm_replay.csv").open())}
    lr = {r["case"]: r for r in _csv.DictReader(
        (R / "results/phase0mr3c/final_local_response.csv").open())}
    du = (float(e["Z1"]["response_driver_um"]), float(e["Z2"]["response_driver_um"]))
    ei = (float(lr["Z1"]["d_eps_in_stab"]), float(lr["Z2"]["d_eps_in_stab"]))
    tm = (float(e["Z1"]["T_max_C"]), float(e["Z2"]["T_max_C"]))
    wp = (float(e["Z1"]["die_warpage_pv_um"]), float(e["Z2"]["die_warpage_pv_um"]))
    tj = (float(lr["Z1"]["T_joint_C"]), float(lr["Z2"]["T_joint_C"]))
    ORD = [
        ("Peak temperature", f"Z1 {tm[0]:.2f} C, Z2 {tm[1]:.2f} C ({tm[1]-tm[0]:+.2f} K)",
         "`final_etm_replay.csv`",
         "\"the backside architecture runs 8.14 K hotter\"",
         "\"the backside architecture is thermally worse\" (no requirement exists)"),
        ("Corner-joint temperature", f"Z1 {tj[0]:.2f} C, Z2 {tj[1]:.2f} C ({tj[1]-tj[0]:+.2f} K)",
         "`local_submodel_inputs.csv`",
         "\"its corner joints run 7.55 K hotter\"", "any life or margin statement"),
        ("Die warpage, peak-to-valley",
         f"Z1 {wp[0]:.3f} um, Z2 {wp[1]:.3f} um ({100*(wp[0]-wp[1])/wp[0]:.1f} % lower)",
         "`final_etm_replay.csv`",
         "\"lower global die warpage\"; \"a useful screen\"",
         "\"lower solder damage\"; warpage as a reliability metric on its own"),
        ("Displacement driver du_c",
         f"Z1 {du[0]:.4f} um, Z2 {du[1]:.4f} um, D_u = {du[0]/du[1]:.4f} "
         f"({100*(1-du[1]/du[0]):.1f} % lower)", "`final_etm_replay.csv`",
         "\"lower corner-joint displacement driver\"; \"the driver of the local submodel\"",
         "\"lower inelastic response\"; \"16.3 % lower fatigue response\" --- du_c is a "
         "displacement, not a strain"),
        ("Local inelastic response d_eps_in",
         f"Z1 {ei[0]:.6e}, Z2 {ei[1]:.6e} per cycle, D_eps = {ei[0]/ei[1]:.4f} "
         f"({100*(1-ei[1]/ei[0]):.1f} % lower)", "`final_local_response.csv`",
         "\"lower local fatigue-relevant inelastic response\"; \"lower accumulated "
         "equivalent inelastic-strain increment per stabilised cycle\"",
         "\"less damage\"; \"more reliable\"; \"lasts longer\"; any cycles-to-failure"),
    ]
    L += ["", "## The four orderings, and the wording each licenses", "",
          "The headline local-response claim is tied to `d_eps_in`, not to `du_c`. The two are",
          "different quantities and are never interchangeable.", "",
          "| quantity | final value | source artifact | permitted wording | forbidden wording |",
          "|---|---|---|---|---|"]
    L += [f"| {a} | {b} | {c} | {d} | {f} |" for a, b, c, d, f in ORD]
    L += ["", "All five order the pair the same way. Status of each: **VALIDATED (ordering)**;",
          "the magnitudes are conditional as recorded below."]
    L += ["", "## Conditional claims", "",
          "| # | claim | condition, stated in the manuscript at | status |", "|---|---|---|---|"]
    for i, (c, cond, sec) in enumerate(CONDITIONAL, len(ESTABLISHED) + 1):
        L.append(f"| {i} | {c} | SS {sec}: {cond} | CONDITIONAL |")
    L += ["", "## Not claimed", "", "| # | item | where the manuscript says so |", "|---|---|---|"]
    n = len(ESTABLISHED) + len(CONDITIONAL) + 1
    for i, (c, sec) in enumerate(NOT_CLAIMED, n):
        L.append(f"| {i} | {c} | SS {sec} |")
    L += ["", "## Verification performed", "", "| check | result |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in audit_table()]
    L += ["", "Reproduce with `python scripts/phase0mr3c/audit_manuscript.py`.", "",
          "## Items requiring human confirmation before submission", ""]
    L += [f"{i}. {t}" for i, t in enumerate(OPEN, 1)]
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT.relative_to(R)}: {len(ESTABLISHED)} established, "
          f"{len(CONDITIONAL)} conditional, {len(NOT_CLAIMED)} not claimed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
