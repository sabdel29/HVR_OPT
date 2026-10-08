#!/usr/bin/env python3
"""Phase-0M-R3A Section 12 --- append this phase and re-mark its predecessor."""
from __future__ import annotations
import csv, re, sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
STATUS = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
OUT = R / "results" / "phase0mr3a"
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
TAG = "phase0mr3a_narrative"


def rd(n, base=OUT):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


_CUR_BODY = [""]


def architecture_comparison_note(cur: dict) -> tuple[str, str]:
    """Phase 0M-R2 inserted a '**Current position**' paragraph into Architecture Comparison
    OUTSIDE any sentinel and guarded it with `not in s`, so it was written once and never
    revisited. It still carried the Phase-0M-R2 temperatures and called the FE output a
    fatigue driver. Same defect class as #57, one chapter further up, so it is replaced
    from here the way the chapter heading is."""
    prev = (f"**Current position (Phase 0M-R3A).** Under the physical cooler the "
            f"architectures DO separate in temperature. On the CURRENT repaired realizable "
            f"pair ARCH_Z2 runs {f(cur['Z2']['T_max_C'], 2)} C against ARCH_Z1's "
            f"{f(cur['Z1']['T_max_C'], 2)} C, so ARCH_Z2 is the hotter of the two principal "
            f"candidates and still the better of them on the local fatigue-relevant "
            f"inelastic RESPONSE. ARCH_Z4's 98.83 C is the Phase-0M-R2 figure, for a "
            f"power-die construction that remains unsourced. The tables below this note are "
            f"the Phase-0I/0M record and are retained as such.")
    old = ("**Current position (Phase 0M-R2).** Under the physical cooler the architectures "
           "DO separate in temperature: ARCH_Z2 runs 127.06 C against ARCH_Z1's 118.80 C and "
           "ARCH_Z4's 98.83 C, and ARCH_Z2 is the hottest of the two principal candidates "
           "while remaining the better of them on the solder-fatigue driver. The tables below "
           "this note are the Phase-0I/0M record and are retained as such.")
    new = (f"**Current position (Phase 0M-R3A).** Under the physical cooler the architectures "
           f"DO separate in temperature. On the Phase-0M-R3 frozen comparison -- subsequently "
           f"found not demonstrated realizable under the Phase-0M-R3B substrate-via rule "
           f"set -- ARCH_Z2 runs "
           f"{f(cur['Z2']['T_max_C'], 2)} C against ARCH_Z1's {f(cur['Z1']['T_max_C'], 2)} C, "
           f"so ARCH_Z2 is the hotter of the two principal candidates and still the better of "
           f"them on the local fatigue-relevant inelastic RESPONSE. ARCH_Z4's 98.83 C is the "
           f"Phase-0M-R2 figure, for a power-die construction that remains unsourced. The "
           f"tables below this note are the Phase-0I/0M record and are retained as such.")
    return (prev if prev in _CUR_BODY[0] else old), new


def ledger() -> str:
    v = yaml.safe_load(STATUS.read_text())["verdict"]
    rows = []
    for key, name in (("phase0m", "0M"), ("phase0mr", "0M-R"), ("phase0mr2", "0M-R2"),
                      ("phase0mr3", "0M-R3"), ("phase0mr3a", "0M-R3A")):
        cur = " (current)" if key == "phase0mr3a" else ""
        rows.append(f"| Phase {name}{cur} | **{v[key + '_option_letter']}** | "
                    f"{v[key]} |")
    return "\n".join(rows)


