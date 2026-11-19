"""Converter-tier material cards by unit-cell homogenization (TCPMT revision).

WHAT IS REPLACED
  inductor + C_out tier, flying-capacitor tier   `hvr_effective`: k = 60 W/mK isotropic,
        E 120 GPa, CTE 6 ppm/K, flagged "UNSPECIFIED surrogate" (package_stack.yaml). Its
        x0.1 stress test made Z1 and Z2 infeasible under cooling A, so the value matters.
  GaN device tiers                                solid silicon over the whole cell footprint.
WHAT REPLACES IT
  One card per tier, derived from what the tier CONTAINS in the design in force: the die
  count and part of each device tier, the inductors, flying and output capacitors, the
  output-current posts and the encapsulant fill, in the cell of that design. Every number is
  a function of TierContents (die count, dimensions, keep-out, cell size, part counts and
  output current), read from the compiled design and the Z1 config in force
  (TierContents.from_design), so a change of design point re-derives the cards; the 49-cell
  N3K3K_A2 and the 36-cell N4K4K_A2 are both evaluated in main().

METHOD (all tiers)
  conductivity  through the thickness: parallel prisms that span the tier (exact for
                prisms), each prism a SERIES stack of its own layers (die body + solder
                terminal; capacitor mount + body + encapsulant cap); in plane: each component
                in its share of the cell, the classical series-parallel (Kirchhoff/Rayleigh)
                bounds of a rectangular inclusion in a periodic rectangular cell (adiabatic
                planes -> lower, isothermal planes -> upper), averaged over the two in-plane
                directions; the production in-plane value is the midpoint of that bracket.
                Outer bounds: Reuss (series) and Voigt (parallel) over the phase fractions.
  elasticity    Voigt and Reuss over the phase volume fractions; production iso E = Hill
                (their mean), nu = volume mean.
  expansion     iso-strain (Turner, modulus-weighted) and iso-stress (volume mean) bounds;
                production iso CTE = Turner: the stiff phases (Si dies, MLCC ceramic, Cu)
                span the tier and are bonded to continuous RDL above and below, which
                enforces nearly common in-plane strain.
  The FE takes iso E/nu/CTE and orthotropic k (etm.config.Material); the full set with its
  bounds is in the JSON for the mechanical model.

PHASES (sources; status)
  silicon, copper     framework cards, configs/phase0b/package_stack.yaml (SOURCE_BACKED)
  encapsulant         the framework's fill card underfill_homog (k 0.7, E 8 GPa, nu 0.32,
                      CTE 30 ppm/K; PROVISIONAL there) -- the same medium that fills between
                      the cells, so the in-cell and out-of-cell fill are one material
  solder (SAC305)     k 57 W/mK, E 50 GPa, CTE 22 ppm/K (scripts/phase0nw/z2_converter, the
                      framework's attach card); nu 0.35 (ASSUMPTION)
  nickel              k 90.7 W/mK, E 200 GPa, nu 0.31, CTE 13.4 ppm/K (handbook values)
  BaTiO3 X7R/X7T      k 2.6 W/mK (range 2.0-3.5), E 120 GPa (100-150), nu 0.30, CTE
                      10.5 ppm/K (9.5-11.5): base-metal-electrode MLCC dielectric
                      (LITERATURE_TYPICAL; MLCC bodies are quoted at ~10-12 ppm/K)
  TY-M5 core          the inductor paper (Rasheedi et al., inductor-array TCPMT manuscript,
                      Table II) names Taiyo Yuden TY-M5, a METAL COMPOSITE (mu_r 15, B_sat
                      1.25 T) and gives NEITHER its composition NOR its thermal conductivity;
                      no datasheet value is available here. Declared: Fe-based alloy powder
                      in epoxy, metal fraction B_sat(composite)/B_sat(alloy) = 0.70 (0.58-0.80
                      over the paper's Table II alloys with B_sat >= 1.56 T); k 3.0 W/mK
                      (range 1.5-6: the insulated-particle effective-medium bracket); E and
                      CTE from Hill/Turner on alloy 200 GPa, 12 ppm/K and epoxy 3 GPa,
                      60 ppm/K. The rod is ~5 % of the inductor tier: the card is insensitive
                      to it (sensitivity in the JSON).
CONSTRUCTIONS (sources)
  GaN dies            EPC2014C / EPC2057 datasheets, DIE OUTLINE (die A x B, body and solder
                      terminal heights, bar/bump pad dimensions); dies flip-chip on the RDL
                      below, terminal gap filled with the encapsulant; GaN epi not resolved
                      (Si carrier); keep-out 50 um between dies (declared design rule).
  inductor            the inductor paper, Fig. 7 (vertical two-turn two-layer segment: 800 um
                      outer, outer ring 110 um, inner ring 145 um, 20 um turn and layer gaps,
                      two 114-um Cu layers, 250-um opening carrying the shared TY-M5 rod; its
                      stated 5 mOhm DCR is reproduced by these dimensions); its segment
                      fractions are applied to the library inductor envelope (footprint and
                      tier height of the design). Only the outer ring's two vertical legs span
                      the tier: they are its vertical Cu prisms.
  output posts        one rail of the cell output current (the ground return: the inductor's
                      output pin delivers V_out at the tier's top face, per the paper), sized
                      at the framework's intra-VR current density (final_closure_ledger
                      INTRA_J_MAX = 1e8 A/m^2) for the cell output RMS current.
  MLCC                BaTiO3/Ni laminate body with horizontal electrodes (active fraction
                      0.65, Ni 0.25 of the active volume), fired Cu thick-film end
                      terminations 25 um on both W ends (k 250 W/mK by Wiedemann-Franz); the
                      terminations span the part from the RDL below to the RDL above, so they
                      are vertical metal prisms of the tier (a flying capacitor is contacted
                      from both faces: HS tier below, LS tier above). The no-conduction
                      case is reported as kz_without_terminations.

    python tcpmt_converter_cards.py  -> research/tcpmt_revision/converter_cards.json
"""
from __future__ import annotations

import json
import math
import re
import os
import sys
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m", "scripts/phase0f",
           "scripts/phase0i", "scripts/phase0b", "scripts/phase0e", "scripts/phase0dr",
           "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "converter_cards.json"   # campaign hook
INDUCTOR_PAPER = "/home/beams0/SABDELZAHER/Salma_Thesis/HVR/Inductor_Arrays__Rami__Salma__TCPMT_-2.pdf"

