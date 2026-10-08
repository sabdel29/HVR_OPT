#!/usr/bin/env python3
"""Phase-0M Part 39 -- focused design-space sensitivities.

NOT a DOE and NOT an optimizer. The question is only whether each new dimension moves any
decision-relevant quantity by more than the uncertainty already in the model.

The TSV dimension is carried all the way to the mechanical driver, because that is the one
that could support verdict B: if interconnect geometry changes the corner-joint shear, it
changes the reliability ranking, and no earlier phase could ask that -- the TSV field
entered the mechanical model as a fixed homogenized block.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for d in ("phase0m", "phase0i", "phase0h", "phase0g", "phase0f", "phase0e", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / d))
OUT = R / "results" / "phase0m"
WD = OUT / "sens"
WD.mkdir(parents=True, exist_ok=True)

H_TOP_1KW = 166000.0
P_CONV_W = 125.26443889730017
P_DIE_W = 1000.0
H_SUB = {"ARCH_Z1_EMBEDDED": 1.30, "ARCH_Z2_BACKSIDE": 0.30}


def tsv_to_mechanics() -> list[dict]:
    """Vary the TSV field geometry and carry it into the global mechanical driver.

    `tsv_homog` is DERIVED from the stack geometry at load time (etm.materials.
    derive_tsv_homog), so changing the via diameter or pitch in the stack changes the
    effective modulus, CTE and conductivity of the whole through-substrate layer -- and
    therefore the corner-joint shear that every reliability number depends on.
    """
    import zglobal as ZG
    from etm.config import load_stack
    import json
    rows = []
    base = load_stack()
    geo = base["geometry"]["tsv_field"]
    d0 = geo["diameter"]["value"] if isinstance(geo.get("diameter"), dict) else None
    p0 = geo["pitch"]["value"] if isinstance(geo.get("pitch"), dict) else None
    cases = [("baseline", None, None)]
    if d0 and p0:
        for dm, pm in ((0.5, 1.0), (1.5, 1.0), (1.0, 0.7), (1.0, 1.5), (2.0, 2.0)):
            cases.append((f"d_x{dm:g}_p_x{pm:g}", d0 * dm, p0 * pm))
    orig_load = ZG.load_stack
    for tag, dnew, pnew in cases:
        def patched(_d=dnew, _p=pnew):
            st = json.loads(json.dumps(orig_load()))
            if _d is not None:
                st["geometry"]["tsv_field"]["diameter"]["value"] = _d
                st["geometry"]["tsv_field"]["pitch"]["value"] = _p
            return st
        ZG.load_stack = patched
        try:
            vals = {}
            for arch in ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE"):
                vals[arch] = ZG.corner_joint_response(arch, H_SUB[arch], P_CONV_W, P_DIE_W,
                                                      H_TOP_1KW, wd=WD)
        finally:
            ZG.load_stack = orig_load
        z1, z2 = vals["ARCH_Z1_EMBEDDED"], vals["ARCH_Z2_BACKSIDE"]
        f_cu = (math.pi * (dnew or d0) ** 2 / (4 * (pnew or p0) ** 2)) if d0 else float("nan")
        rows.append({"dimension": "TSV geometry", "case": tag,
                     "tsv_d_mm": dnew or d0, "tsv_p_mm": pnew or p0, "f_cu": f_cu,
                     "du_Z1_um": z1["du_corner_um"], "du_Z2_um": z2["du_corner_um"],
                     "du_ratio": z1["du_corner_um"] / z2["du_corner_um"],
                     "T_max_Z1_C": z1["T_max_C"], "T_max_Z2_C": z2["T_max_C"],
                     "warp_Z1_um": z1["die_warpage_pv_um"],
                     "warp_Z2_um": z2["die_warpage_pv_um"]})
        print(f"  {tag:16s} f_cu={f_cu:.4f} du_Z1={z1['du_corner_um']:.4f} "
              f"du_Z2={z2['du_corner_um']:.4f} ratio={rows[-1]['du_ratio']:.4f} "
              f"Tmax_Z1={z1['T_max_C']:.2f}", flush=True)
    b = rows[0]
    for r in rows:
        r["du_Z1_shift_pct"] = 100 * (r["du_Z1_um"] - b["du_Z1_um"]) / b["du_Z1_um"]
        r["ratio_shift_pct"] = 100 * (r["du_ratio"] - b["du_ratio"]) / b["du_ratio"]
        r["Tmax_Z1_shift_K"] = r["T_max_Z1_C"] - b["T_max_Z1_C"]
        r["warp_Z1_shift_pct"] = 100 * (r["warp_Z1_um"] - b["warp_Z1_um"]) / b["warp_Z1_um"]
    return rows


def main() -> int:
    rows = tsv_to_mechanics()
    k = sorted({x for r in rows for x in r})
    with open(OUT / "design_space_sensitivity.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
    print(f"wrote {OUT/'design_space_sensitivity.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
