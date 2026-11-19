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
                terminal; capacitor mount + body) and, over a part shorter than its tier,
                the gap layer: copper posts on the part's terminals in the encapsulant
                (review round 3; the legacy encapsulant cap is variant conv_gap_legacy);
                in plane: each component
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
  gap posts           (review round 3, mixed tiers) a part shorter than its tier reaches the
                      RDLs through copper posts on its terminals (terminals on both faces, the
                      authors' assumption): production cross-section = the die's datasheet
                      RECOMMENDED LAND PATTERN (EPC2014C 0.295 of the die, EPC2055 0.371; a
                      Cu-pillar die its pillars), the MLCC's electrode bands (Murata GRM18 e =
                      0.35 mm nominal, 0.2-0.5), the inductor's current at J_POST; range for
                      the uncertainty step: posts carrying only the terminal RMS currents at
                      J_POST (lower) to the full solder-bar outline / widest band / J_POST/2
                      (upper). POST_BASES, post_area_mm2.
  PQFN (EPC2366)      (review round 3, count neighbour m25) as PUBLISHED: the die is EXPOSED
                      on top (its silicon back is the package top), flip-chip on a 200-um Cu
                      leadframe (A3) whose terminals are the published land pattern; mould
                      beside the die and between the terminals. Two parallel columns over the
                      3.3 x 2.6 mm package: leadframe + internal joint (solder bars, 0.40,
                      declared) + silicon under the 2.5 x 1.8 mm die, leadframe + mould beside
                      it; the silicon thickness reproduces the published R_thJC (0.6 K/W), the
                      bottom path is checked against R_thJB. Replaces the declared mould-cap
                      body (tier k_z 1.62 W/mK). _qfn_prism.

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
#: mould compound of a packaged part (EPC2366 PQFN: beside the exposed die, between the
#: leadframe terminals and in the internal flip-chip joint). Review round 3: replaces the
#: DECLARED 'qfn_body', which put a 200-um mould cap over a die the datasheet shows EXPOSED
#: (that body gave the EPC2366 tiers of m25 k_z 1.62 W/mK); the values are those the declared
#: body used for its mould
PHASES["mould"] = {"k": 0.9, "E": 20000.0, "nu": 0.30, "cte": 10.0e-6,
                   "source": "filled epoxy mould compound class (k 0.9 W/mK, E 20 GPa, CTE 10 "
                             "ppm/K below Tg; the mould values of the earlier declared QFN "
                             "body)", "status": "ASSUMPTION"}
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
                 "land_um": [(180.0, 814.0)] * 3 + [(180.0, 296.0)] * 2,
                 "terminal": "solder bars (SAC305 class)",
                 "source": "EPC2014C datasheet, DIE OUTLINE: A 1702, B 1087; bars 3-5 "
                           "200 x 834 um, pads 1-2 200 x 316 um; terminal 100 +/- 20 um; "
                           "overall 685 um (815 max)",
                 "land_source": "EPC2014C datasheet, RECOMMENDED LAND PATTERN (solder mask "
                                "defined): bars 3-5 180 x 814 um, pads 1-2 180 x 296 um"},
    "EPC2057": {"die_mm": (1.500, 1.200), "body_um": 518.0, "terminal_um": 120.0,
                "overall_um": 638.0,
                "pads_um": [(250.0, 300.0), (250.0, 525.0), (250.0, 1050.0), (250.0, 1050.0)],
                "terminal": "solder bumps",
                "source": "EPC2057 datasheet, DIE OUTLINE: A 1500, B 1200; pad 1 250 x 300, "
                          "pad 2 250 x 525, pads 3-4 250 x 1050 um; die 518 +/- 25, bump "
                          "120 +/- 12 um; overall 638 um"},
}
#: TCPMT round 3: the parts of the decided design point and of the count neighbours. Overall
#: heights from HVR_epc_device_data.json (datasheet Side View, the engine's stack heights).
#: Review round 3: the terminal (solder bar / bump / pillar) pattern of EPC2055 and EPC2090
#: and the EPC2055 land pattern are read from the public EPC datasheets (the earlier entries
#: DECLARED six 250 x 1000-um lands, 40 %, and five 250 x 1000-um bumps, 37 %).
DEVICES.update({
    "EPC2055": {"die_mm": (2.500, 1.500), "body_um": 518.0, "terminal_um": 120.0,
                "overall_um": 638.0,
                "pads_um": [(250.0, 300.0), (250.0, 825.0), (250.0, 1175.0),
                            (250.0, 1350.0), (250.0, 1175.0), (250.0, 1350.0)],
                "land_um": [(230.0, 280.0), (230.0, 805.0), (230.0, 1155.0),
                            (230.0, 1330.0), (230.0, 1155.0), (230.0, 1330.0)],
                "pads_um_legacy": [(250.0, 1000.0)] * 6,
                "terminal": "solder bars (bump view)", "status": "DATASHEET",
                "source": "EPC2055 datasheet, DIE OUTLINE (solder bump view): A 2500, B "
                          "1500; pad 1 (gate) 250 x 300, pad 2 (source) 250 x 825, bars 3, 5 "
                          "(drain) 250 x 1175, bars 4, 6 (source) 250 x 1350 um; die 518 +/- "
                          "25, bump 120 +/- 12, overall 638 um",
                "land_source": "EPC2055 datasheet, RECOMMENDED LAND PATTERN (solder mask "
                               "defined): 230 x 280, 230 x 805, 230 x 1155 (x2), 230 x 1330 "
                               "(x2) um"},
    "EPC2090": {"die_mm": (2.300, 1.450), "body_um": 518.0, "terminal_um": 88.0,
                "overall_um": 606.0, "pads_um": [(150.0, 180.0)] * 35, "corner_r_um": 75.0,
                "pads_um_legacy": [(250.0, 1000.0)] * 5,
                "terminal": "Cu pillar + solder bumps", "status": "DATASHEET",
                "source": "EPC2090 datasheet, DIE OUTLINE (solder bump view): A 2300, B 1450; "
                          "35 bumps c x d = 150 x 180 um, radius 75; 518 die + 50 Cu + 3 Ni + "
                          "35 solder = 606 um (solder card for the whole terminal). Cu pillar "
                          "die for use in a package: no land pattern (the posts take the "
                          "pillar footprint)"},
    # Review round 3: a PQFN WITH THE DIE EXPOSED ON TOP, modelled as published (_qfn_prism):
    # the GaN-on-Si die is flip-chip on a 200-um Cu leadframe whose five terminals form the
    # bottom face, and its silicon back IS the package top; mould fills beside the die,
    # between the terminals and in the internal joint. die_mm is the package body (the
    # engine's part footprint); body_um / terminal_um are the die + joint and the leadframe.
    "EPC2366": {"die_mm": (3.300, 2.600), "body_um": 500.0, "terminal_um": 200.0,
                "overall_um": 700.0,
                "qfn": {"exposed_die_mm": (2.500, 1.800), "leadframe_um": 200.0,
                        "R_jc_K_W": 0.6, "R_jb_K_W": 1.8,
                        #: published RECOMMENDED LAND PATTERN (solder mask defined, radius
                        #: 0.05 mm not subtracted: < 0.2 %) as rectangles (x0, x1, y0, y1) in
                        #: mm about the package centre, x along the 3.3-mm side (E), y along
                        #: the 2.6-mm side (D): gate, source (pin 2), drain, source, drain (pin
                        #: 5 with its four wettable-flank toes)
                        "land_rects_mm": [
                            (-1.850, -0.975, 0.676, 1.026), (-1.325, -0.975, 1.026, 1.450),
                            (-1.850, -0.975, -0.024, 0.326), (-1.550, -0.975, -1.175, -0.024),
                            (-1.325, -0.975, -1.450, -1.175), (-1.850, -1.550, -1.175, -0.775),
                            (-0.625, -0.175, -1.450, 1.450), (0.175, 0.625, -1.450, 1.450),
                            (0.975, 1.325, -1.450, 1.450), (1.325, 1.550, -1.175, 1.175),
                            (1.550, 1.850, 0.775, 1.175), (1.550, 1.850, 0.125, 0.525),
                            (1.550, 1.850, -0.525, -0.125), (1.550, 1.850, -1.175, -0.775)],
                        #: DECLARED: the internal flip-chip joint as solder bars at the EPC
                        #: bare-die bar fraction (DIE OUTLINE: EPC2014C 0.34, EPC2055 0.41,
                        #: EPC2057 0.41 of the die) in the mould
                        "joint_metal_fraction": 0.40,
                        "die_thickness_rule": "the silicon path of the card reproduces the "
                                              "published R_thJC (Case TOP = the exposed die): "
                                              "t_Si = R_thJC k_Si A_die; the internal joint "
                                              "takes the rest of A - A3",
                        "leadframe_rule": "the leadframe spans A3 = 0.20 mm at the published "
                                          "land pattern inside the outline (the terminals "
                                          "seen from the bottom); mould between"},
                "terminal": "PQFN leadframe terminals (gate, 2 x source, 2 x drain; wettable "
                            "flanks)", "status": "DATASHEET (outline, exposed die, leadframe "
                            "A3, land pattern, R_thJC / R_thJB) + DECLARED (die / joint split "
                            "by R_thJC, joint bar fraction, mould card)",
                "source": "EPC2366 datasheet (epc_ds/EPC2366/EPC2366.pdf, rev. June 12, 2026): "
                          "PACKAGE OUTLINE (p. 9: E 3.30 x D 2.60 mm, A 0.70 max, A3 0.20 ref, "
                          "exposed die 2.5 x 1.8 mm, 'the exposed die is the silicon substrate'), "
                          "Thermal Characteristics (p. 1: R_thJC 0.6 K/W to Case TOP, R_thJB "
                          "1.8 K/W), RECOMMENDED LAND PATTERN (p. 10)",
                "land_source": "EPC2366 datasheet, RECOMMENDED LAND PATTERN (solder mask "
                               "defined, p. 10)",
                "superseded": "the DECLARED QFN body of the cards before review round 3 (Cu pad "
                              "200 + die 250 + mould CAP 200 um over 45 % of the package, mould "
                              "elsewhere: part k_z 1.93, tier k_z 1.62 W/mK) contradicted the "
                              "published exposed die"},
})


