"""Derive every tool-evidence folder from the reference artifacts.

presentation/prelim_hvr/tool_evidence/<stage>/ gets, for each matched benchmark:
  01_geometry*.png   exported from the reference-tool session itself (AEDT folders), or
  04_field.png       rendered from the reference's own output file (MOOSE folders)
  05_comparison.png  production vs reference values, plotted from the artifact
  setup.json, runtime.json, result.json, README.md
Nothing here is typed by hand: a stage whose artifact is missing or unsolved is written
as such, and the top-level README's execution table is derived from the same artifacts.
"""
from __future__ import annotations

import glob
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
import numpy as np                                                  # noqa: E402

R = Path(__file__).resolve().parents[1]
FC = R / "research" / "final_closure"
EV = R / "presentation" / "prelim_hvr" / "tool_evidence"
AEDT = "Ansys Electronics Desktop 2026 R1 Mechanical"


def J(name):
    f = FC / name
    return json.loads(f.read_text()) if f.exists() else None


def dump(d, name, obj):
    (d / name).write_text(json.dumps(obj, indent=2, default=float) + "\n")


def comparison_png(d, title, labels, prod, ref, unit, prod_name, ref_name):
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    x = np.arange(len(labels))
    ax.bar(x - 0.18, prod, 0.36, label=prod_name, color="#2a6fbb")
    ax.bar(x + 0.18, ref, 0.36, label=ref_name, color="#d08a2c")
    for i, (p, r) in enumerate(zip(prod, ref)):
        ax.text(i, max(p, r) * 1.02, f"{100 * (p - r) / r:+.2f} %", ha="center", fontsize=9)
    ax.set_xticks(x, labels)
    ax.set_ylabel(unit)
    ax.set_ylim(0, max(max(prod), max(ref)) * 1.18)
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(d / "05_comparison.png", dpi=150)
    plt.close(fig)


def _exodus(path, var):
    """Nodal field `var` at the LAST stored step. A steady MOOSE solve writes the initial
    condition as step 0, so reading the default step renders an all-zero field."""
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    r = vtk.vtkExodusIIReader()
    r.SetFileName(str(path))
    r.UpdateInformation()
    r.SetAllArrayStatus(vtk.vtkExodusIIReader.NODAL, 1)
    r.SetTimeStep(r.GetNumberOfTimeSteps() - 1)
    r.Update()
    it = r.GetOutput().NewIterator()
    it.InitTraversal()
    P, V = [], []
    while not it.IsDoneWithTraversal():
        ds = it.GetCurrentDataObject()
        arr = ds.GetPointData().GetArray(var)
        if arr is not None:
            P.append(vtk_to_numpy(ds.GetPoints().GetData()))
            V.append(vtk_to_numpy(arr))
        it.GoToNextItem()
    P, V = np.vstack(P), np.concatenate(V)
    if not np.ptp(V) > 0:
        raise RuntimeError(f"{path}: field {var} is uniform -- not a solved state")
    return P, V


def field_png_sheet(d, exo, title):
    P, V = _exodus(exo, "V")
    fig, ax = plt.subplots(figsize=(5.6, 4.8))
    sc = ax.tricontourf(P[:, 0], P[:, 1], V * 1e3, levels=40, cmap="viridis")
    fig.colorbar(sc, ax=ax, label="potential drop at 1 A (mV)")
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(d / "04_field.png", dpi=150)
    plt.close(fig)


def field_png_column(d, exo, title):
    P, V = _exodus(exo, "T")
    y0 = P[np.argmin(np.abs(P[:, 1])), 1]
    sel = np.abs(P[:, 1] - y0) < 1e-9
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    sc = ax.tricontourf(P[sel, 0], P[sel, 2], V[sel], levels=40, cmap="inferno")
    fig.colorbar(sc, ax=ax, label="T (°C)")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("z (mm)")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(d / "04_field.png", dpi=150)
    plt.close(fig)


def readme(d, title, lines):
    (d / "README.md").write_text(f"# {title}\n\n" + "\n".join(lines) + "\n")


