"""Class-B sensitivities on the production lineage (headline scenario, production mesh).

Each variant changes ONE declared input of the physical Z1/Z2 packages and runs the same
E-T fixed point, thermoelastic solve and all-site joint search as the production cases.
Results go to research/final_closure/sensitivity/etm_{ARCH}_{SCEN}__{VARIANT}.json; the
production case files are never touched, and the production path is unchanged (the hooks
in final_closure_physical_etm are empty unless a variant sets them in its own process).

Two kinds:
  full   electrical-thermal fixed point + mechanics, because the variant changes heat
         paths or losses
  mech   mechanics only, on the CONVERGED production temperature field, because the
         variant changes only stiffness and expansion (asserted: the field's peak must
         equal the production case's to 1e-6 K)

Variants that are bounding stress tests, not property claims, say so in `nature`.

    python final_closure_sensitivity.py [VARIANT[:ARCH] ...]     (default: all)
"""
from __future__ import annotations

import copy
import json
import multiprocessing as mp
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402
from hvr_scratch import path as scratch                             # noqa: E402

OUT = R / "research" / "final_closure" / "sensitivity"
SCEN = "HV_S0"
#: converged production temperature fields kept outside the repo (scratch), see README
FIELDS = Path(os.environ.get("HVR_FIELDS", Path.home() / "claude_scratch" / "hvr_work"
                             / "fields"))
HOMOG = R / "research" / "phase0nv" / "pcb_homogenization.json"
CONV_TIERS = ("flying_caps", "inductor_plus_cout")


# ------------------------------------------------------------------ board variants
def eta_material(eta):
    """The IT-968G board card at copper coverage eta, by the SAME rule that derives the
    production card (research/phase0nv nominal_tensor: in-plane E and CTE of the sweep
    row, midpoint of each bounded conductivity bracket). At eta = 0.5 it must reproduce
    the production card exactly -- checked in board_case_check()."""
    h = json.loads(HOMOG.read_text())
    row = next(r for r in h["sweep"] if abs(r["eta"] - eta) < 1e-12)
    mid = lambda b: 0.5 * (b[0] + b[1])
    return {"E_MPa": row["Ex_MPa"], "nu": h["nominal_tensor"]["nu"],
            "cte": row["cte_x"] * 1e-6, "k": mid(row["k_z_bounds"]),
            "k_ortho": [mid(row["k_xy_bounds"]), mid(row["k_xy_bounds"]),
                        mid(row["k_z_bounds"])]}


def board_case_check():
    import board as BRD
    prod = {k: v for k, v in BRD.BOARD_CASES["it968g_2p4mm"].items() if k != "t_mm"}
    mine = eta_material(0.5)
    for k, v in prod.items():
        a, b = np.atleast_1d(v), np.atleast_1d(mine[k])
        if not np.allclose(a, b, rtol=1e-12, atol=0.0):
            raise RuntimeError(f"eta rule does not reproduce the production board: {k}")


def v_board_thickness(case, t_um):
    import physical_package as PP
    z1o, z2o = PP.load_z1_package_config, PP.load_physical_package_config
    PP.load_z1_package_config = lambda path=None: replace(
        z1o(path), board_case=case, board_thickness_um=t_um)
    PP.load_physical_package_config = lambda path: replace(
        z2o(path), board_case=case, board_thickness_um=t_um)


def v_board_eta(eta):
    import board as BRD
    board_case_check()
    t = BRD.BOARD_CASES["it968g_2p4mm"]["t_mm"]
    BRD.BOARD_CASES["it968g_2p4mm"] = dict(eta_material(eta), t_mm=t)


