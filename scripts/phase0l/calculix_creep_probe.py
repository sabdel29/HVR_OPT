#!/usr/bin/env python3
"""Phase-0L Part IV -- controlled single-element probes of the CalculiX viscoplastic law.

Part III derived the following from the CalculiX 2.23 source (src/incplas.f, src/creeps.f,
src/materialdata_me.f). With *PLASTIC and *CREEP,LAW=NORTON both present (kode = -52) in a
*VISCO step (ivisco = 1):

    ftrial = sqrt(2/3) * (sigma_vm,trial - sigma_y(eps_in))          [incplas.f:310]
    if ftrial <= 1e-10  ->  NO inelastic strain at all                [incplas.f:311]
    qtild  = (ftrial - ...) / (sqrt(2/3) * J)  ==  sigma_vm - sigma_y(eps_in)
    decra(1) = A * (ttime+time)**m * dtime * qtild**n                 [incplas.f:141,605]

These probes test that derivation against the binary, using the PRODUCTION material card.
Candidate laws, evaluated pointwise at the measured PEEQ:

    H1  edot = A * sigma_vm ** n                    (the variable the card was FITTED in)
    H2  edot = A * (sigma_vm - sigma_y0(T)) ** n    (overstress, no hardening)
    H3  edot = A * (sigma_vm - sigma_y(T,PEEQ))**n  (overstress + bilinear hardening) <- source

Tests follow the Phase-0L brief, Part IV:

  TEST A  creep only, no *PLASTIC card        -- is it eps_dot = A sigma^n?
  TEST B  *PLASTIC + *CREEP, same stresses    -- A sigma^n, A (sigma-sigma_y)^n, or other?
  TEST C  total stress below sigma_y          -- does creep occur at all?
  TEST D  narrow sweep across sigma_y         -- discontinuity / shifted power law?
  TEST E  temperature dependence              -- incl. 125/150 C where the plastic card
                                                 is extrapolated beyond its 122 C source
  TEST F  (extra) reproduction of the 19 calibration points
  TEST G  (extra) form of the temperature interpolation: linear in A, or Arrhenius?
  TEST H  (extra) the time-hardening exponent m
"""
from __future__ import annotations
import csv, math, re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
import solder_model as sm                                                   # noqa: E402

WD = R / "results" / "phase0l" / "ccx_probe"
WD.mkdir(parents=True, exist_ok=True)
CARD_TEMPS = list(sm.DATA_TEMPS)                 # 45, 80, 115, 150
SWEEP = (5.0, 10.0, 15.0, 25.0, 50.0, 75.0, 100.0)
EPS_SAT = 0.02                                   # bilinear *PLASTIC saturation strain
ROWS: list[dict] = []


def card_sigma0(T: float, temps=None) -> float:
    """sigma_y AS THE SOLVER SEES IT: linear between *PLASTIC card rows, clamped outside.
    The card rows are sigma0_of_T() evaluated at the card temperatures; above 122 C the raw
    Chaboche table clamps while the card keeps interpolating, so the two differ there."""
    temps = sorted(temps or CARD_TEMPS)
    ys = [sm.sigma0_of_T(t) for t in temps]
    if T <= temps[0]:
        return ys[0]
    if T >= temps[-1]:
        return ys[-1]
    i = max(j for j, t in enumerate(temps) if t <= T)
    if temps[i] == T:
        return ys[i]
    w = (T - temps[i]) / (temps[i+1] - temps[i])
    return ys[i] + (ys[i+1] - ys[i]) * w


def card_sat(T: float, temps=None) -> float:
    temps = sorted(temps or CARD_TEMPS)
    ys = [sm.sat_stress_of_T(t) for t in temps]
    if T <= temps[0]:
        return ys[0]
    if T >= temps[-1]:
        return ys[-1]
    i = max(j for j, t in enumerate(temps) if t <= T)
    if temps[i] == T:
        return ys[i]
    w = (T - temps[i]) / (temps[i+1] - temps[i])
    return ys[i] + (ys[i+1] - ys[i]) * w


