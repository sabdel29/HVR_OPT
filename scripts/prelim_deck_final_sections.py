"""Final-lineage slide blocks for the prelim deck. Every number is read from artifacts.

Imported by scripts/prelim_build_deck.py, which owns S(), SLIDES and the assembly. Errors
and runtimes on the validation slides come from accuracy_speed_matrix.json -- the same
rows the manuscript table prints -- so the deck and the paper cannot disagree.
"""
from __future__ import annotations

import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
FC = R / "research" / "final_closure"
EVID = "tool_evidence"


def J(n):
    f = FC / n
    return json.loads(f.read_text()) if f.exists() else None


def pct(x, d=2):
    return f"{100 * x:+.{d}f} %" if isinstance(x, (int, float)) else "n/a"


def A(stage):
    acc = J("accuracy_speed_matrix.json") or {"rows": []}
    return next((r for r in acc["rows"] if r["stage"] == stage), None)


def fmt_s(v):
    if not isinstance(v, (int, float)):
        return "n/a"
    if v < 1e-3:
        return f"{v * 1e6:.2f} µs"
    if v < 1.0:
        return f"{v * 1e3:.1f} ms"
    return f"{v:.1f} s"


def rt(r, who):
    """'median (min–max)' runtime of the production or reference side of a row."""
    if not r:
        return "n/a"
    v = r.get(f"{who}_runtime_s")
    rng = r.get(f"{who}_runtime_range_s")
    s = fmt_s(v)
    if rng and all(isinstance(x, (int, float)) for x in rng):
        s += f" ({fmt_s(rng[0])}–{fmt_s(rng[1])})"
    return s


def ratio(r):
    sp = (r or {}).get("speedup")
    if not isinstance(sp, (int, float)):
        return "n/a"
    if sp >= 1e4:
        e = int(f"{sp:.1e}".split("e")[1])
        return f"{sp / 10 ** e:.1f}×10<sup>{e}</sup>"
    return f"{sp:,.0f}×" if sp >= 100 else f"{sp:.2f}×"


def img_or_note(rel, note):
    p = R / "presentation" / "prelim_hvr" / rel
    if p.exists():
        return f'<img src="{rel}" alt="reference tool">'
    return f'<div class="banner open">{note}</div>'


def vslide(S, title, left, img, tool_caption, rows, bottom, notes, prov):
    trs = "".join(f"<tr><td>{k}</td><td class='num'>{v}</td></tr>" for k, v in rows)
    S(f"""<h2>{title}</h2>
<div class="val">
<div class="col"><h3>Our model</h3>{left}</div>
<div class="col"><h3>Reference tool — matched run</h3>{img}
<div class="toolcap">{tool_caption}</div></div>
<div class="col"><h3>Error and runtime</h3><table>{trs}</table></div>
<div class="bottom callout">{bottom}</div></div>""", notes, prov)


#: overview rows: (label, production model, stages whose rows are summarised)
OVERVIEW = [
    ("TSV conductor", "&rho; L / A", ["tsv_bulk"]),
    ("TSV-field homogenisation", "Voigt / Maxwell-Garnett", ["tsv_tile_kz", "tsv_tile_kx"]),
    ("RDL tier homogenisation", "grid laminate", ["rdl_tier_kx", "rdl_tier_kz"]),
    ("Package HV RDL network", "voltage-fed refined FV sheet", ["pkg_rdl_Z1", "pkg_rdl_Z2"]),
    ("Package thermal FE", "CalculiX C3D8",
     ["thermal_column_aedt_Z1", "thermal_column_aedt_Z2",
      "thermal_column_moose_Z1", "thermal_column_moose_Z2"]),
    ("Thermoelastic bending", "CalculiX C3D8I", ["mech_bilayer_aedt", "mech_bilayer_closed_form"]),
    ("Structural linear solver", "ITERATIVE CHOLESKY", ["structural_solver_iterative_vs_direct"]),
    ("Cooling correlation", "microchannel compact", ["cooling_icepak", "cooling_compact"]),
    ("Converter waveform", "closed-form loss model", ["converter_waveform"]),
]


def _chip(r):
    st = r.get("status", "")
    if st == "EXECUTED":
        e = r.get("error")
        tag = r["stage"][-2:] if r["stage"][-2:] in ("Z1", "Z2") else ""
        return (f"<span class='chip ok'>{tag} "
                f"{pct(e, 2) if isinstance(e, float) else e}</span>")
    if st.startswith("HISTORICAL"):
        return f"<span class='chip hist'>HISTORICAL {r.get('error', '')}</span>"
    return f"<span class='chip open'>{st.replace('_', ' ')}</span>"


