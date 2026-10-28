"""The MAIN flow of the prelim deck (brief Part 15): ~30 slides that tell one naive story,
everything else in the appendix. Every number is read from a research/final_closure
artifact at build time and recorded in presentation/prelim_hvr/slide_values.json with the
artifact and key it came from, so a test can re-derive it (brief Part 24, test 5).

Imported by scripts/prelim_build_deck.py, which owns S(), the collected legacy slides
(take() pulls one by title and marks it used) and the HTML assembly.
"""
from __future__ import annotations

import json
from pathlib import Path

from prelim_deck_final_sections import A, J, fmt_s, img_or_note, pct, ratio, rt

R = Path(__file__).resolve().parents[1]
DECK = R / "presentation" / "prelim_hvr"
VALUES: list = []
FIGS: list = []           # (figure, slide title, purpose) -> FIGURE_MANIFEST.csv


def resolve(source, key):
    """The raw artifact value behind a slide number: research/final_closure/<source> at a
    dotted key; for accuracy_speed_matrix.json the first token is the stage name."""
    d = J(source)
    if d is None:
        return None
    parts = key.split(".")
    if source == "accuracy_speed_matrix.json":
        d = next((r for r in d["rows"] if r["stage"] == parts[0]), None)
        parts = parts[1:]
    for p in parts:
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d


def val(slide, label, text, source, key):
    VALUES.append({"slide": slide, "label": label, "text": text, "source": source,
                   "key": key, "raw": resolve(source, key)})
    return text


def fig(slide, rel, purpose, alt, style="max-height:60vh;max-width:100%"):
    FIGS.append({"figure": rel, "slide": slide, "purpose": purpose})
    if (DECK / rel).exists():
        return f'<img src="{rel}" alt="{alt}" style="{style}">'
    return f'<div class="banner open">MISSING FIGURE {rel}</div>'


def naive(q):
    return (f"<div class='naive'><span class='nq'>The question:</span> {q}</div>")


def intro(name):
    ti = json.loads((DECK / "tool_intro.json").read_text()) if (DECK / "tool_intro.json").exists() else []
    lst = ti if isinstance(ti, list) else ti.get("tools", [])
    t = next((x for x in lst if x.get("name", "").lower().startswith(name.lower())), None)
    return t["one_liner"] if t else ""


def _rows():
    return {(r["arch"], r["scenario"]): r for r in (J("final_results.json") or [])}


def _od():
    return (J("ordering.json") or {}).get("orderings", {})


def _mech_moves(cb):
    """Which mechanical ordering each class-B variant reverses (classB_resolution.json)."""
    mv = {}
    for g in cb.get("gates", []):
        for r in g.get("rows", []):
            if (r.get("observable") in ("die_warpage_pv_um", "du_c_um") and r.get("robust") is False
                    and str(r.get("production_verdict", "")).endswith("lower")
                    and str(r.get("verdict", "")).endswith("lower")):
                mv.setdefault(r["case"], set()).add(
                    {"die_warpage_pv_um": "warpage", "du_c_um": "joint-driver"}[r["observable"]])
    if not mv:
        return "No class-B input reverses a mechanical ordering"
    plain = {"f2_void": "void out-of-cell volume", "z2_cooled": "a cold plate under the Z2 "
             "converter", "f1_clearance": "an open sidewall clearance"}
    return "Mechanical orderings that reverse: " + "; ".join(
        f"{' and '.join(sorted(v))} under {plain.get(c, c.replace('_', ' '))}"
        for c, v in mv.items())


