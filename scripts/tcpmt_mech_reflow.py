"""Finding 5 -- isothermal warpage at the reflow / bonding temperature, against coplanarity
limits.

The operational chain measures warpage against a 25-C stress-free state at the steady
operating field. Assembly needs a different question: is the part flat enough, AT the
joining temperature, for the joints to form? Each architecture is checked for both joints it
makes (configs/tcpmt_mech: reflow):

  bga   the unmounted package (no board, no BGA layer, no TIM; for Z3 also without the
        converter, which sits on the board) at the SAC305 reflow peak and solidus; the
        measure is the BGA plane (substrate underside) over the ball-lattice footprint
  tcb   the fine-pitch joint: Z1 die onto the converter top (the die is flat silicon at a
        uniform temperature, so the receiving surface alone sets the gap), Z2 converter onto
        the substrate underside (30-um Cu pillar, thermocompression), Z3 converter onto the
        board underside (100-um SAC bump reflow); both mating parts are solved separately
        and the gap non-uniformity is the plane-removed peak-to-valley of the difference of
        their surface displacements over the joint footprint

Every part is a layer subset of the production mesh (same nodes, same cards), solved with a
uniform temperature from the stated stress-free reference (25 C, as the operational model;
an encapsulant-cure reference of 150 C is reported by exact linear scaling for the
temperature-independent cards) with 3-2-1 on its lowest surface. The encapsulant variants of
finding 7 (glass transition) can replace the out-of-cell card (--encap).

    python tcpmt_mech_reflow.py run ARCH [--refine 11] [--encap NAME]
    python tcpmt_mech_reflow.py summarize   -> research/tcpmt_revision/reflow_warpage.json
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_mech_laws as LAW                                       # noqa: E402

OUTD = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "reflow"   # campaign hook
SUMMARY = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "reflow_warpage.json"


def rcfg():
    return LAW.cfg()["reflow"]


def _is_conv(name):
    return name.startswith(("z1conv_", "conv_", "z3conv_")) or name in (
        "conv_attach_vr_substrate", "z3_attach_vr_pcb")


def parts(arch, layers):
    """{part: (layer names, measured surface (layer, side), footprint)}."""
    names = [L.name for L in layers]
    pkg_top = [n for n in names if n not in ("board", "bga", "tim") and not (
        arch == "Z3" and _is_conv(n))]
    out = {"bga_package": (pkg_top, ("sub_lower", "bot"), "bga")}
    if arch == "Z1":
        recv = [n for n in names if n in ("sub_lower", "tile_band") or n.startswith("z1conv_")]
        out["tcb_receiving"] = (recv, ("z1conv_8_output_rdl", "top"), "die")
    elif arch == "Z2":
        recv = [n for n in names if n in ("sub_lower", "tile_band", "z2_top_rdl", "interface",
                                          "die")]
        conv = [n for n in names if n.startswith("conv_") and n != "conv_attach_vr_substrate"]
        out["tcb_receiving"] = (recv, ("sub_lower", "bot"), "cells")
        out["tcb_attached"] = (conv, ("conv_0_land_side_attach_rdl", "top"), "cells")
    elif arch == "Z3":
        out["tcb_receiving"] = (["board"], ("board", "bot"), "cells")
        conv = [n for n in names if n.startswith("z3conv_")]
        out["tcb_attached"] = (conv, ("z3conv_0_land_side_attach_rdl", "top"), "cells")
    return out


def submesh(m, keep):
    from etm.mesh import Mesh
    sel = np.isin(m.elem_layer.astype(str), list(keep))
    el = m.elems[sel]
    used = np.unique(el)
    remap = np.zeros(m.n_nodes + 1, int)
    remap[used] = np.arange(1, len(used) + 1)
    nodes = m.nodes[used - 1]
    sm = Mesh(nodes=nodes, elems=remap[el], elem_material=m.elem_material[sel],
              elem_layer=m.elem_layer[sel], elem_tile=m.elem_tile[sel],
              layers=[L for L in m.layers if L.name in keep], xs=m.xs, ys=m.ys,
              zs=np.unique(np.round(nodes[:, 2], 9)))
    return sm, used


def surface_nodes(sm, layer, side, footprint, arch, tiles):
    import pkg_rdl_network as K
    L = next(l for l in sm.layers if l.name == layer)
    z = L.z0 if side == "bot" else L.z1
    ids = sm.node_ids_at_z(z)
    p = sm.nodes[ids - 1]
    if footprint == "bga":
        h = 14.4 + 0.2
        keep = (np.abs(p[:, 0]) <= h + 1e-9) & (np.abs(p[:, 1]) <= h + 1e-9)
        cut = K.architecture_cutout_mm(arch) if arch != "Z3" else None
        if cut:
            keep &= ~((np.abs(p[:, 0]) < cut / 2 - 1e-9) & (np.abs(p[:, 1]) < cut / 2 - 1e-9))
    elif footprint == "die":
        h = 22.36 / 2
        keep = (np.abs(p[:, 0]) <= h + 1e-9) & (np.abs(p[:, 1]) <= h + 1e-9)
    else:                                         # the cell-grid bounding box
        x0, x1 = min(t.x0 for t in tiles), max(t.x1 for t in tiles)
        y0, y1 = min(t.y0 for t in tiles), max(t.y1 for t in tiles)
        keep = (p[:, 0] >= x0 - 1e-9) & (p[:, 0] <= x1 + 1e-9) & \
               (p[:, 1] >= y0 - 1e-9) & (p[:, 1] <= y1 + 1e-9)
    return ids[keep]


def plane_removed(p, w):
    A = np.column_stack([np.ones(len(p)), p[:, 0], p[:, 1]])
    c, *_ = np.linalg.lstsq(A, w, rcond=None)
    return w - A @ c


def warp_measures(xy, w):
    """raw and plane-removed peak-to-valley (um) and the signed bow: mean of the outermost
    corners minus the mean nearest the centre (positive = corners displaced +z, i.e. away
    from the board for a ball side facing down)."""
    r = np.hypot(xy[:, 0], xy[:, 1])
    rc = r <= r.min() + 0.75
    rk = r >= r.max() - 0.75
    pr = plane_removed(xy, w)
    return {"pv_raw_um": float((w.max() - w.min()) * 1e3),
            "pv_plane_removed_um": float((pr.max() - pr.min()) * 1e3),
            "bow_corner_minus_centre_um": float((w[rk].mean() - w[rc].mean()) * 1e3),
            "n_nodes": int(len(w))}


def solve_part(E, m, mats, st, arch, tiles, name, keep, surf, fp, T_C, T_sf, wd):
    import production_et as PE
    sm, used = submesh(m, keep)
    st2 = copy.deepcopy(st)
    st2["structural_bc"]["t_ref"]["value"] = float(T_sf)
    T = np.full(sm.n_nodes, float(T_C))
    wd.mkdir(parents=True, exist_ok=True)
    inp = wd / f"{name}.inp"
    t0 = time.time()
    PE.ccxio.write_structural(sm, mats, T, st2, "BC_BOARD", inp, solver="")
    PE.ccxio.run_ccx(inp, threads=int(os.environ.get("FC_THREADS", "2")))
    U = PE.ccxio.read_frd(inp.with_suffix(".frd"))["DISP"]
    ids = surface_nodes(sm, *surf, fp, arch, tiles)
    xy = sm.nodes[ids - 1][:, :2]
    return {"part": name, "layers": list(keep), "n_elems": sm.n_elems, "T_C": T_C,
            "T_stress_free_C": T_sf, "surface": list(surf), "footprint": fp,
            "wall_s": time.time() - t0, "warpage": warp_measures(xy, U[ids, 2]),
            "_xy": xy, "_w": U[ids, 2], "_gid": used[ids - 1]}


def encap_hook(name):
    """BUILD_HOOK putting encapsulant variant `name` (finding 7) on the out-of-cell card."""
    import tcpmt_mech_variants as MV
    return MV.encap_hook(name)


def run(arch, refine, encap=None):
    import final_closure_physical_etm as E
    from hvr_scratch import path as scratch
    if encap:
        E.BUILD_HOOKS.append(encap_hook(encap))
    m, mats, st, tiles, _info = E.build(arch, E.PRODUCTION_H_XY, refine)
    st_cfg = rcfg()["states"]
    sfx = f"_{encap}" if encap else ""
    rt = "" if tuple(refine) == (1, 1) else f"_r{refine[0]}{refine[1]}"
    wd = scratch("mech_reflow", f"{arch}{rt}{sfx}")
    res = {"arch": arch, "refine": list(refine), "encapsulant": encap or "production card",
           "n_elems_full": m.n_elems, "parts": {}, "checks": {}}
    P = parts(arch, m.layers)
    # temperature-independent cards: one solve per part at the bonding temperature scales
    # exactly to the other states; a temperature-dependent card is solved at each state
    states = {"bga_package": ["bga_reflow", "bga_solidus"],
              "tcb_receiving": ["tcb_bond"] if arch != "Z3" else ["bga_reflow"],
              "tcb_attached": ["tcb_bond"] if arch != "Z3" else ["bga_reflow"]}
    for part, (keep, surf, fp) in P.items():
        for s in states[part]:
            T_C, T_sf = float(st_cfg[s]["T_C"]), float(st_cfg[s]["T_stress_free_C"])
            r = solve_part(E, m, mats, st, arch, tiles, f"{part}_{s}", keep, surf, fp, T_C,
                           T_sf, wd)
            res["parts"][f"{part}@{s}"] = r
            if not encap:
                break                                # linear: the other states by scaling
        print(arch, part, {k: v for k, v in res["parts"][f"{part}@{states[part][0]}"]
                           ["warpage"].items()}, flush=True)
    lim = rcfg()["limits"]
    T_cure = float(rcfg()["cure_reference_variant_C"])

    def scaled(w, T_from, sf_from, T_to, sf_to):
        f = (T_to - sf_to) / (T_from - sf_from)
        return {k: (v * f if k.endswith("_um") else v) for k, v in w.items()}

    b = res["parts"][f"bga_package@bga_reflow"]
    bw = b["warpage"]
    for s in ("bga_reflow", "bga_solidus"):
        T_C = float(st_cfg[s]["T_C"])
        w = res["parts"].get(f"bga_package@{s}", {}).get("warpage") or scaled(
            bw, b["T_C"], b["T_stress_free_C"], T_C, float(st_cfg[s]["T_stress_free_C"]))
        res["checks"][f"bga@{s}"] = {
            "T_C": T_C, "warpage": w,
            "cure_reference_150C": (scaled(w, T_C, 25.0, T_C, T_cure) if not encap else None),
            "limit_reflow_um": lim["bga_reflow_warpage_um"]["value"],
            "limit_room_coplanarity_um": lim["bga_coplanarity_room_um"]["value"],
            "within_reflow_limit_magnitude": abs(w["bow_corner_minus_centre_um"]) <= min(
                abs(v) for v in lim["bga_reflow_warpage_um"]["value"]),
            "pv_over_room_coplanarity": w["pv_plane_removed_um"]
            / lim["bga_coplanarity_room_um"]["value"]}
    rk = next(k for k in res["parts"] if k.startswith("tcb_receiving"))
    rec = res["parts"][rk]
    ak = next((k for k in res["parts"] if k.startswith("tcb_attached")), None)
    if ak:
        att = res["parts"][ak]
        common = {int(g): i for i, g in enumerate(att["_gid"])}
        pairs = [(i, common[int(g)]) for i, g in enumerate(rec["_gid"]) if int(g) in common]
        if not pairs:            # different z planes: match on (x, y)
            amap = {(round(x, 6), round(y, 6)): j for j, (x, y) in enumerate(att["_xy"])}
            pairs = [(i, amap[(round(x, 6), round(y, 6))])
                     for i, (x, y) in enumerate(rec["_xy"]) if (round(x, 6), round(y, 6)) in amap]
        i0 = np.array([p[0] for p in pairs])
        j0 = np.array([p[1] for p in pairs])
        gap = rec["_w"][i0] - att["_w"][j0]
        gw = warp_measures(rec["_xy"][i0], gap)
    else:
        gw = rec["warpage"]
    key = "tcb_coplanarity_um" if arch != "Z3" else "z3_attach_coplanarity_um"
    res["checks"]["tcb"] = {"T_C": rec["T_C"], "gap_nonuniformity": gw,
                            "receiving": rec["warpage"],
                            "attached": (res["parts"][ak]["warpage"] if ak else
                                         "flat silicon die at a uniform temperature"),
                            "limit_um": lim[key]["value"], "limit_status": lim[key]["status"],
                            "within_limit": gw["pv_plane_removed_um"] <= lim[key]["value"]}
    for r in res["parts"].values():
        for k in ("_xy", "_w", "_gid"):
            r.pop(k, None)
    OUTD.mkdir(parents=True, exist_ok=True)
    f = OUTD / f"{arch}{rt}{sfx}.json"
    f.write_text(json.dumps(res, indent=1, default=float) + "\n")
    return f


def summarize():
    out = {"what": "isothermal warpage at the reflow / bonding temperature (finding 5)",
           "states": rcfg()["states"], "limits": rcfg()["limits"],
           "assemblies": "bga: the unmounted package (no board, BGA, TIM; Z3 without its "
                         "converter); tcb: Z1 converter top (die is flat silicon), Z2 "
                         "substrate underside vs converter top, Z3 board underside vs "
                         "converter top, both parts solved alone, gap = difference",
           "cases": {}}
    for f in sorted(OUTD.glob("*.json")):
        r = json.loads(f.read_text())
        out["cases"][f.stem] = {"encapsulant": r["encapsulant"], "checks": r["checks"]}
    SUMMARY.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main():
    if sys.argv[1:2] == ["run"]:
        r = sys.argv[sys.argv.index("--refine") + 1] if "--refine" in sys.argv else "11"
        enc = sys.argv[sys.argv.index("--encap") + 1] if "--encap" in sys.argv else None
        print(run(sys.argv[2], (int(r[0]), int(r[1])), enc))
    elif sys.argv[1:2] == ["summarize"]:
        s = summarize()
        for k, c in s["cases"].items():
            print(k, json.dumps({kk: (vv.get("warpage") or vv.get("gap_nonuniformity"))
                                 for kk, vv in c["checks"].items()}, default=float))


if __name__ == "__main__":
    main()
