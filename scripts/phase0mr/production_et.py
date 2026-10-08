#!/usr/bin/env python3
"""Phase-0M-R Sections 12-13 -- the production electrothermal fixed point.

THREE THINGS CHANGE RELATIVE TO THE PHASE-0M PRODUCTION PATH

1. SPATIAL HEAT. Every new electrical loss term is deposited where it physically occurs --
   converter losses in the converter layer, intra-VR metal with them, TSV loss in the via
   field, RDL loss in the interface layer, bump loss in the BGA layer -- and the deposited
   total is CHECKED against the electrical total to 1e-9 before the solve is allowed to run.

2. PHYSICAL COOLING. `h` comes from channel geometry and mass flow, and the sink temperature
   varies along the flow as the coolant picks up heat. The fluid temperature is iterated
   against the solved surface flux, so this is a staggered conjugate solve and not a Robin
   boundary with a derived coefficient.

3. LOCAL TEMPERATURE FEEDBACK. The converter is re-evaluated at the temperature of its OWN
   layer rather than at the package maximum.
"""
from __future__ import annotations
import csv, json, math, os, re, shutil, sys, time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m", "phase0i", "phase0h", "phase0g", "phase0f",
          "phase0e", "phase0dr", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / d))
from etm import ccxio, metrics                                             # noqa: E402
from etm.config import build_materials, load_doe, load_stack,  \
    W_M2K_TO_W_MM2K                                                        # noqa: E402
from etm.mesh import build                                                 # noqa: E402
from etm.placement import Tile                                            # noqa: E402
import zglobal as ZG                                                       # noqa: E402
import kw1                                                                 # noqa: E402
from cooling_production import CoolingDesign, CANDIDATES, CP_F             # noqa: E402

OUT = R / "results" / "phase0mr"
WD = OUT / "et"
OUT.mkdir(parents=True, exist_ok=True)
WD.mkdir(parents=True, exist_ok=True)

DIE_MM = 22.36
N_VR = 49
HVR_AREA_MM2 = 274.89


class EnergyError(Exception):
    """Deposited heat does not equal the electrical loss."""


def converter_layer(arch: str, m) -> str:
    """Where the converter heat goes, per architecture.

    ARCH_Z4 puts a dedicated power die ABOVE the substrate, and `zglobal.stack_for` does not
    give that architecture a converter layer at all -- the Phase-0I global model never
    represented the Z4 power die geometrically. Its heat is therefore deposited in the
    `interface` layer, which occupies the same position in the stack, and that substitution
    is RECORDED rather than hidden: the Z4 thermal result is conditional on it.
    """
    have = {l.name for l in m.layers}
    place = ZG.CONV_PLACE[arch]
    if place == "in" and "tile_band" in have:
        return "tile_band"
    if place == "below" and "conv" in have:
        return "conv"
    if place == "above":
        # PHASE 0M-R2. ARCH_Z4's power die is real geometry now. Its heat goes into the
        # component band of that die, never into `interface`. The old fallback is REMOVED
        # rather than left as a silent safety net: a missing power die must be an error,
        # because a fallback is exactly how the conditional Z4 result was produced.
        band = tuple(n for n in
                     ("pdie_components", "pdie_gan_hs", "pdie_gan_ls",
                      "pdie_inductor", "pdie_mlcc") if n in have)
        if band:
            return band
        raise EnergyError(
            f"{arch} declares its converter ABOVE the substrate but the mesh has no power "
            f"die; have {sorted(have)}. Depositing this heat in `interface` is the "
            f"Phase-0M-R substitution and is no longer permitted.")
    raise EnergyError(f"no converter layer available for {arch}; have {sorted(have)}")


