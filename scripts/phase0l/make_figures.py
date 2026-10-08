#!/usr/bin/env python3
"""Phase-0L figures FIG-0L-A .. FIG-0L-H (brief Part XVII)."""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0l"
for d in ("phase0i", "phase0l"):
    sys.path.insert(0, str(R / "scripts" / d))
import solder_model as sm                                                   # noqa: E402
import candidate_laws as cl                                                 # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .3,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
C = {"z1": "#1565c0", "z2": "#1b5e20", "z4": "#6a1b9a", "grey": "#9e9e9e", "bad": "#c62828",
     "warn": "#ef6c00", "ok": "#2e7d32", "ink": "#37474f", "old": "#8d6e63"}
T_LO, T_HI, S_LO, S_HI = 45.0, 150.0, 7.51, 15.92
rows = lambda p: list(csv.DictReader(open(OUT / p)))
F = lambda r, k: float(r[k])


def fig_A():
    """Solver output versus the candidate analytic laws."""
    pr = [r for r in rows("calculix_creep_probe.csv") if r["test"] in ("B", "A_zero")]
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.8))
    ax = axes[0]
    for test, mk, lab in (("A_zero", "o", "no yield surface"), ("B", "s", "with *PLASTIC card")):
        sub = [r for r in pr if r["test"] == test and F(r, "rate_meas_1_per_s") > 1e-18]
        if not sub:
            continue
        ax.loglog([F(r, "rate_H1") for r in sub], [F(r, "rate_meas_1_per_s") for r in sub],
                  mk, ms=3.5, alpha=.55, label=f"vs  A·σ$^n$   ({lab})",
                  color=C["bad"] if test == "B" else C["ok"])
    sub = [r for r in pr if r["test"] == "B" and F(r, "rate_meas_1_per_s") > 1e-18]
    ax.loglog([F(r, "rate_H3") for r in sub], [F(r, "rate_meas_1_per_s") for r in sub],
              "^", ms=3.5, alpha=.7, color=C["z1"], label="vs  A·(σ−σ$_y$)$^n$  (with *PLASTIC)")
    lim = [1e-20, 1e1]
    ax.plot(lim, lim, "-", color=C["ink"], lw=1, zorder=0, label="1:1")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("predicted rate (1/s)"); ax.set_ylabel("CalculiX measured rate (1/s)")
    ax.set_title("A. solver output vs candidate laws\n864 + 1344 increments", fontsize=9)
    ax.legend(fontsize=7, loc="upper left")

    ax = axes[1]
    for test, col, lab in (("B", C["bad"], "with *PLASTIC"), ("A_zero", C["ok"], "σ$_y$=0")):
        for h, mk in (("ratio_H1", "o"), ("ratio_H3", "^")):
            sub = [r for r in pr if r["test"] == test and F(r, "rate_meas_1_per_s") > 1e-18
                   and r[h] not in ("", "inf", "nan") and F(r, h) > 0]
            if not sub:
                continue
            if test == "A_zero" and h == "ratio_H3":
                continue
            ax.semilogy([F(r, "overstress_MPa") if test == "B" else F(r, "sigma_meas_MPa")
                         for r in sub], [F(r, h) for r in sub], mk, ms=3, alpha=.5, color=col,
                        label=f"{'A·σ$^n$' if h=='ratio_H1' else 'A·(σ−σ$_y$)$^n$'}  ({lab})")
    ax.axhline(1.0, color=C["ink"], lw=1)
    ax.set_xlabel("driving stress (MPa)")
    ax.set_ylabel("measured / predicted")
    ax.set_title("A (right). ratio to each candidate\n1.0 = law identified", fontsize=9)
    ax.legend(fontsize=7)
    fig.savefig(OUT / "FIG_0L_A_probe.png"); plt.close(fig)
    print("  FIG-0L-A")


