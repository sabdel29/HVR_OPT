#!/usr/bin/env python3
"""Phase-0G Sec.17 -- generate the report's current-status sections from the single source
of truth.

DEFECT #29: the report stated the same claim in five places -- Executive Summary, Positive
Results, Negative Results, the uncertainty ladder, Next Steps -- and each phase updated only
some of them. Every individual sentence was true when written, so regex assertions could not
catch the resulting contradictions. The fix has to be structural, not another assertion:
these sections are now DERIVED from results/CURRENT_SCIENTIFIC_STATUS.yaml, so a claim can
only change in one place.

Emits results/phase0g/generated_status_sections.md, which build_report.py splices into the
full technical report. test_status_sections.py then re-derives the text and compares.
"""
from __future__ import annotations
import sys, textwrap
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
SRC = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
OUT = R / "results" / "phase0g" / "generated_status_sections.md"
OUT_CF = R / "results" / "phase0h" / "generated_current_facing.md"


def flow(text: str) -> str:
    """YAML block scalars arrive with hard-wrapped newlines; make them one paragraph."""
    return " ".join(str(text).split())


def wrap(text: str, width: int = 96, indent: str = "") -> str:
    return textwrap.fill(flow(text), width=width, initial_indent=indent,
                         subsequent_indent=indent)


def emit(d: dict) -> str:
    L: list[str] = []
    A = L.append
    m, v = d["meta"], d["verdict"]

    A("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml -- DO NOT EDIT BY HAND. -->")
    A("<!-- Regenerate with scripts/phase0g/generate_status_sections.py (DEFECT #29). -->")
    A("")
    A(f"## Current scientific status (Phase {m['current_phase']})")
    A("")
    # DEFECT #53. The authoritative contract goes FIRST, so a reader sees the state of every
    # subsystem before any narrative about it.
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase0mr"))
    from state_contract import as_markdown as _contract_md      # noqa: E402
    A(_contract_md())
    A("")
    A(wrap(f"**Phase {m['current_phase']} — {m['phase_name']}.** "
           f"This section supersedes the corresponding statements of Phase "
           f"{m['supersedes_verdict_of']}."))
    A("")
    # '0I-R' -> 'phase0ir'. Without stripping the hyphen this silently fell back to the
    # Phase-0G verdict, so the generated section showed the wrong verdict from Phase 0I-R on.
    _k = "phase" + m["current_phase"].lower().replace("-", "")
    cur = v.get(_k) or v["phase0g"]
    assert v.get(_k), f"no verdict recorded for current phase {m['current_phase']} (key {_k})"
    A(f"### Verdict — {cur}")
    A("")
    if v.get("phase0g") and cur != v["phase0g"]:
        A(wrap(f"*Phase 0G verdict, still standing and refined by this phase:* "
               f"{v['phase0g']}."))
        A("")
    # DEFECT #53. `basis` was written at Phase 0H and never phase-scoped, so every later
    # phase printed six Phase-0H bullets under its own verdict heading. It is now scoped the
    # same way `rejected_verdicts_` already was, and the unscoped key is the fallback only
    # for the phase that wrote it.
    for b in (v.get("basis_" + _k) or v["basis"]):
        A(f"- {flow(b)}")
    A("")
    A(wrap(f"**What this is not.** {flow(v['what_this_is_not'])}"))
    A("")
    if v.get("g2_status"):
        A(wrap(f"**Falsification gate G2: {v['g2_status']}.** {flow(v.get('g2_note',''))}"))
        A("")

    A("#### Verdicts considered and rejected")
    A("")
    A("| candidate verdict | why rejected |")
    A("|---|---|")
    for k, why in (v.get("rejected_verdicts_" + _k) or v["rejected_verdicts"]).items():
        A(f"| {k.replace('_', ' ').title()} | {flow(why)} |")
    A("")

    g = v.get("optimiser_gate")
    if g:
        A("#### Optimizer gate")
        A("")
        A("| condition | met | detail |")
        A("|---|---|---|")
        A(f"| 1 — assembly-state response survives calibrated board and thermal-boundary "
          f"uncertainty | **{g['condition_1_assembly_response_survives']}** | "
          f"{flow(g['condition_1_detail'])} |")
        A(f"| 2 — a criterion or user-set ε can actually alter the feasible design set | "
          f"**{str(g['condition_2_criterion_or_epsilon_alters_feasible_set']).upper()}** | "
          f"{flow(g['condition_2_detail'])} |")
        A("")
        A(wrap(f"**{flow(g['conclusion'])}**"))
        A("")

    A("### Claims by status")
    A("")
    A("Status vocabulary: **PROVEN** — numerically converged *and* cross-checked against an "
      "independent solver. **SUPPORTED** — converged in one solver, no independent "
      "cross-check. **CONDITIONAL** — true only under a named open input. **SUPERSEDED** — "
      "asserted in an earlier phase and no longer current.")
    A("")
    for key, title in (("proven", "PROVEN"), ("supported", "SUPPORTED"),
                       ("conditional", "CONDITIONAL")):
        items = d["claims"].get(key) or []
        A(f"#### {title} ({len(items)})")
        A("")
        if not items:
            A("*(none)*"); A(""); continue
        for c in items:
            A(f"- **{c['id']}** (Phase {c.get('phase', '?')}) — {flow(c['statement'])}")
            if c.get("condition"):
                A(f"    - *Condition:* {flow(c['condition'])}")
            if c.get("quantitative"):
                A(f"    - *Quantitative:* {flow(c['quantitative'])}")
            if c.get("corroboration"):
                A(f"    - *Independent corroboration:* {flow(c['corroboration'])}")
            if c.get("evidence"):
                A(f"    - *Evidence:* `{flow(c['evidence'])}`")
        A("")

    sup = d["claims"].get("superseded") or []
    A(f"#### SUPERSEDED ({len(sup)})")
    A("")
    A("| claim | asserted in | superseded by |")
    A("|---|---|---|")
    for c in sup:
        A(f"| **{c['id']}** — {flow(c['statement'])} | {c.get('phases_asserted', '?')} | "
          f"{flow(c['superseded_by'])} |")
    A("")

    A("### Open items")
    A("")
    for o in d["open"]:
        A(f"- **{o['id']}** — {flow(o['what'])}")
        if o.get("why_it_matters"):
            A(f"    - *Why it matters:* {flow(o['why_it_matters'])}")
        if o.get("status_change"):
            A(f"    - *Change in this phase:* {flow(o['status_change'])}")
        if o.get("evidence"):
            A(f"    - *Evidence:* `{flow(o['evidence'])}`")
    A("")

    A("### Not tested")
    A("")
    for n in d["not_tested"]:
        A(f"- **{n['id']}** — {flow(n['what'])}")
        if n.get("why"):
            A(f"    - *Why:* {flow(n['why'])}")
        if n.get("consequence"):
            A(f"    - *Consequence:* {flow(n['consequence'])}")
    A("")

    A("### Defects logged in this phase")
    A("")
    for x in d.get("phase0g_defects", []):
        A(f"#### DEFECT #{x['id']} — {x['title']}")
        A("")
        A(wrap(flow(x["detail"])))
        A("")
        if x.get("detected_by"):
            A(f"- *Detected by:* {flow(x['detected_by'])}")
        if x.get("impact"):
            A(f"- *Impact:* {flow(x['impact'])}")
        A(f"- *Fix:* {flow(x['fix'])}")
        A(f"- *Status:* **{x['status']}**")
        if x.get("lesson"):
            A(f"- *Lesson:* {flow(x['lesson'])}")
        A("")

    ng = d["next_gate"]
    A("### Next gate")
    A("")
    A(wrap(f"**{flow(ng['id'])}.** {flow(ng['rationale'])}"))
    A("")
    if ng.get("recommended_framing"):
        A(wrap(f"**Recommended framing.** {flow(ng['recommended_framing'])}"))
        A("")
    if ng.get("contribution_claims"):
        A("The contribution then consists of:")
        A("")
        for r in ng["contribution_claims"]:
            A(f"- {flow(r)}")
        A("")
    key = ("required_to_unblock_a_constrained_optimizer" if
           "required_to_unblock_a_constrained_optimizer" in ng else "required_to_unblock")
    if ng.get(key):
        A("Required to unblock a constrained optimizer:")
        A("")
        for r in ng[key]:
            A(f"- {flow(r)}")
        A("")
    A(wrap(f"**Explicitly not next:** {flow(ng['explicitly_not_next'])}."))
    A("")
    return "\n".join(L) + "\n"