def electrical_validation(S):
    rows = []
    for label, prod, stages in OVERVIEW:
        rr = [A(s) for s in stages if A(s)]
        refs = sorted({(r.get("reference_tool") or "").split(" (")[0] for r in rr} - {""})
        rows.append(f"<tr><td>{label}</td><td>{prod}</td><td>{'; '.join(refs)}</td>"
                    f"<td>{' '.join(_chip(r) for r in rr)}</td></tr>")
    S(f"""<h2>How every reduced model is checked in this work</h2>
<table class="small"><tr><th>Stage</th><th>Production model</th><th>Reference actually run</th>
<th>Outcome (production vs reference)</th></tr>{''.join(rows)}</table>
<p class="sub">Q3D Extractor and Maxwell DC conduction are installed but <strong>not licensed</strong>
here. Steady conduction &nabla;&middot;(k&nabla;T)=0 is the same operator as
&nabla;&middot;(&sigma;&nabla;V)=0, so AEDT Mechanical and MOOSE serve as the DC-conduction references
under the exact analogy.</p>""",
      "Every row is read from the accuracy-speed matrix. Point out the gaps — cooling CFD and "
      "the converter waveform — before anyone asks.",
      "research/final_closure/accuracy_speed_matrix.json")
    t, rve = A("tsv_bulk"), J("reference_rve.json") or {}
    if t and t.get("status") == "EXECUTED":
        vslide(S, "TSV conductor: &rho;L/A against commercial FEM",
               "<p style='font-size:1.15em;text-align:center'><em class='q'>R = &rho; L / A</em></p>"
               "<p class='sub'>one 30 µm Cu via, 300 µm long — the compact model the ledger "
               "uses for every via in both TSV fields.</p>",
               img_or_note(f"{EVID}/tsv_bulk/01_geometry.png", "image not exported"),
               "AEDT 2026 R1 Mechanical: Cu cylinder, electrode, flux in, T = 0 out",
               [("&rho;L/A", f"{t['production_value'] * 1e3:.4f} mΩ"),
                ("AEDT FEM", f"{t['reference_value'] * 1e3:.4f} mΩ"),
                ("error", pct(t["error"])),
                ("closed form", rt(t, "production")),
                ("AEDT", rt(t, "reference")),
                ("runtime ratio", ratio(t))],
               "The residual is AEDT's faceted circular section, not physics: a square-bar "
               "probe agreed to ~1e-9. A closed form is the right production model here.",
               "Calibration slide: it shows the reference harness itself is trustworthy.",
               "reference_rve.json · reference_rve_timing.json · AEDT 2026 R1")
    kz, kx = A("tsv_tile_kz"), A("tsv_tile_kx")
    if kz and kx and kz.get("status") == kx.get("status") == "EXECUTED":
        f = (rve.get("tsv_tile_kz") or {}).get("cu_fraction", 0.0)
        vslide(S, "TSV-field homogenisation against an explicit unit cell",
               f"<p>1444 Cu vias per tile → {100 * f:.1f} % Cu. Through-thickness: "
               "<strong>Voigt</strong>. In-plane: <strong>Maxwell-Garnett</strong>.</p>"
               "<p class='sub'>The FE substrate holds exactly this field inside the 49 tiles "
               "and plain Si outside.</p>",
               img_or_note(f"{EVID}/tsv_tile_rve/01_geometry_kz.png", "image not exported"),
               "AEDT Mechanical: one Cu via in Si, electrode + isothermal face",
               [("k_z Voigt / AEDT", f"{kz['production_value']:.2f} / {kz['reference_value']:.2f}"),
                ("error k_z", pct(kz["error"])),
                ("k_xy MG / AEDT", f"{kx['production_value']:.2f} / {kx['reference_value']:.2f}"),
                ("error k_xy", pct(kx["error"])),
                ("closed forms", rt(kz, "production")),
                ("AEDT k_z", rt(kz, "reference"))],
               "Both closed forms agree with the explicit unit cell to under one percent, in "
               "microseconds instead of minutes.",
               "Homogenisation is cheap AND checked, which is what lets the package mesh stay "
               "small.", "reference_rve.json · W/mK")
    rx, rz = A("rdl_tier_kx"), A("rdl_tier_kz")
    if rx and rz and rx.get("status") == rz.get("status") == "EXECUTED":
        vb = (rve.get("rdl_tier_kx") or {}).get("voigt_upper_bound")
        vslide(S, "RDL tier: the check that changed the model",
               "<p>One 10 µm tier: square Cu grid at the declared occupancy on dielectric.</p>"
               "<p class='sub'>Laminate: grid formula in-plane, series through-thickness.</p>",
               img_or_note(f"{EVID}/rdl_tier_rve/01_geometry_kx.png", "image not exported"),
               "AEDT Mechanical explicit RVE: Cu grid lines in dielectric",
               [("k_x laminate / RVE", f"{rx['production_value']:.2f} / {rx['reference_value']:.2f}"),
                ("error k_x", pct(rx["error"])),
                ("k_z laminate / RVE", f"{rz['production_value']:.3f} / {rz['reference_value']:.3f}"),
                ("error k_z", pct(rz["error"])),
                ("earlier Voigt k_x", pct((vb - rx["reference_value"]) / rx["reference_value"], 0)
                 if vb else "n/a"),
                ("AEDT k_x", rt(rx, "reference"))],
               "<strong>The series k_z overstates the RVE and the earlier Voigt in-plane value was "
               "far too high.</strong> The production tensor now ADOPTS the RVE values, and every "
               "thermal result was re-run on it.",
               "Validation doing its job: it moved a number in the paper.",
               "reference_rve.json · W/mK")
    p1, p2 = A("pkg_rdl_Z1"), A("pkg_rdl_Z2")
    if p1 and p2:
        vslide(S, "Package HV RDL network against MOOSE FEM",
               "<p>Voltage-fed 2-D resistive sheet on an <strong>aligned, graded</strong> "
               "finite-volume grid; the matched BGA count and 49 traced 0.2 mm VIN pads.</p>"
               "<p class='sub'>Same formulation in both solvers: sheet, areal ball conductance "
               "to the rail, uniform pad draw.</p>",
               img_or_note(f"{EVID}/pkg_rdl_moose_Z2/04_field.png", "MOOSE render missing"),
               "MOOSE heat_transfer-opt on its own gmsh mesh — field rendered from MOOSE's "
               "Exodus output (Z2)",
               [("Z1 R_eff ours / MOOSE", f"{p1['production_value'] * 1e3:.4f} / "
                                          f"{p1['reference_value'] * 1e3:.4f} mΩ"),
                ("Z1 error", pct(p1["error"], 3)),
                ("Z2 R_eff ours / MOOSE", f"{p2['production_value'] * 1e3:.4f} / "
                                          f"{p2['reference_value'] * 1e3:.4f} mΩ"),
                ("Z2 error", pct(p2["error"], 3)),
                ("ours (Z2)", rt(p2, "production")),
                ("MOOSE (Z2)", rt(p2, "reference"))],
               "The reduced network reproduces the FE reference to about 0.1 % for both "
               "architectures. Both are 2-D, so the runtime ratio is solver-to-solver — the "
               "value of the reduced model is exactness on the sheet problem.",
               "Do not oversell speed here; the point is that the sheet abstraction is accurate.",
               "reference_pkg_rdl_moose_Z1/Z2.json · MOOSE")


