#!/usr/bin/env python3
"""Phase-0M Parts 27-38 -- missing-mechanics audit with two decisive experiments.

Most of the physics matrix is classification. Two entries are not, because they can be
tested with what is already built, and both were classified by SPECULATION in earlier
phases:

  POLYMER VISCOELASTICITY (Part 30). The organic board, the underfill and the TIM are
  modelled as linear elastic with one modulus. A polymer's modulus falls with temperature
  and relaxes with time, so a 300 s dwell at 83 C is not the same stiffness as the ramp.
  If that matters, it biases the displacement TRANSFERRED to the solder joint, which is
  the one quantity the whole reliability chain hangs on. Screened by perturbing each
  polymer modulus on the global model and measuring the corner-joint shear for Z1 and Z2.

  ASSEMBLY PRESTRESS (Part 31). The operational model is stress-free at the cycle minimum.
  The real joint is stress-free near reflow, about 217 C, and arrives at room temperature
  already loaded. Tested by prepending a reflow cool-down to the joint submodel and
  comparing the STABILISED cycle -- which is the only thing the life law reads.
"""
from __future__ import annotations
import csv, math, re, sys, time
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0i", "phase0ir", "phase0jr", "phase0l", "phase0m", "phase0h",
          "phase0g", "phase0f", "phase0e", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / d))
OUT = R / "results" / "phase0m"
WD = OUT / "mech"
OUT.mkdir(parents=True, exist_ok=True)
WD.mkdir(parents=True, exist_ok=True)

H_TOP_1KW = 166000.0
P_CONV_W = 125.26443889730017
P_DIE_W = 1000.0
H_SUB = {"ARCH_Z1_EMBEDDED": 1.30, "ARCH_Z2_BACKSIDE": 0.30}
REFLOW_C = 217.0                 # SAC305 peak reflow; stress-free reference for prestress


# ---------------------------------------------------------------------------
# Part 30 -- polymer modulus screen on the GLOBAL model
# ---------------------------------------------------------------------------
def polymer_screen() -> list[dict]:
    import zglobal as ZG
    from etm import ccxio, metrics
    from etm.config import build_materials
    orig = build_materials
    rows = []
    cases = [("baseline", {})]
    for mat in ("board_fr4", "underfill_homog", "tim"):
        for f in (0.5, 0.7, 1.3):
            cases.append((f"{mat}_E_x{f:g}", {mat: {"E": f}}))
    cases.append(("all_polymers_E_x0.5", {m: {"E": 0.5} for m in
                                          ("board_fr4", "underfill_homog", "tim")}))
    for tag, ov in cases:
        vals = {}
        for arch in ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE"):
            def patched(stack, overrides=None, _ov=ov):
                merged = dict(overrides or {})
                for k, v in _ov.items():
                    merged[k] = {**merged.get(k, {}), **v}
                return orig(stack, merged)
            ZG.build_materials = patched
            try:
                r = ZG.corner_joint_response(arch, H_SUB[arch], P_CONV_W, P_DIE_W,
                                             H_TOP_1KW, wd=WD / "glob")
            finally:
                ZG.build_materials = orig
            vals[arch] = r
        z1, z2 = vals["ARCH_Z1_EMBEDDED"], vals["ARCH_Z2_BACKSIDE"]
        rows.append({"case": tag, "override": str(ov),
                     "du_Z1_um": z1["du_corner_um"], "du_Z2_um": z2["du_corner_um"],
                     "du_ratio_Z1_over_Z2": z1["du_corner_um"] / z2["du_corner_um"],
                     "T_joint_Z1_C": z1["T_joint_C"], "T_joint_Z2_C": z2["T_joint_C"],
                     "warp_Z1_um": z1["die_warpage_pv_um"],
                     "warp_Z2_um": z2["die_warpage_pv_um"]})
        print(f"  {tag:26s} du_Z1={z1['du_corner_um']:.4f} du_Z2={z2['du_corner_um']:.4f} "
              f"ratio={rows[-1]['du_ratio_Z1_over_Z2']:.4f}", flush=True)
    b = rows[0]
    for r in rows:
        r["du_Z1_shift_pct"] = 100 * (r["du_Z1_um"] - b["du_Z1_um"]) / b["du_Z1_um"]
        r["du_Z2_shift_pct"] = 100 * (r["du_Z2_um"] - b["du_Z2_um"]) / b["du_Z2_um"]
        r["ratio_shift_pct"] = (100 * (r["du_ratio_Z1_over_Z2"] - b["du_ratio_Z1_over_Z2"])
                                / b["du_ratio_Z1_over_Z2"])
    return rows