def _qfn_land_mm2(q, hx=None, hy=None):
    """Area (mm^2) of a PQFN's published land pattern, optionally clipped to |x| <= hx,
    |y| <= hy (the package outline, the exposed die)."""
    tot = 0.0
    for x0, x1, y0, y1 in q["land_rects_mm"]:
        if hx is not None:
            x0, x1, y0, y1 = max(x0, -hx), min(x1, hx), max(y0, -hy), min(y1, hy)
        tot += max(0.0, x1 - x0) * max(0.0, y1 - y0)
    return tot


for _dev in DEVICES.values():                 # a PQFN's land / terminal patterns (w x l, um)
    if "qfn" in _dev:
        _dev["land_um"] = [(round((x1 - x0) * 1e3, 6), round((y1 - y0) * 1e3, 6))
                           for x0, x1, y0, y1 in _dev["qfn"]["land_rects_mm"]]
        _dev["pads_um"] = list(_dev["land_um"])
KEEPOUT_UM = 50.0                    # declared die-to-die keep-out (design rule)


def pad_area_mm2(dev: dict, key: str = "pads_um") -> float:
    """Total area (mm^2) of a die's terminal pattern (key 'pads_um': the solder bars / bumps
    of the DIE OUTLINE; 'land_um': the recommended land pattern; 'pads_um_legacy': the
    DECLARED pattern of the cards before review round 3, falling back to 'pads_um'), each pad
    w x l less the rounded corners when the datasheet gives a radius (corner_r_um)."""
    legacy = key == "pads_um_legacy"
    if legacy and key not in dev:
        key = "pads_um"
    r = 0.0 if (legacy and "pads_um_legacy" in dev) else float(dev.get("corner_r_um", 0.0))
    return sum(w * l - (4.0 - math.pi) * min(r, w / 2, l / 2) ** 2
               for w, l in dev[key]) * 1e-6


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
    f_s = pad_area_mm2(dev) / (a * b)
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
#: tolerance margin), so its prism is a 30-um solder mount, the nominal body and the gap up
#: to the tier top (copper posts on its electrode bands; the legacy card: encapsulant). A thin
#: part (the 100-um sensitivity) sits on the RDL with the rest of its tier as the gap.
CF_0603 = {"L_mm": 1.6, "W_mm": 0.8, "T_nom_um": 800.0, "mount_um": 30.0,
           # external-electrode band e (the termination's wrap onto the top and bottom faces):
           # Murata GRM18 dimension table e = 0.2 - 0.5 mm; nominal the midpoint
           "band_mm": 0.35, "band_mm_range": [0.2, 0.5],
           "band_source": "Murata GRM18 (0603) series dimensions: external electrode e = "
                          "0.2 to 0.5 mm"}