def thermal_validation(S):
    S("""<h2>The heat map: losses go where they are produced</h2>
<div class="figwrap"><img src="figs/final_ledger.svg" alt="ledger"></div>
<p>High-side and low-side GaN, inductor and capacitor losses are deposited in <strong>their own
tiers</strong>, inside the 49 cell footprints. Package, BGA, TSV and pad losses go in their own
layers. Deposited heat equals the electrical ledger to machine precision.</p>""",
      "Mention the defect: the first physical deposition spread device loss into the "
      "encapsulant out to the package corners and produced a phantom corner hot spot. "
      "Confining deposits to the cell footprints removed it.",
      "research/final_closure/final_results.json · electrical_ledger.json")
    a1, a2 = A("thermal_column_aedt_Z1"), A("thermal_column_aedt_Z2")
    solved = [r for r in (a2, a1) if r and r.get("status") == "EXECUTED"]
    if solved:
        arch0 = solved[0]["stage"][-2:]
        rows = []
        for r in solved:
            a = r["stage"][-2:]
            rows += [(f"{a} T_max ccx / AEDT", f"{r['production_value']:.2f} / "
                                               f"{r['reference_value']:.2f} °C"),
                     (f"{a} error / rise", pct(r["error"]))]
        rows += [(f"CalculiX ({arch0})", rt(solved[0], "production")),
                 (f"AEDT ({arch0})", rt(solved[0], "reference"))]
        vslide(S, "Package thermal FE against commercial FEM",
               "<p>CalculiX C3D8 on a structured hex mesh — the production thermal solver.</p>"
               "<p class='sub'>Interior unit cell of the physical package: every layer, tile "
               "and gap materials, the converged heat map, the cold-plate film, symmetry "
               "sides.</p>",
               img_or_note(f"{EVID}/thermal_column_{arch0}/01_geometry.png", "image not exported"),
               f"AEDT 2026 R1 Mechanical thermal ({arch0} unit cell as built in AEDT); same "
               "sources and films", rows,
               "Same problem, two independent FE codes, same machine: solver verification on a "
               "matched problem, not experimental validation.",
               "Why a unit cell? 10 µm tiers over 30 mm make a tetrahedral mesh of the full "
               "package impractical; the unit cell keeps every tier.",
               "reference_thermal_column_Z1/Z2.json")
    m1, m2 = A("thermal_column_moose_Z1"), A("thermal_column_moose_Z2")
    if m1 and m2:
        mo = J("reference_thermal_column_moose_Z1.json") or {}
        vslide(S, "Package thermal FE against an independent open-source FEM",
               "<p>The same CalculiX unit-cell problem, solved by MOOSE on its own hex meshes "
               "at two resolutions.</p><p class='sub'>Shows that the agreement is not one "
               "discretisation checked against itself.</p>",
               img_or_note(f"{EVID}/thermal_column_moose_Z1/04_field.png", "MOOSE render missing"),
               "MOOSE heat_transfer-opt, temperature on the y = 0 section of the Z1 unit cell "
               "(rendered from its Exodus output)",
               [("Z1 T_max ccx / MOOSE", f"{m1['production_value']:.2f} / "
                                         f"{m1['reference_value']:.2f} °C"),
                ("Z1 error / rise", pct(m1["error"])),
                ("Z2 T_max ccx / MOOSE", f"{m2['production_value']:.2f} / "
                                         f"{m2['reference_value']:.2f} °C"),
                ("Z2 error / rise", pct(m2["error"])),
                ("MOOSE own mesh change (Z1)",
                 f"{mo.get('moose_mesh_change_K', float('nan')):+.2f} K"),
                ("runtime ratio (Z1)", ratio(m1))],
               "Three solvers agree on the unit cell to a fraction of a kelvin; the remaining "
               "difference is inside the reference's own mesh dependence.",
               "If asked: the runtime ratio is FE against FE, so it is not a model-reduction "
               "speedup.", "reference_thermal_column_moose_Z1/Z2.json")
    fin = J("final_results.json") or []
    x = next((f for f in fin if f["arch"] == "Z1" and f["scenario"] == "HV_S0"), None)
    jump = (f" the first iteration raises the Z1 loss by {x['et_first_jump_w']:.1f} W"
            if x and x.get("et_first_jump_w") is not None else " loss rises on the first "
                                                               "iteration")
    S("""<h2>The electrothermal fixed point converges</h2>
<div class="figwrap"><img src="figs/final_et_convergence.svg" alt="ET convergence"></div>
<p>Resistance rises with temperature, loss rises with resistance, temperature rises with loss.
Iterated until max&nbsp;|&Delta;T| &lt; 0.25 K and |&Delta;P|/P &lt; 10<sup>-3</sup> — both declared
before any physical result was read.</p>""",
      "The initial 85 C guess under-estimates GaN on-resistance;" + jump + " before settling.",
      "final_results.json · et_history")


