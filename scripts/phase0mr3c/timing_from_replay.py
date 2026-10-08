#!/usr/bin/env python3
"""Stage timing of the frozen R3C pair, derived from the timing run's own artifacts.

Nothing is re-solved. The replay wrote one .inp and one .frd per thermal sub-solve and one
pair for the thermoelastic solve; their timestamps give the measured split between the
electrical-thermal loop and the single mechanical solve that follows it.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3c"
REPLAY = R / "results" / "phase0mr" / "replay"
CASES = {"Z1": "ARCH_Z1_EMBEDDED", "Z2": "ARCH_Z2_BACKSIDE"}
TPL, COOLER = "T1C_REORDERED", "TOP_SI_MICROCHANNEL_27"


def main() -> int:
    lr = {}
    f = OUT / "final_local_response.csv"
    if f.is_file():
        lr = {r["case"]: r for r in csv.DictReader(f.open())}
    out = {}
    for case, arch in CASES.items():
        d = REPLAY / f"{arch}_AFTER_{TPL}_{COOLER}"
        if not d.is_dir():
            print(f"  MISSING {d.relative_to(R)}"); return 1
        its = sorted(d.glob("it*"), key=lambda p: int(p.name[2:]))
        ev, per_iter = [], []
        for it in its:
            fr = sorted(it.glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))
            ip = sorted(it.glob("th_*.inp"), key=lambda p: int(p.stem.split("_")[1]))
            per_iter.append(len(fr))
            ev += [x.stat().st_mtime for x in fr] + [x.stat().st_mtime for x in ip]
        ev.sort()
        t0 = ev[0]
        si = (d / "structural.inp").stat().st_mtime - t0
        sf = (d / "structural.frd").stat().st_mtime - t0
        rec = {"n_et_iterations": len(its),
               "thermal_subsolves_per_iteration": per_iter,
               "thermal_subsolves_total": sum(per_iter),
               "thermal_fe_total_s": round(ev[-1] - t0, 1),
               "thermoelastic_solve_s": round(sf - si, 1),
               "span_s": round(sf, 1),
               "mechanics_inside_et_loop": False}
        if case in lr:
            rec["local_solder_submodel_s"] = round(float(lr[case]["wall_s"]), 1)
        out[case] = rec
        print(f"  {case}: {len(its)} E-T iterations, thermal sub-solves {per_iter} "
              f"(total {sum(per_iter)}), thermal FE {rec['thermal_fe_total_s']} s, "
              f"one thermoelastic solve {rec['thermoelastic_solve_s']} s, "
              f"span {rec['span_s']} s")
    p = OUT / "timing_breakdown.json"
    p.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n  mechanics is OUTSIDE the E-T loop (code: replay_production.run_case)")
    print(f"  wrote {p.relative_to(R)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