#: output-post current density: the framework's intra-VR density (final_closure_ledger.
#: INTRA_J_MAX, checked equal by the tests); a constant here so the cards import nothing of
#: the package chain
J_POST = 1.0e8

#: REVIEW ROUND 3 -- parts shorter than their tier. A part's terminals must reach the RDLs
#: above and below its tier (the authors' assumption: die terminals on BOTH faces), so the gap
#: between a shorter part and the tier faces is bridged by COPPER POSTS on the part's
#: terminals, not filled with encapsulant: the part's column is its own layers plus a post
#: layer (Cu posts in the encapsulant over the part's footprint) in SERIES; the columns act in
#: parallel with the encapsulant fill. The split of the gap between the two faces does not
#: change a series column, so the post layer is carried as one layer of the gap height.
#: GAP_MODEL 'encapsulant' is the earlier card, reproduced exactly (an encapsulant cap over a
#: shorter part, and the DECLARED EPC2055 / EPC2090 terminal patterns the datasheet ones
#: replaced), kept as the legacy variant conv_gap_legacy (final_closure_sensitivity).
GAP_MODELS = ("posts", "encapsulant")
GAP_MODEL = "posts"
#: post cross-section per part (one face), three bases:
#:   current   LOWER bound: posts carry the part's terminal RMS currents (the ledger's
#:             netlist, routing.nets) at J_POST -- two power terminals per die and per MLCC
#:             (drain/source; the two ends), one per inductor (the terminal facing the gap)
#:   land      PRODUCTION: a die's posts continue its datasheet RECOMMENDED LAND PATTERN (a
#:             Cu-pillar die without one: its pillar footprint); an MLCC's posts cover its
#:             external-electrode bands (2 W e, e nominal); an inductor has no published land
#:             pattern, so its post is sized by current at J_POST
#:   terminal  UPPER bound: a die's full solder-bar / bump outline (DIE OUTLINE), an MLCC's
#:             bands at the largest e, an inductor post at J_POST / 2
POST_BASES = ("current", "land", "terminal")
POST_BASIS = "land"
#: inductor post current density at each basis (no land pattern: a declared density range)
J_IND = {"current": 2.0 * J_POST, "land": J_POST, "terminal": 0.5 * J_POST}


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
    #: largest RMS terminal current of each part class, ((class, A), ...), from the ledger's
    #: cell netlist (routing.nets); empty -> every class at the inductor branch current
    #: (only the lower-bound post basis 'current' reads it, and the inductor's posts)
    i_terminal_a: tuple = ()

    @property
    def cell_area_mm2(self) -> float:
        return self.cell_side_mm ** 2

    def i_terminal(self, cls: str) -> float:
        """RMS terminal current (A) of a part of class `cls`."""
        d = dict(self.i_terminal_a)
        if cls in d:
            return float(d[cls])
        return float(self.i_out_rms_a) / max(int(self.n_ind_total), 1)

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
            cf_um=float(d["part_heights_um"]["cap_fly"]), n_ind_total=int(d["topology"]["K"]),
            i_terminal_a=terminal_currents(d.get("routing")))


#: part-name prefix in the ledger's cell netlist -> part class
_NET_PREFIX = (("HS", "gan_hs"), ("LS", "gan_ls"), ("CF", "cap_fly"), ("L", "inductor"))


def terminal_currents(routing_dict) -> tuple:
    """((class, A), ...): the largest RMS current of a net ending on a part of each class, in
    the ledger's cell netlist (routing.nets of the design record's routing block). The HV
    nets (VIN -> high side) carry the scenario factor in the ledger, not here: their stated
    value is the average share, below the high side's flying-capacitor loop current."""
    if not routing_dict:
        return ()
    import routing as RT
    best: dict = {}
    for n in RT.nets(routing_dict):
        for end in (n.src, n.dst):
            cls = next((c for p, c in _NET_PREFIX if end.startswith(p) and end[len(p):]
                        .isdigit()), None)
            if cls:
                best[cls] = max(best.get(cls, 0.0), float(n.i_rms_a))
    return tuple(sorted(best.items()))


