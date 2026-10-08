#!/usr/bin/env python3
"""Phase-0M Parts 7 and 8 -- canonical transition cells and the current-crowding factor.

Three canonical cells, each a via/bump entering a pad and leaving through one or more RDL
traces:

    TSV       -> landing pad -> RDL
    microbump -> UBM -> pad  -> RDL
    C4        -> pad         -> package plane

K_crowd = R_3D_transition / R_bulk is reported as a DERIVED RESULT of each geometry. It is
never assumed constant and is never applied as one global multiplier -- which is exactly what
the incumbent `CROWDING_DEFAULT = 1.326` does to BGA, C4, TSV and microbump alike.
"""
from __future__ import annotations
import csv, math, sys
from dataclasses import dataclass
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0m"))
from conduction3d import FVConduction, refined, snapped                              # noqa: E402
from interconnect import rho_cu, rho_solder                                # noqa: E402

OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)
SIG_DIEL_RATIO = 1e-9


@dataclass(frozen=True)
class Cell:
    """A via/bump -> (optional UBM) -> pad -> RDL trace transition.

    THE PAD AND THE TRACE ARE ONE METAL LAYER. An earlier version of this cell stacked a
    pad layer under a separate trace layer, which put 1.5x the trace thickness of copper
    over the via and returned K_crowd < 1 for a reason that was geometric bookkeeping and
    not physics. A TSV lands on a pad that IS part of the redistribution layer, so the pad
    is a local widening of that layer, not an extra one.

    All lengths in metres.
    """
    name: str
    r_via: float
    h_via: float
    r_pad: float
    w_trace: float
    t_rdl: float
    l_trace: float
    n_trace: int = 1
    entry_deg: float = 0.0
    r_ubm: float = 0.0            # 0 -> no UBM layer
    t_ubm: float = 0.0
    sigma_via: float = 1.0 / 2.1343e-8
    sigma_ubm: float = 1.0 / 2.1343e-8
    sigma_metal: float = 1.0 / 2.1343e-8

    @property
    def z_ubm0(self): return self.h_via

    @property
    def z_rdl0(self): return self.h_via + self.t_ubm

    @property
    def z_top(self): return self.z_rdl0 + self.t_rdl

    def r_bulk(self) -> float:
        """1-D series of the NAMED conductors: via, UBM if present, and the trace over its
        full length from the via axis. No credit for the pad -- the pad's effect is exactly
        what K_crowd is being asked to measure."""
        rv = (1.0 / self.sigma_via) * self.h_via / (math.pi * self.r_via ** 2)
        ru = ((1.0 / self.sigma_ubm) * self.t_ubm / (math.pi * self.r_ubm ** 2)
              if self.t_ubm > 0 and self.r_ubm > 0 else 0.0)
        rt = (1.0 / self.sigma_metal) * self.l_trace / \
             (self.n_trace * self.w_trace * self.t_rdl)
        return rv + ru + rt

    def trace_angles(self):
        """Traces leave the pad along AXIS-ALIGNED directions, rotated by `entry_deg`.

        The first version fanned them at +/- 60 degrees. On a square domain grounded only at
        x_max that left every non-zero-degree trace a DEAD END carrying no current, so the
        three-trace case returned K_crowd = 2.49 -- an artifact of the boundary condition,
        not a crowding result. Axis-aligned directions with all four lateral faces grounded
        give every trace an exit and keep them aligned with the mesh.
        """
        base = [0.0, 90.0, 180.0, 270.0][:max(self.n_trace, 1)]
        return [math.radians(self.entry_deg + a) for a in base]

    def sigma_fn(self):
        rad = self.trace_angles()

        def fn(X, Y, Z):
            s = np.full(X.shape, self.sigma_metal * SIG_DIEL_RATIO)
            rr = X ** 2 + Y ** 2
            s[(rr <= self.r_via ** 2) & (Z <= self.z_ubm0)] = self.sigma_via
            if self.t_ubm > 0:
                s[(rr <= self.r_ubm ** 2) & (Z > self.z_ubm0) &
                  (Z <= self.z_rdl0)] = self.sigma_ubm
            lay = (Z > self.z_rdl0) & (Z <= self.z_top)
            s[(rr <= self.r_pad ** 2) & lay] = self.sigma_metal
            for A in rad:
                u = X * math.cos(A) + Y * math.sin(A)
                v = -X * math.sin(A) + Y * math.cos(A)
                s[(u >= 0) & (np.abs(v) <= self.w_trace / 2) & lay] = self.sigma_metal
            return s
        return fn

    def mesh(self, refine: float = 1.0, nz_rdl: int = 5):
        h = min(self.r_pad / 8.0, self.w_trace / 6.0, self.r_via / 6.0) / refine
        core = 1.45 * self.r_pad
        # square domain of half-width l_trace so every axis-aligned trace has the same
        # length to its exit and all four lateral faces can be grounded
        man = [-self.r_pad, -self.r_via, -self.w_trace / 2, 0.0,
               self.w_trace / 2, self.r_via, self.r_pad]
        xn = snapped(refined(-core, core, h, -self.l_trace, self.l_trace), man, h)
        yn = snapped(refined(-core, core, h, -self.l_trace, self.l_trace), man, h)
        zparts = [refined(max(self.z_ubm0 - 3 * h, 0.0), self.z_ubm0, h, 0.0, self.z_ubm0)]
        if self.t_ubm > 0:
            zparts.append(np.linspace(self.z_ubm0, self.z_rdl0,
                                      max(int(3 * refine), 2) + 1))
        zparts.append(np.linspace(self.z_rdl0, self.z_top,
                                  max(int(nz_rdl * refine), 3) + 1))
        return xn, yn, zn_clean(np.concatenate(zparts))