def fig_B():
    """The 19 source points and the laws fitted to them."""
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.6))
    ax = axes[0]
    s = np.logspace(math.log10(5), math.log10(30), 120)
    for T, col in zip(sm.DATA_TEMPS, (C["z1"], C["ok"], C["warn"], C["bad"])):
        pts = [(x, e) for (t, x, e) in sm.CREEP_DATA if t == T]
        ax.loglog([p[0] for p in pts], [p[1] for p in pts], "o", ms=5, color=col,
                  label=f"{T:.0f} °C measured")
        f = sm.fit_norton_data(T)
        ax.loglog(s, f["A"] * s ** f["n"], "-", lw=1.3, color=col)
        ax.loglog(s, cl.garofalo_rate(s, T, "einn_bi"), "--", lw=1.0, color=col, alpha=.7)
    ax.axvspan(S_LO, S_HI, color=C["ok"], alpha=.12)
    ax.set_xlabel("applied stress (MPa)"); ax.set_ylabel("steady creep rate (1/s)")
    ax.set_title("B. the 19 source points\nsolid = Norton fit, dashed = Garofalo", fontsize=9)
    ax.legend(fontsize=7, loc="lower right")

    ax = axes[1]
    d = rows("original_19point_fit.csv")
    x = np.arange(len(d))
    ax.bar(x - .2, [F(r, "edot_measured_1_per_s") for r in d], .4, color=C["ok"], label="measured")
    fit = [F(r, "edot_fit_in_sigma_applied") for r in d]
    ax.bar(x + .2, fit, .4, color=C["z1"], label="Norton fit in σ$_{applied}$")
    sol = [F(r, "edot_solver_would_give") for r in d]
    ax.plot(x, [max(v, 1e-22) for v in sol], "v", ms=6, color=C["bad"],
            label="what the SOLVER returns")
    ax.set_yscale("log"); ax.set_ylim(1e-21, 1e-5)
    ax.set_xticks(x); ax.set_xticklabels([f"{F(r,'T_C'):.0f}" for r in d], fontsize=6)
    ax.set_xlabel("calibration point (grouped by temperature, °C)")
    ax.set_ylabel("rate (1/s)")
    ax.set_title("B (right). the card cannot reproduce its own data\n"
                 "16 of 19 return exactly zero", fontsize=9)
    ax.legend(fontsize=7, loc="lower left")
    fig.savefig(OUT / "FIG_0L_B_dataset.png"); plt.close(fig)
    print("  FIG-0L-B")


def fig_C():
    """Source-data coverage in temperature x stress, with package trajectories."""
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    ax.add_patch(Rectangle((T_LO, S_LO), T_HI - T_LO, S_HI - S_LO, fc=C["ok"], alpha=.32,
                           ec=C["ok"], lw=2, zorder=3))
    ax.annotate("CREEP CALIBRATION\n45–150 °C, 7.51–15.92 MPa\n19 points, "
                "alloy Sn3.9Ag0.6Cu", (97, 10.9), ha="center", fontsize=8, zorder=6,
                bbox=dict(fc="white", ec=C["ok"], lw=.7, alpha=.9, pad=1.6))
    ax.add_patch(Rectangle((-40, 0.5), 162, 60, fc=C["z1"], alpha=.10, ec=C["z1"],
                           lw=1.2, ls="--", zorder=1))
    ax.annotate("SAC305 Anand (Motalab, via Yuan Tables 7/9)\n−40…122 °C, tensile stress levels,\n"
                "strain rates 1e−3…1e−5 — no overlap in RATE", (-36, 4.2), fontsize=7.5,
                color=C["z1"], zorder=4, va="bottom")
    prof = [("Z1 / Z2 operating baseline", 25, 82.9, 20.5, 216.9, C["bad"], 1.9),
            ("experiment 45→125 °C", 45, 125, 20.7, 178.8, C["warn"], 1.35),
            ("experiment 110→150 °C", 110, 150, 19.9, 147.1, C["z4"], 1.05)]
    for lab, t0, t1, s0, s1, col, yf in prof:
        ax.add_patch(Rectangle((t0, s0), t1 - t0, s1 - s0, fc="none", ec=col, lw=2, zorder=5))
        ax.annotate(lab, (t0 + 1.5, s1 * yf), fontsize=8, color=col, zorder=7, va="center",
                    bbox=dict(fc="white", ec=col, lw=.7, alpha=.92, pad=1.6))
    ax.set_yscale("log"); ax.set_ylim(3, 900); ax.set_xlim(-45, 168)
    ax.set_xlabel("temperature (°C)"); ax.set_ylabel("von Mises stress (MPa)")
    ax.set_title("C. where the data is, and where the package goes", fontsize=10)
    fig.savefig(OUT / "FIG_0L_C_domain.png"); plt.close(fig)
    print("  FIG-0L-C")


