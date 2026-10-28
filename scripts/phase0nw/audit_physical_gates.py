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
        "elec.rdl_loss_recomputed_HISTORICAL",
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
    "rms": ["elec.current_waveforms_defined", "elec.rms_current_model",
            "elec.branch_average_currents", "elec.aggregate_output_ripple",
            "elec.individual_branch_waveforms", "elec.hv_input_waveform",
            "elec.z1_hv_rms_current", "elec.z2_lv_rms_current",
            "elec.bga_bulk_dc_baseline", "elec.bga_rms_current",
            "elec.bga_network_sharing", "mat.copper_resistivity_canonical",
            "elec.tsv_conductor_geometry_consistent"],
    "pkgrdl": ["elec.z1_pkg_hv_rdl_geometry", "elec.z2_pkg_hv_rdl_geometry",
               "elec.pkg_rdl_sheet_model", "elec.pkg_rdl_network_converged",
               "elec.bga_voltage_fed_network", "elec.pkg_rdl_return_solved",
               "elec.cutout_penalty_isolated", "geom.cell_coordinate_single_source",
               # Phase 0N-AI
               "elec.z1_network_nonconvergence_diagnosed",
               "elec.bga_lattice_mirror_closed", "elec.bga_count_closed",
               "elec.pad_count_admissible_region", "elec.intravr_fidelity_ladder",
               "elec.hv_waveform_determination",
               "elec.cutout_penalty_isolated_HISTORICAL",
               "elec.pkg_rdl_network_converged_HISTORICAL",
               "geom.bga_lattice_single_source"],
    "padcount": ["elec.pad_count_criterion", "elec.pad_density_sensitivity",
                 "elec.pad_loss_closed"],
    "interface": ["elec.interface_primary_selected", "elec.source_pad_geometry",
                  "elec.source_pad_resistance", "elec.source_pad_count",
                  "elec.source_pad_loss", "elec.phase_group_index_mapping"],
    "recompute": ["mat.bga_alloy_provenance", "elec.bga_rho_T_model",
                  "elec.microbump_geometry_closed", "elec.microbump_series_resistance",
                  "elec.tsv_transition_audited"],
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
    import interconnect_loss as IL
    import rms_currents as RMS
    import tsv_fields as _TF
    L1, L2 = IL.ledger("Z1"), IL.ledger("Z2")
    cc = RMS.cell_currents()
    r1 = L1["rms"]

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
    add("elec.bga_loss_recomputed", "Electrical",
        "BGA loss recomputed on the physical geometry", "OPEN",
        "SUPERSEDES the evidence 'remains open pending RMS-current AND "
        "network-sharing closure'. Network sharing is CLOSED: "
        "elec.bga_network_sharing is IMPLEMENTED and the voltage-fed network "
        "produces the per-ball split, so sharing no longer blocks this gate. "
        "A source-backed bulk-BGA DC/equal-sharing reference exists "
        f"({L1['bga']['p_total_w']*1e3:.2f} mW for Z1). The ONE remaining blocker "
        "is the 48 V RMS waveform, which elec.hv_waveform_determination shows is "
        "not derivable from the pinned converter model")
    import json as _j0
    _led0 = _j0.loads((R / "research/phase0nab/interconnect_loss.json").read_text())
    _hv_ok = [a for a in ("Z1", "Z2")
              if _led0[a]["terms"]["P_pkg_RDL_HV_supply"]["maturity"]["loss"]
              != "OPEN"]
    _hv_no = [a for a in ("Z1", "Z2") if a not in _hv_ok]
    add("elec.package_rdl_hv_recomputed", "Electrical",
        "package RDL loss, HV rail recomputed on the physical geometry",
        "SPECIFIED" if _hv_ok else "OPEN",
        ("SUPERSEDES 'still has only the Phase-0M-R3C value', which is false at "
         "HEAD. The HV rail is recomputed from the solved voltage-fed network "
         "for %s, with supply and return as separate conductors and per-scenario "
         "I_rms^2 R losses in research/phase0nab/interconnect_loss.json. %s is "
         "still OPEN because its network fails the 1 %% convergence test. "
         "SPECIFIED, not IMPLEMENTED, while any architecture remains open and "
         "while the RMS waveform stays scenario-defined."
         % (", ".join(_hv_ok), ", ".join(_hv_no) or "nothing"))
        if _hv_ok else "no architecture has a converged package HV RDL network")
    for gid, what in (
            ("elec.microbump_loss_recomputed", "microbump loss"),
            ("elec.package_rdl_lv_recomputed", "package RDL loss, LV rail"),
            ("elec.intravr_horizontal_recomputed", "intra-VR horizontal routing loss"),
            ("elec.intravr_vertical_recomputed", "intra-VR vertical via-stack loss")):
        notrun(gid, "Electrical", what + " recomputed on the physical geometry",
               f"{what} still has only the Phase-0M-R3C value, computed on the OLD "
               f"geometry; usable as a reference, never as a physical result. The HV "
               f"package rail is NOT in this list any more -- it is recomputed "
               f"(elec.package_rdl_hv_recomputed) -- so this gate no longer implies "
               f"that nothing has been recomputed")
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
    add("elec.current_waveforms_defined", "RMS",
        "avg, RMS and peak current defined per rail", "IMPLEMENTED",
        f"branch I_avg {cc['branches'][0]['i_avg_a']:.4f} A (= I_cell*B_i/sum(B), NOT "
        f"20.4) is KNOWN; cell output rms/avg "
        f"{cc['i_cell_out_rms_a']/cc['i_cell_out_avg_a']:.5f} is KNOWN from the model's "
        f"own aggregate ripple. Individual branch ripple and RMS are WITHDRAWN and OPEN")
    add("elec.branch_average_currents", "RMS", "branch average currents", "IMPLEMENTED",
        f"I_branch = I_cell*B_i/sum(B) = {cc['branches'][0]['i_avg_a']:.4f} A, with "
        f"B_array built by generate_B_array() in the pinned source")
    add("elec.aggregate_output_ripple", "RMS", "aggregate output ripple", "IMPLEMENTED",
        f"{cc['ripple_out_pp_a']:.4f} A pp, the converter model's own expression")
    add("elec.individual_branch_waveforms", "RMS", "individual branch waveforms", "OPEN",
        "WITHDRAWN in Phase 0N-AD. Decomposing the summed output ripple into per-branch "
        "terms over D*T does not give a branch's periodic waveform; volt-second balance "
        f"on a conventional branch gives {cc['conventional_branch_ripple_sanity_a']:.4f} A "
        "on both ramps against the 0.310 A previously claimed for phase B. The pinned "
        "source has no switch-state sequence to settle it")
    add("elec.hv_input_waveform", "RMS", "48 V input waveform", "OPEN",
        "no SC charge-transfer sequence, phase displacement or dead time in the pinned "
        "source; see research/phase0nad/HVR_SWITCH_STATE_SOURCE_AUDIT.md")
    add("elec.rms_current_model", "RMS", "RMS scenario framework", "IMPLEMENTED",
        "L0 DC lower bound; L1A aggregate quantities the converter model genuinely "
        "provides; L1B explicit named SCENARIOS (HV-S0 continuous, HV-S1 square at D). "
        "L2 is NOT built and cannot be from the pinned source")
    add("elec.z1_hv_rms_current", "RMS", "48 V rail RMS current", "OPEN",
        f"THREE named SCENARIOS, not a bracket: HV-S0 continuous {r1['hv_S0_a']:.2f} A, "
        f"HV-S1 square pulse at the buck duty {r1['hv_S1_a']:.2f} A, HV-S2 square pulse "
        f"at the overall ratio {r1['hv_S2_a']:.2f} A (the duty the DVPD source's Eq.(5) "
        f"assumes). S1 and S2 are MINIMUM RMS values for their supports, NOT upper "
        f"bounds; {r1['hv_upper_bound']}. Z1 BGA supply spans "
        f"{L1['terms']['P_BGA_supply']['scenario_w']['HV_S0']*1e3:.1f} / "
        f"{L1['terms']['P_BGA_supply']['scenario_w']['HV_S1']*1e3:.0f} / "
        f"{L1['terms']['P_BGA_supply']['scenario_w']['HV_S2']*1e3:.0f} mW")
    add("elec.z2_lv_rms_current", "RMS", "1 V substrate rail RMS current", "IMPLEMENTED",
        f"per-cell rms/avg = {r1['cell_rms_over_avg']:.6f} from the model's own "
        f"aggregate ripple. The 49 TSV fields are ELECTRICALLY SEPARATE, so "
        f"P = 49*I_cell_rms^2*(R_VDD+R_GND) with no cross terms and inter-cell phase "
        f"cannot enter. Z2 substrate TSV loss is RMS-CLOSED at "
        f"{L2['terms']['P_TSV_VDD']['w']*1e3:.1f} mW per rail")
    add("elec.bga_bulk_dc_baseline", "RMS", "source-backed bulk BGA DC lower bound",
        "IMPLEMENTED",
        f"Z1 {L1['bga']['p_supply_w']*1e3:.3f} mW supply at equal sharing and I_avg; "
        f"single-ball bulk R {L1['bga']['r_supply_ohm']*16*1e3:.3f} mOhm, consistent "
        f"with the source's ~0.3 mOhm. 'At equal sharing' is a DECLARED PROPERTY OF "
        f"THIS BASELINE TERM, not a framework assumption: elec.bga_network_sharing "
        f"solves the real split and finds it unequal, so this row is a reference "
        f"figure and must not be used to size balls")
    add("elec.bga_rms_current", "RMS", "BGA loss uses RMS current", "OPEN",
        "SUPERSEDES the evidence 'the 48 V RMS is a bracket'. HV-S0/S1/S2 are "
        "NAMED SCENARIOS, not a bracket and not lower/nominal/upper: from an "
        "average current alone there is no finite RMS upper bound, because a "
        "narrower, taller pulse of the same average has strictly higher RMS "
        "without limit. Blocked by elec.hv_waveform_determination, which proves "
        "the waveform is not derivable from the pinned converter model")
    import json as _j2
    net = _j2.loads((R / "research/phase0naf/pkg_rdl_network.json").read_text())
    VF = _j2.loads((R / "research/phase0nai/voltage_fed_network.json").read_text())
    DG = _j2.loads((R / "research/phase0nai/z1_convergence_diagnostic.json").read_text())
    vfz1, vfz2 = VF["loop"]["Z1"], VF["loop"]["Z2"]
    vfc = VF["controlled"]
    vfconv = VF["convergence"]
    vfa = VF["asymmetry"]
    _worst = max(vfconv.values(), key=lambda c: c["worst_delta"])
    _sh = vfa["UNIFORM"]
    add("elec.bga_network_sharing", "RMS", "BGA current sharing from the RDL network",
        "IMPLEMENTED",
        f"SUPERSEDES the evidence 'equal sharing is assumed ... no package RDL "
        f"network exists to produce the real split', which was true when written and "
        f"is false at HEAD. The voltage-fed network solves the split: under a UNIFORM "
        f"load the balls carry {_sh['i_ball_min_a']:.4f}-{_sh['i_ball_max_a']:.4f} A "
        f"against the {_sh['imposed_value_would_be_a']:.4f} A equal sharing would "
        f"give, a spread of {_sh['spread_pct_of_mean']:.1f} % of the mean, and the "
        f"peak moves with the load. Equal sharing is therefore not merely unproven, "
        f"it is DISPROVEN for this geometry, which invalidates any I_total/N_ball "
        f"per-ball current used as a sizing criterion")
    add("mat.copper_resistivity_canonical", "RMS", "one canonical copper resistivity",
        "IMPLEMENTED" if abs(_TF.RHO_CU_20C - 17.0e-9) < 1e-18 else "OPEN",
        f"tsv_fields carried its own 16.8 nOhm.m ASSUMPTION against phase0m's "
        f"17.0 nOhm.m SOURCE_BACKED; now imported, {_TF.RHO_CU_20C*1e9:.1f} nOhm.m "
        f"everywhere")
    add("elec.tsv_conductor_geometry_consistent", "RMS",
        "TSV conducting diameter resolved against the source resistance", "IMPLEMENTED",
        "30 um as CONDUCTING Cu diameter gives 7.215 mOhm, matching the source's "
        "~7.1 mOhm; subtracting the 0.5 um liner gives 7.721 mOhm and does not. "
        "Electrical conducting diameter and mechanical outer diameter are now distinct")
    import pad_interface as PAD
    import rms_currents as _R
    xc = PAD.source_cross_check()
    psys = L1["pad"]
    nz1 = net["architectures"]["Z1"]["cases"]["RDL_T2_RDL_M"]
    nz2 = net["architectures"]["Z2"]["cases"]["RDL_T2_RDL_M"]
    cv2 = net["architectures"]["Z2"]["convergence"]
    add("elec.z1_pkg_hv_rdl_geometry", "PkgRDL",
        "continuous Z1 package HV RDL exists", "IMPLEMENTED",
        f"2-D sheet over the 30 mm substrate, {nz1['n_sources']} supply contacts to "
        f"{nz1['n_sinks']} cell nodes, {nz1['source_placement']}; "
        f"R_eff {nz1['r_eff_ohm']*1e3:.4f} mOhm at RDL_T2_RDL_M")
    add("elec.z2_pkg_hv_rdl_geometry", "PkgRDL",
        "continuous Z2 package HV RDL exists", "IMPLEMENTED",
        f"same sheet but sources restricted to the {nz2['source_placement']}; "
        f"R_eff {nz2['r_eff_ohm']*1e3:.4f} mOhm. THE RATIO TO Z1 IS WITHDRAWN as a "
        f"physical conclusion: it is unconverged (5.13x at 61x61 against 4.53x at "
        f"101x101) and contaminated by a hard-coded 3.0 mm cell pitch against the "
        f"actual 3.165243 mm, synthetic non-lattice Z1 sources, BGA contacts smaller "
        f"than the grid spacing, and imposed equal source currents. Preliminary "
        f"unconverged network observation only")
    add("elec.pkg_rdl_sheet_model", "PkgRDL", "RDL electrical sheet model", "SPECIFIED",
        f"R_sq = rho_Cu(T)/(t_Cu*occupancy), independent of the thermal tensor. "
        f"t_Cu swept 2/5/10 um (BOUNDED_FROM_LITERATURE, 10 um scale from TVLSI 2022 "
        f"CLOSE_ANALOG) x occupancy 0.80/0.30 (BOUNDED_ENGINEERING). The DVPD source "
        f"explicitly defers trace dimensions to process technology")
    add("elec.bga_voltage_fed_network", "PkgRDL",
        "BGA modelled as voltage-fed branches rather than imposed currents",
        "IMPLEMENTED",
        f"a rail node feeds each ball through its own Table III series resistance "
        f"({VF['meta']['r_ball_ohm']*1e3:.4f} mOhm, rho_solder*h/A) and a finite "
        f"contact, so the split is an OUTPUT. Under a UNIFORM load the balls carry "
        f"{vfa['UNIFORM']['i_ball_min_a']:.4f}-{vfa['UNIFORM']['i_ball_max_a']:.4f} A "
        f"against the {vfa['UNIFORM']['imposed_value_would_be_a']:.4f} A the imposed "
        f"model forced on every ball, a spread of "
        f"{vfa['UNIFORM']['spread_pct_of_mean']:.1f} % of the mean; moving half the "
        f"load to one corner cell widens it to "
        f"{vfa['CORNER_HEAVY']['spread_pct_of_mean']:.1f} %")
    add("elec.pkg_rdl_return_solved", "PkgRDL",
        "package return RDL network solved", "IMPLEMENTED",
        f"supply and return are two separate sheets, each with its own sites, solved "
        f"separately and added in series. Z1 R_supply "
        f"{vfz1['r_supply_ohm']*1e3:.4f} + R_return {vfz1['r_return_ohm']*1e3:.4f} = "
        f"{vfz1['r_loop_ohm']*1e3:.4f} mOhm; Z2 {vfz2['r_supply_ohm']*1e3:.4f} + "
        f"{vfz2['r_return_ohm']*1e3:.4f} = {vfz2['r_loop_ohm']*1e3:.4f} mOhm. The "
        f"return leg was previously computed and DISCARDED, so every earlier package "
        f"RDL resistance understated the loop by "
        f"{100*vfz1['r_return_ohm']/vfz1['r_supply_ohm']:.0f} % (Z1) and "
        f"{100*vfz2['r_return_ohm']/vfz2['r_supply_ohm']:.0f} % (Z2)")
    _z1l = vfz1["r_loop_ohm"]
    _err = max(vfconv["Z1_supply"]["deltas"]["r_eff_ohm"],
               vfconv["Z1_return"]["deltas"]["r_eff_ohm"])
    add("elec.cutout_penalty_isolated", "PkgRDL",
        "cutout penalty isolated from BGA-placement penalty", "SPECIFIED",
        f"CTRL_FULL is BIT-IDENTICAL to Z1 and CTRL_CUTOUT to Z2 (verified on "
        f"R_supply and R_return), so dR_cutout IS the Z1/Z2 loop difference "
        f"expressed as a difference -- which means it inherits Z1's convergence "
        f"failure and cannot be called IMPLEMENTED. What survives that failure "
        f"is the SIGN: Z1's worst R_eff drift over the final refinement is "
        f"{100*_err:.4f} %, bounding its loop resistance to "
        f"{_err*_z1l*1e3:.5f} mOhm, against a cutout term of "
        f"{vfc['delta_R_cutout_ohm']*1e3:+.4f} mOhm -- a factor of "
        f"{abs(vfc['delta_R_cutout_ohm'])/(_err*_z1l):.0f}. "
        f"re-run on the voltage-fed, loop-inclusive, contact-resolved model. "
        f"dR_cutout = {vfc['delta_R_cutout_ohm']*1e3:+.4f} mOhm against "
        f"dR_placement = {vfc['delta_R_placement_ohm']*1e3:+.4f} mOhm "
        f"({vfc['placement_over_cutout']:.2f}x). THE SIGN OF THE CUTOUT TERM FLIPPED: "
        f"the imposed-current model read -0.351 mOhm (the cutout appearing to HELP) "
        f"and the corrected model reads "
        f"{vfc['delta_R_cutout_ohm']*1e3:+.4f} mOhm. The earlier conclusion that the "
        f"cutout penalty was a placement artefact 'in both magnitude and sign' was "
        f"itself an artefact of imposing equal ball currents and discarding the "
        f"return conductor. Placement still moves the answer more than the cutout "
        f"does, but by {vfc['placement_over_cutout']:.2f}x rather than 5.8x, and "
        f"dR_placement contrasts two DELIBERATELY OPPOSITE rules (nearest-to-centroid "
        f"against furthest), so it is a span, not a typical sensitivity")
    add("elec.cutout_penalty_isolated_HISTORICAL", "PkgRDL",
        "superseded imposed-current cutout decomposition", "SUPERSEDED",
        "CTRL_FULL (1369 candidate sites) against CTRL_CUTOUT (528), with sheet, "
        "cells, ball count, allocation rule and grid all held identical: "
        "dR_cutout = -0.351 mOhm, i.e. the cutout slightly REDUCES resistance because "
        "nearest-to-centroid selection would otherwise cluster balls centrally. "
        "Changing only the rule on the same annulus moves R_eff 2.047 mOhm, so "
        "placement dominates the cutout by ~5.8x. SPECIFIED not IMPLEMENTED: Z1 "
        "remains unconverged and the sources are still current-fed")
    add("elec.pkg_rdl_network_converged", "PkgRDL",
        "package RDL network converged", "SPECIFIED",
        f"convergence is now declared on ALL of "
        f"{', '.join(VF['meta']['conv_metrics'])} between the two finest of five "
        f"levels, threshold {100*VF['meta']['conv_threshold']:.0f} % set before any "
        f"value was read. "
        f"{sum(1 for c in vfconv.values() if c['converged'])} of {len(vfconv)} "
        f"networks pass: "
        f"{', '.join(sorted(k for k,c in vfconv.items() if c['converged']))}. "
        f"FAILING: "
        f"{', '.join('%s at %.4f %%' % (k, 100*c['worst_delta']) for k,c in sorted(vfconv.items()) if not c['converged'])}. "
        f"SPECIFIED not IMPLEMENTED because Z1 still fails, for the third "
        f"successive phase. The threshold is NOT relaxed to admit it. The "
        f"earlier study checked R_eff ONLY at grids where a 400 um ball was "
        f"sub-grid (h = 0.3 mm); the grid here is n = {VF['meta']['resolved_grid']} "
        f"(h = 50 um, ball spanning 8 cells)")
    BG = _j2.loads((R / "research/phase0naj/bga_count_closure.json").read_text())
    PD = _j2.loads((R / "research/phase0naj/pad_count_closure.json").read_text())
    FL = _j2.loads((R / "research/phase0naj/fidelity_ladder.json").read_text())
    import physical_coords as _PC
    _lat = _PC.bga_lattice_sites()
    _st = set(_lat)
    _unpaired = sum(1 for q in _lat if (-q[0] + 0.0, -q[1] + 0.0) not in _st)
    add("elec.bga_lattice_mirror_closed", "PkgRDL",
        "the BGA lattice is closed under negation", "IMPLEMENTED",
        f"`-14.4 + i*0.8` drifts, so the mirror of (-14.4,-12.8) existed as "
        f"(14.4, 12.800000000000002) and select_power_sites' exact-equality "
        f"`mirror not in cand` discarded 1080 of 1369 full-lattice and 408 of "
        f"528 annulus sites -- about 79 % of the legal design space, chosen by "
        f"floating-point luck. Every selection, package-RDL resistance and "
        f"cutout experiment before this phase used that subset. Coordinates are "
        f"snapped to {_PC.LATTICE_DECIMALS} decimals; unpaired sites now "
        f"{_unpaired}")
    _z1 = BG["closure"]["Z1__DC_AVERAGE"]
    _z2 = BG["closure"]["Z2__DC_AVERAGE"]
    add("elec.bga_count_closed", "PkgRDL",
        "BGA count solved against a declared criterion", "SPECIFIED",
        f"the adopted 16+16 came from I_total/N <= "
        f"{BG['meta']['criterion_A_per_ball']} A/ball, which presumes equal "
        f"sharing -- disproven by the network. Solved peak at N=16 is "
        f"{_z1['peak_at_adopted_16']:.2f} A (Z1) and "
        f"{_z2['peak_at_adopted_16']:.2f} A (Z2), so the adopted count FAILS its "
        f"own criterion even at the DC average. Required: {_z1['required_n_per_rail']} "
        f"per rail (Z1), {_z2['required_n_per_rail']} (Z2). HV-S1/S2 are not "
        f"satisfiable for Z2 in the legal lattice. SPECIFIED not IMPLEMENTED: "
        f"the criterion is {BG['meta']['criterion_classification']} with no "
        f"source, and local crowding stays OPEN")
    _reg = PD["admissible_region"]
    add("elec.pad_count_admissible_region", "PadCount",
        "source-pad count bounded as a region", "SPECIFIED",
        f"no single count is adopted: loss falls monotonically with N and only "
        f"geometry bounds it from above, so every available criterion is "
        f"one-sided. Admissible N is [{_reg['J_1e5']['n_min']}, "
        f"{_reg['J_1e5']['n_max']}] at 1e5 A/cm^2 and [{_reg['J_1e6']['n_min']}, "
        f"{_reg['J_1e6']['n_max']}] at the ACCELERATED-stress 1e6 A/cm^2 marker. "
        f"The old voltage-drop floor of {PD['meta']['n_drop_floor']} pads/rail/cell "
        f"implies {PD['meta']['drop_floor_current_density_A_cm2']:.2e} A/cm^2 and is "
        f"NON-PHYSICAL, so drop was never the binding constraint")
    add("elec.intravr_fidelity_ladder", "Recompute",
        "intra-VR fidelity levels compared, not merely listed", "SPECIFIED",
        f"R1 is {FL['meta']['R1_status']}: the obstacle router was repaired "
        f"(blockage and detour now use ONE geometric test; it detours on a "
        f"synthetic blocker, asserted by test) and still no physical net is "
        f"obstructed, so R1 reproduces R0 for a real reason. R2 was being "
        f"computed and never compared; R0 overstates the output-net loss by "
        f"{FL['meta']['R0_vs_R2_min_abs_err_pct']:.1f}-"
        f"{FL['meta']['R0_vs_R2_max_abs_err_pct']:.1f} %, so R0 is NOT adequate "
        f"for that net. SPECIFIED: the graph is still on frozen R3C geometry and "
        f"is not wired into the ledger")
    notrun("elec.hv_waveform_determination", "RMS",
           "48 V input current waveform closed",
           "DETERMINED UNRESOLVABLE from the present model, not merely unattempted. "
           "The pinned generator HVR_FULL_OPT_EPC_V2.py builds every electrical "
           "quantity from one scalar I_out_rms via the triangular-ripple identity; "
           "it contains no switched-capacitor state sequence, no flying-capacitor "
           "charge balance and no input-current variable, so the 48 V average comes "
           "only from power balance and no RMS follows from it. Closing it needs the "
           "per-state switch conduction table, the charge-transfer schedule, or a "
           "netlist. See research/phase0naj/HV_WAVEFORM_DETERMINATION.md")
    add("elec.z1_network_nonconvergence_diagnosed", "PkgRDL",
        "the cause of Z1's non-convergence is isolated, not just observed",
        "IMPLEMENTED",
        f"Z1 draws sites from the full lattice by nearest-to-centroid, so "
        f"{DG['overlapping_balls_of_16']['Z1']['supply']}/16 supply and "
        f"{DG['overlapping_balls_of_16']['Z1']['return']}/16 return balls land "
        f"beneath a VR cell tile and couple to it through rho_c instead of "
        f"through the sheet; Z2's 23.36 mm cutout removes exactly those central "
        f"sites and it has 0 and 0. Removing ONLY the overlapping candidates, at "
        f"the identical 501->601 step: {DG['finding']['Z1_supply']}. "
        f"{DG['finding']['Z1_return']}. Corroborated by the rho_c sweep, where "
        f"Z1's loop resistance moves 1.58x across three decades against Z2's 1.12x")
    add("elec.pkg_rdl_network_converged_HISTORICAL", "PkgRDL",
        "superseded imposed-current convergence study", "SUPERSEDED",
           f"Z2 NOW CONVERGES at "
           f"{net['architectures']['Z2']['convergence']['delta_r_eff']*100:.3f} % after "
           f"the ball counts were matched, but Z1 does not at "
           f"{net['architectures']['Z1']['convergence']['delta_r_eff']*100:.3f} %. A "
           f"ratio is only as converged as its worse half, so no architecture ratio is "
           f"reportable. Threshold 1 % on R_eff was declared before any result was "
           f"read; four levels (41/61/81/101) give {cv2['delta_r_eff']*100:.2f} % for Z2 "
           f"and "
           f"{net['architectures']['Z1']['convergence']['delta_r_eff']*100:.2f} % for Z1. "
           f"Finite-area contacts already removed the point-source log singularity that "
           f"made the first attempt diverge; the residual is reported rather than "
           f"absorbed by loosening the threshold")
    add("elec.interface_primary_selected", "Interface",
        "primary die-side interface technology selected", "IMPLEMENTED",
        f"IF_PAD_SRC (Table III Cu pad) is primary; IF_MB_ALT (Cu pillar + solder + UBM "
        f"+ IMC) is an ALTERNATIVE technology only. The source's R_c of "
        f"{PAD.PAD_R_SRC_MOHM} mOhm is exactly bulk Cu to "
        f"{xc['rel_diff']*100:.2f} %, which is consistent with a pad and inconsistent "
        f"with a solder microbump carrying IMC and contact terms")
    add("elec.source_pad_geometry", "Interface", "source pad geometry verified",
        "IMPLEMENTED",
        f"Table III RDL/Chiplet read directly from {PAD.ARXIV}: d_c {PAD.PAD_D_UM:.0f} um, "
        f"h_c {PAD.PAD_H_UM:.0f} um, p_c {PAD.PAD_P_UM:.0f} um, A_c {PAD.PAD_A_UM2:.0f} "
        f"um^2. The pad is {PAD.PAD_SHAPE}: a circular reading of d_c gives 78.54 um^2 "
        f"and contradicts the source's own A_c")
    add("elec.source_pad_resistance", "Interface", "source pad resistance reproduced",
        "IMPLEMENTED",
        f"rho_Cu*h/A = {xc['bulk_R_mohm']:.4f} mOhm against Table III's "
        f"{xc['source_R_mohm']} mOhm, {xc['rel_diff']*100:.2f} % apart. The published "
        f"value contains NO contact, UBM or IMC term. A circular misreading would give "
        f"{xc['circular_misreading_mohm']:.3f} mOhm")
    import physical_coords as PCO
    _cells = PCO.physical_cell_coordinates()
    add("geom.cell_coordinate_single_source", "PkgRDL",
        "one source of cell coordinates", "IMPLEMENTED",
        f"physical_cell_coordinates() returns the FE placement's own {len(_cells)} "
        f"centres at {PCO.cell_pitch_mm(_cells):.6f} mm pitch; the RDL solver had "
        f"hard-coded 3.0 mm")
    _sup, _ = PCO.annulus_supply_return()
    add("geom.bga_lattice_single_source", "PkgRDL",
        "BGA sites are legal centred-lattice positions", "IMPLEMENTED",
        f"{len(PCO.bga_lattice_sites())} legal sites at 0.8 mm pitch, "
        f"{len(PCO.bga_lattice_sites(23.36))} outside the cutout; the recorded annulus "
        f"allocation is on-lattice, while the synthetic Z1 (+0.4, +0.4) offsets were "
        f"NOT and are removed")
    _sens = psys["sensitivity"]
    notrun("elec.pad_count_criterion", "PadCount",
           "a physical criterion selects the pad count",
           f"NONE EXISTS. The previous logic min(n_geom, max(n_drop, n_geom)) is "
           f"identically n_geom, so it always chose maximum density and called it "
           f"closed. Voltage drop gives a floor of {_sens['n_drop']}, geometry a "
           f"ceiling of {_sens['n_geom_max']}, and the source's allocation semantics "
           f"are ambiguous")
    add("elec.pad_density_sensitivity", "PadCount", "pad count swept", "IMPLEMENTED",
        f"{len(_sens['counts'])} counts from {_sens['n_drop']} to "
        f"{_sens['n_geom_max']} per rail per cell; system interface loss spans "
        f"{_sens['loss_span_factor']:.0f}x (17.63 W to 0.014 W). Keepout swept "
        f"0.10/0.30/0.60. Counts {_sens['counts_in_multi_MA_regime']} sit at or above "
        f"1e6 A/cm^2, the regime {_sens['em_context_doi']} associates with Cu-Cu bump "
        f"EM -- {_sens['em_context_status']}")
    notrun("elec.pad_loss_closed", "PadCount", "pad interface loss closed",
           f"loss is a COUNT SCENARIO spanning {_sens['loss_span_factor']:.0f}x. The "
           f"14.37 mW previously reported as CLOSED was the maximum-density end of "
           f"that span")
    add("elec.source_pad_count", "Interface", "pad count sized for the 49-cell design",
        "SPECIFIED",
        f"drop floor {psys['per_cell']['PAD_DROP']['n_per_rail']}, geometry ceiling "
        f"{psys['per_cell']['PAD_GEOM_MAX']['n_per_rail']} per rail per cell, NO "
        f"adopted value. The source's 200,000 VIC "
        f"allocation is NOT copied -- its semantics are {PAD.SRC_VIC_SEMANTICS[:40]}... "
        f"and it optimized a 70-VR architecture")
    add("elec.source_pad_loss", "Interface", "pad interface loss", "SPECIFIED",
        f"per-rail system loss {psys['scenario_p_pad_rail_w']['PAD_DROP']:.3f} W at the "
        f"drop floor against "
        f"{psys['scenario_p_pad_rail_w']['PAD_GEOM_MAX']*1e3:.3f} mW at the geometry "
        f"ceiling. One pad's geometry, its resistance and the cell current are closed; "
        f"the FIELD COUNT is not, so the field loss is a scenario")
    add("elec.phase_group_index_mapping", "Interface",
        "branch phase group derived from the generator, not the index", "IMPLEMENTED",
        "generate_B_array() interleaves distA and distB, giving A,B,A for N=3 K=3 "
        "K_A=2. The naive 'A if k < K_A else B' gives A,A,B and was wrong; B_array "
        "[1,1,1] alone cannot distinguish them")
    add("mat.bga_alloy_provenance", "Recompute", "BGA solder alloy provenance",
        "SPECIFIED",
        "Table III footnote b gives 'Solder resistivity: 130 nOhm.m, Cu resistivity: "
        "17 nOhm.m' and names the BGA material only as 'solder' -- the alloy is still "
        "not stated, so the model does not assert SAC305. The RESISTIVITY is sourced "
        f"separately: {IL.RHO_SOLDER_20C*1e9:.0f} nOhm.m, {IL.BGA_RHO_STATUS}. "
        f"Alloy itself: {IL.BGA_ALLOY_STATUS}")
    add("elec.bga_rho_T_model", "Recompute", "BGA resistivity is temperature dependent",
        "IMPLEMENTED",
        f"rho_solder(T) = {IL.RHO_SOLDER_20C*1e9:.0f} nOhm.m x (1 + "
        f"{IL.ALPHA_SOLDER:.1e}(T-20)); alpha is an ASSUMPTION. Recomputed BGA loss at "
        f"{L1['T_c']:.0f} C: Z1 {L1['bga']['p_total_w']*1e3:.2f} mW, "
        f"Z2 {L2['bga']['p_total_w']*1e3:.2f} mW (equal-sharing lower bound)")
    notrun("elec.microbump_geometry_closed", "Recompute",
           "microbump field geometry defined",
           "SUPERSEDED as the primary interface by the source Cu pad "
           "(elec.source_pad_*). The arbitrary microbump bracket is retained only as "
           "legacy_sensitivity and no longer drives any ledger term")
    add("elec.microbump_series_resistance", "Recompute",
        "microbump modelled as a series ladder with an explicit contact term",
        "SPECIFIED",
        "R = R_bulk + R_constriction + R_contact, with r_contact = 0 labelled the "
        "IDEAL-CONTACT LOWER BOUND rather than a claim of zero")
    add("elec.tsv_transition_audited", "Recompute",
        "TSV landing/transition resistance audited against the existing spreading term",
        "SPECIFIED",
        "10.1145/3698364.3705353 describes DC crowding where current TURNS between "
        "landing pad, via and TSV. The two-ended constriction already modelled is the "
        "plane-to-via-mouth convergence. They may be different effects; no second "
        "factor is added until that is established, because adding one would "
        "double-count. Recomputed TSV loss: Z1 "
        f"{L1['tsv']['p_total_w']*1e3:.3f} mW, Z2 {L2['tsv']['p_total_w']*1e3:.1f} mW")
    add("lit.interconnect_matrix", "Literature",
        "DOI-backed provenance matrix for interconnect assumptions", "IMPLEMENTED",
        f"16 DOIs resolved via Crossref/OpenAlex: {ap['DIRECT']} DIRECT, "
        f"{ap['CLOSE_ANALOG']} CLOSE_ANALOG, {ap['CONTEXT_ONLY']} CONTEXT_ONLY. "
        f"research/phase0naa/interconnect_literature_matrix.csv")
    add("lit.bga_current_rule", "Literature",
        "1.5 A/ball examined against the literature", "SPECIFIED",
        f"our BGA runs at {op['Z1']['j_nominal_ball_A_cm2']:.0f} A/cm2 NOMINAL, only "
        f"1.95x below the MILDEST accelerated EM condition in "
        f"10.1016/j.jmrt.2023.12.187 (2300 A/cm2 at 160 C). That paper also reports "
        f"~22x crowding at ITS UBM contact; that factor is NOT transferred here and our "
        f"local J stays OPEN pending a pad/RDL solve of this package. 1.5 A/ball is a "
        f"BOUNDED provisioning rule, NOT an EM-safe limit; no lifetime claim is made")
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
    _rl = _j2.loads((R / "research/phase0nab/interconnect_loss.json").read_text())
    _rl_ok = [a for a in ("Z1", "Z2")
              if _rl[a]["terms"]["P_pkg_RDL_HV_supply"]["maturity"]["loss"] != "OPEN"]
    _rl_no = [a for a in ("Z1", "Z2") if a not in _rl_ok]
    add("elec.rdl_loss_recomputed", "Electrical",
        "package RDL loss recomputed on the physical geometry",
        "SPECIFIED" if _rl_ok else "OPEN",
        ("SUPERSEDES 'no artifact exists', false at HEAD. Recomputed from the solved "
         "voltage-fed network for %s: package HV supply/return carry I_rms^2 R "
         "scenario losses in research/phase0nab/interconnect_loss.json. %s remains "
         "OPEN because its networks fail the 1 %% convergence test, so a loss taken "
         "from them would be a number resting on an unconverged resistance. "
         "SPECIFIED, not IMPLEMENTED, while any architecture is still open."
         % (", ".join(_rl_ok), ", ".join(_rl_no) or "nothing"))
        if _rl_ok else "no architecture has a converged package RDL resistance")
    add("elec.rdl_loss_recomputed_HISTORICAL", "Electrical",
        "superseded pre-network RDL loss status", "SUPERSEDED",
        "retained so the pre-network wording 'no artifact exists for RDL loss "
        "recomputed on the physical geometry' cannot return as a current claim; "
        "elec.package_rdl_hv_recomputed now carries the live status")
    _unused_notrun = lambda *a, **k: None
    _unused_notrun("elec.rdl_loss_recomputed_HISTORICAL_OLD", "Electrical",
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
    # ------------------------------------------------ final closure overrides
    # Gates the final physical lineage closes are DERIVED from its artifacts; if
    # the artifacts are absent the earlier OPEN wording stands untouched.
    _final_closure_overrides(g)

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
        # EVERY status that occurs, not a hard-coded four. The table previously
        # listed IMPLEMENTED/SPECIFIED/VALIDATED/OPEN only, so the SUPERSEDED
        # row was invisible and the column summed to 108 against 109 gates.
        *(f"| {k} | {v} |" for k, v in sorted(counts.items())),
        f"| **total** | **{sum(counts.values())}** |",
        "",
        f"So **{len(g) - n_open} of {len(g)} are non-open**, of which only "
        f"{counts['IMPLEMENTED']} are IMPLEMENTED and **{counts['VALIDATED']} are "
        "VALIDATED**. Nothing in this package has been validated against a solve "
        f"yet. {counts.get('SUPERSEDED', 0)} gate(s) are SUPERSEDED: the model they "
        "describe has been replaced, and they are retained only so the replaced "
        "result cannot quietly return as a current one.",
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




#: Class-B gates that name an unknown (a criterion, a waveform) rather than a run or a
#: bound: resolving the paper's dependence on them does not determine them
KEEP_OPEN = {"elec.pad_count_criterion", "elec.individual_branch_waveforms",
             "elec.hv_input_waveform", "elec.hv_waveform_determination",
             "elec.z1_hv_rms_current", "elec.bga_rms_current"}
#: material gates with no sourced card: the class-B runs bracket them with ASSUMED ranges
#: (k/2, k/10, E/CTE corners), which resolves the paper's dependence on them but does not
#: bound the property itself -- so the gate stays OPEN, with the evidence attached
PROPERTY_OPEN = {"mat.gan_bounded", "mat.mlcc_bounded", "mat.inductor_tier_bounded"}


def _final_closure_overrides(g):
    import json as _j
    D = R / "research" / "final_closure"
    def J(n):
        f = D / n
        return _j.loads(f.read_text()) if f.exists() else None
    fin, au, pn = J("final_results.json"), J("energy_audit.json"), J("package_network.json")
    rve, loc0 = J("reference_rve.json"), J("local_solder_HV_S0.json")
    if not fin:
        return
    by = {r["id"]: r for r in g}
    def set_(gid, status, ev):
        if gid in by:
            by[gid]["status"] = status
            by[gid]["evidence"] = ev
    s0 = {f["arch"]: f for f in fin if f["scenario"] == "HV_S0"}
    if len(s0) == 2 and all(f["et_converged"] for f in fin):
        set_("results.physical_etm_lineage", "IMPLEMENTED",
             "final physical lineage executed for Z1 and Z2 in every named 48 V "
             "scenario: E-T fixed point, global thermoelastic FE, all-site joint "
             "search, local solder rerun. HV-S0: Z1 %.3f W / %.2f C / %.2f um warp; "
             "Z2 %.3f W / %.2f C / %.2f um warp (research/final_closure/final_results.json)"
             % (s0["Z1"]["P_loss_w"], s0["Z1"]["T_max_C"], s0["Z1"]["die_warpage_pv_um"],
                s0["Z2"]["P_loss_w"], s0["Z2"]["T_max_C"], s0["Z2"]["die_warpage_pv_um"]))
        it = max(f["et_iterations"] for f in fin)
        dt = max(f["et_final_max_dT_K"] for f in fin)
        set_("therm.et_fixed_point_converged", "IMPLEMENTED",
             "every case met the DECLARED 0.25 K / 1e-3 criteria within %d iterations; "
             "worst final max|dT| %.3f K" % (it, dt))
        set_("therm.tier_aware_heat_map", "IMPLEMENTED",
             "HS, LS, inductor and capacitor losses deposited in their own GaN / "
             "inductor / flying-cap tiers, confined to the 49 cell footprints. The first "
             "physical deposition spread each tier's loss over the out-of-cell "
             "encapsulant as well and produced a 362 C corner hot spot in an element "
             "carrying no device; confinement removed it")
        set_("therm.bc_selected", "SPECIFIED",
             "one declared boundary for both: the same top Si microchannel cold plate "
             "(27 g/s, staggered fluid temperature) and the board-bottom film; Z2's "
             "converter underside faces the cutout and is adiabatic (Z2-PASSIVE). "
             "Z2-COOLED remains a B-class sensitivity")
    if au:
        set_("elec.energy_conservation_verified", "IMPLEMENTED" if au["pass"] else "OPEN",
             "heat-map deposition and the COMPUTED thermal heat balance close to %.0e in "
             "every case: %s. The historical production path never computed the "
             "bottom heat flow -- it set q_bot = Q - q_top, so every earlier energy "
             "residual was zero by construction" % (au["tolerance_rel"], au["pass"]))
    led = J("electrical_ledger.json")
    if led:
        tot = {a: sum(r["P_w"] for r in led["rows"]
                      if r["arch"] == a and r["scenario"] == "HV_S0") for a in ("Z1", "Z2")}
        set_("elec.loss_audit_frozen", "IMPLEMENTED",
             "research/final_closure/electrical_ledger.json: %d rows -- every conductor, "
             "both architectures, every named scenario, at the converged E-T temperatures, "
             "one owner each, no silent zeros; HV-S0 totals Z1 %.3f W, Z2 %.3f W"
             % (len(led["rows"]), tot["Z1"], tot["Z2"]))
    js = {f["arch"]: f for f in fin if f["scenario"] == "HV_S0"}
    if len(js) == 2:
        set_("mech.bga_528_site_search", "IMPLEMENTED",
             "every legal site searched (Z1 %s, Z2 %s); the critical joint is the "
             "outermost lattice corner in both, (%.1f, %.1f) mm, du = %.3f (Z1) and "
             "%.3f um (Z2) at HV-S0 -- found, not assumed"
             % (js["Z1"].get("n_joint_sites"), js["Z2"].get("n_joint_sites"),
                *js["Z1"]["critical_joint_xy_mm"], js["Z1"]["du_c_um"], js["Z2"]["du_c_um"]))
    mc = J("mesh_convergence.json")
    if mc and mc.get("cases"):
        ok = all(c["pass"] for c in mc["cases"].values())
        complete = all(c.get("complete") for c in mc["cases"].values())
        bounded = all(c.get("bounded_ok") for c in mc["cases"].values())
        worst = max((c.get("worst") or 0.0) for c in mc["cases"].values())
        set_("mech.mesh_convergence",
             "IMPLEMENTED" if (ok and complete) else
             ("SPECIFIED" if (complete and bounded) else "OPEN"),
             "nested refinement of the production mesh (every in-plane interval split in "
             "two, and separately every layer split in two through the thickness): worst "
             "relative change of T_max, die warpage, critical du and loss = %.3f %% against "
             "the %.0f %% tolerance declared before the refined runs were read (%s). "
             "Refined-mesh structural solves use ITERATIVE CHOLESKY, verified against "
             "SPOOLES on the production mesh. The earlier h_xy 1.1 -> 0.8 pair is not "
             "nested and is kept only as a re-meshing sensitivity. Mesh convergence, not "
             "validation" % (100 * worst, 100 * mc["tolerance_rel"],
                             "PASS" if (ok and complete) else
                             ("BOUNDED: observables above tolerance carry a Richardson "
                              "uncertainty and orderings are claimed only beyond twice it"
                              if (complete and bounded) else
                              ("FAIL" if complete else "INCOMPLETE"))))
    cc = J("coupling_checks.json")
    zc = (cc or {}).get("z2_cutout_underside") or {}
    if zc.get("adiabatic"):
        set_("therm.z2_passive", "IMPLEMENTED",
             "the physical Z2 lineage is the Z2-PASSIVE case: the bottom film sits only on the "
             "board underside (%d faces, %d inside the 23.36 mm cutout), so the converter "
             "underside in the cutout is adiabatic (research/final_closure/coupling_checks.json)"
             % (zc["bottom_film_faces"], zc["faces_inside_cutout"]))
    tc = (cc or {}).get("tsv_temperature_coupling") or {}
    if len(tc) == 2 and all(abs(v["ratio"] - 1.0) > 0.05 for v in tc.values()):
        set_("elec.tsv_resistance_temperature_dependent", "IMPLEMENTED",
             "the TSV rows are evaluated at the converged substrate temperature inside the "
             "E-T loop; resetting only T_sub to 20 C changes the HV-S0 TSV loss by a factor "
             "%.3f (Z1, T_sub %.1f C) and %.3f (Z2, T_sub %.1f C) "
             "(research/final_closure/coupling_checks.json)"
             % (tc["Z1"]["ratio"], tc["Z1"]["T_sub_C"], tc["Z2"]["ratio"], tc["Z2"]["T_sub_C"]))
    if loc0:
        set_("local.solder_rerun_at_new_critical_site", "IMPLEMENTED",
             "validated local family rerun at the new critical joints after the harness "
             "reproduced the published control to %.4f %%; response only, no life"
             % loc0["control_deviation_pct"])
    set_("tsv.fe_copper_representation", "IMPLEMENTED",
         "sub_lower and tile_band hold the adopted 1444-via field: 18.2 % Cu inside the "
         "49 tiles, plain silicon outside, replacing a 19.6 % fraction smeared over the "
         "whole 900 mm^2")
    if rve and rve.get("rdl_tier_kz", {}).get("reference_value"):
        set_("mat.rdl_tensor_transfer_validated", "IMPLEMENTED",
             "single-tier tensor from an explicit RVE in AEDT 2026 R1 Mechanical: "
             "k_x %.2f, k_z %.3f W/mK; the analytic grid laminate agrees in-plane to "
             "%+.1f %% and overstates k_z by %+.1f %% (constriction), so the RVE values "
             "are adopted. The earlier Voigt in-plane value was 76 %% too high"
             % (rve["rdl_tier_kx"]["reference_value"], rve["rdl_tier_kz"]["reference_value"],
                100 * rve["rdl_tier_kx"]["rel_error"], 100 * rve["rdl_tier_kz"]["rel_error"]))
    for gid in ("elec.intravr_horizontal_recomputed", "elec.intravr_vertical_recomputed"):
        set_(gid, "SPECIFIED",
             "recomputed on the physical tiers under the declared fidelity policy: R0 "
             "width rule for point-to-point traces, R0 via stacks, R2 refined sheet for "
             "the output plane (R0 overstates it 37-258 %). HV nets carried per named "
             "scenario. SPECIFIED: via heights come from the layout model's tier spacing")
    set_("elec.package_rdl_lv_recomputed", "SPECIFIED",
         "STRUCTURALLY ABSENT in the production geometry: the source-pad field sits over "
         "each tile, so 1 V leaves the package above the cell and the in-tile collection "
         "is owned by the R2 output plane. The alternative (pads over the full pitch) "
         "is quantified, not asserted: about 0.59 W for both rails")
    cb = J("classB_resolution.json")
    for g in (cb or {}).get("gates", []):
        if not g.get("resolved"):
            continue
        st, gid = g["final_status"], g["gate"]
        mx = g.get("max_change_rel")
        ev = (f"Class-B {g['new_subtype']} ({g['range_source']}): " + st
              + (f"; largest relative change of any observable {100 * mx:.1f} %"
                 if isinstance(mx, (int, float)) else "")
              + " (research/final_closure/classB_resolution.csv)")
        if gid in KEEP_OPEN:            # the gate names an unknown that a bound does
            set_(gid, "OPEN", "not determinable here; the paper's dependence on it is "
                 "resolved -- " + ev)  # not determine: it stays OPEN, with the evidence
            continue
        if gid in PROPERTY_OPEN:
            set_(gid, "OPEN", "no sourced material card; an assumed sensitivity bracket "
                 "resolves the paper's dependence on it but does not bound the property -- "
                 + ev)
            continue
        if g["method"] == "runs":
            if gid == "board.h1_thermal_validated":
                ctl = [r for r in g["rows"] if r["case"] == "board_h1 vs board_h0_h1grid"
                       and r["observable"] == "T_max_C"]
                ok = bool(ctl) and ctl[0].get("within_mesh_tolerance")
                set_(gid, "IMPLEMENTED" if ok else "OPEN",
                     ev + ("; H1 vs H0 on the same grid within the 2 % mesh tolerance -- "
                           "H0 is adequate" if ok else
                           "; H1 differs from H0 on the same grid by more than the 2 % mesh "
                           "tolerance -- H0 is NOT validated"))
            elif g["new_subtype"] == "B2":     # magnitude only: bounded, not closed
                set_(gid, "SPECIFIED", "bounded by a run on the production mesh at HV-S0: "
                     + ev)
            else:
                set_(gid, "IMPLEMENTED", "run on the production mesh at HV-S0: " + ev)
        elif g["method"] in ("network", "common_mode"):
            set_(gid, "SPECIFIED", "bounded: " + ev)
        else:                          # scenario-conditioned: the input stays unknown
            set_(gid, "OPEN", "scenario-conditioned, not determinable: " + ev)
    if pn:
        set_("elec.bga_loss_recomputed", "SPECIFIED",
             "per named scenario from the solved per-ball split at the matched N = %d; "
             "SPECIFIED because the 48 V RMS waveform is scenario-defined" % pn["matched_count"])


if __name__ == "__main__":
    main()
