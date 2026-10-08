#!/usr/bin/env python3
"""Phase-0M-R3C Section 13 --- the report chapter, and demote its predecessor."""
from __future__ import annotations
import csv, re, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3c"
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
TAG = "phase0mr3c_narrative"
HIST_D = 1.1943


def rd(n):
    p = OUT / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def narrative() -> str:
    etm = {r["case"]: r for r in rd("final_etm_replay.csv")}
    feas = rd("routing_feasibility.csv")
    fz = yaml.safe_load((R / "configs/phase0mr3c/frozen_pair_Z1.yaml").read_text())
    sel = {r["net"]: r for r in feas
           if r["candidate"] == "repartition_C1" and r["pitch_um"] == "150.0"}
    bas = {r["net"]: r for r in feas
           if r["candidate"] == "baseline_T1" and r["pitch_um"] == "150.0"}
    z1, z2 = etm["Z1"], etm["Z2"]
    d = float(z1["response_driver_um"]) / float(z2["response_driver_um"])
    tbl = "".join(
        f"| `{n}` | {float(bas[n]['dielectric_depth_um']):.0f} um | "
        f"{float(bas[n]['AR_worst']):.2f} | {float(sel[n]['dielectric_depth_um']):.0f} um | "
        f"**{float(sel[n]['AR_worst']):.2f}** | {sel[n]['n_required_framework']}/"
        f"{sel[n]['n_available']} |\n" for n in ("ls_to_L", "hs_to_ls", "hs_to_cf"))

    return f"""<!-- BEGIN GENERATED: {TAG} -->

\\newpage

# Phase 0M-R3C --- Component Repartitioning, Physical Realizability and Paper Freeze (current authoritative)

The last planned technical gate. It asked one question: can the existing converter
components be repartitioned so the 20.408 A switch node is physically credible under the
best source-backed substrate-interconnect rules, without inventing devices or process?

## The via count was wrong again, in the opposite direction --- DEFECT #64

Phase 0M-R3B counted three MATERIAL layers across the 120 um gap and concluded three
stacked microvia levels. `RDL_UM = 10 um` is an interlayer REDISTRIBUTION layer ---
patterned copper, which is exactly what a laser microvia lands on. A via level is needed
per DIELECTRIC region between conductor planes, not per material layer:

| # | z | structure | via? |
|---|---|---|---|
| 0 | 1301 um | gan_ls terminal face | no |
| 1 | 1301-1311 | interlayer RDL --- CONDUCTOR PLANE, a capture land | no |
| 2 | 1311-1411 | flying-capacitor layer, no conductor plane inside | **yes, one level** |
| 3 | 1411-1421 | interlayer RDL --- CONDUCTOR PLANE | no |
| 4 | 1421 um | inductor terminal face | no |

**One via level, not three.** Phase 0M-R3B's finding that zero configurations satisfy both
sourced bounds is **withdrawn**; the baseline already passes at a sourced pitch. The
recount also relocates the real problem: the binding net was never `ls_to_L` but
`hs_to_cf`, which in the Phase-0M-R3 tier order crosses the whole 606 um low-side GaN tier
in a single via at aspect ratio 5.05.

## A permutation fixes it

`{fz['partition']['template']}`, bottom to top: **{' / '.join(fz['partition']['tiers_bottom_to_top'])}**.
{fz['partition']['what_moved'].capitalize()}.

| net | baseline depth | baseline AR | repartitioned depth | repartitioned AR | n_req/n_avail |
|---|---|---|---|---|---|
{tbl}
Worst aspect ratio falls from **5.05 to 0.83**. This is a PERMUTATION:
{fz['partition']['invariants']}. It keeps both ends the June-2026 source fixes --- the
high-side GaN flip-chipped at the bottom substrate, the inductors in the top layer near
the POLs. Of 144 partitions that satisfy the per-tier area budget, 8 keep those ends, and
this is the best of them.

## Provisioning is not qualification

`n_required` above is a CONSERVATIVE DESIGN-SIDE ALLOCATION at J_design = 1e8 A/m2. No
sourced current allowable exists for this microvia technology, so it is never a statement
about what manufacturing requires. Two facts from primary sources obtained this phase
sharpen it: the **EPC2057 datasheet** shows four solder bars on a 1500 x 1200 um die, so
the switch-node land is at most a quarter of the die; and the `ls_to_L` edge is an
**aggregate over K = 3 phases**, so per device the switch node carries 6.803 A, inside the
part's 9.6 A continuous rating.

## One final ETM replay

Both configurations were frozen before solving. One solve each, identical settings, no
sweep, with the corrected physical spans enabled.

| | Z1 | Z2 |
|---|---|---|
| P_electronics | {float(z1['P_total_electronics_w']):.3f} W | {float(z2['P_total_electronics_w']):.3f} W |
| T_max | {float(z1['T_max_C']):.2f} C | **{float(z2['T_max_C']):.2f} C** |
| T_mean | {float(z1['T_mean_C']):.2f} C | {float(z2['T_mean_C']):.2f} C |
| die warpage P-V | {float(z1['die_warpage_pv_um']):.3f} um | {float(z2['die_warpage_pv_um']):.3f} um |
| local fatigue-relevant inelastic response | {float(z1['response_driver_um']):.4f} um | **{float(z2['response_driver_um']):.4f} um** |

**D_driver_final = {d:.4f}** against the historical {HIST_D:.4f}: **{100*(d-HIST_D)/HIST_D:+.2f} %**.
The entire interconnect correction --- re-derived topology, repartitioned stack, corrected
spans, source-bounded via geometry --- moves the deciding ratio by four hundredths of a
percent. ARCH_Z2 remains {float(z2['T_max_C'])-float(z1['T_max_C']):+.2f} K hotter while
carrying 16.3 % less response.

## Verdict

**B --- A PROCESS-CONDITIONAL REPARTITION EXISTS, AND THE FINAL Z1/Z2 RESPONSE ORDERING
SURVIVES.**

Neither architecture is PROVEN_REALIZABLE. Geometry closes; the microvia current
allowable, the capture-pad diameter, a vendor design rule and two package clearances
remain OPEN. The licensed verdict is **GEOMETRICALLY_REALIZABLE / PROCESS-CONDITIONAL**.

G2 remains NOT TESTED and the optimizer remains **FORBIDDEN**. No fundamental model
contradiction was found, so framework development stops here and the next action is
manuscript freeze: see `results/PAPER_FREEZE_DECISION.md`.

<!-- END GENERATED: {TAG} -->
"""