def v_board_h1(h0_material=False):
    """PCB-H1: the 18-layer schedule as five depth blocks (scripts/phase0nw/pcb_h1.py),
    each its own material. The blocks keep the layer NAME 'board' so the cutout, the
    board-bottom film and the 3-2-1 restraint treat them exactly as the H0 slab.
    h0_material=True is the CONTROL: the H0 card on the same five-block z grid, so the
    H0 -> H1 difference separates material representation from z discretisation."""
    import board as BRD
    import pcb_h1 as H1
    t = BRD.BOARD_CASES["it968g_2p4mm"]["t_mm"]
    lo, so = BRD.bottom_layers, BRD.stack_with_board

    def bottom_layers(case="fr4_1p6mm", nz_board=2, nz_bga=2):
        base = lo(case, nz_board, nz_bga)
        if case != "it968g_2p4mm" or base[0][0] != "board":
            raise RuntimeError(f"H1 variant applied to an unexpected board stack {base}")
        blocks = [("board", b[1], "board_fr4" if h0_material else b[2], b[3])
                  for b in H1.bottom_layers(t, 0.50, nz=1)]
        if abs(sum(b[1] for b in blocks) - base[0][1]) > 1e-12:
            raise RuntimeError("H1 blocks do not add up to the board thickness")
        return blocks + base[1:]

    def stack_with_board(stack, t_tile_mm, case="fr4_1p6mm"):
        st = so(stack, t_tile_mm, case)
        if not h0_material:
            st["materials"].update(H1.board_materials(t, 0.50))
        return st
    BRD.bottom_layers, BRD.stack_with_board = bottom_layers, stack_with_board


# ------------------------------------------------------------------ TSV density
def v_tsv(n_side):
    """The same field change in the FE substrate AND in the electrical ledger: an
    n_side x n_side checkerboard at the largest pitch that fits (tsv_fields.lattice_for_n,
    the sizing study's own lattice)."""
    import tsv_fields as TF
    E.TSV_N_PER_CELL = n_side * n_side
    orig = TF.system_report

    def system_report(cells, cell_side_mm, h_tsv_mm, i_total_a, n_per_cell=None, **kw):
        pitch, _nv, _ng = TF.lattice_for_n(cell_side_mm, n_side)
        r = orig(cells, cell_side_mm, h_tsv_mm, i_total_a,
                 pitch_mm=pitch * (1.0 - 1e-12), **kw)
        if r["per_cell"]["n_total"] != n_side * n_side:
            raise RuntimeError(f"lattice gave {r['per_cell']['n_total']} vias, "
                               f"not {n_side * n_side}")
        return r
    TF.system_report = system_report


# ------------------------------------------------------------------ fill, cooling
def v_out_of_cell(case):
    import physical_package as PP
    o1, o2 = PP.build_physical_z1, PP.build_physical_package
    PP.build_physical_z1 = lambda cfg=None, h_xy=1.1, out_of_cell=None: o1(cfg, h_xy, case)
    PP.build_physical_package = (lambda cfg, h_xy=1.1, discrete_cells=True,
                                 out_of_cell=None: o2(cfg, h_xy, discrete_cells, case))


def v_f1_clearance():
    """F1 with the specified 1.0 mm sidewall clearance OPEN (DEFECT #66). Production F1
    fills the whole 23.36 mm PCB opening with encapsulant, bonding the Z2 converter block to
    the PCB sidewall, although the stack specifies a clearance between the 21.36 mm cell
    grid and the opening. Here the encapsulant stays between the cells (inside the cell-grid
    bounding box) and the clearance ring is void; nodes are compacted as the F2 builder does.
    Z2 only: Z1 has no opening."""
    def hook(m, st, tiles):
        cen = m.elem_centroids()
        lay = np.array(m.elem_layer, dtype=object)
        x0 = min(t.cx - t.ax / 2 for t in tiles); x1 = max(t.cx + t.ax / 2 for t in tiles)
        y0 = min(t.cy - t.ay / 2 for t in tiles); y1 = max(t.cy + t.ay / 2 for t in tiles)
        conv = np.array([str(l).startswith("conv_") for l in lay])
        ring = conv & ((cen[:, 0] < x0 - 1e-9) | (cen[:, 0] > x1 + 1e-9)
                       | (cen[:, 1] < y0 - 1e-9) | (cen[:, 1] > y1 + 1e-9))
        if ring.any() and set(np.array(m.elem_material, dtype=object)[ring]) != {"underfill_homog"}:
            raise RuntimeError("the clearance ring holds something other than the encapsulant")
        keep = ~ring
        m.elems = m.elems[keep]
        m.elem_material = np.array(m.elem_material, dtype=object)[keep]
        m.elem_layer = lay[keep]
        m.elem_tile = np.asarray(m.elem_tile)[keep]
        used = np.unique(m.elems.ravel())
        newid = np.zeros(len(m.nodes) + 1, dtype=m.elems.dtype)
        newid[used] = np.arange(1, len(used) + 1)
        n0 = len(m.nodes)
        m.elems = newid[m.elems]
        m.nodes = m.nodes[used - 1]
        return {"variant_elements_removed": int(ring.sum()),
                "variant_nodes_removed": int(n0 - len(m.nodes)),
                "cell_grid_bbox_mm": [x0, x1, y0, y1]}
    E.BUILD_HOOKS.append(hook)