def post_area_mm2(kind: str, mc: "MixedContents", part: str | None = None,
                  basis: str | None = None, dims=None) -> tuple:
    """(post cross-section in mm^2 per part, source) on one face of one part of `kind`
    ('gan_hs', 'gan_ls', 'inductor', 'cap_fly') at a POST_BASES basis (default POST_BASIS)."""
    basis = basis or POST_BASIS
    if basis not in POST_BASES:
        raise ValueError(f"post basis {basis!r} not in {POST_BASES}")
    i = mc.i_terminal(kind)
    if kind in ("gan_hs", "gan_ls"):
        dev = DEVICES[part]
        if basis == "current":
            return 2 * i / J_POST * 1e6, (f"2 power terminals x {i:.3f} A RMS (ledger netlist) "
                                         f"at {J_POST:.0e} A/m^2")
        if basis == "land" and "land_um" in dev:
            return pad_area_mm2(dev, "land_um"), dev.get("land_source", dev["source"])
        why = ("no land pattern: " if basis == "land" else "") + "terminal outline"
        return pad_area_mm2(dev), f"{why} ({dev['source']})"
    if kind == "inductor":
        j = J_IND[basis]
        return i / j * 1e6, (f"1 terminal x {i:.3f} A RMS at {j:.1e} A/m^2 (no published land "
                             f"pattern for the library inductor: current sizing)")
    if kind == "cap_fly":
        W = dims[1] if dims else CF_0603["W_mm"]
        if basis == "current":
            return 2 * i / J_POST * 1e6, (f"2 terminations x {i:.3f} A RMS (ledger netlist) "
                                         f"at {J_POST:.0e} A/m^2")
        e = CF_0603["band_mm"] if basis == "land" else CF_0603["band_mm_range"][1]
        return 2 * W * e, f"2 electrode bands {W:g} x {e:g} mm ({CF_0603['band_source']})"
    raise ValueError(f"no post model for {kind}")


def post_layer(f_cu):
    """(k_z, k_in) of a layer of copper posts (area fraction f_cu) in the encapsulant: the
    posts span the layer, so through it they conduct in parallel with the fill (exact); in
    plane they are isolated inclusions -- the midpoint of the parallel value and the 2-D
    Maxwell-Garnett (isolated-cylinder) value, as the solder-terminal layer."""
    enc, cu = PHASES["encapsulant"], PHASES["copper"]
    f = min(max(float(f_cu), 0.0), 1.0)
    kz = f * cu["k"] + (1 - f) * enc["k"]
    k_in = 0.5 * (kz + maxwell_garnett(cu["k"], enc["k"], f, dim=2)) if f < 1.0 else cu["k"]
    return kz, k_in


def _die_prism(part, H, a_post=0.0, legacy=False):
    """One GaN die of `part` as a vertical column spanning a tier of height H, its layers in
    series: solder terminal (its bar fraction in the encapsulant), body, and -- over a die
    shorter than its tier -- the gap layer: copper posts of cross-section a_post (mm^2) in
    the encapsulant (GAP_MODEL 'posts'). legacy: the card before review round 3 (encapsulant
    cap, a_post = 0, and the DECLARED terminal pattern where the datasheet one replaced it)."""
    dev = DEVICES[part]
    if dev.get("qfn"):                 # a packaged part with an exposed die (EPC2366): its own
        return _qfn_prism(part, H, 0.0 if legacy else a_post)      # column, as published
    a, b = dev["die_mm"]
    body = PHASES[dev.get("body_phase", "silicon")]
    enc, sol = PHASES["encapsulant"], PHASES["solder"]
    t_term, t_body = dev["terminal_um"], dev["body_um"]
    cap = H - dev["overall_um"]
    if cap < -1e-9:
        raise ValueError(f"{part} ({dev['overall_um']} um) is taller than its {H} um tier")
    cap = max(cap, 0.0)
    area = a * b
    f_s = min(1.0, pad_area_mm2(dev, "pads_um_legacy" if legacy else "pads_um") / area)
    f_p = min(1.0, float(a_post) / area) if (cap > 1e-12 and not legacy) else 0.0
    k_term = f_s * sol["k"] + (1 - f_s) * enc["k"]
    kz_gap, k_in_gap = post_layer(f_p)
    kz = series([x for x in ((t_term, k_term), (t_body, body["k"]), (cap, kz_gap))
                 if x[0] > 1e-12])
    k_in_term = 0.5 * ((f_s * sol["k"] + (1 - f_s) * enc["k"])
                       + maxwell_garnett(sol["k"], enc["k"], f_s, dim=2))
    k_in = (t_body * body["k"] + t_term * k_in_term + cap * k_in_gap) / H
    vol = {dev.get("body_phase", "silicon"): area * t_body, "solder": area * f_s * t_term,
           "copper": area * f_p * cap,
           "encapsulant": area * ((1 - f_s) * t_term + (1 - f_p) * cap)}
    return {"kind": "die", "part": part, "dims": (a, b), "area": area, "kz": kz,
            "k_in": k_in, "vol_um_mm2": vol, "solder_fraction": f_s, "cap_um": cap,
            "post_fraction": f_p, "post_mm2": area * f_p,
            "kz_layers": {"terminal": k_term, "body": body["k"], "gap": kz_gap}}


