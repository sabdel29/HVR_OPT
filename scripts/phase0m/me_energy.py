#!/usr/bin/env python3
"""Phase-0M Part 0-F -- SOLVER-COHERENT inelastic-energy reconstruction.

WHY THIS EXISTS
---------------
DEFECT #46 (Phase 0L-R) was a *class* of error, not a single bug. The production energy
metric reconstructed the inelastic strain in Python as

    eps_in = E_total - C^-1(T):S - alpha*(T - T_ref)

where E_total came from one parsed block of the .dat file and T came from a DIFFERENT
parsed block. At a step boundary CalculiX prints the same nominal time twice, so the two
parsers could -- and did -- land on opposite sides of the boundary. The spurious
alpha*(T_wrong - T_right) term is ISOTROPIC and of order 1.3e-3, which is large compared
with the inelastic strain increments it corrupted: the cycle energy was inflated 18.5 %.

Phase 0L-R fixed the symptom by making both parsers keep the LAST block at a repeated
time key. That is correct but fragile: it is a convention two independent functions have
to keep agreeing about forever.

Phase 0M removes the possibility. CalculiX can print ME, the MECHANICAL strain
(total minus thermal), for the same element set in the same output block as S and E. Then

    eps_in = ME - C^-1(T):S

and the thermal term -- the entire source of DEFECT #46 -- never appears. Temperature
survives only inside the elastic compliance C^-1(T), where a 55 K error moves E(T) by
6.6 GPa out of ~45 GPa and therefore moves an elastic strain of ~2e-3 by ~3e-4 -- and even
that is eliminated here, because T itself is recovered from the SAME output block:

    tr(E - ME) = 3*alpha*(T - T_zero)   ->   T = T_zero + tr(E - ME)/(3*alpha)

No separately parsed temperature block is used at any point. Three routes are computed and
compared so the claim is falsifiable rather than asserted:

  PROD     the production route (Python thermal reconstruction, DEFECT #46 parser fix)
  ME_NT    ME for the inelastic strain, NT-parsed temperature only inside E(T)
  ME_SELF  ME for the inelastic strain, temperature derived from tr(E - ME) -- fully
           solver-coherent, the route Phase 0M adopts
"""
from __future__ import annotations
import csv, json, math, re, sys, time
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0i", "phase0ir", "phase0jr", "phase0l", "phase0lr"):
    sys.path.insert(0, str(R / "scripts" / d))
import solder_model as sm                                                   # noqa: E402
from graded_joint import build_joint_graded                                 # noqa: E402
from joint import run as run_ccx, write_inp                                 # noqa: E402
from decompose import parse_temperature, eq_strain, CTE_SAC305              # noqa: E402
from cycle_audit import cycle_quantities, per_element_series                # noqa: E402
import replay as RP                                                         # noqa: E402
import replay_lr as RLR                                                     # noqa: E402

OUT = R / "results" / "phase0m"
WD = OUT / "wd"
WD.mkdir(parents=True, exist_ok=True)
NU = sm.NU

_KINDS = (r"stresses|strains|mechanical strains|equivalent plastic strain|volume")


def parse_tensors_me(dat: Path, elems: set | None = None) -> dict:
    """{time: {elem: {'S','E','ME','P','V'}}}, integration-point averaged.

    Identical in structure to decompose.parse_tensors but also captures ME. The regex
    alternation puts 'mechanical strains' BEFORE 'strains' so the longer label wins; with
    the order reversed CalculiX's 'mechanical strains' header matches the 'strains' branch
    and ME silently overwrites E. That ordering is negative-tested.
    """
    out, kind, tm = {}, None, None
    for l in dat.read_text().splitlines():
        h = re.match(r"\s*(" + _KINDS + r").*time\s+([0-9.E+-]+)", l)
        if h:
            kind, tm = h.group(1), float(h.group(2))
            out.setdefault(tm, {})
            continue
        p = l.split()
        if not (kind and p and p[0].isdigit()):
            continue
        e = int(p[0])
        if elems is not None and e not in elems:
            continue
        d = out[tm].setdefault(e, {})
        if kind == "stresses" and len(p) >= 8:
            d.setdefault("S", []).append([float(x) for x in p[2:8]])
        elif kind == "mechanical strains" and len(p) >= 8:
            d.setdefault("ME", []).append([float(x) for x in p[2:8]])
        elif kind == "strains" and len(p) >= 8:
            d.setdefault("E", []).append([float(x) for x in p[2:8]])
        elif kind == "equivalent plastic strain" and len(p) >= 3:
            d.setdefault("P", []).append(float(p[2]))
        elif kind == "volume" and len(p) >= 2:
            d["V"] = float(p[-1])
    for tm, per in out.items():
        for e, d in per.items():
            for k in ("S", "E", "ME"):
                if k in d:
                    d[k] = list(np.mean(np.array(d[k]), axis=0))
            if "P" in d:
                d["P"] = float(np.mean(d["P"]))
    return out