def v_z2_cooled():
    """Z2-COOLED, bounding: a second cold plate of the SAME kind as the top one (uniform
    h of the top microchannel plate at the dissipated power, fluid at the inlet
    temperature) on the whole converter underside inside the PCB opening. The strongest
    backside cooling this model can state without inventing a new cooler."""
    from cooling_production import CANDIDATES
    cooler = CANDIDATES[E.COOLER]

    def film(m, tiles, q_w):
        inside = [L for L in m.layers if L.region == "inside_cutout"]
        deepest = min(inside, key=lambda L: L.z0)
        ids = m.elem_set(layer=deepest.name)
        keep = [e for e in ids
                if abs(m.nodes[m.elems[e - 1] - 1][:, 2].min() - deepest.z0) < 1e-9]
        return {"elems": np.array(keep, int), "h_W_m2K": float(cooler.h_uniform(q_w)),
                "T_C": float(cooler.t_in_c), "layer": deepest.name,
                "label": "second top-type cold plate on the converter underside"}
    E.EXTRA_FILM = film


# ------------------------------------------------------------------ pad count
def v_pad_drop():
    """The 1 V source-pad field at its voltage-drop FLOOR (pad_interface.size_for_cell
    PAD_DROP: the fewest pads per rail per cell that meet the drop budget) instead of the
    production SOURCE_ANCHORED count. Both architectures carry the same pad field and
    current, so the electrical change is common-mode; this run shows what the extra
    interface heat does to temperatures and mechanics. A range END, not a design: the
    floor puts several MA/cm^2 through each pad."""
    import final_closure_ledger as FL
    import pad_interface as PAD
    import rms_currents as RMS
    n = PAD.size_for_cell(RMS.cell_currents()["i_cell_out_rms_a"])["PAD_DROP"]["n_per_rail"]
    orig = FL.pad_count
    FL.PAD_CASES["PAD_DROP"] = "voltage-drop floor of the pad sweep (range end, not a design)"
    FL.pad_count = lambda case: n if case == "PAD_DROP" else orig(case)
    FL.ledger.__defaults__ = ("PAD_DROP",)          # the ledger's pad_case default


# ------------------------------------------------------------------ tier materials
def _retag(m, st, new, base, card_edit, layer_has, base_mat):
    card = copy.deepcopy(st["materials"][base])
    card_edit(card)
    card["status"] = "ASSUMPTION"
    card["note"] = "class-B sensitivity bound (final_closure_sensitivity.py), not a property"
    st["materials"][new] = card
    mat = np.array(m.elem_material, dtype=object)
    lay = np.array(m.elem_layer, dtype=object)
    sel = np.array([any(t in str(l) for t in layer_has) for l in lay]) & (mat == base_mat)
    mat[sel] = new
    m.elem_material = mat
    return int(sel.sum())


def v_gan_k_half():
    """GaN epi bound: the two device tiers are meshed as their Si carrier. Halving the
    tier conductivity adds t_tier/k_Si of through-thickness resistance (4.9e-6 and
    5.3e-6 m^2K/W for the 638 and 685 um tiers at 130 W/mK) -- more than any epi stack
    with t_epi/k_epi below that can add, e.g. 10 um at k > 2.1 W/mK. A stress bound,
    not a GaN property."""
    def hook(m, st, tiles):
        def edit(c):
            c["k"] = {"value": st["materials"]["silicon"]["k"]["value"] / 2.0,
                      "status": "ASSUMPTION"}
        n = _retag(m, st, "gan_tier_bound", "silicon", edit, ("gan_",), "silicon")
        return {"variant_elements_retagged": n}
    E.BUILD_HOOKS.append(hook)