def sigma_y(T: float, peeq: float) -> float:
    s0, ss = card_sigma0(T), card_sat(T)
    return s0 + (ss - s0) * min(max(peeq, 0.0), EPS_SAT) / EPS_SAT


def card(T: float, temps=None):
    """A and n AS THE SOLVER SEES THEM: linear in A and n between the deck's *CREEP rows,
    clamped outside (creeps.f:300-330 then materialdata_me.f:413-429).  This is NOT
    sm.norton_at(), which interpolates the RATE on an Arrhenius basis -- the difference
    between the two is measured in TEST G."""
    temps = sorted(temps or CARD_TEMPS)
    rows = [(t, sm.fit_norton_data(t) if t in sm.DATA_TEMPS else sm.norton_at(t))
            for t in temps]
    if T <= rows[0][0]:
        return rows[0][1]["A"], rows[0][1]["n"]
    if T >= rows[-1][0]:
        return rows[-1][1]["A"], rows[-1][1]["n"]
    i = max(j for j, (t, _) in enumerate(rows) if t <= T)
    if rows[i][0] == T:
        return rows[i][1]["A"], rows[i][1]["n"]
    w = (T - rows[i][0]) / (rows[i+1][0] - rows[i][0])
    return (rows[i][1]["A"] + (rows[i+1][1]["A"] - rows[i][1]["A"]) * w,
            rows[i][1]["n"] + (rows[i+1][1]["n"] - rows[i][1]["n"]) * w)


def predict(T, sig, peeq, A=None, n=None, yield_on=True):
    if A is None:
        A, n = card(T)
    y0 = card_sigma0(T) if yield_on else 0.0
    y = sigma_y(T, peeq) if yield_on else 0.0
    return {"H1": A * sig ** n,
            "H2": A * (sig - y0) ** n if sig > y0 else 0.0,
            "H3": A * (sig - y) ** n if sig > y else 0.0, "sigma_y": y}


def material(temps, plastic: str = "full") -> list[str]:
    """plastic: 'full' = production card; 'none' = omit *PLASTIC; 'zero' = sigma_y ~ 0."""
    c = sm.calculix_cards(temps)
    L = ["*MATERIAL, NAME=SLD", "*ELASTIC"]
    L += [f"{e:.6g}, {nu:.4g}, {T:.1f}" for e, nu, T in c["elastic"]]
    if plastic == "full":
        L.append("*PLASTIC")
        L += [f"{s:.6g}, {p:.4g}, {T:.1f}" for s, p, T in c["plastic"]]
    elif plastic == "zero":
        L.append("*PLASTIC")
        for T in temps:                       # flat, effectively zero yield surface
            L += [f"1.E-6, 0., {T:.1f}", f"1.E-6, 0.02, {T:.1f}"]
    L.append("*CREEP, LAW=NORTON")
    L += [f"{A:.6e}, {n:.6g}, {m:.4g}, {T:.1f}" for A, n, m, T in c["creep"]]
    L += ["*EXPANSION, ZERO=25.", f"{c['expansion']:.4g}"]
    return L


