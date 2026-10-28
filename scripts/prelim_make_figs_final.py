"""Final-lineage presentation figures, every value read from research/final_closure."""
from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

R = Path(__file__).resolve().parents[1]
D = R / "research" / "final_closure"
FIG = R / "presentation" / "prelim_hvr" / "figs"
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 15, "axes.labelsize": 16, "axes.titlesize": 17,
                     "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 13,
                     "svg.fonttype": "none", "axes.spines.top": False,
                     "axes.spines.right": False})
C = {"Z1": "#1f6feb", "Z2": "#d1442f", "ok": "#1a7f37", "warn": "#bf8700",
     "open": "#cf222e", "hist": "#8c959f", "acc": "#6639ba"}
SCEN = ("HV_S0", "HV_S1", "HV_S2")


def J(n):
    f = D / n
    return json.loads(f.read_text()) if f.exists() else None


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)
    print("  ", name)


def etm(a, s):
    """Production-mesh ETM case (final_closure_physical_etm.case_path)."""
    import sys
    sys.path.insert(0, str(R / "scripts"))
    import final_closure_physical_etm as E
    f = E.case_path(a, s)
    return json.loads(f.read_text()) if f.exists() else None


def fig_ledger():
    groups = [("HS GaN", ("P_conv_hs",)), ("LS GaN", ("P_conv_ls",)),
              ("inductor DCR", ("P_conv_inductor_dcr",)), ("cap ESR", ("P_conv_cap_esr",)),
              ("intra-VR", ("P_intraVR_metal", "P_intraVR_vertical")),
              ("pkg HV RDL", ("P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return")),
              ("BGA + TSV + pads", ("P_BGA_supply", "P_BGA_return", "P_TSV_VDD",
                                    "P_TSV_GND", "P_pad_VDD", "P_pad_GND"))]
    cols = ["#24292f", "#57606a", "#8250df", "#bf8700", "#1a7f37", "#d1442f", "#1f6feb"]
    fig, ax = plt.subplots(figsize=(12.5, 3.9))
    for yi, a in enumerate(("Z2", "Z1")):
        r = etm(a, "HV_S0")
        t = {x["term"]: x["P_w"] for x in r["ledger_rows"]}
        left = 0.0
        for (lab, keys), c in zip(groups, cols):
            v = sum(t.get(k, 0.0) for k in keys)
            ax.barh(yi, v, left=left, color=c, height=0.55, label=lab if yi == 0 else None)
            if v > 4:
                ax.text(left + v / 2, yi, f"{v:.1f}", ha="center", va="center",
                        color="white", fontsize=12)
            left += v
        ax.text(left + 1.5, yi, f"{left:.2f} W", va="center", fontsize=14,
                fontweight="bold", color=C[a])
    ax.set_yticks([0, 1], ["Z2 backside", "Z1 embedded"])
    ax.set_xlabel("electrical loss at the converged E–T state, HV-S0 (W)")
    ax.set_xlim(0, 175)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.32))
    save(fig, "final_ledger.svg")


def fig_scenarios():
    keys = [("P_loss_w", "electrical loss (W)"), ("T_max_C", "peak temperature (°C)"),
            ("die_warpage_pv_um", "die warpage p-v (µm)"),
            ("du_c_um", "critical-joint driver Δu (µm)")]
    fin = J("final_results.json")
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.4))
    x = np.arange(3)
    for ax, (k, lab) in zip(axes, keys):
        for i, a in enumerate(("Z1", "Z2")):
            v = [next(f[k] for f in fin if f["arch"] == a and f["scenario"] == s)
                 for s in SCEN]
            ax.bar(x + (i - 0.5) * 0.38, v, 0.38, color=C[a], label=a)
        ax.set_xticks(x, ["S0", "S1", "S2"])
        ax.set_title(lab, fontsize=14)
        ax.grid(axis="y", alpha=.25)
    axes[0].legend(frameon=False)
    fig.suptitle("Physical lineage, per named 48 V scenario (HV-S0/S1/S2 are not a bracket)",
                 fontsize=14, y=1.03)
    save(fig, "final_scenarios.svg")


