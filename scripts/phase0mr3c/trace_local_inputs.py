#!/usr/bin/env python3
"""Trace the exact local-solder-submodel inputs for the FINAL FROZEN R3C pair.

Nothing is solved. The converged thermal field and the displacement field written by the
frozen replay are read back, every frozen global quantity is reproduced and asserted, and
the two local-submodel inputs are derived with the same node selection the production
metric uses:

    du_c      the corner-joint relative in-plane displacement  (already frozen)
    T_joint   the mean corner-band joint temperature           (derived here)

T_joint is defined exactly as in scripts/phase0i/zglobal.py: the mean over the corner band
r > 0.92 r_max of the half-sum of the BGA bottom- and top-face nodal temperatures.
"""
from __future__ import annotations
import csv, importlib.util, json, math, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3c"
REPLAY = R / "results" / "phase0mr" / "replay"
TPL, COOLER = "T1C_REORDERED", "TOP_SI_MICROCHANNEL_27"
CASES = {"Z1": "ARCH_Z1_EMBEDDED", "Z2": "ARCH_Z2_BACKSIDE"}
TOL = 1e-4


def _load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def main() -> int:
    rp = _load("rp", R / "scripts" / "phase0mr" / "replay_production.py")
    PE = rp.PE
    frozen = {r["case"]: r for r in csv.DictReader((OUT / "final_etm_replay.csv").open())}
    rows, bad = [], 0

    for case, arch in CASES.items():
        d = REPLAY / f"{arch}_AFTER_{TPL}_{COOLER}"
        if not d.is_dir():
            print(f"  MISSING {d.relative_to(R)}"); return 1
        its = sorted(d.glob("it*"), key=lambda p: int(p.name[2:]))
        ths = sorted(its[-1].glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))
        thf = ths[-1]                                   # converged sub-solve of the last iter
        m = PE.build_global(arch, rp.H_SUB[arch], h_xy=0.80)
        m = m[0] if isinstance(m, tuple) else m
        Tn = np.asarray(PE.ccxio.read_frd(thf)["NDTEMP"]).ravel()
        U = PE.ccxio.read_frd(d / "structural.frd")["DISP"]

        g = frozen[case]
        chk = [("T_max_C", float(np.nanmax(Tn)), float(g["T_max_C"]), 2e-3),
               ("T_mean_C", float(np.nanmean(Tn)), float(g["T_mean_C"]), 2e-3)]

        # die warpage, by the production named-layer rule
        ids = m.node_ids_at_z(m.layer("die").z1)
        uz = U[ids, 2] * 1000.0
        chk.append(("die_warpage_pv_um", float(np.nanmax(uz) - np.nanmin(uz)),
                    float(g["die_warpage_pv_um"]), 1e-6))

        # corner band of the BGA layer -- the SAME selection as the production metric
        zl = {L.name: (L.z0, L.z1) for L in m.layers}
        z0, z1 = zl["bga"]
        nb, nt = m.node_ids_at_z(z0), m.node_ids_at_z(z1)
        pb, pt = m.nodes[nb - 1], m.nodes[nt - 1]
        rb = np.hypot(pb[:, 0], pb[:, 1])
        sel = nb[rb > 0.92 * rb.max()]
        du_max, tj = 0.0, []
        for idb in sel:
            p = m.nodes[idb - 1]
            j = int(np.argmin((pt[:, 0] - p[0]) ** 2 + (pt[:, 1] - p[1]) ** 2))
            idt = nt[j]
            du_max = max(du_max, math.hypot(U[idt, 0] - U[idb, 0], U[idt, 1] - U[idb, 1]))
            tj.append(0.5 * (Tn[idb - 1] + Tn[idt - 1]))
        chk.append(("response_driver_um", du_max * 1000.0,
                    float(g["response_driver_um"]), 1e-6))

        for name, got, want, tol in chk:
            ok = abs(got - want) <= tol
            bad += not ok
            print(f"  {'ok  ' if ok else 'FAIL'} {case} {name:22s} {got:14.6f}  frozen {want:14.6f}")

        rows.append({
            "case": case, "arch": arch,
            "du_c_um": f"{du_max * 1000.0:.10f}",
            "T_joint_C": f"{float(np.mean(tj)):.6f}",
            "T_joint_max_C": f"{float(np.max(tj)):.6f}",
            "T_max_C": g["T_max_C"], "T_mean_C": g["T_mean_C"],
            "bga_standoff_mm": f"{z1 - z0:.6f}",
            "n_corner_joints": len(sel),
            "shear_strain_pct": f"{100.0 * du_max / (z1 - z0):.6f}",
            "thermal_source": str(thf.relative_to(R)),
            "structural_source": str((d / 'structural.frd').relative_to(R)),
        })

    if bad:
        print(f"\n  {bad} frozen value(s) not reproduced -- STOP"); return 1
    f = OUT / "local_submodel_inputs.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\n  every frozen global value reproduced; wrote {f.relative_to(R)}")
    for r in rows:
        print(f"    {r['case']}: du_c = {float(r['du_c_um']):.4f} um, "
              f"T_joint = {float(r['T_joint_C']):.3f} C "
              f"(max {float(r['T_joint_max_C']):.3f} C over {r['n_corner_joints']} joints)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
