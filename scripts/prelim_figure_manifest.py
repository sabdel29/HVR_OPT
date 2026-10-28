"""presentation/prelim_hvr/FIGURE_MANIFEST.csv -- every image the deck shows, where it
comes from and whether a person has looked at it (brief Part 11).

Rows are derived, not typed: the image list and slide numbers come from index.html, the
purpose of main-slide figures from slide_values.json, type/tool/script from the figure's
own sidecar or metadata (figs/*.sources.json, *.json sidecars, tool_evidence/<stage>/
setup.json, the SVG data-spec-sha256 of the package figures), and 'inspected' from
presentation/prelim_hvr/qa/inspection_log.json, which records actual visual inspection.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = R / "presentation" / "prelim_hvr"

#: (filename regex, type, tool, script, to_scale, hand_entered, notes)
FAMILIES = [
    (r"figs/z1_package_cross_section\.svg|figs/z2_package_cross_section\.svg|"
     r"figs/z1_z2_package_comparison\.svg", "diagram (vector, from the architecture spec)",
     "native SVG (Python)", "scripts/final_closure_package_figs.py",
     "no: vertical exaggeration and minimum layer height stated on the figure",
     "no (architecture_geometry.json, measured on the solver mesh)", ""),
    (r"figs/z1_z2_exploded\.png", "illustration (exploded view)", "native SVG (Python) + "
     "rsvg-convert", "scripts/final_closure_package_figs.py",
     "no: ILLUSTRATIVE — NOT TO SCALE (stamped)", "no (layer order from the spec)", ""),
    (r"figs/regulator_cell_zoom\.svg", "diagram (one cell, schematic placement)",
     "native SVG (Python)", "scripts/final_closure_package_figs.py",
     "partly: true cell side and tier heights; component placement schematic",
     "no (spec + stack card)", ""),
    (r"figs/rdl_model_explained_Z[12]\.svg", "diagram (exact solver geometry, plan view)",
     "native SVG (Python)", "scripts/visualize_rdl_geometry.py",
     "yes in plan; inset schematic", "no (reference problem() geometry, hashed)", ""),
    (r"figs/rdl_reference_annotated_Z[12]\.png", "field render + annotation overlay",
     "VTK 9.6.2 (MOOSE Exodus)", "scripts/visualize_rdl_geometry.py",
     "yes (scale bar)", "no (field data unchanged; overlay from the hashed geometry)", ""),
    (r"figs/tool_map\.svg", "diagram (data flow)", "native SVG (Python)",
     "scripts/final_closure_tool_map.py", "n/a", "no (tool_provenance.json)", ""),
    (r"figs/(s0_cards|scenario_small_multiples|accuracy_runtime_split|local_convergence|"
     r"et_convergence|joint_map|ball_sharing)\.svg", "chart", "Matplotlib 3.10.8", "scripts/final_closure_slide_charts.py", "n/a",
     "no (research/final_closure artifacts)", ""),
    (r"figs/die_warpage_maps\.png", "field render (production structural solution)",
     "Matplotlib 3.10.8 (CalculiX .frd)", "scripts/final_closure_slide_charts.py",
     "yes (axes in mm)", "no (peak-to-valley asserted against final_results.json)", ""),
    (r"figs/rerender_.*\.png", "geometry re-render (EXACT GEOMETRY RE-RENDERED FROM "
     "REFERENCE MODEL)", "PyAEDT export + VTK 9.6.2", "see sidecar", "yes (scale bar)",
     "no (exported AEDT geometry, hashed)", "not a screenshot"),
    (r"tool_evidence/.*/01_geometry.*\.png", "tool screenshot (native AEDT export)",
     "Ansys Electronics Desktop 2026 R1", "scripts/final_closure_evidence.py",
     "as exported", "no", "real session image"),
    (r"tool_evidence/.*/02_annotated\.png", "tool screenshot, cropped + annotated overlay",
     "Ansys Electronics Desktop 2026 R1 + overlay", "see 02_annotated.json",
     "as exported", "labels from setup.json", "pixels unchanged apart from cropping"),
    (r"tool_evidence/.*/04_field\.png", "field render (MOOSE Exodus)",
     "VTK reader + Matplotlib", "scripts/final_closure_evidence.py", "yes", "no", ""),
    (r"tool_evidence/.*/05_comparison\.png", "chart", "Matplotlib", "scripts/final_closure_"
     "evidence.py", "n/a", "no", ""),
    (r"figs/(sharing|cutout|pads|ladder|gates|runtime|bga_count)\.svg", "chart (legacy)",
     "Matplotlib", "scripts/prelim_make_figs.py", "n/a", "no", "appendix"),
    (r"figs/final_.*\.svg", "chart", "Matplotlib", "scripts/prelim_make_figs_final.py",
     "n/a", "no", ""),
]


def _family(rel):
    for pat, *rest in FAMILIES:
        if re.fullmatch(pat, rel):
            return rest
    return ["unclassified", "?", "?", "?", "?", "UNCLASSIFIED"]


def _sources(rel):
    p = D / rel
    side = [p.with_suffix(".sources.json"), p.with_suffix(".json"),
            p.parent / "setup.json"]
    for s in side:
        if s.exists():
            try:
                j = json.loads(s.read_text())
            except json.JSONDecodeError:
                continue
            src = j.get("sources") or j.get("source") or j.get("source_project") or j
            txt = json.dumps(src)[:220] if not isinstance(src, str) else src
            return f"{s.relative_to(D)}: {txt}"
    if p.suffix == ".svg" and p.exists():
        m = re.search(r'data-spec-sha256="([0-9a-f]{12})', p.read_text()[:4000])
        if m:
            return f"research/final_closure/architecture_geometry.json (sha256 {m.group(1)}…)"
    return ""


def main():
    html = (D / "index.html").read_text()
    secs = re.findall(r"<section class='[^']*'>(.*?)</section>", html, re.S)
    sv = json.loads((D / "slide_values.json").read_text())
    n_main = sv["n_main"]
    purpose = {f["figure"]: f["purpose"] for f in sv.get("figures", [])}
    insp_f = D / "qa" / "inspection_log.json"
    insp = json.loads(insp_f.read_text()) if insp_f.exists() else {}
    uses = {}
    for i, s in enumerate(secs, 1):
        t = re.search(r"<h[12][^>]*>(.*?)</h[12]>", s, re.S)
        title = re.sub(r"<[^>]+>", "", t.group(1)).strip() if t else ""
        for rel in re.findall(r'src="((?:figs|tool_evidence)/[^"]+)"', s):
            uses.setdefault(rel, []).append((i, title))
    rows = []
    for rel, where in sorted(uses.items(), key=lambda kv: kv[1][0][0]):
        typ, tool, script, scale, hand, notes = _family(rel)
        slides = "; ".join(f"{i}{'' if i <= n_main else ' (appendix)'}" for i, _ in where)
        ins = insp.get(rel)
        rows.append({"figure": rel, "slide": slides,
                     "purpose": purpose.get(rel) or where[0][1],
                     "type": typ, "source artifacts": _sources(rel), "script": script,
                     "tool": tool, "to-scale?": scale, "values hand-entered?": hand,
                     "inspected?": (f"yes — {ins['how']} ({ins['date']})" if ins else "NO"),
                     "notes": notes})
    with (D / "FIGURE_MANIFEST.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    bad = [r["figure"] for r in rows if r["values hand-entered?"] == "UNCLASSIFIED"]
    not_insp = [r["figure"] for r in rows if r["inspected?"] == "NO"]
    print(f"{len(rows)} figures; unclassified {bad}; not yet inspected: {len(not_insp)}")


if __name__ == "__main__":
    main()