def fig_et():
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    for a in ("Z1", "Z2"):
        h = etm(a, "HV_S0")["et_history"]
        it = [x["iter"] for x in h]
        ax[0].plot(it, [x["T_max_C"] for x in h], "o-", color=C[a], lw=2.2, label=a)
        ax[1].semilogy(it, [max(x["max_dT_K"], 1e-4) for x in h], "o-", color=C[a], lw=2.2)
    ax[0].set_xlabel("E–T iteration"); ax[0].set_ylabel("T_max (°C)"); ax[0].legend(frameon=False)
    ax[1].axhline(0.25, color=C["open"], ls="--"); ax[1].text(0.1, 0.3, "declared tolerance 0.25 K",
                                                             color=C["open"], fontsize=12)
    ax[1].set_xlabel("E–T iteration"); ax[1].set_ylabel("max |ΔT| between iterations (K)")
    for a_ in ax:
        a_.grid(alpha=.25)
    save(fig, "final_et_convergence.svg")


def fig_joint_map():
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 5.6))
    vmax = max(etm(a, "HV_S0")["mechanics"]["joint_search"]["critical"]["du_um"]
               for a in ("Z1", "Z2"))
    for k, a in enumerate(("Z1", "Z2")):
        js = etm(a, "HV_S0")["mechanics"]["joint_search"]
        xy = np.array([[r["x_mm"], r["y_mm"]] for r in js["ranked"]])
        du = np.array([r["du_um"] for r in js["ranked"]])
        sc = ax[k].scatter(xy[:, 0], xy[:, 1], c=du, s=10, cmap="magma_r", vmin=0, vmax=vmax)
        c = js["critical"]
        ax[k].plot(c["x_mm"], c["y_mm"], marker="o", ms=16, mfc="none", mec=C["open"], mew=2.5)
        ax[k].set_title(f"{a}: {js['n_sites']} sites, critical Δu = {c['du_um']:.2f} µm")
        ax[k].set_aspect("equal"); ax[k].set_xlabel("x (mm)")
    ax[0].set_ylabel("y (mm)")
    fig.colorbar(sc, ax=ax, label="in-plane joint driver Δu (µm)", shrink=0.85)
    fig.savefig(FIG / "final_joint_map.svg", bbox_inches="tight"); plt.close(fig)
    print("   final_joint_map.svg")


def fig_count():
    rows = list(csv.DictReader((D / "bga_count_screen.csv").open()))
    pn = J("package_network.json")
    fig, ax = plt.subplots(figsize=(12, 4.6))
    for a in ("Z1", "Z2"):
        sub = sorted([r for r in rows if r["arch"] == a], key=lambda r: int(r["n_per_rail"]))
        ax.plot([int(r["n_per_rail"]) for r in sub],
                [float(r["i_ball_max_A__HV_S0"]) for r in sub], "-", color=C[a], lw=2, label=a)
    ax.axhline(1.5, color=C["open"], lw=2)
    ax.text(200, 1.62, "1.5 A ENGINEERING CRITERION — not a lifetime limit",
            color=C["open"], fontsize=12, ha="right")
    ax.axvline(pn["matched_count"], color=C["acc"], ls="--")
    ax.text(pn["matched_count"] + 3, 6, f"matched count\nN = {pn['matched_count']}/rail",
            color=C["acc"], fontsize=12)
    ax.set_yscale("log"); ax.set_xlim(0, 250)
    ax.set_xlabel("BGA balls per rail"); ax.set_ylabel("solved peak ball current, HV-S0 (A)")
    ax.set_title("Production model: exhaustive even counts, traced VIN pads, refined grid")
    ax.legend(frameon=False); ax.grid(alpha=.25, which="both")
    save(fig, "final_count_closure.svg")


SHORT = {"tsv_bulk": "TSV ρL/A", "tsv_tile_kz": "TSV-field k_z", "tsv_tile_kx": "TSV-field k_xy",
         "rdl_tier_kx": "RDL tier k_x", "rdl_tier_kz": "RDL tier k_z",
         "pkg_rdl_Z1": "pkg RDL Z1", "pkg_rdl_Z2": "pkg RDL Z2",
         "thermal_column_aedt_Z1": "unit cell, AEDT, Z1",
         "thermal_column_aedt_Z2": "unit cell, AEDT, Z2",
         "thermal_column_moose_Z1": "unit cell, MOOSE, Z1",
         "thermal_column_moose_Z2": "unit cell, MOOSE, Z2",
         "mech_bilayer_aedt": "bilayer, AEDT"}