def v_conv_k(factor):
    """Converter-medium conductivity bound: the flying-cap and inductor/Cout tiers carry
    the generic hvr_effective card (k 60 W/mK, PROVISIONAL, no sourced MLCC/ferrite
    card in the framework). Reducing it tenfold is a declared stress test."""
    def hook(m, st, tiles):
        def edit(c):
            c["k"] = {"value": st["materials"]["hvr_effective"]["k"]["value"] * factor,
                      "status": "ASSUMPTION"}
        n = _retag(m, st, "hvr_effective_k_bound", "hvr_effective", edit, CONV_TIERS,
                   "hvr_effective")
        return {"variant_elements_retagged": n}
    E.BUILD_HOOKS.append(hook)


def v_conv_mech(E_mpa, cte):
    """A corner of the converter medium's OWN declared range (package_stack.yaml:
    'Sensitivity E = 80-160 GPa, CTE 4-10 ppm/K'). Conductivity unchanged."""
    def hook(m, st, tiles):
        def edit(c):
            c["E"] = {"value": E_mpa, "status": "ASSUMPTION"}
            c["cte"] = {"value": cte, "status": "ASSUMPTION"}
        n = _retag(m, st, "hvr_effective_corner", "hvr_effective", edit, CONV_TIERS,
                   "hvr_effective")
        return {"variant_elements_retagged": n}
    E.BUILD_HOOKS.append(hook)


VARIANTS = {
    "board_t3p2": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_thickness(
        "it968g_3p2mm", 3200.0), gates=["board.t_only_comparison_run",
                                        "mech.t_only_mechanical"],
        nature="declared case (config thickness_sensitivity_case)",
        what="PCB 3.2 mm instead of 2.4 mm, same IT-968G material dict"),
    "board_eta025": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_eta(0.25),
                         gates=["board.eta_sensitivity_run"],
                         nature="declared range (config eta_sensitivity)",
                         what="board copper coverage eta = 0.25 instead of 0.50"),
    "board_eta075": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_eta(0.75),
                         gates=["board.eta_sensitivity_run"],
                         nature="declared range (config eta_sensitivity)",
                         what="board copper coverage eta = 0.75 instead of 0.50"),
    "board_h1": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_board_h1(False),
                     gates=["board.h1_meshed", "board.h1_thermal_validated",
                            "therm.h0_h1_compared"],
                     nature="model-form check of the homogenised board",
                     what="PCB-H1: five depth blocks with their own copper fractions"),
    "board_h0_h1grid": dict(kind="full", archs=("Z1", "Z2"),
                            apply=lambda: v_board_h1(True),
                            gates=["board.h1_meshed", "therm.h0_h1_compared"],
                            nature="control for board_h1",
                            what="the H0 card on the H1 five-block z grid"),
    "tsv_min": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_tsv(8),
                    gates=["tsv.density_sensitivity_run"],
                    nature="declared range (TSV sizing study: electrical minimum)",
                    what="64 vias/cell (8 x 8) instead of 1444, FE substrate and ledger"),
    "tsv_mid": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_tsv(27),
                    gates=["tsv.density_sensitivity_run"],
                    nature="declared range (TSV sizing study: mid)",
                    what="729 vias/cell (27 x 27) instead of 1444, FE substrate and ledger"),
    "f2_void": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_out_of_cell("F2_void"),
                    gates=["mech.f1_f2_bracket_run"],
                    nature="declared bracket (z2_converter.OUT_OF_CELL)",
                    what="out-of-cell converter-tier volume void instead of encapsulated"),
    "f1_clearance": dict(kind="full", archs=("Z2",), apply=v_f1_clearance,
                         gates=["mech.f1_f2_bracket_run"],
                         nature="model-form check (DEFECT #66: specified sidewall clearance)",
                         what="encapsulant between the cells, the 1.0 mm clearance to the PCB "
                              "sidewall void"),
    "z2_cooled": dict(kind="full", archs=("Z2",), apply=v_z2_cooled,
                      gates=["therm.z2_cooled"],
                      nature="bounding case (strongest backside cooling the model states)",
                      what="top-type cold plate on the Z2 converter underside"),
    "pad_drop": dict(kind="full", archs=("Z1", "Z2"), apply=v_pad_drop,
                     gates=["elec.pad_count_criterion", "elec.pad_loss_closed"],
                     nature="declared range end (pad sweep: voltage-drop floor)",
                     what="1 V source pads at the drop floor (4 per rail per cell) "
                          "instead of 2040"),
    "gan_k_half": dict(kind="full", archs=("Z1", "Z2"), apply=v_gan_k_half,
                       gates=["mat.gan_bounded"], nature="bounding stress test",
                       what="GaN device tiers at half the Si carrier conductivity"),
    "conv_k_tenth": dict(kind="full", archs=("Z1", "Z2"), apply=lambda: v_conv_k(0.1),
                         gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded"],
                         nature="bounding stress test",
                         what="flying-cap and inductor/Cout tiers at k = 6 W/mK"),
}
for _E in (80e3, 160e3):
    for _a in (4e-6, 10e-6):
        VARIANTS[f"conv_E{_E / 1e3:.0f}_a{_a * 1e6:.0f}"] = dict(
            kind="mech", archs=("Z1", "Z2"),
            apply=(lambda E_=_E, a_=_a: v_conv_mech(E_, a_)),
            gates=["mat.mlcc_bounded", "mat.inductor_tier_bounded"],
            nature="declared range (package_stack.yaml hvr_effective)",
            what=f"converter medium E = {_E / 1e3:.0f} GPa, CTE = {_a * 1e6:.0f} ppm/K")