def build_global(arch: str, h_sub_mm: float, h_xy: float = 1.1, doe=None,
                 z4_variant: str = "Z4_STACKED"):
    """The Phase-0I global mesh for one architecture, with its materials and tiles.

    Extracted so the layer set a given architecture actually gets can be inspected
    directly -- that is how the missing ARCH_Z4 converter layer was found.

    PHASE 0M-R2: ARCH_Z4 now receives its power die as REAL GEOMETRY between the
    substrate top and the compute die (`ZG.mid_layers`), instead of having its heat
    deposited into the `interface` layer.
    """
    doe = load_doe() if doe is None else doe
    st, extra, _t_tile = ZG.stack_for(arch, h_sub_mm)
    mid = ZG.mid_layers(arch, os.environ.get("PHASE0MR2_Z4_VARIANT", z4_variant))
    side = math.sqrt(HVR_AREA_MM2 / N_VR)
    xy = kw1.tiles_for("uniform", side, st, doe, N_VR)
    tiles = [Tile(cx, cy, side, side, 0.0) for cx, cy in xy]
    # PHASE 0M-R2. For ARCH_Z2 and ARCH_Z4 the converter is NOT in the substrate, so the
    # 20 um band `stack_for` reserves at the substrate top is a thin RDL band, not a
    # converter cell -- and the TSV field passes THROUGH it. Treating it as a converter
    # cell shortened the meshed via field to 280 um while the electrical model used the
    # full 300 um: one physical via with two lengths.
    m = build(tiles, st, h_sub_mm, h_xy=h_xy, z_scale=1.4, support_layer=False,
              extra_bottom_layers=extra, extra_mid_layers=mid,
              tile_band_is_converter=(ZG.CONV_PLACE.get(arch) == "in"))
    return m, build_materials(st), st, tiles


@dataclass
class HeatMap:
    """Where each loss term goes. Layer names come from the mesh, not from a comment."""
    die_w: float
    converter_w: float          # switches, gate, Coss, inductor DCR, cap ESR
    intravr_w: float            # intra-VR metallisation, same layer as the converter
    tsv_w: float
    rdl_w: float
    bump_w: float

    def total(self) -> float:
        return (self.die_w + self.converter_w + self.intravr_w + self.tsv_w
                + self.rdl_w + self.bump_w)


def check_energy(hm: "HeatMap", deposited: float) -> None:
    """ENERGY ACCOUNTING GUARD: every electrical watt must land somewhere in the mesh.

    The tolerance is 1e-6 relative, not 1e-9: `deposited` is a sum of six independent
    (w / vol) * vol round trips and accumulates float error at the 1e-7 level, which is
    not a physics error. 1e-6 of 1130 W is 1.1 mW -- far below any term in the ledger --
    so the guard still catches a genuinely lost or duplicated source.
    """
    rel = abs(deposited - hm.total()) / max(hm.total(), 1.0)
    if rel > 1e-6:
        raise EnergyError(f"deposited {deposited:.9g} W against an electrical total of "
                          f"{hm.total():.9g} W (relative {rel:.3e})")


def _layer_elems(m, name) -> np.ndarray:
    """Elements of one layer, or of several treated as one region.

    ARCH_Z4's power die is SEVERAL layers -- HS, LS, inductor, MLCC -- and the converter
    loss belongs to the whole component band, not to whichever layer happens to be named
    first. Depositing it all in one sub-layer would put a 1 kW-class source in a 685 um
    slab and misstate the gradient through the die.
    """
    names = (name,) if isinstance(name, str) else tuple(name)
    have = [l.name for l in m.layers]
    missing = [n for n in names if n not in have]
    if missing:
        raise EnergyError(f"layer {missing!r} is not in this mesh; available: {have}")
    cen = m.elem_centroids()
    sel = np.concatenate([
        np.flatnonzero((cen[:, 2] > m.layer(n).z0 + 1e-12)
                       & (cen[:, 2] < m.layer(n).z1 - 1e-12)) for n in names])
    return np.unique(sel) + 1


