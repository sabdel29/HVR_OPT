#!/usr/bin/env python3
"""Does the Phase-0L experiment-design arithmetic reproduce Phase 0K-R?

Two separate questions, and they have different answers:

  (a) With the DEFAULT solver control -- the settings Phase 0K-R actually used -- does the
      incumbent model reproduce D = 1.4395 and n = 34?  If yes, the METHOD is verified.
  (b) With the TIGHT solver control -- the correct settings, which resolve the inelastic-energy
      integral -- what does the same incumbent model give?  Any difference is a numerical
      correction to Phase 0K-R, not a constitutive one.
"""
from __future__ import annotations
import csv, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0l"
SIM_SE_D, SIM_SE_A, BETA, ZT = 0.08, 0.06, 5.1, 3.0
A, B = "EXP_45_125", "EXP_110_150"
F = lambda r, k: float(r[k])


def design(rows_):
    d = {(r["model"], r["arch"], r["profile_tag"]): r for r in rows_ if r["status"] == "OK"}
    out = {}
    for m in sorted({k[0] for k in d}):
        if not all((m, a, c) in d for a in ("Z1", "Z2") for c in (A, B)):
            continue
        we, eff = {}, {}
        for c in (A, B):
            z1, z2 = d[(m, "Z1", c)], d[(m, "Z2", c)]
            we[c] = F(z1, "inelastic_work_MJ_per_m3") / F(z1, "d_peeq_per_cycle")
            eff[c] = min(F(z1, "d_peeq_per_cycle") / F(z2, "d_peeq_per_cycle"),
                         F(z1, "inelastic_work_MJ_per_m3") / F(z2, "inelastic_work_MJ_per_m3"))
        D = max(we.values()) / min(we.values())
        nq1 = next((n for n in range(4, 20001)
                    if math.log(D) / math.sqrt(2/(BETA**2*n) + SIM_SE_D**2) >= ZT), None)
        nq2 = next((n for n in range(4, 20001)
                    if sum(math.log(eff[c]) for c in (A, B))
                    / math.sqrt(2/(BETA**2*n) + SIM_SE_A**2) / math.sqrt(2) >= ZT), None)
        out[m] = dict(D=D, n=max(nq1 or 0, nq2 or 0) or None, nq1=nq1, nq2=nq2)
    return out


def main() -> int:
    dflt = design(list(csv.DictReader(open(OUT / "package_model_replay.csv"))))
    tght = design(list(csv.DictReader(open(OUT / "package_model_replay_tight.csv"))))
    print(f"{'model':>11} | {'DEFAULT control':^24} | {'TIGHT control':^24}")
    print(f"{'':>11} | {'D':>9} {'n/cell':>7} {'pkgs':>5} | {'D':>9} {'n/cell':>7} {'pkgs':>5}")
    rows_out = []
    for m in sorted(set(dflt) | set(tght)):
        a, b = dflt.get(m), tght.get(m)
        f = lambda x: (f"{x['D']:9.4f} {str(x['n']):>7} {str(4*x['n']) if x['n'] else '--':>5}"
                       if x else f"{'--':>9} {'--':>7} {'--':>5}")
        print(f"{m:>11} | {f(a)} | {f(b)}")
        rows_out.append({"model": m,
                         "D_default": a["D"] if a else "", "n_default": a["n"] if a else "",
                         "D_tight": b["D"] if b else "", "n_tight": b["n"] if b else ""})
    print()
    ref = dflt.get("M0_COARSE")
    if ref:
        okD = abs(ref["D"] - 1.4395) < 5e-4
        okn = ref["n"] == 34
        print(f"(a) METHOD CHECK against Phase 0K-R (D = 1.4395, n = 34), DEFAULT control:")
        print(f"    D = {ref['D']:.4f}  {'MATCH' if okD else 'MISMATCH'};  "
              f"n = {ref['n']}  {'MATCH' if okn else 'MISMATCH'}")
        print(f"    -> the experiment-design arithmetic is "
              f"{'REPRODUCED' if (okD and okn) else 'NOT REPRODUCED'}")
    t = tght.get("M0_COARSE")
    if ref and t:
        print()
        print(f"(b) SAME MODEL, TIGHT control: D = {t['D']:.4f}, n = {t['n']}")
        print(f"    The incumbent constitutive model moves from D = {ref['D']:.4f} to "
              f"{t['D']:.4f} and from n = {ref['n']} to {t['n']} with NO change of physics.")
        print(f"    That shift is numerical: Phase 0K-R's inelastic-energy metric was")
        print(f"    under-integrated, so its w/eps and hence its D were biased.")
    p = OUT / "method_reproduction_check.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        w.writeheader(); w.writerows(rows_out)
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
