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

from prelim_deck_final_sections import A, J, case_plain, fmt_s, img_or_note, pct, ratio, rt

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


def _case(a, scen="HV_S0"):
    """The production case file of an architecture (final_results.json names it); for the
    BGA-fed control, the one control_results.json names."""
    r = _rows().get((a, scen))
    name = (r or {}).get("case_file") or (((J("control_results.json") or {}).get("cases") or {})
                                          .get(f"{a}_{scen}") or {}).get("case_file")
    return J(name) if name else None


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


def thesis_items(cb):
    """Part 24's clauses, each only where classB_resolution.json supports it: 'reverse' where
    a resolved ordering flips, 'change' where a verdict is created or withdrawn."""
    moved, rev = {}, {}
    for g in cb.get("gates", []):
        for r in g.get("rows", []):
            if r.get("robust") is not False:
                continue
            moved.setdefault(r["case"], set()).add(r["observable"])
            p_, v_ = str(r.get("production_verdict", "")), str(r.get("verdict", ""))
            if p_.endswith("lower") and v_.endswith("lower"):
                rev.setdefault(r["case"], set()).add(r["observable"])

    def verb(cases, obs):
        if any(rev.get(c, set()) & obs for c in cases):
            return "reverse"
        if any(moved.get(c, set()) & obs for c in cases):
            return "change"
        return None
    items = ["<li><strong>Converter placement</strong> changes the high-voltage entry path: Z1 pays "
             "for 48 V inside the package, Z2 in an external feed whose resistance decides the "
             "electrical comparison.</li>"]
    v = verb(("tsv_min", "tsv_mid"), {"P_loss_package_internal_w"})
    if v:
        items.append(f"<li><strong>TSV provisioning</strong> can {v} the package-internal "
                     "electrical preference.</li>")
    v = verb(("attach_sparse", "attach_sparse_stiff"), {"P_loss_package_internal_w"})
    if v:
        items.append(f"<li><strong>The regulator-to-substrate attach density</strong> can {v} "
                     "it.</li>")
    mech = {"die_warpage_pv_um", "du_c_um", "d_eps_in_per_cycle"}
    v = verb(("z2_cooled", "z2_cooled_tim", "icepak_equivalent"), mech)
    w = verb(("f2_void", "f1_sidewall_filled"), mech)
    if v and w == v:
        items.append(f"<li><strong>Cooling</strong> and the <strong>out-of-cell construction"
                     f"</strong> can {v} the mechanical preference.</li>")
    else:
        if v:
            items.append(f"<li><strong>Cooling</strong> can {v} the mechanical preference.</li>")
        if w:
            items.append(f"<li>The <strong>out-of-cell construction</strong> can {w} the "
                         "mechanical preference.</li>")
    if verb(("f2_void", "f1_sidewall_filled", "attach_h20", "attach_h40", "attach_sn",
             "attach_stiff", "attach_uf_soft", "attach_uf_stiff", "bga_depop",
             "attach_sparse", "attach_sparse_stiff"),
            {"du_c_um", "d_eps_in_per_cycle"}):
        items.append("<li><strong>Local construction</strong> determines the solder "
                     "response.</li>")
    return "".join(items)