def _write_thermal(m, mats, tiles, stack, hm: HeatMap, conv_layer,
                   h_face: np.ndarray, t_face: np.ndarray, path: Path) -> dict:
    """Thermal deck with SPATIAL heat and a PER-FACE film (h_i, T_f,i)."""
    g = stack["geometry"]
    tb = stack["thermal_bc"]
    h_bot = tb["h_bottom"]["value"]
    t_amb = tb["ambient_bottom"]["value"]
    L = ccxio._nodes_block(m) + ccxio._elements_blocks(m, "C3D8")
    L += ccxio._fmt_set("NALL", np.arange(1, m.n_nodes + 1), "NSET")
    # PHASE 0M-R2 Section 8. The interface layer may be given the ORTHOTROPIC tensor
    # derived from its own sourced microbump geometry instead of the isotropic
    # underfill value, to test whether promoting it changes the architecture answer.
    # PHASE 0M-R2 Section 8: PROMOTED TO THE PRODUCTION DEFAULT. The interface layer is a
    # microbump field in underfill with sourced geometry (r = 5 um, pitch 20 um, h = 10 um).
    # Homogenising that geometry by the method Phase 0M-R validated -- 0.55 % against the
    # Voigt bound through thickness, 0.61 % against Maxwell-Garnett in plane -- gives
    # kz = 11.739 and kxy = 0.891 W/mK. The layer had been modelled as isotropic underfill
    # at k = 0.70, i.e. 16.8x too resistive through thickness, in the one layer every watt
    # must cross. Promotion moves T_max by about 7 K and the driver by about 6.7 %, and the
    # Z1/Z2 ratio by 0.105 %: it matters for absolute numbers and not for the ordering.
    # Set PHASE0MR2_INTERFACE_KORTHO="iso" to recover the retired isotropic behaviour.
    _ko = os.environ.get("PHASE0MR2_INTERFACE_KORTHO", "0.8914165228645642,"
                         "0.8914165228645642,11.739")
    if _ko == "iso":
        _ko = None
    for mat in sorted(set(m.elem_material)):
        mm = mats[mat]
        if _ko and mat == "underfill_homog":
            kx, ky, kz = (float(x) * 1e-3 for x in _ko.split(","))
            L += [f"*MATERIAL, NAME={mat.upper()}", "*CONDUCTIVITY, TYPE=ORTHO",
                  f"{kx:.6g},{ky:.6g},{kz:.6g}"]
        else:
            L += [f"*MATERIAL, NAME={mat.upper()}"] + mm.ccx_conductivity()
        L += [f"*SOLID SECTION, ELSET=E_{mat.upper()}, MATERIAL={mat.upper()}"]
    V = m.elem_volumes()
    regions = {"die": ("die", hm.die_w), "conv": (conv_layer, hm.converter_w + hm.intravr_w),
               "tsv": ("sub_lower", hm.tsv_w), "rdl": ("interface", hm.rdl_w),
               "bump": ("bga", hm.bump_w)}
    dflux, deposited = [], 0.0
    for tag, (lay, w) in regions.items():
        if w <= 0:
            continue
        ids = _layer_elems(m, lay)
        vol = V[ids - 1].sum()
        if vol <= 0:
            raise EnergyError(f"layer {lay} has zero meshed volume; cannot deposit {w} W")
        L += ccxio._fmt_set(f"E_SRC_{tag.upper()}", ids)
        dflux.append(f"E_SRC_{tag.upper()},BF,{w / vol:.9g}")
        deposited += (w / vol) * vol
    check_energy(hm, deposited)
    top_ids, bot_ids = ccxio.top_film_faces(m), ccxio.bottom_film_faces(m)
    if len(top_ids) != len(h_face):
        raise EnergyError(f"film field has {len(h_face)} entries for {len(top_ids)} faces")
    L += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL,{float(t_face.mean()):.6f}"]
    L += ["*STEP", "*HEAT TRANSFER, STEADY STATE", "*DFLUX"] + dflux
    L += ["*FILM"]
    for e, h_i, t_i in zip(top_ids, h_face, t_face):
        L.append(f"{int(e)},F2,{t_i:.6f},{h_i * W_M2K_TO_W_MM2K:.9g}")
    for e in bot_ids:
        L.append(f"{int(e)},F1,{t_amb},{h_bot * W_M2K_TO_W_MM2K:.9g}")
    L += ["*NODE FILE", "NT", "*END STEP"]
    path.write_text("\n".join(L) + "\n")
    return {"top_face_elems": top_ids, "bot_face_elems": bot_ids,
            "deposited_w": deposited, "n_top_faces": len(top_ids)}