# ------------------------------------------------------------------ stages ----
def rve_stages(status):
    rve = J("reference_rve.json") or {}
    groups = {"tsv_bulk": ["tsv_bulk"], "tsv_tile_rve": ["tsv_tile_kz", "tsv_tile_kx"],
              "rdl_tier_rve": ["rdl_tier_kx", "rdl_tier_kz"]}
    for folder, keys in groups.items():
        d = EV / folder
        d.mkdir(parents=True, exist_ok=True)
        rows = {k: rve[k] for k in keys if k in rve and rve[k].get("solved")}
        status[folder] = ("AEDT", bool(rows))
        if not rows:
            readme(d, folder, ["No solved AEDT result exists for this stage."])
            continue
        dump(d, "setup.json", {k: {kk: v.get(kk) for kk in (
            "observable", "production_model", "reference_tool", "cu_fraction")}
            for k, v in rows.items()})
        rt = J("reference_rve_timing.json") or {}
        dump(d, "runtime.json", {k: {"production": v["production_timing"],
                                     "reference_first_solve_s": v["reference_wall_s"],
                                     "reference_retimed": rt.get(k),
                                     "reference_cores": 4, "hardware": v.get("hardware")}
                                 for k, v in rows.items()})
        dump(d, "result.json", {k: {kk: v[kk] for kk in (
            "production_value", "reference_value", "rel_error")} for k, v in rows.items()})
        comparison_png(d, f"{folder}: production model vs AEDT FEM",
                       [k.replace("_", " ") for k in rows],
                       [v["production_value"] for v in rows.values()],
                       [v["reference_value"] for v in rows.values()],
                       "value (Ohm or W/mK)", "production", "AEDT FEM")
        imgs = sorted(p.name for p in d.glob("01_*.png"))
        readme(d, folder, [
            f"Reference: {AEDT}, steady conduction (exact analogue of DC conduction).",
            f"Images {', '.join(imgs) or '(none)'} were exported from the AEDT session that "
            "produced the numbers (native ExportModelImageToFile under a virtual display).",
            "AEDT field plots fail over this PyAEDT/gRPC pairing, so no field image is shown; "
            "none is synthesised.", "",
            "| observable | production | AEDT | error |", "|---|---|---|---|"] + [
            f"| {v['observable']} | {v['production_value']:.6g} | {v['reference_value']:.6g} "
            f"| {100 * v['rel_error']:+.3f} % |" for v in rows.values()] + [
            "", "Runtimes: the production model is the median of repeated calls; the AEDT "
            "reference is the median of three re-solves after a warm-up (4 cores) where "
            "reference_retimed is present, otherwise its single first solve. See "
            "runtime.json."])


def pkg_rdl_stages(status):
    for arch in ("Z1", "Z2"):
        m = J(f"reference_pkg_rdl_moose_{arch}.json")
        d = EV / f"pkg_rdl_moose_{arch}"
        d.mkdir(parents=True, exist_ok=True)
        status[d.name] = ("MOOSE", bool(m))
        if not m:
            readme(d, d.name, ["No MOOSE result exists for this stage."])
            continue
        wd = Path(f"/tmp/moose_rdl_{arch}")
        for f in ("rdl.i", "moose_log_tail.txt"):
            if (wd / f).exists():
                shutil.copy(wd / f, d / f)
        exo = sorted(glob.glob(str(wd / "rdl_out*.e")))
        if exo:
            field_png_sheet(d, exo[-1], f"MOOSE potential, package HV RDL {arch}")
        ref = m["moose"]["m3"]
        dump(d, "setup.json", {"formulation": m["formulation"], "arch": arch,
                               "mesh_sequence": {t: {"h_fine_mm": v["h_fine_mm"],
                                                     "n_elements": v["n_elements"]}
                                                 for t, v in m["moose"].items()},
                               "production_cells_L3": m["production_L3"]["n_cv"]})
        dump(d, "runtime.json", {"production_L3": m["production_L3"].get("timing"),
                                 "moose_m3": ref.get("timing"), "cores": m.get("cores"),
                                 "load_average": m.get("load_average"),
                                 "method": m.get("timing_method")})
        dump(d, "result.json", {k: m.get(k) for k in (
            "rel_err_R_eff", "rel_err_max_drop", "rel_err_R_eff_vs_extrapolated",
            "moose_R_eff_extrapolated_ohm", "speedup_L3_vs_moose_m3")})
        comparison_png(d, f"Package HV RDL {arch}: FV sheet vs MOOSE FEM (m3)",
                       ["R_eff (mOhm)", "max pad drop (mV)"],
                       [m["production_L3"]["R_eff_ohm"] * 1e3,
                        m["production_L3"]["max_pad_drop_V"] * 1e3],
                       [ref["R_eff_ohm"] * 1e3, ref["max_pad_drop_V"] * 1e3],
                       "at 1 A", "production FV (L3)", "MOOSE FEM (m3)")
        readme(d, d.name, [
            "Reference: MOOSE heat_transfer-opt solving the exact analogue "
            "div(k grad T) = -q of the DC sheet problem on an unstructured gmsh mesh.",
            "04_field.png is rendered from MOOSE's own Exodus output of the finest mesh.",
            "rdl.i is the MOOSE input as run; moose_log_tail.txt the end of its log.", "",
            f"- R_eff error vs finest MOOSE mesh: {100 * m['rel_err_R_eff']:+.3f} %",
            f"- max pad drop error: {100 * m['rel_err_max_drop']:+.3f} %",
            f"- runtime ratio (MOOSE m3 / production L3, medians): "
            f"{m['speedup_L3_vs_moose_m3']:.2f}"])