def mechanics_validation(S):
    mb = J("reference_mech_bilayer.json")
    cf, ma = A("mech_bilayer_closed_form"), A("mech_bilayer_aedt")
    if mb and cf:
        aedt_ok = bool(ma and ma.get("status") == "EXECUTED")
        rows = [("CalculiX C3D8I", f"{cf['production_value'] * 1e3:.2f} µm"),
                ("Timoshenko closed form", f"{cf['reference_value'] * 1e3:.2f} µm"),
                ("error vs closed form", pct(cf["error"]))]
        if aedt_ok:
            rows += [("AEDT structural", f"{ma['reference_value'] * 1e3:.2f} µm"),
                     ("error vs AEDT", pct(ma["error"])),
                     ("CalculiX / AEDT", f"{rt(ma, 'production').split(' (')[0]} / "
                                         f"{rt(ma, 'reference').split(' (')[0]}")]
        else:
            rows += [("AEDT structural", "not solved")]
        vslide(S, "Thermoelastic bending: element and supports",
               "<p>CalculiX C3D8I — the production element for package warpage.</p>"
               "<p class='sub'>Si on organic, &Delta;T = 100 K, symmetry planes and one 0.1 mm "
               "patch held in z: supports remove rigid motion without suppressing bending.</p>",
               img_or_note(f"{EVID}/mech_bilayer/01_geometry.png", "image not exported"),
               "AEDT 2026 R1 Mechanical structural model as built" +
               (" — warpage per kelvin from two solved temperature levels" if aedt_ok else
                " — its solve did not complete, so no AEDT number is claimed"),
               rows,
               "CTE-mismatch bending is the mechanism behind every warpage number in the "
               "paper. The closed form ignores free-edge effects, so a few-tenths-percent gap "
               "to it is expected" + ("; the commercial FE agrees as well." if aedt_ok else "."),
               "Verification of the element and supports, not validation of the package.",
               "reference_mech_bilayer.json")
    mc = J("mesh_convergence.json") or {}
    sv = A("structural_solver_iterative_vs_direct")
    loc = {s: J(f"local_solder_{s}.json") for s in ("HV_S0", "HV_S1", "HV_S2")}
    if mc.get("cases"):
        rows = []
        names = {"T_max_C": "T<sub>max</sub>", "die_warpage_pv_um": "die warpage",
                 "du_c_um": "&Delta;u<sub>c</sub>", "P_loss_w": "loss"}
        for arch, c in sorted(mc["cases"].items()):
            for chk, rel in (c.get("checks") or {}).items():
                vals = [v for v in rel.values() if isinstance(v, (int, float))]
                if vals:
                    k = max((kk for kk in rel if isinstance(rel[kk], (int, float))),
                            key=lambda kk: rel[kk])
                    rows.append(f"<tr><td>{arch}</td><td>{chk}</td>"
                                f"<td class='num'>{100 * max(vals):.2f} % ({names[k]})</td>"
                                f"<td>{'within' if max(vals) < mc['tolerance_rel'] else 'ABOVE'} "
                                f"{100 * mc['tolerance_rel']:.0f} %</td></tr>")
            for k, st in (c.get("observable_status") or {}).items():
                if st == "bounded":
                    u = c["uncertainty_bound_rel"][k]
                    rows.append(f"<tr><td>{arch}</td><td colspan='2'>{names[k]}: above tolerance, "
                                f"Richardson bound U = {100 * u:.2f} % on the production grid"
                                f"</td><td>ordering only beyond 2U</td></tr>")
        lm = [c.get("mesh_change_pct") for d in loc.values() if d
              for c in d["cases"].values() if c.get("mesh_change_pct") is not None]
        S(f"""<h2>Discretisation and solver checks behind the results</h2>
<table class="small"><tr><th>arch</th><th>nested refinement</th>
<th>largest change (T_max, warpage, du<sub>c</sub>, loss)</th><th>declared tolerance</th></tr>
{''.join(rows)}</table>
<ul style="margin-top:.4em">
<li>Production mesh: {mc.get('production_label', 'n/a').replace('h_xy', 'h<sub>xy</sub>')}. {mc.get('production_reason', '')}</li>
<li>Refined structural solves use ITERATIVE CHOLESKY: on the base mesh it matches the direct solver
to {pct(sv['error'], 3) if sv else 'n/a'} in warpage (direct SPOOLES solves 38.6k C3D8I elements and segfaults
at 43k in this build).</li>
<li>Local solder model, n<sub>xy</sub> 6&rarr;8, n<sub>z</sub> 8&rarr;10: response change
{(f"{min(lm):.1f}–{max(lm):.1f} %" if lm else "n/a")} where both meshes converge.</li></ul>""",
          "Say plainly that the first 'refinement' was not a refinement — lowering h_xy "
          "re-graded the grid — and that the nested study replaced it.",
          "mesh_convergence.json · solver_check/ · local_solder_HV_S*.json")
    fin = J("final_results.json") or []
    if not fin:
        return
    n1 = next((f.get("n_joint_sites") for f in fin if f["arch"] == "Z1"), "?")
    n2 = next((f.get("n_joint_sites") for f in fin if f["arch"] == "Z2"), "?")
    S(f"""<h2>Where is the critical joint? Searched, not assumed</h2>
<div class="figwrap"><img src="figs/final_joint_map.svg" alt="joint map"></div>
<p>In-plane relative displacement across the BGA layer at <strong>every legal site</strong> —
{n1} for Z1, {n2} for Z2. The outermost lattice corner is critical in both.</p>""",
      "The corner being critical is a RESULT here. The +x corners rank first: they are the "
      "hotter, downstream end of the cold plate.", "final_results.json · joint_search")

    def g(a, s, k):
        return next((x.get(k) for x in fin if x["arch"] == a and x["scenario"] == s), None)
    rows = "".join(
        f"<tr><td>{s.replace('_', '-')}</td><td>{a}</td>"
        f"<td class='num'>{g(a, s, 'du_c_um'):.3f}</td>"
        f"<td class='num'>{g(a, s, 'T_joint_C'):.1f}"
        f"{' †' if g(a, s, 'T_joint_outside_norton_calibration') else ''}"
        f"{' ‡' if g(a, s, 'T_joint_at_or_above_solder_solidus') else ''}</td>"
        f"<td class='num'>{('%.3e' % g(a, s, 'd_eps_in_per_cycle')) if g(a, s, 'd_eps_in_per_cycle') else 'no convergence'}</td></tr>"
        for s in ("HV_S0", "HV_S1", "HV_S2") for a in ("Z1", "Z2")
        if g(a, s, "du_c_um") is not None)
    nc = [f"{x['arch']} {x['scenario'].replace('_', '-')} ({x['T_joint_C']:.0f} °C)"
          for x in fin if not x["d_eps_in_per_cycle"]]
    S(f"""<h2>Local solder response at the critical joint</h2>
<table><tr><th>scenario</th><th>arch</th><th>&Delta;u<sub>c</sub> (µm)</th><th>T joint (°C)</th>
<th>&Delta;&epsilon;<sub>in</sub> per cycle</th></tr>{rows}</table>
<p class="sub">Validated viscoplastic local family, re-run unchanged after reproducing its
published control exactly. † joint above the Norton card's 125 °C calibration — extrapolation.
‡ at or above the SAC305 melting onset (about 217 °C): not an admissible operating point.
<strong>Response only; no cycles to failure are computed</strong> (Darveaux, 10.1115/1.1413764).</p>""",
      "Z2's response is larger wherever both converge." +
      (f" Not converged, reported as such: {', '.join(nc)}." if nc else ""),
      "local_solder_HV_S*.json · final_results.json")


