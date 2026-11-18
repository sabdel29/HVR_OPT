"""Uncertainty of every compared output, per architecture, and the comparison rule
(TCPMT review MC13).

NUMERICAL uncertainty of an output y of architecture a (production mesh r21):
  U_mesh  the extrapolation of the production ladder r21 -> r31 (h = 1/2 -> 1/3) at the
          order P_ORDER = 0.6, e = F (y_r31 - y_r21) with F = h21^p / (h21^p - h31^p) = 4.63.
          The order is the LOWEST observed in the independent MOOSE ladders of the complete
          package (uniform 2x2x2 and 3x3x3 refinement: 0.60-0.63 in the converter, substrate,
          BGA and board; in-plane x1..x4: 0.6 -> 1.1; fullpkg_verification.json), because the
          coarsest production level r11 is not in the asymptotic range and a three-level
          Richardson estimate understates the error
  U_tt    the through-thickness split r11 -> r12, as a relative change (Z1, Z2; Z3 takes
          the larger of the two)
  U_et    the E-T stop: 0.1 % of the loss, 0.25 K of a temperature
  U_ref   the matched-reference agreement of the solver that produced y: 0.13 % of the
          temperature rise (thermal unit cells, AEDT/MOOSE), 0.43 % of a displacement
          (bimaterial closed form)
  U = U_mesh + U_tt + U_et + U_ref (linear sum: no credit for independence)
For a tier case (same mesh as its architecture's production case) the production relative
uncertainty is applied to the tier value (temperatures: to the rise above the inlet).
The local response carries its own U = U_mesh + U_time + U_cyc (local_mesh_study.json, or
the solder study's stabilized values when present) plus the L0 -> L3 offset when the
compared values are L0 solves.

RULE: a difference D = y_b - y_a between two architectures is RESOLVED when
|D| > 2 (U_a + U_b), i.e. without credit for the correlation of errors on one mesh family.
It is RESOLVED WITH CORRELATION CREDIT when it exceeds twice the paired estimate, in which
the signed discretization errors of the two architectures (same mesh family, same direction)
cancel, the matched-reference agreement (common solver) cancels, and the fixed-point stops
and local-response uncertainties add. MODEL-FORM uncertainty (material cards, boundaries, omitted physics)
is not added to U: it is handled by rerunning both architectures under each declared
alternative (the robustness map), and a resolved ranking that a declared alternative reverses
is CONDITIONAL on that decision.

    python tcpmt_uncertainty.py   -> research/tcpmt_revision/uncertainty.json,
                                     manuscript_v2/tab_uncertainty.tex
"""
from __future__ import annotations

import json
import os
from pathlib import Path

R = Path(__file__).resolve().parents[1]
FC = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"
SENS = FC / "sensitivity"
TR = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"
OUT = TR / "uncertainty.json"
TAB = Path(os.environ.get("ETM_RESULTS_ROOT") or R) / "manuscript_v2" / "tab_uncertainty.tex"
ATAG = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}
OBS = ("P", "T", "warp", "du")
U_ET = {"P_rel": 1e-3, "T_K": 0.25}
U_REF = {"T_rel_rise": 0.0013, "mech_rel": 0.0043}
T_IN = 25.0
P_ORDER = 0.6
F_MESH = 0.5 ** P_ORDER / (0.5 ** P_ORDER - (1 / 3) ** P_ORDER)