def fig_F():
    """Candidate laws over 5-120 MPa."""
    fig, axes = plt.subplots(1, 4, figsize=(13.6, 3.9), sharey=True)
    s = np.logspace(math.log10(5), math.log10(120), 90)
    for ax, T in zip(axes, (45., 80., 115., 150.)):
        for (name, f), col, ls in zip(cl.MODELS.items(),
                                      (C["old"], C["z1"], C["warn"], C["z4"]),
                                      ("-", "-", "--", ":")):
            y = np.array([float(np.atleast_1d(f(x, T))[0]) for x in s])
            m = np.isfinite(y) & (y > 0)
            ax.loglog(s[m], y[m], ls, lw=1.5, color=col, label=name.replace("_", " "))
        pts = [(x, e) for (t, x, e) in sm.CREEP_DATA if t == T]
        ax.loglog([p[0] for p in pts], [p[1] for p in pts], "ko", ms=4, zorder=5,
                  label="source data")
        ax.axvspan(S_LO, S_HI, color=C["ok"], alpha=.15)
        ax.axvspan(54, 91, color=C["bad"], alpha=.10)
        ax.set_title(f"{T:.0f} °C", fontsize=9)
        ax.set_xlabel("σ (MPa)")
    axes[0].set_ylabel("steady rate (1/s)")
    axes[0].set_ylim(1e-12, 1e18)
    axes[0].legend(fontsize=6.5, loc="upper left")
    fig.suptitle("F. candidate constitutive laws over 5–120 MPa.  green = calibration window, "
                 "red = damage-weighted package stresses", fontsize=9.5)
    fig.savefig(OUT / "FIG_0L_F_candidates.png"); plt.close(fig)
    print("  FIG-0L-F")




