"""PHASE 0N-W --- PCB-H1, a reduced multilayer board (brief section 7).

PCB-H0 is one 2.4 mm orthotropic slab. It is a legitimate reduced-order baseline, but the
cited multilayer-PCB thermal literature warns that a single effective-conductivity board
can be insufficient for 3-D spreading, so H0 has to be VALIDATED rather than assumed.

H1 resolves the real 18-layer schedule into depth blocks without meshing a single trace.

AN HONEST NOTE ON "ALTERNATING Cu-RICH / DIELECTRIC". The UGPCB schedule is 14 x 1 oz +
4 x 2 oz, i.e. UNIFORM 1 oz everywhere except four heavy central plane layers. So the only
COMPOSITIONAL alternation this board has is central-vs-outer, and a five-block reduction
produces four blocks of identical composition. They are kept as separate blocks anyway,
because they sit at different DEPTHS and depth is what matters for 3-D spreading -- but
the reduction is not hiding a rich alternating structure, because the published schedule
does not have one.

    B1  outer block (top)          layers 1-2      2 oz    f_Cu 0.131
    B2  upper block                layers 3-7      5 oz    f_Cu 0.131
    B3  central plane block        layers 8-11     8 oz    f_Cu 0.261   <- the 4 x 2 oz
    B4  lower block                layers 12-16    5 oz    f_Cu 0.131
    B5  outer block (bottom)       layers 17-18    2 oz    f_Cu 0.131

If the real artwork thins the signal layers (it is unpublished), the outer blocks would be
less copper-rich than this and the contrast with B3 would grow. That is the eta sweep.

WHY THIS IS NOT A GUARANTEED NO-OP. In pure 1-D series conduction, five blocks whose k_z
follows the same Reuss rule reproduce the single slab's through-thickness resistance
exactly. The difference is entirely three-dimensional: in H1 the copper-rich blocks have a
much higher in-plane k and sit at specific depths, so heat entering locally spreads at
those depths instead of through a depth-averaged medium. A localized source over a thick
board is exactly the configuration where that matters -- which is this package.

So an H0-vs-H1 difference near zero would be a RESULT (the board may be treated as one
slab), not a tautology, and a large difference invalidates H0 for the final thermal claim.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0g", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

HOMOG_JSON = R / "research" / "phase0nv" / "pcb_homogenization.json"

# (name, n_layers, copper_oz) -- must sum to 18 layers and 22 oz, which is asserted below.
BLOCKS = (
    ("b1_outer_top",      2, 2.0),
    ("b2_upper",          5, 5.0),
    ("b3_central_planes", 4, 8.0),   # the only Cu-rich block in this schedule
    ("b4_lower",          5, 5.0),
    ("b5_outer_bot",      2, 2.0),
)
OZ_UM = 34.8


def _constituents():
    h = json.loads(HOMOG_JSON.read_text())
    return h["laminate"], h["copper"], h["bounds"], h["board"], h["nominal_tensor"]


def blocks(t_board_mm: float = 2.4, eta: float = 0.50) -> list:
    """Per-block effective properties at copper coverage `eta`.

    Each block carries its OWN copper fraction, so the central plane block is stiff and
    thermally conductive and the dielectric blocks are not -- which is the whole point.
    """
    lam, cu, bnd, brd, _nom = _constituents()
    n_tot = sum(b[1] for b in BLOCKS)
    oz_tot = sum(b[2] for b in BLOCKS)
    assert n_tot == brd["layers"], f"{n_tot} layers against the schedule's {brd['layers']}"
    assert abs(oz_tot - (brd["n_1oz"] + 2 * brd["n_2oz"])) < 1e-9, (
        f"{oz_tot} oz against the schedule's {brd['n_1oz'] + 2*brd['n_2oz']} oz")

    E_cu, cte_cu, k_cu, nu_cu = cu["E_MPa"], cu["cte_ppm"], cu["k_W_mK"], cu["nu"]
    E_warp, E_fill = lam["E_warp_MPa"], lam["E_fill_MPa"]
    cte_lx, cte_ly = lam["cte_xy_primary_ppm"]
    cte_lz = lam["cte_z_pre_tg_ppm"]
    k_lam_xy = 0.5 * (bnd["k_lam_xy"][0] + bnd["k_lam_xy"][1])
    k_lam_z = 0.5 * (bnd["k_lam_z"][0] + bnd["k_lam_z"][1])

    out = []
    for name, n_lay, oz in BLOCKS:
        t_mm = t_board_mm * n_lay / n_tot
        t_cu_um = oz * OZ_UM * eta
        fv = min(t_cu_um / (t_mm * 1e3), 0.95)
        fl = 1.0 - fv
        Ex = fv * E_cu + fl * E_warp                      # Voigt
        Ey = fv * E_cu + fl * E_fill
        cx = (fv * E_cu * cte_cu + fl * E_warp * cte_lx) / Ex
        cz = fv * cte_cu + fl * cte_lz
        kxy = fv * k_cu + fl * k_lam_xy                   # Voigt
        kz = 1.0 / (fv / k_cu + fl / k_lam_z)             # Reuss
        out.append({"name": name, "n_layers": n_lay, "copper_oz": oz,
                    "t_mm": t_mm, "f_cu": fv,
                    "E_MPa": Ex, "Ey_MPa": Ey, "nu": nu_cu * fv + 0.20 * fl,
                    "cte": cx * 1e-6, "cte_z_ppm": cz,
                    "k_xy": kxy, "k_z": kz})
    return out


def board_materials(t_board_mm: float = 2.4, eta: float = 0.50) -> dict:
    """Material cards, one per block, for injection into a stack."""
    mats = {}
    for b in blocks(t_board_mm, eta):
        mats[f"board_{b['name']}"] = {
            "status": "DERIVED", "elastic_type": "iso",
            "E": {"value": b["E_MPa"], "status": "DERIVED"},
            "nu": {"value": b["nu"], "status": "ASSUMPTION"},
            "cte": {"value": b["cte"], "status": "DERIVED"},
            "k": {"value": b["k_z"], "status": "DERIVED"},
            "k_ortho": {"value": [b["k_xy"], b["k_xy"], b["k_z"]], "status": "DERIVED"}}
    return mats


def bottom_layers(t_board_mm: float = 2.4, eta: float = 0.50, nz: int = 1) -> list:
    """(name, thickness_mm, material, nz) replacing the single `board` layer, deepest first.

    B5 is deepest because the stack is laid down from the PCB backside upward toward the
    BGA.
    """
    bs = blocks(t_board_mm, eta)
    return [(f"board_{b['name']}", b["t_mm"], f"board_{b['name']}", nz)
            for b in reversed(bs)]


def series_kz(t_board_mm: float = 2.4, eta: float = 0.50) -> float:
    """Effective through-thickness k of the five blocks in series.

    Compared against H0's single k_z, this is the 1-D consistency check: if the two differ
    materially, H1 is not a refinement of H0 but a different board.

    THEY DO NOT AGREE EXACTLY, AND THE REASON IS WORTH STATING. k_lam_z is an OPEN
    quantity carried as a bracket, and the midpoint is taken at different stages: H0
    reduces the bracket once for the whole board, H1 reduces it per block and then
    combines in series. Reuss is non-linear, so midpoint-of-Reuss != Reuss-of-midpoint.
    The resulting relative difference is ~8e-7 -- six orders below any physical effect,
    and it would vanish entirely if k_lam_z were a single sourced number instead of a
    bracket. It is recorded rather than tuned away.
    """
    bs = blocks(t_board_mm, eta)
    t = sum(b["t_mm"] for b in bs)
    return t / sum(b["t_mm"] / b["k_z"] for b in bs)


def summary(t_board_mm: float = 2.4, eta: float = 0.50) -> dict:
    bs = blocks(t_board_mm, eta)
    _l, _c, _b, _brd, nom = _constituents()
    kz_h1 = series_kz(t_board_mm, eta)
    t = sum(b["t_mm"] for b in bs)
    kxy_h1 = sum(b["k_xy"] * b["t_mm"] for b in bs) / t      # thickness-weighted, parallel
    return {"eta": eta, "t_board_mm": t, "blocks": bs,
            "h0_k_xy": nom["k_xy"], "h0_k_z": nom["k_z"],
            "h1_series_k_z": kz_h1, "h1_parallel_k_xy": kxy_h1,
            "k_z_rel_diff": abs(kz_h1 - nom["k_z"]) / nom["k_z"],
            "k_xy_rel_diff": abs(kxy_h1 - nom["k_xy"]) / nom["k_xy"]}


if __name__ == "__main__":
    s = summary()
    print(f"PCB-H1 at eta = {s['eta']}, total {s['t_board_mm']:.3f} mm")
    print(f"{'block':20s} {'lay':>4s} {'oz':>5s} {'t mm':>7s} {'f_Cu':>7s} "
          f"{'E GPa':>8s} {'k_xy':>8s} {'k_z':>8s}")
    for b in s["blocks"]:
        print(f"{b['name']:20s} {b['n_layers']:4d} {b['copper_oz']:5.1f} {b['t_mm']:7.4f} "
              f"{b['f_cu']:7.4f} {b['E_MPa']/1e3:8.2f} {b['k_xy']:8.2f} {b['k_z']:8.4f}")
    print(f"\nH0  k_xy {s['h0_k_xy']:8.3f}   k_z {s['h0_k_z']:.4f}")
    print(f"H1  k_xy {s['h1_parallel_k_xy']:8.3f}   k_z {s['h1_series_k_z']:.4f} (series)")
    print(f"relative difference  k_xy {100*s['k_xy_rel_diff']:.3f} %   "
          f"k_z {100*s['k_z_rel_diff']:.3f} %")