def qfn_construction(part):
    """The published PQFN of `part` (DEVICES[part]['qfn']) as card inputs: package, exposed
    die and land areas (mm^2), leadframe / internal joint / silicon thicknesses (um, the
    silicon set by the published R_thJC through the silicon card) and the leadframe copper
    fraction under the die and beside it."""
    dev = DEVICES[part]
    q = dev["qfn"]
    a, b = dev["die_mm"]
    da, db = q["exposed_die_mm"]
    A, Ad = a * b, da * db
    land_in = _qfn_land_mm2(q, a / 2, b / 2)
    land_die = _qfn_land_mm2(q, da / 2, db / 2)
    t_lf = float(q["leadframe_um"])
    t_si = float(q["R_jc_K_W"]) * PHASES["silicon"]["k"] * Ad * 1e-6 * 1e6
    t_j = float(dev["overall_um"]) - t_lf - t_si
    if t_j <= 0:
        raise ValueError(f"{part}: R_thJC {q['R_jc_K_W']} K/W needs {t_si:.0f} um of silicon, "
                         f"more than A - A3")
    return {"A_package_mm2": A, "A_die_mm2": Ad, "A_beside_mm2": A - Ad,
            "land_mm2": _qfn_land_mm2(q), "land_in_outline_mm2": land_in,
            "land_under_die_mm2": land_die, "leadframe_um": t_lf, "joint_um": t_j,
            "silicon_um": t_si, "f_cu_leadframe_under_die": land_die / Ad,
            "f_cu_leadframe_beside": (land_in - land_die) / (A - Ad),
            "f_cu_leadframe": land_in / A, "f_joint": float(q["joint_metal_fraction"])}


def _qfn_prism(part, H, a_post=0.0):
    """A packaged part with its die EXPOSED ON TOP (review round 3: EPC2366 as published), a
    column spanning a tier of height H. Over the package two parallel columns: under the die,
    the leadframe (Cu at the land pattern, mould between) + the internal flip-chip joint
    (solder bars in mould) + the silicon die reaching the package top; beside the die, the
    leadframe + mould to the top. Over a part shorter than its tier the gap layer (copper
    posts of a_post mm^2 in the encapsulant) is in series with both. In plane: the leadframe
    layer as the solder-terminal layer (parallel / 2-D Maxwell-Garnett midpoint), the
    die-and-mould layer as the die in its package (series-parallel midpoint). The card's
    silicon path reproduces R_thJC by construction; its bottom path (joint + leadframe under
    the die) is recorded against R_thJB, which also holds the device metallization the
    Si-carrier convention does not resolve."""
    dev = DEVICES[part]
    q = qfn_construction(part)
    a, b = dev["die_mm"]
    cu, sol, mld, si = (PHASES["copper"], PHASES["solder"], PHASES["mould"],
                        PHASES["silicon"])
    A, Ad, Am = q["A_package_mm2"], q["A_die_mm2"], q["A_beside_mm2"]
    t_lf, t_j, t_si = q["leadframe_um"], q["joint_um"], q["silicon_um"]
    h_part = float(dev["overall_um"])
    cap = H - h_part
    if cap < -1e-9:
        raise ValueError(f"{part} ({h_part} um) is taller than its {H} um tier")
    cap = max(cap, 0.0)

    def mix(f, k_i, k_m):
        return f * k_i["k"] + (1 - f) * k_m["k"]
    k_lf_d = mix(q["f_cu_leadframe_under_die"], cu, mld)
    k_lf_m = mix(q["f_cu_leadframe_beside"], cu, mld)
    k_j = mix(q["f_joint"], sol, mld)
    r_die = t_lf / k_lf_d + t_j / k_j + t_si / si["k"]           # um / (W/mK): series column
    r_bes = t_lf / k_lf_m + (t_j + t_si) / mld["k"]
    k_part = h_part * (Ad / r_die + Am / r_bes) / A               # the two columns in parallel
    f_p = min(1.0, float(a_post) / A) if cap > 1e-12 else 0.0
    kz_gap, k_in_gap = post_layer(f_p)
    kz = series([x for x in ((h_part, k_part), (cap, kz_gap)) if x[0] > 1e-12])

    def lay_in(f, k_i, k_m):
        return 0.5 * (mix(f, k_i, k_m) + maxwell_garnett(k_i["k"], k_m["k"], f, dim=2))
    k_in_lf = lay_in(q["f_cu_leadframe"], cu, mld)
    k_die_layer = (t_j * lay_in(q["f_joint"], sol, mld) + t_si * si["k"]) / (t_j + t_si)
    lo, up, _ = rect_cell_bounds(k_die_layer, *dev["qfn"]["exposed_die_mm"], mld["k"], A)
    k_in = (t_lf * k_in_lf + (t_j + t_si) * 0.5 * (lo + up) + cap * k_in_gap) / H
    land_in = q["land_in_outline_mm2"]
    vol = {"silicon": Ad * t_si, "solder": Ad * q["f_joint"] * t_j,
           "copper": land_in * t_lf + A * f_p * cap,
           "mould": Ad * (1 - q["f_joint"]) * t_j + Am * (t_j + t_si) + (A - land_in) * t_lf,
           "encapsulant": A * (1 - f_p) * cap}
    pub = dev["qfn"]
    check = {"R_top_card_K_W": t_si / si["k"] / Ad,
             "R_thJC_datasheet_K_W": pub["R_jc_K_W"],
             "R_bottom_card_K_W": (t_j / k_j + t_lf / k_lf_d) / Ad,
             "R_thJB_datasheet_K_W": pub["R_jb_K_W"],
             "note": "1-D columns over the exposed die (um / (W/mK) / mm^2 = K/W); R_thJB "
                     "also holds the device metallization (not resolved)"}
    return {"kind": "die", "part": part, "dims": (a, b), "area": A, "kz": kz, "k_in": k_in,
            "vol_um_mm2": vol, "solder_fraction": q["f_joint"], "cap_um": cap,
            "post_fraction": f_p, "post_mm2": A * f_p,
            "kz_layers": {"column_under_die": h_part / r_die, "column_beside_die": h_part / r_bes,
                          "part": k_part, "gap": kz_gap},
            "qfn": {**q, "k_z_part": k_part, "check_vs_datasheet": check,
                    "construction": "exposed die (published): leadframe + joint + silicon under "
                                    "the die, leadframe + mould beside it"}}