def column_stages(status):
    for arch in ("Z1", "Z2"):
        mo = J(f"reference_thermal_column_moose_{arch}.json")
        d = EV / f"thermal_column_moose_{arch}"
        d.mkdir(parents=True, exist_ok=True)
        status[d.name] = ("MOOSE", bool(mo))
        if mo:
            exo = sorted(glob.glob(f"/tmp/col_moose_{arch}_m2/column_out*.e"))
            if exo:
                field_png_column(d, exo[-1], f"MOOSE temperature, unit cell {arch}, y = 0")
            dump(d, "setup.json", mo["spec"])
            dump(d, "runtime.json", {"ccx": mo["ccx"]["timing"],
                                     "moose_m2": mo["moose"]["m2"]["timing"],
                                     "cores": mo["cores"], "load_average": mo["load_average"],
                                     "method": mo["timing_method"]})
            dump(d, "result.json", {k: mo[k] for k in (
                "T_max_err_K", "T_rise_rel_err", "moose_mesh_change_K",
                "max_abs_layer_err_K", "speedup_ccx_vs_moose_median")})
            comparison_png(d, f"Unit-cell thermal {arch}: CalculiX vs MOOSE (temperature rise)",
                           ["T_max rise (K)"],
                           [mo["ccx"]["T_max_C"] - mo["spec"]["T_fluid_C"]],
                           [mo["moose"]["m2"]["T_max_C"] - mo["spec"]["T_fluid_C"]],
                           "K above fluid", "CalculiX C3D8", "MOOSE (m2)")
            readme(d, d.name, [
                "Reference: MOOSE heat_transfer-opt, AnisoHeatConduction on its own "
                "structured hex meshes (two levels), same unit cell, sources and films.",
                f"- T_max difference (CalculiX - MOOSE m2): {mo['T_max_err_K']:+.3f} K "
                f"({100 * mo['T_rise_rel_err']:+.3f} % of the rise)",
                f"- MOOSE own mesh change m1 -> m2: {mo['moose_mesh_change_K']:+.3f} K",
                f"- worst layer-mean difference: {mo['max_abs_layer_err_K']:.3f} K"])
        t = J(f"reference_thermal_column_{arch}.json")
        d = EV / f"thermal_column_{arch}"
        d.mkdir(parents=True, exist_ok=True)
        solved = bool(t and t.get("aedt", {}).get("solved"))
        status[d.name] = ("AEDT", solved)
        if solved:
            comparison_png(d, f"Unit-cell thermal {arch}: CalculiX vs AEDT (temperature rise)",
                           ["T_max rise (K)"],
                           [t["ccx_fine"]["T_max_C"] - t["spec"]["T_fluid_C"]],
                           [t["aedt"]["T_max_C"] - t["spec"]["T_fluid_C"]],
                           "K above fluid", "CalculiX C3D8", "AEDT Mechanical")
        else:
            readme(d, d.name, ["The AEDT unit-cell solve has no solved result in "
                               f"reference_thermal_column_{arch}.json; no number is claimed."])