# ------------------------------------------------------------------ phases
#: E in MPa, CTE in 1/K, k in W/mK
PHASES = {
    "silicon": {"k": 130.0, "E": 130000.0, "nu": 0.28, "cte": 2.6e-6,
                "source": "configs/phase0b/package_stack.yaml silicon (isotropic check)",
                "status": "SOURCE_BACKED"},
    "copper": {"k": 400.0, "E": 110000.0, "nu": 0.34, "cte": 16.66e-6,
               "source": "configs/phase0b/package_stack.yaml copper", "status": "SOURCE_BACKED"},
    "encapsulant": {"k": 0.7, "E": 8000.0, "nu": 0.32, "cte": 30.0e-6,
                    "source": "configs/phase0b/package_stack.yaml underfill_homog (the "
                              "framework's fill, also between the cells)",
                    "status": "PROVISIONAL"},
    "solder": {"k": 57.0, "E": 50000.0, "nu": 0.35, "cte": 22.0e-6,
               "source": "SAC305; k from z2_converter.K_SOLDER, E/CTE from the column-stiffened "
                         "attach card (z2_converter.vr_attach_material); nu ASSUMPTION",
               "status": "DERIVED"},
    "nickel": {"k": 90.7, "E": 200000.0, "nu": 0.31, "cte": 13.4e-6,
               "source": "handbook values (CRC Handbook of Chemistry and Physics; ASM)",
               "status": "SOURCE_BACKED"},
    "termination": {"k": 250.0, "E": 110000.0, "nu": 0.34, "cte": 16.66e-6,
                    "range": {"k": [0.0, 400.0]},
                    "source": "fired Cu thick-film MLCC end termination: k from Wiedemann-"
                              "Franz at a typical fired thick-film resistivity ~2.7 uOhm cm "
                              "(bulk Cu 1.7 -> 400 W/mK); E/CTE of the copper card",
                    "status": "DERIVED"},
    "batio3": {"k": 2.6, "E": 120000.0, "nu": 0.30, "cte": 10.5e-6,
               "range": {"k": [2.0, 3.5], "E": [100000.0, 150000.0], "cte": [9.5e-6, 11.5e-6]},
               "source": "BaTiO3-based X7R/X7T MLCC dielectric, literature-typical values "
                         "(MLCC bodies are quoted at ~10-12 ppm/K)",
               "status": "LITERATURE_TYPICAL"},
    "epoxy": {"k": 0.2, "E": 3000.0, "nu": 0.35, "cte": 60.0e-6,
              "source": "unfilled epoxy binder, typical", "status": "LITERATURE_TYPICAL"},
    "fe_alloy": {"k": 20.0, "E": 200000.0, "nu": 0.29, "cte": 12.0e-6,
                 "range": {"k": [9.0, 80.0]},
                 "source": "Fe-based soft-magnetic alloy powder (Fe-Si/Fe-Si-Cr/amorphous "
                           "class; pure Fe 80 W/mK, amorphous ~9 W/mK)",
                 "status": "LITERATURE_TYPICAL"},
}
#: QFN body (EPC2366, count neighbour M = 25): a 200-um Cu exposed pad, ~250 um of die and a
#: 200-um mould cap over 45 % of the package, mould elsewhere (k 0.9 W/mK, E 20 GPa, CTE
#: 10 ppm/K: filled epoxy mould compound) -- DECLARED construction, used only by that design
_QFN_K = 0.45 * 650.0 / (200.0 / 400.0 + 250.0 / 130.0 + 200.0 / 0.9) + 0.55 * 0.9
PHASES["qfn_body"] = {"k": _QFN_K, "E": 25000.0, "nu": 0.30, "cte": 9.0e-6,
                      "source": "DECLARED QFN construction: Cu pad 200 um + Si die 250 um + "
                                "mould 200 um over 45 % of the package, mould compound "
                                "(k 0.9 W/mK) elsewhere; E/CTE of a filled mould compound with "
                                "the pad and die", "status": "ASSUMPTION"}
#: TY-M5 metal composite, declared (the paper gives no composition or k; see docstring)
TYM5 = {"metal_fraction": 0.70, "metal_fraction_range": [0.58, 0.80],
        "k": 3.0, "k_range": [1.5, 6.0], "B_sat_T": 1.25, "mu_r": 15.0,
        "source": "inductor paper Table II (mu_r 15, B_sat 1.25 T, Taiyo Yuden TY-M5); "
                  "metal fraction from B_sat(composite)/B_sat(alloy) over the Table II "
                  "alloys with B_sat >= 1.56 T; k DECLARED within the insulated-particle "
                  "effective-medium bracket (Hashin-Shtrikman lower ~1.5 W/mK at 0.70)",
        "status": "ASSUMPTION"}

# ------------------------------------------------------------------ constructions
#: EPC datasheets, DIE OUTLINE (micrometres): die A x B, body and terminal heights, pads
DEVICES = {
    "EPC2014C": {"die_mm": (1.702, 1.087), "body_um": 585.0, "terminal_um": 100.0,
                 "overall_um": 685.0,
                 "pads_um": [(200.0, 834.0)] * 3 + [(200.0, 316.0)] * 2,
                 "terminal": "solder bars (SAC305 class)",
                 "source": "EPC2014C datasheet, DIE OUTLINE: A 1702, B 1087; bars 3-5 "
                           "200 x 834 um, pads 1-2 200 x 316 um; terminal 100 +/- 20 um; "
                           "overall 685 um (815 max)"},
    "EPC2057": {"die_mm": (1.500, 1.200), "body_um": 518.0, "terminal_um": 120.0,
                "overall_um": 638.0,
                "pads_um": [(250.0, 300.0), (250.0, 525.0), (250.0, 1050.0), (250.0, 1050.0)],
                "terminal": "solder bumps",
                "source": "EPC2057 datasheet, DIE OUTLINE: A 1500, B 1200; pad 1 250 x 300, "
                          "pad 2 250 x 525, pads 3-4 250 x 1050 um; die 518 +/- 25, bump "
                          "120 +/- 12 um; overall 638 um"},
}
#: TCPMT round 3: the parts of the decided design point and of the count neighbours. Overall
#: heights from HVR_epc_device_data.json (datasheet Side View, the engine's stack heights);
#: the land/bump pattern under the die is not tabulated here, so the solder fraction is
#: DECLARED (between the EPC2014C outline's 0.34 and the EPC2057 outline's 0.41).
DEVICES.update({
    "EPC2055": {"die_mm": (2.500, 1.500), "body_um": 518.0, "terminal_um": 120.0,
                "overall_um": 638.0, "pads_um": [(250.0, 1000.0)] * 6,
                "terminal": "solder lands (LGA)", "status": "ASSUMPTION (land pattern)",
                "source": "EPC-Product-Table: LGA 2.5 x 1.5 mm; HVR_epc_device_data.json: "
                          "518 +/- 25 die + 120 +/- 12 bump = 638 um; land pattern DECLARED "
                          "as six 250 x 1000-um lands (40 % of the die)"},
    "EPC2090": {"die_mm": (2.300, 1.450), "body_um": 518.0, "terminal_um": 88.0,
                "overall_um": 606.0, "pads_um": [(250.0, 1000.0)] * 5,
                "terminal": "Cu pillar + solder bumps", "status": "ASSUMPTION (bump pattern)",
                "source": "EPC-Product-Table: BGA 2.3 x 1.45 mm; HVR_epc_device_data.json: "
                          "518 die + 50 Cu + 3 Ni + solder = 606 um; bump fraction DECLARED "
                          "(37 % of the die, solder card for the whole terminal)"},
    # a packaged QFN: the die sits on an exposed Cu pad under a mould cap, so the vertical path
    # through the part is pad + die + mould, not a bare die (body phase 'qfn_body' below)
    "EPC2366": {"die_mm": (3.300, 2.600), "body_um": 650.0, "terminal_um": 50.0,
                "overall_um": 700.0, "pads_um": [(3300.0, 2600.0 * 0.55)],
                "body_phase": "qfn_body", "terminal": "QFN exposed pad + leads (55 %)",
                "status": "ASSUMPTION (package construction)",
                "source": "EPC-Product-Table: QFN 3.3 x 2.6 mm; HVR_epc_device_data.json: "
                          "A = 0.70 mm; construction DECLARED (qfn_body)"},
})
KEEPOUT_UM = 50.0                    # declared die-to-die keep-out (design rule)
#: inductor paper, Fig. 7 (micrometres): one vertical two-turn two-layer segment
IND_SEGMENT = {"outer_um": 800.0, "ring_outer_w_um": 110.0, "ring_inner_w_um": 145.0,
               "turn_gap_um": 20.0, "layer_um": 114.0, "layer_gap_um": 20.0,
               "segment_gap_um": 20.0, "opening_um": 250.0, "dcr_stated_mohm": 5.0,
               "source": "inductor paper Fig. 7 (dimensions and the 5 mOhm DCR) and Fig. 4 "
                         "(five-segment section, 20-um spacing, shared rod)"}
#: MLCC construction (declared, typical of base-metal-electrode parts)
MLCC = {"active_fraction": 0.65, "ni_in_active": 0.25, "termination_um": 25.0,
        "termination_um_range": [15.0, 40.0], "LW_ratio": 1.6,
        "source": "BME-MLCC construction: ~1-um Ni electrodes between ~3-um BaTiO3 layers "
                  "(Ni 0.25 of the active volume), cover/margins 0.35 of the body; Cu thick-"
                  "film end terminations 15-40 um", "status": "ASSUMPTION"}
#: the rated 0603 flying capacitor of case A1 (research/tcpmt_revision/flying_caps.json)
A1_PART = {"part": "GRM188D71H105KE01", "L_mm": 1.6, "W_mm": 0.8, "T_nom_mm": 0.8,
           "T_max_mm": 1.0, "mount_um": 30.0}
COUT_MOUNT_UM = 20.0                 # C_out part <= 480 um in the 500-um tier
FLY_A0_UM = 100.0