def _history(tag):
    """Damage-weighted stress history from a replay .dat: (t, sigma_vm, PEEQ, dPEEQ) per step,
    volume-averaged over the Syed layers, weighted by the SOLVER'S OWN PEEQ increment."""
    import sys as _s
    for d in ("phase0ir", "phase0jr", "phase0i"):
        _s.path.insert(0, str(R / "scripts" / d))
    from decompose import parse_tensors                                     # noqa: E402
    from graded_joint import build_joint_graded                             # noqa: E402
    dat = OUT / "wd" / f"{tag}.dat"
    if not dat.is_file():
        return None
    ids = set(build_joint_graded(6, 6).sets["ESYED"])
    data = parse_tensors(dat, ids)
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ts = sorted(data)
    hist = []
    for t in ts:
        per = data[t]
        num_s = num_p = den = 0.0
        for e, dd in per.items():
            if "S" not in dd or "P" not in dd:
                continue
            v = vols.get(e, 1.0)
            # parse_tensors already averages over integration points: S is a 6-vector, P scalar
            sx, sy, sz, sxy, sxz, syz = dd["S"]
            vm = math.sqrt(0.5 * ((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2)
                           + 3.0 * (sxy**2 + sxz**2 + syz**2))
            num_s += vm * v; num_p += float(dd["P"]) * v; den += v
        if den:
            hist.append((t, num_s/den, num_p/den))
    out = []
    for (t0, s0, p0), (t1, s1, p1) in zip(hist, hist[1:]):
        out.append((t1, 0.5*(s0+s1), p1, max(p1 - p0, 0.0)))
    return out


def fig_D():
    """Actual package stress / overstress histories, Z1 vs Z2, incumbent vs corrected."""
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6), sharey=True)
    for ax, model, title in ((axes[0], "M0_FINE", "M0 incumbent (overstress law, yield active)"),
                             (axes[1], "M1", "M1 corrected (yield removed)")):
        for arch, col in (("Z1", C["z1"]), ("Z2", C["z2"])):
            h = _history(f"{model}_{arch}_BASE")
            if not h:
                continue
            t = np.array([r[0] for r in h]) / 3600.0
            s = np.array([r[1] for r in h])
            ax.plot(t, s, "-", lw=1.1, color=col, label=f"{arch}  sigma_vm")
        ax.axhspan(S_LO, S_HI, color=C["ok"], alpha=.30, zorder=0)
        ax.text(0.02, S_HI * 1.15, "creep calibration window", fontsize=7, color="#1b5e20")
        ax.set_xlabel("time (h)"); ax.set_title(title, fontsize=9)
        ax.legend(fontsize=7.5); ax.set_yscale("log")
    axes[0].set_ylabel("Syed-layer mean von Mises stress (MPa)")
    fig.suptitle("D. the stress the joint actually sees, against the window the creep law was "
                 "fitted in", fontsize=9.5)
    fig.savefig(OUT / "FIG_0L_D_histories.png"); plt.close(fig)
    print("  FIG-0L-D")


def fig_E():
    """Damage-weighted stress distribution versus the calibrated window."""
    fig, ax = plt.subplots(figsize=(10.4, 5.0))
    series = [("M0_FINE_Z1_BASE", "M0 incumbent, Z1", C["old"], "-"),
              ("M1_Z1_BASE", "M1 corrected, Z1", C["z1"], "-"),
              ("M1_Z2_BASE", "M1 corrected, Z2", C["z2"], "--")]
    txt = []
    for tag, lab, col, ls in series:
        h = _history(tag)
        if not h:
            continue
        s = np.array([r[1] for r in h]); w = np.array([r[3] for r in h])
        if w.sum() <= 0:
            continue
        o = np.argsort(s)
        s, w = s[o], w[o]
        cw = np.cumsum(w) / w.sum()
        ax.plot(s, 100 * cw, ls, lw=1.8, color=col, label=lab)
        med = float(np.interp(0.5, cw, s))
        frac_out = 100.0 * w[s > S_HI].sum() / w.sum()
        txt.append(f"{lab}: damage-weighted median {med:.0f} MPa, {frac_out:.1f} % of damage "
                   f"above {S_HI} MPa")
    ax.axvspan(S_LO, S_HI, color=C["ok"], alpha=.32, zorder=0)
    ax.text(S_HI * 1.1, 8, "creep calibration\nwindow 7.51-15.92 MPa", fontsize=8,
            color="#1b5e20")
    ax.set_xscale("log"); ax.set_xlabel("von Mises stress (MPa)")
    ax.set_ylabel("cumulative % of per-cycle damage below this stress")
    ax.set_ylim(0, 100); ax.grid(alpha=.3, which="both")
    ax.legend(fontsize=8, loc="upper left")
    ax.set_title("E. where the damage actually accumulates\n" + "\n".join(txt), fontsize=9)
    fig.savefig(OUT / "FIG_0L_E_damage_weighted.png"); plt.close(fig)
    print("  FIG-0L-E")