def zn_clean(z):
    z = np.unique(z)
    return z[np.concatenate([[True], np.diff(z) > 1e-12])]


def solve_cell(c: Cell, **mesh_kw) -> dict:
    xn, yn, zn = c.mesh(**mesh_kw)
    m = FVConduction(xn, yn, zn)
    m.assign(c.sigma_fn())
    X, Y, Z = np.meshgrid(m.xc, m.yc, m.zc, indexing="ij")
    inj = (X ** 2 + Y ** 2 <= c.r_via ** 2) & (Z <= m.zc[0] + 1e-18)
    # ground every metal cell on ANY lateral outer face, so a trace leaving in -x or +/-y
    # is a real exit rather than a dead end
    edge = ((X >= m.xc[-1] - 1e-18) | (X <= m.xc[0] + 1e-18)
            | (Y >= m.yc[-1] - 1e-18) | (Y <= m.yc[0] + 1e-18))
    gnd = edge & (m.sigma > c.sigma_metal * 0.5)
    if not inj.any() or not gnd.any():
        return {"status": "DEGENERATE MESH", "cell": c.name}
    m.solve(inj, 1.0, gnd, axis_in=2, axis_gnd=0)
    # the ground half-cell conductance is computed on axis 0; for a trace exiting through a
    # +/-y face that under-states the contact area. The outer cells are the coarsest in the
    # graded mesh, so the half-cell term is a small fraction of R and the residual is
    # reported rather than ignored.
    r3 = m.resistance()
    rp = m.resistance_from_power()
    j = m.j_field()
    metal = m.sigma > c.sigma_metal * 0.5
    vol = (m.dx[:, None, None] * m.dy[None, :, None] * m.dz[None, None, :])
    jm, vm = j[metal], vol[metal]
    j_avg = float((jm * vm).sum() / vm.sum())
    order = np.argsort(jm)
    cw = np.cumsum(vm[order]) / vm.sum()
    j_999 = float(jm[order][np.searchsorted(cw, 0.999)])
    rb = c.r_bulk()
    # VALIDITY GATE. A solve that does not deliver the injected current to the ground has
    # not converged on the intended geometry, whatever number it returns.
    i_err = abs(m.current_out() - 1.0)
    if i_err > 1e-3:
        return {"status": f"CURRENT BALANCE FAILED ({i_err:.3e})", "cell": c.name,
                "current_balance_err": i_err, "n_cells": m.n}
    # discretised via area, so the circular staircase error is reported not hidden
    zlayer = np.argmax(m.zc > 0)
    a_via_disc = float(vol[:, :, zlayer][m.sigma[:, :, zlayer] > c.sigma_metal * 0.5].sum()
                       / m.dz[zlayer])
    return {"status": "OK", "cell": c.name,
            "r_via_um": c.r_via * 1e6, "h_via_um": c.h_via * 1e6,
            "r_pad_um": c.r_pad * 1e6, "t_rdl_um": c.t_rdl * 1e6,
            "w_trace_um": c.w_trace * 1e6, "l_trace_um": c.l_trace * 1e6,
            "n_trace": c.n_trace, "entry_deg": c.entry_deg,
            "r_ubm_um": c.r_ubm * 1e6, "t_ubm_um": c.t_ubm * 1e6,
            "pad_over_via": c.r_pad / c.r_via,
            "trace_over_via": c.w_trace / (2 * c.r_via),
            "R_bulk_mohm": rb * 1e3, "R_3D_mohm": r3 * 1e3,
            "R_3D_from_power_mohm": rp * 1e3,
            "power_vs_terminal_pct": 100 * abs(rp - r3) / r3,
            "K_crowd": r3 / rb,
            "J_avg_A_per_m2": j_avg, "J_p999_A_per_m2": j_999,
            "J_peak_over_avg": j_999 / j_avg,
            "current_balance_err": abs(m.current_out() - 1.0),
            "via_area_discrete_over_exact": a_via_disc / (math.pi * c.r_via ** 2),
            "n_cells": m.n, "n_active": getattr(m, "n_active", -1)}


# ---------------------------------------------------------------------------
# Part 8 -- the sweep
# ---------------------------------------------------------------------------
T_C = 85.0
SIG_CU = 1.0 / rho_cu(T_C)
SIG_SN = 1.0 / rho_solder(T_C)