def emit_current_facing(d: dict) -> str:
    """Phase-0H Sec.1 / DEFECT #32.

    Everything the report says in the PRESENT TENSE now originates here. Before this, the
    Executive Summary, governing equations, validation status, novelty, limitations,
    publication claims and next steps were hand-written, and each phase updated only some of
    them -- so the document simultaneously called substrate thickness "win/win/win and
    survived every correction" and reported an electrical-versus-mechanical thickness
    opposition on a geometry that made the original sweep unbuildable.
    """
    cf = d["current_facing"]
    es, L = cf["executive_summary"], []
    A = L.append

    A("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml -- DO NOT EDIT BY HAND. -->")
    A("<!-- Regenerate with scripts/phase0g/generate_status_sections.py (DEFECT #32). -->")
    A("")
    A("<!-- BEGIN GENERATED: exec_summary -->")
    A("")
    A("# Executive Summary")
    A("")
    A(wrap(f"**Original hypothesis.** {flow(es['hypothesis'])}"))
    A("")
    A(wrap(f"**Answer.** {flow(es['answer'])}"))
    A("")
    A(wrap(f"**Method.** {flow(es['method'])}"))
    A("")
    A("**What survived.**")
    A("")
    for x in es["survived"]:
        A(f"* {flow(x)}")
    A("")
    A("**What failed.**")
    A("")
    for x in es["failed"]:
        A(f"* {flow(x)}")
    A("")
    A(wrap(f"**Current strongest novelty.** {flow(es['novelty'])}"))
    A("")
    A("**Current limitations.**")
    A("")
    for x in es["limitations"]:
        A(f"* {flow(x)}")
    A("")
    A(wrap(f"**Exact next work.** {flow(es['next_work'])}"))
    A("")
    A("<!-- END GENERATED: exec_summary -->")
    A("")

    A("<!-- BEGIN GENERATED: governing_equations -->")
    A("")
    A("## Governing-equation status")
    A("")
    A("| # | equation | status | note |")
    A("|---|---|---|---|")
    for i, e in enumerate(cf["governing_equations"], 1):
        note = flow(e["note"])
        if e.get("superseded_form"):
            note += f" **Superseded form:** `{flow(e['superseded_form'])}`."
        A(f"| {i} | `{flow(e['equation'])}` | **{e['status']}** | {note} |")
    syms = sorted({s for e in cf["governing_equations"] for s in e.get("symbols_required", [])})
    if syms:
        A("")
        A(wrap("Symbols required by the current forms and therefore mandatory in the symbol "
               "table: " + ", ".join(f"`{x}`" for x in syms) + "."))
    A("")

    A("<!-- END GENERATED: governing_equations -->")
    A("")
    A("<!-- BEGIN GENERATED: validation_status -->")
    A("")
    A("## Validation status")
    A("")
    A("| domain | status | validated | not validated |")
    A("|---|---|---|---|")
    for dom in ("electrical", "thermal", "mechanical"):
        v = cf["validation_status"][dom]
        A(f"| {dom} | **{v['status']}** | {flow(v['done'])} | {flow(v['not_done'])} |")
    rm = cf["validation_status"]["mechanical"].get("restraint_models")
    if rm:
        A("")
        A(wrap(f"**Restraint models.** {flow(rm)}"))
    A("")

    # ---- Phase-0I-R closure blocks, rendered where they exist -------------------------
    rm = d.get("reliability_metric")
    if rm:
        A("<!-- END GENERATED: validation_status -->")
        A("")
        A("<!-- BEGIN GENERATED: reliability_metric -->")
        A("")
        A("## The local reliability metric, exactly defined")
        A("")
        A("| field | value |")
        A("|---|---|")
        for k in ("name", "exact_definition", "units", "solver_output", "plastic_component",
                  "creep_component", "creep_verification", "is_a_range",
                  "range_clarification", "stabilized_cycle_definition", "numerical_status",
                  "metric_agreement", "metric_disagreement"):
            if k in rm:
                A(f"| **{k.replace('_', ' ')}** | {flow(rm[k])} |")
        A("")
        rl = d.get("relative_life", {})
        if rl:
            A("### Relative life")
            A("")
            A(wrap(f"**{flow(rl['status'])}.** `{flow(rl['formula'])}`"))
            A("")
            A(f"- The constant **C cancels** in a ratio: `{rl['C_cancels']}`.")
            A(f"- The exponent **m does NOT cancel**: exponent required = "
              f"`{rl['exponent_required']}`, status = **{rl['exponent_status']}**.")
            A(f"- *Provenance:* {flow(rl['exponent_provenance'])}")
            A(f"- *Correction:* {flow(rl['correction'])}")
            A(f"- *What may be claimed:* {flow(rl['what_may_be_claimed'])}")
            A("")
        ac = d.get("architecture_closure", {})
        if ac:
            A("### Architecture claim closure")
            A("")
            A("| architecture | component height | electrical | local damage |")
            A("|---|---|---|---|")
            for k, v in ac.items():
                A(f"| **{k}** | {flow(v.get('component_height_status', v.get('topology_scope','')))} "
                  f"| {flow(v.get('electrical_resolution', v.get('electrical_status','')))} "
                  f"| {flow(v.get('damage_status', '--'))} |")
            A("")
        A("<!-- END GENERATED: reliability_metric -->")
        A("")
        A("<!-- BEGIN GENERATED: publication_claims -->")
        A("")
    A("## Publication-defensible claims")
    A("")
    for x in cf["publication_claims"]["defensible"]:
        A(f"* {flow(x)}")
    A("")
    A("### Claims that must not be made")
    A("")
    for x in cf["publication_claims"]["must_not_claim"]:
        A(f"* {flow(x)}")
    A("")
    A("<!-- END GENERATED: publication_claims -->")
    A("")
    return "\n".join(L) + "\n"


def main() -> int:
    d = yaml.safe_load(SRC.read_text())
    OUT.write_text(emit(d))
    print(f"wrote {OUT}  ({len(OUT.read_text().splitlines())} lines)")
    if "current_facing" in d:
        OUT_CF.parent.mkdir(parents=True, exist_ok=True)
        OUT_CF.write_text(emit_current_facing(d))
        print(f"wrote {OUT_CF}  ({len(OUT_CF.read_text().splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