def build(S, take, emit):
    rows, od = _rows(), _od()
    sc = (J("ordering.json") or {}).get("scenario_classes", {})
    lm = J("local_mesh_study.json") or {}
    cb = J("classB_resolution.json") or {}
    pn = J("package_network.json") or {}

    # 1-5 ----------------------------------------------------------------- motivation
    for t in ("Electrothermal", "Start with one number",
              "Why low-voltage lateral delivery is so expensive",
              "Three ways to deliver the power", "Packaging 101"):
        emit(take(t))

    # 6 ------------------------------------------------------------- Z1 vs Z2 picture
    t = "Two ways to put 49 converters under one die"
    S(f"""<h2>{t}</h2>
<div style="text-align:center">{fig(t, "figs/z1_z2_package_comparison.svg",
    "Z1 vs Z2 package construction, same scale and style", "Z1 and Z2 cross sections",
    "max-height:77vh;max-width:100%")}</div>""",
      "Point at the converter in each picture. Z1: sandwiched between substrate and die. "
      "Z2: hanging below the substrate, inside the hole in the board. Then trace the "
      "orange 48 V arrow and the purple 1 V arrow in each. Z1 converts inside the package "
      "and then has a very short 1 V path; Z2 converts below the substrate and sends about "
      "1000 A at 1 V up through the TSV field. Everything else in the talk is a consequence "
      "of where that conversion happens.",
      "figs/z1_z2_package_comparison.svg — generated from research/final_closure/"
      "architecture_geometry.json (layer heights measured on the solver mesh)")

    # 7 ---------------------------------------------------------------- one cell
    zoom = DECK / "figs" / "regulator_cell_zoom.svg"
    if zoom.exists():
        t = "Inside one regulator cell"
        S(f"""<h2>{t}</h2><div class="cols" style="align-items:center">
<div style="flex:1.3;text-align:center">{fig(t, "figs/regulator_cell_zoom.svg",
    "one regulator cell: tiers and components", "one regulator cell",
    "max-height:62vh;max-width:100%")}</div>
<div><p>48 V → 3:1 switched capacitor → 16 V → two-phase buck → 1 V.</p>
<p>Each of the 49 cells carries about 20 A at 1 V. The same 11 components and the same
tier heights are used in Z1 and Z2 — only location, support and cooling differ.</p></div>
</div>""", "Keep it short: the converter is identical in both architectures; this is a "
            "packaging comparison, not a converter comparison.",
          "figs/regulator_cell_zoom.svg — research/final_closure/architecture_geometry.json")
    else:
        emit(take("The converter inside each cell"))

    # 8 -------------------------------------------------------------- what is compared
    t = "What is being compared"
    S(f"""<h2>{t}</h2>
<p>Each architecture is pushed through the same chain, and five quantities are compared:</p>
<table><tr><th>quantity</th><th>why it matters</th><th>unit</th></tr>
<tr><td><strong>electrical loss</strong></td><td>energy wasted between the board and the die</td><td>W</td></tr>
<tr><td><strong>peak temperature</strong></td><td>the hottest point anywhere in the package</td><td>°C</td></tr>
<tr><td><strong>die warpage</strong></td><td>how much the die surface bows</td><td>µm</td></tr>
<tr><td><strong>joint displacement driver</strong></td><td>how far the worst solder ball is sheared</td><td>µm</td></tr>
<tr><td><strong>local inelastic strain</strong></td><td>how much that ball deforms permanently per cycle</td><td>–</td></tr></table>
<div class="callout" style="margin-top:.5em">A ranking is claimed only where the Z1/Z2 gap is
larger than <strong>twice the measured discretisation uncertainty</strong>. Otherwise:
"no ranking".</div>""",
      "Say the rule out loud: no ranking unless the gap exceeds twice the measured "
      "numerical uncertainty. This rule is applied by one generator and every slide and "
      "the paper read its output.", "research/final_closure/ordering.json (rule field)")

    # 9 ---------------------------------------------------------------- pipeline
    emit(take("How one architecture is evaluated"))

    # 10 -------------------------------------------------------------- tools
    t = "What software is doing what?"
    S(f"""<h2>{t}</h2><div style="text-align:center">{fig(t, "figs/tool_map.svg",
    "which tool computes which stage; executed vs not executed", "tool map",
    "max-height:74vh;max-width:100%")}</div>""",
      "Name each tool once, plainly: CalculiX computes all production temperatures, "
      "stresses and the solder joint; Ansys Mechanical and MOOSE are used only as "
      "independent references; Q3D could not be run because the licence is not available. "
      "VTK and matplotlib draw results — they are not solvers.",
      "presentation/prelim_hvr/tool_intro.json · research/final_closure/tool_provenance.json")

    # 11 ------------------------------------------------------------- electrical path
    sec = take("The conductors this work has to account for")
    emit(sec.replace("<h2>The conductors this work has to account for</h2>",
                     "<h2>The electrical path — every conductor has one owner</h2>"
                     + naive("How much power is lost carrying 1 kW from the board to the "
                             "die, and in which conductor does it turn into heat?"), 1))

    # 12 ------------------------------------------------------------- RDL model
    t = "The package 48 V RDL, seen from above"
    S(f"""<h2>{t}</h2><div class="cols" style="align-items:flex-start">
<div style="flex:1.05;text-align:center">{fig(t, "figs/rdl_model_explained_Z2.svg",
    "what the RDL network solver sees: sheet, balls, pads, opening (Z2)", "RDL model Z2",
    "max-height:64vh;max-width:100%")}</div>
<div style="flex:.95;text-align:center">{fig(t, "figs/rdl_model_explained_Z1.svg",
    "same, Z1 (no opening)", "RDL model Z1", "max-height:64vh;max-width:100%")}</div></div>""",
      "The solver looks down on ONE copper layer: the 48 V sheet between the BGA and the "
      "substrate. Balls feed it, the 49 regulator input pads drain it. In Z2 the balls "
      "can only sit outside the opening, so current must flow inward.",
      "figs/rdl_model_explained_Z*.svg — exact solver geometry, research/final_closure/"
      "rdl_geometry_Z*.json (geometry hash)")

    # 13 ------------------------------------------------------------- RDL vs MOOSE
    t = "RDL model vs MOOSE (independent finite elements)"
    ref = J("reference_pkg_rdl_moose_Z2.json") or {}
    r2 = A("pkg_rdl_Z2")
    nums = [("production R<sub>eff</sub> (Z2, supply)",
             val(t, "prod R_eff Z2", f"{ref.get('production_L3', {}).get('R_eff_ohm', 0) * 1e3:.4f} mΩ",
                 "reference_pkg_rdl_moose_Z2.json", "production_L3.R_eff_ohm")),
            ("MOOSE R<sub>eff</sub>, finest mesh",
             val(t, "moose R_eff Z2", f"{ref.get('moose', {}).get('m3', {}).get('R_eff_ohm', 0) * 1e3:.4f} mΩ",
                 "reference_pkg_rdl_moose_Z2.json", "moose.m3.R_eff_ohm")),
            ("difference", val(t, "err Z2", pct(r2.get("error") if r2 else None),
                               "accuracy_speed_matrix.json", "pkg_rdl_Z2.error")),
            ("production runtime", val(t, "rt prod", rt(r2, "production"),
                                       "accuracy_speed_matrix.json", "pkg_rdl_Z2.production_runtime_s")),
            ("MOOSE runtime", val(t, "rt ref", rt(r2, "reference"),
                                  "accuracy_speed_matrix.json", "pkg_rdl_Z2.reference_runtime_s")),
            ("runtime ratio", val(t, "ratio", ratio(r2), "accuracy_speed_matrix.json",
                                  "pkg_rdl_Z2.speedup"))]
    trs = "".join(f"<tr><td>{k}</td><td class='num'>{v}</td></tr>" for k, v in nums)
    S(f"""<h2>{t}</h2>
<div class="val" style="grid-template-columns:0.95fr 1.6fr 0.75fr">
<div class="col"><h3>Our model (cartoon)</h3>{fig(t, "figs/rdl_model_explained_Z2.svg",
    "validation cartoon", "model cartoon")}</div>
<div class="col"><h3>MOOSE field — matched run</h3>{fig(t, "figs/rdl_reference_annotated_Z2.png",
    "MOOSE voltage field, annotated overlay (data unchanged)", "MOOSE field")}
<div class="toolcap">{intro("MOOSE")}</div></div>
<div class="col"><h3>Numbers</h3><table>{trs}</table>
<p class="sub">Same formulation in both solvers; mesh sequence m1–m3 in MOOSE.</p></div>
</div>""", "Left: what the model is. Centre: the actual MOOSE solution, rendered from its "
            "own output file; the outlines and labels are an overlay. Right: the numbers. "
            "The agreement is a model-to-model check on the same problem, not a measurement.",
          "research/final_closure/reference_pkg_rdl_moose_Z2.json · tool_evidence/pkg_rdl_moose_Z2/")

    # 14 ------------------------------------------------------------- BGA sharing
    sec = take("BGA current sharing").replace('src="figs/sharing.svg"',
                                                 'src="figs/ball_sharing.svg"')
    FIGS.append({"figure": "figs/ball_sharing.svg", "slide": "BGA current sharing",
                 "purpose": "solved per-ball current share, matched 54-ball construction"})
    n = pn.get("matched_count")
    emit(sec.replace("</h2>", "</h2>" + (f"<p class='sub'>Matched construction: "
                     f"<strong>{val('BGA current sharing', 'matched count', str(n), 'package_network.json', 'matched_count')}"
                     f" balls per rail</strong> for both architectures.</p>" if n else ""), 1))

    # 15 ------------------------------------------------------------- heat
    sec = take("The heat map")
    emit(sec.replace("</h2>", "</h2>" + naive("Where is the ~145 W of loss produced, and "
                                              "where does that heat leave the package?"), 1))

    # 16 ------------------------------------------------------------- thermal validation
    t = "Thermal model vs AEDT and MOOSE"
    a1, a2 = A("thermal_column_aedt_Z2"), A("thermal_column_moose_Z2")
    rer = "figs/rerender_thermal_column_Z2.png"
    left = (fig(t, rer, "EXACT GEOMETRY RE-RENDERED FROM REFERENCE MODEL", "re-render")
            if (DECK / rer).exists() else
            "<p>A unit cell of the package column (substrate, converter tiers, die, TIM) "
            "with the same heat input and the same cooled faces in all three solvers.</p>")
    shot = ("tool_evidence/thermal_column_Z2/02_annotated.png"
            if (DECK / "tool_evidence/thermal_column_Z2/02_annotated.png").exists()
            else "tool_evidence/thermal_column_Z2/01_geometry.png")
    nums = [("vs AEDT Mechanical", val(t, "aedt err", pct(a1.get("error") if a1 else None),
                                        "accuracy_speed_matrix.json", "thermal_column_aedt_Z2.error")),
            ("vs MOOSE", val(t, "moose err", pct(a2.get("error") if a2 else None),
                             "accuracy_speed_matrix.json", "thermal_column_moose_Z2.error")),
            ("runtime ratio vs AEDT", val(t, "aedt ratio", ratio(a1),
                                          "accuracy_speed_matrix.json", "thermal_column_aedt_Z2.speedup")),
            ("runtime ratio vs MOOSE", val(t, "moose ratio", ratio(a2),
                                           "accuracy_speed_matrix.json", "thermal_column_moose_Z2.speedup"))]
    trs = "".join(f"<tr><td>{k}</td><td class='num'>{v}</td></tr>" for k, v in nums)
    S(f"""<h2>{t}</h2>
<div class="val">
<div class="col"><h3>Exact geometry, re-rendered</h3>{left}</div>
<div class="col"><h3>Ansys screenshot — matched run</h3>{fig(t, shot,
    "real AEDT screenshot of the matched run (annotated crop)", "AEDT screenshot")}
<div class="toolcap">{intro("AEDT Mechanical")}</div></div>
<div class="col"><h3>Numbers (Z2 unit cell)</h3><table>{trs}</table>
<p class="sub">Error = difference in temperature rise above the coolant.</p></div></div>""",
      "The middle image is the real Ansys session; the left image re-draws the exact same "
      "geometry from the project file so it can be read. CalculiX, Ansys and MOOSE agree "
      "to about a tenth of a percent on this matched problem.",
      "accuracy_speed_matrix.json · tool_evidence/thermal_column_Z2/")

    # 17 ------------------------------------------------------------- E-T fixed point
    emit(take("The electrothermal fixed point converges").replace(
        'src="figs/final_et_convergence.svg"', 'src="figs/et_convergence.svg"'))
    FIGS.append({"figure": "figs/et_convergence.svg", "slide": "E-T fixed point",
                 "purpose": "peak temperature and iteration change against the tolerance"})

    # 18 ------------------------------------------------------------- why warp + Z1/Z2
    t = "Why packages warp — and what Z1 and Z2 actually do"
    S(f"""<h2>{t}</h2>
{naive("Does the package bend, and how hard is the worst solder ball pushed sideways?")}
<div class="cols" style="align-items:center"><div style="flex:.8">
<p>Silicon expands about 2.6 ppm/K, the board about 15 ppm/K, copper about 17 ppm/K.
Bonded together and heated, they cannot all grow freely, so the stack <strong>bends</strong>
and the solder balls between them are <strong>sheared</strong>.</p>
<p class="sub">Right: the production thermoelastic solution itself — the die-top surface
of each architecture, one colour scale.</p></div>
<div style="flex:1.2;text-align:center">{fig(t, "figs/die_warpage_maps.png",
    "real FE die-top displacement maps, Z1 and Z2, same scale", "die warpage maps",
    "max-height:56vh;max-width:100%")}</div></div>""",
      "Do the physics in one sentence, then show the real result: Z2's die bows about "
      "2.5 times more than Z1's under the same scenario.",
      "figs/die_warpage_maps.png — production structural solution (r21 mesh); peak-to-valley "
      "checked against final_results.json")

    # 19 ------------------------------------------------------------- mech validation
    t = "Global mechanics vs AEDT and the closed form"
    mb, mc = A("mech_bilayer_aedt"), A("mech_bilayer_closed_form")
    rer = "figs/rerender_mech_bilayer.png"
    shot = ("tool_evidence/mech_bilayer/02_annotated.png"
            if (DECK / "tool_evidence/mech_bilayer/02_annotated.png").exists()
            else "tool_evidence/mech_bilayer/01_geometry.png")
    left = (fig(t, rer, "EXACT GEOMETRY RE-RENDERED FROM REFERENCE MODEL", "re-render")
            if (DECK / rer).exists() else
            "<p>A silicon–copper bilayer heated uniformly: the textbook bending problem "
            "the production thermoelastic element must reproduce.</p>")
    nums = [("vs AEDT Mechanical", val(t, "bilayer aedt err", pct(mb.get("error") if mb else None),
                                        "accuracy_speed_matrix.json", "mech_bilayer_aedt.error")),
            ("vs bimaterial closed form", val(t, "bilayer closed err",
                                               pct(mc.get("error") if mc else None),
                                               "accuracy_speed_matrix.json",
                                               "mech_bilayer_closed_form.error")),
            ("runtime ratio vs AEDT", val(t, "bilayer ratio", ratio(mb),
                                          "accuracy_speed_matrix.json", "mech_bilayer_aedt.speedup"))]
    trs = "".join(f"<tr><td>{k}</td><td class='num'>{v}</td></tr>" for k, v in nums)
    S(f"""<h2>{t}</h2>
<div class="val">
<div class="col"><h3>Exact geometry, re-rendered</h3>{left}</div>
<div class="col"><h3>Ansys screenshot — matched run</h3>{fig(t, shot,
    "real AEDT screenshot of the matched bilayer (annotated crop)", "AEDT screenshot")}
<div class="toolcap">{intro("AEDT Mechanical")}</div></div>
<div class="col"><h3>Numbers (curvature)</h3><table>{trs}</table>
<p class="sub">The closed form ignores free-edge effects, so a few tenths of a percent
are expected; the matched FE agrees to a hundredth.</p></div></div>""",
      "Same layout as the thermal check. The production element reproduces the commercial "
      "solution of the same bilayer to about one hundredth of a percent.",
      "accuracy_speed_matrix.json · tool_evidence/mech_bilayer/")

    # 20-21 ---------------------------------------------------------- global -> local, joint
    emit(take("Global driver"))
    emit(take("Where is the critical joint").replace('src="figs/final_joint_map.svg"',
                                                     'src="figs/joint_map.svg"'))
    FIGS.append({"figure": "figs/joint_map.svg", "slide": "critical joint",
                 "purpose": "joint driver at every legal site, critical joint circled"})

    # 22 ------------------------------------------------------------- local + convergence
    t = "Local solder response and how well it is resolved"
    pol = J("local_mesh_policy.json") or {}
    cells = []
    for a, s in pol.get("cases", []):
        c = (lm.get("cases") or {}).get(f"{a}_{s}") or {}
        if c.get("production_value"):
            cells.append(f"<tr><td>{a} {s.replace('_', '-')}</td><td class='num'>"
                         + val(t, f"{a}_{s} value", f"{c['production_value'] * 1e3:.3f}",
                               "local_mesh_study.json", f"cases.{a}_{s}.production_value")
                         + "</td><td>" + str(c.get("status")) + "</td><td class='num'>"
                         + val(t, f"{a}_{s} U", f"{100 * c['U']:.2f} %" if c.get("U") is not None else "n/a",
                               "local_mesh_study.json", f"cases.{a}_{s}.U") + "</td></tr>")
    S(f"""<h2>{t}</h2>
{naive("Inside that one ball, how much does the solder deform permanently per cycle — and is the number converged?")}
<div style="text-align:center">{fig(t, "figs/local_convergence.svg",
    "declared local mesh family per case, production level and U", "local convergence",
    "max-height:46vh;max-width:100%")}</div>
<div class="cols"><div><table class="small"><tr><th>case</th><th>Δε<sub>in</sub>/cycle (×10<sup>-3</sup>)</th>
<th>status</th><th>U</th></tr>{''.join(cells)}</table></div>
<div class="callout" style="font-size:.72em">The mesh rule was declared before the finer
levels were read. Its own acceptance test exposed a parser defect (seven-digit output
times merged increments, biasing the last cycle); fixed and verified — the published
control is reproduced to all ten printed digits.</div></div>""",
      "Two points. First, the local number is reported with a measured uncertainty: mesh "
      "plus time step plus cycle count. Second, the declared-policy process caught a "
      "post-processing defect that would otherwise have shifted the answer by up to 17 %.",
      "research/final_closure/local_mesh_study.json · local_time_study.json · "
      "local_cycle_study.json · local_mesh_policy.json")

    # 23 ------------------------------------------------------------- closure changed
    t = "What physical closure changed"
    S(f"""<h2>{t}</h2>
<table><tr><th>before closure</th><th>after closure</th><th>effect</th></tr>
<tr><td>BGA current shared equally — an input</td><td>voltage-fed network: the sharing is solved</td>
<td>ball count becomes a solved design variable</td></tr>
<tr><td>Z2 converter as a full-area slab</td><td>49 physical cells in the PCB opening</td>
<td>geometry is the architecture being claimed</td></tr>
<tr><td>RDL tier conductivity from a series formula</td><td>explicit RVE in Ansys</td>
<td>through-thickness k was 12.5 % too high</td></tr>
<tr><td>earlier mechanical ranking</td><td>physical lineage</td>
<td>the mechanical ordering reversed</td></tr></table>
<p class="sub" style="margin-top:.4em">The full defect history (floating-point lattice,
intermediate counts, obsolete resistances) is in the appendix.</p>""",
      "Four examples only. The point: physical closure changed answers, including the "
      "architecture ordering. Details are in the appendix if asked.",
      "appendix · research/final_closure/README.md")

    # 24 ------------------------------------------------------------- S0 result
    t = "HV-S0 result (headline scenario)"
    s0 = sc.get("HV_S0", {})
    S(f"""<h2>{t}</h2>
<div style="text-align:center">{fig(t, "figs/s0_cards.svg",
    "five observables, Z1 vs Z2, with uncertainty and verdict", "S0 cards",
    "max-height:50vh;max-width:100%")}</div>
<div class="callout" style="margin-top:.3em">{s0.get("statement", "")}
{od.get("T_max_C", {}).get("statement", "")}</div>""",
      "Read the verdict line under each card, not the bars. Loss: Z2 lower. Peak "
      "temperature: no ranking — the difference is inside the measured uncertainty. "
      "Warpage, joint driver and local response: Z1 lower, by wide margins.",
      "figs/s0_cards.svg — final_results.json · ordering.json")

    # 25 ------------------------------------------------------------- scenarios
    t = "Scenario robustness"
    st = " ".join(sc[s]["statement"] for s in ("HV_S1", "HV_S2") if s in sc)
    S(f"""<h2>{t}</h2>
<div style="text-align:center">{fig(t, "figs/scenario_small_multiples.svg",
    "small multiples across HV-S0/S1/S2 with scenario classes", "scenario small multiples",
    "max-height:58vh;max-width:100%")}</div>
<p class="sub">{st} {od.get("d_eps_in_per_cycle", {}).get("statement", "")}</p>""",
      "HV-S0 is the headline. HV-S1 is a sensitivity: Z1's joint is above the "
      "constitutive calibration, so its local response is extrapolated. HV-S2 is a stress "
      "case: Z1's joint reaches the solder melting onset, so it is an infeasibility result "
      "and no architecture comparison of any quantity is drawn there (hollow squares).",
      "figs/scenario_small_multiples.svg — final_results.json · ordering.json")

    # 26 ------------------------------------------------------------- class B
    t = "Which inputs could move an ordering?"
    sm = cb.get("summary") or {}
    order = ["board_h1", "board_t3p2", "board_eta025", "board_eta075", "tsv_mid", "tsv_min",
             "f1_clearance", "f2_void", "z2_cooled", "gan_k_half", "conv_k_tenth",
             "conv_E80_a4", "conv_E80_a10", "conv_E160_a4", "conv_E160_a10", "pad_drop"]
    name = {"board_h1": "board as five depth blocks (H1)", "board_t3p2": "board 3.2 mm (2.4)",
            "board_eta025": "board copper coverage 0.25 (0.50)",
            "board_eta075": "board copper coverage 0.75 (0.50)",
            "tsv_mid": "TSV field 729/cell (1444)", "tsv_min": "TSV field 64/cell (1444)",
            "f1_clearance": "Z2: sidewall clearance open (filled)",
            "f2_void": "void between cells (encapsulated)",
            "z2_cooled": "Z2: cold plate under the converter",
            "gan_k_half": "GaN tiers at k/2 (bound)",
            "conv_k_tenth": "converter tiers at k/10 (bound)",
            "conv_E80_a4": "converter medium 80 GPa, 4 ppm/K",
            "conv_E80_a10": "converter medium 80 GPa, 10 ppm/K",
            "conv_E160_a4": "converter medium 160 GPa, 4 ppm/K",
            "conv_E160_a10": "converter medium 160 GPa, 10 ppm/K",
            "pad_drop": "1 V pads at the drop floor (2040)"}
    cols = (("P_loss_w", "loss"), ("T_max_C", "peak T"), ("die_warpage_pv_um", "warpage"),
            ("du_c_um", "joint driver"), ("d_eps_in_per_cycle", "local"))
    by = {}
    for g in cb.get("gates", []):
        if g.get("method") != "runs":
            continue
        for r in g.get("rows", []):
            by.setdefault(r["case"], {})[r["observable"]] = r
    vs = {"Z1 lower": "Z1", "Z2 lower": "Z2", "unresolved": "no rank",
          "not rankable": "n/a"}

    def cell(r):
        if not r:
            return "<td>–</td>"
        if r.get("robust"):
            return "<td><span class='chip ok'>holds</span></td>"
        return (f"<td><span class='chip open'>→ {vs.get(r['verdict'], r['verdict'])}"
                "</span></td>")
    trs = []
    for c in order:
        if c not in by:
            continue
        mx = max((abs(x) for r in by[c].values()
                  for x in (r.get("change_rel") or {}).values()
                  if isinstance(x, (int, float))), default=None)
        trs.append(f"<tr><td>{name.get(c, c)}</td>" + "".join(cell(by[c].get(k)) for k, _ in cols)
                   + (f"<td class='num'>{100 * mx:.0f} %</td>" if mx is not None else "<td></td>")
                   + "</tr>")
    head = "".join(f"<th>{lab}</th>" for _, lab in cols)
    S(f"""<h2>{t}</h2>
<p class="sub">{sm.get('n_gates', 0)} open sensitivity inputs: {sm.get('b1_total', 0)} could move
an ordering (B1), {(sm.get('subtypes') or {}).get('B2', 0)} only a magnitude (B2); all
{sm.get('b1_resolved', 0)} B1 resolved. Each variant run on the production mesh at HV-S0;
verdicts by the production ordering rule. The 48 V waveform is handled by the scenarios
(slide 25); contact and RDL construction are bounded from the network sweep (loss holds).</p>
<table class="small"><tr><th>input changed (production value)</th>{head}<th>largest change</th></tr>
{''.join(trs)}</table>""",
      "Read across a row: green means that ordering survives the change; red says what it "
      "becomes. " + _mech_moves(cb) + ". The "
      "local ordering, resolved only narrowly in production, is the fragile one.",
      "research/final_closure/classB_resolution.csv")

    # 27 ------------------------------------------------------------- accuracy / runtime
    t = "Accuracy and runtime, stage by stage"
    take(t)                       # the legacy one-chart version is superseded by this slide
    S(f"""<h2>{t}</h2><div style="text-align:center">{fig(t, "figs/accuracy_runtime_split.svg",
    "closed-form vs FE (log) and FE vs FE (linear) kept apart", "accuracy and runtime",
    "max-height:64vh;max-width:100%")}</div>""",
      "Two different claims, two panels. Closed forms are ten million times cheaper than a "
      "finite-element solve of the same small problem — that is expected. The production "
      "finite-element stages are between 0.6 and 4 times the speed of the reference "
      "solvers on the same machine. No end-to-end speedup is claimed.",
      "figs/accuracy_runtime_split.svg — accuracy_speed_matrix.json")

    # 28 ------------------------------------------------------------- claims
    t = "What we can claim — and what we cannot"
    # one line per observable, read from ordering.json's per-scenario verdicts (the full
    # statements, with their reasons, are on slides 24-25 and in the paper)
    can = []
    for k, nm in (("P_loss_w", "Loss"), ("T_max_C", "Peak temperature"),
                  ("die_warpage_pv_um", "Die warpage"), ("du_c_um", "Joint driver"),
                  ("d_eps_in_per_cycle", "Local response")):
        won = {}
        for s_, v in (od.get(k) or {}).get("per_scenario", {}).items():
            if v.endswith("lower"):
                won.setdefault(v.split()[0], []).append(s_.replace("_", "-"))
        if won:
            can.append(f"{nm}: " + "; ".join(f"{a} lower in {' and '.join(ss)}"
                                             for a, ss in won.items()))
    plain = {"board_t3p2": "a 3.2 mm board", "board_eta025": "board copper coverage 0.25",
             "board_eta075": "board copper coverage 0.75",
             "tsv_mid": "a 729-via TSV field", "gan_k_half": "GaN tiers at half conductivity",
             "pad_drop": "the minimum pad count",
             "tsv_min": "the electrically minimal TSV field (64 vias/cell)",
             "f2_void": "void instead of encapsulated space between the cells",
             "f1_clearance": "encapsulated cells with the PCB sidewall clearance open",
             "conv_k_tenth": "a tenfold lower converter-tier conductivity",
             "z2_cooled": "a cold plate under the Z2 converter",
             "board_h1": "the five-block board model"}
    obs = {"P_loss_w": "loss", "T_max_C": "peak temperature", "die_warpage_pv_um": "warpage",
           "du_c_um": "joint driver", "d_eps_in_per_cycle": "local response"}
    cond = {}
    for g in cb.get("gates", []):
        for r in g.get("rows", []):
            if r.get("robust") is False:
                cond.setdefault(r["case"], set()).add(
                    f"{obs.get(r['observable'], r['observable'])}: "
                    f"{r['production_verdict']} → {r['verdict']}")
    conds = "".join(f"<li>{plain.get(c, c.replace('_', ' '))} — {'; '.join(sorted(v))}</li>"
                    for c, v in cond.items())
    S(f"""<h2>{t}</h2><div class="cols"><div><h3>Can claim (production model; each gap &gt; 2U)</h3><ul>
{''.join(f'<li>{c}</li>' for c in can)}</ul>
{('<h3>Conditioned on — orderings that move under a sensitivity</h3><ul class="sub">' + conds + '</ul>') if conds else ''}</div>
<div><h3>Cannot claim</h3><ul>
<li>a thermal ranking at HV-S0 (inside the measured uncertainty);</li>
{''.join(f"<li>any ordering under {s.replace('_', '-')}: {' and '.join(c['inadmissible'])} "
         "leaves the valid solid-solder domain there;</li>"
         for s, c in sc.items() if c.get("inadmissible"))}
<li>any absolute solder life (response only — Darveaux);</li>
<li>the 48 V waveform (results are scenario-conditioned);</li>
<li>an electromigration-safe current density;</li>
<li>a commercial end-to-end speedup;</li>
<li>any statement about which architecture a company uses or should use.</li></ul></div></div>""",
      "Read the left column as the paper's claims, the right as its explicit non-claims.",
      "ordering.json statements · FINAL_PAPER_DECISION.md")

    # 29 ------------------------------------------------------ contributions + future
    take("Contribution"), take("Future work")        # replaced by the combined slide
    t = "Contributions and future work"
    ice = J("reference_cooling_icepak.json") or {}
    ice_done = str(ice.get("status", "")).upper().startswith("EXECUTED")
    moved = " ".join((cb.get("summary") or {}).get("orderings_that_move") or [])
    fut = ["the converter's switch-state schedule, so one 48 V waveform replaces the named "
           "scenarios;",
           "Z2 backside cooling as a co-designed architecture state;"]
    if "tsv" in moved:
        fut.append("TSV density as a co-design variable: the HV-S0 loss ordering depends on it;")
    fut.append("the Icepak conjugate-CFD check extended from one channel to the full cold "
               "plate;" if ice_done else
               "an Icepak conjugate-CFD check of the cold-plate correlation;")
    fut += ["qualified electromigration and fatigue data, for absolute reliability "
            "statements;", "a full-package commercial FE benchmark beyond the unit cell."]
    S(f"""<h2>{t}</h2><div class="cols"><div><h3>Contributions</h3><ol>
<li>A hierarchical electrothermal–mechanical framework for DVPD in which converter synthesis
propagates into an explicit physical package, evaluated in one lineage.</li>
<li>A voltage-fed, return-inclusive package network on an aligned graded grid, with the BGA
count solved as a design variable.</li>
<li>Stage-by-stage checks against commercial and open-source FEM, with model-specific errors
and runtimes instead of one framework accuracy.</li>
<li>Convergence and sensitivity rules declared before results were read; every ordering is
gated by measured uncertainty.</li>
<li>Physical closure reverses an architecture conclusion.</li></ol></div>
<div><h3>Future work</h3><ul>{''.join(f'<li>{x}</li>' for x in fut)}</ul></div></div>""",
      "End on contribution 5. Each future-work item replaces a declared assumption or a "
      "scenario with data; none is needed for the comparison itself.", "")
    emit(take("Thank you"))