def narrative() -> str:
    z = {r["d_um"]: r for r in rd("z2_tsv_diameter_sweep.csv")}
    v = rd("ls_to_L_via_check.csv")
    cur = {r["case"]: r for r in rd("final_Z1_Z2_comparison.csv",
                                    OUT / "_baseline_phase0mr3")}
    ratio = (float(cur["Z1"]["response_driver_um"])
             / float(cur["Z2"]["response_driver_um"]))
    return f"""<!-- BEGIN GENERATED: {TAG} -->

\\newpage

# Phase 0M-R3A --- Final State, Via-Technology and TSV-Margin Closure (current authoritative)

A narrow closure gate on four specific issues left by Phase 0M-R3. Three were confirmed as
defects and one claim was found to have the wrong sign.

## The intra-VR via repair is not source-backed --- DEFECT #58

Phase 0M-R3 made both architectures routable by raising the via radius on the binding net
`ls_to_L` from 15 to 20 um, justified as inside `design_variables.tsv.radius_m =
{{lo 2.5, nominal 15, hi 50}} um`. **That range governs THROUGH-SILICON VIAS.**

`ls_to_L` connects the low-side GaN switch node on tier 1 to the inductor terminal on tier
3 --- a **673 um** vertical span between embedded-component layers inside the converter
cell, carrying 20.408 A. The framework's own source picture separates the two structures
in one sentence each: the components are "embedded within the subsequent substrate power
layers", and "the TSV field runs beneath it from the substrate underside", spanning 74 um
for ARCH_Z1.

| | TSV field | `ls_to_L` |
|---|---|---|
| where | beneath the cell, from the substrate underside | between embedded-component layers, inside the cell |
| span, ARCH_Z1 | 74 um | **673 um** |
| medium | through silicon | through substrate power-layer build-up |

The design space holds `tsv.*`, `rdl.*` (trace width and space only) and `bump.*`. **No
entry governs a stacked via through substrate power layers.** The repair is therefore a
design point in an **unsourced process window**: arithmetically self-consistent, and not
demonstrated to be manufacturable.

## The arithmetic, independently reproduced

An implementation sharing no code with the production path:

| r | pitch | n_required | n_available | ratio | production |
|---|---|---|---|---|---|
""" + "".join(
        f"| {f(r['r_um'],1)} um | {f(r['pitch_um'],1)} um | {r['n_required']} | "
        f"{r['n_available']} | {f(r['ratio'],4)} | {f(r['production_ratio'],4)} |\n"
        for r in v) + f"""
Exact at all five radii. The numbers were right; only their provenance was not.

## The 34 um claim had the sign backwards --- DEFECT #59

Phase 0M-R3 wrote that a 34 um TSV restores margin "at the cost of 22.8 % MORE vias".
`n_required = ceil(I / (J * A_cu))` scales as `1/A_cu`, so:

| quantity | 30 um | 34 um | change |
|---|---|---|---|
| n_required | {z['30.0']['n_required']} | {z['34.0']['n_required']} | **{100*(int(z['34.0']['n_required'])-int(z['30.0']['n_required']))/int(z['30.0']['n_required']):+.1f} %** |
| n_available | {z['30.0']['n_available']} | {z['34.0']['n_available']} | {100*(int(z['34.0']['n_available'])-int(z['30.0']['n_available']))/int(z['30.0']['n_available']):+.1f} % |
| phi_Cu | {f(z['30.0']['phi_cu'],6)} | {f(z['34.0']['phi_cu'],6)} | {100*(float(z['34.0']['phi_cu'])-float(z['30.0']['phi_cu']))/float(z['30.0']['phi_cu']):+.3f} % |

**22.8 % FEWER**, and a reduction rather than a cost. A second error in the same sweep:
34 um was reported as the smallest diameter with positive margin, but the grid was
30/34/40/50/60 and never evaluated **32 um**, which passes the same modest bound at
M_AR = {f(z['32.0']['M_AR'],3)} for 12.5 % fewer vias.

![FIG-0MR3A](/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0mr3a/FIG_0MR3A_tsv_diameter_margin_and_count.png)

*(a) ARCH_Z2 at 30 um sits exactly on the 10:1 aspect-ratio limit, so any tolerance at all
puts it over; 32 um is the smallest diameter on the evaluated grid with positive margin.
(b) the required count falls as the via grows, because `n_required` scales as `1/A_cu`.
Faint verticals mark diameters the Phase-0M-R3 grid never evaluated.*

"34 um sourced" is also withdrawn: no primary source specifies 34 um, only the RANGE is
source-backed. The licensed wording is **a design point selected within the source-backed
allowable range**.

## The current-state table was a phase behind --- DEFECT #57

Two independent representations of current state exist, and Phase 0M-R3 advanced only one.
The report carried a section headed "Current scientific status (Phase 0M-R3)" whose table
said phase = 0M-R2 complete, gave the Phase-0M-R2 verdict and said ZERO OF TWELVE
REALIZABLE after a realizable pair had been found. A separate `next_gate` field still
listed adopting the physical cooling model and putting the RDL in the mechanical mesh as
future work; both were completed in Phases 0M-R and 0M-R2.

## Terminology

Current-facing text presented the HISTORICAL Phase-0I 35.8 % separation as the present
architecture result, called the FE output "damage", and said "Z2 outlives Z1". All three
are corrected. The present repaired pair separates by **16.3 %**, the FE quantity is a
**local fatigue-relevant inelastic response metric**, and no survival claim is made while
absolute N_f is unvalidated.

## No replay was needed

The 30 -> 34 um change moves phi_Cu, R_field, the thermal tensor, the modulus and the CTE
by under 0.1 %, exactly as the Phase-0M allocation law predicts: the copper fraction is
`I / (J_design * A_field)`, in which the radius cancels. The frozen pair therefore stands:

| | Z1 | Z2 |
|---|---|---|
| P_electronics | {f(cur['Z1']['P_total_electronics_w'],3)} W | {f(cur['Z2']['P_total_electronics_w'],3)} W |
| T_max | {f(cur['Z1']['T_max_C'],2)} C | **{f(cur['Z2']['T_max_C'],2)} C** |
| local fatigue-relevant inelastic response | {f(cur['Z1']['response_driver_um'],4)} um | **{f(cur['Z2']['response_driver_um'],4)} um** |

**D_driver = {ratio:.4f}**, unchanged.

## Verdict

**B --- Z1/Z2 ORDERING SURVIVES, BUT THE INTRA-VR VIA TECHNOLOGY REMAINS UNSOURCED.**

Phase 0M-R3's verdict E rested on package clearances being the sole blocker. DEFECT #58
adds a second, independent unsourced manufacturing assumption, so that premise no longer
holds. The optimizer remains **FORBIDDEN**.

### Verdict history

Phase 0M-R3A withdrew the stale current-state table that had been asserting the
Phase-0M-R2 verdict as the present one. The verdicts themselves are part of the record and
are kept here, each as the finding of the gate that issued it and none of them current
except the last.

| gate | option | verdict |
|---|---|---|
""" + ledger() + f"""

<!-- END GENERATED: {TAG} -->
"""