def build(S, take, emit, S_appx=None):
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
      "Z2: hanging below the substrate, inside the hole in the board, with a 1 mm air gap "
      "to the board edge. Then trace the orange 48 V arrow in each: Z1 takes it up through "
      "the board's balls and the package; Z2 takes it straight into the regulator from "
      "below, through the opening (the connector drawn is illustrative). Then the purple "
      "1 V arrow: Z1 has a very short 1 V path; Z2 sends about 1000 A at 1 V up through "
      "the pillar attach and the TSV field. The grey balls around Z2's opening carry "
      "signals and hold the package down; they do not carry the 48 V. Everything else in "
      "the talk is a consequence of where that conversion happens.",
      "figs/z1_z2_package_comparison.svg — generated from research/final_closure/"
      "architecture_geometry.json (layer heights measured on the solver mesh)")

    # 7 ------------------------------------------------- A. where does 48 V go?
    led = {a: {r["term"]: r["P_w"] for r in (_case(a) or {}).get("ledger_rows", [])}
           for a in ("Z1", "Z2", "Z2BF")}
    ext = (_case("Z2") or {}).get("external_feed") or {}
    p48 = lambda a: sum(v for k, v in led[a].items() if k.startswith(("P_pkg_RDL_HV", "P_BGA_")))
    _rstar0 = (((J("direct_feed_crossover.json") or {}).get("scenarios") or {}).get("HV_S0")
               or {}).get("R_star_mohm") or 0.0
    t = "A. Where does the 48 V go?"
    S(f"""<h2>{t}</h2>
{naive("Z2 avoids sending its 48 V input through the package: the low-current, "
       "high-voltage supply enters the regulator directly through the PCB opening.")}
<div style="text-align:center">{fig(t, "figs/z1_z2_power_path_48v.svg",
    "48 V path only: Z1 through BGA + package RDL + TSVs; Z2 direct into the regulator",
    "48 V paths", "max-height:52vh;max-width:100%")}</div>
<div class="cols"><div><p><strong>Z1:</strong> board &rarr; 48 V BGA balls
({val(t, "matched balls", str(pn.get("matched_count")), "package_network.json", "matched_count")} per rail)
&rarr; package 48 V RDL &rarr; 48 V TSVs &rarr; regulator. Package 48 V loss at HV-S0:
<strong>{val(t, "Z1 pkg 48V W", f"{p48('Z1'):.2f} W", "etm_Z1_HV_S0_h1.1_r21.json", "ledger_rows")}</strong>.</p></div>
<div><p><strong>Z2:</strong> a dedicated external feed &rarr; regulator. No package 48 V
ball or RDL term exists; Z2's remaining BGA balls carry signals and hold the package to the
board. The feed itself is outside the package: every mΩ of loop costs
<strong>{val(t, "Z2 W per mOhm", f"{ext.get('P_feed_per_mohm_w', 0):.3f} W", "etm_Z2_HV_S0_h1.1_r21.json", "external_feed.P_feed_per_mohm_w")}</strong>
at HV-S0, so Z2's electrical advantage holds only while that loop stays below
R* = {val(t, "Rstar S0 arch", f"{_rstar0:.2f} mΩ", "direct_feed_crossover.json", "scenarios.HV_S0.R_star_mohm")}.</p></div></div>""",
      "This is the first half of the electrical story. Z1 pays for 48 V inside the package: "
      "balls, a copper sheet, vias. Z2 pays nothing inside the package for 48 V, but needs "
      "its own connection from the board to the regulator, and that connection's "
      "resistance is unknown — no source gives it. We do not invent one; the direct-feed slide turns it "
      "into a requirement.",
      "figs/z1_z2_power_path_48v.svg · etm_Z1/Z2_HV_S0_h1.1_r21.json ledger · "
      "z2_direct_feed_architecture.json")

    # 8 ------------------------------------------------- B. where does 1 V go?
    tsv = lambda a: led[a].get("P_TSV_VDD", 0.0) + led[a].get("P_TSV_GND", 0.0)
    att = led["Z2"].get("P_VR_attach_VDD", 0.0) + led["Z2"].get("P_VR_attach_GND", 0.0)
    t = "B. After conversion, where does the 1 V go?"
    S(f"""<h2>{t}</h2>
{naive("After conversion the voltage is only 1 V, so roughly 1 kA must travel the remaining "
       "few hundred microns — through many parallel TSVs in Z2.")}
<div style="text-align:center">{fig(t, "figs/z1_z2_power_path_1v.svg",
    "1 V path only: Z1 short output RDL; Z2 attach + 1 V TSVs + top RDL",
    "1 V paths", "max-height:52vh;max-width:100%")}</div>
<div class="cols"><div><p><strong>Z1:</strong> regulator &rarr; output RDL &rarr; microbumps
&rarr; die. Its TSV field carries 48 V at about 20 A in total:
{val(t, "Z1 TSV W", f"{tsv('Z1') * 1e3:.2f} mW", "etm_Z1_HV_S0_h1.1_r21.json", "ledger_rows")}.</p></div>
<div><p><strong>Z2:</strong> regulator &rarr; pillar attach &rarr; 1 V VDD + GND TSVs
&rarr; top RDL &rarr; die. At ~1 kA: attach
{val(t, "Z2 attach W", f"{att:.3f} W", "etm_Z2_HV_S0_h1.1_r21.json", "ledger_rows")},
TSV field {val(t, "Z2 TSV W", f"{tsv('Z2'):.3f} W", "etm_Z2_HV_S0_h1.1_r21.json", "ledger_rows")}.</p></div></div>""",
      "Second half. The same TSV field is in both packages, but it carries a different "
      "rail: 48 V and almost no current in Z1, 1 V and the full kiloampere in Z2. That is "
      "why the TSV count matters so much more for Z2 (TSV provisioning slide).",
      "figs/z1_z2_power_path_1v.svg · ledger rows of the production cases")

    # 9 ------------------------------------------------- the attach
    spec = (J("z2_direct_feed_architecture.json") or {}).get("vr_attach") or {}
    _att_study = J("vr_attach_density_study.json") or {}
    t = "The bridge: backside regulator to substrate"
    S(f"""<h2>{t}</h2>
{naive("These bumps or pillars are the electrical bridge between the backside regulator and "
       "the silicon package substrate.")}
<div class="cols" style="align-items:center"><div style="flex:1.65;text-align:center">
{fig(t, "figs/z2_vr_attach_detail.svg", "VR-to-substrate attach: VDD/GND Cu pillars + solder "
     "caps on the checkerboard, routed to the VDD/GND TSVs", "attach detail",
     "max-height:70vh;max-width:100%")}</div>
<div style="flex:.55"><table class="small">
<tr><td>height (Cu + cap)</td><td class='num'>{val(t, "h", f"{spec.get('h_total_um', 0):.0f} µm", "z2_direct_feed_architecture.json", "vr_attach.h_total_um")}
({spec.get('h_cu_um', 0):.0f} + {spec.get('h_cap_um', 0):.0f})</td></tr>
<tr><td>pillar / pitch</td><td class='num'>{spec.get('d_um', 0):.0f} / {spec.get('pitch_um', 0):.0f} µm</td></tr>
<tr><td>pillars per cell, VDD + GND</td><td class='num'>{val(t, "n", str(_att_study['cases']['dense']['n_vdd']), "vr_attach_density_study.json", "cases.dense.n_vdd")} + {_att_study['cases']['dense']['n_gnd']}</td></tr>
<tr><td>attach loss, HV-S0</td><td class='num'>{val(t, "attach W", f"{att:.3f} W", "etm_Z2_HV_S0_h1.1_r21.json", "ledger_rows")}</td></tr></table>
<p class="sub">Geometry: a published 30 µm-pitch Cu-pillar process (close analog, not
this design). Its density is an input of its own: a sparser published construction
(30 µm at 80 µm) is run against it (attach-density slide); 20/40 µm heights, all-solder
bumps and underfill corners are class-B variants.</p></div></div>""",
      "Before this correction the model glued the regulator straight onto the substrate. "
      "Now the joint is a real tier: pillars carry the current and heat, underfill carries "
      "the load. Its resistance enters the loss ledger and its height and material are "
      "tested as sensitivities.",
      "figs/z2_vr_attach_detail.svg · research/final_closure/z2_direct_feed_architecture.json")

    # 10 ---------------------------------------------------------------- one cell
    zoom = DECK / "figs" / "regulator_cell_zoom.svg"
    if zoom.exists():
        t = "Inside one regulator cell"
        S(f"""<h2>{t}</h2><div class="cols" style="align-items:center">
<div style="flex:1.3;text-align:center">{fig(t, "figs/regulator_cell_zoom.svg",
    "one regulator cell: tiers and components", "one regulator cell",
    "max-height:62vh;max-width:100%")}</div>
<div><p>48 V → 3:1 switched capacitor → 16 V → two-phase buck → 1 V.</p>
<p>Each of the 49 cells carries about 20 A at 1 V. The same 11 components and the same
tier heights are used in Z1 and Z2 — only location, feed, support and cooling differ.</p>
<p class="sub">The tier order is the order energy flows, not a series circuit: switch-node,
flying-capacitor, ground and phase connections run between non-adjacent tiers.</p></div>
</div>""", "Keep it short: the converter is identical in both architectures; this is a "
            "packaging comparison, not a converter comparison.",
          "figs/regulator_cell_zoom.svg — research/final_closure/architecture_geometry.json")
    else:
        emit(take("The converter inside each cell"))

    # 9 ---------------------------------------------------------------- pipeline
    emit(take("How one architecture is evaluated").replace("</h2>", "</h2>" + naive(
        "What does it take to turn one converter design into a temperature, a bend and a "
        "solder strain — for each architecture, the same way?"), 1))

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

    # 13 ------------------------------------------- Z1 package 48 V RDL vs MOOSE
    t = "Z1's package 48 V RDL: model vs MOOSE"
    ref = J("reference_pkg_rdl_moose_Z1.json") or {}
    r1 = A("pkg_rdl_Z1")
    nums = [("production R<sub>eff</sub> (Z1, supply)",
             val(t, "prod R_eff Z1", f"{ref.get('production_L3', {}).get('R_eff_ohm', 0) * 1e3:.4f} mΩ",
                 "reference_pkg_rdl_moose_Z1.json", "production_L3.R_eff_ohm")),
            ("MOOSE R<sub>eff</sub>, finest mesh",
             val(t, "moose R_eff Z1", f"{ref.get('moose', {}).get('m3', {}).get('R_eff_ohm', 0) * 1e3:.4f} mΩ",
                 "reference_pkg_rdl_moose_Z1.json", "moose.m3.R_eff_ohm")),
            ("difference", val(t, "err Z1", pct(r1.get("error") if r1 else None),
                               "accuracy_speed_matrix.json", "pkg_rdl_Z1.error")),
            ("production runtime", val(t, "rt prod Z1", rt(r1, "production"),
                                       "accuracy_speed_matrix.json", "pkg_rdl_Z1.production_runtime_s")),
            ("MOOSE runtime", val(t, "rt ref Z1", rt(r1, "reference"),
                                  "accuracy_speed_matrix.json", "pkg_rdl_Z1.reference_runtime_s"))]
    trs = "".join(f"<tr><td>{k}</td><td class='num'>{v}</td></tr>" for k, v in nums)
    S(f"""<h2>{t}</h2>
<div class="val" style="grid-template-columns:0.95fr 1.6fr 0.75fr">
<div class="col"><h3>What the solver sees</h3>{fig(t, "figs/rdl_model_explained_Z1.svg",
    "Z1 48 V sheet seen from above: balls feed it, 49 pads drain it", "model cartoon Z1")}</div>
<div class="col"><h3>MOOSE field — matched run</h3>{fig(t, "figs/rdl_reference_annotated_Z1.png",
    "MOOSE voltage field of the Z1 sheet, annotated overlay (data unchanged)", "MOOSE field Z1")}
<div class="toolcap">{intro("MOOSE")}</div></div>
<div class="col"><h3>Numbers</h3><table>{trs}</table>
<p class="sub">Only Z1 has this object. The direct-fed Z2 has no package 48 V sheet; the
BGA-fed control's sheet is checked the same way (appendix).</p></div>
</div>""", "The solver looks down on ONE copper layer: Z1's 48 V sheet between the BGA and the "
            "substrate. Balls feed it, the 49 regulator input pads drain it. The centre image "
            "is MOOSE's own solution of the same problem. This is a model-to-model check, not a "
            "measurement — and it says nothing about the primary Z2, which has no such sheet.",
          "research/final_closure/reference_pkg_rdl_moose_Z1.json · tool_evidence/pkg_rdl_moose_Z1/")
    if S_appx:
        ref2, r2 = J("reference_pkg_rdl_moose_Z2.json") or {}, A("pkg_rdl_Z2")
        t2 = "Appendix — the BGA-fed control's package 48 V RDL vs MOOSE"
        S_appx(f"""<h2>{t2}</h2><div class="cols"><div style="flex:1;text-align:center">
{fig(t2, "figs/rdl_model_explained_Z2.svg", "control: sheet, balls, pads, opening", "control sheet")}</div>
<div style="flex:1;text-align:center">{fig(t2, "figs/rdl_reference_annotated_Z2.png",
    "MOOSE field of the control sheet", "control MOOSE")}</div></div>
<p class="sub">Control geometry only (Z2_BGA_FED_CONTROL): production R<sub>eff</sub>
{val(t2, "prod R_eff ctrl", f"{ref2.get('production_L3', {}).get('R_eff_ohm', 0) * 1e3:.4f} mΩ", "reference_pkg_rdl_moose_Z2.json", "production_L3.R_eff_ohm")},
MOOSE {val(t2, "moose R_eff ctrl", f"{ref2.get('moose', {}).get('m3', {}).get('R_eff_ohm', 0) * 1e3:.4f} mΩ", "reference_pkg_rdl_moose_Z2.json", "moose.m3.R_eff_ohm")},
difference {val(t2, "err ctrl", pct(r2.get("error") if r2 else None), "accuracy_speed_matrix.json", "pkg_rdl_Z2.error")}.
Not evidence about the primary, direct-fed Z2.</p>""",
               "The same solver check on the opening geometry, which only the BGA-fed control "
               "uses. Balls can only sit outside the opening, so current flows inward.",
               "reference_pkg_rdl_moose_Z2.json · figs/rdl_model_explained_Z2.svg")

    # 14 ------------------------------------- C. what did the equal-BGA experiment test?
    sec = take("BGA current sharing").replace('src="figs/sharing.svg"',
                                                 'src="figs/ball_sharing.svg"')
    FIGS.append({"figure": "figs/ball_sharing.svg",
                 "slide": "C. What did the equal-BGA experiment test?",
                 "purpose": "solved per-ball current share, matched construction (control)"})
    ctrl = (J("control_results.json") or {}).get("cases") or {}
    cz1, cz2, cbf = (ctrl.get(k) or {} for k in ("Z1_HV_S0", "Z2_HV_S0", "Z2BF_HV_S0"))
    t = "C. What did the equal-BGA experiment test?"
    rel = lambda k: ((cbf[k] - cz2[k]) / cz2[k] if isinstance(cbf.get(k), (int, float))
                     and isinstance(cz2.get(k), (int, float)) else None)
    dl = (cbf.get("P_loss_w", 0) - cz2.get("P_loss_w", 0)) if cbf and cz2 else None
    mrel = [abs(x) for x in (rel("die_warpage_pv_um"), rel("du_c_um")) if x is not None]
    ctrl_txt = ((f"Feeding through the package costs Z2 {dl:.2f} W; " if dl is not None else "")
                + ("its warpage and joint driver change by less than "
                   f"{100 * max(mrel):.1f} %, so the mechanics follow the opening, not the 48 V "
                   "path." if mrel and max(mrel) < 0.02 else
                   "its mechanics change too (table)." if mrel else ""))
    rowsc = "".join(
        f"<tr><td>{lab}</td>" + "".join(
            f"<td class='num'>{val(t, f'{key} {lab}', fmt % c[key], 'control_results.json', f'cases.{case}.{key}') if isinstance(c.get(key), (int, float)) else 'n/a'}</td>"
            for key, fmt in (("P_loss_w", "%.2f W"), ("T_max_C", "%.1f °C"),
                             ("die_warpage_pv_um", "%.1f µm"), ("du_c_um", "%.3f µm")))
        + "</tr>" for lab, c, case in (("Z1 (BGA-fed)", cz1, "Z1_HV_S0"),
                                       ("Z2 direct-fed", cz2, "Z2_HV_S0"),
                                       ("Z2 BGA-fed control", cbf, "Z2BF_HV_S0")))
    S(f"""<h2>{t}</h2>
<p class="sub">A controlled experiment, not the primary Z2: both architectures are forced to take
48 V through the same package-level BGA injection
({val(t, "matched balls C", str(pn.get("matched_count")), "package_network.json", "matched_count")}
balls per rail), on the same corrected geometry.</p>
<div style="text-align:center">
{fig(t, "figs/ball_sharing.svg", "per-ball current share, solved", "ball sharing",
     "max-height:38vh;max-width:92%")}</div>
<div class="cols" style="align-items:flex-start"><div style="flex:1.1"><table class="small">
<tr><th></th><th>internal loss</th><th>T<sub>max</sub></th><th>warpage</th><th>joint driver</th></tr>
{rowsc}</table></div>
<div style="flex:1"><p class="sub">It isolates what the opening and the ball placement do: balls
must sit outside the opening, so current crowds inward. {ctrl_txt}</p></div></div>""",
      "This used to be the main Z1 vs Z2 comparison. It is now a control: we deliberately "
      "force the backside regulator to take its 48 V through the package, like Z1, to see "
      "what the opening and the ball placement cost. Compare the middle and bottom rows: "
      "same mechanics, different loss. That difference is the price of feeding through "
      "the package.",
      "research/final_closure/control_results.json · package_network.json")

    # 15 ------------------------------------------- Z2 direct-feed requirement
    cx = (J("direct_feed_crossover.json") or {}).get("scenarios") or {}
    lossv = (od.get("P_loss_package_internal_w") or {}).get("per_scenario", {})
    req, other = [], []
    for s_, c in cx.items():
        lab = s_.replace("_", "-")
        if c.get("Z1_operating_point_inadmissible"):
            other.append(f"{lab}: Z1 inadmissible, no comparison")
        elif c.get("R_star_mohm") and lossv.get(s_) == "Z2 lower":
            txt = val("Z2's direct feed: how much resistance can it afford?", f"R* {lab}",
                      f"{c['R_star_mohm']:.2f} mΩ", "direct_feed_crossover.json",
                      f"scenarios.{s_}.R_star_mohm")
            req.append(f"below <strong>{txt}</strong> at {lab}")
        elif c.get("R_star_mohm"):
            other.append(f"{lab}: Z2 ahead by {c['advantage_at_zero_feed_w']:.2f} W with a "
                         "lossless feed, inside the loss uncertainty — no resolved requirement")
        else:
            other.append(f"{lab}: Z2 not ahead even with a lossless feed — every mΩ only adds "
                         "loss")
    t = "Z2's direct feed: how much resistance can it afford?"
    S(f"""<h2>{t}</h2>
{naive("Z2's 48 V still has to reach the regulator through its own connection. How good must "
       "that connection be for Z2 to stay ahead?")}
<div style="text-align:center">{fig(t, "figs/direct_feed_crossover.svg",
    "Z2 platform loss vs the swept external feed resistance, Z1 as reference, R* marked",
    "direct-feed crossover", "max-height:56vh;max-width:100%")}</div>
<div class="callout">{("For Z2 to keep its electrical advantage the loop (supply + return, from the "
  "board node shared with Z1 to the 49 regulator inputs) must stay " + " and ".join(req) + ". ")
  if req else "No scenario leaves Z2 a resolved advantage to protect, so the feed sets no "
  "requirement. "}{"; ".join(other) + "." if other else ""} No source gives a real connector's
value, so R* is a <strong>requirement</strong>, never a result.</div>""",
      "Read the left panel: the blue line is Z1, fixed. The red curve is Z2 as the external "
      "feed gets worse; where they cross is R star. We do not claim either side of it, "
      "because nobody publishes this connector's resistance; the patent we cite names "
      "connector types only.",
      "research/final_closure/direct_feed_crossover.json · figs/direct_feed_crossover.svg")

    # 16 ------------------------------------------------ TSV provisioning
    t = "TSV provisioning decides the electrical preference"
    tsvrows, lossv = [], {}
    # verdicts by the uncertainty-aware ordering rule (ordering.json / classB rows), never
    # by comparing the raw numbers
    v_prod = (od.get("P_loss_package_internal_w") or {}).get("per_scenario", {}).get("HV_S0")
    v_var = {}
    for g in cb.get("gates", []):
        for r in g.get("rows", []):
            if (r.get("case") in ("tsv_min", "tsv_mid")
                    and r.get("observable") == "P_loss_package_internal_w"):
                v_var[r["case"]] = r.get("verdict")
    short = {"Z1 lower": "Z1 lower", "Z2 lower": "Z2 lower",
             "unresolved": "no ranking (within 2U)"}
    for v, nv in (("tsv_min", 64), ("tsv_mid", 729), (None, 1444)):
        cells_ = []
        for a in ("Z1", "Z2"):
            src = (f"sensitivity/etm_{a}_HV_S0__{v}.json" if v else
                   (_rows().get((a, "HV_S0")) or {}).get("case_file"))
            d = J(src) if src else None
            if d:
                lossv[(a, nv)] = d["P_loss_w"]
            cells_.append(val(t, f"{a} loss {nv}", f"{d['P_loss_w']:.2f} W", src, "P_loss_w")
                          if d else "n/a")
        vd = v_prod if v is None else v_var.get(v)
        tsvrows.append(f"<tr><td>{nv} vias per cell{' (production)' if v is None else ''}</td>"
                       f"<td class='num'>{cells_[0]}</td><td class='num'>{cells_[1]}</td>"
                       f"<td><strong>{short.get(vd, vd or 'n/a')}</strong></td></tr>")
    say = {"Z1 lower": "Z1 dissipates less inside the package",
           "Z2 lower": "Z2 dissipates less inside the package",
           "unresolved": "the package-internal losses are equal within the measured "
                         "uncertainty"}
    tsv_txt = "The production field is the densest that fits (1444 per cell)."
    if v_prod in say:
        tsv_txt += f" There {say[v_prod]}"
        if v_var.get("tsv_min") in say:
            tsv_txt += (f"; with the electrically minimal field (64 per cell) "
                        f"{say[v_var['tsv_min']]}")
        tsv_txt += "."
        if v_var.get("tsv_min") and v_var["tsv_min"] != v_prod:
            tsv_txt += (" The package-internal loss verdict therefore depends on how the TSVs "
                        "are provisioned (sensitivity slide).")
    S(f"""<h2>{t}</h2>
{naive("After conversion the voltage is only 1 V, so roughly 1 kA must cross the substrate. "
       "How many parallel vias does that take — and does it change which design wins?")}
<table style="font-size:1.15em"><tr><th>TSV field</th><th>Z1 internal loss (48 V vias)</th>
<th>Z2 internal loss (1 V vias)</th><th>verdict (HV-S0)</th></tr>
{''.join(tsvrows)}</table>
<p class="sub" style="margin-top:.6em">{tsv_txt}</p>""",
      "Same TSVs, different job. In Z1 they carry 48 V at 20 A total and cost nothing. In Z2 "
      "they carry 1000 A at 1 V. Starve them and Z2 loses its electrical edge.",
      "research/final_closure/sensitivity/etm_*_HV_S0__tsv_*.json · production case files")

    # 15 ------------------------------------------------------------- heat
    sec = take("The heat map")
    ploss = [r["P_loss_w"] for k, r in rows.items() if k[1] == "HV_S0"] if rows else []
    about = f"about {10 * round(sum(ploss) / len(ploss) / 10):.0f} W" if ploss else "the"
    emit(sec.replace("</h2>", "</h2>" + naive(f"Where is {about} of loss produced, and "
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
{naive("Can an independent commercial and an open-source solver reproduce our temperatures on "
       "the same piece of the package?")}
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

    # 17a ------------------------------------------------------ cooling vs Icepak
    t = "Cooling model vs Icepak (conjugate CFD)"
    ic = J("reference_cooling_icepak.json") or {}
    lvi = {k: v for k, v in (ic.get("levels") or {}).items() if v.get("solved")}
    fin = max(lvi, key=lambda k: lvi[k]["cells"]) if lvi else None
    ai = A("cooling_icepak")
    cbi = {}
    for g in cb.get("gates", []):
        for r in g.get("rows", []):
            if r.get("case") == "icepak_equivalent":
                cbi[r["observable"]] = r
    moved_i = [r["observable"] for r in cbi.values() if r.get("robust") is False]
    nums = [("compact correlation ΔT", val(t, "corr dT", f"{ic.get('correlation_dT_matched_loading_K', 0):.2f} K",
                                         "reference_cooling_icepak.json", "correlation_dT_matched_loading_K")),
            ("Icepak, finest mesh", val(t, "cfd dT", f"{lvi[fin]['dT_base_mean_K']:.2f} K" if fin else "n/a",
                                       "reference_cooling_icepak.json", f"levels.{fin}.dT_base_mean_K")),
            ("compact vs CFD", val(t, "ice err", pct(ai.get("error") if ai else None, 1),
                                   "accuracy_speed_matrix.json", "cooling_icepak.error")),
            ("CFD solve (4 cores)", val(t, "cfd rt", rt(ai, "reference"), "accuracy_speed_matrix.json",
                                        "cooling_icepak.reference_runtime_s")),
            ("compact evaluation", val(t, "corr rt", rt(ai, "production"), "accuracy_speed_matrix.json",
                                       "cooling_icepak.production_runtime_s"))]
    trs = "".join(f"<tr><td>{k}</td><td class='num'>{v}</td></tr>" for k, v in nums)
    S(f"""<h2>{t}</h2>
<div class="val" style="grid-template-columns:1.35fr 1fr">
<div class="col"><h3>Ansys Icepak — one channel half-pitch, matched load</h3>{fig(t,
    "tool_evidence/cooling_icepak/01_geometry.png", "real Icepak session export of the matched "
    "channel model", "Icepak model", "max-height:36vh;max-width:100%")}
<p class="sub">The modelled domain is half a fin (25 µm) plus half a channel (25 µm), with 300 µm
fins on a 100 µm silicon base, over the full 22.36 mm length — so the real session view is a
needle. Water at 25 °C, laminar, the same heat flux on the base as the compact model.</p>
<div class="toolcap">{intro("Ansys Icepak")}</div></div>
<div class="col"><h3>Numbers</h3><table>{trs}</table>
<p class="sub">The compact model is conservative. It is <strong>not</strong> recalibrated to
Icepak; the coefficient that would match it (×{(ic.get('correlation_dT_matched_loading_K', 0) / lvi[fin]['dT_base_mean_K']) if fin else 0:.3f})
is run as a class-B sensitivity on both architectures:
{"it moves the " + ", ".join(sorted(moved_i)) + " verdict" if moved_i else "it moves no ordering"}.</p></div></div>""",
      "The cold plate is a formula, not a CFD model. Here is the formula against a full "
      "conjugate CFD solve of one channel in Icepak at the same heat load: the formula "
      "overstates the temperature rise by about 16 percent, so it is on the safe side. We "
      "did not tune the formula to Icepak and call that validation; we ran the Icepak-"
      "matched cooling as a separate sensitivity instead. The formula takes microseconds, "
      "the CFD solve about twenty minutes on four cores.",
      "research/final_closure/reference_cooling_icepak.json · tool_evidence/cooling_icepak/ · "
      "classB_resolution.json")

    # 17 ------------------------------------------------------------- E-T fixed point
    emit(take("The electrothermal fixed point converges").replace("</h2>", "</h2>" + naive(
        "Heat raises copper resistance, which raises the loss, which raises the heat: does "
        "that loop settle, and where?"), 1).replace(
        'src="figs/final_et_convergence.svg"', 'src="figs/et_convergence.svg"'))
    FIGS.append({"figure": "figs/et_convergence.svg", "slide": "E-T fixed point",
                 "purpose": "peak temperature and iteration change against the tolerance"})

    # 18 ------------------------------------------------------------- why warp + Z1/Z2
    t = "Why packages warp — and what Z1 and Z2 actually do"
    S(f"""<h2>{t}</h2>
{naive("Moving and cooling the regulator changes which materials expand together, so an "
       "electrically better architecture can become mechanically worse — or vice versa.")}
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
{naive("Does our bending model get the textbook two-layer strip right — the same answer as the "
       "closed form and as Ansys?")}
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
    emit(take("Where is the critical joint").replace("</h2>", "</h2>" + naive(
        "Which of the hundreds of solder balls is pushed sideways the most? We search every "
        "one instead of assuming the corner."), 1).replace('src="figs/final_joint_map.svg"',
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

    # (appendix) ---------------------------------------------- closure changed
    t = "Appendix — What physical closure changed"
    (S_appx or S)(f"""<h2>{t}</h2>
<table><tr><th>before closure</th><th>after closure</th><th>effect</th></tr>
<tr><td>BGA current shared equally — an input</td><td>voltage-fed network: the sharing is solved</td>
<td>ball count becomes a solved design variable</td></tr>
<tr><td>Z2 converter as a full-area slab</td><td>49 physical cells in the PCB opening</td>
<td>geometry is the architecture being claimed</td></tr>
<tr><td>Z2 fed through peripheral package balls and a 48 V RDL</td><td>direct 48 V feed into the
regulator (construction precedent: ARM US20260059645A1)</td><td>the BGA-fed Z2 becomes a control
experiment; the feed becomes a requirement R*</td></tr>
<tr><td>Z2 regulator touching the substrate</td><td>explicit 30 µm Cu-pillar attach tier</td>
<td>its resistance, conductivity and stiffness enter the model</td></tr>
<tr><td>Z2 converter bonded to the board sidewall (DEFECT #66)</td><td>1 mm void clearance, as
specified</td><td>the sidewall-filled case is a sensitivity</td></tr>
<tr><td>RDL tier conductivity from a series formula</td><td>explicit RVE in Ansys</td>
<td>through-thickness k was 12.5 % too high</td></tr>
<tr><td>earlier mechanical ranking</td><td>physical lineage</td>
<td>the mechanical ordering reversed</td></tr></table>""",
      "Physical closure changed answers, including the architecture ordering and the way "
      "the backside regulator is fed.",
      "Z2_DIRECT_FEED_ARCHITECTURE.md · research/final_closure/README.md")

    # 24 ------------------------------------------------------------- S0 result
    t = "HV-S0 result (headline scenario)"
    s0 = sc.get("HV_S0", {})
    cx0 = ((J("direct_feed_crossover.json") or {}).get("scenarios") or {}).get("HV_S0") or {}
    r0 = _rows()
    z1i = (r0.get(("Z1", "HV_S0")) or {}).get("P_loss_package_internal_w")
    z2i = (r0.get(("Z2", "HV_S0")) or {}).get("P_loss_package_internal_w")
    iv0 = (od.get("P_loss_package_internal_w") or {}).get("per_scenario", {}).get("HV_S0", "")
    u0 = ((od.get("P_loss_package_internal_w") or {}).get("uncertainty_rel") or {}).get("HV_S0")
    internal_txt = (f"<strong>Package-internal loss:</strong> Z2 "
                    f"{val(t, 'Z2 internal', f'{z2i:.2f} W', 'control_results.json', 'cases.Z2_HV_S0.P_loss_w')} "
                    f"vs Z1 {val(t, 'Z1 internal', f'{z1i:.2f} W', 'control_results.json', 'cases.Z1_HV_S0.P_loss_w')}, "
                    f"about {abs(z1i - z2i):.1f} W apart against a resolution limit (2U) of "
                    f"{2 * u0 * max(z1i, z2i):.1f} W"
                    + ((": Z2 lower, narrowly." if abs(z1i - z2i) < 1.25 * 2 * u0 * max(z1i, z2i)
                        else ": Z2 lower.") if iv0 == "Z2 lower" else
                       ": Z1 lower." if iv0 == "Z1 lower" else
                       ": no ranking.")) if z1i and z2i and u0 else ""
    rs = cx0.get("R_star_mohm")
    platform_txt = ((f"<strong>Platform loss:</strong> conditional &mdash; Z2 keeps the advantage "
                     f"only while its complete 48 V feed loop stays below R* = "
                     f"{val(t, 'Rstar S0', f'{rs:.2f} mΩ', 'direct_feed_crossover.json', 'scenarios.HV_S0.R_star_mohm')}"
                     " (direct-feed slide); above it Z1 is lower.") if rs else
                    "<strong>Platform loss:</strong> Z2 is not ahead even with a lossless feed.")
    ppm0 = cx0.get("P_feed_per_mohm_w", 0.0)
    strip = ((f"<div style='display:flex;gap:.5em;justify-content:center;margin-top:.35em;"
              f"font-size:.9em'><span class='chip ok'>external feed loop below R* = "
              f"{val(t, 'Rstar S0 strip', f'{rs:.2f} mΩ', 'direct_feed_crossover.json', 'scenarios.HV_S0.R_star_mohm')}"
              f": Z2 lower, platform-inclusive</span><span class='chip open'>above R*: Z1 lower "
              f"&mdash; each mΩ of loop costs "
              f"{val(t, 'W per mOhm S0', f'{ppm0:.3f} W', 'direct_feed_crossover.json', 'scenarios.HV_S0.P_feed_per_mohm_w')}"
              f"</span></div>") if rs else "")
    S(f"""<h2>{t}</h2>
<div style="text-align:center">{fig(t, "figs/s0_cards.svg",
    "five observables, Z1 vs Z2, with uncertainty and verdict", "S0 cards",
    "max-height:46vh;max-width:100%")}</div>
<div class="callout" style="margin-top:.3em">{internal_txt}<br>{platform_txt}<br>
{od.get("T_max_C", {}).get("statement", "")}</div>{strip}
<p class="sub">A ranking is claimed only where the Z1/Z2 gap exceeds <strong>twice the measured
discretisation uncertainty</strong>; otherwise "no ranking". The unknown external feed is
never treated as lossless.</p>""",
      "Read the verdict line under each card, not the bars. Package-internal loss: "
      + {"Z1 lower": "Z1 lower", "Z2 lower": "Z2 about 1 W lower"}.get(
          iv0, "no ranking — the difference is inside the measured uncertainty")
      + "; platform loss: conditional on the direct feed (R* above); " + "; ".join(
          f"{nm}: " + ({"Z1 lower": "Z1 lower", "Z2 lower": "Z2 lower"}.get(
              (od.get(k) or {}).get("per_scenario", {}).get("HV_S0", ""),
              "no ranking — the difference is inside the measured uncertainty"))
          for k, nm in (("T_max_C", "Peak temperature"),
                        ("die_warpage_pv_um", "Warpage"), ("du_c_um", "Joint driver"),
                        ("d_eps_in_per_cycle", "Local response"))) + ".",
      "figs/s0_cards.svg — final_results.json · ordering.json · direct_feed_crossover.json")

    # 25 ------------------------------------------------------------- scenarios
    t = "Appendix — Scenario robustness"
    st = " ".join(sc[s]["statement"] for s in ("HV_S1", "HV_S2") if s in sc)
    (S_appx or S)(f"""<h2>{t}</h2>
<div style="text-align:center">{fig(t, "figs/scenario_small_multiples.svg",
    "small multiples across HV-S0/S1/S2 with scenario classes", "scenario small multiples",
    "max-height:58vh;max-width:100%")}</div>
<p class="sub">{st} {od.get("d_eps_in_per_cycle", {}).get("statement", "")}</p>""",
      "HV-S0 is the headline, HV-S1 a sensitivity, HV-S2 a stress case. The statements "
      "under the chart are generated from ordering.json: they name which joints are "
      "extrapolated beyond the constitutive calibration and which operating points are "
      "inadmissible (hollow squares), where no comparison is drawn.",
      "figs/scenario_small_multiples.svg — final_results.json · ordering.json")

    # 26 ------------------------------------------------------------- class B
    t = "Which neighbouring decisions reverse a ranking?"
    sm = cb.get("summary") or {}
    order = ["tsv_min", "tsv_mid", "f2_void", "f1_sidewall_filled", "z2_cooled", "z2_cooled_tim",
             "icepak_equivalent", "feed_heat_at_crossover", "attach_h20", "attach_h40",
             "attach_sn", "attach_dense", "attach_sparse", "attach_sparse_stiff",
             "attach_stiff", "attach_uf_soft", "attach_uf_stiff", "bga_depop",
             "board_h1", "board_t3p2", "board_eta025", "board_eta075", "gan_k_half",
             "conv_k_tenth", "conv_E80_a4", "conv_E80_a10", "conv_E160_a4", "conv_E160_a10",
             "pad_drop"]
    name = {"board_h1": "board as five depth blocks (H1)", "board_t3p2": "board 3.2 mm (2.4)",
            "board_eta025": "board copper coverage 0.25 (0.50)",
            "board_eta075": "board copper coverage 0.75 (0.50)",
            "tsv_mid": "TSV field 729/cell (1444)", "tsv_min": "TSV field 64/cell (1444)",
            "f1_sidewall_filled": "Z2: opening filled to the board sidewall (1 mm void)",
            "f2_void": "void between cells (encapsulated)",
            "z2_cooled": "Z2: cold plate under the converter",
            "z2_cooled_tim": "Z2: that plate behind a 50 µm TIM",
            "icepak_equivalent": "Icepak-matched cooling coefficient",
            "feed_heat_at_crossover": "Z2: feed loss at the largest R* deposited in the package",
            "attach_h20": "Z2 attach 20 µm (30)", "attach_h40": "Z2 attach 40 µm (30)",
            "attach_sn": "Z2 attach: all-Sn bound, 30 µm at 80 µm",
            "attach_dense": "Z2 attach 15/30 µm on the real lattice (smeared card)",
            "attach_sparse": "Z2 attach 30/80 µm, published (15/30)",
            "attach_sparse_stiff": "Z2 attach 30/80 µm, column-stiffened card",
            "attach_stiff": "Z2 attach: column-stiffened card",
            "attach_uf_soft": "Z2 attach underfill 4 GPa, 40 ppm/K",
            "attach_uf_stiff": "Z2 attach underfill 12 GPa, 20 ppm/K",
            "bga_depop": "Z2 BGA field 420/528 sites",
            "gan_k_half": "GaN tiers at k/2 (bound)",
            "conv_k_tenth": "converter tiers at k/10 (bound)",
            "conv_E80_a4": "converter medium 80 GPa, 4 ppm/K",
            "conv_E80_a10": "converter medium 80 GPa, 10 ppm/K",
            "conv_E160_a4": "converter medium 160 GPa, 4 ppm/K",
            "conv_E160_a10": "converter medium 160 GPa, 10 ppm/K",
            "pad_drop": "1 V pads at the drop floor (2040)",
            "board_h0_h1grid": "board H0 card on the five-block grid (control)"}
    cols = (("P_loss_package_internal_w", "internal loss"), ("T_max_C", "peak T"),
            ("die_warpage_pv_um", "warpage"),
            ("du_c_um", "joint driver"), ("d_eps_in_per_cycle", "local"))
    by = {}
    for g in cb.get("gates", []):
        if g.get("method") != "runs":
            continue
        for r in g.get("rows", []):
            if r.get("robust") is None:     # H1 vs H0 on one grid: a material effect, no verdict
                continue
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
    trs, holds = [], []
    for c in order + sorted(set(by) - set(order)):
        if c not in by:
            continue
        if all(r.get("robust") for r in by[c].values()):
            holds.append(name.get(c, c.replace("_", " ")))
            continue
        mx = max((abs(x) for r in by[c].values()
                  for x in (r.get("change_rel") or {}).values()
                  if isinstance(x, (int, float))), default=None)
        trs.append(f"<tr><td>{name.get(c, c)}</td>" + "".join(cell(by[c].get(k)) for k, _ in cols)
                   + (f"<td class='num'>{100 * mx:.0f} %</td>" if mx is not None else "<td></td>")
                   + "</tr>")
    if holds:
        trs.append(f"<tr><td colspan='{len(cols) + 2}' class='sub'><span class='chip ok'>every "
                   f"ordering holds</span> under: {'; '.join(holds)}</td></tr>")
    head = "".join(f"<th>{lab}</th>" for _, lab in cols)
    S(f"""<h2>{t}</h2>
<p class="sub">{sm.get('n_gates', 0)} open inputs: {sm.get('b1_total', 0)} could move an ordering
(B1), {(sm.get('subtypes') or {}).get('B2', 0)} only a magnitude (B2); {sm.get('b1_resolved', 0)}
of the B1 resolved. Each variant is run on the production mesh at HV-S0 and judged by the
production rule. The reversals are the result: they name what a ranking depends on. The feed
resistance is the requirement on the direct-feed slide.</p>
<div style="max-height:62vh;overflow:hidden"><table class="small" style="font-size:.58em">
<tr><th>input changed (production value)</th>{head}<th>largest change</th></tr>
{''.join(trs)}</table></div>""",
      "Read across a row: green means that ordering survives the change; red says what it "
      "becomes. " + _mech_moves(cb) + ". " + (
          "The local response is not ranked even in production: its discretisation bound "
          "exceeds the gap, so a variant can create a local ranking but never reverse one."
          if (od.get("d_eps_in_per_cycle") or {}).get("per_scenario", {}).get("HV_S0")
          == "unresolved" else
          "The local ordering is resolved only beyond twice its bound in production; it is "
          "the one most exposed to a neighbouring decision."),
      "research/final_closure/classB_resolution.csv")

    # 26b ---------------------------------------------------------- attach density
    t = "The tiny connection that can change the architecture result"
    lc = (((cb.get("attach_density_crossover") or {}).get("crossover") or {})
          .get("P_loss_package_internal_w") or {})
    sp_rows = by.get("attach_sparse", {})
    adr = ((((J("direct_feed_crossover.json") or {}).get("scenarios") or {}).get("HV_S0") or {})
           .get("attach_density_R_star") or {})
    vtx = {"Z1 lower": "Z1 lower", "Z2 lower": "Z2 lower", "unresolved": "no ranking",
           "not rankable": "n/a"}
    res = "; ".join(f"{lab} {vtx.get(sp_rows[k]['verdict'], sp_rows[k]['verdict'])}"
                    for k, lab in cols if k in sp_rows)
    lines = [f"<strong>Sparser published attach, HV-S0:</strong> {res}." if res else ""]
    _ast = J("vr_attach_density_study.json") or {}
    e_d, e_s = ((((_ast.get("cases") or {}).get(c) or {}).get("etm_S0") or {})
                for c in ("dense", "sparse"))
    if e_d.get("P_conv_w") is not None and e_s.get("P_conv_w") is not None:
        lines.append(
            "<strong>Coupled solution:</strong> Z2's package-internal loss rises by "
            + val(t, "attach dP etm", f"{e_s['P_Z2_internal_w'] - e_d['P_Z2_internal_w']:.2f} W",
                  "vr_attach_density_study.json", "cases.sparse.etm_S0.P_Z2_internal_w")
            + f", of which the attach itself is only "
            f"{e_s['P_attach_total_w'] - e_d['P_attach_total_w']:.2f} W: the converter runs "
            f"{e_s['T_conv_C'] - e_d['T_conv_C']:.1f} K warmer because less metal carries its "
            "heat into the substrate.")
    if lc.get("f_star"):
        fs_ = 100 * lc["f_star"]
        ps_ = lc.get("pitch_star_um_d15")
        lines.append(
            "<strong>Where the internal-loss ranking stops</strong> (engineering sweep, not a "
            "manufacturing geometry): Z2 stays lower above about "
            + val(t, "f star", f"{fs_:.1f} %", "classB_resolution.json",
                  "attach_density_crossover.crossover.P_loss_package_internal_w.f_star")
            + " metal" + (f" (about {ps_:.1f} µm pitch for 15 µm pillars)" if ps_ else "")
            + "; below it, no ranking" + ("" if lc.get("reversal") else ", and no published "
                                          "density reverses it") + ".")
    elif lc.get("status", "").startswith("holds"):
        lines.append("<strong>Internal loss:</strong> the ranking holds at every swept density "
                     "down to the sparser published construction.")
    rd, rsp = ((adr.get(k) or {}).get("R_star_mohm") for k in ("dense", "sparse"))
    if rd and rsp:
        lines.append("<strong>Platform requirement:</strong> R* = "
                     + val(t, "Rstar dense", f"{rd:.2f} mΩ", "direct_feed_crossover.json",
                           "scenarios.HV_S0.attach_density_R_star.dense.R_star_mohm")
                     + " with the dense attach, "
                     + val(t, "Rstar sparse", f"{rsp:.2f} mΩ", "direct_feed_crossover.json",
                           "scenarios.HV_S0.attach_density_R_star.sparse.R_star_mohm")
                     + " with the sparse one.")
    S(f"""<h2>{t}</h2>
<div style="text-align:center">{fig(t, "figs/z2_attach_density.svg",
    "dense vs sparse published attach in plan at one scale, and what density changes",
    "attach density", "max-height:52vh;max-width:100%")}</div>
<div class="callout" style="margin-top:.3em;font-size:.8em">{'<br>'.join(x for x in lines if x)}</div>""",
      "Both lattices are published constructions, and the material and height are held, so "
      "only the density changes. Fewer bumps raise the attach resistance; fewer metal "
      "columns conduct less heat downward; a different metal fraction changes how stiff the "
      "layer can be, which we bound rather than claim. The current per bump is reported, "
      "never checked against an allowable. "
      + ("Read the verdicts: the attach density alone decides whether the internal-loss "
         "ranking is resolved." if (sp_rows.get("P_loss_package_internal_w") or {}).get(
             "robust") is False else
         "Read the verdicts: the internal-loss ranking survives even the sparse attach."),
      "figs/z2_attach_density.svg — vr_attach_density_study.json · classB_resolution.json · "
      "direct_feed_crossover.json")

    # 27 ------------------------------------------------------------- accuracy / runtime
    t = "Accuracy and runtime, stage by stage"
    take(t)                       # the legacy one-chart version is superseded by this slide
    S(f"""<h2>{t}</h2><div style="text-align:center">{fig(t, "figs/accuracy_runtime_split.svg",
    "closed-form vs FE (log) and FE vs FE (linear) kept apart", "accuracy and runtime",
    "max-height:64vh;max-width:100%")}</div>""",
      "Two different claims, two panels. Top: closed forms and the compact cooling "
      "correlation evaluate in microseconds, the matched commercial or CFD solve takes "
      "seconds to about twenty minutes — that is model reduction, so only the two times "
      "are shown, never a ratio. Bottom: production field solvers against reference field "
      "solvers on the same problem and machine, as a runtime ratio. No end-to-end speedup "
      "is claimed.",
      "figs/accuracy_runtime_split.svg — accuracy_speed_matrix.json")

    # 28 ------------------------------------------------------------- claims
    t = "What we can claim — and what we cannot"
    # one line per observable, read from ordering.json's per-scenario verdicts (the full
    # statements, with their reasons, are on slides 24-25 and in the paper)
    can = []
    for k, nm in (("P_loss_package_internal_w", "Package-internal loss"),
                  ("T_max_C", "Peak temperature"),
                  ("die_warpage_pv_um", "Die warpage"), ("du_c_um", "Joint driver"),
                  ("d_eps_in_per_cycle", "Local response")):
        won = {}
        for s_, v in (od.get(k) or {}).get("per_scenario", {}).items():
            if v.endswith("lower"):
                won.setdefault(v.split()[0], []).append(s_.replace("_", "-"))
        if won:
            can.append(f"{nm}: " + "; ".join(f"{a} lower in {' and '.join(ss)}"
                                             for a, ss in won.items()))
        if k == "P_loss_package_internal_w":
            # the platform loss is conditional on Z2's unsourced feed: never one winner
            rs = (od.get("P_loss_platform_inclusive_w") or {}).get("R_star_mohm") or {}
            cond = [f"{s_.replace('_', '-')} below R* = {v:.2f} mΩ" for s_, v in rs.items()
                    if v and (od.get("P_loss_platform_inclusive_w") or {}).get(
                        "per_scenario", {}).get(s_, "").startswith("conditional")]
            if cond:
                can.append("Platform loss: conditional — Z2 lower only " + "; ".join(cond)
                           + " (complete direct-feed loop)")
    plain = {"board_t3p2": "a 3.2 mm board", "board_eta025": "board copper coverage 0.25",
             "board_eta075": "board copper coverage 0.75",
             "tsv_mid": "a 729-via TSV field", "gan_k_half": "GaN tiers at half conductivity",
             "pad_drop": "the minimum pad count",
             "tsv_min": "the electrically minimal TSV field (64 vias/cell)",
             "f2_void": "void instead of encapsulated space between the cells",
             "f1_sidewall_filled": "the Z2 opening filled to the board sidewall",
             "conv_k_tenth": "a tenfold lower converter-tier conductivity",
             "z2_cooled": "a cold plate under the Z2 converter",
             "z2_cooled_tim": "that cold plate behind a 50 µm TIM",
             "icepak_equivalent": "the Icepak-matched cooling coefficient",
             "feed_heat_at_crossover": "the feed loss at the largest R* deposited in the package",
             "attach_h20": "a 20 µm attach", "attach_h40": "a 40 µm attach",
             "attach_sn": "all-Sn attach bumps", "attach_stiff": "a column-stiffened attach",
             "attach_dense": "the dense attach on its real lattice",
             "attach_sparse": "the sparser published attach (30 µm at 80 µm)",
             "attach_sparse_stiff": "that sparser attach with a column-stiffened card",
             "attach_uf_soft": "a soft attach underfill",
             "attach_uf_stiff": "a stiff attach underfill",
             "bga_depop": "a depopulated Z2 BGA field",
             "board_h1": "the five-block board model"}
    obs = {"P_loss_package_internal_w": "package-internal loss",
           "P_loss_platform_inclusive_w": "platform-inclusive loss",
           "T_max_C": "peak temperature", "die_warpage_pv_um": "warpage",
           "du_c_um": "joint driver", "d_eps_in_per_cycle": "local response"}
    # single-input rows only, as in the manuscript (the converter-rescaling threshold has no
    # production verdict and is stated in the decision report). A REVERSAL flips a resolved
    # verdict to the other architecture; every other change only withdraws a ranking.
    rev, unres, made = {}, {}, {}
    for g in cb.get("gates", []):
        for r in g.get("rows", []):
            pv, av = r.get("production_verdict"), r.get("verdict", "")
            if r.get("robust") is not False or pv is None:
                continue
            o = obs.get(r["observable"], r["observable"])
            # a case can serve several gates: each entry is listed once (dict as ordered set)
            if pv.endswith("lower") and av.endswith("lower"):
                rev.setdefault(r["case"], {})[f"{o}: {pv} → {av}"] = None
            elif pv.endswith("lower"):
                unres.setdefault(o, {})[case_plain(plain, r["case"])] = None
            else:                                   # no production ranking; one appears
                made.setdefault(o, {})[f"{case_plain(plain, r['case'])} ({av})"] = None
    revs = "".join(f"<li>{case_plain(plain, c)} — {'; '.join(sorted(v))}</li>"
                   for c, v in rev.items())

    def grouped(names):
        """The package 48 V RDL thickness/occupancy corners are one input: name them once."""
        rdl = [n for n in names if "package 48 V RDL" in n]
        rest = [n for n in names if "package 48 V RDL" not in n]
        return rest + ([f"{len(rdl)} package 48 V RDL thickness/occupancy corners"]
                       if len(rdl) > 1 else rdl)
    unr = "".join(f"<li>{o}: {'; '.join(grouped(list(v)))}</li>" for o, v in unres.items())
    mk = "".join(f"<li>{o}: {'; '.join(v)}</li>" for o, v in made.items())
    therm0 = (od.get("T_max_C") or {}).get("per_scenario", {}).get("HV_S0")
    S(f"""<h2>{t}</h2><div class="cols"><div><h3>Can claim (production model; each gap &gt; 2U)</h3><ul>
{''.join(f'<li>{c}</li>' for c in can)}</ul>
{('<h3>Reversed by one neighbouring decision</h3><ul class="sub" style="font-size:.8em">' + revs + '</ul>') if revs else ''}</div>
<div><h3>Cannot claim</h3><ul>
{"<li>a thermal ranking at HV-S0 (inside the measured uncertainty);</li>"
 if therm0 == "unresolved" else ""}
{''.join(f"<li>any ordering under {s.replace('_', '-')}: {' and '.join(c['inadmissible'])} "
         "leaves the valid solid-solder domain there;</li>"
         for s, c in sc.items() if c.get("inadmissible"))}
<li>any absolute solder life (response only — Darveaux);</li>
<li>the 48 V waveform (results are scenario-conditioned);</li>
<li>a value for Z2's direct-feed loop resistance (it is a requirement, R*);</li>
<li>an electromigration-safe current density, or a qualified attach;</li>
<li>a commercial end-to-end speedup;</li>
<li>any statement about which architecture a company uses or should use.</li></ul>
{('<h3>Left unresolved by</h3><ul class="sub" style="font-size:.8em">' + unr + '</ul>') if unr else ''}
{('<h3>Ranked only under</h3><ul class="sub" style="font-size:.8em">' + mk + '</ul>') if mk else ''}</div></div>""",
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
        fut.append("TSV density as a co-design variable: the HV-S0 package-internal loss "
                   "ordering depends on it;")
    if "attach_sparse" in moved:
        fut.append("a qualified attach process of known density: the HV-S0 package-internal "
                   "ranking depends on it;")
    fut.append("the Icepak conjugate-CFD check extended from one channel to the full cold "
               "plate;" if ice_done else
               "an Icepak conjugate-CFD check of the cold-plate correlation;")
    fut += ["qualified electromigration and fatigue data, for absolute reliability "
            "statements;", "a full-package commercial FE benchmark beyond the unit cell."]
    S(f"""<h2>{t}</h2><div class="cols"><div><h3>Contributions</h3><ol>
<li>A hierarchical electrothermal–mechanical framework for DVPD in which converter synthesis
propagates into an explicit physical package, evaluated in one lineage.</li>
<li>Both architectures closed physically: Z1's package 48 V network solved (BGA count as a
design variable); Z2 direct-fed, with an explicit pillar attach and the specified sidewall
clearance, and its unsourced feed turned into a requirement R*.</li>
<li>Stage-by-stage checks against commercial and open-source FEM and a conjugate CFD, with
model-specific errors and runtimes instead of one framework accuracy.</li>
<li>Convergence and sensitivity rules declared before results were read; every ordering is
gated by measured uncertainty.</li>
<li>The reversals as a result: which neighbouring decisions an architecture ranking depends
on.</li></ol></div>
<div><h3>Future work</h3><ul>{''.join(f'<li>{x}</li>' for x in fut)}</ul></div></div>""",
      "End on contribution 5. Each future-work item replaces a declared assumption or a "
      "scenario with data; none is needed for the comparison itself.", "")

    # 31 ------------------------------------------------------------ the thesis
    t = "The thesis in one sentence"
    S(f"""<h2>{t}</h2>
<div class="big" style="font-size:1.5em;line-height:1.35;margin-top:.6em">Physically closing the
architectures shows that no architecture can be ranked independently of its neighbouring
design decisions.</div>
<ul style="margin-top:1.1em">{thesis_items(cb)}</ul>
<p class="sub" style="margin-top:.8em">So an architecture-level decision needs a coupled
electrothermal–mechanical framework — the nominal results are on the HV-S0 slide, the conditions on
the sensitivity slide.</p>""",
      "This is the one sentence to remember. Each bullet is backed by a result in this talk; "
      "a bullet appears only if its artifact supports it.",
      "classB_resolution.json · direct_feed_crossover.json · ordering.json")
    emit(take("Thank you"))
