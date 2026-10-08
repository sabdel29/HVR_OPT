#!/usr/bin/env python3
"""alpha_GaN sensitivity on the FROZEN R3C pair -- electrical only, no new physics.

alpha_GaN is an adopted calibration coefficient, not a sourced material constant: the EPC
product table carried in this repository has no temperature columns
(results/phase0d/electrical_model_validation.md). It is already swept 0.005/0.0075/0.010 /K
through the full electrical-thermal loop in the Phase-0D robustness study
(results/phase0d/robustness_0d.csv). This script adds the missing piece -- the first-order
effect on the FROZEN pair itself -- by re-evaluating the converter loss model at the frozen
converged converter-layer temperature with alpha perturbed. The temperature is held at its
frozen value, so this is the electrical sensitivity alone and the E-T feedback is not
re-converged; the Phase-0D sweep is what carries the feedback.
"""
from __future__ import annotations
import csv, importlib.util, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3c"
ALPHAS = [("-20 %", 6.0e-3), ("reference", 7.5e-3), ("+20 %", 9.0e-3),
          ("-33 % (Phase-0D lo)", 5.0e-3), ("+33 % (Phase-0D hi)", 1.0e-2)]
REF = 7.5e-3


def main() -> int:
    s = importlib.util.spec_from_file_location("rp", R / "scripts/phase0mr/replay_production.py")
    rp = importlib.util.module_from_spec(s); s.loader.exec_module(rp)
    sys.path.insert(0, str(R / "scripts" / "phase0d"))
    import electrical as EL

    frozen = {r["case"]: r for r in csv.DictReader((OUT / "final_etm_replay.csv").open())}
    rows = []
    for case in ("Z1", "Z2"):
        t_conv = float(frozen[case]["T_conv_C"])
        base = None
        for label, a in ALPHAS:
            EL.ALPHA_GAN_RDSON = a
            rp._DESIGN_CACHE.clear()
            p_conv = rp.converter_terms(t_conv)["p_conv_total_w"]
            if label == "reference":
                base = p_conv
            rows.append({"case": case, "label": label, "alpha_gan_per_K": a,
                         "T_conv_C": f"{t_conv:.4f}", "P_converter_w": f"{p_conv:.6f}"})
        for r in rows:
            if r["case"] == case and "dP_pct" not in r:
                r["dP_pct"] = f"{100 * (float(r['P_converter_w']) - base) / base:+.4f}"
    EL.ALPHA_GAN_RDSON = REF
    rp._DESIGN_CACHE.clear()

    f = OUT / "gan_alpha_sensitivity.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print(f"{'case':<6}{'alpha':<22}{'a /K':>9}{'T_conv C':>10}{'P_conv W':>11}{'dP %':>9}")
    for r in rows:
        print(f"{r['case']:<6}{r['label']:<22}{r['alpha_gan_per_K']:9.4f}"
              f"{float(r['T_conv_C']):10.2f}{float(r['P_converter_w']):11.3f}{r['dP_pct']:>9}")
    # does the Z1/Z2 converter-loss ordering survive?
    print("\n  Z2 - Z1 converter loss at each alpha (Z2 higher throughout means the ordering holds):")
    ok = True
    for label, a in ALPHAS:
        p1 = float(next(r for r in rows if r["case"] == "Z1" and r["label"] == label)["P_converter_w"])
        p2 = float(next(r for r in rows if r["case"] == "Z2" and r["label"] == label)["P_converter_w"])
        ok &= p2 > p1
        print(f"    {label:<22} {p2 - p1:+.4f} W")
    print(f"\n  converter-loss ordering preserved across the sweep: {ok}")
    print(f"  wrote {f.relative_to(R)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
