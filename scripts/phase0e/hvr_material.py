"""Phase-0E Sec.12: map HVR electrical footprint onto PHYSICAL material distribution.

Phase 0B/0C/0D modelled the HVR tile as a homogeneous block of `hvr_effective`
(E = 120 GPa, CTE = 6 ppm/K) filling the whole electrical bounding box at a fixed 150 um
thickness. Every mechanical footprint result rests on that. The stack file itself flags it:
"MUST be replaced by the HVR compiler stack height".

The compiler's own area rule is
    A_HVR = max( N*fp_hs , K*fp_ls , K*fp_ind , (N-1)*fp_cap )
i.e. components are VERTICALLY STACKED on separate layers and the tile footprint is set by
the largest layer -- which matches June-2026 ("all VR components are vertically aligned
within a single cell footprint"; "the overall VR footprint is primarily determined by the
low-side switches and the embedded inductors"). Every other layer is therefore only
PARTIALLY filled, and the fill fraction is not constant as the footprint changes.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

# Constituent cards. Silicon is SOURCE_BACKED from configs/phase0b/package_stack.yaml;
# the ceramic and mould cards are declared ASSUMPTION and carried in the uncertainty table.
CONSTITUENTS = {
    "silicon":  {"E": 130000.0, "nu": 0.28, "cte": 2.6e-6,  "k": 130.0,
                 "status": "SOURCE_BACKED", "src": "package_stack.yaml silicon card"},
    "ceramic":  {"E": 110000.0, "nu": 0.30, "cte": 10.0e-6, "k": 3.0,
                 "status": "ASSUMPTION", "src": "X7R BaTiO3 MLCC, no primary source retrieved"},
    "mould":    {"E": 8000.0,  "nu": 0.32, "cte": 30.0e-6, "k": 0.7,
                 "status": "PROVISIONAL", "src": "reuses the underfill_homog card"},
}

# Which constituent each component group is made of.
GROUP_MATERIAL = {"hs_gan": "silicon",     # GaN-on-Si power device
                  "ls_gan": "silicon",
                  "inductor": "silicon",   # the selected part's category IS 'silicon_interposer'
                  "capacitor": "ceramic"}


@dataclass
class TileComposition:
    j_target: float
    a_hvr_mm2: float
    n_layers: int
    group_area_mm2: dict
    fill_by_group: dict
    phi_by_material: dict
    E_eff_mpa: float
    nu_eff: float
    cte_eff: float
    k_eff: float
    component_area_mm2: float
    areal_fill: float
    inductor_height_um: float

    def as_row(self) -> dict:
        d = {k: v for k, v in asdict(self).items()
             if k not in ("group_area_mm2", "fill_by_group", "phi_by_material")}
        d.update({f"area_{k}": v for k, v in self.group_area_mm2.items()})
        d.update({f"fill_{k}": v for k, v in self.fill_by_group.items()})
        d.update({f"phi_{k}": v for k, v in self.phi_by_material.items()})
        return d


def compose(design, j_target: float) -> TileComposition:
    """Physical composition of one compiled HVR design."""
    a = design.arch
    g = {"hs_gan": a.N * design.hs.footprint_mm2,
         "ls_gan": a.K * design.ls.footprint_mm2,
         "inductor": a.K * design.inductor.footprint_mm2,
         "capacitor": (a.N - 1) * design.capacitor.footprint_mm2}
    A = max(g.values())
    n_layers = len(g)

    # Equal layer thickness is the neutral choice: only the inductor height (500 um) is
    # sourced, and GaN / MLCC heights are OPEN. The RATIO between footprints -- which is
    # what drives the footprint trend -- is independent of the common thickness.
    denom = n_layers * A
    phi = {m: 0.0 for m in CONSTITUENTS}
    for grp, area in g.items():
        phi[GROUP_MATERIAL[grp]] += area / denom
    phi["mould"] = max(0.0, 1.0 - sum(v for k, v in phi.items() if k != "mould"))

    E = sum(phi[m] * CONSTITUENTS[m]["E"] for m in phi)
    nu = sum(phi[m] * CONSTITUENTS[m]["nu"] for m in phi)
    # Stiffness-weighted CTE (Levin/Turner form) -- a volume-weighted CTE would overstate
    # the contribution of the compliant mould, which is exactly the phase that cannot
    # transmit the mismatch.
    cte = sum(phi[m] * CONSTITUENTS[m]["E"] * CONSTITUENTS[m]["cte"] for m in phi) / E
    k = sum(phi[m] * CONSTITUENTS[m]["k"] for m in phi)

    return TileComposition(
        j_target=j_target, a_hvr_mm2=A, n_layers=n_layers, group_area_mm2=g,
        fill_by_group={kk: vv / A for kk, vv in g.items()},
        phi_by_material=phi, E_eff_mpa=E, nu_eff=nu, cte_eff=cte, k_eff=k,
        component_area_mm2=sum(g.values()), areal_fill=sum(g.values()) / denom,
        inductor_height_um=design.inductor.height_um)


def homogeneous_reference() -> dict:
    """The Phase-0B/0C/0D `hvr_effective` card, for side-by-side comparison."""
    return {"E": 120000.0, "nu": 0.28, "cte": 6.0e-6, "k": 60.0, "status": "PROVISIONAL"}