def bilayer_stage(status):
    mb = J("reference_mech_bilayer.json")
    d = EV / "mech_bilayer"
    d.mkdir(parents=True, exist_ok=True)
    a = (mb or {}).get("aedt") or {}
    solved = bool(a.get("solved") and a.get("warp_pv_mm"))
    status[d.name] = ("AEDT", solved)
    if not mb:
        return
    prod = mb["ccx_n50"]["warp_pv_mm"]
    tim = mb["timoshenko"]["warp_pv_mm"]
    dump(d, "setup.json", {"geometry": "quarter 10 x 10 mm plate, Si 0.3 mm on organic 0.3 mm",
                           "load": "uniform dT = 100 K", "supports":
                           "symmetry x=0, y=0; 0.1 mm patch held in z at the centre"})
    dump(d, "runtime.json", {"ccx_n50": mb["ccx_n50"].get("timing"),
                             "aedt": a.get("timing"), "load_average": mb.get("load_average")})
    res = {"ccx_n50_mm": prod, "ccx_n30_mm": mb["ccx_n30"]["warp_pv_mm"],
           "timoshenko_mm": tim, "aedt_mm": a.get("warp_pv_mm"),
           "aedt_error": a.get("error")}
    dump(d, "result.json", res)
    labels, p, r = ["vs closed form"], [prod * 1e3], [tim * 1e3]
    if solved:
        labels.append("vs AEDT structural")
        p.append(prod * 1e3)
        r.append(a["warp_pv_mm"] * 1e3)
    comparison_png(d, "Bilayer warpage: CalculiX C3D8I vs references", labels, p, r,
                   "peak-to-valley warpage (µm)", "CalculiX C3D8I", "reference")
    readme(d, "mech_bilayer", [
        f"CalculiX C3D8I {prod * 1e3:.3f} µm; Timoshenko {tim * 1e3:.3f} µm "
        f"({100 * (prod - tim) / tim:+.3f} %).",
        (f"AEDT structural {a['warp_pv_mm'] * 1e3:.3f} µm "
         f"({100 * (prod - a['warp_pv_mm']) / a['warp_pv_mm']:+.3f} %); warpage per kelvin "
         "from two solved temperature levels, so AEDT's stress-free reference cannot bias it."
         if solved else f"AEDT structural: not solved ({a.get('error', 'no result')})."),
        "01_geometry.png is exported from the AEDT session that ran the model."])


def top_readme(status):
    rows = [f"| `{k}` | {tool} | {'solved, compared' if ok else 'NOT solved'} |"
            for k, (tool, ok) in sorted(status.items())]
    (EV / "README.md").write_text("\n".join([
        "# Reference-tool evidence", "",
        "Generated by `scripts/final_closure_evidence.py` from the reference artifacts in",
        "`research/final_closure/`. AEDT images are exported from the AEDT session that",
        "produced the matching number (native `ExportModelImageToFile` under a virtual",
        "display); MOOSE field images are rendered from MOOSE's own Exodus output. No vendor",
        "or documentation image is presented as a validation run.", "",
        "| stage | reference tool | status |", "|---|---|---|"] + rows + [
        "", "## Licensing on this host", "",
        "- AEDT 2026 R1 Mechanical (thermal, structural): licensed. Solves requesting more "
        "than 4 cores fail without HPC licences; every reported AEDT solve uses 4 cores.",
        "- AEDT Icepak: licensed; the matched CFD cooling benchmark was not executed.",
        "- Q3D Extractor and Maxwell DC conduction: installed, not licensed (licence error "
        "at solve). `scripts/reference_tools/q3d_dc_reference.py` is READY_NOT_EXECUTED.",
        "- MOOSE heat_transfer-opt: executed.",
        "- No circuit simulator (LTspice, PLECS, PSIM, ngspice) is installed, and no "
        "switch-state schedule exists for the converter; no waveform is simulated.", ""]))


def main():
    status = {}
    rve_stages(status)
    pkg_rdl_stages(status)
    column_stages(status)
    bilayer_stage(status)
    old = EV / "pkg_rdl_moose"                # superseded by the per-architecture folders
    if old.exists():
        shutil.rmtree(old)
    top_readme(status)
    for k, v in sorted(status.items()):
        print(f"  {k:28s} {v[0]:6s} {'solved' if v[1] else 'NOT solved'}")


if __name__ == "__main__":
    main()