# ------------------------------------------------------------------ tier contents
@dataclass(frozen=True)
class TierContents:
    """What the converter tiers of ONE cell contain, for one design."""
    label: str
    n_cells: int
    cell_side_mm: float
    i_out_rms_a: float
    hs_part: str
    n_hs: int
    ls_part: str
    n_ls: int
    n_ind: int
    ind_footprint_mm2: float
    n_cfly: int
    cfly_footprint_mm2: float
    n_cout: int
    cout_footprint_mm2: float
    hs_um: float
    ls_um: float
    ind_um: float
    cfly_um: float = FLY_A0_UM
    keepout_um: float = KEEPOUT_UM
    n_cfly_a1: int | None = None
    source: str = ""

    @property
    def cell_area_mm2(self) -> float:
        return self.cell_side_mm ** 2

    @staticmethod
    def from_design(path=None) -> "TierContents":
        """The design in force: compiled design (counts, parts, footprints, output current)
        and the Z1 config in force (cell side, tier heights)."""
        import yaml
        import z1_design as Z1D
        import replay_production as RPX
        d = RPX.compiled_design()
        cfg = yaml.safe_load(Z1D.config_path(path).read_text())
        tiers = {t["name"]: float(t["um"]) for t in cfg["converter"]["tiers_from_substrate_upward"]}

        def th(prefix, default):
            return next((u for n, u in tiers.items() if n.startswith(prefix)), default)
        if Z1D.is_default(path):
            import rms_currents as RMS
            i_rms = float(RMS.cell_currents()["i_cell_out_rms_a"])
        else:
            i_rms = float(d.i_out_a)
        arch = d.arch
        return TierContents(
            label=f"{d.label} ({Z1D.n_vr(path)} cells)", n_cells=int(Z1D.n_vr(path)),
            cell_side_mm=float(cfg["converter"]["cell_side_mm"]), i_out_rms_a=i_rms,
            hs_part=d.hs.part_number, n_hs=int(arch.K), ls_part=d.ls.part_number,
            n_ls=int(arch.K), n_ind=int(arch.K),
            ind_footprint_mm2=float(d.inductor.footprint_mm2), n_cfly=int(arch.N) - 1,
            cfly_footprint_mm2=float(d.capacitor.footprint_mm2), n_cout=1,
            cout_footprint_mm2=float(d.capacitor.footprint_mm2),
            hs_um=th("gan_hs", 685.0), ls_um=th("gan_ls", 638.0),
            ind_um=th("inductor", 500.0), cfly_um=th("flying_caps", FLY_A0_UM),
            source=f"replay_production.compiled_design() + {Z1D.config_path(path).name}")


# ------------------------------------------------------------------ homogenization helpers
def voigt(fr: dict, prop: str) -> float:
    return sum(f * PHASES[p][prop] if isinstance(p, str) else f * p[prop] for p, f in fr)


def _ph(p):
    return PHASES[p] if isinstance(p, str) else p


def mix_bounds(fr):
    """fr: [(phase or dict, volume fraction)], fractions summing to 1."""
    tot = sum(f for _, f in fr)
    if abs(tot - 1.0) > 1e-9:
        raise ValueError(f"volume fractions sum to {tot}")
    kV = sum(f * _ph(p)["k"] for p, f in fr)
    kR = 1.0 / sum(f / _ph(p)["k"] for p, f in fr)
    EV = sum(f * _ph(p)["E"] for p, f in fr)
    ER = 1.0 / sum(f / _ph(p)["E"] for p, f in fr)
    nu = sum(f * _ph(p)["nu"] for p, f in fr)
    aT = sum(f * _ph(p)["E"] * _ph(p)["cte"] for p, f in fr) / EV
    aV = sum(f * _ph(p)["cte"] for p, f in fr)
    return {"k_voigt": kV, "k_reuss": kR, "E_voigt": EV, "E_reuss": ER, "E_hill": 0.5 * (EV + ER),
            "nu_mean": nu, "cte_turner": aT, "cte_volume": aV}


def series(layers):
    """Through-thickness conductivity of [(thickness, k)] in series."""
    h = sum(t for t, _ in layers)
    return h / sum(t / k for t, k in layers if t > 0)


def rect_cell_bounds(k_i, a, b, k_m, area):
    """Series-parallel bounds on the in-plane conductivity of a periodic array of a x b
    rectangles (k_i) in matrix k_m, one per cell of `area`, the cell similar to the inclusion
    plus a uniform gap g: (a+g)(b+g) = area (g = 0 if the inclusion fills its share).
    Returns (lower, upper), averaged over the two in-plane directions."""
    g = max(0.0, (-(a + b) + math.sqrt((a + b) ** 2 - 4 * (a * b - area))) / 2.0)
    lo = up = 0.0
    for lx, ly in ((a, b), (b, a)):
        Lx, Ly = lx + g, ly + g
        # adiabatic planes parallel to the flow: strips conduct in parallel (lower bound)
        k_strip = Lx / (lx / k_i + (Lx - lx) / k_m) if Lx > lx else k_i
        lo += (ly / Ly) * k_strip + (1 - ly / Ly) * k_m
        # isothermal planes normal to the flow: slices conduct in series (upper bound)
        k_slice = (ly * k_i + (Ly - ly) * k_m) / Ly
        up += Lx / (lx / k_slice + (Lx - lx) / k_m) if Lx > lx else k_slice
    return lo / 2.0, up / 2.0, g


def maxwell_garnett(k_i, k_m, f, dim=3):
    """Isolated inclusions (lower Hashin-Shtrikman for k_i > k_m); dim 2: aligned cylinders."""
    if dim == 2:
        return k_m * ((k_i + k_m) + f * (k_i - k_m)) / ((k_i + k_m) - f * (k_i - k_m))
    b = (k_i - k_m) / (k_i + 2 * k_m)
    return k_m * (1 + 2 * b * f) / (1 - b * f)


def card(name, kx, ky, kz, mech, bounds, provenance, extra=None):
    """A framework material card (etm.config.Material conventions: MPa, 1/K, W/mK)."""
    c = {"status": "DERIVED", "elastic_type": "iso",
         "E": {"value": mech["E_hill"], "status": "DERIVED"},
         "nu": {"value": mech["nu_mean"], "status": "DERIVED"},
         "cte": {"value": mech["cte_turner"], "status": "DERIVED"},
         "k": {"value": kz, "status": "DERIVED"},
         "k_ortho": {"value": [kx, ky, kz], "status": "DERIVED"},
         "provenance": provenance,
         "derivation": {"script": "scripts/tcpmt_converter_cards.py", "card": name,
                        "bounds": bounds,
                        "mechanical": {"E_voigt_MPa": mech["E_voigt"],
                                       "E_reuss_MPa": mech["E_reuss"],
                                       "E_hill_MPa": mech["E_hill"], "nu_mean": mech["nu_mean"],
                                       "cte_turner_per_K": mech["cte_turner"],
                                       "cte_volume_per_K": mech["cte_volume"],
                                       "production": "iso E = Hill, nu = volume mean, "
                                                     "CTE = Turner (iso-strain)"}}}
    if extra:
        c["derivation"].update(extra)
    return c


# ------------------------------------------------------------------ packing check
def die_packing(n, a_mm, b_mm, keepout_um, cell_side_mm):
    """Smallest square cell holding n dies a x b with the keep-out g between dies and g/2 to
    the cell edge (so dies of neighbouring cells are g apart): row, L (2+1), 2x2 grid and
    pinwheel layouts."""
    g = keepout_um * 1e-3
    A, B = max(a_mm, b_mm) + g, min(a_mm, b_mm) + g
    lay = {"row": max(n * B, A)}
    if n == 1:
        lay = {"single": A}
    elif n == 2:
        lay.update({"side_by_side": max(2 * B, A)})
    elif n == 3:
        lay.update({"L_2_plus_1": max(A + B, 2 * B), "grid_2x2": max(2 * A, 2 * B)})
    elif n == 4:
        lay.update({"grid_2x2": 2 * A, "pinwheel": A + B})
    else:
        c = math.ceil(math.sqrt(n))
        lay.update({"grid": c * A})
    best = min(lay, key=lay.get)
    return {"n": n, "die_mm": [a_mm, b_mm], "keepout_um": keepout_um,
            "layouts_side_mm": lay, "best_layout": best, "min_side_mm": lay[best],
            "cell_side_mm": cell_side_mm, "fits": lay[best] <= cell_side_mm + 1e-9,
            "die_area_fraction": n * a_mm * b_mm / cell_side_mm ** 2}