def fig_acc_speed():
    acc = J("accuracy_speed_matrix.json")
    pts = [r for r in acc["rows"] if r.get("status") == "EXECUTED"
           and isinstance(r.get("error"), (int, float)) and isinstance(r.get("speedup"), (int, float))]
    fe = [r for r in pts if r["speedup"] < 100]
    cf = [r for r in pts if r["speedup"] >= 100]
    fig, ax = plt.subplots(1, 2, figsize=(13.5, 5.2), gridspec_kw={"width_ratios": [1.15, 1]})
    for a_, rows, title in ((ax[0], fe, "FE against FE (solver-to-solver)"),
                            (ax[1], cf, "closed form against FE")):
        rows = sorted(rows, key=lambda r: r["speedup"])
        for k, r in enumerate(rows):
            c = C["acc"] if "MOOSE" in r["reference_tool"] else C["Z1"]
            x, y = r["speedup"], 100 * abs(r["error"])
            a_.scatter(x, y, s=120, color=c, zorder=3)
            a_.annotate(SHORT.get(r["stage"], r["stage"]), (x, y), textcoords="offset points",
                        xytext=(8, 10 if k % 2 == 0 else -16), fontsize=11)
        a_.set_title(title)
        a_.grid(alpha=.25, which="both")
    ax[0].set_xlim(0, 1.25 * max(r["speedup"] for r in fe))
    ax[0].set_ylim(0, 1.6 * max(100 * abs(r["error"]) for r in fe))
    ax[0].set_ylabel("|error| vs matched reference (%)")
    ax[0].set_xlabel("runtime ratio, reference / production (×)")
    ax[1].set_xscale("log")
    ax[1].set_ylim(0, 1.25 * max(100 * abs(r["error"]) for r in cf))
    ax[1].set_xlabel("runtime ratio, reference / production (×, log)")
    ax[0].scatter([], [], color=C["Z1"], label="AEDT 2026 R1 Mechanical (commercial FEM)")
    ax[0].scatter([], [], color=C["acc"], label="MOOSE (open-source FEM)")
    ax[0].legend(frameon=False, loc="upper right", fontsize=11)
    save(fig, "final_accuracy_speed.svg")


def fig_runtime():
    r1 = etm("Z1", "HV_S0"); r2 = etm("Z2", "HV_S0")
    loc = J("local_solder_HV_S0.json") or {"cases": {}}
    items = []
    for a, r in (("Z1", r1), ("Z2", r2)):
        th = [h["wall_s"] for h in r["et_history"]]
        items.append((f"{a} thermal FE, per E–T iteration (median)", float(np.median(th))))
        items.append((f"{a} E–T fixed point, total ({len(th)} iterations)", r["et_wall_s"]))
        items.append((f"{a} global thermoelastic FE", r["mechanics"]["wall_s"]))
        lr = loc["cases"].get(a, {}).get("response") or {}
        if lr.get("wall_s"):
            items.append((f"{a} local nonlinear solder", lr["wall_s"]))
    items = [(k, v) for k, v in items if v and np.isfinite(v)]
    fig, ax = plt.subplots(figsize=(12.5, 5.0))
    lab = [k for k, _ in items]; val = [v for _, v in items]
    b = ax.barh(lab, val, color=[C["Z1"] if k.startswith("Z1") else C["Z2"] for k in lab], height=.6)
    for bb, v in zip(b, val):
        ax.text(v * 1.05, bb.get_y() + bb.get_height() / 2, f"{v:.0f} s", va="center", fontsize=12)
    ax.set_xscale("log"); ax.set_xlabel("measured wall time (s, log)")
    ax.set_title(f"CURRENT physical lineage runtime — thermal CalculiX {r1['threads']} threads; "
                 "structural iterative solver single-threaded")
    ax.grid(axis="x", alpha=.25, which="both")
    save(fig, "final_runtime.svg")


def fig_cutout_final():
    pn = J("package_network.json")
    c = pn["controlled"]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    vals = [c["delta_R_cutout_ohm"] * 1e3, c["delta_R_placement_ohm"] * 1e3]
    b = ax.barh(["ΔR cutout\n(central sites removed)", "ΔR placement\n(same sites, opposite rule)"],
                vals, color=[C["Z2"], C["acc"]], height=.55)
    for bb, v in zip(b, vals):
        ax.text(max(v, 0) + max(abs(x) for x in vals) * .02, bb.get_y() + bb.get_height() / 2,
                f"{v:+.4f} mΩ", va="center", fontsize=15)
    ax.axvline(0, color="k", lw=1)
    ax.set_xlabel("change in loop resistance (mΩ), matched N = %d/rail" % pn["matched_count"])
    ax.set_title("Controlled experiment on the production network")
    ax.grid(axis="x", alpha=.25)
    save(fig, "final_cutout.svg")


if __name__ == "__main__":
    # every figure is required: a missing artifact must stop the rebuild, not be skipped
    for fn in (fig_ledger, fig_scenarios, fig_et, fig_joint_map, fig_count, fig_acc_speed,
               fig_runtime, fig_cutout_final):
        fn()
