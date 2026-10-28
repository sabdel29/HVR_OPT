"""Quantitative slide charts, rebuilt (brief Part 17). Every number is read from a
research/final_closure artifact at build time; nothing is typed in.

  s0_cards.svg                one card per observable, Z1 vs Z2 at HV-S0, with the
                              measured discretisation uncertainty and the verdict
  scenario_small_multiples.svg  one panel per observable across HV-S0/S1/S2, scenario
                              class marked, extrapolated and inadmissible points flagged
  accuracy_runtime_split.svg  (A) closed-form / homogenised models vs commercial FE,
                              (B) production FE vs reference FE -- never one axis
  local_convergence.svg       the declared local solder mesh family per case
  die_warpage_maps.png        the production structural solution itself: die-top
                              out-of-plane displacement, Z1 and Z2 on one colour scale

Conventions: hairline axes, no chart junk, units on every axis, the deck's Z1/Z2 colours
(validated for colour-vision deficiency), identity also carried by text labels.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
import numpy as np                                                      # noqa: E402

R = Path(__file__).resolve().parents[1]
FC = R / "research" / "final_closure"
FIG = R / "presentation" / "prelim_hvr" / "figs"
sys.path.insert(0, str(R / "scripts"))
import figstyle as S                                                    # noqa: E402

COL = {"Z1": S.Z1, "Z2": S.Z2}
OBS = (("P_loss_w", "Electrical loss", "W"), ("T_max_C", "Peak temperature", "°C"),
       ("die_warpage_pv_um", "Die warpage (peak-to-valley)", "µm"),
       ("du_c_um", "Critical-joint displacement driver", "µm"),
       ("d_eps_in_per_cycle", "Local inelastic strain per cycle", "–"))
SCEN = ("HV_S0", "HV_S1", "HV_S2")
SLAB = {"HV_S0": "HV-S0", "HV_S1": "HV-S1", "HV_S2": "HV-S2"}
FIELDS = Path(os.environ.get("HVR_FIELDS", Path.home() / "claude_scratch" / "hvr_work"
                             / "fields"))

plt.rcParams.update({
    "font.family": "Lato", "font.size": 13, "axes.titlesize": 14,
    "axes.titleweight": "bold", "axes.labelsize": 12.5, "axes.edgecolor": "#c3cad3",
    "axes.linewidth": 0.8, "axes.labelcolor": S.INK, "xtick.color": S.MUTED,
    "ytick.color": S.MUTED, "xtick.labelsize": 11.5, "ytick.labelsize": 11.5,
    "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "path",
    "figure.dpi": 100, "savefig.dpi": 150})


def J(n):
    f = FC / n
    return json.loads(f.read_text()) if f.exists() else None


def save(fig, name, src):
    fig.savefig(FIG / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    (FIG / (name.rsplit(".", 1)[0] + ".sources.json")).write_text(json.dumps(
        {"figure": name, "generator": "scripts/final_closure_slide_charts.py",
         "sources": src}, indent=1))


def _fmt(v, k):
    if v is None:
        return "n/a"
    if k == "d_eps_in_per_cycle":
        return f"{v * 1e3:.2f}×10⁻³"
    return f"{v:.1f}" if k in ("P_loss_w", "T_max_C", "die_warpage_pv_um") else f"{v:.2f}"


def _verdict_text(o, s):
    v = o["per_scenario"].get(s, "n/a")
    g, u = (o.get("relative_gap") or {}).get(s), (o.get("uncertainty_rel") or {}).get(s)
    if v.endswith("lower") and g is not None and u is not None:
        return v, f"gap {100 * g:.1f} % > 2U = {200 * u:.1f} %"
    if v == "unresolved" and g is not None and u is not None:
        return "no ranking", f"gap {100 * g:.1f} % ≤ 2U = {200 * u:.1f} %"
    return v, (o.get("reasons") or {}).get(s, "")


# ------------------------------------------------------------------- S0 cards
def s0_cards():
    fin, od = J("final_results.json"), J("ordering.json")
    if not (fin and od):
        return
    rows = {(r["arch"], r["scenario"]): r for r in fin}
    fig, axes = plt.subplots(1, 5, figsize=(17.5, 3.9))
    for ax, (k, name, unit) in zip(axes, OBS):
        o = od["orderings"][k]
        u = (o.get("uncertainty_rel") or {}).get("HV_S0") or 0.0
        vals = [rows[(a, "HV_S0")].get(k) for a in ("Z1", "Z2")]
        for i, (a, v) in enumerate(zip(("Z1", "Z2"), vals)):
            if v is None:
                continue
            y = 1 - i
            ax.barh(y, v, height=0.46, color=COL[a], zorder=2)
            ax.errorbar(v, y, xerr=u * v, color=S.INK, capsize=4, lw=1.2, zorder=3)
            ax.text(v * 1.0 + u * v, y, "  " + _fmt(v, k), va="center", ha="left",
                    fontsize=13, color=S.INK, fontweight="bold")
        ax.set_yticks([1, 0], ["Z1", "Z2"], fontsize=13)
        ax.set_ylim(-0.7, 1.7)
        m = max(v for v in vals if v is not None)
        ax.set_xlim(0, m * 1.55)
        ax.set_title(f"{name}\n({unit})" if unit != "–" else f"{name}\n(dimensionless)",
                     loc="left", fontsize=13.5)
        ax.xaxis.set_major_locator(plt.MaxNLocator(3))
        verdict, why = _verdict_text(o, "HV_S0")
        colr = S.OK if verdict.endswith("lower") else S.WARN
        ax.text(0.0, -0.33, verdict.upper(), transform=ax.transAxes, fontsize=12.5,
                fontweight="bold", color=colr)
        ax.text(0.0, -0.47, why, transform=ax.transAxes, fontsize=10.5, color=S.MUTED)
        if k == "d_eps_in_per_cycle":
            lv = rows[("Z1", "HV_S0")].get("local_mesh_level")
            ax.text(0.0, -0.60, f"local mesh {lv}; U = mesh + time + cycles",
                    transform=ax.transAxes, fontsize=10.5, color=S.MUTED)
    fig.suptitle("HV-S0 (headline scenario): Z1 vs Z2, with the measured discretisation "
                 "uncertainty (whiskers = ±U)", x=0.01, ha="left", fontsize=15,
                 fontweight="bold", y=1.07)
    fig.subplots_adjust(wspace=0.55)
    save(fig, "s0_cards.svg", ["final_results.json", "ordering.json"])


# ------------------------------------------------------- scenario small multiples
#: panel titles short enough not to run into the neighbouring panel
SHORT_T = {"die_warpage_pv_um": "Die warpage, peak-to-valley",
           "du_c_um": "Joint driver Δu", "d_eps_in_per_cycle": "Local inelastic Δε / cycle"}


def scenario_small_multiples():
    fin, od = J("final_results.json"), J("ordering.json")
    if not (fin and od):
        return
    rows = {(r["arch"], r["scenario"]): r for r in fin}
    sc = od["scenario_classes"]
    fig, axes = plt.subplots(1, 5, figsize=(18.5, 4.6))
    for ax, (k, name, unit) in zip(axes, OBS):
        o = od["orderings"][k]
        top = 0.0
        for j, s in enumerate(SCEN):
            u = (o.get("uncertainty_rel") or {}).get(s) or 0.0
            for i, a in enumerate(("Z1", "Z2")):
                r = rows.get((a, s)) or {}
                v = r.get(k)
                x = j + (-0.16 if a == "Z1" else 0.16)
                if v is None:
                    ax.text(x, 0.02, "×", ha="center", va="bottom", color=COL[a],
                            fontsize=16, transform=ax.get_xaxis_transform())
                    continue
                extrap = (k == "d_eps_in_per_cycle"
                          and r.get("T_joint_outside_norton_calibration"))
                if r.get("T_joint_at_or_above_solder_solidus"):
                    # an infeasibility result, not an operating point: pale, never ranked
                    ax.plot(x, v, "s", ms=8.5, mfc="none", mec=COL[a], mew=1.6, alpha=0.5,
                            zorder=3)
                    top = max(top, v)
                    continue
                ax.errorbar(x, v, yerr=u * v, fmt="o", ms=8.5, color=COL[a],
                            mfc="white" if extrap else COL[a], mew=2, capsize=3.5,
                            lw=1.2, zorder=3)
                top = max(top, v * (1 + u))
            verdict = o["per_scenario"].get(s, "n/a")
            short = {"Z1 lower": "Z1\nlower", "Z2 lower": "Z2\nlower",
                     "unresolved": "no\nranking", "not rankable": "not\nrankable"}.get(
                         verdict, verdict)
            ax.text(j, -0.31, short, ha="center", va="center", fontsize=10.5,
                    transform=ax.get_xaxis_transform(), linespacing=1.0,
                    color=S.OK if verdict.endswith("lower") else S.WARN, fontweight="bold")
        ax.set_xticks(range(3), [f"{SLAB[s]}\n{sc[s]['class'].split(' /')[0]}" for s in SCEN],
                      fontsize=10.5)
        ax.set_xlim(-0.6, 2.6)
        ax.set_ylim(0, top * 1.18)
        ax.set_title(f"{SHORT_T.get(k, name)}" + (f" ({unit})" if unit != "–" else ""),
                     loc="left", fontsize=12.5)
        ax.yaxis.set_major_locator(plt.MaxNLocator(4))
    h = [plt.Line2D([], [], marker="o", ls="", ms=8, color=COL[a], label=a)
         for a in ("Z1", "Z2")]
    h.append(plt.Line2D([], [], marker="o", ls="", ms=8, color=S.MUTED, mfc="white", mew=2,
                        label="local response EXTRAPOLATED (joint above the 125 °C "
                              "Norton calibration)"))
    h.append(plt.Line2D([], [], marker="s", ls="", ms=8, mfc="none", mec=S.MUTED, mew=1.6,
                        alpha=0.6, label="joint at/above the ~217 °C melting onset: "
                                         "infeasible, shown but not ranked"))
    h.append(plt.Line2D([], [], marker="x", ls="", ms=9, color=S.MUTED,
                        label="no local response (solder at/above the melting onset)"))
    fig.legend(handles=h, loc="upper left", bbox_to_anchor=(0.01, 0.0), ncol=3,
               frameon=False, fontsize=11.5)
    fig.suptitle("Scenario robustness: HV-S0 headline, HV-S1 sensitivity, HV-S2 stress / "
                 "inadmissible (whiskers = ±U; verdicts from ordering.json)", x=0.01,
                 ha="left", fontsize=15, fontweight="bold", y=1.04)
    fig.subplots_adjust(wspace=0.42, bottom=0.25)
    save(fig, "scenario_small_multiples.svg", ["final_results.json", "ordering.json"])


# ------------------------------------------------------------ accuracy / runtime
LABEL = {"tsv_bulk": "TSV field, bulk k", "tsv_tile_kz": "TSV tile k_z",
         "tsv_tile_kx": "TSV tile k_x", "rdl_tier_kx": "RDL tier k_x (grid laminate)",
         "rdl_tier_kz": "RDL tier k_z (series form)",
         "pkg_rdl_Z1": "Package 48 V RDL, Z1 (MOOSE)",
         "pkg_rdl_Z2": "Package 48 V RDL, Z2 (MOOSE)",
         "thermal_column_aedt_Z1": "Thermal unit cell, Z1 (AEDT)",
         "thermal_column_aedt_Z2": "Thermal unit cell, Z2 (AEDT)",
         "thermal_column_moose_Z1": "Thermal unit cell, Z1 (MOOSE)",
         "thermal_column_moose_Z2": "Thermal unit cell, Z2 (MOOSE)",
         "mech_bilayer_aedt": "Thermoelastic bilayer (AEDT)",
         "cooling_icepak": "Cold-plate correlation (Icepak CFD)"}


SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def sci(v):
    e = int(math.floor(math.log10(v)))
    return f"{v / 10 ** e:.1f}×10{str(e).translate(SUP)}"


def accuracy_runtime_split():
    acc = J("accuracy_speed_matrix.json")
    if not acc:
        return
    rows = [r for r in acc["rows"] if r.get("status") == "EXECUTED"
            and isinstance(r.get("error"), float) and r["stage"] in LABEL]
    A = [r for r in rows if r["stage"].startswith(("tsv_", "rdl_tier", "cooling_"))]
    B = [r for r in rows if r not in A]
    fig, ax = plt.subplots(2, 2, figsize=(15.5, 7.4),
                           gridspec_kw={"width_ratios": [1.15, 1], "hspace": 0.55,
                                        "wspace": 0.55})
    for row, grp, title, log in ((0, A, "A · Closed-form / reduced model vs commercial "
                                  "reference (same problem)", True),
                                 (1, B, "B · Production solver vs reference FE solver "
                                  "(same problem, same machine)", False)):
        names = [LABEL[r["stage"]] for r in grp][::-1]
        errs = [100 * r["error"] for r in grp][::-1]
        sp = [r.get("speedup") for r in grp][::-1]
        y = np.arange(len(grp))
        a = ax[row, 0]
        a.axvline(0, color="#c3cad3", lw=0.8)
        a.scatter(errs, y, s=60, color=S.INK, zorder=3)
        lim = max(2.0, max(abs(e) for e in errs) * 1.35)
        for yi, e in zip(y, errs):
            a.annotate(f"{e:+.2f} %", (e, yi), xytext=(9, 0), textcoords="offset points",
                       va="center", ha="left", fontsize=10.5, color=S.INK)
        a.set_yticks(y, names, fontsize=11)
        a.set_xlim(-lim, lim)
        a.set_ylim(-0.6, len(grp) - 0.4)
        a.set_xlabel("model error vs reference (%)")
        a.text(-0.62, 1.10, title, transform=a.transAxes, fontsize=13.5, fontweight="bold",
               ha="left", color=S.INK)
        b = ax[row, 1]
        vv = [s if isinstance(s, float) else np.nan for s in sp]
        b.barh(y, vv, height=0.45, color=S.ACCENT, left=0 if not log else None)
        if log:
            b.set_xscale("log")
            b.set_xlim(1, max(v for v in vv if v == v) * 30)
            for yi, v in zip(y, vv):
                if v == v:
                    b.text(v * 1.4, yi, sci(v) + "×", va="center", fontsize=10.5)
            b.set_xlabel("runtime ratio, reference / model (log scale)")
        else:
            b.axvline(1, color=S.MUTED, lw=1)
            b.text(1, len(grp) - 0.35, " equal runtime", color=S.MUTED, fontsize=10)
            b.set_xlim(0, max(v for v in vv if v == v) * 1.35)
            for yi, v in zip(y, vv):
                if v == v:
                    b.text(v, yi, f"  {v:.2f}×", va="center", fontsize=10.5)
            b.set_xlabel("runtime ratio, reference / production (>1: production faster)")
        b.set_yticks(y, [""] * len(y))
    fig.text(0.01, -0.02, "Timing: warm-up + 3 timed repeats, median wall time, 4 cores "
             "(AEDT limit); closed-form ratios compare an analytic evaluation with an FE "
             "solve and are shown on their own log axis. Source: "
             "research/final_closure/accuracy_speed_matrix.json", fontsize=10,
             color=S.MUTED)
    save(fig, "accuracy_runtime_split.svg", ["accuracy_speed_matrix.json"])


# --------------------------------------------------------------- local convergence
def local_convergence():
    lm, pol = J("local_mesh_study.json"), J("local_mesh_policy.json")
    if not (lm and pol):
        return
    cases = [f"{a}_{s}" for a, s in pol["cases"]]
    fig, axes = plt.subplots(1, len(cases), figsize=(16.5, 4.2), sharey=False)
    for ax, k in zip(axes, cases):
        c = lm["cases"].get(k) or {}
        lv = c.get("levels") or {}
        pts = sorted([(6.0 / r["n_xy"], r["d_peeq_per_cycle"], t) for t, r in lv.items()
                      if r.get("d_peeq_per_cycle")], reverse=True)
        arch = k.split("_")[0]
        if pts:
            h, v, t = zip(*pts)
            ax.plot(h, np.array(v) * 1e3, "-o", color=COL[arch], ms=8, lw=2)
            for hi, vi, ti in pts:
                ax.text(hi, vi * 1e3, f"  {ti}", fontsize=10.5, va="bottom", color=S.MUTED)
            if c.get("production_value") and c.get("U") is not None:
                pv = c["production_value"] * 1e3
                ph = 6.0 / LEVELS_NXY(pol, c["production_level"])
                ax.errorbar(ph, pv, yerr=c["U"] * pv, color=S.INK, capsize=5, lw=1.4,
                            zorder=4)
        failed = c.get("levels_failed") or []
        u = c.get("U")
        sub = (f"= mesh {100 * c['U_mesh']:.2f} + time {100 * c['U_time']:.2f} + cycles "
               f"{100 * c['U_cyc']:.2f} (%)" if u is not None else "U not quantified") + (
            f"; failed: {', '.join(failed)}" if failed else "")
        ax.set_title(f"{k.replace('_HV_', ' HV-')}: {c.get('status', '?')}"
                     + (f", U = {100 * u:.2f} %" if u is not None else "") + "\n",
                     loc="left", fontsize=12.5)
        ax.text(0.0, 1.015, sub, transform=ax.transAxes, fontsize=10.8, color=S.MUTED)
        if pts and c.get("production_value") and u is not None:
            lo = min(min(v), c["production_value"] * (1 - u)) * 1e3
            hi = max(max(v), c["production_value"] * (1 + u)) * 1e3
            pad = 0.06 * (hi - lo)
            ax.set_ylim(lo - pad, hi + pad)
        ax.set_xlabel("relative element size h (L0 = 1)")
        ax.invert_xaxis()
        ax.yaxis.set_major_locator(plt.MaxNLocator(4))
    axes[0].set_ylabel("inelastic Δε per cycle (×10⁻³)")
    fig.suptitle("Local solder joint: declared mesh family L0 → L3 at each production "
                 "critical joint (whisker = ±U at the production level)", x=0.01,
                 ha="left", fontsize=14.5, fontweight="bold", y=1.04)
    fig.subplots_adjust(wspace=0.35)
    save(fig, "local_convergence.svg", ["local_mesh_study.json", "local_mesh_policy.json"])


def LEVELS_NXY(pol, level):
    return pol["levels"][level]["n_xy"]


# --------------------------------------------------------------- die warpage maps
def _frd_nodes(frd):
    xyz = {}
    with open(frd) as fh:
        inblk = False
        for line in fh:
            if line.startswith("    2C"):
                inblk = True
                continue
            if inblk:
                if line.startswith(" -3"):
                    break
                if line.startswith(" -1"):
                    nid = int(line[3:13])
                    xyz[nid] = (float(line[13:25]), float(line[25:37]), float(line[37:49]))
    n = max(xyz)
    out = np.full((n + 1, 3), np.nan)
    for k, v in xyz.items():
        out[k] = v
    return out


def die_warpage_maps():
    fin, spec = J("final_results.json"), J("architecture_geometry.json")
    if not (fin and spec):
        return
    import final_closure_physical_etm  # noqa: F401  (sets the solver import paths)
    from etm import ccxio
    rows = {(r["arch"], r["scenario"]): r for r in fin}
    data, src = {}, {}
    for a in ("Z1", "Z2"):
        f = FIELDS / f"etm_{a}_HV_S0_r21" / "structural.frd"
        if not f.exists():
            return
        die = next(L for L in spec["architectures"][a]["layers"] if L["name"] == "die")
        z_top = die["z1_um"] / 1e3
        half = spec["architectures"][a]["die_mm"][0] / 2
        xyz = _frd_nodes(f)
        U = ccxio.read_frd(f)["DISP"]
        sel = np.where((np.abs(xyz[:, 2] - z_top) < 1e-6) & (np.abs(xyz[:, 0]) <= half + 1e-6)
                       & (np.abs(xyz[:, 1]) <= half + 1e-6))[0]
        w = U[sel, 2] * 1e3
        ref = rows[(a, "HV_S0")]["die_warpage_pv_um"]
        if abs((w.max() - w.min()) - ref) > 1e-6 * max(ref, 1.0):
            raise RuntimeError(f"{a}: field PV {w.max() - w.min():.6f} um differs from "
                               f"final_results {ref:.6f} um -- wrong field or surface")
        data[a] = (xyz[sel, 0], xyz[sel, 1], w - w.mean(), w.max() - w.min(), half)
        src[a] = {"frd": str(f), "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                  "n_nodes_die_top": int(len(sel)), "pv_um": float(w.max() - w.min()),
                  "final_results_die_warpage_pv_um": rows[(a, "HV_S0")]["die_warpage_pv_um"]}
    lim = max(np.abs(d[2]).max() for d in data.values())
    lim = 5.0 * math.ceil(lim / 5.0)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.6))
    for ax, a in zip(axes, ("Z1", "Z2")):
        x, y, wv, pv, half = data[a]
        tc = ax.tricontourf(x, y, wv, levels=np.linspace(-lim, lim, 21), cmap="RdBu_r")
        ax.set_aspect("equal")
        ax.set_xlim(-half, half)
        ax.set_ylim(-half, half)
        ax.set_title(f"{a}: peak-to-valley {pv:.1f} µm", loc="left", fontsize=14)
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
    cb = fig.colorbar(tc, ax=axes, shrink=0.85, pad=0.03,
                      ticks=np.arange(-lim, lim + 1e-9, 10.0))
    cb.set_label("die-top out-of-plane displacement minus its mean (µm)")
    fig.suptitle("Production thermoelastic solution, HV-S0: the die surface bows "
                 "(same colour scale for Z1 and Z2)", x=0.01, ha="left", fontsize=14.5,
                 fontweight="bold")
    save(fig, "die_warpage_maps.png", src)


# ------------------------------------------------------- E-T, joint map, sharing
def _case(a):
    import final_closure_physical_etm as E
    return json.loads(E.case_path(a, "HV_S0").read_text())


def et_convergence():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.3))
    import final_closure_physical_etm as E
    for a in ("Z1", "Z2"):
        h = _case(a)["et_history"]
        it = [x["iter"] for x in h]
        a1.plot(it, [x["T_max_C"] for x in h], "-o", color=COL[a], ms=7, lw=2, label=a)
        a2.semilogy(it, [x["max_dT_K"] for x in h], "-o", color=COL[a], ms=7, lw=2, label=a)
        a1.annotate(f"{h[-1]['T_max_C']:.2f} °C", (it[-1], h[-1]["T_max_C"]),
                    xytext=(8, 0), textcoords="offset points", va="center", fontsize=11)
    a2.axhline(E.ET_TOL_K, color=S.MUTED, lw=1)
    a2.text(0.02, E.ET_TOL_K * 1.25, f"declared tolerance {E.ET_TOL_K} K", fontsize=10.5,
            color=S.MUTED, transform=a2.get_yaxis_transform())
    for ax in (a1, a2):
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.set_xlabel("electrothermal iteration")
        ax.legend(frameon=False, loc="lower right" if ax is a1 else "upper right")
    a1.set_ylabel("peak temperature (°C)")
    a2.set_ylabel("largest temperature change\nbetween iterations (K)")
    a1.set_title("Peak temperature settles", loc="left")
    a2.set_title("Change falls below the declared tolerance", loc="left")
    fig.subplots_adjust(wspace=0.38)
    save(fig, "et_convergence.svg", ["etm_Z1_HV_S0_h1.1_r21.json", "etm_Z2_HV_S0_h1.1_r21.json"])


def joint_map():
    fig = plt.figure(figsize=(13.0, 5.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.045], wspace=0.28)
    axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    cax = fig.add_subplot(gs[0, 2])
    vmax = 0.0
    data = {}
    for a in ("Z1", "Z2"):
        js = _case(a)["mechanics"]["joint_search"]
        r = js["ranked"]
        data[a] = (np.array([[x["x_mm"], x["y_mm"], x["du_um"]] for x in r]), js)
        vmax = max(vmax, max(x["du_um"] for x in r))
    for ax, a in zip(axes, ("Z1", "Z2")):
        d, js = data[a]
        sc = ax.scatter(d[:, 0], d[:, 1], c=d[:, 2], cmap="magma_r", vmin=0, vmax=vmax, s=9)
        c = js["critical"]
        ax.scatter([c["x_mm"]], [c["y_mm"]], s=170, facecolors="none", edgecolors=S.INK, lw=1.8)
        ax.set_aspect("equal")
        ax.set_title(f"{a}: {js['n_sites']} legal sites\ncritical Δu = {c['du_um']:.2f} µm",
                     loc="left", fontsize=13)
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
    cb = fig.colorbar(sc, cax=cax)
    cb.set_label("in-plane joint displacement driver Δu (µm), HV-S0")
    save(fig, "joint_map.svg", ["etm_Z1_HV_S0_h1.1_r21.json", "etm_Z2_HV_S0_h1.1_r21.json"])


def ball_sharing():
    pn = J("package_network.json")
    if not pn:
        return
    fig, ax = plt.subplots(figsize=(12.5, 4.4))
    n = pn["matched_count"]
    for k, a in enumerate(("Z1", "Z2")):
        fr = np.sort(np.array(pn["convergence"][f"{a}_supply"]["i_ball_frac"]))[::-1]
        x = np.arange(len(fr)) + (k - 0.5) * 0.38
        ax.bar(x, 100 * fr, width=0.36, color=COL[a],
               label=f"{a} (solved): peak {100 * fr[0]:.1f} % = "
                     f"{fr[0] * len(fr):.2f}× the equal share")
    ax.axhline(100 / n, color=S.MUTED, lw=1.2)
    ax.text(n - 0.5, 100 / n * 1.06, f"equal sharing 1/{n} = {100 / n:.2f} %", ha="right",
            fontsize=10.5, color=S.MUTED)
    ax.set_xlabel(f"48 V supply ball, sorted by solved current ({n} matched balls per rail)")
    ax.set_ylabel("share of the rail current (%)")
    ax.set_title("A uniform load does not give uniform ball currents (voltage-fed network, "
                 "HV-S0)", loc="left")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "ball_sharing.svg", ["package_network.json"])


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (s0_cards, scenario_small_multiples, accuracy_runtime_split, local_convergence,
              die_warpage_maps, et_convergence, joint_map, ball_sharing):
        f()
        print("wrote", f.__name__)


if __name__ == "__main__":
    main()