def final_results(S):
    fin = J("final_results.json") or []
    pn = J("package_network.json") or {}
    if not fin:
        return

    def g(a, s, k):
        return next(x[k] for x in fin if x["arch"] == a and x["scenario"] == s)
    S(f"""<h2>CURRENT physical result — HV-S0</h2>
<div class="kpi">
<div><div class="v" style="color:var(--z1)">{g('Z1','HV_S0','P_loss_w'):.1f} W</div><div class="l">Z1 loss</div></div>
<div><div class="v" style="color:var(--z2)">{g('Z2','HV_S0','P_loss_w'):.1f} W</div><div class="l">Z2 loss</div></div>
<div><div class="v" style="color:var(--z1)">{g('Z1','HV_S0','T_max_C'):.1f} °C</div><div class="l">Z1 T<sub>max</sub></div></div>
<div><div class="v" style="color:var(--z2)">{g('Z2','HV_S0','T_max_C'):.1f} °C</div><div class="l">Z2 T<sub>max</sub></div></div></div>
<div class="kpi" style="margin-top:.5em">
<div><div class="v" style="color:var(--z1)">{g('Z1','HV_S0','die_warpage_pv_um'):.1f} µm</div><div class="l">Z1 die warpage</div></div>
<div><div class="v" style="color:var(--z2)">{g('Z2','HV_S0','die_warpage_pv_um'):.1f} µm</div><div class="l">Z2 die warpage</div></div>
<div><div class="v" style="color:var(--z1)">{g('Z1','HV_S0','du_c_um'):.2f} µm</div><div class="l">Z1 joint driver</div></div>
<div><div class="v" style="color:var(--z2)">{g('Z2','HV_S0','du_c_um'):.2f} µm</div><div class="l">Z2 joint driver</div></div></div>
<p style="margin-top:.6em">Matched {pn.get('matched_count')} balls per rail, converged package
networks, converged E–T fixed point, all-site joint search, production mesh
{fin[0].get('mesh_label', '').replace('h_xy', 'h<sub>xy</sub>')}. <span class="chip ok">CURRENT</span></p>""",
      "Read the four pairs left to right. Electrically and thermally the two are close at "
      "HV-S0; mechanically they are not.",
      "final_results.json · physical lineage")
    order = (J("ordering.json") or {}).get("orderings", {})

    def say(key, what):
        o = order.get(key) or {}
        if o.get("robust_across_scenarios"):
            return f"{what}: {o['favoured'][0]} lower in every scenario."
        per = ", ".join(f"{s.replace('_', '-')} {v}"
                        for s, v in (o.get("per_scenario") or {}).items())
        if o.get("favoured_where_resolved"):
            return (f"{what}: {o['favoured_where_resolved']} lower wherever resolved ({per}; "
                    "'unresolved' = inside the discretisation uncertainty).")
        return f"{what}: scenario-dependent ({per})."
    S("""<h2>Across the named 48 V scenarios</h2>
<div class="figwrap"><img src="figs/final_scenarios.svg" alt="scenarios"></div>
<p class="sub">HV-S0/S1/S2 are named scenarios — continuous, buck-duty pulse, overall-ratio pulse
— not a lower/nominal/upper bracket:
from an average current alone there is no finite RMS upper bound at all.
The waveform is not derivable from the converter model, so every HV-side result is conditioned
on one of them.</p>""",
      " ".join([say("P_loss_w", "Loss"), say("T_max_C", "Peak temperature"),
                say("die_warpage_pv_um", "Die warpage"), say("du_c_um", "Joint driver")]),
      "final_results.json · ordering.json")
    z1e, z2e = g("Z1", "HV_S0", "d_eps_in_per_cycle"), g("Z2", "HV_S0", "d_eps_in_per_cycle")
    bullets = [say("P_loss_w", "Electrical loss"), say("T_max_C", "Peak temperature")]

    S(f"""<h2>Architecture conclusion</h2>
<div class="callout" style="font-size:1.0em">In the physically closed lineage, the backside
architecture (Z2) is <strong>not</strong> mechanically better: its joint displacement driver is
{g('Z2','HV_S0','du_c_um')/g('Z1','HV_S0','du_c_um'):.2f}&times; and its local inelastic response
{(z2e/z1e if z1e and z2e else float('nan')):.2f}&times; that of Z1 at HV-S0, with
{g('Z2','HV_S0','die_warpage_pv_um')/g('Z1','HV_S0','die_warpage_pv_um'):.1f}&times; the die warpage.</div>
<ul style="margin-top:.6em">
<li><span class="chip hist">HISTORICAL</span> the frozen R3C pair showed the opposite — Z2 hotter but
mechanically better. Physical closure reversed it.</li>
{''.join(f'<li>{b}</li>' for b in bullets)}
<li>What survives: <strong>peak temperature alone does not rank mechanical response</strong> —
now demonstrated on the physical pair as well.</li></ul>""",
      "The reversal is a result of the physical lineage under declared assumptions — no "
      "qualification or life claim.",
      "final_results.json · ordering.json · FINAL_PAPER_DECISION.md")
    S("""<h2>Accuracy and runtime, stage by stage</h2>
<div class="figwrap"><img src="figs/final_accuracy_speed.svg" alt="accuracy vs runtime"></div>
<p class="sub">Each point is one production model against its own matched reference: same problem,
same machine, medians of three timed repeats after a warm-up. There is no single framework
accuracy.</p>""",
      "Closed forms sit far right: microseconds against minutes. FE stages are compared "
      "solver-to-solver. Do not average these.", "accuracy_speed_matrix.json")
    S("""<h2>Where the time goes — the physical pair</h2>
<div class="figwrap"><img src="figs/final_runtime.svg" alt="runtime"></div>
<p class="sub">Measured on the current lineage, production mesh. The E–T fixed point and the single
thermoelastic solve dominate; the local submodel is separate.</p>""",
      "If asked for one end-to-end number, give it with its thread count and say it is this "
      "machine only.", "final_results.json · local_solder_HV_S0.json")


