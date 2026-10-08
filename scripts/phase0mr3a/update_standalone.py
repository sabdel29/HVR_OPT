#!/usr/bin/env python3
"""Phase-0M-R3A Section 12 --- bring the STANDALONE current-state audit to 0M-R3A.

The Phase-0M-R builder is left untouched and its artifacts byte-identical. This script
runs it, then applies the 0M-R3A delta as a list of ASSERTED substitutions: every one of
them must match exactly once, so a drifting upstream sentence fails the build instead of
silently leaving stale text in a document whose whole purpose is to be current.
"""
from __future__ import annotations
import csv, re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
PY = sys.executable
OUT = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
R3A = R / "results" / "phase0mr3a"
DATE = "2026-09-21"

GATES = ("0B, 0C, 0D, 0D-R, 0E, 0F, 0G, 0H, 0I, 0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R, "
         "0M, 0M-R, 0M-R2, 0M-R3, 0M-R3A")


def rd(n, base=R3A):
    return list(csv.DictReader((Path(base) / n).open()))


def new_1_2(z, v) -> str:
    """Section 1.2 for this phase, replacing the 0M-R3 one (which moves down to 1.3)."""
    d30, d32, d34 = z["30.0"], z["32.0"], z["34.0"]
    drop = 100 * (int(d34["n_required"]) - int(d30["n_required"])) / int(d30["n_required"])
    ex = sum(1 for r in v if abs(float(r["ratio"]) - float(r["production_ratio"])) < 5e-5)
    return "\n".join([
        "## 1.2 What Phase 0M-R3A changed",
        "",
        "A narrow closure gate on four issues left open by Phase 0M-R3. Three were "
        "confirmed as defects; one claim was found to have the wrong sign.",
        "",
        "| question | answer |",
        "|---|---|",
        "| Was the 15 -> 20 um routing repair source-backed? | **No --- DEFECT #58.** The "
        "range quoted to license it, `tsv.radius_m`, governs THROUGH-SILICON vias. `ls_to_L` "
        "is a **673 um** stacked via between embedded-component layers inside the converter "
        "cell, where the Z1 TSV field spans 74 um. The design space holds `tsv.*`, `rdl.*` "
        "and `bump.*` and has no entry for this structure. The repair is a design point in "
        "an unsourced process window |",
        "| Is the repair arithmetic right? | **Yes.** An independent implementation sharing "
        f"no code with production reproduces the routing ratio exactly at {ex} of {len(v)} "
        "radii --- 1.2360 at r = 15 um, 0.9344 at r = 20 um. The numbers were right; only "
        "their provenance was not |",
        "| Does a 34 um TSV cost 22.8 % more vias? | **No --- DEFECT #59, the sign was "
        f"backwards.** n_required scales as 1/A_cu, so 30 -> 34 um gives {drop:+.1f} %: "
        f"{d30['n_required']} -> {d34['n_required']}. It is a reduction, not a cost. The "
        f"sweep also skipped **32 um**, which passes the same bound at M_AR = "
        f"{float(d32['M_AR']):.3f} |",
        "| Was the current-state table current? | **No --- DEFECT #57.** A section headed "
        "\"Current scientific status (Phase 0M-R3)\" carried a table saying phase = 0M-R2 "
        "complete, the 0M-R2 verdict, ZERO OF TWELVE REALIZABLE, and two already-completed "
        "actions listed as future work |",
        "",
        "Nothing was re-solved. The 30 -> 34 um change moves every E/T/M property by under "
        "0.1 %, because under minimum-capability provisioning the copper fraction is "
        "`I / (J_design * A_field)`, in which the radius cancels.",
        "",
        "**Verdict B --- the Z1/Z2 ordering survives, but the intra-VR via technology "
        "remains unsourced.** Phase 0M-R3's verdict rested on package clearances being the "
        "sole remaining blocker. DEFECT #58 adds a second, independent unsourced "
        "manufacturing assumption, so that premise no longer holds.",
    ])


