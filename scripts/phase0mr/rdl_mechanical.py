#!/usr/bin/env python3
"""Phase-0M-R Section 9 -- put the RDL into the mechanical and thermal model.

THE RDL IS NOT IN THE MECHANICAL MESH. The layer between the substrate top and the die is
10 um of `underfill_homog` -- E = 8 GPa, k = 0.7 W/m.K isotropic -- and the package stack
calls it "homogenized microbump + underfill". The redistribution metal that carries the
entire 1 V rail is absent from it.

Two things are wrong as a result, and they pull in opposite directions:
  THERMAL     the real stack spreads heat laterally at 92 to 335 W/m.K. The model gives that
              layer 0.7, isotropic -- two to three orders of magnitude too low in plane.
  MECHANICAL  the real stack is 48 to 104 GPa in plane. The model gives it 8 GPa -- six to
              thirteen times too compliant, directly under the die.

FIDELITY LADDER
  M-RDL0  as built: 10 um of underfill_homog
  M-RDL1  same thickness, composite RDL + bump properties, ORTHOTROPIC conductivity
  M-RDL2  true thickness (RDL stack + bump layer), same composite properties

NO RDL ALLOWABLE IS INVENTED. A new stress metric without an allowable is RESPONSE COUPLING,
not a constraint, and is labelled so.
"""
from __future__ import annotations
import csv, json, math, sys
from dataclasses import replace as dc_replace
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m", "phase0i", "phase0h", "phase0g", "phase0f",
          "phase0e", "phase0dr", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / d))
import zglobal as ZG                                                       # noqa: E402
from etm.config import build_materials                                     # noqa: E402

OUT = R / "results" / "phase0mr"
OUT.mkdir(parents=True, exist_ok=True)

H_SUB = {"ARCH_Z1_EMBEDDED": 1.30, "ARCH_Z2_BACKSIDE": 0.30}
P_CONV_W, P_DIE_W, H_TOP = 125.26443889730017, 1000.0, 166000.0

# from rdl_effective_tensor.csv (ORTHOGONAL stack, t_diel = 5 um) and
# bump_layer_effective_tensor.csv (microbump_underfill)
RDL = {"k_x": 117.63, "k_y": 117.63, "k_z": 1.24, "E_MPa": 57.3e3, "nu": 0.30,
       "cte": 20.67e-6, "t_um": 40.0,
       "src": "results/phase0mr/rdl_effective_tensor.csv, ORTHOGONAL t_diel=5 um"}
BUMP = {"k_x": 0.891, "k_y": 0.891, "k_z": 11.739, "E_MPa": 8.0e3, "nu": 0.32,
        "cte": 30.0e-6, "t_um": 10.0,
        "src": "results/phase0mr/bump_layer_effective_tensor.csv, microbump_underfill"}


def composite(t_rdl_um: float, t_bump_um: float) -> dict:
    """Series through thickness, parallel in plane -- the two layers stacked."""
    t = t_rdl_um + t_bump_um
    fr, fb = t_rdl_um / t, t_bump_um / t
    kz = 1.0 / (fr / RDL["k_z"] + fb / BUMP["k_z"])
    kx = fr * RDL["k_x"] + fb * BUMP["k_x"]
    e = fr * RDL["E_MPa"] + fb * BUMP["E_MPa"]            # in-plane load sharing
    cte = (fr * RDL["E_MPa"] * RDL["cte"] + fb * BUMP["E_MPa"] * BUMP["cte"]) / e
    return {"t_um": t, "k_x": kx, "k_y": kx, "k_z": kz, "E_MPa": e,
            "nu": 0.31, "cte": cte}


RUNGS = {
    "M-RDL0": None,
    "M-RDL1": composite(RDL["t_um"], BUMP["t_um"]) | {"t_um": 10.0},
    "M-RDL2": composite(RDL["t_um"], BUMP["t_um"]),
}


def run(arch: str, rung: str, wd: Path) -> dict:
    """One architecture at one fidelity rung."""
    import json as _json
    spec = RUNGS[rung]
    orig_load, orig_mat = ZG.load_stack, ZG.build_materials

    def patched_load():
        st = _json.loads(_json.dumps(orig_load()))
        if spec:
            st["geometry"]["interface_layer"]["thickness"]["value"] = spec["t_um"] * 1e-3
        return st

    def patched_mats(stack, overrides=None):
        mats = orig_mat(stack, overrides)
        if spec:
            m = mats["underfill_homog"]
            mats["underfill_homog"] = dc_replace(
                m, E=spec["E_MPa"], nu=spec["nu"], cte=spec["cte"],
                k=(spec["k_x"] + spec["k_y"] + spec["k_z"]) / 3.0,
                k_ortho=(spec["k_x"], spec["k_y"], spec["k_z"]))
        return mats

    ZG.load_stack, ZG.build_materials = patched_load, patched_mats
    try:
        r = ZG.corner_joint_response(arch, H_SUB[arch], P_CONV_W, P_DIE_W, H_TOP, wd=wd)
    finally:
        ZG.load_stack, ZG.build_materials = orig_load, orig_mat
    return {"arch": arch, "rung": rung,
            "interface_t_um": (spec or {}).get("t_um", 10.0),
            "E_MPa": (spec or {}).get("E_MPa", 8000.0),
            "k_x": (spec or {}).get("k_x", 0.7), "k_z": (spec or {}).get("k_z", 0.7),
            "cte": (spec or {}).get("cte", 30.0e-6),
            "T_max_C": r["T_max_C"], "T_joint_C": r["T_joint_C"],
            "du_corner_um": r["du_corner_um"],
            "die_warpage_pv_um": r["die_warpage_pv_um"],
            "pkg_warpage_pv_um": r["pkg_warpage_pv_um"],
            "n_elem": r["n_elem"],
            "energy_residual_pct": r["energy_residual_pct"]}


def main() -> int:
    rows = []
    for rung in RUNGS:
        vals = {}
        for arch in H_SUB:
            v = run(arch, rung, OUT / "rdlmech")
            rows.append(v)
            vals[arch] = v
            print(f"  {rung:8s} {arch:20s} du={v['du_corner_um']:.4f} um  "
                  f"warp={v['die_warpage_pv_um']:8.4f} um  Tmax={v['T_max_C']:7.3f} C",
                  flush=True)
        r1, r2 = vals["ARCH_Z1_EMBEDDED"], vals["ARCH_Z2_BACKSIDE"]
        rows.append({"arch": "RATIO", "rung": rung,
                     "du_corner_um": r1["du_corner_um"] / r2["du_corner_um"],
                     "die_warpage_pv_um": r1["die_warpage_pv_um"] / r2["die_warpage_pv_um"],
                     "T_max_C": r1["T_max_C"] - r2["T_max_C"]})
        print(f"  {rung:8s} {'Z1/Z2 ratio':20s} du={r1['du_corner_um']/r2['du_corner_um']:.4f}"
              f"   warp={r1['die_warpage_pv_um']/r2['die_warpage_pv_um']:.4f}", flush=True)
    base = next(r for r in rows if r["arch"] == "RATIO" and r["rung"] == "M-RDL0")
    for r in rows:
        if r["arch"] == "RATIO":
            r["ratio_shift_pct"] = 100 * (r["du_corner_um"] - base["du_corner_um"]) \
                / base["du_corner_um"]
            r["ordering_preserved"] = r["du_corner_um"] > 1.0
    k = sorted({x for r in rows for x in r})
    with open(OUT / "rdl_mechanical_fidelity.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
    print(f"wrote {OUT/'rdl_mechanical_fidelity.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
