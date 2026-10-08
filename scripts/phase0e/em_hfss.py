#!/usr/bin/env python3
"""Phase-0E EM validation with ANSYS HFSS -- shorted one-port P/G TSV loop.

WHY THIS STRUCTURE AND THIS FREQUENCY RANGE
  Q3D Extractor is NOT licensed here (licence log: UNSUPPORTED "elec_solve_q3d", -5,346),
  so DC conduction is validated separately with a conduction FE. HFSS is used only where a
  full-wave formulation is valid.

  A two-port series extraction (Z11 - Z12) was tried first and REJECTED: at 286 kHz the
  structure is ~3e-9 wavelengths long, HFSS returns Z11 = Z12 = -4.2e7 ohm, and the series
  impedance is their difference -- 11 digits of catastrophic cancellation. That is classic
  low-frequency breakdown, not a usable number.

  Instead the far end is SHORTED and a single port drives the loop, so Z11 IS the loop
  impedance with no cancellation. The sweep spans 1 MHz - 1 GHz, which brackets the skin
  crossover (delta = via radius at 19.1 MHz). Showing R(f) flat below the crossover and
  rising as sqrt(f) above it validates the DC model AND demonstrates -- rather than assumes
  -- that f_sw = 0.286 MHz (delta/r = 8.2) carries no skin correction.
"""
from __future__ import annotations
import argparse, csv, json, math, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "results" / "phase0e" / "aedt"
OUT.mkdir(parents=True, exist_ok=True)

RHO_CU = 17.0e-9
SIGMA_CU = 1.0 / RHO_CU
MU0 = 4e-7 * math.pi


def skin_depth_um(f_hz: float, rho: float = RHO_CU) -> float:
    return math.sqrt(rho / (math.pi * f_hz * MU0)) * 1e6


def _parse_semicolon_csv(path: Path):
    """AEDT writes ';'-separated rows: 'Freq [GHz]; <expr> (Real); <expr> (Imag); ...'

    Columns are matched BY HEADER NAME, never by position: AEDT reorders the expressions
    relative to the list handed to get_solution_data (it emitted im(Z) before re(Z) here),
    and a positional parse silently transposes R and X.
    """
    raw = [ln for ln in path.read_text().splitlines() if ln.strip()]
    hdr = raw[0].split(";")
    body = []
    for ln in raw[1:]:
        try:
            body.append([float(x) for x in ln.split(";")])
        except ValueError:
            continue
    def col(expr):
        for i, hname in enumerate(hdr):
            hn = hname.replace(" ", "")
            if hn.startswith(expr.replace(" ", "")) and "(Real)" in hname:
                return i
        raise KeyError(f"{expr} not in {hdr}")
    return hdr, body, col