def case_file(arch, variant, scen=SCEN):
    return OUT / f"etm_{arch}_{scen}__{variant}.json"


def _spec(variant):
    v = VARIANTS[variant]
    return {"name": variant, "kind": v["kind"], "gates": v["gates"],
            "nature": v["nature"], "what": v["what"]}


def run_full(arch, variant):
    E.WD = scratch("fc_sens", variant)
    VARIANTS[variant]["apply"]()
    E._raise_stack_limit()
    h, r = E.PRODUCTION_H_XY, E.PRODUCTION_REFINE
    m, mats, st, tiles, minfo, L, th, hist, t_et, wd = E.run_et(arch, SCEN, h, r)
    res = {"arch": arch, "scenario": SCEN, "h_xy_mm": h, "refine": list(r),
           "variant": _spec(variant), "materials": minfo,
           "ledger_rows": L["rows"], "P_loss_w": L["P_loss_w"],
           "i_hv_avg_a": L["i_hv_avg_a"], "energy_ledger": L["energy"],
           "thermal": {k: v for k, v in th.items() if k != "T_node"},
           "et_history": hist,
           "et_converged": (hist[-1]["max_dT_K"] < E.ET_TOL_K
                            and hist[-1]["dP_rel"] < E.ET_TOL_P_REL),
           "et_wall_s": t_et, "threads": E.THREADS,
           "production_case": E.case_path(arch, SCEN).name}
    f = case_file(arch, variant)
    f.write_text(json.dumps(res, indent=1, default=float))
    try:
        res["mechanics"] = E.mechanics(m, mats, st, th["T_node"], wd, arch, tiles,
                                       E.PRODUCTION_SOLVER, 1)
    except Exception as e:                        # recorded, never silently dropped
        res["mechanics_error"] = str(e)[-600:]
    f.write_text(json.dumps(res, indent=1, default=float))
    return f.name, "mechanics" in res