def temperature_from_fields(Etot, ME, t_zero_c: float, alpha: float = CTE_SAC305) -> float:
    """Recover the element temperature from the solver's OWN thermal strain.

    CalculiX defines ME = E - eps_thermal with eps_thermal = alpha*(T - T_zero)*I, so
    tr(E - ME) = 3*alpha*(T - T_zero). Both tensors come from the same output block, so
    this temperature cannot be aliased against the fields it is used with -- which is the
    whole point of DEFECT #46.
    """
    tr = (Etot[0] - ME[0]) + (Etot[1] - ME[1]) + (Etot[2] - ME[2])
    return t_zero_c + tr / (3.0 * alpha)


def elastic_strain(S, T_c):
    E, nu = sm.E_of_T(T_c), NU
    return np.array([(S[0] - nu * (S[1] + S[2])) / E, (S[1] - nu * (S[0] + S[2])) / E,
                     (S[2] - nu * (S[0] + S[1])) / E,
                     (1 + nu) * S[3] / E, (1 + nu) * S[4] / E, (1 + nu) * S[5] / E])


def ddot(S, dE):
    """sigma : d(eps) in the TENSOR shear convention -> factor 2 on the off-diagonals."""
    return float(S[0] * dE[0] + S[1] * dE[1] + S[2] * dE[2]
                 + 2.0 * (S[3] * dE[3] + S[4] * dE[4] + S[5] * dE[5]))


def cycle_quantities_me(data, vols, t0, t1, t_zero_c: float, temps_nt=None):
    """Volume-averaged per-cycle quantities on (t0, t1] by all three routes.

    Returns None if no element carries a full (S, E, ME, P) record -- the caller must then
    fall back, never silently report a partial answer.
    """
    ser = {}
    for t in sorted(data):
        for e, d in data[t].items():
            if all(k in d for k in ("S", "E", "ME", "P")):
                ser.setdefault(e, []).append((t, d["S"], d["E"], d["ME"], d["P"]))
    ser = {e: v for e, v in ser.items() if len(v) > 8}
    if not ser:
        return None
    acc = {k: 0.0 for k in ("w_prod", "w_me_nt", "w_me_self", "dpeeq", "rng",
                            "vol_resid_me", "vol_resid_prod", "t_err_max")}
    den = 0.0
    for e, rows in ser.items():
        w = [r for r in rows if t0 - 1e-9 < r[0] <= t1 + 1e-9]
        if len(w) < 3:
            continue
        v = vols.get(e, 1.0)
        den += v
        inel_prod, inel_nt, inel_self, Ss = [], [], [], []
        for (t, S, Et, Me, P) in w:
            S = np.array(S); Et = np.array(Et); Me = np.array(Me)
            t_self = temperature_from_fields(Et, Me, t_zero_c)
            t_nt = (temps_nt or {}).get(t, t_self)
            acc["t_err_max"] = max(acc["t_err_max"], abs(t_nt - t_self))
            th_prod = CTE_SAC305 * (t_nt - t_zero_c)
            inel_prod.append(Et - elastic_strain(S, t_nt)
                             - np.array([th_prod, th_prod, th_prod, 0., 0., 0.]))
            inel_nt.append(Me - elastic_strain(S, t_nt))
            inel_self.append(Me - elastic_strain(S, t_self))
            Ss.append(S)
        for key, series in (("w_prod", inel_prod), ("w_me_nt", inel_nt),
                            ("w_me_self", inel_self)):
            wk = 0.0
            for k in range(1, len(w)):
                wk += ddot(0.5 * (Ss[k - 1] + Ss[k]), series[k] - series[k - 1])
            acc[key] += wk * v
        # isochoric residual: inelastic flow is volume preserving, so |tr(eps_in)| relative
        # to the equivalent strain is a direct, assumption-free quality measure
        def resid(series):
            num = max(abs(float(s[0] + s[1] + s[2])) for s in series)
            dem = max(eq_strain(list(s)) for s in series) or 1.0
            return num / dem
        acc["vol_resid_me"] += resid(inel_self) * v
        acc["vol_resid_prod"] += resid(inel_prod) * v
        acc["dpeeq"] += (w[-1][4] - w[0][4]) * v
        eqs = [eq_strain(list(s)) for s in inel_self]
        acc["rng"] += (max(eqs) - min(eqs)) * v
    if not den:
        return None
    out = {k: (val / den if k != "t_err_max" else val) for k, val in acc.items()}
    out["n_elements"] = len(ser)
    return out