# ------------------------------------------------------------------ tier cards
def gan_tier(tc: TierContents, which: str, height_um: float | None = None):
    part = tc.hs_part if which == "hs" else tc.ls_part
    n = tc.n_hs if which == "hs" else tc.n_ls
    dev = DEVICES[part]
    a, b = dev["die_mm"]
    H = float(height_um or (tc.hs_um if which == "hs" else tc.ls_um))
    t_term = dev["terminal_um"]
    t_body = H - t_term
    A_cell = tc.cell_area_mm2
    pack = die_packing(n, a, b, tc.keepout_um, tc.cell_side_mm)
    # vertical prisms: the dies' TOTAL cross-section in the drawn cell (cell-preserving)
    f_d = min(1.0, n * a * b / A_cell)
    f_s = sum(w * l for w, l in dev["pads_um"]) * 1e-6 / (a * b)
    si, enc, sol = PHASES["silicon"], PHASES["encapsulant"], PHASES["solder"]
    kz_body = f_d * si["k"] + (1 - f_d) * enc["k"]
    kz_term_die = f_s * sol["k"] + (1 - f_s) * enc["k"]
    kz_term = f_d * kz_term_die + (1 - f_d) * enc["k"]
    kz = series([(t_body, kz_body), (t_term, kz_term)])
    # in plane: each die in its share of the cell; when the drawn cell is below the packed
    # minimum, the declared keep-out sets the gap (the share the dies cannot have)
    area_share = A_cell / n
    g_keep = tc.keepout_um * 1e-3
    if not pack["fits"]:
        area_share = (a + g_keep) * (b + g_keep)
    lo, up, gap = rect_cell_bounds(si["k"], a, b, enc["k"], area_share)
    k_in_body = 0.5 * (lo + up)
    k_in_bump = 0.5 * ((f_s * sol["k"] + (1 - f_s) * enc["k"])
                       + maxwell_garnett(sol["k"], enc["k"], f_s, dim=2))
    k_in_term = f_d * k_in_bump + (1 - f_d) * enc["k"]
    k_in = (t_body * k_in_body + t_term * k_in_term) / H
    fr = [("silicon", f_d * t_body / H), ("solder", f_d * f_s * t_term / H)]
    fr.append(("encapsulant", 1.0 - sum(f for _, f in fr)))
    mech = mix_bounds(fr)
    bounds = {"kz_reuss": mech["k_reuss"], "kz_voigt": mech["k_voigt"],
              "kz_estimate": kz, "kxy_series_parallel": [
                  (t_body * lo + t_term * k_in_term) / H, (t_body * up + t_term * k_in_term) / H],
              "kxy_reuss": mech["k_reuss"], "kxy_voigt": mech["k_voigt"]}
    extra = {"tier": f"gan_{which}", "part": part, "dies_per_cell": n, "tier_um": H,
             "body_um": t_body, "terminal_um": t_term, "die_area_fraction": f_d,
             "solder_fraction_under_die": f_s, "gap_um_in_plane": gap * 1e3,
             "packing": pack, "volume_fractions": dict((p, f) for p, f in fr),
             "kz_layers": {"body": kz_body, "terminal": kz_term},
             "packing_note": ("drawn cell below the packed minimum: vertical prisms keep the "
                              "dies' total cross-section in the drawn cell; the in-plane gap "
                              "is the declared keep-out" if not pack["fits"] else
                              "packing feasible in the drawn cell")}
    return card(f"conv_gan_{which}", k_in, k_in, kz, mech, bounds,
                f"{n} x {part} dies ({dev['source']}) in the encapsulant, cell "
                f"{tc.cell_side_mm:.4f} mm ({tc.label})", extra)


def mlcc_body(ph_bt=None):
    """BaTiO3/Ni laminate body, electrodes horizontal: (k_in, k_z, phase dict)."""
    bt = dict(PHASES["batio3"]) if ph_bt is None else ph_bt
    ni = PHASES["nickel"]
    fa, fn = MLCC["active_fraction"], MLCC["ni_in_active"]
    phi = fa * fn
    k_in = fa * (fn * ni["k"] + (1 - fn) * bt["k"]) + (1 - fa) * bt["k"]
    k_z = 1.0 / (fa * (fn / ni["k"] + (1 - fn) / bt["k"]) + (1 - fa) / bt["k"])
    m = mix_bounds([(ni, phi), (bt, 1 - phi)])
    body = {"k": k_z, "E": m["E_voigt"], "nu": m["nu_mean"], "cte": m["cte_turner"],
            "k_in": k_in, "ni_fraction": phi}
    return body


def mlcc_tier(tc: TierContents, n_parts, L_mm, W_mm, H_um, mount_um, name, label,
              t_term_um=None, k_tym5=None):
    """MLCCs in the encapsulant: parallel prisms of (i) body, (ii) Cu terminations, (iii)
    encapsulant; each prism a series of its mount (solder), part and encapsulant cap."""
    t_term = (MLCC["termination_um"] if t_term_um is None else t_term_um) * 1e-3
    A_cell = tc.cell_area_mm2
    T_part = H_um - mount_um
    body = mlcc_body()
    enc, cu, sol = PHASES["encapsulant"], PHASES["termination"], PHASES["solder"]
    a_term = n_parts * 2 * W_mm * t_term
    a_body = n_parts * (L_mm - 2 * t_term) * W_mm
    a_enc = A_cell - a_term - a_body
    if a_enc < -1e-9:
        raise ValueError(f"{name}: {n_parts} parts {L_mm} x {W_mm} mm exceed the "
                         f"{A_cell:.3f} mm^2 cell")
    lay_b = [(mount_um, sol["k"] if mount_um > 0 else enc["k"]), (T_part, body["k"])]
    lay_t = [(mount_um, sol["k"]), (T_part, cu["k"])]
    kz_b, kz_t = series([x for x in lay_b if x[0] > 0]), series([x for x in lay_t if x[0] > 0])
    kz = (a_body * kz_b + a_term * kz_t + a_enc * enc["k"]) / A_cell
    kz_no_term = (a_body * kz_b + (a_term + a_enc) * enc["k"]) / A_cell
    k_part_in = (body["k_in"] * a_body + cu["k"] * a_term) / (a_body + a_term)
    lo, up, gap = rect_cell_bounds(k_part_in, L_mm, W_mm, enc["k"], A_cell / n_parts)
    k_in = 0.5 * (lo + up)
    hfac = T_part / H_um
    mf = mount_um / H_um
    fr = [(body, a_body / A_cell * hfac), ("termination", a_term / A_cell * hfac),
          ("solder", (a_body + a_term) / A_cell * mf)]
    fr.append(("encapsulant", 1.0 - sum(f for _, f in fr)))
    mech = mix_bounds(fr)
    bounds = {"kz_reuss": mech["k_reuss"], "kz_voigt": mech["k_voigt"],
              "kz_estimate": kz, "kz_without_terminations": kz_no_term,
              "kxy_series_parallel": [lo, up], "kxy_reuss": mech["k_reuss"],
              "kxy_voigt": mech["k_voigt"]}
    extra = {"tier": name, "parts_per_cell": n_parts, "part_mm": [L_mm, W_mm, T_part / 1e3],
             "tier_um": H_um, "mount_um": mount_um, "termination_um": t_term * 1e3,
             "area_fractions": {"body": a_body / A_cell, "terminations": a_term / A_cell,
                                "encapsulant": a_enc / A_cell},
             "mlcc_body": body, "gap_um_in_plane": gap * 1e3,
             "volume_fractions": {("mlcc_body" if isinstance(p, dict) else p): f
                                  for p, f in fr}}
    return card(name, k_in, k_in, kz, mech, bounds, f"{label} ({tc.label})", extra)