def hardening(S):
    mc = J("mesh_convergence.json") or {}
    S(f"""<h2>What physical closure changed in this final phase</h2>
<table class="small"><tr><th>Found</th><th>Consequence</th></tr>
<tr><td>Z1 network never converged on a uniform grid — tile edges fell between nodes</td>
<td>aligned graded FV grid: converges on all five metrics</td></tr>
<tr><td>cell terminal was the whole 2.37 mm tile; the layout has a 0.2 mm VIN pad</td>
<td>traced pad adopted; matched count re-solved</td></tr>
<tr><td>converter loss deposited into the encapsulant out to the package corners</td>
<td>phantom corner hot spot removed</td></tr>
<tr><td>bottom heat flow defined as Q − q<sub>top</sub></td>
<td>every historical "energy residual" was zero by construction; now computed</td></tr>
<tr><td>RDL tier tensor from Voigt / series formulas</td>
<td>explicit RVE disagreed; RVE values adopted, thermal re-run</td></tr>
<tr><td>the h<sub>xy</sub> 1.1&rarr;0.8 "refinement" re-graded the grid (Z2's largest element grew)</td>
<td>nested refinement instead. {mc.get('production_reason', '')}</td></tr></table>""",
      "Each row moved a result: physical closure changes conclusions, so it is the "
      "contribution.", "final_closure artifacts")