def deck(sig_mpa, T_c, hold, temps=None, t_offset=0.0, direct=False, plastic="full") -> str:
    temps = temps or CARD_TEMPS
    pts = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
           (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    L = ["*NODE"] + [f"{i}, {x}., {y}., {z}." for i, (x, y, z) in enumerate(pts, 1)]
    L += ["*ELEMENT, TYPE=C3D8, ELSET=EALL", "1, 1,2,3,4,5,6,7,8"]
    L += material(temps, plastic)
    L += ["*SOLID SECTION, ELSET=EALL, MATERIAL=SLD",
          "*AMPLITUDE, NAME=AJUMP", "0., 1., 1.E30, 1.",
          "*BOUNDARY", "1,1,3", "4,1", "4,3", "5,1", "5,2", "2,3", "3,3", "8,1",
          "*INITIAL CONDITIONS, TYPE=TEMPERATURE"] + [f"{i},{T_c}" for i in range(1, 9)]
    if t_offset > 0.0:
        L += ["*STEP, INC=10", "*VISCO, CETOL=1.E-5, DIRECT",
              f"{t_offset:.8e}, {t_offset:.8e}",
              "*TEMPERATURE"] + [f"{i},{T_c}" for i in range(1, 9)] + ["*END STEP"]
    if direct:
        L += ["*STEP, INC=1000", "*VISCO, CETOL=1.E-5, DIRECT",
              f"{hold/40.0:.8e}, {hold:.8e}",
              "*TEMPERATURE"] + [f"{i},{T_c}" for i in range(1, 9)]
    else:
        L += ["*STEP, INC=100000", "*VISCO, CETOL=1.E-5",
              f"{hold/2000.0:.6e}, {hold:.6e}, 1.E-14, {hold/40.0:.6e}",
              "*TEMPERATURE"] + [f"{i},{T_c}" for i in range(1, 9)]
    L += ["*CLOAD, AMPLITUDE=AJUMP"] + [f"{i},1,{sig_mpa/4.0:.10f}" for i in (2, 3, 6, 7)]
    L += ["*EL PRINT, ELSET=EALL, FREQUENCY=1", "S, PEEQ", "*END STEP"]
    return "\n".join(L) + "\n"


def run(tag: str, **kw):
    """-> [(time, sigma_xx, PEEQ)] at integration point 1, or None if the solver failed."""
    (WD / f"{tag}.inp").write_text(deck(**kw))
    cp = subprocess.run(["ccx", "-i", tag], cwd=WD, capture_output=True, text=True)
    (WD / f"{tag}.log").write_text(cp.stdout + cp.stderr)
    d = WD / f"{tag}.dat"
    if not d.is_file() or not d.read_text().strip():
        return None
    S, P, kind, tm = {}, {}, None, None
    for line in d.read_text().splitlines():
        h = re.match(r"\s*(stresses|equivalent plastic strain).*time\s+([0-9.E+-]+)", line)
        if h:
            kind, tm = h.group(1), float(h.group(2)); continue
        q = line.split()
        if not (kind and q and q[0].isdigit()):
            continue
        if kind == "stresses" and len(q) == 8 and q[1] == "1":
            S[tm] = float(q[2])
        elif kind == "equivalent plastic strain" and len(q) >= 3 and q[1] == "1":
            P[tm] = float(q[2])
    ts = sorted(set(S) & set(P))
    return [(t, S[t], P[t]) for t in ts] or None


def peeq_ordered(tag: str):
    """PEEQ per increment in FILE ORDER. CalculiX prints time to ~7 digits, so once the
    total analysis time is large the printed times collide and a time-keyed dict silently
    drops increments. TEST H compares runs that differ only in elapsed time."""
    out, inblk = [], False
    for line in (WD / f"{tag}.dat").read_text().splitlines():
        if re.match(r"\s*equivalent plastic strain", line):
            inblk = True; continue
        if "INCREMENT" in line or "S T E P" in line:
            inblk = False; continue
        q = line.split()
        if inblk and len(q) == 3 and q[0] == "1" and q[1] == "1":
            out.append(float(q[2]))
    return out


def hold_for(T, sig, yield_on=True, target=5.0e-4):
    p = predict(T, sig, 0.0, yield_on=yield_on)
    r = max(p["H1"], p["H3"])
    return min(max(target / r if r > 0 else 1.0e9, 1.0e-4), 1.0e9)


def record(ser, T, sig, test, tag, A=None, n=None, yield_on=True):
    """Per-increment measured rate vs each candidate law at the interval midpoint."""
    out = []
    for (t0, s0, p0), (t1, s1, p1) in zip(ser, ser[1:]):
        dt = t1 - t0
        if dt <= 0:
            continue
        rate, pm, sg = (p1 - p0) / dt, 0.5 * (p0 + p1), 0.5 * (s0 + s1)
        pr = predict(T, sg, pm, A, n, yield_on)
        row = {"test": test, "tag": tag, "T_C": T, "sigma_nom_MPa": sig,
               "sigma_meas_MPa": sg, "t0_s": t0, "t1_s": t1, "dt_s": dt,
               "peeq0": p0, "peeq1": p1, "peeq_mid": pm, "rate_meas_1_per_s": rate,
               "sigma_y_mid_MPa": pr["sigma_y"], "overstress_MPa": sg - pr["sigma_y"],
               "rate_H1": pr["H1"], "rate_H2": pr["H2"], "rate_H3": pr["H3"]}
        for h in ("H1", "H2", "H3"):
            row[f"ratio_{h}"] = (rate / pr[h]) if pr[h] > 0 else (
                float("inf") if rate > 0 else float("nan"))
        out.append(row)
    ROWS.extend(out)
    return out


def last_rate(iv):
    return iv[-1]["rate_meas_1_per_s"] if iv else 0.0


def band(rows, key):
    v = [r[key] for r in rows if r[key] == r[key] and 0 < r[key] < float("inf")]
    if not v:
        return None
    lv = sorted(abs(math.log10(x)) for x in v)
    return len(v), lv[len(lv) // 2], max(lv)


def test_A():
    print("=" * 110)
    print("TEST A -- CREEP ONLY.  Is the law eps_dot = A sigma^n when there is no yield surface?")
    print("=" * 110)
    print("  Two ways to remove the yield surface are probed, because they are NOT equivalent:")
    print("    'none' = omit *PLASTIC entirely.  materialdata_me.f sets plconloc(801)=0.5, so")
    print("             incplas.f:130 takes user_hardening=1 and calls uhardening(), whose")
    print("             default body (src/uhardening.f) is an empty RETURN -- it never assigns")
    print("             fiso, which incplas.f never initialises.  The yield stress is then")
    print("             whatever was left on the stack.  This is undefined behaviour.")
    print("    'zero' = keep *PLASTIC but set sigma_y = 1e-6 MPa, flat.  user_hardening stays 0")
    print("             and the overstress equals sigma_vm to 7 significant figures.")
    print()
    print(f"{'mode':>6} {'T':>5} {'sigma':>7} {'CCX edot':>12} {'A sigma^n':>12} {'meas/Asig^n':>12}")
    for mode in ("none", "zero"):
        for T in CARD_TEMPS:
            for sig in SWEEP:
                tag = f"A_{mode}_T{T:g}_s{sig:g}".replace(".", "p")
                hold = hold_for(T, sig, yield_on=False)
                ser = run(tag, sig_mpa=sig, T_c=T, hold=hold, plastic=mode)
                if ser is None:
                    print(f"{mode:>6} {T:5.0f} {sig:7.1f}   SOLVER FAILED"); continue
                iv = record(ser, T, sig, f"A_{mode}", tag, yield_on=False)
                r = last_rate(iv)
                A, n = card(T)
                p = A * sig ** n
                if T == CARD_TEMPS[0] or sig in (5.0, 25.0, 100.0):
                    print(f"{mode:>6} {T:5.0f} {sig:7.1f} {r:12.4e} {p:12.4e} "
                          f"{(r/p if p else float('nan')):12.6f}")
    for mode in ("none", "zero"):
        b = band([r for r in ROWS if r["test"] == f"A_{mode}"
                  and r["rate_meas_1_per_s"] > 1e-18], "ratio_H1")
        if b:
            print(f"  mode '{mode}': n={b[0]:4d} live increments, "
                  f"median |log10(meas / A sigma^n)| = {b[1]:.6f}  (max {b[2]:.6f})")
        else:
            print(f"  mode '{mode}': NO measurable creep in any increment")


def test_B():
    print()
    print("=" * 110)
    print("TEST B -- *PLASTIC + *CREEP.  A sigma^n, A (sigma - sigma_y)^n, or something else?")
    print("=" * 110)
    print(f"{'T':>5} {'sigma':>7} {'sig_y0':>7} {'overstr':>8} {'CCX edot':>12} "
          f"{'H1':>11} {'H2':>11} {'H3':>11} {'meas/H3':>9}")
    for T in CARD_TEMPS:
        for sig in SWEEP:
            tag = f"B_T{T:g}_s{sig:g}".replace(".", "p")
            ser = run(tag, sig_mpa=sig, T_c=T, hold=hold_for(T, sig))
            if ser is None:
                print(f"{T:5.0f} {sig:7.1f}   SOLVER FAILED"); continue
            iv = record(ser, T, sig, "B", tag)
            if not iv:
                continue
            L = iv[-1]; r = L["ratio_H3"]
            print(f"{T:5.0f} {sig:7.1f} {sm.sigma0_of_T(T):7.2f} "
                  f"{sig-sm.sigma0_of_T(T):+8.2f} {L['rate_meas_1_per_s']:12.4e} "
                  f"{L['rate_H1']:11.3e} {L['rate_H2']:11.3e} {L['rate_H3']:11.3e} "
                  f"{(f'{r:9.4f}' if r == r and r != float('inf') else '      n/a')}")
    live = [r for r in ROWS if r["test"] == "B" and r["rate_meas_1_per_s"] > 1e-18]
    print(f"\n  {len(live)} increments with measurable creep, of "
          f"{len([r for r in ROWS if r['test']=='B'])}")
    for h in ("H1", "H2", "H3"):
        b = band(live, f"ratio_{h}")
        if b:
            print(f"    {h}: median |log10(meas/pred)| = {b[1]:9.6f}  max = {b[2]:9.6f}  "
                  f"-> median factor {10**b[1]:.5g}x")
    dead = [r for r in ROWS if r["test"] == "B" and r["rate_meas_1_per_s"] <= 1e-18
            and r["rate_H1"] > 0]
    print(f"    increments with ZERO measured creep but H1 predicting creep: {len(dead)}")


def test_C():
    print()
    print("=" * 110)
    print("TEST C -- BELOW YIELD.  Does creep occur when the total stress is under sigma_y?")
    print("=" * 110)
    print(f"{'T':>5} {'sigma':>7} {'sig_y0':>7} {'sigma/sig_y':>11} {'hold s':>10} "
          f"{'final PEEQ':>12} {'A sigma^n * hold':>17}  verdict")
    for T in CARD_TEMPS:
        y0 = sm.sigma0_of_T(T)
        for frac in (0.25, 0.50, 0.75, 0.90, 0.99):
            sig = frac * y0
            tag = f"C_T{T:g}_f{frac:g}".replace(".", "p")
            A, n = card(T)
            hold = min(max(1.0e-3 / (A * sig ** n), 1.0), 1.0e9)
            ser = run(tag, sig_mpa=sig, T_c=T, hold=hold)
            if ser is None:
                print(f"{T:5.0f} {sig:7.2f}   SOLVER FAILED"); continue
            record(ser, T, sig, "C", tag)
            pk = ser[-1][2]
            print(f"{T:5.0f} {sig:7.2f} {y0:7.2f} {frac:11.2f} {hold:10.2e} {pk:12.4e} "
                  f"{A*sig**n*hold:17.4e}  "
                  f"{'NO CREEP' if pk <= 1e-18 else 'creep occurred'}")


def test_D():
    print()
    print("=" * 110)
    print("TEST D -- JUST ABOVE YIELD.  Narrow sweep across sigma_y: discontinuity?")
    print("=" * 110)
    for T in (45.0, 115.0):
        y0 = sm.sigma0_of_T(T)
        print(f"  T = {T:.0f} C, sigma_y0 = {y0:.3f} MPa")
        print(f"    {'sigma':>9} {'sigma-sig_y':>12} {'CCX edot':>13} {'A(sig-sy)^n':>13} "
              f"{'ratio':>10}")
        for d in (-0.50, -0.10, -0.01, 0.01, 0.10, 0.50, 1.00, 2.00, 5.00):
            sig = y0 + d
            tag = f"D_T{T:g}_d{d:+g}".replace(".", "p").replace("+", "p").replace("-", "m")
            A, n = card(T)
            pr = A * d ** n if d > 0 else 0.0
            hold = min(max(5.0e-4 / pr if pr > 0 else 1.0e7, 1.0e-3), 1.0e9)
            ser = run(tag, sig_mpa=sig, T_c=T, hold=hold)
            if ser is None:
                print(f"    {sig:9.3f}   SOLVER FAILED"); continue
            iv = record(ser, T, sig, "D", tag)
            r = last_rate(iv)
            print(f"    {sig:9.3f} {d:+12.2f} {r:13.4e} {pr:13.4e} "
                  f"{(f'{r/pr:10.5f}' if pr > 0 else ('   inf' if r > 0 else '     0')):>10}")


def test_E():
    print()
    print("=" * 110)
    print("TEST E -- TEMPERATURE.  Card nodes 45/80/115/150 C, plus the plastic-card")
    print("          extrapolation exposed at 125 and 150 C (Chaboche source ends at 122 C).")
    print("=" * 110)
    print(f"{'T':>6} {'plastic card':>14} {'sigma':>7} {'sig_y used':>11} {'CCX edot':>12} "
          f"{'H3':>12} {'ratio':>9}")
    for T in (45.0, 80.0, 115.0, 125.0, 150.0):
        src = "INTERPOLATED" if T <= 122.0 else "EXTRAPOLATED"
        for sig in (25.0, 50.0):
            tag = f"E_T{T:g}_s{sig:g}".replace(".", "p")
            ser = run(tag, sig_mpa=sig, T_c=T, hold=hold_for(T, sig))
            if ser is None:
                print(f"{T:6.1f} {src:>14} {sig:7.1f}   SOLVER FAILED"); continue
            iv = record(ser, T, sig, "E", tag)
            if not iv:
                continue
            L = iv[-1]
            print(f"{T:6.1f} {src:>14} {sig:7.1f} {L['sigma_y_mid_MPa']:11.3f} "
                  f"{L['rate_meas_1_per_s']:12.4e} {L['rate_H3']:12.4e} "
                  f"{L['ratio_H3']:9.5f}")
    print("  NOTE: at 125 and 150 C the *PLASTIC card rows are themselves a linear")
    print("        extrapolation of a Chaboche table whose last measured node is 122 C.")


def test_F():
    print()
    print("=" * 110)
    print("TEST F (extra) -- can the card reproduce its own 19 calibration points?")
    print("=" * 110)
    print(f"{'T':>5} {'sigma':>7} {'sig_y0':>7} {'overstr':>8} {'Yuan edot':>11} "
          f"{'CCX edot':>11} {'H1':>11}   verdict")
    nz = 0
    for (T, sig, ed) in sm.CREEP_DATA:
        tag = f"F_T{T:g}_s{sig:g}".replace(".", "p")
        ser = run(tag, sig_mpa=sig, T_c=T, hold=hold_for(T, sig))
        if ser is None:
            print(f"{T:5.0f} {sig:7.2f}   SOLVER FAILED"); continue
        iv = record(ser, T, sig, "F", tag)
        r = last_rate(iv)
        y0, (A, n) = sm.sigma0_of_T(T), card(T)
        ok = ("REPRODUCED" if r > 0 and 0.2 < r / ed < 5.0
              else "ZERO CREEP" if r <= 1e-20 else "WRONG RATE")
        nz += (ok == "REPRODUCED")
        print(f"{T:5.0f} {sig:7.2f} {y0:7.2f} {sig-y0:+8.2f} {ed:11.3e} {r:11.3e} "
              f"{A*sig**n:11.3e}   {ok}")
    print(f"  reproduced within a factor of 5: {nz} of {len(sm.CREEP_DATA)}")


def test_G():
    print()
    print("=" * 110)
    print("TEST G (extra) -- form of the temperature interpolation of the Norton card")
    print("=" * 110)
    for Tq, Ta, Tb in ((62.5, 45.0, 80.0), (97.5, 80.0, 115.0), (132.5, 115.0, 150.0)):
        sig, tag = 40.0, f"G_T{Tq:g}".replace(".", "p")
        Aa, na = card(Ta); Ab, nb = card(Tb)
        w = (Tq - Ta) / (Tb - Ta)
        A_lin, n_lin = Aa + (Ab - Aa) * w, na + (nb - na) * w
        y_lin = card_sigma0(Tq)
        f_arr = sm.norton_at(Tq)
        hold = min(max(5e-4 / max(A_lin * max(sig - y_lin, 1e-9) ** n_lin, 1e-30),
                       1e-4), 1e9)
        ser = run(tag, sig_mpa=sig, T_c=Tq, hold=hold)
        if ser is None:
            print(f"{Tq:6.1f} C  SOLVER FAILED"); continue
        iv = record(ser, Tq, sig, "G", tag, A=A_lin, n=n_lin)
        r, pm = last_rate(iv), iv[-1]["peeq_mid"]
        p_nohard = A_lin * (sig - y_lin) ** n_lin              # no hardening correction
        p_lin = predict(Tq, sig, pm, A_lin, n_lin)["H3"]        # full solver model
        p_arr = predict(Tq, sig, pm, f_arr["A"], f_arr["n"])["H3"]
        print(f"{Tq:6.1f} C  measured {r:11.4e}")
        print(f"            linear-in-A + hardening (solver model) {p_lin:11.4e} "
              f"(x{r/p_lin:8.5f})   <- what incplas.f does")
        print(f"            linear-in-A, hardening ignored         {p_nohard:11.4e} "
              f"(x{r/p_nohard:8.5f})")
        print(f"            ARRHENIUS in rate (norton_at)          {p_arr:11.4e} "
              f"(x{r/p_arr:8.5f})   <- what solder_model.py assumes")


def test_H():
    print()
    print("=" * 110)
    print("TEST H (extra) -- total-analysis-time dependence (the Norton m exponent)")
    print("=" * 110)
    T, sig, hold, ninc = 80.0, 40.0, 4.0, 40
    dt, base, ser_h = hold / ninc, None, {}
    for k, off in enumerate((0.0, 1.0e3, 1.0e6, 1.0e9)):
        tag = f"H_{k}"
        run(tag, sig_mpa=sig, T_c=T, hold=hold, t_offset=off, direct=True)
        pe = peeq_ordered(tag)
        if not pe:
            print(f"  t_offset={off:9.3g}  SOLVER FAILED"); continue
        ser_h[off] = pe
        base = base or pe
        print(f"  t_offset = {off:9.3g} s : {len(pe):3d} increments, final PEEQ = "
              f"{pe[-1]:.12e}, ratio to offset 0 = {pe[-1]/base[-1]:.12f}")
        for q in range(1, len(pe)):
            rate, pm = (pe[q] - pe[q-1]) / dt, 0.5 * (pe[q] + pe[q-1])
            pr = predict(T, sig, pm)
            ROWS.append({"test": "H", "tag": tag, "T_C": T, "sigma_nom_MPa": sig,
                         "sigma_meas_MPa": sig, "t0_s": off + (q-1)*dt, "t1_s": off + q*dt,
                         "dt_s": dt, "peeq0": pe[q-1], "peeq1": pe[q], "peeq_mid": pm,
                         "rate_meas_1_per_s": rate, "sigma_y_mid_MPa": pr["sigma_y"],
                         "overstress_MPa": sig - pr["sigma_y"], "rate_H1": pr["H1"],
                         "rate_H2": pr["H2"], "rate_H3": pr["H3"],
                         "ratio_H1": rate / pr["H1"] if pr["H1"] else float("nan"),
                         "ratio_H2": rate / pr["H2"] if pr["H2"] else float("nan"),
                         "ratio_H3": rate / pr["H3"] if pr["H3"] else float("nan")})
    if len(ser_h) > 1:
        n = min(len(v) for v in ser_h.values())
        worst = max(abs(v[q] / base[q] - 1.0)
                    for v in ser_h.values() for q in range(n) if base[q])
        print(f"  increment-wise worst |PEEQ/PEEQ(offset 0) - 1| = {worst:.3e}")
        print(f"  -> m = 0 (no total-analysis-time dependence) is "
              f"{'CONFIRMED' if worst < 1e-9 else 'REFUTED'}")


def main() -> int:
    for f in (test_A, test_B, test_C, test_D, test_E, test_F, test_G, test_H):
        f()
    out = R / "results" / "phase0l" / "calculix_creep_probe.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0].keys()))
        w.writeheader(); w.writerows(ROWS)
    print(f"\nwrote {out}  ({len(ROWS)} increments)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