def inductor_envelope(k_core=None):
    """The inductor body from the paper's Fig. 7 segment: (kz, k_in_x, k_in_y, fractions)."""
    s = IND_SEGMENT
    D, w1, w2, gt = s["outer_um"], s["ring_outer_w_um"], s["ring_inner_w_um"], s["turn_gap_um"]
    tl, gl, gs, op = s["layer_um"], s["layer_gap_um"], s["segment_gap_um"], s["opening_um"]
    pitch_y = 2 * tl + gl + gs
    inner_outer = D - 2 * (w1 + gt)                    # outer edge of the inner ring
    a_ring1 = D ** 2 - (D - 2 * w1) ** 2
    a_ring2 = inner_outer ** 2 - op ** 2
    V = D * D * pitch_y
    v_cu = (a_ring1 + a_ring2) * tl
    v_rod = op * op * pitch_y
    v_leg = 2 * w1 * tl * D                            # outer ring vertical legs: full height
    f_cu, f_rod, f_leg = v_cu / V, v_rod / V, v_leg / V
    f_fill = 1.0 - f_cu - f_rod
    # DCR check of the dimensions against the paper's stated 5 mOhm (rho_Cu 1.72e-8)
    l1, l2 = 4 * (D - w1), 4 * (inner_outer - w2)
    dcr = 1.72e-8 * (l1 * 1e-6 / (w1 * tl * 1e-12) + l2 * 1e-6 / (w2 * tl * 1e-12)) * 1e3
    kc = TYM5["k"] if k_core is None else k_core
    enc, cu = PHASES["encapsulant"], PHASES["copper"]
    # the rest (non-spanning Cu, rod, fill): isolated inclusions in the fill (two-phase MG
    # generalised: sum of beta_i f_i)
    rest = 1.0 - f_leg
    fc_r, fr_r = (f_cu - f_leg) / rest, f_rod / rest
    bc = (cu["k"] - enc["k"]) / (cu["k"] + 2 * enc["k"])
    br = (kc - enc["k"]) / (kc + 2 * enc["k"])
    sb = bc * fc_r + br * fr_r
    k_rest = enc["k"] * (1 + 2 * sb) / (1 - sb)
    kz = f_leg * cu["k"] + rest * k_rest
    kx = kz                                            # ring symmetric in its own plane
    # across the segments (rod axis): every path crosses >= one 114-um fill layer and two
    # 20-um gaps; the rod runs through in parallel
    ky = (1 - op ** 2 / D ** 2) * series([(tl, cu["k"]), (tl + gl + gs, enc["k"])]) \
        + (op ** 2 / D ** 2) * kc
    tym5 = tym5_card(kc)
    fr = [("copper", f_cu), (tym5, f_rod), ("encapsulant", f_fill)]
    return {"kz": kz, "kx": kx, "ky": ky, "k_in_orientation_avg": math.sqrt(kx * ky),
            "fractions": {"copper": f_cu, "copper_spanning_legs": f_leg, "tym5_rod": f_rod,
                          "fill": f_fill}, "dcr_from_dimensions_mohm": dcr,
            "mix": mix_bounds(fr), "tym5": tym5}


def tym5_card(k_core=None):
    fm = TYM5["metal_fraction"]
    m = mix_bounds([("fe_alloy", fm), ("epoxy", 1 - fm)])
    return {"k": TYM5["k"] if k_core is None else k_core, "E": m["E_hill"],
            "nu": m["nu_mean"], "cte": m["cte_turner"],
            "bounds": {"k_HS_lower": maxwell_garnett(PHASES["fe_alloy"]["k"],
                                                     PHASES["epoxy"]["k"], fm),
                       "E_voigt": m["E_voigt"], "E_reuss": m["E_reuss"],
                       "cte_volume": m["cte_volume"]}}


def ind_cout_tier(tc: TierContents, height_um=None, k_core=None, j_post=None,
                  post_rails=1):
    import final_closure_ledger as FL
    H = float(height_um or tc.ind_um)
    A_cell = tc.cell_area_mm2
    ind = inductor_envelope(k_core)
    J = FL.INTRA_J_MAX if j_post is None else j_post
    a_post = post_rails * tc.i_out_rms_a / J * 1e6        # mm^2
    a_ind = tc.n_ind * tc.ind_footprint_mm2
    # C_out: one MLCC body of the library footprint (L/W 1.6), mounted, <= H - mount tall
    L = math.sqrt(tc.cout_footprint_mm2 * MLCC["LW_ratio"])
    W = tc.cout_footprint_mm2 / L
    t_term = MLCC["termination_um"] * 1e-3
    body = mlcc_body()
    enc, cu, sol = PHASES["encapsulant"], PHASES["copper"], PHASES["solder"]
    a_ct = tc.n_cout * 2 * W * t_term
    a_cb = tc.n_cout * tc.cout_footprint_mm2 - a_ct
    a_enc = A_cell - a_ind - a_post - a_ct - a_cb
    if a_enc < -1e-9:
        raise ValueError(f"inductor tier over-full: {a_ind + a_post + a_ct + a_cb:.3f} mm^2 "
                         f"in a {A_cell:.3f} mm^2 cell")
    T_part = H - COUT_MOUNT_UM
    term = PHASES["termination"]
    kz_cb = series([(COUT_MOUNT_UM, sol["k"]), (T_part, body["k"])])
    kz_ct = series([(COUT_MOUNT_UM, sol["k"]), (T_part, term["k"])])
    kz = (a_ind * ind["kz"] + a_post * cu["k"] + a_cb * kz_cb + a_ct * kz_ct
          + a_enc * enc["k"]) / A_cell
    # in plane: each component in its area share of the cell (series-parallel midpoint)
    comps = [(ind["k_in_orientation_avg"], math.sqrt(tc.ind_footprint_mm2),
              math.sqrt(tc.ind_footprint_mm2), a_ind, tc.n_ind),
             ((body["k_in"] * a_cb + term["k"] * a_ct) / (a_cb + a_ct), L, W,
              a_cb + a_ct, tc.n_cout),
             (cu["k"], math.sqrt(a_post), math.sqrt(a_post), a_post, 1)]
    a_comp = sum(c[3] for c in comps)
    lo = up = 0.0
    for k_i, a_, b_, area, n in comps:
        share = A_cell * area / a_comp / n
        l_, u_, _ = rect_cell_bounds(k_i, a_, b_, enc["k"], share)
        lo += area / a_comp * l_
        up += area / a_comp * u_
    k_in = 0.5 * (lo + up)
    hf, mf = T_part / H, COUT_MOUNT_UM / H
    tym5 = ind["tym5"]
    fi = ind["fractions"]
    fr = [("copper", (a_ind * fi["copper"] + a_post) / A_cell),
          ("termination", a_ct * hf / A_cell),
          (tym5, a_ind * fi["tym5_rod"] / A_cell),
          (body, a_cb * hf / A_cell),
          ("solder", (a_cb + a_ct) * mf / A_cell)]
    fr.append(("encapsulant", 1.0 - sum(f for _, f in fr)))
    mech = mix_bounds(fr)
    bounds = {"kz_reuss": mech["k_reuss"], "kz_voigt": mech["k_voigt"], "kz_estimate": kz,
              "kxy_series_parallel": [lo, up], "kxy_reuss": mech["k_reuss"],
              "kxy_voigt": mech["k_voigt"]}
    extra = {"tier": "inductor_plus_cout", "tier_um": H,
             "area_fractions": {"inductors": a_ind / A_cell, "posts": a_post / A_cell,
                                "cout_body": a_cb / A_cell, "cout_terminations": a_ct / A_cell,
                                "encapsulant": a_enc / A_cell},
             "posts": {"rails": post_rails, "I_rms_A": tc.i_out_rms_a, "J_A_m2": J,
                       "area_mm2": a_post},
             "inductor_envelope": {k: v for k, v in ind.items() if k not in ("mix", "tym5")},
             "tym5": tym5, "cout_part_mm": [L, W, T_part / 1e3],
             "volume_fractions": {(("tym5" if "bounds" in p else "mlcc_body")
                                   if isinstance(p, dict) else p): f for p, f in fr}}
    return card("conv_ind_cout", k_in, k_in, kz, mech, bounds,
                f"{tc.n_ind} inductors (TY-M5 rod, Cu windings: inductor paper Fig. 7), "
                f"{tc.n_cout} C_out MLCC, output-current posts, encapsulant ({tc.label})",
                extra)