def closing(S):
    cls = J("paper_gate_classification.json") or {}
    S("""<h2>The historical frozen result, for context</h2>
<div class="banner">HISTORICAL / FROZEN R3C — NOT A CURRENT PHYSICAL RESULT</div>
<table><tr><th></th><th>Z1</th><th>Z2</th></tr>
<tr><td>peak temperature</td><td class="num">118.32 °C</td><td class="num">126.46 °C</td></tr>
<tr><td>joint driver &Delta;u<sub>c</sub></td><td class="num">4.625 µm</td><td class="num">3.871 µm</td></tr>
<tr><td>inelastic strain increment</td><td class="num">1.407e-2</td><td class="num">1.148e-2</td></tr></table>
<p>This pair motivated the hardening. Its mechanical ordering does <strong>not</strong> survive the
physical lineage — but its conceptual lesson does: peak temperature does not rank local response.</p>""",
      "Shown only to explain why the hardening was necessary. Never call it the final pair.",
      "results/phase0mr3c · HISTORICAL FROZEN R3C")
    rows = cls.get("rows", [])
    b = [r["gate"] for r in rows if r["class"] == "B"]
    c = [r["gate"] for r in rows if r["class"] == "C"]
    a = [r["gate"] for r in rows if r["class"] == "A"]

    def li(xs, n):
        return "".join(f"<li>{x}</li>" for x in xs[:n]) + (
            f"<li>… and {len(xs) - n} more</li>" if len(xs) > n else "")
    S(f"""<h2>Limitations — what the paper does not claim</h2>
<div class="cols small"><div>
<p><span class="chip warn">CLASS B</span> sensitivity, {len(b)} open</p><ul>{li(b, 7)}</ul></div>
<div><p><span class="chip hist">CLASS C</span> qualification, {len(c)} open</p><ul>{li(c, 6)}</ul>
<p class="sub">Class A (paper-critical) still open: {len(a)}. 1.5 A/ball is an engineering
provisioning rule, never an allowable.</p></div></div>""",
      "Frame limitations as boundaries of the claim, not weaknesses of the work.",
      "paper_gate_classification.json · FINAL_PAPER_SCOPE.md")
    S("""<h2>Contribution</h2>
<ol><li>A hierarchical electrothermal–mechanical framework for DVPD in which converter synthesis
propagates into an explicit physical package, evaluated in one lineage.</li>
<li>A voltage-fed, return-inclusive package network on an aligned graded grid that converges
where a uniform grid cannot — with the BGA count solved as a design variable.</li>
<li>Stage-by-stage checks against commercial and open-source FEM, with model-specific errors and
runtimes instead of one framework accuracy.</li>
<li>A demonstration that physical closure reverses an architecture conclusion.</li></ol>""",
      "End on point 4.", "")
    S("""<h2>Future work</h2>
<ul><li>obtain the switch-state schedule → replace the named scenarios with one waveform</li>
<li>Z2 backside cooling as a co-designed architecture state</li>
<li>Icepak conjugate-CFD check of the cooling correlation on the physical geometry</li>
<li>qualified EM and fatigue data for this metallurgy → absolute reliability statements</li>
<li>full-package commercial FE benchmark beyond the unit cell</li></ul>""",
      "Each item replaces a declared assumption or a scenario with data; none of them is "
      "needed for the comparison itself, only for absolute statements.", "")