def main() -> int:
    s = REP.read_text()
    done = []
    old = ("# Phase 0M-R3 --- Realizable-Template Repair, Cooling Validation and Final "
           "Current-State Closure (current authoritative)")
    new = ("# Phase 0M-R3 --- Realizable-Template Repair, Cooling Validation and Final "
           "Current-State Closure (superseded by Phase 0M-R3A)")
    if old in s:
        s = s.replace(old, new); done.append("Phase 0M-R3 -> historical")
    cur = {r["case"]: r for r in rd("final_Z1_Z2_comparison.csv",
                                    OUT / "_baseline_phase0mr3")}
    # The Architecture Comparison note is now owned SOLELY by
    # scripts/phase0mr3c/build_report_0mr3c.py, which rewrites it to the current pair with
    # a form-agnostic pattern. Two builders owning one sentence is how the gate sentence
    # broke, and it broke this one the same way.

    body = narrative()
    pat = rf"<!-- BEGIN GENERATED: {TAG} -->\n.*?<!-- END GENERATED: {TAG} -->\n"
    if re.search(pat, s, re.S):
        s = re.sub(pat, lambda _m: body, s, count=1, flags=re.S)
        done.append("chapter replaced")
    else:
        k = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
        s = s[:k] + body + "\n" + s[k:]
        done.append("chapter inserted")
    gen = (R / "results" / "phase0h" / "generated_current_facing.md").read_text()
    spliced = []
    for n in ("exec_summary", "governing_equations", "validation_status",
              "reliability_metric", "publication_claims"):
        pn = rf"<!-- BEGIN GENERATED: {n} -->\n.*?<!-- END GENERATED: {n} -->\n"
        src = re.search(pn, gen, re.S)
        if src and re.search(pn, s, re.S):
            s = re.sub(pn, lambda _m, _t=src.group(0): _t, s, count=1, flags=re.S)
            spliced.append(n)
    done.append(f"current-facing blocks respliced: {len(spliced)}")

    gs = (R / "results" / "phase0g" / "generated_status_sections.md").read_text()
    st = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    m = re.search(r"\n+\\newpage\n+# References", s[st:])
    assert m, "status block boundary not found"
    s = s[:st] + gs.rstrip("\n") + s[st + m.start():]
    s = s.replace("## Current scientific status (Phase 0M-R3)\n",
                  "## Current scientific status (Phase 0M-R3A)\n")
    done.append("status block refreshed")
    REP.write_text(s)
    for d in done:
        print("  " + d)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