def build_deck(model: str, arch: str, profile, tight: bool = True) -> tuple[Path, list, float, dict]:
    a = RP.ARCH[arch]
    du, tmax = a["du"], a["t_hot"]
    tmin = RP.T_OFF if profile is None else profile[0]
    if profile is not None:
        tmax = profile[1]
    prof = "BASE" if profile is None else f"{tmin:g}_{tmax:g}"
    win = (f"_w{RLR.ANAND_WINDOW['lo']:g}_{RLR.ANAND_WINDOW['hi']:g}"
           if model.startswith("M2_ANAND") else "")
    tag = f"ME_{model}{win}_{arch}_{prof}"
    m = build_joint_graded(6, 6)
    cyc, ends, t = [], [], 0.0
    for k in range(RP.N_CYC):
        cyc.append((f"c{k}on", tmax, du / 1000.0, RP.DWELL)); t += RP.DWELL
        cyc.append((f"c{k}off", tmin, 0.0, RP.DWELL)); t += RP.DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    # M2_ANAND's card depends on its reduction window, so it comes from replay_lr, which
    # owns that window. Every other model is a plain Norton card from replay.
    card = RLR.material(model) if model.startswith("M2_ANAND") else RP.material(model)
    write_inp(m, p, card, cyc, t_ref_c=tmin, cetol=5e-2, procedure="VISCO")
    s = p.read_text()
    s = re.sub(r"\*VISCO, CETOL=[0-9.e-]+", "*VISCO, CETOL=0.05", s)
    start = (RP.TIGHT_START if tight else RP.LOOSE_START) % RP.DWELL
    s = re.sub(r"^[0-9.e-]+, %g, [0-9.e-]+, [0-9.e-]+$" % RP.DWELL, start, s, flags=re.M)
    # THE CHANGE: ME is requested alongside S and E, in the same block, for the same set.
    s = s.replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                  "*EL PRINT, ELSET=ESYED\nPEEQ, EVOL, S, E, ME")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E", "*NODE PRINT, NSET=NBOT\nNT")
    ids = m.sets["ESYED"]
    blk = ["*ELSET, ELSET=ESYED"] + [", ".join(map(str, ids[i:i + 8]))
                                     for i in range(0, len(ids), 8)]
    s = s.replace("*SOLID SECTION", "\n".join(blk) + "\n*SOLID SECTION", 1)
    p.write_text(s)
    return p, ends, tmin, {"ids": set(ids), "tag": tag, "du": du,
                           "t_max": tmax, "t_min": tmin, "profile": prof}


def run_case(model: str, arch: str, profile=None) -> dict:
    p, ends, tmin, meta = build_deck(model, arch, profile)
    t0 = time.time()
    run_ccx(p, threads=8)
    wall = time.time() - t0
    d = p.with_suffix(".dat")
    base = {"model": model, "arch": arch, "profile": meta["profile"], "wall_s": wall,
            "du_um": meta["du"], "T_max_C": meta["t_max"], "T_min_C": meta["t_min"]}
    if not (d.is_file() and d.stat().st_size > 5000):
        return {**base, "status": "SOLVER FAILED"}
    data = parse_tensors_me(d, meta["ids"])
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    te = ends[RP.STAB - 1]
    q = cycle_quantities_me(data, vols, te - 2 * RP.DWELL, te, tmin, parse_temperature(d))
    if not q:
        return {**base, "status": "NO ME DATA"}
    # the production number, computed by the production functions, for a like-for-like check
    ser = per_element_series(data, vols, parse_temperature(d))
    qp = cycle_quantities(ser, vols, te - 2 * RP.DWELL, te)
    return {**base, "status": "OK",
            "W_production_MJ_per_m3": qp["inelastic_work_MJ_per_m3"] if qp else float("nan"),
            "W_me_nt_MJ_per_m3": q["w_me_nt"], "W_me_self_MJ_per_m3": q["w_me_self"],
            "W_prod_recomputed_MJ_per_m3": q["w_prod"],
            "d_peeq_per_cycle": q["dpeeq"],
            "range_eq_inelastic": q["rng"],
            "isochoric_residual_ME": q["vol_resid_me"],
            "isochoric_residual_python": q["vol_resid_prod"],
            "max_T_alias_K": q["t_err_max"],
            "me_over_production": (q["w_me_self"] / qp["inelastic_work_MJ_per_m3"]
                                   if qp and qp["inelastic_work_MJ_per_m3"] else float("nan")),
            "n_elements": q["n_elements"]}


def main() -> int:
    only = sys.argv[1:] or None
    cases = [(m, a, None) for m in ("M1", "M0_COARSE", "M1_NLO", "M1_NHI", "M2_ANAND")
             for a in ("Z1", "Z2")]
    if only:
        cases = [c for c in cases if c[0] in only]
    rows = []
    for mdl, arch, prof in cases:
        r = run_case(mdl, arch, prof)
        rows.append(r)
        print(f"{mdl:10s} {arch} {r['status']:12s} "
              f"W_prod={r.get('W_production_MJ_per_m3', float('nan')):.6f} "
              f"W_ME={r.get('W_me_self_MJ_per_m3', float('nan')):.6f} "
              f"ratio={r.get('me_over_production', float('nan')):.4f} "
              f"iso_ME={r.get('isochoric_residual_ME', float('nan')):.2e} "
              f"iso_py={r.get('isochoric_residual_python', float('nan')):.2e}", flush=True)
    keys = sorted({k for r in rows for k in r})
    prior = OUT / "me_energy_reconstruction.csv"
    if prior.is_file() and only:
        import csv as _csv
        old_rows = list(_csv.DictReader(prior.open()))
        seen = {(r["model"], r["arch"]) for r in rows}
        rows = [r for r in old_rows if (r["model"], r["arch"]) not in seen] + rows
        keys = sorted({k for r in rows for k in r})
    with open(OUT / "me_energy_reconstruction.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT/'me_energy_reconstruction.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