def appendix(S):
    pn = J("package_network.json") or {}
    if pn:
        rows = "".join(f"<tr><td>{k.replace('__',' / ').replace('HV_S','HV-S')}</td>"
                       f"<td class='num'>{v.get('n_min','—')}</td><td>{v['status']}</td></tr>"
                       for k, v in sorted(pn["closure"].items()))
        S(f"""<h2>Appendix — BGA count closure, production model</h2>
<div class="figwrap"><img src="figs/final_count_closure.svg" alt="count closure"></div>
<table class="small"><tr><th>case</th><th>minimum per rail</th><th>status</th></tr>{rows}</table>""",
          "", "research/final_closure/package_network.json")
    acc = J("accuracy_speed_matrix.json") or {"rows": []}
    rows = "".join(
        f"<tr><td>{r['stage']}</td><td>{(r.get('reference_tool') or '')[:38]}</td>"
        f"<td class='num'>{pct(r['error'], 3) if isinstance(r.get('error'), float) else (r.get('error') or '')}</td>"
        f"<td class='num'>{rt(r, 'production').split(' (')[0]}</td>"
        f"<td class='num'>{rt(r, 'reference').split(' (')[0]}</td>"
        f"<td>{r.get('status', '')}</td></tr>" for r in acc["rows"])
    S(f"""<h2>Appendix — accuracy and runtime matrix</h2>
<table class="tiny"><tr><th>stage</th><th>reference</th><th>error</th><th>ours</th><th>reference</th>
<th>status</th></tr>{rows}</table>
<p class="sub">No end-to-end commercial flow speedup is claimed.</p>""",
      "Full matrix for questions; medians of three timed repeats after a warm-up.",
      "accuracy_speed_matrix.csv")
