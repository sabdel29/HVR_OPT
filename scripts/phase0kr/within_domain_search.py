#!/usr/bin/env python3
"""Phase-0K-R Sec.9 -- search for a discriminating profile pair INSIDE the creep domain.

Constraint: T_min >= 45 C, the creep-calibration floor. T_max <= 150 C, the ceiling.
Objective: maximise w/eps spread between two profiles (the discriminator), subject to the
domain constraint and to a practical cycle duration. NOT to maximise damage.
"""
from __future__ import annotations
import csv, re, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0kr", "phase0k", "phase0jr", "phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from cycle_audit import cycle_quantities, per_element_series               # noqa: E402
from decompose import material, parse_temperature, parse_tensors           # noqa: E402
from graded_joint import build_joint_graded                                # noqa: E402
from joint import run as run_ccx, write_inp                                # noqa: E402

OUT = R / "results" / "phase0kr"
WD = OUT / "wd"
WD.mkdir(parents=True, exist_ok=True)
N_CYC, STAB = 6, 5
DU_REF, DT_REF = {"Z1": 2.7485664848789826, "Z2": 2.0796010434696357}, \
                 {"Z1": 57.8604875, "Z2": 56.8453000000000}

# every candidate has T_min >= 45 C (the creep floor) and T_max <= 150 C (the ceiling)
CANDS = [("D_LOW_NARROW",   45.0,  85.0, 300.0, "coldest admissible minimum, modest span"),
         ("D_LOW_WIDE",     45.0, 125.0, 300.0, "coldest minimum, wide span"),
         ("D_FULL_SPAN",    45.0, 150.0, 300.0, "the entire calibrated temperature range"),
         ("D_MID",          55.0, 125.0, 300.0, "Phase-0K HOT_SHALLOW, re-run for reference"),
         ("D_HIGH_NARROW", 110.0, 150.0, 300.0, "hottest band, lowest yield stress"),
         ("D_HIGH_WIDE",    80.0, 150.0, 300.0, "hot minimum, wide span"),
         ("D_LOW_LONG",     45.0,  85.0, 900.0, "coldest minimum, 15-min dwells"),
         ("D_HIGH_LONG",   110.0, 150.0, 900.0, "hottest band, 15-min dwells")]


def run_case(tag, arch, tmin, tmax, dwell, n_mid=6):
    du = DU_REF[arch] * (tmax - tmin) / DT_REF[arch]
    m = build_joint_graded(6, n_mid)
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", tmax, du / 1000.0, dwell)); t += dwell
        cyc.append((f"c{k}off", tmin, 0.0, dwell)); t += dwell
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, material("EPC"), cyc, t_ref_c=tmin, cetol=5e-2, procedure="VISCO")
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
    te = ends[STAB - 1]
    q = cycle_quantities(ser, vols, te - 2 * dwell, te)
    qp = cycle_quantities(ser, vols, te - 4 * dwell, te - 2 * dwell)
    if not q:
        return None
    q["stab_pct"] = (100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"])
                     / qp["d_peeq_per_cycle"]) if qp and qp["d_peeq_per_cycle"] else float("nan")
    q["du_um"] = du
    return q


def main() -> int:
    arch = sys.argv[1] if len(sys.argv) > 1 else "Z1"
    rows = []
    for name, tmin, tmax, dwell, desc in CANDS:
        tag = f"{arch}_{name}"
        t0 = time.time()
        q = run_case(tag, arch, tmin, tmax, dwell)
        if q is None:
            print(f"  {tag:18} FAILED", flush=True); continue
        m4, m5 = q["d_peeq_per_cycle"], q["inelastic_work_MJ_per_m3"]
        # cycle duration: two dwells + two ramps at 3 C/min
        dur = 2 * dwell + 2 * (tmax - tmin) / 3.0 * 60.0
        rows.append({"arch": arch, "condition": name, "description": desc,
                     "T_min_C": tmin, "T_max_C": tmax, "dT_K": tmax - tmin,
                     "dwell_s": dwell, "du_um": round(q["du_um"], 4),
                     "M4_creep_strain": m4, "M5_creep_energy_MJ_per_m3": m5,
                     "w_over_eps_MPa": m5 / m4, "stab_pct": q["stab_pct"],
                     "cycle_duration_s_at_3Cpermin": round(dur, 1),
                     "cycles_per_day": round(86400 / dur, 1),
                     "T_min_inside_creep_domain": tmin >= 45.0,
                     "T_max_inside_creep_domain": tmax <= 150.0})
        print(f"  {tag:18} T {tmin:5.0f}/{tmax:5.0f} dw={dwell:4.0f}  M4={m4:.4e}  "
              f"M5={m5:.4f}  w/eps={m5/m4:7.2f}  {dur/3600:.2f} h/cyc  "
              f"({time.time()-t0:.0f}s)", flush=True)
    f = OUT / f"within_domain_{arch}.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    we = [r["w_over_eps_MPa"] for r in rows]
    print(f"\nwrote {f}")
    print(f"w/eps within domain: {min(we):.1f} to {max(we):.1f} MPa -> best D = {max(we)/min(we):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