def cards_for(tc: TierContents, cfly_a1_um=None, heights=None, strict=True):
    """Every converter-tier card of one design. heights: tier name prefix -> um override.
    strict=False omits a card whose contents do not fit the cell (a design that carries
    those parts in another tier); a tier that needs an omitted card fails at the build."""
    heights = heights or {}
    h_a1 = 1030.0 if cfly_a1_um is None else float(cfly_a1_um)
    L0 = math.sqrt(tc.cfly_footprint_mm2 * MLCC["LW_ratio"])
    makers = {
        "conv_gan_hs": lambda: gan_tier(tc, "hs", heights.get("gan_hs")),
        "conv_gan_ls": lambda: gan_tier(tc, "ls", heights.get("gan_ls")),
        "conv_cfly_a0": lambda: mlcc_tier(
            tc, tc.n_cfly, L0, tc.cfly_footprint_mm2 / L0,
            float(heights.get("flying_caps", tc.cfly_um)), 0.0, "conv_cfly_a0",
            f"A0: {tc.n_cfly} thin embedded MLCC flying capacitors of the library "
            f"footprint {tc.cfly_footprint_mm2} mm^2"),
        "conv_ind_cout": lambda: ind_cout_tier(tc, heights.get("inductor")),
        "conv_cfly_a1": lambda: mlcc_tier(
            tc, tc.n_cfly_a1 or tc.n_cfly, A1_PART["L_mm"], A1_PART["W_mm"], h_a1,
            A1_PART["mount_um"], "conv_cfly_a1",
            f"A1: {tc.n_cfly_a1 or tc.n_cfly} x Murata {A1_PART['part']} (0603) per cell, "
            f"{h_a1:.0f}-um tier")}
    out = {}
    for name, make in makers.items():
        try:
            out[name] = make()
        except ValueError:
            if strict:
                raise
    return out


# ------------------------------------------------------------------ mixed tiers (round 3)
#: the rated 0603 flying capacitor of the decided design (Murata GRM188D72A105KE01): 1.6 x
#: 0.8 mm body, 0.8 mm nominal thickness; the DSE stacks it at 1000 um (0.8 mm + 0.2 mm
#: tolerance margin), so its prism is a 30-um solder mount, the nominal body and an
#: encapsulant cap up to the tier top. A thin part (the 100-um sensitivity) fills its tier.
CF_0603 = {"L_mm": 1.6, "W_mm": 0.8, "T_nom_um": 800.0, "mount_um": 30.0}
#: output-post current density: the framework's intra-VR density (final_closure_ledger.
#: INTRA_J_MAX, checked equal by the tests); a constant here so the cards import nothing of
#: the package chain
J_POST = 1.0e8


@dataclass(frozen=True)
class MixedContents:
    """One cell of a design with mixed tiers (configs/design_points.yaml)."""
    label: str
    n_cells: int
    cell_side_mm: float
    i_out_rms_a: float
    hs_part: str
    ls_part: str
    ind_footprint_mm2: float
    ind_um: float
    cf_um: float
    n_ind_total: int
    keepout_um: float = KEEPOUT_UM

    @property
    def cell_area_mm2(self) -> float:
        return self.cell_side_mm ** 2

    @staticmethod
    def from_record(key=None) -> "MixedContents":
        import design_record as DR
        d = DR.get(key)
        des = DR.compiled(key)
        import rms_currents as RMS
        try:
            i_rms = float(RMS.cell_currents()["i_cell_out_rms_a"]) if DR.name(key) == \
                DR.name() else float(des.i_out_a)
        except Exception:                                   # noqa: BLE001
            i_rms = float(des.i_out_a)
        return MixedContents(
            label=f"{d['tag']} ({d['n_vr']} cells, design {DR.name(key)})",
            n_cells=int(d["n_vr"]), cell_side_mm=float(d["cell_side_mm"]), i_out_rms_a=i_rms,
            hs_part=d["hs_part"], ls_part=d["ls_part"],
            ind_footprint_mm2=float(des.inductor.footprint_mm2),
            ind_um=float(d["part_heights_um"]["inductor"]),
            cf_um=float(d["part_heights_um"]["cap_fly"]), n_ind_total=int(d["topology"]["K"]))


def _die_prism(part, H):
    """One GaN die of `part` as a vertical prism spanning a tier of height H: solder terminal
    (its land fraction in the encapsulant), body, encapsulant cap above a shorter part."""
    dev = DEVICES[part]
    a, b = dev["die_mm"]
    body = PHASES[dev.get("body_phase", "silicon")]
    enc, sol = PHASES["encapsulant"], PHASES["solder"]
    t_term, t_body = dev["terminal_um"], dev["body_um"]
    cap = H - dev["overall_um"]
    if cap < -1e-9:
        raise ValueError(f"{part} ({dev['overall_um']} um) is taller than its {H} um tier")
    f_s = min(1.0, sum(w * l for w, l in dev["pads_um"]) * 1e-6 / (a * b))
    k_term = f_s * sol["k"] + (1 - f_s) * enc["k"]
    kz = series([x for x in ((t_term, k_term), (t_body, body["k"]), (cap, enc["k"]))
                 if x[0] > 1e-12])
    k_in_term = 0.5 * ((f_s * sol["k"] + (1 - f_s) * enc["k"])
                       + maxwell_garnett(sol["k"], enc["k"], f_s, dim=2))
    k_in = (t_body * body["k"] + t_term * k_in_term + max(cap, 0.0) * enc["k"]) / H
    area = a * b
    vol = {dev.get("body_phase", "silicon"): area * t_body, "solder": area * f_s * t_term,
           "encapsulant": area * ((1 - f_s) * t_term + max(cap, 0.0))}
    return {"kind": "die", "part": part, "dims": (a, b), "area": area, "kz": kz,
            "k_in": k_in, "vol_um_mm2": vol, "solder_fraction": f_s, "cap_um": max(cap, 0.0)}


def _inductor_prism(fp_mm2, h_ind, H, k_core=None):
    env = inductor_envelope(k_core)
    enc = PHASES["encapsulant"]
    cap = H - h_ind
    if cap < -1e-9:
        raise ValueError(f"inductor ({h_ind} um) is taller than its {H} um tier")
    kz = series([x for x in ((h_ind, env["kz"]), (cap, enc["k"])) if x[0] > 1e-12])
    k_in = (h_ind * env["k_in_orientation_avg"] + max(cap, 0.0) * enc["k"]) / H
    s = math.sqrt(fp_mm2)
    fr = env["fractions"]
    vol = {"copper": fp_mm2 * h_ind * fr["copper"], "tym5": fp_mm2 * h_ind * fr["tym5_rod"],
           "encapsulant": fp_mm2 * (h_ind * fr["fill"] + max(cap, 0.0))}
    return {"kind": "inductor", "dims": (s, s), "area": fp_mm2, "kz": kz, "k_in": k_in,
            "vol_um_mm2": vol, "envelope_kz": env["kz"], "cap_um": max(cap, 0.0),
            "tym5": env["tym5"]}


def _mlcc_prism(L, W, T_part, mount, H, t_term_um=None):
    """One MLCC (body + Cu end terminations) on its solder mount, encapsulant cap above."""
    t_term = (MLCC["termination_um"] if t_term_um is None else t_term_um) * 1e-3
    body = mlcc_body()
    enc, cu, sol = PHASES["encapsulant"], PHASES["termination"], PHASES["solder"]
    cap = H - mount - T_part
    if cap < -1e-9:
        raise ValueError(f"MLCC ({mount + T_part} um) is taller than its {H} um tier")
    a_term, a_body = 2 * W * t_term, (L - 2 * t_term) * W
    lay = lambda k_part: [x for x in ((mount, sol["k"]), (T_part, k_part),        # noqa: E731
                                      (cap, enc["k"])) if x[0] > 1e-12]
    kz_b, kz_t = series(lay(body["k"])), series(lay(cu["k"]))
    kz = (a_body * kz_b + a_term * kz_t) / (a_body + a_term)
    k_part_in = (body["k_in"] * a_body + cu["k"] * a_term) / (a_body + a_term)
    k_in = (T_part * k_part_in + mount * sol["k"] + max(cap, 0.0) * enc["k"]) / H
    vol = {"mlcc_body": a_body * T_part, "termination": a_term * T_part,
           "solder": (a_body + a_term) * mount, "encapsulant": (a_body + a_term) * max(cap, 0.0)}
    return {"kind": "mlcc", "dims": (L, W), "area": L * W, "kz": kz, "k_in": k_in,
            "vol_um_mm2": vol, "kz_without_terminations": kz_b, "cap_um": max(cap, 0.0),
            "mlcc_body": body}


