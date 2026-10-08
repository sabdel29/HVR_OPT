#!/usr/bin/env python3
"""Phase-0M Parts 1-4 -- geometry-resolved interconnect model.

FIRST PRINCIPLE: no interconnect RESISTANCE may be a primitive parameter if geometry can
derive it. Every quantity is tagged as exactly one of

    MATERIAL   a property of the material          rho_Cu(T), alpha
    PROCESS    a technology/design-rule limit      pitch_min, t_liner, AR_max, J_max
    DESIGN     a variable the optimizer may move   r, p, h, n_alloc, t_cu, w, s, N_layer
    DERIVED    computed from the three above       R, I_max, n_avail, P, k_eff, phi_Cu

The classification is enforced: `classify()` raises on an unclassified key and the CSV/YAML
artifacts are written from the same table the code uses.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, asdict

RHO_CU_20C = 17.0e-9          # Ohm.m  -- June-2026, SOURCE_BACKED
ALPHA_CU = 3.93e-3            # 1/K    -- bulk Cu TCR
RHO_SOLDER_20C = 130.0e-9     # Ohm.m  -- June-2026, SOURCE_BACKED
ALPHA_SOLDER = 4.0e-3
K_CU = 385.0                  # W/m.K
K_SI = 130.0                  # W/m.K
K_SIO2 = 1.4                  # W/m.K
K_ORG = 0.35                  # W/m.K  organic build-up dielectric
K_SOLDER = 57.0               # W/m.K  SAC305
K_UNDERFILL = 0.6             # W/m.K
E_CU, NU_CU, CTE_CU = 117e3, 0.34, 17.0e-6          # MPa, -, 1/K
E_SI, NU_SI, CTE_SI = 169e3, 0.28, 2.6e-6
E_SIO2, CTE_SIO2 = 70e3, 0.5e-6
E_ORG, CTE_ORG = 20e3, 30.0e-6
E_SOLDER, CTE_SOLDER = 45e3, 21.5e-6
E_UF, CTE_UF = 8e3, 30.0e-6


def rho_cu(T_c: float) -> float:
    return RHO_CU_20C * (1.0 + ALPHA_CU * (T_c - 20.0))


def rho_solder(T_c: float) -> float:
    return RHO_SOLDER_20C * (1.0 + ALPHA_SOLDER * (T_c - 20.0))


# ---------------------------------------------------------------------------
# Part 1: the classification table. One row per parameter, one class each.
# ---------------------------------------------------------------------------
CLASSES = ("MATERIAL", "PROCESS", "DESIGN", "DERIVED")

PARAMS = [
    # key                      class      unit        value/rule            source status
    ("rho_Cu_20C",             "MATERIAL", "Ohm.m",   RHO_CU_20C,  "SOURCE_BACKED June-2026"),
    ("alpha_Cu",               "MATERIAL", "1/K",     ALPHA_CU,    "ASSUMPTION bulk Cu TCR"),
    ("rho_solder_20C",         "MATERIAL", "Ohm.m",   RHO_SOLDER_20C, "SOURCE_BACKED June-2026"),
    ("k_Cu",                   "MATERIAL", "W/m.K",   K_CU,        "handbook"),
    ("k_Si",                   "MATERIAL", "W/m.K",   K_SI,        "handbook"),
    ("k_SiO2",                 "MATERIAL", "W/m.K",   K_SIO2,      "handbook"),
    ("E_Cu, nu_Cu, CTE_Cu",    "MATERIAL", "MPa,-,1/K", None,      "handbook"),

    ("tsv_liner_thickness",    "PROCESS",  "m",       0.5e-6,      "ASSUMPTION typical SiO2 liner"),
    ("tsv_aspect_ratio_max",   "PROCESS",  "-",       10.0,
     "DERIVED_FROM_SOURCE June-2026 Table III demonstrates d=30 um at h=300 um"),
    ("tsv_spacing_min",        "PROCESS",  "m",       30.0e-6,
     "DERIVED_FROM_SOURCE June-2026 p=60 um at d=30 um implies s_min = p - d = 30 um"),
    ("tsv_koz_ratio",          "PROCESS",  "-",       1.0,
     "ASSUMPTION keep-out radius expressed as a multiple of r; swept, never fixed"),
    ("J_max_Cu",               "PROCESS",  "A/m^2",   None,
     "DERIVED_FROM_SOURCE envelope 1.0e8 (June-2026) to 4.0e8 (ECTC-2024); "
     "the EM-lifetime limit itself remains OPEN"),
    ("J_max_solder",           "PROCESS",  "A/m^2",   None,
     "DERIVED_FROM_SOURCE envelope 1.74e7 to 3.97e7"),
    ("rdl_line_space_min",     "PROCESS",  "m",       2.0e-6,      "SOURCE_BACKED ECTC-2024 Table I S=2 um"),
    ("bump_pitch_min",         "PROCESS",  "m",       None,        "tier-specific, see design space"),

    ("tsv_radius",             "DESIGN",   "m",       15.0e-6,     "June-2024 nominal d=30 um"),
    ("tsv_pitch",              "DESIGN",   "m",       60.0e-6,     "June-2026 nominal; constrained p >= 2r + s_min"),
    ("tsv_height",             "DESIGN",   "m",       300.0e-6,    "= substrate thickness variable"),
    ("tsv_n_allocated",        "DESIGN",   "-",       None,        "set by allocation POLICY"),
    ("tsv_field_footprint",    "DESIGN",   "m^2",     None,        "die shadow or tile footprint"),
    ("tsv_pg_ratio",           "DESIGN",   "-",       0.5,         "supply/ground split"),
    ("rdl_t_cu",               "DESIGN",   "m",       10.0e-6,     "ECTC-2024 REFERENCE, not a fixed constant"),
    ("rdl_width",              "DESIGN",   "m",       10.0e-6,     "ECTC-2024 REFERENCE"),
    ("rdl_space",              "DESIGN",   "m",       2.0e-6,      "ECTC-2024 REFERENCE, >= process min"),
    ("rdl_n_vdd, rdl_n_gnd",   "DESIGN",   "-",       2,           "ECTC-2024 REFERENCE"),
    ("bump_diameter",          "DESIGN",   "m",       None,        "tier-specific"),
    ("bump_height",            "DESIGN",   "m",       None,        "tier-specific"),
    ("bump_pitch",             "DESIGN",   "m",       None,        "tier-specific"),
    ("pad_diameter",           "DESIGN",   "m",       None,        "landing pad, promoted in Part 8"),
    ("trace_width_at_pad",     "DESIGN",   "m",       None,        "promoted in Part 8"),
    ("source_footprint",       "DESIGN",   "m^2",     None,        "VR tile footprint"),
    ("load_footprint",         "DESIGN",   "m^2",     None,        "POL cell footprint"),

    ("A_conductor",            "DERIVED",  "m^2",     None,        "pi (r - t_liner)^2"),
    ("R_single",               "DERIVED",  "Ohm",     None,        "rho(T) h / A_conductor"),
    ("I_max_per_via",          "DERIVED",  "A",       None,        "J_max A_conductor"),
    ("n_required",             "DERIVED",  "-",       None,        "ceil(I / I_max_per_via)"),
    ("n_available",            "DERIVED",  "-",       None,        "footprint pg_ratio / pitch^2"),
    ("R_field",                "DERIVED",  "Ohm",     None,        "R_single / n_allocated"),
    ("P_joule",                "DERIVED",  "W",       None,        "I^2 R_loop"),
    ("phi_Cu",                 "DERIVED",  "-",       None,        "n_alloc A_conductor / footprint"),
    ("k_z_eff, k_xy_eff",      "DERIVED",  "W/m.K",   None,        "effective-medium, Part 20"),
    ("E_eff, CTE_eff",         "DERIVED",  "MPa,1/K", None,        "Voigt/Reuss + Levin, Part 20"),
    ("K_crowd",                "DERIVED",  "-",       None,        "R_3D_transition / R_bulk, Part 8"),
    ("sheet_conductance",      "DERIVED",  "S",       None,        "N t occupancy / rho(T)"),
]


def classify(key: str) -> str:
    for k, c, *_ in PARAMS:
        if key == k or key in [x.strip() for x in k.split(",")]:
            return c
    raise KeyError(f"{key!r} is not classified -- add it to PARAMS before using it")


# ---------------------------------------------------------------------------
# Part 2: TSV geometry
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TSVGeometry:
    """A TSV field. r, p, h, t_liner are inputs; everything else is derived."""
    r_m: float
    h_m: float
    p_m: float | None = None          # None -> minimum legal pitch
    t_liner_m: float = 0.5e-6
    s_min_m: float = 30.0e-6
    koz_ratio: float = 1.0            # keep-out radius = koz_ratio * r beyond the liner
    ar_max: float = 10.0

    @property
    def r_cu_m(self) -> float:
        """Conducting radius. The liner is dielectric and carries no current."""
        return max(self.r_m - self.t_liner_m, 1e-12)

    @property
    def a_cu_m2(self) -> float:
        return math.pi * self.r_cu_m ** 2

    @property
    def pitch_min_m(self) -> float:
        """p >= 2r + s_min, and the keep-out zone may be the binding rule instead."""
        return max(2.0 * self.r_m + self.s_min_m,
                   2.0 * self.r_m * (1.0 + self.koz_ratio))

    @property
    def pitch_m(self) -> float:
        return self.pitch_min_m if self.p_m is None else self.p_m

    @property
    def pitch_legal(self) -> bool:
        return self.pitch_m >= self.pitch_min_m - 1e-15

    @property
    def aspect_ratio(self) -> float:
        return self.h_m / (2.0 * self.r_m)

    @property
    def ar_ok(self) -> bool:
        return self.aspect_ratio <= self.ar_max + 1e-12

    def r_single(self, T_c: float) -> float:
        return rho_cu(T_c) * self.h_m / self.a_cu_m2

    def i_max_per_via(self, j_max: float) -> float:
        return j_max * self.a_cu_m2

    def n_required(self, current_a: float, j_max: float) -> int:
        return max(1, math.ceil(abs(current_a) / self.i_max_per_via(j_max)))

    def n_available(self, footprint_m2: float, pg_ratio: float = 0.5) -> int:
        return max(1, int(footprint_m2 * pg_ratio / self.pitch_m ** 2))

    def phi_cu(self, n_alloc: int, footprint_m2: float) -> float:
        return n_alloc * self.a_cu_m2 / footprint_m2

    # ---- Part 4: the same geometry in the thermal and mechanical domains -------------
    def k_eff(self, n_alloc: int, footprint_m2: float) -> dict:
        """Anisotropic effective conductivity of the Si + liner + Cu layer.

        k_z is a parallel (Voigt/rule-of-mixtures) average: heat flows along the vias, the
        liner and the silicon independently. k_xy is the Hashin-Shtrikman / Maxwell-Garnett
        result for cylinders embedded transverse to the flow, which is the correct bound for
        an array of parallel inclusions and is NOT the parallel average.
        """
        f_cu = self.phi_cu(n_alloc, footprint_m2)
        a_out = math.pi * self.r_m ** 2
        f_ox = max(n_alloc * (a_out - self.a_cu_m2) / footprint_m2, 0.0)
        f_si = max(1.0 - f_cu - f_ox, 0.0)
        k_z = f_cu * K_CU + f_ox * K_SIO2 + f_si * K_SI
        # transverse: treat the lined via (Cu core + oxide shell) as one inclusion of
        # conductivity k_incl, volume fraction f_i, in a silicon matrix
        f_i = f_cu + f_ox
        k_incl = (K_CU * self.a_cu_m2 + K_SIO2 * (a_out - self.a_cu_m2)) / max(a_out, 1e-30)
        k_xy = K_SI * (k_incl * (1 + f_i) + K_SI * (1 - f_i)) / \
               (k_incl * (1 - f_i) + K_SI * (1 + f_i)) if f_i < 1 else k_incl
        return {"f_cu": f_cu, "f_ox": f_ox, "f_si": f_si,
                "k_z": k_z, "k_xy": k_xy, "k_incl": k_incl}

    def mech_eff(self, n_alloc: int, footprint_m2: float) -> dict:
        """Effective in-plane modulus and CTE of the through-silicon layer.

        E_xy uses the Reuss (series) bound in-plane, which is the conservative choice for
        transverse loading of a fibre-like inclusion; E_z uses Voigt. CTE follows the Levin /
        rule-of-mixtures stiffness-weighted average, which is exact for a two-phase composite
        with isotropic phases under uniform temperature.
        """
        d = self.k_eff(n_alloc, footprint_m2)
        f_cu, f_ox, f_si = d["f_cu"], d["f_ox"], d["f_si"]
        e_z = f_cu * E_CU + f_ox * E_SIO2 + f_si * E_SI
        e_xy = 1.0 / (f_cu / E_CU + f_ox / E_SIO2 + f_si / E_SI)
        cte = (f_cu * E_CU * CTE_CU + f_ox * E_SIO2 * CTE_SIO2 + f_si * E_SI * CTE_SI) / e_z
        return {"E_z_MPa": e_z, "E_xy_MPa": e_xy, "CTE_eff": cte, **d}


# ---------------------------------------------------------------------------
# Part 3: allocation policies
# ---------------------------------------------------------------------------
POLICIES = ("A_min_capability", "B_fixed_count", "C_fixed_pitch",
            "D_area_optimal", "E_fixed_cu_fraction")


def allocate(g: TSVGeometry, current_a: float, j_max: float, footprint_m2: float,
             policy: str, n_fixed: int | None = None, phi_target: float | None = None,
             pg_ratio: float = 0.5) -> dict:
    nreq = g.n_required(current_a, j_max)
    navail = g.n_available(footprint_m2, pg_ratio)
    if policy == "A_min_capability":
        n = nreq
    elif policy == "B_fixed_count":
        if n_fixed is None:
            raise ValueError("B_fixed_count needs n_fixed")
        n = n_fixed
    elif policy in ("C_fixed_pitch", "D_area_optimal"):
        n = navail
    elif policy == "E_fixed_cu_fraction":
        if phi_target is None:
            raise ValueError("E_fixed_cu_fraction needs phi_target")
        n = max(1, int(round(phi_target * footprint_m2 / g.a_cu_m2)))
    else:
        raise ValueError(f"unknown policy {policy!r}")
    feasible = (nreq <= navail) and (n <= navail) and g.ar_ok and g.pitch_legal
    return {"policy": policy, "n_required": nreq, "n_available": navail,
            "n_allocated": max(n, 1), "feasible": feasible,
            "binding": ("aspect_ratio" if not g.ar_ok else
                        "pitch_rule" if not g.pitch_legal else
                        "n_req>n_avail" if nreq > navail else
                        "n_alloc>n_avail" if n > navail else "")}


def field_resistance(g: TSVGeometry, alloc: dict, T_c: float) -> float:
    return g.r_single(T_c) / alloc["n_allocated"]


def evaluate(g: TSVGeometry, current_a: float, j_max: float, footprint_m2: float,
             policy: str, T_c: float = 85.0, **kw) -> dict:
    al = allocate(g, current_a, j_max, footprint_m2, policy, **kw)
    rf = field_resistance(g, al, T_c)
    rloop = 2.0 * rf
    m = g.mech_eff(al["n_allocated"], footprint_m2)
    return {"r_um": g.r_m * 1e6, "r_cu_um": g.r_cu_m * 1e6, "h_um": g.h_m * 1e6,
            "pitch_um": g.pitch_m * 1e6, "aspect_ratio": g.aspect_ratio,
            "A_cu_um2": g.a_cu_m2 * 1e12,
            "R_single_mohm": g.r_single(T_c) * 1e3,
            "I_max_per_via_mA": g.i_max_per_via(j_max) * 1e3,
            "R_field_mohm": rf * 1e3, "R_loop_mohm": rloop * 1e3,
            "IR_drop_mV": current_a * rloop * 1e3,
            "P_joule_W": current_a ** 2 * rloop,
            "J_actual_A_per_m2": current_a / (al["n_allocated"] * g.a_cu_m2),
            "phi_cu": m["f_cu"], "k_z": m["k_z"], "k_xy": m["k_xy"],
            "E_z_MPa": m["E_z_MPa"], "E_xy_MPa": m["E_xy_MPa"], "CTE_eff": m["CTE_eff"],
            "area_used_mm2": al["n_allocated"] * g.pitch_m ** 2 * 1e6,
            "area_frac_used": al["n_allocated"] * g.pitch_m ** 2 / footprint_m2,
            **al}


# ---------------------------------------------------------------------------
# the analytic closed forms the sweep must reproduce
# ---------------------------------------------------------------------------
def r_field_policy_A_analytic(rho: float, h: float, j_max: float, current_a: float) -> float:
    """R_field = rho h J / I under n_alloc = I/(J A_cond). Independent of the conductor
    cross-section ENTIRELY -- not merely of the radius."""
    return rho * h * j_max / current_a


def r_field_policy_E_analytic(rho: float, h: float, phi: float, footprint_m2: float) -> float:
    """R_field = rho h / (phi A_field) at fixed total copper fraction. Also r-independent."""
    return rho * h / (phi * footprint_m2)


def r_field_policy_C_analytic(rho: float, h: float, r: float, r_cu: float, s_min: float,
                              footprint_m2: float, pg_ratio: float,
                              koz_ratio: float = 1.0) -> float:
    """R_field = rho h p(r)^2 / (pi r_cu^2 A_field f) with p(r) the binding pitch rule.

    Two spacing rules give OPPOSITE answers and the distinction matters:
      ADDITIVE      p = 2r + s_min          -> R ~ (2 + s_min/r)^2, decreasing, saturating
      PROPORTIONAL  p = 2r(1 + koz_ratio)   -> R ~ constant, the radius cancels EXACTLY
    A keep-out zone scales with via diameter because the stress field around a TSV does, so
    the proportional rule binds for r above s_min/(2 koz_ratio) and the cancellation returns.
    """
    p = max(2.0 * r + s_min, 2.0 * r * (1.0 + koz_ratio))
    n = footprint_m2 * pg_ratio / p ** 2
    return rho * h / (math.pi * r_cu ** 2 * n)
