#!/usr/bin/env python3
"""Phase-0J-R -- what does CalculiX integrate when *PLASTIC and *CREEP are BOTH present?

The EPC decks sit at ~2x their own yield surface while the plastic-only decks cap exactly at
it. Two hypotheses, and they differ by orders of magnitude in creep rate:

    (A)  eps_dot_cr = A * sigma_eq ^ n                (Norton on the FULL stress)
    (B)  eps_dot_cr = A * (sigma_eq - sigma_y) ^ n    (Norton on the OVERSTRESS)

A single C3D8 under CONSTANT uniaxial load, held, decides it: the measured steady creep rate is
compared against both. Load control (not displacement) so sigma is known exactly.
"""
from __future__ import annotations
import math, re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0jr"))
from creep_metric import norton_at_T                                        # noqa: E402

WD = R / "results" / "phase0jr" / "ccx_probe"
WD.mkdir(parents=True, exist_ok=True)
T_C, HOLD = 82.86, 3000.0
SIG0_AT_T = 15.20      # *PLASTIC card interpolated to 82.86 C (yield onset)


def deck(sig_mpa: float, with_plastic: bool) -> str:
    """Unit cube, 3-2-1 support, uniform tensile traction on x=1 via nodal forces."""
    L = ["*NODE"]
    pts = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
           (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    for i, (x, y, z) in enumerate(pts, 1):
        L.append(f"{i}, {x}., {y}., {z}.")
    L += ["*ELEMENT, TYPE=C3D8, ELSET=EALL", "1, 1,2,3,4,5,6,7,8",
          "*MATERIAL, NAME=SLD", "*ELASTIC", "39000., 0.36, 75.", "36000., 0.36, 100."]
    if with_plastic:
        L += ["*PLASTIC", "16.17, 0., 75.", "19.9721, 0.02, 75.",
              "13.0824, 0., 100.", "16.1879, 0.02, 100."]
    A75, n75 = norton_at_T(75.0); A100, n100 = norton_at_T(100.0)
    L += ["*CREEP, LAW=NORTON",
          f"{A75:.6e}, {n75:.6g}, 0., 75.", f"{A100:.6e}, {n100:.6g}, 0., 100.",
          "*EXPANSION, ZERO=25.", "0.",
          "*SOLID SECTION, ELSET=EALL, MATERIAL=SLD",
          "*BOUNDARY", "1,1,3", "4,1", "4,3", "5,1", "5,2", "2,3", "3,3", "8,1",
          f"*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"1,{T_C}", f"2,{T_C}", f"3,{T_C}",
          f"4,{T_C}", f"5,{T_C}", f"6,{T_C}", f"7,{T_C}", f"8,{T_C}",
          "*STEP, INC=20000", "*VISCO, CETOL=1e-4",
          f"0.001, {HOLD}, 1e-9, {HOLD/200}",
          "*TEMPERATURE"] + [f"{i},{T_C}" for i in range(1, 9)] + [
          "*CLOAD"] + [f"{i},1,{sig_mpa/4:.8f}" for i in (2, 3, 6, 7)] + [
          "*EL PRINT, ELSET=EALL", "S, PEEQ", "*END STEP"]
    return "\n".join(L) + "\n"


def run(tag: str, sig: float, with_plastic: bool):
    p = WD / f"{tag}.inp"
    p.write_text(deck(sig, with_plastic))
    subprocess.run(["ccx", "-i", str(p.with_suffix(""))], cwd=WD, capture_output=True)
    d = WD / f"{tag}.dat"
    if not d.is_file():
        return None
    ser, kind, tm = [], None, None
    for l in d.read_text().splitlines():
        h = re.match(r"\s*(stresses|equivalent plastic strain).*time\s+([0-9.E+-]+)", l)
        if h:
            kind, tm = h.group(1), float(h.group(2)); continue
        q = l.split()
        if not (kind and q and q[0].isdigit()):
            continue
        if kind == "stresses" and len(q) == 8:
            ser.append(["S", tm, float(q[2])])
        elif kind == "equivalent plastic strain" and len(q) >= 3:
            ser.append(["P", tm, float(q[2])])
    S = {t: v for k, t, v in ser if k == "S"}
    P = {t: v for k, t, v in ser if k == "P"}
    ts = sorted(set(S) & set(P))
    return [(t, S[t], P[t]) for t in ts]


def main() -> int:
    A, n = norton_at_T(T_C)
    print(f"Norton card at {T_C} C:  A = {A:.4e}, n = {n:.4f}   "
          f"yield onset sigma_y = {SIG0_AT_T} MPa\n")
    print(f"{'sigma':>7} {'plastic?':>9} {'measured rate':>15} {'A*sig^n':>13} "
          f"{'A*(sig-sy)^n':>14} {'which matches':>16}")
    for sig in (20.0, 25.0, 30.0):
        for wp, lab in ((False, "no"), (True, "YES")):
            r = run(f"p_{int(sig)}_{lab}", sig, wp)
            if not r or len(r) < 5:
                print(f"{sig:7.1f} {lab:>9}  FAILED"); continue
            mid = [x for x in r if 0.5 * HOLD < x[0] <= HOLD]
            if len(mid) < 3:
                mid = r[-4:]
            rate = (mid[-1][2] - mid[0][2]) / (mid[-1][0] - mid[0][0])
            full = A * sig ** n
            over = A * max(sig - SIG0_AT_T, 1e-12) ** n
            pick = ("A*sig^n" if abs(math.log10(max(rate, 1e-30) / full)) <
                    abs(math.log10(max(rate, 1e-30) / max(over, 1e-30))) else "OVERSTRESS")
            print(f"{sig:7.1f} {lab:>9} {rate:15.4e} {full:13.4e} {over:14.4e} {pick:>16}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
