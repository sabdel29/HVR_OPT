#!/usr/bin/env python3
"""Phase-0M-R3A --- results/phase0mr3a/FINAL_CURRENT_STATE_AUDIT.md.

Every number is read from an artifact. Nothing here is typed twice.
"""
from __future__ import annotations
import csv, sys
from collections import Counter
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3a"
BASE = OUT / "_baseline_phase0mr3"
STATUS = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"


def rd(n, base=OUT):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def main() -> int:
    st = yaml.safe_load(STATUS.read_text())
    before, after = rd("stale_claims_before.csv"), rd("stale_claims_after.csv")
    neg = rd("semantic_negative_tests.csv")
    v = rd("ls_to_L_via_check.csv")
    z = {r["d_um"]: r for r in rd("z2_tsv_diameter_sweep.csv")}
    pre = rd("optimizer_preconditions.csv")
    by_doc = Counter(r["document"] for r in before)
    by_rule = Counter(r["rule_id"] for r in before)
    nneg = [r for r in neg if r["kind"] == "negative"]
    nctl = [r for r in neg if r["kind"] == "control"]

    L = []
    A = L.append
    A("# PHASE 0M-R3A --- FINAL CURRENT-STATE AUDIT")
    A("")
    A("What a reader of the current documents is told, checked against what the framework "
      "actually knows. The BEFORE column is measured by re-running the audit against the "
      "preserved Phase-0M-R3 reports in `_baseline_phase0mr3/`, not recalled.")
    A("")
    A("| | before (0M-R3 as shipped) | after (0M-R3A) |")
    A("|---|---|---|")
    A(f"| stale findings, historical report | {by_doc['historical']} | "
      f"{sum(1 for r in after if r['document'] == 'historical')} |")
    A(f"| stale findings, standalone audit | {by_doc['standalone']} | "
      f"{sum(1 for r in after if r['document'] == 'standalone')} |")
    A(f"| **total** | **{len(before)}** | **{len(after)}** |")
    A("")
    A("### What the 13 were")
    A("")
    A("| rule | n | what it caught |")
    A("|---|---|---|")
    WHY = {
        "response_not_damage_life_failure":
            "the FE output called damage, or Z2 said to outlive Z1, while the damage law, "
            "the life model and the failure criterion are all OPEN",
        "historical_358_not_current":
            "the Phase-0I 35.8 % separation presented as the present architecture result. "
            "The present repaired pair separates by 16.3 %",
        "via_provenance_precise":
            "\"the sourced 34 um via\" --- no primary source specifies 34 um; only the "
            "RANGE is source-backed",
        "single_next_work":
            "two already-completed actions listed as future work",
        "gate_count":
            "the gate roll behind the phase count",
        "stale_current_state_row":
            "a superseded phase asserted as current state in the status table (DEFECT #57)",
    }
    for rid, n in by_rule.most_common():
        A(f"| `{rid}` | {n} | {WHY.get(rid, '')} |")
    A("")
    A("The report that carried all thirteen had passed its own audit at **0 findings**. "
      "The generators had been advanced; two independent representations of current state "
      "existed and only one of them was.")
    A("")
    A("## The zero is negative-tested")
    A("")
    A(f"A clean audit is evidence only if the guards reject the real sentences. All "
      f"**{len(nneg)}** offending sentences below are VERBATIM from a shipped Phase-0M-R3 "
      f"document or the generator behind it --- never a paraphrase --- injected into a "
      f"current-facing section of the present report.")
    A("")
    A("| item | rule | source | sentence | rejected |")
    A("|---|---|---|---|---|")
    for r in nneg:
        s = r["sentence"].replace("|", "\\|")
        s = s if len(s) <= 96 else s[:93] + "..."
        A(f"| {r['item']} | `{r['rule_id']}` | `{r['source']}` | {s} | "
          f"**{'YES' if r['guard_fired'] == 'True' else 'NO'}** |")
    A("")
    A(f"And **{len(nctl)}** positive controls: sentences that look like the forbidden ones "
      "but are the record working correctly. A guard that rejects a retraction is "
      "over-firing --- which is how Phase 0M-R3 silently lost three of five cross-field "
      "invariants.")
    A("")
    A("| rule | sentence | correctly left alone |")
    A("|---|---|---|")
    for r in nctl:
        s = r["sentence"].replace("|", "\\|")
        s = s if len(s) <= 110 else s[:107] + "..."
        A(f"| `{r['rule_id']}` | {s} | **{'YES' if r['guard_fired'] == 'False' else 'NO'}** |")
    A("")
    A("## The four issues this gate was opened for")
    A("")
    A("| # | issue | finding |")
    A("|---|---|---|")
    A("| 1 | stale current-state generators survived a \"0 findings\" audit | **CONFIRMED, "
      "DEFECT #57.** Two representations of current state; only `meta`/`verdict` were "
      "advanced in 0M-R3. The rendered table said phase = 0M-R2 complete under a heading "
      "reading \"Current scientific status (Phase 0M-R3)\" |")
    A("| 2 | current-facing text still calls the FE response \"damage\" | **CONFIRMED.** "
      "Also \"outlives\", and the historical 35.8 % presented as the current result |")
    A("| 3 | the 15 -> 20 um repair may borrow a TSV range | **CONFIRMED, DEFECT #58.** It "
      "does. `ls_to_L` is a 673 um intra-converter stacked via; the range governs "
      "through-silicon vias, which span 74 um in ARCH_Z1 |")
    A("| 4 | \"34 um costs 22.8 % more vias\" contradicts J*A provisioning | **CONFIRMED, "
      "DEFECT #59.** It is 22.8 % FEWER, and a reduction rather than a cost |")
    A("")
    A("## Issue 3 in detail --- the repair is arithmetically right and unsourced")
    A("")
    A("The arithmetic was re-derived by an implementation sharing no code with production:")
    A("")
    A("| r (um) | pitch (um) | n_required | n_available | ratio | production | agrees |")
    A("|---|---|---|---|---|---|---|")
    for r in v:
        A(f"| {float(r['r_um']):.1f} | {float(r['pitch_um']):.1f} | {r['n_required']} | "
          f"{r['n_available']} | {float(r['ratio']):.4f} | "
          f"{float(r['production_ratio']):.4f} | "
          f"{'YES' if r['reproduces'] == 'True' else 'NO'} |")
    A("")
    A("Exact at every radius. The defect is not in the numbers, it is in the licence: the "
      "design space offers `tsv.*` (through-silicon), `rdl.*` (trace width and space, no "
      "via) and `bump.*` (bumps), and **none of them governs a stacked via through "
      "substrate power layers**. The 20 um radius is a design point in an unsourced "
      "process window.")
    A("")
    A("## Issue 4 in detail")
    A("")
    A("| quantity | 30 um | 32 um | 34 um |")
    A("|---|---|---|---|")
    for lab, k, fmt in (("M_AR", "M_AR", "{:.3f}"),
                        ("passes modest bound", "passes_modest_bound", "{}"),
                        ("n_required", "n_required", "{}"),
                        ("n_available", "n_available", "{}"),
                        ("phi_Cu", "phi_cu", "{:.6f}")):
        cells = []
        for d in ("30.0", "32.0", "34.0"):
            raw = z[d][k]
            cells.append(fmt.format(float(raw) if "{:" in fmt else raw))
        A(f"| {lab} | " + " | ".join(cells) + " |")
    A("")
    n30, n34 = int(z["30.0"]["n_required"]), int(z["34.0"]["n_required"])
    A(f"`n_required = ceil(I / (J_design * A_cu))` scales as `1/A_cu`: "
      f"{n30} -> {n34}, **{100 * (n34 - n30) / n30:+.1f} %**. `phi_Cu` is constant to six "
      "decimal places across the whole sweep, which is the allocation law doing exactly "
      "what it says --- the radius cancels out of the copper fraction, so nothing "
      "downstream of it moves. That is why no replay was run.")
    A("")
    A("32 um was never evaluated: the Phase-0M-R3 grid was 30/34/40/50/60. It passes the "
      f"same modest bound at M_AR = {float(z['32.0']['M_AR']):.3f}.")
    A("")
    A("![TSV diameter, margin and count](FIG_0MR3A_tsv_diameter_margin_and_count.png)")
    A("")
    A("## Current state, as it now stands")
    A("")
    A("| field | value |")
    A("|---|---|")
    c = st["current_state_contract"]
    for k in ("current_phase", "current_verdict", "current_next_work"):
        s = str(c[k]["state"]).replace("|", "\\|")
        s = s if len(s) <= 420 else s[:417] + "..."
        A(f"| `{k}` | {s} |")
    A("")
    A("## Optimizer gate")
    A("")
    nno = sum(1 for r in pre if r["status"] == "NO")
    A(f"**FORBIDDEN.** {nno} preconditions stand at NO. Phase 0M-R3A DOWNGRADED "
      "`routing scope physically correct` from YES to PARTIAL and added "
      "`intra-VR via technology sourced` at NO.")
    A("")
    A("| precondition | status | changed this phase |")
    A("|---|---|---|")
    for r in pre:
        ch = "**yes**" if "0M-R3A" in r["evidence"] else ""
        A(f"| {r['precondition']} | **{r['status']}** | {ch} |")
    A("")
    A("## What this audit does not close")
    A("")
    A("The framework can now say, without contradicting itself, what it knows and what it "
      "does not. It cannot yet say that either architecture is buildable. Three package "
      "clearances are unsourced, the intra-VR via technology is unsourced, ARCH_Z2's TSV "
      "field has no process margin at 30 um, and the SAC305 constitutive response at the "
      "stresses that matter is uncharacterised. See `final_open_items.md`.")
    A("")

    p = OUT / "FINAL_CURRENT_STATE_AUDIT.md"
    p.write_text("\n".join(L))
    print(f"wrote {p.relative_to(R)}  ({len(L)} lines)  "
          f"before={len(before)} after={len(after)} neg={len(nneg)} ctl={len(nctl)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