NOMINAL = {
    "TSV_pad_RDL": dict(r_via=15e-6, h_via=30e-6, r_pad=18e-6, w_trace=10e-6,
                        t_rdl=10e-6, l_trace=100e-6,
                        sigma_via=SIG_CU, sigma_metal=SIG_CU),
    "microbump_UBM_pad_RDL": dict(r_via=5e-6, h_via=10e-6, r_ubm=6e-6, t_ubm=3e-6,
                                  r_pad=6e-6, w_trace=5e-6, t_rdl=5e-6, l_trace=40e-6,
                                  sigma_via=SIG_SN, sigma_ubm=SIG_CU, sigma_metal=SIG_CU),
    "C4_pad_plane": dict(r_via=50e-6, h_via=70e-6, r_pad=60e-6, w_trace=150e-6,
                         t_rdl=15e-6, l_trace=400e-6,
                         sigma_via=SIG_SN, sigma_metal=SIG_CU),
}

# one factor at a time about each nominal; multipliers on the nominal value
FACTORS = {
    "pad_over_via": ("r_pad", "mult_r_via", [1.0, 1.2, 1.5, 2.0, 2.5]),
    "trace_width": ("w_trace", "mult_d_via", [0.33, 0.5, 0.75, 1.0, 1.5, 2.0]),
    "rdl_thickness": ("t_rdl", "abs_um", [2.5, 5.0, 10.0, 20.0, 40.0]),
    # For a CIRCULAR pad, entry angle can have no physical effect -- the geometry is
    # rotationally symmetric. Any spread it produces is the Cartesian staircase error on a
    # rotated rectangle, so this row is a NUMERICAL sensitivity probe and is labelled as one.
    "entry_angle_STAIRCASE_PROBE": ("entry_deg", "abs", [0.0, 15.0, 30.0, 45.0]),
    "n_parallel_traces": ("n_trace", "abs", [1, 2, 3, 4]),
    "via_radius": ("r_via", "abs_um", [2.5, 5.0, 10.0, 15.0, 25.0, 50.0]),
    "trace_length": ("l_trace", "abs_um", [50.0, 100.0, 200.0, 400.0]),
}


def build(cellname: str, field: str | None = None, value=None, kind: str = "abs") -> Cell:
    kw = dict(NOMINAL[cellname])
    if field is not None:
        if kind == "mult_r_via":
            kw[field] = value * kw["r_via"]
        elif kind == "mult_d_via":
            kw[field] = value * 2 * kw["r_via"]
        elif kind == "abs_um":
            kw[field] = value * 1e-6
        else:
            kw[field] = value
    return Cell(name=cellname, **kw)


def sweep(refine: float = 1.0) -> list[dict]:
    rows = []
    for cn in NOMINAL:
        base = solve_cell(build(cn), refine=refine)
        base.update(factor="NOMINAL", factor_value="", cell=cn)
        base["dR_excess_mohm"] = base["R_3D_mohm"] - base["R_bulk_mohm"]
        rows.append(base)
        print(f"  {cn:24s} NOMINAL            K={base['K_crowd']:.4f} "
              f"dR={base['dR_excess_mohm']:+.5f} mOhm", flush=True)
        for fac, (field, kind, vals) in FACTORS.items():
            for v in vals:
                try:
                    r = solve_cell(build(cn, field, v, kind), refine=refine)
                except Exception as e:                       # noqa: BLE001
                    rows.append({"status": f"FAILED {type(e).__name__}: {e}",
                                 "cell": cn, "factor": fac, "factor_value": v})
                    continue
                if r.get("status") != "OK":
                    r.update(cell=cn, factor=fac, factor_value=v); rows.append(r); continue
                r.update(factor=fac, factor_value=v, cell=cn)
                r["dR_excess_mohm"] = r["R_3D_mohm"] - r["R_bulk_mohm"]
                rows.append(r)
                print(f"  {cn:24s} {fac:18s}={v:<6} K={r['K_crowd']:.4f} "
                      f"dR={r['dR_excess_mohm']:+.5f} mOhm  "
                      f"Jpk/avg={r['J_peak_over_avg']:.2f}", flush=True)
    return rows


def convergence(cellname: str = "TSV_pad_RDL") -> list[dict]:
    out = []
    for ref in (0.8, 1.0, 1.3, 1.6, 2.0):
        r = solve_cell(build(cellname), refine=ref)
        r.update(factor="MESH_CONVERGENCE", factor_value=ref, cell=cellname)
        r["dR_excess_mohm"] = r["R_3D_mohm"] - r["R_bulk_mohm"]
        out.append(r)
        print(f"  convergence refine={ref} cells={r['n_cells']} active={r['n_active']} "
              f"K={r['K_crowd']:.5f}", flush=True)
    return out


def main() -> int:
    import time
    t0 = time.time()
    rows = convergence() + sweep()
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "current_crowding_transition_sweep.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    ok = [r for r in rows if r.get("status") == "OK"]
    print(f"\n{len(ok)}/{len(rows)} solves OK in {time.time()-t0:.0f}s")
    print(f"K_crowd spans {min(r['K_crowd'] for r in ok):.3f} to "
          f"{max(r['K_crowd'] for r in ok):.3f}")
    print(f"wrote {OUT/'current_crowding_transition_sweep.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