def _inductor_prism(fp_mm2, h_ind, H, k_core=None, a_post=0.0):
    """The inductor envelope and, over an inductor shorter than its tier, the gap layer of
    copper posts (a_post mm^2) in the encapsulant, in series."""
    env = inductor_envelope(k_core)
    cap = H - h_ind
    if cap < -1e-9:
        raise ValueError(f"inductor ({h_ind} um) is taller than its {H} um tier")
    cap = max(cap, 0.0)
    f_p = min(1.0, float(a_post) / fp_mm2) if cap > 1e-12 else 0.0
    kz_gap, k_in_gap = post_layer(f_p)
    kz = series([x for x in ((h_ind, env["kz"]), (cap, kz_gap)) if x[0] > 1e-12])
    k_in = (h_ind * env["k_in_orientation_avg"] + cap * k_in_gap) / H
    s = math.sqrt(fp_mm2)
    fr = env["fractions"]
    vol = {"copper": fp_mm2 * (h_ind * fr["copper"] + f_p * cap),
           "tym5": fp_mm2 * h_ind * fr["tym5_rod"],
           "encapsulant": fp_mm2 * (h_ind * fr["fill"] + (1 - f_p) * cap)}
    return {"kind": "inductor", "dims": (s, s), "area": fp_mm2, "kz": kz, "k_in": k_in,
            "vol_um_mm2": vol, "envelope_kz": env["kz"], "cap_um": cap,
            "post_fraction": f_p, "post_mm2": fp_mm2 * f_p, "tym5": env["tym5"]}


def _mlcc_prism(L, W, T_part, mount, H, t_term_um=None, a_post=0.0):
    """One MLCC (body + Cu end terminations) on its solder mount; over an MLCC shorter than
    its tier the gap carries copper posts on its terminations (a_post mm^2 per part: first
    over the end walls, the rest over the electrode bands on the body ends), encapsulant
    elsewhere. Parallel prisms, each a series of mount, part and gap: end walls (Cu
    termination), body under the posts, body under the encapsulant."""
    t_term = (MLCC["termination_um"] if t_term_um is None else t_term_um) * 1e-3
    body = mlcc_body()
    enc, term, sol, cu = (PHASES["encapsulant"], PHASES["termination"], PHASES["solder"],
                          PHASES["copper"])
    cap = H - mount - T_part
    if cap < -1e-9:
        raise ValueError(f"MLCC ({mount + T_part} um) is taller than its {H} um tier")
    cap = max(cap, 0.0)
    a_term, a_body = 2 * W * t_term, (L - 2 * t_term) * W
    a_p = min(float(a_post), a_term + a_body) if cap > 1e-12 else 0.0
    f_wall = min(1.0, a_p / a_term)                     # post fraction over the end walls
    a_bp = max(0.0, a_p - a_term)                       # body area under posts
    a_be = a_body - a_bp                                # body area under the encapsulant

    def col(k_part, k_gap):
        return series([x for x in ((mount, sol["k"]), (T_part, k_part), (cap, k_gap))
                       if x[0] > 1e-12])
    kz_gap_wall, k_in_gap_wall = post_layer(f_wall)
    kz_t = col(term["k"], kz_gap_wall)
    kz_bp, kz_be = col(body["k"], cu["k"]), col(body["k"], enc["k"])
    kz = (a_term * kz_t + a_bp * kz_bp + a_be * kz_be) / (a_body + a_term)
    k_part_in = (body["k_in"] * a_body + term["k"] * a_term) / (a_body + a_term)
    f_cap = a_p / (a_body + a_term)
    k_in_cap = post_layer(f_cap)[1]
    k_in = (T_part * k_part_in + mount * sol["k"] + cap * k_in_cap) / H
    vol = {"mlcc_body": a_body * T_part, "termination": a_term * T_part,
           "solder": (a_body + a_term) * mount, "copper": a_p * cap,
           "encapsulant": (a_body + a_term - a_p) * cap}
    return {"kind": "mlcc", "dims": (L, W), "area": L * W, "kz": kz, "k_in": k_in,
            "vol_um_mm2": vol, "kz_without_terminations": col(body["k"], enc["k"]),
            "cap_um": cap, "post_fraction": a_p / (L * W), "post_mm2": a_p,
            "mlcc_body": body}