# (description, old, new). Every old must occur exactly once.
def edits(z, v) -> list[tuple[str, str, str]]:
    d32, d34 = z["32.0"], z["34.0"]
    return [
        ("subtitle",
         "as it exists after Phase 0M-R3\"",
         "as it exists after Phase 0M-R3A\""),
        ("front-matter date", 'date: "2026-09-17"', f'date: "{DATE}"'),
        ("report generated", "| Report generated | 2026-09-19 |",
         f"| Report generated | {DATE} |"),
        ("phase completed", "| Phase completed | 0M-R3, 2026-09-19 |",
         f"| Phase completed | 0M-R3A, {DATE} |"),
        ("gate sentence",
         "**Method.** Twenty sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, 0F, 0G, "
         "0H, 0I, 0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R, 0M, 0M-R, 0M-R2, 0M-R3), each",
         f"**Method.** Twenty-one sequential falsification gates ({GATES}), each"),
        ("demote 0M-R3 summary to 1.3",
         "## 1.2 What Phase 0M-R3 changed",
         new_1_2(z, v) + "\n\n\\newpage\n\n## 1.3 Superseded Phase-0M-R3 summary"),
        ("demote 0M-R2 summary to 1.4",
         "## 1.3 Superseded Phase-0M-R2 summary",
         "## 1.4 Superseded Phase-0M-R2 summary"),
        ("0M-R3 repair row: provenance withdrawn",
         "| What repair was needed? | **One.** The intra-VR via radius 15 -> 20 um at the "
         "framework's own legal pitch, inside the sourced range.",
         "| What repair was needed? | **One.** The intra-VR via radius 15 -> 20 um at the "
         "framework's own legal pitch. *(Phase 0M-R3A withdrew \"inside the sourced range\": "
         "that range governs through-silicon vias, DEFECT #58.)*"),
        ("0M-R3 TSV row: sign corrected",
         "34 um restores 1.089 at 22.8 % more vias and <= 0.02 % change in every E/T/M "
         "property |",
         f"34 um restores 1.089. *(Phase 0M-R3A: that is 22.8 % FEWER vias, not more, and "
         f"32 um already passes at M_AR = {float(d32['M_AR']):.3f}; DEFECT #59.)* Every "
         f"E/T/M property moves by <= 0.02 % |"),
        ("section 21.1: response, not damage",
         "* **Z2 accumulates less solder-fatigue damage than Z1**, under every admitted "
         "constitutive model, every admitted life law, every profile and all three response "
         "metrics. The ordering originates upstream of the solder model.",
         "* **Z2 carries a lower local fatigue-relevant inelastic response than Z1**, under "
         "every admitted constitutive model, every admitted life law, every profile and all "
         "three response metrics. The ordering originates upstream of the solder model. It "
         "is a RESPONSE ordering: calling it less damage would presume a sourced damage "
         "law, and that is OPEN."),
        ("precondition table header",
         "| precondition | status after Phase 0M-R3 | evidence |",
         "| precondition | status after Phase 0M-R3A | evidence |"),
        ("precondition commentary",
         "Phase 0M-R2 DOWNGRADED the cooling precondition from YES to PARTIAL",
         "Phase 0M-R3A DOWNGRADED the routing precondition from YES to PARTIAL, because the "
         "repair that makes both candidates pass sits in an unsourced via process window, "
         "and added a new precondition for whether that via technology is sourced at all. "
         "Phase 0M-R2 had DOWNGRADED the cooling precondition from YES to PARTIAL"),
    ]


def main() -> int:
    src = (R / "scripts" / "phase0mr" / "build_standalone.py")
    # The 0M-R builder reads the 0M-R3 precondition CSV. Point it at the 0M-R3A one for
    # the duration of this build without editing either file.
    p3a_c = R / "results" / "phase0mr3c" / "optimizer_preconditions.csv"
    p3a_b = p3a_c if p3a_c.is_file() else R / "results" / "phase0mr3b" / "optimizer_preconditions.csv"
    p3, p3a = (R / "results" / "phase0mr3" / "optimizer_preconditions.csv",
               p3a_b if p3a_b.is_file() else R3A / "optimizer_preconditions.csv")
    keep = p3.read_bytes()
    try:
        p3.write_bytes(p3a.read_bytes())
        r = subprocess.run([PY, str(src)], cwd=R, capture_output=True, text=True)
    finally:
        p3.write_bytes(keep)
    assert p3.read_bytes() == keep, "0M-R3 artifact not restored"
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:]); return 1

    z = {x["d_um"]: x for x in rd("z2_tsv_diameter_sweep.csv")}
    s = OUT.read_text()
    for desc, old, new in edits(z, rd("ls_to_L_via_check.csv")):
        n = s.count(old)
        if n != 1:
            print(f"  FAIL  {desc}: matched {n} times, expected 1"); return 1
        s = s.replace(old, new, 1)
        print(f"  ok    {desc}")
    OUT.write_text(s)
    print(f"\n{OUT.name}: {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