def run_mech(arch, variant):
    import production_et as PE
    VARIANTS[variant]["apply"]()
    E._raise_stack_limit()
    base = json.loads(E.case_path(arch, SCEN).read_text())
    m, mats, st, tiles, minfo = E.build(arch, E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    frd = FIELDS / f"etm_{arch}_{SCEN}_r21" / "thermal_converged.frd"
    tn = PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]
    if abs(float(np.nanmax(tn)) - base["thermal"]["T_max_C"]) > 1e-6:
        raise RuntimeError(f"{frd} is not the converged field of {base['arch']}")
    res = {k: base[k] for k in ("arch", "scenario", "h_xy_mm", "refine", "ledger_rows",
                                "P_loss_w", "i_hv_avg_a", "energy_ledger", "thermal",
                                "et_history", "et_converged", "et_wall_s")}
    res.update({"variant": _spec(variant), "materials": minfo,
                "thermal_from": "production converged field (mechanics-only variant)",
                "production_case": E.case_path(arch, SCEN).name})
    try:
        res["mechanics"] = E.mechanics(m, mats, st, tn, scratch("fc_sens", variant, arch),
                                       arch, tiles, E.PRODUCTION_SOLVER, 1)
    except Exception as e:
        res["mechanics_error"] = str(e)[-600:]
    f = case_file(arch, variant)
    f.write_text(json.dumps(res, indent=1, default=float))
    return f.name, "mechanics" in res


def _task(t):
    arch, variant = t
    t0 = time.time()
    try:
        fn = run_full if VARIANTS[variant]["kind"] == "full" else run_mech
        name, ok = fn(arch, variant)
        return {"arch": arch, "variant": variant, "file": name, "mechanics_ok": ok,
                "wall_s": time.time() - t0}
    except Exception as e:                        # a crash is a recorded result
        return {"arch": arch, "variant": variant, "error": str(e)[-600:],
                "wall_s": time.time() - t0}


def _local_task(t):
    """The local response at a variant's own critical joint, at the SAME level and
    settings as the production pass-3 L0 solve (block-order extraction, split load step,
    the temporal study's first increment), so variant and production differ only in the
    joint's du and temperature."""
    arch, variant = t
    import final_closure_local_mesh as LM
    c = json.loads(case_file(arch, variant).read_text())
    crit = c["mechanics"]["joint_search"]["critical"]
    inc0 = json.loads(LM.TIME_STUDY.read_text())["production_dt0_s"]
    r = LM._solve(f"{arch}_{variant}", crit["du_um"], crit["T_C"],
                  scratch("fc_sens_local", variant, arch), "L0", inc0, True)
    return arch, variant, r


def _needs_local(a, v):
    if not case_file(a, v).exists():
        return False
    c = json.loads(case_file(a, v).read_text())
    if "mechanics" not in c:
        return False
    crit, loc = c["mechanics"]["joint_search"]["critical"], c.get("local") or {}
    return not (loc.get("d_peeq_per_cycle") and loc.get("du_um") == crit["du_um"]
                and loc.get("T_joint_C") == crit["T_C"])


def local_main(names):
    tasks = [(a, v) for v in (names or list(VARIANTS)) for a in VARIANTS[v]["archs"]
             if _needs_local(a, v)]
    if not tasks:
        print("no variant needs a local solve", flush=True)
        return
    with mp.Pool(min(len(tasks), 24)) as p:
        out = p.map(_local_task, tasks, chunksize=1)
    for arch, variant, r in out:
        f = case_file(arch, variant)
        c = json.loads(f.read_text())
        c["local"] = r
        f.write_text(json.dumps(c, indent=1, default=float))
        print(arch, variant, r["d_peeq_per_cycle"], r["error"], flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if sys.argv[1:2] == ["--local"]:
        return local_main(sys.argv[2:])
    tasks = []
    for a in (sys.argv[1:] or list(VARIANTS)):
        v, *arch = a.split(":")
        tasks += [(x, v) for x in (arch or VARIANTS[v]["archs"])]
    with mp.Pool(len(tasks)) as p:
        out = p.map(_task, tasks)
    log = OUT / "run_log.json"
    old = json.loads(log.read_text()) if log.exists() else []
    log.write_text(json.dumps(old + out, indent=1, default=float))
    for r in out:
        print(r, flush=True)


if __name__ == "__main__":
    main()