def mixed_tier(mc: MixedContents, name, parts, H, j_post=None, k_core=None, t_term_um=None):
    """The card of one MIXED converter tier from what it holds (TCPMT round 3).

    Every part is a vertical prism spanning the tier (a series stack of its own layers and an
    encapsulant cap up to the tier top: a part shorter than its tier conducts through the
    cap); prisms and the encapsulant fill act in parallel through the thickness. A tier
    holding inductors also carries their output-current posts (Cu prisms sized at the
    intra-VR current density for the share of the cell output current those inductors
    deliver; the legacy inductor-tier convention). In plane: each component in its area share
    of the cell (series-parallel bracket, midpoint). Mechanics: Voigt/Reuss/Hill and
    Turner/volume-mean over the volume fractions, as the single-class cards.
    The via conductors of nets crossing the tier are NOT in the card (declared,
    conservative for k_z)."""
    enc, cu = PHASES["encapsulant"], PHASES["copper"]
    A = mc.cell_area_mm2
    comps = []                                    # (prism, count)
    for cls, n in parts.items():
        if not n:
            continue
        if cls in ("gan_hs", "gan_ls"):
            p = _die_prism(mc.hs_part if cls == "gan_hs" else mc.ls_part, H)
        elif cls == "inductor":
            p = _inductor_prism(mc.ind_footprint_mm2, mc.ind_um, H, k_core)
        elif cls == "cap_fly":
            thin = mc.cf_um < CF_0603["T_nom_um"] + CF_0603["mount_um"] - 1e-9
            p = (_mlcc_prism(CF_0603["L_mm"], CF_0603["W_mm"], mc.cf_um, 0.0, H, t_term_um)
                 if thin else
                 _mlcc_prism(CF_0603["L_mm"], CF_0603["W_mm"], CF_0603["T_nom_um"],
                             CF_0603["mount_um"], H, t_term_um))
        else:
            raise ValueError(f"tier {name}: unknown class {cls}")
        comps.append((cls, p, int(n)))
    J = J_POST if j_post is None else j_post
    n_ind = int(parts.get("inductor", 0))
    a_post = (n_ind / mc.n_ind_total) * mc.i_out_rms_a / J * 1e6 if n_ind else 0.0
    a_parts = sum(p["area"] * n for _c, p, n in comps)
    a_enc = A - a_parts - a_post
    if a_enc < -1e-9:
        raise ValueError(f"tier {name} over-full: {a_parts + a_post:.3f} mm^2 of parts in a "
                         f"{A:.3f} mm^2 cell")
    kz = (sum(p["kz"] * p["area"] * n for _c, p, n in comps) + a_post * cu["k"]
          + a_enc * enc["k"]) / A
    lo = up = 0.0
    a_comp = a_parts + a_post
    shares = [(p["k_in"], p["dims"][0], p["dims"][1], p["area"] * n, n) for _c, p, n in comps]
    if a_post > 0:
        s = math.sqrt(a_post)
        shares.append((cu["k"], s, s, a_post, 1))
    for k_i, a_, b_, area, n in shares:
        share = A * area / a_comp / n
        l_, u_, _ = rect_cell_bounds(k_i, a_, b_, enc["k"], share)
        lo += area / a_comp * l_
        up += area / a_comp * u_
    k_in = 0.5 * (lo + up)
    vol = {}
    for _c, p, n in comps:
        for ph, v in p["vol_um_mm2"].items():
            vol[ph] = vol.get(ph, 0.0) + n * v
    vol["copper"] = vol.get("copper", 0.0) + a_post * H
    vol["encapsulant"] = vol.get("encapsulant", 0.0) + a_enc * H
    tot = A * H
    ph_of = {"tym5": next((p["tym5"] for _c, p, _n in comps if p["kind"] == "inductor"), None),
             "mlcc_body": next((p["mlcc_body"] for _c, p, _n in comps if p["kind"] == "mlcc"),
                               None)}
    fr = [(ph_of[ph] if ph in ph_of else ph, v / tot) for ph, v in vol.items() if v > 0]
    s_ = sum(f for _, f in fr)
    fr = [(p, f / s_) for p, f in fr]
    mech = mix_bounds(fr)
    bounds = {"kz_reuss": mech["k_reuss"], "kz_voigt": mech["k_voigt"], "kz_estimate": kz,
              "kxy_series_parallel": [lo, up], "kxy_reuss": mech["k_reuss"],
              "kxy_voigt": mech["k_voigt"]}
    extra = {"tier": name, "tier_um": H, "parts": dict(parts),
             "area_fractions": {**{f"{c}": p["area"] * n / A for c, p, n in comps},
                                "posts": a_post / A, "encapsulant": a_enc / A},
             "prisms": {c: {"kind": p["kind"], "part": p.get("part"), "count": n,
                            "kz": p["kz"], "k_in": p["k_in"], "cap_um": p["cap_um"]}
                        for c, p, n in comps},
             "posts": {"I_rms_A": mc.i_out_rms_a * (n_ind / mc.n_ind_total if n_ind else 0),
                       "J_A_m2": J, "area_mm2": a_post},
             "volume_fractions": {("tym5" if isinstance(p, dict) and "bounds" in p else
                                   "mlcc_body" if isinstance(p, dict) else p): f
                                  for p, f in fr}}
    return card(card_name(name), k_in, k_in, kz, mech, bounds,
                f"mixed tier {name}: " + ", ".join(f"{n} x {c}" for c, n in parts.items() if n)
                + f" in the encapsulant, {H:.0f} um, cell {mc.cell_side_mm:.4f} mm ({mc.label})",
                extra)


def card_name(tier_name: str) -> str:
    """conv_tier<i> for a mixed tier tier<i>_<contents>."""
    return "conv_" + tier_name.split("_")[0]


def mixed_cards(key=None, heights=None):
    """Every tier card of a record design (mixed tiers), keyed by card name."""
    import design_record as DR
    mc = MixedContents.from_record(key)
    out = {}
    for t in DR.tiers(key):
        h = float((heights or {}).get(t["name"], t["height_um"]))
        out[card_name(t["name"])] = mixed_tier(mc, t["name"], t["parts"], h)
    return out


#: tier-name PREFIX -> production card (any GaN part: gan_hs_<part>, gan_ls_<part>)
TIER_CARD = (("gan_hs", "conv_gan_hs"), ("gan_ls", "conv_gan_ls"),
             ("flying_caps", "conv_cfly_a0"), ("inductor_plus_cout", "conv_ind_cout"))
#: the legacy assignment (variant conv_k_legacy)
LEGACY = {"conv_gan_hs": "silicon", "conv_gan_ls": "silicon", "conv_cfly_a0": "hvr_effective",
          "conv_cfly_a1": "hvr_effective", "conv_ind_cout": "hvr_effective"}
_CACHE: dict = {}


def tier_card(tier_name: str):
    """The production card of a converter tier, or None if the tier has no derived card. A
    mixed tier (tier<i>_<contents>, TCPMT round 3) has its own card conv_tier<i>."""
    if re.match(r"^tier\d+_", tier_name):
        return card_name(tier_name)
    return next((c for p, c in TIER_CARD if tier_name.startswith(p)), None)


def _is_mixed(tiers) -> bool:
    return any(re.match(r"^tier\d+_", n) for n, _um in (tiers or ()))


