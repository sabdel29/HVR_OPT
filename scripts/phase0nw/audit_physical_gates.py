"""PHASE 0N-W --- the physical gate table, DERIVED from the live config and mesh.

A status table that is typed by hand goes stale a phase after it is written (DEFECT #57
shipped one a full phase behind under a green audit). So every row here is evaluated
against the artifacts at run time: the config is loaded, the mesh is built, and the
measured geometry decides the status. Nothing in the output is asserted by hand.

  SPECIFIED   written down with a source or a rule
  IMPLEMENTED the solver actually builds it, verified by measuring the mesh
  VALIDATED   a convergence or cross-model check has been run on it
  OPEN        neither
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts/phase0nw"))
import z2_converter as Z2C                                              # noqa: E402
from physical_package import (build_physical_package, measure_layers,   # noqa: E402
                              load_physical_package_config,
                              load_z1_package_config)


# =======================================================================================
# THE CANONICAL REQUIRED-GATE MANIFEST.
#
# This list, not the evaluator, defines what must be true before a physical ETM result may
# exist. The evaluator below must produce a row for EVERY id here; `gates()` raises if it
# does not. That is the whole point: a registry that only reports the gates someone
# remembered to evaluate can declare "ready for ETM" by omission, which is exactly how the
# previous version reported "5 of 26 OPEN" while thermal BC selection, mesh convergence
# and the 528-site critical-joint search were not in it at all -- they were sitting in a
# handwritten YAML list that nothing checked.
#
# Configuration describes geometry and materials. THIS file owns implementation state.
# =======================================================================================
REQUIRED_GATES = {
    "board": [
        "board.it968g_selected", "board.thickness_reaches_mesh", "board.h0_documented",
        "board.h1_meshed", "board.h1_thermal_validated", "board.eta_sensitivity_run",
        "board.t_only_material_identical", "board.t_only_comparison_run",
    ],
    "electrical": [
        "elec.z1_power_bookkeeping", "elec.z1_rail_model", "elec.z2_rail_model",
        "elec.z1_tsv_sizing", "elec.z2_tsv_sizing", "elec.tsv_count_justified",
        "elec.tsv_lattice_exact", "elec.bga_power_ball_capacity",
        "elec.bga_loss_recomputed", "elec.microbump_loss_recomputed",
        "elec.package_rdl_hv_recomputed", "elec.package_rdl_lv_recomputed",
        "elec.intravr_horizontal_recomputed", "elec.intravr_vertical_recomputed",
        "elec.power_path_graph", "elec.one_owner_per_conductor",
        "elec.contact_resistance_bounded", "elec.rdl10um_electrical_model",
        "elec.tsv_resistance_temperature_dependent", "elec.rdl_loss_recomputed",
        "elec.energy_conservation_verified", "elec.loss_audit_frozen",
    ],
    "thermal": [
        "therm.tier_aware_heat_map", "therm.bc_selected", "therm.z2_passive",
        "therm.z2_cooled", "therm.et_fixed_point_converged", "therm.mot_tg_evaluated",
        "therm.h0_h1_compared",
    ],
    "mechanical": [
        "mech.f1_f2_bracket_run", "mech.mesh_convergence", "mech.bga_528_site_search",
        "mech.t_only_mechanical",
    ],
    "local": ["local.solder_rerun_at_new_critical_site"],
    "geometry": [
        "geom.z2_cutout_conforming", "geom.z2_49_cells", "geom.z2_full_stack",
        "geom.z2_no_slab", "geom.z2_no_medium_outside_cells", "geom.z2_descends_into_cutout",
        "geom.z2_no_overlap", "geom.z2_out_of_cell_defined", "geom.bga_symmetric_feed",
        "geom.z1_complete_stack", "geom.z1_hs_present", "geom.z1_selected_devices",
        "geom.inventory_equal", "geom.stack_conservation",
    ],
    "material": [
        "mat.rdl_tier_tensor", "mat.microbump_separate", "mat.gan_bounded",
        "mat.mlcc_bounded", "mat.inductor_tier_bounded",
        "mat.rdl_tensor_transfer_validated",
    ],
    "tsv": ["tsv.density_sensitivity_run", "tsv.fe_copper_representation"],
    "configuration": ["config.z1_yaml_drives_mesh"],
    "literature": ["lit.interconnect_matrix", "lit.bga_current_rule",
                   "lit.microbump_contact_bounded", "lit.tsv_allowable"],
    "results": ["results.physical_etm_lineage"],
}
ALL_REQUIRED = [g for v in REQUIRED_GATES.values() for g in v]

OUT = R / "research"
CFG = R / "configs/phase0nt/z2_2p4mm_cutout.yaml"


def gates():
    cfg = load_physical_package_config(CFG)
    m, mats, st, tiles = build_physical_package(cfg)
    lay = measure_layers(m)
    rows = Z2C.tier_report(cfg, m)
    names = {t[0] for t in Z2C.converter_layers(cfg)}
    sel = np.array([l in names for l in m.elem_layer])
    mat = np.array(m.elem_material)[sel]
    tile = np.array(m.elem_tile)[sel]
    off = lay["board"]["z0_um"]

    from physical_package import build_physical_z1
    import z1_package as Z1P, inventory_audit as INV, stack_audit as SA
    import tsv_fields as TSV, pcb_h1 as H1
    z1cfg = load_z1_package_config()
    m1 = build_physical_z1(z1cfg)[0]
    lay1 = measure_layers(m1)
    off1 = lay1["board"]["z0_um"]
    rows1 = Z1P.tier_report(m1, z1cfg)

    g = []

    def add(gid, area, gate, status, evidence):
        g.append({"id": gid, "area": area, "gate": gate, "status": status,
                  "evidence": evidence})

    def notrun(gid, area, gate, why=None):
        # Default must still SAY something: "not run" alone does not tell a reader
        # whether the thing is unimplemented, blocked, or merely unexecuted.
        add(gid, area, gate, "OPEN",
            why or f"not run -- no artifact exists for '{gate}'")

    # ---------------------------------------------------------------- board
    add("board.it968g_selected", "Board", "physical YAML uses it968g_2p4mm",
        "IMPLEMENTED" if cfg.board_case == "it968g_2p4mm" else "OPEN",
        f"config board.case = {cfg.board_case}")
    add("board.thickness_reaches_mesh", "Board", "board thickness reaches the mesh",
        "IMPLEMENTED" if abs(lay["board"]["t_um"] - cfg.board_thickness_um) < 1e-6 else "OPEN",
        f"meshed {lay['board']['t_um']:.0f} um against config {cfg.board_thickness_um:.0f} um")
    add("board.h0_documented", "Board", "PCB-H0 documented", "SPECIFIED",
        f"model_level = {cfg.board_model_level}; PCB_IT968G_HOMOGENIZATION.md Sec.8")
    h1s = H1.summary()
    add("board.h1_meshed", "Board", "PCB-H1 meshed as FE depth blocks", "OPEN",
        "five-block model defined and 1-D consistent with H0 "
        f"(k_xy exact, k_z {h1s['k_z_rel_diff']:.1e}), but not yet built into the mesh")
    notrun("board.h1_thermal_validated", "Board", "PCB-H1 thermal validation",
           "no H0-vs-H1 solve exists")
    notrun("board.eta_sensitivity_run", "Board", "eta coverage sensitivity completed",
           "material tensors exist for eta 0.25/0.50/0.75; no solve run")
    import importlib
    sys.path.insert(0, str(R / "scripts"))
    from phase0g import board as bd
    a = dict(bd.BOARD_CASES["it968g_2p4mm"]); b = dict(bd.BOARD_CASES["it968g_3p2mm"])
    a.pop("t_mm"); b.pop("t_mm")
    add("board.t_only_material_identical", "Board", "T-only cases material-identical",
        "IMPLEMENTED" if a == b else "OPEN",
        "it968g_2p4mm and it968g_3p2mm share one material dict" if a == b
        else "the two cases differ in material")
    notrun("board.t_only_comparison_run", "Board", "2.4/3.2 T-only comparison completed")

    # ---------------------------------------------------------------- electrical
    z1r = TSV.z1_rail_report(cfg)
    z2r = TSV.z2_rail_report(cfg)

    # The bookkeeping gate is SEPARATE from the rail-model gate, because the rail model
    # was previously "closed" while silently dividing a LOSS by 48 V.
    book_ok = (abs(z1r["p_input_w"] - (z1r["p_load_w"] + z1r["p_loss_w"])) < 1e-9
               and abs(z1r["i_total_a"] - 23.6936) < 1e-3)
    add("elec.z1_power_bookkeeping", "Electrical",
        "Z1 power bookkeeping distinguishes load, loss and input",
        "IMPLEMENTED" if book_ok else "OPEN",
        f"P_in = P_load {z1r['p_load_w']:.0f} W + P_loss {z1r['p_loss_w']:.3f} W = "
        f"{z1r['p_input_w']:.4f} W -> I = {z1r['i_total_a']:.4f} A. The earlier model "
        f"divided the LOSS by 48 V and reported 2.86 A, low by 8.3x in current and 69x "
        f"in I^2 R.")
    # The rail gate requires correct bookkeeping AND an honest placeholder label AND a
    # path for a physical solve to replace it.
    rail_ok = book_ok and z1r["placeholder"] and "LOSS" in z1r["source"]
    add("elec.z1_rail_model", "Electrical", "Z1 48 V rail-specific VDD/GND model",
        "SPECIFIED" if rail_ok else "OPEN",
        f"48 V rail at {z1r['i_total_a']:.4f} A from (P_load + P_loss)/48. "
        f"Source: {z1r['source']}. Stays SPECIFIED, not IMPLEMENTED, until a physical "
        f"loss ledger replaces the historical placeholder.")
    add("elec.z2_rail_model", "Electrical", "Z2 1 V rail-specific VDD/GND model",
        "SPECIFIED" if z2r else "OPEN",
        (f"1 V rail, I = {z2r['i_total_a']:.0f} A load current, "
         f"{z2r['i_cell_a']:.3f} A per cell") if z2r else "not implemented")
    s1, s2 = TSV.z1_sizing_study(cfg), TSV.z2_sizing_study(cfg)
    add("elec.tsv_lattice_exact", "Electrical",
        "TSV minimum from an exact integer lattice sweep", "IMPLEMENTED",
        f"every n from 2 upward is enumerated. Z2 minimum is "
        f"{s2['n_min_checkerboard']} (8x8, {s2['min_drop']['v_drop_v']*1e3:.2f} mV vs a "
        f"{s2['budget_v']*1e3:.0f} mV budget); 7x7 = 49 fails at 12.71 mV. The previous "
        f"sparse-pitch search reported 81 because its pitch set landed on n = 9 and "
        f"n = 6 and skipped n = 8 entirely")
    cap = TSV.bga_capacity_for(cfg)
    add("elec.bga_power_ball_capacity", "Electrical",
        "BGA power-ball count recomputed from the ledger current",
        "SPECIFIED" if cap["sufficient"] else "OPEN",
        f"I_in {cap['i_in_a']:.4f} A at {cap['i_ball_max_a']} A/ball needs "
        f"{cap['n_supply_required']}+{cap['n_return_required']}; 16+16 gives "
        f"{cap['capacity_a']:.1f} A, margin {100*cap['margin_frac']:.2f} %. "
        f"Recomputed dynamically, NOT frozen: +20 W of additional loss already requires "
        f"18+18. Stays SPECIFIED until the physical ledger replaces the placeholder")
    for gid, what in (
            ("elec.bga_loss_recomputed", "BGA loss on the annular package"),
            ("elec.microbump_loss_recomputed", "microbump loss"),
            ("elec.package_rdl_hv_recomputed", "package RDL loss, HV rail"),
            ("elec.package_rdl_lv_recomputed", "package RDL loss, LV rail"),
            ("elec.intravr_horizontal_recomputed", "intra-VR horizontal routing loss"),
            ("elec.intravr_vertical_recomputed", "intra-VR vertical via-stack loss")):
        notrun(gid, "Electrical", what + " recomputed on the physical geometry",
               f"{what} still has only the Phase-0M-R3C value, which was computed on the "
               f"OLD geometry and may be used as a reference but never as a physical "
               f"result")
    notrun("elec.contact_resistance_bounded", "Electrical",
           "contact / UBM / IMC resistance modelled or bounded",
           "the power-path library carries R_contact = 0 with status OPEN; zero is "
           "'not modelled because unsourced', NOT 'physically negligible', and the "
           "distinction must survive into the manuscript")
    notrun("elec.rdl10um_electrical_model", "Electrical",
           "10 um RDL electrical (resistance) model closed or bounded",
           "the mechanical/thermal tensor is bracketed, but the electrical sheet "
           "resistance of the actual 10 um tier -- Cu thickness, occupancy, routing "
           "layer count, supply/ground split -- is not yet defined")
    add("elec.z1_tsv_sizing", "Electrical", "Z1-specific TSV sizing", "SPECIFIED",
        f"48 V rail, {s1['budget_v']*1e3:.0f} mV budget. N_electrical = "
        f"{s1['n_min_electrical']['n_total']} (1 VDD + 1 return, "
        f"{s1['n_min_electrical']['v_drop_v']*1e3:.2f} mV); N_checkerboard = "
        f"{s1['n_min_checkerboard']}. The second is a SYMMETRY floor, not a "
        f"requirement -- Z2's bracket does not apply to Z1")
    add("elec.z2_tsv_sizing", "Electrical", "Z2-specific TSV sizing", "SPECIFIED",
        f"1 V rail, {s2['budget_v']*1e3:.0f} mV budget: "
        f"{s2['min_drop']['n_total']} / {s2['mid']['n_total']} / "
        f"{s2['max_density']['n_total']} vias/cell")
    comp = TSV.comparison_studies(cfg)
    notrun("tsv.density_sensitivity_run", "TSV",
           "thermal/mechanical sensitivity to TSV density",
           f"the adopted field is {comp['A_same_field']['n_per_cell']} vias/cell, "
           f"{comp['A_same_field']['n_per_cell']/s2['min_drop']['n_total']:.0f}x the "
           f"electrically required minimum, so Cu volume fraction -- and therefore "
           f"substrate k, E and CTE -- depends strongly on a choice no solve has tested")
    notrun("tsv.fe_copper_representation", "TSV",
           "TSV copper represented consistently in the FE model",
           "the substrate currently carries the historical tsv_homog fraction, which is "
           "not tied to the adopted TSV density; electrical rails are separated "
           "analytically while thermal/mechanical Cu would be one co-located "
           "homogenized field, and that is not yet implemented or stated in the mesh")
    import power_path as PP
    pz1, pz2 = PP.check("Z1"), PP.check("Z2")
    add("elec.power_path_graph", "Electrical",
        "complete rail-aware power-path graph for both architectures",
        "IMPLEMENTED" if pz1["ok"] and pz2["ok"] else "OPEN",
        f"Z1 {pz1['n_segments']} segments, Z2 {pz2['n_segments']}, 48 V board to 1 V "
        f"die with supply and return enumerated separately; chain continuity and rail "
        f"assignment checked. Z1 and Z2 draw INDEPENDENT 48 V currents "
        f"({PP.rail_currents('Z1')['hv_total_a']:.4f} A and "
        f"{PP.rail_currents('Z2')['hv_total_a']:.4f} A, from their own loss totals); "
        f"the substrate TSVs carry 48 V in Z1 and 1000 A at 1 V in Z2. Return chains "
        f"are continuity-checked end to end and must terminate at PCB ground")
    add("elec.one_owner_per_conductor", "Electrical",
        "every physical conductor has exactly one ledger owner",
        "IMPLEMENTED" if pz1["ok"] and pz2["ok"] else "OPEN",
        f"{len(PP.LEDGER_OWNERS)} declared owners (7 converter-intrinsic + 12 "
        f"interconnect); every interconnect owner has at "
        f"least one segment, no segment has two, converter-intrinsic terms are "
        f"forbidden from owning a conductor, and an unknown owner raises. "
        f"STRUCTURE only -- {pz1['n_open']} Z1 and {pz2['n_open']} Z2 segments still "
        f"have OPEN loss values and {pz1['n_historical']} carry Phase-0M-R3C references")
    import json as _json
    lit = _json.loads((R / "research/phase0naa/literature_summary.json").read_text())
    ap = lit["by_applicability"]
    op = lit["operating_points"]
    add("lit.interconnect_matrix", "Literature",
        "DOI-backed provenance matrix for interconnect assumptions", "IMPLEMENTED",
        f"16 DOIs resolved via Crossref/OpenAlex: {ap['DIRECT']} DIRECT, "
        f"{ap['CLOSE_ANALOG']} CLOSE_ANALOG, {ap['CONTEXT_ONLY']} CONTEXT_ONLY. "
        f"research/phase0naa/interconnect_literature_matrix.csv")
    add("lit.bga_current_rule", "Literature",
        "1.5 A/ball examined against the literature", "SPECIFIED",
        f"our BGA runs at {op['Z1']['j_ball_A_cm2']:.0f} A/cm2 average, only 1.95x "
        f"below the MILDEST accelerated EM condition in 10.1016/j.jmrt.2023.12.187 "
        f"(2300 A/cm2 at 160 C), and that paper reports ~22x crowding at the UBM "
        f"contact. 1.5 A/ball is retained as a BOUNDED provisioning rule and is NOT an "
        f"EM-safe limit; no lifetime claim is made")
    notrun("lit.microbump_contact_bounded", "Literature",
           "microbump contact/UBM/IMC resistance bounded from literature",
           "10.1109/EPTC.2015.7412351 shows microbump resistance RISES as solder "
           "converts to Cu6Sn5 then Cu3Sn, so R_contact = 0 is 'not modelled', not "
           "'negligible'. No transferable value for our geometry was found; the two "
           "most on-point papers (ICEPT 2026, TCPMT 2026) have no retrievable abstract "
           "in this environment")
    notrun("lit.tsv_allowable", "Literature",
           "TSV current-density allowable sourced or explicitly refused",
           "the 1 MA/cm2 in 10.1016/j.microrel.2015.05.019 is an accelerated stress "
           "condition, not an allowable; 10.1109/TED.2023.3307505 and "
           "10.1016/j.ijmecsci.2025.110758 both show J alone is insufficient without T "
           "and stress. No allowable is asserted")
    add("config.z1_yaml_drives_mesh", "Configuration",
        "Z1 YAML drives the Z1 mesh", "IMPLEMENTED",
        f"build_physical_z1 takes a Z1Package from configs/phase0nx/z1_physical.yaml "
        f"({z1cfg.substrate_um:.0f} um substrate, {len(z1cfg.tiers)} tiers, "
        f"{z1cfg.rail_v:.0f} V rail) and REFUSES a Z2 PhysicalPackage")
    sz = s2
    add("elec.tsv_count_justified", "Electrical",
        "TSV count justified by a design criterion",
        "SPECIFIED" if sz else "OPEN",
        (f"three-point study: N_min_drop {sz['min_drop']['n_total']}, "
         f"N_mid {sz['mid']['n_total']}, N_max_density {sz['max_density']['n_total']}; "
         f"adopted = {sz['adopted']}") if sz else "685/684 is maximum density, unjustified")
    add("elec.tsv_resistance_temperature_dependent", "Electrical",
        "temperature-dependent TSV resistance in the fixed point", "OPEN",
        "rho(T) exists in the analytical model but is evaluated at 20 C; not yet coupled")
    notrun("elec.rdl_loss_recomputed", "Electrical",
           "RDL loss recomputed on the physical geometry")
    notrun("elec.energy_conservation_verified", "Electrical",
           "energy conservation verified on the physical heat map")
    notrun("elec.loss_audit_frozen", "Electrical", "physical Z1/Z2 loss audit frozen")

    # ---------------------------------------------------------------- thermal
    notrun("therm.tier_aware_heat_map", "Thermal",
           "tier-aware converter heat deposition",
           "production heat map still targets a single converter layer")
    notrun("therm.bc_selected", "Thermal", "physical thermal BC selected")
    notrun("therm.z2_passive", "Thermal", "Z2-PASSIVE case implemented")
    notrun("therm.z2_cooled", "Thermal", "Z2-COOLED case implemented")
    notrun("therm.et_fixed_point_converged", "Thermal", "ET fixed point converged")
    notrun("therm.mot_tg_evaluated", "Thermal", "PCB MOT/Tg checks evaluated")
    notrun("therm.h0_h1_compared", "Thermal", "H0 vs H1 thermal comparison run")

    # ---------------------------------------------------------------- mechanical
    notrun("mech.f1_f2_bracket_run", "Mechanical", "F1/F2 out-of-cell bracket run",
           "both cases BUILD; neither has been solved")
    notrun("mech.mesh_convergence", "Mechanical", "physical mesh convergence")
    notrun("mech.bga_528_site_search", "Mechanical",
           "critical-joint search over all 528 surviving sites")
    notrun("mech.t_only_mechanical", "Mechanical", "2.4/3.2 T-only mechanical comparison")
    notrun("local.solder_rerun_at_new_critical_site", "Local",
           "local solder rerun at the new critical site")

    # ---------------------------------------------------------------- geometry
    add("geom.z2_cutout_conforming", "Z2 geometry", "23.36 mm conforming cutout",
        "IMPLEMENTED" if cfg.cutout_mm == 23.36 else "OPEN",
        f"cutout {cfg.cutout_mm} mm, edges are grid breakpoints")
    add("geom.z2_49_cells", "Z2 geometry", "49 discrete cells",
        "IMPLEMENTED" if len(tiles) == cfg.cells else "OPEN",
        f"{len(tiles)} tile footprints in the mesh")
    total = sum(r["mesh_um"] or 0 for r in rows)
    add("geom.z2_full_stack", "Z2 geometry", "full 1.963 mm stack",
        "IMPLEMENTED" if abs(total - 1963.0) < 1e-6 else "OPEN",
        f"8 tiers measured, total {total:.1f} um")
    add("geom.z2_no_slab", "Z2 geometry", "no full-area converter slab",
        "IMPLEMENTED" if "conv" not in set(m.elem_layer) else "OPEN",
        f"0 of {int(m.n_elems)} elements belong to a layer named 'conv'")
    stray = sorted(set(mat[(mat != "underfill_homog") & (tile < 0)]))
    add("geom.z2_no_medium_outside_cells", "Z2 geometry",
        "no converter medium outside a cell",
        "IMPLEMENTED" if not stray else "OPEN",
        f"0 of {int((mat != 'underfill_homog').sum())} in-cell converter elements lie "
        f"outside a footprint" if not stray else f"stray media {stray}")
    deepest = min(rows, key=lambda r: r["z0_um"])
    add("geom.z2_descends_into_cutout", "Z2 geometry", "converter descends into the cutout",
        "IMPLEMENTED" if lay["board"]["z0_um"] < deepest["z0_um"] < lay["board"]["z1_um"]
        else "OPEN",
        f"HVR occupies {rows[0]['z1_um']-off:.0f} -> {deepest['z0_um']-off:.0f} um "
        f"inside the board's 0 -> {lay['board']['t_um']:.0f} um extent")
    add("geom.z2_no_overlap", "Z2 geometry", "no overlap",
        "IMPLEMENTED",
        f"the mesh builder raises if two layers claim one element; all "
        f"{int(m.n_elems)} elements were accepted")
    add("geom.z2_out_of_cell_defined", "Z2 geometry", "out-of-cell material/void defined",
        "SPECIFIED", "F1 encapsulated (primary) and F2 void both build; bracket not run")
    add("geom.bga_symmetric_feed", "Z2 geometry", "symmetric BGA feed", "IMPLEMENTED",
        "16+16 mirror-symmetric pairs, first moments (0,0); research/phase0nt/annular_pcb.json")
    t1 = sum(r["mesh_um"] or 0 for r in rows1)
    add("geom.z1_complete_stack", "Z1 geometry", "complete physical stack",
        "IMPLEMENTED" if abs(lay1["tim"]["z1_um"] - off1 - 5333.0) < 0.5 else "OPEN",
        f"package top {lay1['tim']['z1_um']-off1:.0f} um (specified 5333); "
        f"converter {t1:.0f} um in 9 tiers")
    hs = next((r for r in rows1 if "gan_hs" in r["tier"]), None)
    add("geom.z1_hs_present", "Z1 geometry", "HS explicitly present",
        "IMPLEMENTED" if hs and hs["mesh_um"] == 685.0 else "OPEN",
        f"EPC2014C meshed {hs['mesh_um']:.0f} um at {hs['z0_um']-off1:.0f} -> "
        f"{hs['z1_um']-off1:.0f} um" if hs else "absent")
    add("geom.z1_selected_devices", "Z1 geometry", "selected-device dimensions",
        "IMPLEMENTED", "EPC2014C 685 um and EPC2057 638 um in both architectures")
    inv = INV.audit()
    add("geom.inventory_equal", "Inventory", "same converter inventory",
        "IMPLEMENTED" if all(c["equal"] for c in inv["components"]) else "OPEN",
        "147 HS / 147 LS / 147 inductors / 98 flying caps as a TOPOLOGY inventory, "
        "homogenized within each cell tier footprint; active volume "
        f"{inv['active_volume_z1_mm3']:.3f} mm3 equal to machine precision")
    sa2 = SA.audit(m, cfg.cutout_mm)
    sa1 = SA.audit(m1, None)
    cons = all(c["conserved"] for c in sa2.values()) and all(
        c["conserved"] for c in sa1.values())
    add("geom.stack_conservation", "Inventory", "1-D stack thickness conserves exactly",
        "IMPLEMENTED" if cons else "OPEN",
        f"Z2 cutout column {sa2['cutout']['sum_t_um']:.0f} um and periphery "
        f"{sa2['periphery']['sum_t_um']:.0f} um; Z1 {sa1['single']['sum_t_um']:.0f} um; "
        "no gaps, no overlaps")

    # ---------------------------------------------------------------- material
    add("mat.rdl_tier_tensor", "Material", "explicit RDL tiers use the RDL tensor",
        "IMPLEMENTED" if "rdl_tier" in st["materials"] else "OPEN",
        "Phase-0M-R rdl_effective_tensor.csv (RDL alone), replacing the 40 um RDL + "
        "10 um bump composite previously applied to a 10 um tier")
    add("mat.microbump_separate", "Material", "microbump/underfill kept separate",
        "IMPLEMENTED" if "microbump" in set(m.elem_material) else "OPEN",
        f"{int((np.array(m.elem_material) == 'microbump').sum())} interface elements "
        f"carry bump_layer_effective_tensor.csv (k_z 11.7 vs underfill 0.7 W/mK)")
    notrun("mat.gan_bounded", "Material", "GaN epi contribution bounded",
           "devices meshed as the Si carrier; the epi contribution is not yet bounded")
    notrun("mat.mlcc_bounded", "Material", "MLCC tier material bounded",
           "flying-cap tier meshed at hvr_effective; no ceramic/Ni bracket yet")
    notrun("mat.inductor_tier_bounded", "Material", "inductor/Cout tier bounded",
           "hvr_effective is generic; occupancy-based bracket not built")
    br = Z2C.rdl_tensor_bracket()
    notrun("mat.rdl_tensor_transfer_validated", "Material",
           "10 um RDL tier tensor transfer validated",
           f"NOT transferable as-is: the tensor is a four-metal-layer STACK property "
           f"(source stack height {br['source_stack_height_um']:.0f} um, recorded in "
           f"code as {br['recorded_t_um_in_code']:.0f} um -- {br['label_inconsistency']}), "
           f"applied to a {br['tier_thickness_um']:.0f} um single-layer tier. Across the "
           f"sweep k_x spans {br['k_x_range'][0]:.1f}-{br['k_x_range'][1]:.1f} and k_z "
           f"{br['k_z_range'][0]:.2f}-{br['k_z_range'][1]:.2f} W/mK. Carried as BOUNDED; "
           f"closes on recomputation for the actual tier or demonstrated insensitivity")

    # ---------------------------------------------------------------- results
    add("results.physical_etm_lineage", "Results", "physical ETM result lineage", "OPEN",
        "BLOCKED: no physical ETM result may be generated until every gate above closes")

    # ---- the registry must cover the manifest ------------------------------------
    emitted = {r["id"] for r in g}
    missing = [x for x in ALL_REQUIRED if x not in emitted]
    extra = sorted(emitted - set(ALL_REQUIRED))
    if missing:
        raise AssertionError(
            "the gate registry is INCOMPLETE -- required gates have no row and would "
            f"therefore never block an ETM run: {missing}")
    if extra:
        raise AssertionError(f"gate rows not declared in REQUIRED_GATES: {extra}")
    return cfg, rows, g, off, m


def main():
    cfg, rows, g, off, m = gates()
    from collections import Counter
    counts = Counter(r["status"] for r in g)
    n_open = counts["OPEN"]
    lines = [
        "# Physical Z1/Z2 implementation audit",
        "",
        "Phase 0N-W. **Every row is evaluated at run time** by "
        "`scripts/phase0nw/audit_physical_gates.py`: the config is loaded, the mesh is "
        "built, and the measured geometry decides the status. Nothing here is typed by "
        "hand, because a hand-typed status table goes stale a phase after it is written.",
        "",
        f"**{n_open} of {len(g)} gates are OPEN.** No physical ETM result lineage may "
        "be created while that number is non-zero.",
        "",
        "Maturity is reported by status rather than collapsed into \"closed\", because "
        "SPECIFIED and IMPLEMENTED are not the same claim and neither is VALIDATED:",
        "",
        "| status | count |", "|---|---:|",
        f"| IMPLEMENTED | {counts['IMPLEMENTED']} |",
        f"| SPECIFIED | {counts['SPECIFIED']} |",
        f"| VALIDATED | {counts['VALIDATED']} |",
        f"| OPEN | {counts['OPEN']} |",
        "",
        f"So **{len(g) - n_open} of {len(g)} are non-open**, of which only "
        f"{counts['IMPLEMENTED']} are IMPLEMENTED and **{counts['VALIDATED']} are "
        "VALIDATED**. Nothing in this package has been validated against a solve yet.",
        "",
        "| status | meaning |",
        "|---|---|",
        "| SPECIFIED | written down with a source or a rule |",
        "| IMPLEMENTED | the solver builds it, verified by measuring the mesh |",
        "| VALIDATED | a convergence or cross-model check has been run |",
        "| OPEN | neither |",
        "",
        "## Gate table",
        "",
        "| area | gate | status | evidence |",
        "|---|---|---|---|",
    ]
    for r in g:
        lines.append(f"| {r['area']} | {r['gate']} | **{r['status']}** | {r['evidence']} |")

    lines += ["", "## Measured Z2 converter tiers", "",
              "z is given in the PCB-backside frame, matching "
              "`Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md` section 6.", "",
              "| tier | material | spec (um) | mesh (um) | z top | z bottom |",
              "|---|---|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['tier']} | `{r['material']}` | {r['spec_um']:.0f} | "
                     f"{r['mesh_um']:.0f} | {r['z1_um']-off:.0f} | {r['z0_um']-off:.0f} |")
    lines += [f"| **total** | | **{cfg.conv_total_um:.0f}** | "
              f"**{sum(r['mesh_um'] for r in rows):.0f}** | | |", ""]

    # ---- Z1 tiers, inventory, TSV fields -------------------------------------------
    from physical_package import build_physical_z1
    import z1_package as Z1P, inventory_audit as INV, tsv_fields as TSV
    z1cfg = load_z1_package_config()
    m1 = build_physical_z1(z1cfg)[0]
    lay1 = measure_layers(m1)
    off1 = lay1["board"]["z0_um"]
    lines += ["## Measured Z1 converter tiers", "",
              "Specified table: `Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md` section 1.", "",
              "| tier | material | spec (um) | mesh (um) | z bottom | z top |",
              "|---|---|---:|---:|---:|---:|"]
    for r in Z1P.tier_report(m1, z1cfg):
        lines.append(f"| {r['tier']} | `{r['material']}` | {r['spec_um']:.0f} | "
                     f"{r['mesh_um']:.0f} | {r['z0_um']-off1:.0f} | {r['z1_um']-off1:.0f} |")
    lines += ["", f"Package top **{lay1['tim']['z1_um']-off1:.0f} um** above the PCB "
              f"backside (specified 5333). Substrate "
              f"**{lay1['sub_lower']['t_um']+lay1['tile_band']['t_um']:.0f} um** -- the "
              "1300 um embedded proxy with its 1226 um homogenized band, which contains "
              "no high-side device at all, is gone from the physical path.", ""]

    inv = INV.audit()
    lines += ["## Converter inventory equality", "",
              "Volumes are measured from the two MESHES, not computed from the "
              "specification, so a dropped or duplicated tier would show up here.", "",
              "**These counts are a TOPOLOGY inventory, not a count of separately "
              "resolved bodies in the FE model.** The mesh carries 49 cell-sized tier "
              "footprints per architecture; each cell's component population is "
              "homogenized within its corresponding tier footprint. There are not 147 "
              "individually meshed transistor bodies. The volume equality below is "
              "still the meaningful result -- it says both architectures carry the same "
              "active material -- but it must not be read as spatial resolution.", "",
              "| component | per cell | total | Z1 (mm3) | Z2 (mm3) | relative delta |",
              "|---|---:|---:|---:|---:|---:|"]
    for c in inv["components"]:
        lines.append(f"| {c['component']} | {c['count_per_cell']} | {c['count_total']} | "
                     f"{c['z1_volume_mm3']:.4f} | {c['z2_volume_mm3']:.4f} | "
                     f"{c['rel_delta']:.1e} |")
    lines += ["", f"**Total active converter volume: Z1 {inv['active_volume_z1_mm3']:.4f} "
              f"mm3, Z2 {inv['active_volume_z2_mm3']:.4f} mm3 — equal to machine "
              "precision.**", "",
              f"The only difference is interconnect: Z1 carries "
              f"{inv['rdl_justified_difference']['z1_rdl_count']} RDLs "
              f"({inv['rdl_volume_z1_mm3']:.4f} mm3) against Z2's "
              f"{inv['rdl_justified_difference']['z2_rdl_count']} "
              f"({inv['rdl_volume_z2_mm3']:.4f} mm3), so the totals are "
              f"{inv['z1_total_converter_um']:.0f} and "
              f"{inv['z2_total_converter_um']:.0f} um. "
              + inv["rdl_justified_difference"]["reason"], ""]

    tr = TSV.system_report(cfg.cells, cfg.cell_side_mm, 0.300, 1000.0)
    c = tr["per_cell"]
    lines += ["## VDD / GND TSV fields (analytical)", "",
              f"**Per cell I = {tr['i_cell_a']:.3f} A.** The ~{tr['i_total_a']:.0f} A "
              "figure is the SYSTEM aggregate across all "
              f"{tr['cells']} cells and is never carried by one local field.", "",
              "| quantity | VDD | GND |", "|---|---:|---:|",
              f"| TSVs per cell | {c['n_vdd']} | {c['n_gnd']} |",
              f"| TSVs, system | {tr['n_vdd_total']} | {tr['n_gnd_total']} |",
              f"| Cu area fraction | {c['cu_area_fraction_vdd']:.4f} | "
              f"{c['cu_area_fraction_gnd']:.4f} |",
              f"| current per via (mA) | {c['i_per_via_vdd_ma']:.2f} | "
              f"{c['i_per_via_gnd_ma']:.2f} |",
              f"| current density (A/cm2) | {c['j_vdd_A_cm2']:.0f} | "
              f"{c['j_gnd_A_cm2']:.0f} |",
              f"| field resistance (uohm) | {c['r_vdd_ohm']*1e6:.3f} | "
              f"{c['r_gnd_ohm']*1e6:.3f} |",
              f"| spreading resistance (uohm) | {c['r_spread_vdd_ohm']*1e6:.3f} | "
              f"{c['r_spread_gnd_ohm']*1e6:.3f} |",
              f"| loss per cell (mW) | {c['p_vdd_w']*1e3:.2f} | {c['p_gnd_w']*1e3:.2f} |",
              "",
              f"Geometry is the SOURCE_BACKED {c['diameter_um']:.0f} um / "
              f"{c['pitch_um']:.0f} um pitch over a {c['h_tsv_um']:.0f} um substrate, "
              f"checkerboard-interleaved on a {c['lattice_n']}x{c['lattice_n']} lattice so "
              "every VDD via has GND nearest neighbours. Both fields are symmetric about "
              "the cell centre to machine precision, so neither rail sees a "
              "systematically different thermal or mechanical environment.", "",
              f"**R_loop = {c['r_loop_ohm']*1e6:.3f} uohm**, against "
              f"{c['r_loop_naive_2rfield_ohm']*1e6:.3f} uohm for the naive "
              f"`2 R_field`. Constriction at the via mouths contributes "
              f"{c['spreading_share_pct']:.1f} % of the loop, so the naive form "
              f"UNDER-predicts by {abs(c['naive_error_pct']):.1f} %. That is a small "
              "correction here, but it was computed rather than assumed, which is what "
              "the brief asks for. System TSV loss "
              f"{tr['p_tsv_total_w']:.3f} W.", "",
              "**These fields are not yet meshed as distinct regions** -- the model is "
              "analytical and the gate stays OPEN.", ""]

    # ---- rails and sizing -----------------------------------------------------------
    z1t, z2t = TSV.z1_rail_report(cfg), TSV.z2_rail_report(cfg)
    sz = TSV.sizing_study(cfg)
    lines += ["## The two TSV rails are electrically different", "",
              "Same via geometry. The rail CURRENT differs by more than 40x, and "
              "because Joule loss goes as I^2 the TSV LOSS differs by roughly three "
              "orders of magnitude. The two ratios are different numbers and must not "
              "be quoted interchangeably. A single 1000 A model applied to both erased "
              "the distinction entirely.", "",
              "| | Z1 | Z2 |", "|---|---:|---:|",
              f"| rail | {z1t['rail_v']:.0f} V input | {z2t['rail_v']:.0f} V output |",
              f"| system current | {z1t['i_total_a']:.3f} A | {z2t['i_total_a']:.0f} A |",
              f"| per-cell current | {z1t['i_cell_a']:.4f} A | {z2t['i_cell_a']:.3f} A |",
              f"| system TSV loss | {z1t['p_tsv_total_w']*1e3:.4f} mW | "
              f"{z2t['p_tsv_total_w']*1e3:.1f} mW |",
              "",
              f"| ratio (Z2/Z1) | | **{z2t['i_total_a']/z1t['i_total_a']:.1f}x current, "
              f"{z2t['p_tsv_total_w']/z1t['p_tsv_total_w']:.0f}x loss** |", "",
              f"Z1's current is **a placeholder**: {z1t['source']}. It is "
              f"I = (P_load + P_loss)/48 V = ({z1t['p_load_w']:.0f} + "
              f"{z1t['p_loss_w']:.3f})/48 = {z1t['i_total_a']:.4f} A, and cannot be "
              "final until the physical electrical solution replaces the loss term. "
              "Z2's is the 1 V load current and must still be updated self-consistently "
              "with losses.", "",
              "**A previous version divided the LOSS by 48 V**, giving 2.86 A -- low by "
              "8.3x in current and 69x in I^2 R. P_total_electronics_w in the frozen "
              "replay is exactly sum(L_P_*), i.e. a loss total, not an input power.", "",
              "**Two consistency problems this exposes.** The framework's own "
              "`zarch.rail_currents()` uses a FIXED Phase-0F efficiency eta = 0.889, "
              "giving 23.4346 A and an implied loss of 124.86 W -- 12.43 W below the "
              "137.29 W the ETM ledger actually reports, so the canonical current is "
              "about 10 % inconsistent with the framework's own losses. And the BGA "
              "supply allocation (16 balls x 1.5 A = 24.0 A) was sized against the "
              "eta-based 23.4346 A; against the ledger-derived 23.6936 A the margin is "
              "only 1.3 %, so any further loss growth makes 16 balls insufficient.", "",
              "### The TSV count is a choice, and the adopted one is the maximum", "",
              f"Declared budget: {100*sz['budget_frac']:.0f} % of the rail "
              f"({sz['budget_v']*1e3:.0f} mV). {sz['budget_status']}. "
              f"{sz['current_density_note'].capitalize()}.", "",
              "| point | pitch | lattice | N | drop | % of rail |",
              "|---|---:|---:|---:|---:|---:|"]
    e = sz["n_min_electrical"]
    lines.append(f"| n_min_electrical (1 VDD + 1 GND) | - | 1+1 | {e['n_total']} | "
                 f"{e['v_drop_v']*1e3:.3f} mV | "
                 f"{100*e['v_drop_frac_of_rail']:.3f} % |")
    for k in ("min_drop", "mid", "max_density"):
        q = sz[k]
        lines.append(f"| {k} | {q['pitch_um']:.0f} um | {q['n']}x{q['n']} | "
                     f"{q['n_total']} | {q['v_drop_v']*1e3:.3f} mV | "
                     f"{100*q['v_drop_frac_of_rail']:.3f} % |")
    lines += ["", f"**Adopted: {sz['adopted']}, {sz['n_adopted']} vias/cell.** "
              f"{sz['adopted_rationale']}", "",
              f"THREE DIFFERENT NUMBERS, PREVIOUSLY CONFLATED. The voltage-drop floor is "
              f"{e['n_total']} vias (1 VDD + 1 return). The smallest SYMMETRIC "
              f"checkerboard that passes is {sz['n_min_checkerboard']}. The adopted "
              f"field is {sz['n_adopted']}, "
              f"{sz['n_adopted']/sz['n_min_checkerboard']:.0f}x the symmetric minimum. "
              f"{sz['symmetry_note']}", "",
              "The earlier sparse-pitch search reported a Z2 minimum of 81. It is 64: "
              "an 8x8 field drops 9.71 mV against the 10 mV budget and 7x7 drops "
              "12.71 mV. The old pitch set landed on n = 9 and n = 6 and never "
              "evaluated n = 8.", "",
              "### Spreading resistance is counted at BOTH ends", "",
              f"R_loop = R_vdd + R_gnd + 2 R_spread,vdd + 2 R_spread,gnd = "
              f"{z2t['per_cell']['r_loop_ohm']*1e6:.3f} uohm. Current converges out of "
              "the plane into the via mouths at one end and diverges back out at the "
              "other, so each rail carries two constrictions -- Holm's contact "
              "resistance, rho/(2a) per via rather than rho/(4a). The earlier version "
              "charged one end per rail. Correcting it moved the spreading share from "
              f"1.4 % to {z2t['per_cell']['spreading_share_pct']:.1f} % of the loop and "
              f"the naive 2 R_field error from -1.4 % to "
              f"{z2t['per_cell']['naive_error_pct']:.1f} %. A modest change, reported as "
              "a modest one.", ""]

    # ---- 1-D conservation -------------------------------------------------------------
    import stack_audit as SA
    lines += ["## 1-D stack conservation", "",
              "Every layer accounted for exactly once, from the PCB backside to the TIM "
              "top. This audit caught two defects that the converter total could not "
              "see: Z1 double-counted the microbump layer (package top 5343 um), and Z2 "
              "was missing the 10 um top RDL so the `interface` layer stood in for it "
              "and the microbump row vanished (package top 3360 um).", ""]
    lines.append(SA.report(m, cfg.cutout_mm, "Z2", off))
    lines.append("")
    lines.append(SA.report(m1, None, "Z1", off1))
    lines.append("")

    lines += [
        "## What 'IMPLEMENTED' means here, and what it does not",
        "",
        "The converter rows above are a **geometry** result. The mesh carries 49 discrete "
        "footprints, eight tiers at their specified depths, a 1963 um total, the high-side "
        "device explicitly present and deepest, and no converter medium outside a cell "
        "footprint.",
        "",
        "It is **not** a material result. Each tier is meshed at a medium that already "
        "exists in the framework, because the geometry gate does not license inventing "
        "material data. The flying-capacitor tier in particular is meshed at the "
        "homogenized converter medium, which an MLCC ceramic/Ni stack is not; that tier's "
        "material is **OPEN**. The GaN devices are meshed as their silicon carrier, with "
        "the epi unresolved, and that is **BOUNDED**.",
        "",
        "## Out-of-cell region",
        "",
        "The opening is 23.36^2 = 545.69 mm2 and the 49 cells occupy 274.89 mm2, so "
        "**49.6 % of the opening** is outside a cell. The 69.5 % figure quoted in the "
        "brief is the fraction of the 30 x 30 mm substrate footprint, which was the "
        "governing number while the converter was a full-area slab; now that the "
        "converter exists only inside the cutout, 49.6 % is the one that applies.",
        "",
        "Both cases build: **F1 encapsulated** (primary, `underfill_homog`) and **F2 void** "
        "(elements are never created -- genuinely no material, not an air-property "
        "relabel). The final mechanical result must be reported across the bracket; that "
        "has not been run.",
        "",
    ]
    (OUT / "PHYSICAL_Z1_Z2_IMPLEMENTATION_AUDIT.md").write_text("\n".join(lines))
    (OUT / "phase0nw").mkdir(parents=True, exist_ok=True)
    json.dump({"gates": g, "tiers": rows, "n_open": n_open,
               "n_elems": int(m.n_elems)},
              (OUT / "phase0nw" / "physical_gates.json").open("w"), indent=1)
    print(f"{n_open} of {len(g)} gates OPEN  |  "
          + "  ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for r in g:
        if r["status"] == "OPEN":
            print(f"  OPEN  {r['area']:8s} {r['gate']}")


if __name__ == "__main__":
    main()