# ---------------------------------------------------------------------------
# Part 31 -- assembly prestress on the JOINT submodel
# ---------------------------------------------------------------------------
def prestress_case(arch: str, reflow: bool) -> dict:
    import replay as RP
    from graded_joint import build_joint_graded
    from joint import run as run_ccx, write_inp
    from decompose import parse_temperature, parse_tensors
    from cycle_audit import cycle_quantities, per_element_series

    a = RP.ARCH[arch]
    du, tmax, tmin = a["du"], a["t_hot"], RP.T_OFF
    tag = f"PRE_{arch}_{'reflow' if reflow else 'nominal'}"
    m = build_joint_graded(6, 6)
    cyc, ends, t = [], [], 0.0
    if reflow:
        # stress-free at reflow, cooled to the cycle minimum with no imposed shear
        cyc.append(("reflow_cool", tmin, 0.0, RP.DWELL)); t += RP.DWELL
    for k in range(RP.N_CYC):
        cyc.append((f"c{k}on", tmax, du / 1000.0, RP.DWELL)); t += RP.DWELL
        cyc.append((f"c{k}off", tmin, 0.0, RP.DWELL)); t += RP.DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    card = RP.material("M1")
    if reflow:
        card = card.replace("*EXPANSION, ZERO=25.", f"*EXPANSION, ZERO={REFLOW_C:g}.")
    write_inp(m, p, card, cyc, t_ref_c=(REFLOW_C if reflow else tmin),
              cetol=5e-2, procedure="VISCO")
    s = p.read_text()
    s = re.sub(r"\*VISCO, CETOL=[0-9.e-]+", "*VISCO, CETOL=0.05", s)
    s = re.sub(r"^[0-9.e-]+, %g, [0-9.e-]+, [0-9.e-]+$" % RP.DWELL,
               RP.TIGHT_START % RP.DWELL, s, flags=re.M)
    s = s.replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                  "*EL PRINT, ELSET=ESYED\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E", "*NODE PRINT, NSET=NBOT\nNT")
    ids = m.sets["ESYED"]
    blk = ["*ELSET, ELSET=ESYED"] + [", ".join(map(str, ids[i:i + 8]))
                                     for i in range(0, len(ids), 8)]
    s = s.replace("*SOLID SECTION", "\n".join(blk) + "\n*SOLID SECTION", 1)
    p.write_text(s)
    t0 = time.time()
    run_ccx(p, threads=8)
    d = p.with_suffix(".dat")
    base = {"arch": arch, "reflow": reflow, "wall_s": time.time() - t0,
            "t_ref_c": REFLOW_C if reflow else tmin}
    if not (d.is_file() and d.stat().st_size > 5000):
        return {**base, "status": "SOLVER FAILED"}
    data = parse_tensors(d, set(ids))
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = per_element_series(data, vols, parse_temperature(d))
    te = ends[RP.STAB - 1]
    q = cycle_quantities(ser, vols, te - 2 * RP.DWELL, te)
    qp = cycle_quantities(ser, vols, te - 4 * RP.DWELL, te - 2 * RP.DWELL)
    if not q:
        return {**base, "status": "NO CYCLE DATA"}
    return {**base, "status": "OK", **q,
            "stab_pct": (100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"])
                         / qp["d_peeq_per_cycle"]) if qp else float("nan")}


def prestress_test() -> list[dict]:
    rows = []
    for arch in ("Z1", "Z2"):
        for reflow in (False, True):
            r = prestress_case(arch, reflow)
            rows.append(r)
            print(f"  {arch} reflow={reflow!s:5s} {r['status']:12s} "
                  f"dPEEQ={r.get('d_peeq_per_cycle', float('nan')):.6f} "
                  f"W={r.get('inelastic_work_MJ_per_m3', float('nan')):.5f} "
                  f"stab={r.get('stab_pct', float('nan')):.3f}% "
                  f"({r.get('wall_s', 0):.0f}s)", flush=True)
    ok = {(r["arch"], r["reflow"]): r for r in rows if r["status"] == "OK"}
    for arch in ("Z1", "Z2"):
        a, b = ok.get((arch, False)), ok.get((arch, True))
        if a and b:
            for r in rows:
                if r["arch"] == arch and r["reflow"]:
                    r["dpeeq_shift_pct"] = (100 * (b["d_peeq_per_cycle"]
                                                   - a["d_peeq_per_cycle"])
                                            / a["d_peeq_per_cycle"])
                    r["work_shift_pct"] = (100 * (b["inelastic_work_MJ_per_m3"]
                                                  - a["inelastic_work_MJ_per_m3"])
                                           / a["inelastic_work_MJ_per_m3"])
    if len(ok) == 4:
        rn = ok[("Z1", False)]["d_peeq_per_cycle"] / ok[("Z2", False)]["d_peeq_per_cycle"]
        rr = ok[("Z1", True)]["d_peeq_per_cycle"] / ok[("Z2", True)]["d_peeq_per_cycle"]
        rows.append({"arch": "RATIO", "reflow": "nominal vs reflow", "status": "OK",
                     "d_peeq_per_cycle": rn, "inelastic_work_MJ_per_m3": rr,
                     "dpeeq_shift_pct": 100 * (rr - rn) / rn,
                     "note": "Z1/Z2 strain ratio: nominal in d_peeq column, "
                             "reflow in work column"})
        print(f"  Z1/Z2 strain ratio: nominal {rn:.4f} -> reflow {rr:.4f} "
              f"({100*(rr-rn)/rn:+.2f} %)")
    return rows


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "polymer"):
        rows = polymer_screen()
        k = sorted({x for r in rows for x in r})
        with open(OUT / "polymer_modulus_screen.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
        print(f"wrote {OUT/'polymer_modulus_screen.csv'}")
    if which in ("all", "prestress"):
        rows = prestress_test()
        k = sorted({x for r in rows for x in r})
        with open(OUT / "assembly_prestress_test.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
        print(f"wrote {OUT/'assembly_prestress_test.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