def production_cards(tiers=None):
    """The cards of the design in force, for a tier list [(name, um)] (heights override).
    A tier list of mixed tiers (the design record) gets the mixed cards of the design in
    force (design_record), each from its own contents and height."""
    if _is_mixed(tiers):
        import design_record as DR
        heights = {n: float(um) for n, um in tiers if re.match(r"^tier\d+_", n)}
        known = {t["name"] for t in DR.tiers()}
        if set(heights) - known:
            raise ValueError(f"tiers {sorted(set(heights) - known)} are not tiers of design "
                             f"{DR.name()} ({sorted(known)})")
        key = ("mixed", DR.name(), tuple(sorted(heights.items()))) + _design_key()
        if key not in _CACHE:
            _CACHE[key] = mixed_cards(heights=heights)
        return _CACHE[key]
    heights = {}
    for name, um in (tiers or ()):
        for key in ("gan_hs", "gan_ls", "flying_caps", "inductor"):
            if name.startswith(key):
                heights[key] = float(um)
    key = (tuple(sorted(heights.items())),) + _design_key()
    if key not in _CACHE:
        _CACHE[key] = cards_for(TierContents.from_design(), heights=heights, strict=False)
    return _CACHE[key]


def _design_key() -> tuple:
    """What the design in force depends on: the converter rules of this process
    (electrical.production_rules; a pinned lineage compiles another converter) and the Z1
    config, so the card cache follows replay_production's design cache."""
    import replay_production  # noqa: F401  (puts scripts/phase0d on the path)
    import electrical as EL
    import z1_design as Z1D
    import design_record as DR
    return (tuple(sorted(EL.production_rules().items())), str(Z1D.config_path()), DR.name())


def install(stack: dict, tiers=None) -> dict:
    """Add the converter-tier cards of the design in force to a stack's materials; every
    tier of `tiers` that maps to a derived card must have one."""
    cards = production_cards(tiers)
    for name, _um in (tiers or ()):
        c = tier_card(name)
        if c is not None and c not in cards:
            raise ValueError(f"tier {name}: card {c} does not fit the cell of the design "
                             f"in force")
    for name, c in cards.items():
        stack["materials"][name] = json.loads(json.dumps(c))
    return cards


# ------------------------------------------------------------------ record
def sensitivity(tc: TierContents):
    """kz of each card over its uncertain inputs (one at a time)."""
    base = cards_for(tc)
    out = {}
    kz = lambda c: c["k_ortho"]["value"][2]
    for k in TYM5["k_range"]:
        out[f"ind_cout_kz_at_TYM5_k_{k:g}"] = kz(ind_cout_tier(tc, k_core=k))
    out["ind_cout_kz_two_post_rails"] = kz(ind_cout_tier(tc, post_rails=2))
    out["ind_cout_kz_posts_at_half_J"] = kz(ind_cout_tier(tc, j_post=0.5e8))
    for t in MLCC["termination_um_range"]:
        c = mlcc_tier(tc, tc.n_cfly_a1 or tc.n_cfly, A1_PART["L_mm"], A1_PART["W_mm"],
                      1030.0, A1_PART["mount_um"], "a1", "A1", t_term_um=t)
        out[f"cfly_a1_kz_termination_{t:g}um"] = kz(c)
    for phase, values in (("batio3", PHASES["batio3"]["range"]["k"]),
                          ("termination", [0.7, 400.0])):
        old = PHASES[phase]["k"]
        for kb in values:
            PHASES[phase]["k"] = kb
            try:
                cs = cards_for(tc)
                for nm in ("conv_cfly_a0", "conv_cfly_a1", "conv_ind_cout"):
                    out[f"{nm}_kz_{phase}_k_{kb:g}"] = kz(cs[nm])
            finally:
                PHASES[phase]["k"] = old
    out["base"] = {n: kz(c) for n, c in base.items()}
    return out


def summary_rows(cards):
    rows = {}
    for n, c in cards.items():
        d = c["derivation"]
        rows[n] = {"kx": c["k_ortho"]["value"][0], "ky": c["k_ortho"]["value"][1],
                   "kz": c["k_ortho"]["value"][2],
                   "kz_bounds": [d["bounds"]["kz_reuss"], d["bounds"]["kz_voigt"]],
                   "kxy_bracket": d["bounds"]["kxy_series_parallel"],
                   "E_GPa": c["E"]["value"] / 1e3,
                   "E_bounds_GPa": [d["mechanical"]["E_reuss_MPa"] / 1e3,
                                    d["mechanical"]["E_voigt_MPa"] / 1e3],
                   "nu": c["nu"]["value"], "cte_ppm": c["cte"]["value"] * 1e6,
                   "cte_bounds_ppm": [d["mechanical"]["cte_turner_per_K"] * 1e6,
                                      d["mechanical"]["cte_volume_per_K"] * 1e6]}
    return rows


def mixed_sensitivity(key):
    """k_z of every mixed tier over its uncertain inputs (one at a time): TY-M5 core k, the
    MLCC termination thickness, the BaTiO3 and termination conductivities, the post density."""
    import design_record as DR
    mc = MixedContents.from_record(key)
    kz = lambda c: c["k_ortho"]["value"][2]                              # noqa: E731
    out = {}
    for t in DR.tiers(key):
        n, parts, h = t["name"], t["parts"], float(t["height_um"])
        rec = {"base": kz(mixed_tier(mc, n, parts, h))}
        if parts.get("inductor"):
            for k in TYM5["k_range"]:
                rec[f"TYM5_k_{k:g}"] = kz(mixed_tier(mc, n, parts, h, k_core=k))
            rec["posts_at_half_J"] = kz(mixed_tier(mc, n, parts, h, j_post=0.5 * J_POST))
        if parts.get("cap_fly"):
            for tt in MLCC["termination_um_range"]:
                rec[f"termination_{tt:g}um"] = kz(mixed_tier(mc, n, parts, h, t_term_um=tt))
            for phase, values in (("batio3", PHASES["batio3"]["range"]["k"]),
                                  ("termination", [0.7, 400.0])):
                old = PHASES[phase]["k"]
                for kb in values:
                    PHASES[phase]["k"] = kb
                    try:
                        rec[f"{phase}_k_{kb:g}"] = kz(mixed_tier(mc, n, parts, h))
                    finally:
                        PHASES[phase]["k"] = old
        out[n] = rec
    return out


def main():
    """Every design of THE design record (configs/design_points.yaml): one card per mixed
    tier from its contents, with the bounds and the one-at-a-time sensitivity. The round-2
    single-class cards of the frozen 49-cell lineage are no longer regenerated here (git
    history); the stale 36-cell N4K4K_A2 / EPC2057 entry is gone."""
    import design_record as DR
    rec = {"what": "converter-tier material cards by unit-cell homogenization (TCPMT round "
                   "3: one card per MIXED tier of every design of the design record); "
                   "production uses the cards of the design in force",
           "record": str(DR.RECORD.relative_to(R)), "production": DR.production_key(),
           "replaces": {"mixed tiers": "the single-class tier cards (conv_gan_hs, conv_gan_ls, "
                                       "conv_cfly_a0/a1, conv_ind_cout) of the 49-cell build"},
           "legacy_variant": "conv_k_legacy (final_closure_sensitivity)",
           "method": __doc__.split("METHOD (all tiers)")[1].split("PHASES (sources")[0].strip(),
           "mixed_tier_method": mixed_tier.__doc__,
           "phases": PHASES, "tym5": TYM5, "devices": DEVICES, "inductor_segment": IND_SEGMENT,
           "mlcc": MLCC, "cf_0603": CF_0603, "keepout_um": KEEPOUT_UM, "j_post_A_m2": J_POST,
           "inductor_paper": INDUCTOR_PAPER, "designs": {}}
    for key in DR.keys():
        mc = MixedContents.from_record(key)
        cards = mixed_cards(key)
        rec["designs"][key] = {"tier_contents": asdict(mc),
                               "tiers": [{k: t[k] for k in ("name", "height_um", "parts")}
                                         for t in DR.tiers(key)],
                               "cards": cards, "summary": summary_rows(cards),
                               "sensitivity": mixed_sensitivity(key)}
    OUT.write_text(json.dumps(rec, indent=1, default=float))
    for key, d in rec["designs"].items():
        print(f"== {key}")
        for n, r in d["summary"].items():
            print(f"  {n:12s} kx={r['kx']:7.2f} kz={r['kz']:7.2f} "
                  f"[{r['kz_bounds'][0]:6.2f}, {r['kz_bounds'][1]:6.2f}]  "
                  f"E={r['E_GPa']:6.1f} GPa nu={r['nu']:.3f} CTE={r['cte_ppm']:5.2f} ppm/K")
    print(f"wrote {OUT}")
    return rec


if __name__ == "__main__":
    main()