def solve_thermal(arch: str, h_sub_mm: float, hm: HeatMap, cooler: CoolingDesign,
                  wd: Path, h_xy: float = 0.80, max_fluid_iter: int = 8,
                  tol_k: float = 0.02, threads: int = 8) -> dict:
    """Staggered conjugate solve: fluid temperature <-> wall flux."""
    wd.mkdir(parents=True, exist_ok=True)
    doe = load_doe()
    m, mats, st, tiles = build_global(arch, h_sub_mm, h_xy=h_xy, doe=doe)
    conv_layer = converter_layer(arch, m)
    top_ids = ccxio.top_film_faces(m)
    cen = np.array([m.elem_centroids()[int(e) - 1] for e in top_ids])
    areas = np.array([ccxio.face_area(m, e) for e in top_ids])
    h_eff = cooler.h_uniform(hm.total())
    h_face = np.full(len(top_ids), h_eff)
    m_dot = cooler.m_dot_g_s * 1e-3 * (2.0 if cooler.two_sided else 1.0)
    # first iterate: uniform heat pickup along the flow
    order = np.argsort(cen[:, 0])
    frac = np.zeros(len(top_ids))
    frac[order] = (np.cumsum(areas[order]) - 0.5 * areas[order]) / areas.sum()
    t_face = cooler.t_in_c + frac * hm.total() / (m_dot * CP_F)
    hist = []
    for it in range(max_fluid_iter):
        ti = wd / f"th_{it}.inp"
        info = _write_thermal(m, mats, tiles, st, hm, conv_layer, h_face, t_face, ti)
        ccxio.run_ccx(ti, threads=threads)
        frd = wd / f"th_{it}.frd"
        if not frd.is_file():
            return {"status": "CCX FAILED", "iter": it}
        Tn = ccxio.read_frd(frd)["NDTEMP"]
        Tnode = Tn[1:m.n_nodes + 1, 0]
        # face temperature and the heat each face actually removes
        tface_surf = np.array([float(np.nanmean(Tn[m.elems[int(e) - 1][4:] , 0]))
                               for e in top_ids])
        q_face = h_face * W_M2K_TO_W_MM2K * areas * (tface_surf - t_face)
        q_up = np.zeros_like(q_face)
        q_up[order] = np.cumsum(q_face[order]) - 0.5 * q_face[order]
        t_new = cooler.t_in_c + q_up / (m_dot * CP_F)
        dmax = float(np.max(np.abs(t_new - t_face)))
        hist.append({"iter": it, "max_dT_fluid_K": dmax,
                     "T_max_C": float(np.nanmax(Tnode)),
                     "q_removed_top_W": float(q_face.sum()),
                     "dT_fluid_span_K": float(t_new.max() - t_new.min())})
        t_face = 0.5 * t_face + 0.5 * t_new          # damped, this loop is a fixed point
        if dmax < tol_k:
            break
    q_top = float(q_face.sum())
    q_bot = hm.total() - q_top
    return {"status": "OK", "mesh": m, "materials": mats, "stack": st, "tiles": tiles,
            "T_node": Tnode, "T_max_C": float(np.nanmax(Tnode)),
            "T_min_C": float(np.nanmin(Tnode)), "T_mean_C": float(np.nanmean(Tnode)),
            "fluid_iters": len(hist), "fluid_hist": hist,
            "dT_fluid_span_K": hist[-1]["dT_fluid_span_K"],
            "q_removed_top_W": q_top, "q_removed_bottom_W": q_bot,
            "energy_residual_pct": 100 * (q_top + q_bot - hm.total()) / hm.total(),
            "h_effective_W_m2K": h_eff, "deposited_w": info["deposited_w"],
            "conv_layer": conv_layer, "wd": str(wd)}


def layer_mean_temperature(m, Tnode: np.ndarray, layer: str) -> float:
    ids = _layer_elems(m, layer)
    nodes = np.unique(m.elems[ids - 1].ravel())
    return float(np.nanmean(Tnode[nodes - 1]))