def _prisms(mc: MixedContents, name, parts, H, k_core=None, t_term_um=None, gap=None,
            basis=None):
    """[(class, prism, count)] of a mixed tier under a gap model and post basis."""
    gap = gap or GAP_MODEL
    if gap not in GAP_MODELS:
        raise ValueError(f"gap model {gap!r} not in {GAP_MODELS}")
    posts = gap == "posts"
    comps = []
    for cls, n in parts.items():
        if not n:
            continue
        if cls in ("gan_hs", "gan_ls"):
            part = mc.hs_part if cls == "gan_hs" else mc.ls_part
            ap = post_area_mm2(cls, mc, part, basis)[0] if posts else 0.0
            p = _die_prism(part, H, ap, legacy=not posts)
        elif cls == "inductor":
            ap = post_area_mm2(cls, mc, basis=basis)[0] if posts else 0.0
            p = _inductor_prism(mc.ind_footprint_mm2, mc.ind_um, H, k_core, ap)
        elif cls == "cap_fly":
            dims = (CF_0603["L_mm"], CF_0603["W_mm"])
            ap = post_area_mm2(cls, mc, basis=basis, dims=dims)[0] if posts else 0.0
            thin = mc.cf_um < CF_0603["T_nom_um"] + CF_0603["mount_um"] - 1e-9
            p = (_mlcc_prism(*dims, mc.cf_um, 0.0, H, t_term_um, ap) if thin else
                 _mlcc_prism(*dims, CF_0603["T_nom_um"], CF_0603["mount_um"], H, t_term_um,
                             ap))
        else:
            raise ValueError(f"tier {name}: unknown class {cls}")
        comps.append((cls, p, int(n)))
    return comps


def _tier_k(mc, comps, a_post, A):
    """(k_z, in-plane bracket lo, up, midpoint) of a tier from its prisms."""
    enc, cu = PHASES["encapsulant"], PHASES["copper"]
    a_parts = sum(p["area"] * n for _c, p, n in comps)
    a_enc = A - a_parts - a_post
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
    return kz, lo, up, 0.5 * (lo + up)


def mixed_tier(mc: MixedContents, name, parts, H, j_post=None, k_core=None, t_term_um=None,
               gap=None, post_basis=None):
    """The card of one MIXED converter tier from what it holds (TCPMT round 3; gap posts:
    review round 3).

    Every part is a vertical COLUMN spanning the tier, a series stack of its own layers (die:
    solder terminal + body; MLCC: mount + part, with its Cu end terminations as a parallel
    prism; inductor: its homogenized envelope) and, over a part shorter than its tier, the
    GAP LAYER: copper posts on the part's terminals bridging it to the RDLs (the authors'
    assumption: terminals on both faces; the split of the gap between the faces does not
    change a series column), sized by POST_BASIS (production 'land': a die's datasheet land
    pattern, an MLCC's electrode bands, an inductor's current at J_POST), the rest of the gap
    encapsulant. The columns and the encapsulant fill act in parallel through the thickness.
    A tier holding inductors also carries their output-current posts (Cu prisms spanning the
    tier, sized at the intra-VR current density for the share of the cell output current
    those inductors deliver). In plane: each component in its area share of the cell
    (series-parallel bracket, midpoint). Mechanics: Voigt/Reuss/Hill and Turner/volume-mean
    over the volume fractions, as the single-class cards. The card records the k_z / k_xy
    range over the post bases ('current' lower, 'terminal' upper) for the uncertainty step
    and the legacy encapsulant-gap value (GAP_MODEL 'encapsulant', variant conv_gap_legacy).
    The via conductors of nets crossing the tier are NOT in the card (declared, conservative
    for k_z)."""
    gap = gap or GAP_MODEL
    basis = post_basis or POST_BASIS
    A = mc.cell_area_mm2
    comps = _prisms(mc, name, parts, H, k_core, t_term_um, gap, basis)
    J = J_POST if j_post is None else j_post
    n_ind = int(parts.get("inductor", 0))
    a_post = (n_ind / mc.n_ind_total) * mc.i_out_rms_a / J * 1e6 if n_ind else 0.0
    a_parts = sum(p["area"] * n for _c, p, n in comps)
    a_enc = A - a_parts - a_post
    if a_enc < -1e-9:
        raise ValueError(f"tier {name} over-full: {a_parts + a_post:.3f} mm^2 of parts in a "
                         f"{A:.3f} mm^2 cell")
    kz, lo, up, k_in = _tier_k(mc, comps, a_post, A)
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
    gap_posts = {}
    for c, p, n in comps:
        if p["cap_um"] > 1e-12:
            part = p.get("part")
            dims = p["dims"] if c == "cap_fly" else None
            a_, src = (post_area_mm2(c, mc, part, basis, dims) if gap == "posts"
                       else (0.0, "legacy: encapsulant cap"))
            gap_posts[c] = {"gap_um": p["cap_um"], "post_mm2_per_part": p["post_mm2"],
                            "post_fraction_of_part": p["post_fraction"],
                            "basis": basis if gap == "posts" else None, "source": src,
                            "I_terminal_A": mc.i_terminal(c)}
    if gap == "posts" and post_basis is None:
        # the range for the uncertainty step: the same tier at the lower / upper post basis
        rng = {}
        for b_ in ("current", "terminal"):
            cb = _prisms(mc, name, parts, H, k_core, t_term_um, "posts", b_)
            rng[b_] = _tier_k(mc, cb, a_post, A)
        legacy = _tier_k(mc, _prisms(mc, name, parts, H, k_core, t_term_um, "encapsulant"),
                         a_post, A)
        bounds["kz_post_range"] = [rng["current"][0], rng["terminal"][0]]
        bounds["kxy_post_range"] = [rng["current"][3], rng["terminal"][3]]
        bounds["kz_gap_encapsulant_legacy"] = legacy[0]
        bounds["kxy_gap_encapsulant_legacy"] = legacy[3]
    extra = {"tier": name, "tier_um": H, "parts": dict(parts),
             "gap_model": gap, "post_basis": basis if gap == "posts" else None,
             "area_fractions": {**{f"{c}": p["area"] * n / A for c, p, n in comps},
                                "posts": a_post / A, "encapsulant": a_enc / A},
             "prisms": {c: {"kind": p["kind"], "part": p.get("part"), "count": n,
                            "kz": p["kz"], "k_in": p["k_in"], "cap_um": p["cap_um"],
                            "gap_um": p["cap_um"], "post_fraction": p["post_fraction"],
                            **({"qfn": p["qfn"]} if p.get("qfn") else {})}
                        for c, p, n in comps},
             "gap_posts": gap_posts,
             "posts": {"I_rms_A": mc.i_out_rms_a * (n_ind / mc.n_ind_total if n_ind else 0),
                       "J_A_m2": J, "area_mm2": a_post,
                       "what": "output-current posts spanning the tier"},
             "volume_fractions": {("tym5" if isinstance(p, dict) and "bounds" in p else
                                   "mlcc_body" if isinstance(p, dict) else p): f
                                  for p, f in fr}}
    fill = ("every part spans the tier" if not gap_posts else
            "copper posts over the shorter parts" if gap == "posts" else
            "encapsulant over the shorter parts (legacy)")
    return card(card_name(name), k_in, k_in, kz, mech, bounds,
                f"mixed tier {name}: " + ", ".join(f"{n} x {c}" for c, n in parts.items() if n)
                + f" in the encapsulant ({fill}), {H:.0f} um, cell {mc.cell_side_mm:.4f} mm "
                f"({mc.label})", extra)