def J(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.is_file() else None


def obs(c):
    if not c:
        return None
    me = c.get("mechanics") or {}
    cr = (me.get("joint_search") or {}).get("critical") or {}
    return {"P": c["P_loss_w"], "T": c["thermal"]["T_max_C"],
            "warp": me.get("die_warpage_pv_um"), "du": cr.get("du_um"),
            "Tj": cr.get("T_C")}


def richardson(t1, t2, t3, h=(1.0, 1 / 2, 1 / 3)):
    d1, d2 = t2 - t1, t3 - t2
    if d1 == 0 or d2 == 0 or d1 * d2 < 0:
        return None
    target = d1 / d2
    f = lambda p: (h[0] ** p - h[1] ** p) / (h[1] ** p - h[2] ** p) - target
    lo, hi = 0.2, 6.0
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    p = 0.5 * (lo + hi)
    c = d1 / (h[1] ** p - h[0] ** p)
    return {"order": p, "extrapolated": t1 - c * h[0] ** p}


def production_uncertainty(a):
    lv = {r: obs(J(FC / f"etm_{a}_HV_S0_h1.1{'' if r == 'r11' else '_' + r}.json"))
          for r in ("r11", "r21", "r31", "r12")}
    out = {}
    tt_rel = {}
    for y in OBS:
        v11, v21, v31, v12 = (lv[r][y] if lv[r] else None for r in ("r11", "r21", "r31", "r12"))
        if v12 is not None and v11:
            tt_rel[y] = abs(v12 - v11) / abs(v11)
    for y in OBS:
        v11, v21, v31 = (lv[r][y] if lv[r] else None for r in ("r11", "r21", "r31"))
        rich = (richardson(v11, v21, v31) if None not in (v11, v21, v31) else None)
        e = F_MESH * (v31 - v21)                # signed: r21 -> converged
        u_mesh = abs(e)
        basis = f"extrapolation of r21 -> r31 at order {P_ORDER} (lowest MOOSE-ladder order)"
        out[y] = {"value_r21": v21, "U_mesh": u_mesh, "e_mesh_signed": e,
                  "mesh_basis": basis,
                  "richardson_three_level": rich["extrapolated"] if rich else None,
                  "tt_rel": tt_rel.get(y)}
    return out


def assemble():
    prod = {a: production_uncertainty(a) for a in ("Z1", "Z2", "Z3")}
    # Z3 has no through-thickness level: take the larger of Z1 and Z2
    for y in OBS:
        prod["Z3"][y]["tt_rel"] = max(prod["Z1"][y]["tt_rel"] or 0, prod["Z2"][y]["tt_rel"] or 0)
    rel = {}
    for a, d in prod.items():
        rel[a] = {}
        for y, v in d.items():
            x = v["value_r21"]
            base = (x - T_IN) if y == "T" else x
            u_mesh_rel = v["U_mesh"] / abs(base)
            u_tt = v["tt_rel"] or 0.0
            u_et = (U_ET["P_rel"] if y == "P" else (U_ET["T_K"] / abs(base) if y == "T" else 0.0))
            u_ref = (U_REF["T_rel_rise"] if y == "T" else (U_REF["mech_rel"] if y in ("warp", "du")
                                                           else 0.0))
            rel[a][y] = {"mesh": u_mesh_rel, "tt": u_tt, "et": u_et, "ref": u_ref,
                         "total": u_mesh_rel + u_tt + u_et + u_ref,
                         "e_mesh_rel_signed": v["e_mesh_signed"] / abs(base)}
    return prod, rel


TIERS = {
    "A": {"Z1": FC / "etm_Z1_HV_S0_h1.1_r21.json", "Z2": FC / "etm_Z2_HV_S0_h1.1_r21.json",
          "Z3": SENS / "etm_Z3_HV_S0__z3_land_t40_A_fvmap.json"},
    "B": {"Z1": SENS / "etm_Z1_HV_S0__z1_bottom_plate_tim.json",
          "Z2": SENS / "etm_Z2_HV_S0__z2_cooled_tim.json",
          "Z3": SENS / "etm_Z3_HV_S0__z3_land_t40_B_fvmap.json"},
}
#: tier L0 local responses (x1e-3 / cycle), replaced by the solder study when present
EPS_L0 = {"A": {"Z1": 5.80, "Z2": 8.03, "Z3": 13.47}, "B": {"Z1": 2.08, "Z2": 4.15, "Z3": 2.52}}


def local_u():
    lm = (J(FC / "local_mesh_study.json") or {}).get("cases", {})
    u = {a: (lm.get(f"{a}_HV_S0") or {}).get("U") for a in ("Z1", "Z2", "Z3")}
    l3 = {a: (lm.get(f"{a}_HV_S0") or {}).get("production_value") for a in ("Z1", "Z2", "Z3")}
    ss = J(TR / "solder_studies.json")
    eps, u_t, basis = {t: dict(v) for t, v in EPS_L0.items()}, {}, "4-cycle L0 (production)"
    if ss and (ss.get("stabilization") or {}).get("cases"):
        basis = "stabilized L0 (48 cycles; U = mesh + time + cycle + card grid)"
        for lab, v in ss["stabilization"]["cases"].items():
            t, a = lab.split("_")
            if v.get("stabilised") is not None:
                eps[t][a] = 1e3 * v["stabilised"]
            if v.get("U_stab_num") is not None:
                u_t[(t, a)] = v["U_stab_num"]
        zl = J(TR / "solder_z3land.json")          # Z3 with the coupled land side
        for t, v in ((zl or {}).get("cases") or {}).items():
            if v.get("stabilised") is not None:
                eps[t]["Z3"] = 1e3 * v["stabilised"]
                if v.get("U_stab_num") is not None:
                    u_t[(t, "Z3")] = v["U_stab_num"]
    return eps, u, u_t, l3, basis


def comparisons(rel):
    eps, u_loc, u_t, l3, eps_basis = local_u()
    cases = {t: {a: obs(J(f)) for a, f in v.items()} for t, v in TIERS.items()}
    U = {}
    for t, v in cases.items():
        for a, o in v.items():
            if not o:
                continue
            for y in OBS:
                x = o[y]
                if x is None:
                    continue
                base = (x - T_IN) if y == "T" else x
                U[(t, a, y)] = rel[a][y]["total"] * abs(base)
            # local response: own U (or the production arch's) + L0 -> L3 offset
            u_rel = u_t.get((t, a), u_loc.get(a) or 0.0)
            off = 0.0
            if not u_t and l3.get(a) and t == "A" and a in ("Z1", "Z2"):
                off = abs(eps["A"][a] - 1e3 * l3[a]) / (1e3 * l3[a])
            U[(t, a, "eps")] = (u_rel + off) * eps[t][a]
    res = []
    pairs = [("A", "Z1", "Z2"), ("A", "Z1", "Z3"), ("B", "Z2", "Z1"), ("B", "Z3", "Z1"),
             ("B", "Z2", "Z3")]
    for t, a, b in pairs:
        for y in OBS + ("eps",):
            ya = eps[t][a] if y == "eps" else (cases[t][a] or {}).get(y)
            yb = eps[t][b] if y == "eps" else (cases[t][b] or {}).get(y)
            if ya is None or yb is None:
                continue
            d = yb - ya
            ud = U.get((t, a, y), 0.0) + U.get((t, b, y), 0.0)
            if y == "eps":
                up = ud
            else:
                def signed(arch, val):
                    base = (val - T_IN) if y == "T" else val
                    return rel[arch][y]["e_mesh_rel_signed"] * abs(base)

                def indep(arch, val):
                    base = (val - T_IN) if y == "T" else val
                    return rel[arch][y]["et"] * abs(base)
                up = (abs(signed(b, yb) - signed(a, ya)) + indep(a, ya) + indep(b, yb)
                      + abs(rel[b][y]["tt"] * yb - rel[a][y]["tt"] * ya))
            verdict = ("resolved" if abs(d) > 2 * ud else
                       "resolved with correlation credit" if abs(d) > 2 * up else
                       "not resolved")
            res.append({"tier": t, "a": a, "b": b, "output": y, "y_a": ya, "y_b": yb,
                        "D": d, "U_a": U.get((t, a, y)), "U_b": U.get((t, b, y)),
                        "U_D": ud, "U_D_paired": up, "verdict": verdict,
                        "resolved": verdict != "not resolved",
                        "lower": a if d > 0 else b})
    return res, U, eps, eps_basis


def latex(prod, rel, U, res):
    names = {"P": "Loss (W)", "T": "Peak temp.\\ (K)", "warp": "Die warpage (\\textmu m)",
             "du": "$\\du$ (\\textmu m)", "eps": "$\\deps$ ($10^{-3}$/cycle)"}
    L = [r"% GENERATED by scripts/tcpmt_uncertainty.py -- do not edit",
         r"\begin{table}[!t]",
         r"\caption{Numerical uncertainty $U$ of each compared output (S0, production mesh) and "
         r"the comparisons it resolves: a gap is resolved when it exceeds $2(U_a+U_b)$.}",
         r"\label{tab:uncertainty}", r"\centering", r"\footnotesize",
         r"\setlength{\tabcolsep}{2.5pt}",
         r"\begin{tabular}{@{}lrrrrrr@{}}", r"\toprule",
         r" & \multicolumn{3}{c}{Cooling A: $\pm U$} & \multicolumn{3}{c}{Cooling B: $\pm U$}\\",
         r"\cmidrule(lr){2-4}\cmidrule(l){5-7}",
         r"Output & Z1 & Z2 & Z3 & Z1 & Z2 & Z3 \\", r"\midrule"]
    for y in OBS + ("eps",):
        cells = []
        for t in ("A", "B"):
            for a in ("Z1", "Z2", "Z3"):
                u = U.get((t, a, y))
                cells.append("--" if u is None else (f"{u:.2f}" if u < 10 else f"{u:.1f}"))
        L.append(f"{names[y]} & " + " & ".join(cells) + r" \\")
    L += [r"\midrule", r"\multicolumn{7}{@{}p{0.95\columnwidth}@{}}{\emph{Comparisons (lower "
          r"first). R: gap $>2(U_a+U_b)$; Rc: resolved only with the paired discretization errors "
          r"(same mesh family); --: not resolved.}}\\"]
    seen = {}
    for r in res:
        seen.setdefault((r["tier"], r["a"], r["b"]), []).append(r)
    for (t, a, b), rows in seen.items():
        code = {"resolved": "R", "resolved with correlation credit": "Rc", "not resolved": "--"}
        s = "; ".join(f"{names[r['output']].split(' (')[0]} {r['lower']} "
                      f"{code[r['verdict']]}" for r in rows)
        L.append(f"\\multicolumn{{7}}{{@{{}}p{{0.95\\columnwidth}}@{{}}}}{{{t}, {a}/{b}: {s}}}\\\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return L


def main():
    prod, rel = assemble()
    res, U, eps, eps_basis = comparisons(rel)
    mac = {}
    for (t, a, y), u in U.items():
        mac[f"U{t}{ATAG[a]}{ {'P': 'Ploss', 'T': 'Tmax', 'warp': 'Warp', 'du': 'Du', 'eps': 'Eps'}[y] }"
            .replace(" ", "")] = f"{u:.2f}"
    for a in ("Z1", "Z2", "Z3"):
        for y, tag in (("P", "Ploss"), ("T", "Tmax"), ("warp", "Warp"), ("du", "Du")):
            mac[f"Urel{ATAG[a]}{tag}"] = f"{100 * rel[a][y]['total']:.2f}"
    for r in res:
        k = f"Res{r['tier']}{ATAG[r['a']]}{ATAG[r['b']]}" + \
            {"P": "Ploss", "T": "Tmax", "warp": "Warp", "du": "Du", "eps": "Eps"}[r["output"]]
        mac[k] = r["verdict"]
        mac[k + "Ratio"] = f"{abs(r['D']) / r['U_D']:.1f}" if r["U_D"] else "--"
        mac[k + "RatioPaired"] = f"{abs(r['D']) / r['U_D_paired']:.1f}" if r["U_D_paired"] else "--"
    out = {"rule": __doc__.split("RULE:")[1].split("python")[0].strip(),
           "production": prod, "relative": rel,
           "U": {f"{t}.{a}.{y}": u for (t, a, y), u in U.items()},
           "eps_basis": eps_basis, "eps": eps, "comparisons": res, "macros": mac,
           "latex_supplement": latex(prod, rel, U, res)}
    OUT.write_text(json.dumps(out, indent=1, default=float))
    TAB.write_text("\n".join(latex(prod, rel, U, res)) + "\n")
    for r in res:
        print(f"{r['tier']} {r['a']}/{r['b']} {r['output']:5s} D={r['D']:+8.3f} U_D={r['U_D']:.3f} "
              f"paired={r['U_D_paired']:.3f} {r['verdict']}")
    return out


if __name__ == "__main__":
    main()
