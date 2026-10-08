#!/usr/bin/env python3
"""Phase-0L Part XXIV -- splice Phase 0L into the chronological full technical report.

The standalone current-framework audit report is a SEPARATE deliverable and is not appended
here; this adds the Phase-0L chapter to the historical record only.
"""
from __future__ import annotations
import csv, re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
OUT = R / "results" / "phase0l"
G = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l"
rows = lambda p: list(csv.DictReader(open(OUT / p)))
F = lambda r, k: float(r[k])


def place(s, name, frag, before):
    pat = re.compile(rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n",
                     re.S)
    if pat.search(s):
        print(f"  ok  {name}: refreshed"); return pat.sub(lambda _: frag, s, count=1)
    assert before in s, f"anchor missing for {name}"
    print(f"  ok  {name}: inserted"); return s.replace(before, frag + before, 1)


def sub(s, old, new, what):
    if new in s and old not in s:
        print(f"  ok  {what} (already applied)"); return s
    assert old in s and s.count(old) == 1, f"anchor problem for {what}"
    print(f"  ok  {what}"); return s.replace(old, new, 1)


def narrative() -> str:
    vd = rows("common_mode_verdict.csv")
    base = [c for c in vd if c["profile"] == "OP_BASELINE"]
    rep = [r for r in rows("common_mode_cancellation_test.csv") if r["profile"] == "OP_BASELINE"]
    ex = rows("experiment_reaudit.csv")
    lo, hi = min(F(c, "min") for c in base), max(F(c, "max") for c in base)
    worst = max(base, key=lambda c: F(c, "spread_S"))
    ns = [int(r["n_required_per_cell"]) for r in ex if r["n_required_per_cell"]]
    L = ["<!-- BEGIN GENERATED: phase0l_narrative -->", "", r"\newpage", "",
         "# Phase 0L --- High-Stress SAC305 Constitutive Closure (current authoritative)", ""]
    A = L.append
    A("**Verdict: C --- HIGH-STRESS MODEL-FORM UNCERTAINTY PRESENT BUT Z2/Z1 RANKING SURVIVES.**")
    A("")
    A("Two defects confirmed and two more found. The relative-life ordering holds under every "
      "admissible constitutive model; its magnitude does not, and the claim that the stress "
      "extrapolation is common mode is **withdrawn** in favour of a measured figure.")
    A("")
    A("## What the solver actually integrates")
    A("")
    A("Traced from the CalculiX 2.23 source and confirmed against the binary over 7603 "
      "single-element increments:")
    A("")
    A("$$ \\dot{\\varepsilon}_{in} = A(T)\\left(\\sigma_{vm} - \\sigma_y(\\bar\\varepsilon_{in})"
      "\\right)^{n(T)}, \\qquad \\dot{\\varepsilon}_{in} \\equiv 0 \\ \\text{ for } \\ "
      "\\sigma_{vm} \\le \\sigma_y $$")
    A("")
    A("Median relative error of that form against the solver: 1.2e-5. The manual's stated form "
      "on the full von Mises stress is wrong by a median factor of 14.4. There is no "
      "rate-independent plastic strain in a `*VISCO` step, m = 0, and the temperature "
      "interpolation is linear in A rather than Arrhenius.")
    A("")
    A("## DEFECT #40 --- CONFIRMED")
    A("")
    A("The card was fitted against total applied stress and is consumed as an overstress. The "
      "overstress is non-positive at **16 of the 19 calibration points**, so the card reproduces "
      "**0 of 19** of its own source points when fed back through the solver: 16 return exactly "
      "zero and three are low by 4.7e7, 1.8e12 and 2.4e5. A consistent refit is not "
      "constructible (0 usable points at 45 and 80 C), so the resolution is to remove the yield "
      "threshold, which is what the CalculiX manual itself prescribes for creep below yield.")
    A("")
    A("## DEFECT #41 --- the creep data is a different alloy")
    A("")
    A("The 19 points are Yuan 2023 **Table 5**, not \"Table 26\"; the paper has eleven tables. "
      "Yuan sources them to Xiao & Armstrong 2005, alloy **Sn3.9Ag0.6Cu**, not SAC305. The yield "
      "half of the card is SAC305 but two model layers from measurement. No transferability "
      "evidence exists; 344 works were screened and none is retrievable in this environment.")
    A("")
    A("## Was the extrapolation common mode?")
    A("")
    A("Tested against a tolerance predeclared and hashed before any ratio under an alternative "
      "model existed.")
    A("")
    A("| quantity | min | median | max | S | classification |")
    A("|---|---|---|---|---|---|")
    for c in base:
        A(f"| {c['quantity'].replace('_',' ')} | {F(c,'min'):.4f} | {F(c,'median'):.4f} | "
          f"{F(c,'max'):.4f} | **{F(c,'spread_S'):.4f}** | {c['classification']} |")
    A("")
    A(f"**{worst['classification']}.** The ranking survives in every model, every law and every "
      f"profile; the magnitude does not. Revised Z2/Z1 relative life **{lo:.2f} to {hi:.2f}**, "
      f"against 1.21 to 1.38 before Phase 0L.")
    A("")
    A(f"![FIG-0L-G]({G}/FIG_0L_G_ratios.png)")
    A("")
    A("## Where the damage actually accumulates")
    A("")
    A(f"![FIG-0L-E]({G}/FIG_0L_E_damage_weighted.png)")
    A("")
    A("## Consequence for the experiment")
    A("")
    A("| model | D | n per cell | packages |")
    A("|---|---|---|---|")
    for r in ex:
        A(f"| `{r['model']}` | {F(r,'D_discrimination'):.4f} | "
          f"{r['n_required_per_cell'] or 'unreachable'} | {r['total_packages_4_cells'] or '---'} |")
    A("")
    if ns:
        A(f"The incumbent model reproduces the Phase-0K-R design exactly (D = 1.4395, n = 34), "
          f"verifying the method. Under the corrected model the architecture question needs "
          f"**{max(ns)} per cell, {4*max(ns)} packages**. The 34-per-cell design does not "
          f"survive and the experiment stays unfrozen.")
    A("")
    A(f"![FIG-0L-H]({G}/FIG_0L_H_experiment.png)")
    A("")
    A("## Standalone deliverable")
    A("")
    A("Phase 0L also produced a separate, non-chronological current-framework audit report for "
      "an independent reviewer: `results/ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md` and its "
      "PDF. It is not part of this chronological record and is not reproduced here.")
    A("")
    A("<!-- END GENERATED: phase0l_narrative -->")
    return "\n".join(L) + "\n"


def main() -> int:
    s = REP.read_text()
    s = sub(s, "# Phase 0K-R --- Experimental-Domain and Statistical-Design Closure "
            "(current authoritative)",
            "# Phase 0K-R --- Experimental-Domain and Statistical-Design Closure "
            "(extended by Phase 0L)", "demote Phase 0K-R")
    s = place(s, "phase0l_narrative", narrative(),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