def card_name(tier_name: str) -> str:
    """conv_tier<i> for a mixed tier tier<i>_<contents>."""
    return "conv_" + tier_name.split("_")[0]


def mixed_cards(key=None, heights=None, gap=None):
    """Every tier card of a record design (mixed tiers), keyed by card name; gap: GAP_MODEL
    by default ('encapsulant' = the legacy cards of variant conv_gap_legacy)."""
    import design_record as DR
    mc = MixedContents.from_record(key)
    out = {}
    for t in DR.tiers(key):
        h = float((heights or {}).get(t["name"], t["height_um"]))
        out[card_name(t["name"])] = mixed_tier(mc, t["name"], t["parts"], h, gap=gap)
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
        key = ("mixed", DR.name(), tuple(sorted(heights.items())), GAP_MODEL,
               POST_BASIS) + _design_key()
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
                   "kz_post_range": d["bounds"].get("kz_post_range"),
                   "kxy_post_range": d["bounds"].get("kxy_post_range"),
                   "kz_gap_encapsulant_legacy": d["bounds"].get("kz_gap_encapsulant_legacy"),
                   "kxy_gap_encapsulant_legacy": d["bounds"].get("kxy_gap_encapsulant_legacy"),
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
        for b_ in POST_BASES:
            rec[f"posts_{b_}"] = kz(mixed_tier(mc, n, parts, h, post_basis=b_))
        rec["gap_encapsulant_legacy"] = kz(mixed_tier(mc, n, parts, h, gap="encapsulant"))
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
           "legacy_gap_variant": "conv_gap_legacy (final_closure_sensitivity): the encapsulant "
                                 "cap over parts shorter than their tier (GAP_MODEL "
                                 "'encapsulant'), the cards before review round 3",
           "gap_model": GAP_MODEL, "post_basis": POST_BASIS, "post_bases": {
               "current": "lower bound: posts carry the terminal RMS currents (ledger "
                          "netlist) at J_POST",
               "land": "production: die datasheet land pattern (Cu-pillar die: pillar "
                       "footprint), MLCC electrode bands at the nominal e, inductor current "
                       "at J_POST",
               "terminal": "upper bound: die solder-bar / bump outline, MLCC bands at the "
                           "largest e, inductor current at J_POST / 2"},
           "j_inductor_post_A_m2": J_IND,
           "method": __doc__.split("METHOD (all tiers)")[1].split("PHASES (sources")[0].strip(),
           "mixed_tier_method": mixed_tier.__doc__,
           "phases": PHASES, "tym5": TYM5, "devices": DEVICES, "inductor_segment": IND_SEGMENT,
           "mlcc": MLCC, "cf_0603": CF_0603, "keepout_um": KEEPOUT_UM, "j_post_A_m2": J_POST,
           "inductor_paper": INDUCTOR_PAPER, "designs": {}}
    for key in DR.keys():
        mc = MixedContents.from_record(key)
        cards = mixed_cards(key)
        legacy = mixed_cards(key, gap="encapsulant")
        rec["designs"][key] = {"tier_contents": asdict(mc),
                               "tiers": [{k: t[k] for k in ("name", "height_um", "parts")}
                                         for t in DR.tiers(key)],
                               "cards": cards, "summary": summary_rows(cards),
                               "legacy_gap_encapsulant_summary": summary_rows(legacy),
                               "sensitivity": mixed_sensitivity(key)}
    OUT.write_text(json.dumps(rec, indent=1, default=float))
    for key, d in rec["designs"].items():
        print(f"== {key}")
        for n, r in d["summary"].items():
            print(f"  {n:12s} kx={r['kx']:7.2f} kz={r['kz']:7.2f} "
                  f"[{r['kz_bounds'][0]:6.2f}, {r['kz_bounds'][1]:6.2f}]  posts kz "
                  f"[{r['kz_post_range'][0]:6.2f}, {r['kz_post_range'][1]:6.2f}] kxy "
                  f"[{r['kxy_post_range'][0]:5.2f}, {r['kxy_post_range'][1]:5.2f}]  legacy kz "
                  f"{r['kz_gap_encapsulant_legacy']:6.2f} kxy "
                  f"{r['kxy_gap_encapsulant_legacy']:5.2f}  E={r['E_GPa']:6.1f} GPa "
                  f"nu={r['nu']:.3f} CTE={r['cte_ppm']:5.2f} ppm/K")
    print(f"wrote {OUT}")
    return rec


if __name__ == "__main__":
    main()