def pg_tsv_loop(d_um=30.0, h_um=300.0, gap_um=30.0, npair=1,
                f_start_mhz=1.0, f_stop_mhz=1000.0, npts=13,
                ng=True, mesh_passes=8) -> dict:
    from ansys.aedt.core import Hfss
    proj = OUT / f"em1_hfss_np{npair}.aedt"
    h = Hfss(project=str(proj), design=f"EM1_np{npair}", version="2026.1",
             non_graphical=ng, new_desktop=True, solution_type="Terminal")
    h.modeler.model_units = "um"
    if "cu_src" not in h.materials.material_keys:
        h.materials.add_material("cu_src").conductivity = SIGMA_CU

    pad_t = 5.0
    xv, xg = -(gap_um / 2 + d_um / 2), (gap_um / 2 + d_um / 2)
    pad_w, pad_d = d_um + 20.0, d_um + 20.0 + (npair - 1) * 60.0

    vdd, gnd = [], []
    for k in range(npair):
        y = (k - (npair - 1) / 2) * 60.0
        vdd.append(h.modeler.create_cylinder("Z", [xv, y, 0], d_um / 2, h_um,
                                             name=f"vdd{k}", material="cu_src"))
        gnd.append(h.modeler.create_cylinder("Z", [xg, y, 0], d_um / 2, h_um,
                                             name=f"gnd{k}", material="cu_src"))

    def box(x0, w, z0, t, nm):
        return h.modeler.create_box([x0 - w / 2, -pad_d / 2, z0], [w, pad_d, t],
                                    name=nm, material="cu_src")

    pvb, pgb = box(xv, pad_w, -pad_t, pad_t, "pvb"), box(xg, pad_w, -pad_t, pad_t, "pgb")
    # SHORTING BAR across the top: makes this a one-port loop, no Z11-Z12 cancellation.
    short = box(0.0, (xg - xv) + pad_w, h_um, pad_t, "short_top")

    h.modeler.unite([pvb] + vdd + [short] + gnd + [pgb])
    body = h.modeler["pvb"]
    # CRITICAL: by default HFSS applies a SURFACE-IMPEDANCE boundary to good conductors and
    # does not mesh their interior. That approximation is only valid for delta << conductor
    # size, so it cannot reproduce a DC resistance -- the first attempt returned R(1 MHz)
    # 11x below R_DC and scaling as f. Solving inside the copper makes the low-frequency
    # limit meaningful.
    body.solve_inside = True
    h.mesh.assign_length_mesh([body.name], maximum_length=d_um / 4,
                              maximum_elements=None, name="mesh_cu")

    x0p, x1p = xv + pad_w / 2, xg - pad_w / 2
    sh = h.modeler.create_rectangle("XZ", [x0p, 0, -pad_t], [pad_t, x1p - x0p], name="psheet")
    eps = 1e-3 * (x1p - x0p)
    h.lumped_port(assignment=sh.name, name="p1",
                  integration_line=[[x0p + eps, 0, -pad_t / 2], [x1p - eps, 0, -pad_t / 2]],
                  impedance=50, renormalize=False)

    h.modeler.create_air_region(300, 300, 150, 300, 300, 150)
    h.assign_radiation_boundary_to_objects("Region")

    su = h.create_setup(name="s1")
    su.props["Frequency"] = f"{f_stop_mhz}MHz"
    su.props["MaximumPasses"] = mesh_passes
    su.props["MaxDeltaS"] = 0.02
    su.update()
    # Logarithmically spaced discrete points: a linear sweep wastes nearly every point
    # above the skin crossover and leaves the physically important decade under-sampled.
    fpts = [f_start_mhz * (f_stop_mhz / f_start_mhz) ** (i / (npts - 1)) for i in range(npts)]
    fpts = [0.286] + fpts                       # include f_sw itself, flagged as out-of-regime
    h.create_single_point_sweep(setup="s1", unit="MHz", freq=fpts, name="sw",
                                save_single_field=False, save_fields=True)
    print(f"   sweep points (MHz): {[round(f,3) for f in fpts]}")

    t0 = time.time(); ok = h.analyze_setup("s1"); el = time.time() - t0
    print(f"   analyze -> {ok} in {el:.1f}s")

    res = {"ok": bool(ok), "solve_s": el, "npair": npair, "d_um": d_um, "h_um": h_um,
           "gap_um": gap_um, "mesh_passes": mesh_passes}
    if ok:
        d = h.post.get_solution_data(expressions=["re(Z(p1,p1))", "im(Z(p1,p1))"],
                                     setup_sweep_name="s1 : sw",
                                     report_category="Terminal Solution Data")
        csvf = OUT / f"em1_np{npair}_Zsweep.csv"
        d.export_data_to_csv(str(csvf))
        hdr, body_rows, col = _parse_semicolon_csv(csvf)
        i_re, i_im = col("re(Z(p1,p1))"), col("im(Z(p1,p1))")
        print(f"   header={hdr}\n   re col={i_re}  im col={i_im}")
        pts = []
        for r in body_rows:
            f = r[0] * 1e9                      # GHz -> Hz
            reZ, imZ = r[i_re], r[i_im]
            pts.append({"f_hz": f, "R_ohm": reZ, "L_nH": imZ / (2 * math.pi * f) * 1e9,
                        "delta_um": skin_depth_um(f),
                        "delta_over_r": skin_depth_um(f) / (d_um / 2),
                        "hfss_regime_ok": f >= 1e6})
        res["sweep"] = pts
        res["csv_header"] = hdr
    h.save_project(); h.release_desktop(close_projects=False, close_desktop=True)

    a = math.pi * (d_um * 1e-6) ** 2 / 4
    r1 = RHO_CU * (h_um * 1e-6) / a
    res["r_single_via_dc_ohm"] = r1
    res["r_loop_dc_analytic_ohm"] = 2 * r1 / npair    # supply + identical return
    res["skin_crossover_mhz"] = RHO_CU / (math.pi * MU0 * (d_um / 2 * 1e-6) ** 2) / 1e6
    res["fsw_mhz"] = 0.286
    res["delta_over_r_at_fsw"] = skin_depth_um(0.286e6) / (d_um / 2)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npair", type=int, default=1)
    ap.add_argument("--passes", type=int, default=8)
    ap.add_argument("--npts", type=int, default=13)
    a = ap.parse_args()
    r = pg_tsv_loop(npair=a.npair, mesh_passes=a.passes, npts=a.npts)
    (OUT / f"em1_hfss_np{a.npair}.json").write_text(json.dumps(r, indent=2))
    print(f"\nR_loop DC analytic = {r['r_loop_dc_analytic_ohm']*1e3:.3f} mOhm")
    print(f"skin crossover     = {r['skin_crossover_mhz']:.1f} MHz ; at f_sw delta/r = {r['delta_over_r_at_fsw']:.2f}")
    if r.get("sweep"):
        print(f"\n{'f (MHz)':>10s} {'R (mOhm)':>10s} {'R/R_dc':>8s} {'L (nH)':>8s} {'delta/r':>8s}")
        for p in r["sweep"]:
            print(f"{p['f_hz']/1e6:10.2f} {p['R_ohm']*1e3:10.4f} "
                  f"{p['R_ohm']/r['r_loop_dc_analytic_ohm']:8.3f} {p['L_nH']:8.3f} {p['delta_over_r']:8.2f}")