def architecture_comparison_note() -> tuple[str, str]:
    """The Architecture Comparison note is a once-only insert from Phase 0M-R2 that each
    later phase re-marks from outside. It must carry the CURRENT pair."""
    etm = {r["case"]: r for r in rd("final_etm_replay.csv")}
    z1, z2 = etm["Z1"], etm["Z2"]
    new = (f"**Current position (Phase 0M-R3C).** Under the physical cooler the "
           f"architectures do separate in temperature. On the current frozen repartitioned "
           f"pair ARCH_Z2 runs {float(z2['T_max_C']):.2f} C against ARCH_Z1's "
           f"{float(z1['T_max_C']):.2f} C, so ARCH_Z2 is the hotter of the two principal "
           f"candidates and still the better of them on the local fatigue-relevant "
           f"inelastic RESPONSE ({float(z2['response_driver_um']):.4f} um against "
           f"{float(z1['response_driver_um']):.4f} um). ARCH_Z4's 98.83 C is the "
           f"Phase-0M-R2 figure, for a power-die construction that remains unsourced. The "
           f"tables below this note are the Phase-0I/0M record and are retained as such.")
    return new


def main() -> int:
    s = REP.read_text()
    # re-mark the Architecture Comparison note to the current pair, from outside
    import re as _re
    _pat = _re.compile(r"\*\*Current position \(Phase [^)]*\)\.\*\*[^\n]*")
    _new = architecture_comparison_note()
    if _pat.search(s) and _pat.search(s).group(0) != _new:
        s = _pat.sub(lambda _m: _new, s, count=1)
        print("  Architecture Comparison note -> current pair")
    done = []
    old = ("# Phase 0M-R3B --- Substrate-Via Technology, Package Rules and Process Margin "
           "(current authoritative)")
    new = ("# Phase 0M-R3B --- Substrate-Via Technology, Package Rules and Process Margin "
           "(superseded by Phase 0M-R3C)")
    if old in s:
        s = s.replace(old, new); done.append("Phase 0M-R3B -> historical")
    body = narrative()
    pat = rf"<!-- BEGIN GENERATED: {TAG} -->\n.*?<!-- END GENERATED: {TAG} -->\n"
    if re.search(pat, s, re.S):
        s = re.sub(pat, lambda _m: body, s, count=1, flags=re.S); done.append("replaced")
    else:
        k = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
        s = s[:k] + body + "\n" + s[k:]; done.append("inserted")
    s = s.replace("## Current scientific status (Phase 0M-R3B)\n",
                  "## Current scientific status (Phase 0M-R3C)\n")
    REP.write_text(s)
    for x in done:
        print("  " + x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