def fig_G():
    """Z2/Z1 under each admissible constitutive model."""
    cm = rows("common_mode_cancellation_test.csv")
    vd = rows("common_mode_verdict.csv")
    profs = ["BASE", "45_125", "110_150"]
    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.4), sharey=True)
    for ax, prof in zip(axes, profs):
        sub = sorted([r for r in cm if r["profile"] == prof], key=lambda r: r["model"])
        if not sub:
            ax.axis("off"); continue
        ms = [r["model"] for r in sub]
        x = np.arange(len(ms))
        for k, (key, lab, col) in enumerate((
                ("life_Syed2004_Eq14_strain", "Syed Eq.14 strain", C["z1"]),
                ("life_Schubert2003_strain", "Schubert strain", C["warn"]),
                ("life_Syed2004_Eq15_energy", "Syed Eq.15 energy", C["z2"]))):
            ax.bar(x + (k - 1) * 0.26, [F(r, key) for r in sub], 0.25, color=col,
                   label=lab if prof == "BASE" else None)
        ax.axhline(1.0, color=C["bad"], lw=1.4)
        v = [c for c in vd if c["profile"] == prof]
        if v:
            worst = max(v, key=lambda c: F(c, "spread_S"))
            ax.set_title(f"{prof}\nS = {F(worst,'spread_S'):.3f}  "
                         f"{worst['classification'].split()[0]}", fontsize=8.5)
        ax.set_xticks(x); ax.set_xticklabels([m.replace("_", "\n") for m in ms], fontsize=6.5)
    axes[0].set_ylabel("N$_{f,Z2}$ / N$_{f,Z1}$")
    axes[0].legend(fontsize=7, loc="lower right")
    axes[0].set_ylim(0.9, 1.5)
    fig.suptitle("G. Z2/Z1 relative life under every admissible constitutive model. "
                 "Red line = parity; above it Z2 outlives Z1.", fontsize=9.5)
    fig.savefig(OUT / "FIG_0L_G_ratios.png"); plt.close(fig)
    print("  FIG-0L-G")


def fig_H():
    """Experiment discrimination and sample size, before and after."""
    ex = rows("experiment_reaudit.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.4))
    ms = [r["model"] for r in ex]
    x = np.arange(len(ms))
    ax = axes[0]
    ax.bar(x, [F(r, "D_discrimination") for r in ex], .55, color=C["z1"])
    ax.axhline(1.4395, color=C["bad"], ls="--", lw=1.4, label="Phase 0K-R: D = 1.4395")
    ax.set_xticks(x); ax.set_xticklabels([m.replace("_", "\n") for m in ms], fontsize=7)
    ax.set_ylabel("D  (law discrimination)"); ax.legend(fontsize=7.5); ax.grid(alpha=.3, axis="y")
    ax.set_title("law-discrimination power is retained", fontsize=9)
    ax = axes[1]
    n = [int(r["n_required_per_cell"]) if r["n_required_per_cell"] else 0 for r in ex]
    ax.bar(x, n, .55, color=C["bad"])
    ax.axhline(34, color=C["ok"], ls="--", lw=1.6, label="Phase 0K-R design: 34 per cell")
    for xi, ni in zip(x, n):
        ax.text(xi, ni * 1.04, str(ni), ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([m.replace("_", "\n") for m in ms], fontsize=7)
    ax.set_ylabel("specimens per cell for Z = 3"); ax.set_yscale("log")
    ax.legend(fontsize=7.5); ax.grid(alpha=.3, axis="y", which="both")
    ax.set_title("but the ARCHITECTURE question does not", fontsize=9)
    fig.suptitle("H. experiment design before and after the constitutive correction",
                 fontsize=9.5)
    fig.savefig(OUT / "FIG_0L_H_experiment.png"); plt.close(fig)
    print("  FIG-0L-H")


if __name__ == "__main__":
    for w in (sys.argv[1:] or list("ABCDEFGH")):
        globals()[f"fig_{w}"]()
