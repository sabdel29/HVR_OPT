#!/usr/bin/env python3
"""Phase-0J Sec.1/10/11 -- freeze M1, M2, M3 natively for EVERY architecture and thickness.

Sec.2 forbids deriving M2 from M1 by the Phase-0I-R factor 3.72. Every quantity here is
computed DIRECTLY from the same solve:

  M1  accumulated equivalent inelastic PATH per stabilised cycle   = d(PEEQ)
  M2  direct within-cycle inelastic strain RANGE                   = max-min of eq(eps_in)
  M3  dissipated inelastic energy density per stabilised cycle     = int sigma:d(eps_in)

Phase 0I-R measured M1/M2 = 3.72 for ONE trajectory. Running all eleven z-sweep points tests
whether that ratio is a constant of the material, of the cycle, or of neither.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from cycle_audit import cycle_quantities, per_element_series              # noqa: E402
from decompose import material, parse_temperature, parse_tensors          # noqa: E402
from joint import build_joint, run, write_inp                             # noqa: E402

OUT = R / "results" / "phase0j"
WD = OUT / "native"
WD.mkdir(parents=True, exist_ok=True)
N_CYC, DWELL, T_OFF = 4, 300.0, 25.0


def load_cases():
    """Every z-sweep point Phase 0I actually solved, with its own du and T_hot."""
    rows = list(csv.DictReader(open(R / "results/phase0i/z_architecture_comparison.csv")))
    return [(r["arch"], float(r["h_sub_mm"]), float(r["du_corner_um"]),
             float(r["T_joint_C"]), float(r["P_elec_total_w"]), float(r["d_eps_in_stab"]))
            for r in rows]


def run_case(tag, du_um, t_hot, kind="EPC"):
    m = build_joint(6, 8, 1)
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", t_hot, du_um / 1000.0, DWELL)); t += DWELL
        cyc.append((f"c{k}off", T_OFF, 0.0, DWELL)); t += DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    # Without a *CREEP card there is nothing for *VISCO to integrate and the
    # near-perfectly-plastic response diverges; EP therefore uses *STATIC.
    write_inp(m, p, material(kind), cyc, cetol=1e-2,
              procedure=("STATIC" if kind == "EP" else "VISCO"))
    s = p.read_text().replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                              "*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E",
                  "*EL PRINT, ELSET=ESOL\nS, E\n*NODE PRINT, NSET=NBOT\nNT")
    p.write_text(s)
    run(p, threads=6)
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        return None
    data = parse_tensors(d, set(m.sets["ESOLCORE"]))
    ser = per_element_series(data, {e: dd["V"] for per in data.values()
                                    for e, dd in per.items() if "V" in dd},
                             parse_temperature(d))
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    te = ends[-1]
    q = cycle_quantities(ser, vols, te - 2 * DWELL, te)
    if q is None:
        return None
    qp = cycle_quantities(ser, vols, te - 4 * DWELL, te - 2 * DWELL)
    q["stab_pct"] = (100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"])
                     / qp["d_peeq_per_cycle"]) if qp and qp["d_peeq_per_cycle"] else float("nan")
    return q


def main() -> int:
    rows = []
    for arch, h, du, th, pel, d0i in load_cases():
        tag = f"{arch.replace('ARCH_','')}_{str(h).replace('.','p')}"
        print(f"  {tag:26} du={du:.3f}um  T_hot={th:.2f}C", flush=True)
        q = run_case(tag, du, th)
        if q is None:
            print("      FAILED"); continue
        m1, m2, m3 = (q["d_peeq_per_cycle"], q["range_eq_inelastic"],
                      q["inelastic_work_MJ_per_m3"])
        rows.append({"arch": arch, "h_sub_mm": h, "du_corner_um": du, "T_hot_C": th,
                     "T_min_C": T_OFF, "dT_K": round(th - T_OFF, 3),
                     "T_mean_C": round((th + T_OFF) / 2, 3), "P_elec_total_w": pel,
                     "M1_accum_inelastic_path": m1, "M2_strain_range": m2,
                     "M3_inelastic_work_MJ_per_m3": m3,
                     "M1_over_M2": m1 / m2, "stab_pct": q["stab_pct"],
                     "phase0i_d_eps_in_stab": d0i})
        print(f"      M1={m1:.4e}  M2={m2:.4e}  M3={m3:.4f}  M1/M2={m1/m2:.3f}", flush=True)
    f = OUT / "native_metrics_by_architecture.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    r = [x["M1_over_M2"] for x in rows]
    print(f"\nwrote {f}")
    print(f"M1/M2 across {len(r)} cases: {min(r):.3f} to {max(r):.3f} "
          f"(Phase-0I-R measured 3.72 for one trajectory)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
