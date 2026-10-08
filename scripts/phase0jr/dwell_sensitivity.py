#!/usr/bin/env python3
"""Phase-0J-R Sec.11 -- DWELL-TIME SENSITIVITY. Not a mission prediction.

Sec.10 established from the solver's own NT output that the Phase-0I waveform is a SQUARE wave
-- temperature is STEPPED, then HELD for the step duration -- so the 300 s named DWELL really
is a 300 s hold at each extreme, not a ramp. This study varies that hold with T_min, T_max and
the (instantaneous) ramp held fixed, which is exactly the variable SAC creep is most sensitive
to and the one that differs most between our cycle and Syed's TC1/TC2/TC3.
"""
from __future__ import annotations
import csv, re, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0jr", "phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from cycle_audit import cycle_quantities, per_element_series               # noqa: E402
from decompose import material, parse_temperature, parse_tensors           # noqa: E402
from graded_joint import build_joint_graded                                # noqa: E402
from joint import run as run_ccx, write_inp                                # noqa: E402

OUT = R / "results" / "phase0jr"
WD = OUT / "dwell"
WD.mkdir(parents=True, exist_ok=True)
N_CYC, STAB_CYCLE, T_OFF = 6, 5, 25.0
C_PL, W_PL = 0.0468, 0.0015
DWELLS = [30.0, 60.0, 300.0, 900.0]
CASES = [("Z1", "ARCH_Z1_EMBEDDED", 2.7485664848789826, 82.8604875),
         ("Z2", "ARCH_Z2_BACKSIDE", 2.0796010434696357, 81.8453000000000)]


def run_case(tag, du_um, t_hot, dwell, n_mid=6):
    m = build_joint_graded(6, n_mid)
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", t_hot, du_um / 1000.0, dwell)); t += dwell
        cyc.append((f"c{k}off", T_OFF, 0.0, dwell)); t += dwell
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, material("EPC"), cyc, cetol=5e-2, procedure="VISCO")
    s = p.read_text()
    s = re.sub(r"\*VISCO, CETOL=[0-9.e-]+", "*VISCO, CETOL=0.05", s)
    s = re.sub(r"^[0-9.e-]+, %g, [0-9.e-]+, [0-9.e-]+$" % dwell,
               f"1e-5, {dwell:g}, 1e-12, {dwell/30:g}", s, flags=re.M)
    s = s.replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                  "*EL PRINT, ELSET=ESYED\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E", "*NODE PRINT, NSET=NBOT\nNT")
    ids = m.sets["ESYED"]
    blk = ["*ELSET, ELSET=ESYED"] + [", ".join(map(str, ids[i:i + 8]))
                                     for i in range(0, len(ids), 8)]
    s = s.replace("*SOLID SECTION", "\n".join(blk) + "\n*SOLID SECTION", 1)
    p.write_text(s)
    run_ccx(p, threads=6)
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        return None
    data = parse_tensors(d, set(ids))
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = per_element_series(data, vols, parse_temperature(d))
    te = ends[STAB_CYCLE - 1]
    q = cycle_quantities(ser, vols, te - 2 * dwell, te)
    qp = cycle_quantities(ser, vols, te - 4 * dwell, te - 2 * dwell)
    if not q:
        return None
    q["stab_pct"] = (100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"])
                     / qp["d_peeq_per_cycle"]) if qp and qp["d_peeq_per_cycle"] else float("nan")
    return q


def main() -> int:
    rows = []
    for short, arch, du, th in CASES:
        for dw in DWELLS:
            tag = f"{short}_dw{int(dw)}"
            t0 = time.time()
            q = run_case(tag, du, th, dw)
            if q is None:
                print(f"  {tag:10} FAILED"); continue
            m4, m5 = q["d_peeq_per_cycle"], q["inelastic_work_MJ_per_m3"]
            rows.append({"label": "DWELL-TIME SENSITIVITY -- NOT a mission prediction",
                         "arch": arch, "short": short, "dwell_s": dw,
                         "period_s": 4 * dw, "T_min_C": T_OFF, "T_max_C": th,
                         "M4_creep_strain": m4, "M5_creep_energy_MJ_per_m3": m5,
                         "M2_range": q["range_eq_inelastic"],
                         "Nf_syed_strain": 1.0 / (C_PL * m4),
                         "Nf_syed_energy": 1.0 / (W_PL * m5),
                         "w_over_eps_MPa": m5 / m4, "stab_pct": q["stab_pct"]})
            print(f"  {tag:10} dwell={dw:6.0f}s  M4={m4:.4e}  M5={m5:.4f}  "
                  f"Nf_s={1/(C_PL*m4):7.0f}  Nf_e={1/(W_PL*m5):6.0f}  "
                  f"stab={q['stab_pct']:.2f}%  ({time.time()-t0:.0f}s)", flush=True)
    f = OUT / "dwell_sensitivity.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}")
    for short in ("Z1", "Z2"):
        rs = sorted([r for r in rows if r["short"] == short], key=lambda r: r["dwell_s"])
        if len(rs) > 1:
            print(f"  {short}: M4 {rs[0]['M4_creep_strain']:.3e} ({rs[0]['dwell_s']:.0f}s) "
                  f"-> {rs[-1]['M4_creep_strain']:.3e} ({rs[-1]['dwell_s']:.0f}s)  "
                  f"{100*(rs[-1]['M4_creep_strain']/rs[0]['M4_creep_strain']-1):+.1f} %")
    z1 = {r["dwell_s"]: r for r in rows if r["short"] == "Z1"}
    z2 = {r["dwell_s"]: r for r in rows if r["short"] == "Z2"}
    print("\n  Z2/Z1 RELATIVE response vs dwell:")
    for dw in DWELLS:
        if dw in z1 and dw in z2:
            print(f"    dwell {dw:6.0f} s : strain-life ratio "
                  f"{z1[dw]['M4_creep_strain']/z2[dw]['M4_creep_strain']:.4f}   "
                  f"energy-life ratio "
                  f"{z1[dw]['M5_creep_energy_MJ_per_m3']/z2[dw]['M5_creep_energy_MJ_per_m3']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
