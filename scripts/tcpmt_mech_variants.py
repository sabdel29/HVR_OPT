"""Material variants of the mechanics revision, from configs/tcpmt_mech (findings 7, 11).

  encapsulant (finding 7)  the out-of-cell converter fill (underfill_homog of the physical
                           builders) as a capillary underfill or a low-CTE mold compound WITH
                           its glass transition: E(T) logistic between the glassy and rubbery
                           moduli, the instantaneous CTE switching from alpha1 to alpha2 over
                           the same width, written as the SECANT CTE about the stress-free
                           temperature (*EXPANSION, ZERO=). Conductivity is untouched, so the
                           variants run on the converged fields (mechanics only).
  bga_card_local (11a)     the homogenised BGA layer from the LOCAL solder card -- E(T), nu
                           and CTE of tcpmt_mech_laws -- smeared by the ball area fraction,
                           instead of board.py's STAMP-2.5D values (E 20 GPa, 20.5 ppm/K).

Every number comes from the config or from the stack the builder assembled, so a tier card
merged into the stack flows through unchanged. The hooks are BUILD_HOOKS of
final_closure_physical_etm (applied after the builders' own material assignment).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_mech_laws as LAW                                       # noqa: E402


def _rows(a, b, s):
    n = int(round((b - a) / s)) + 1
    return [round(a + s * k, 6) for k in range(n)]


def encap_tables(v: dict, t_ref: float = 25.0, rows=None):
    """[(T, E)], [(T, alpha_secant)] of one encapsulant variant."""
    rows = rows or _rows(*LAW.cfg()["encapsulant"]["T_rows_C"])
    Eg, Er = float(v["E_g_MPa"]), float(v["E_r_MPa"])
    a1, a2 = float(v["alpha1_per_K"]), float(v["alpha2_per_K"])
    Tg, w = float(v["Tg_C"]), float(v["width_K"])

    def E(T):
        return Er + (Eg - Er) / (1.0 + math.exp((T - Tg) / w))

    def strain(T):                       # integral of the logistic instantaneous CTE
        sp = lambda t: w * math.log1p(math.exp((t - Tg) / w))      # noqa: E731
        return a1 * (T - t_ref) + (a2 - a1) * (sp(T) - sp(t_ref))

    def inst(T):
        return a1 + (a2 - a1) / (1.0 + math.exp(-(T - Tg) / w))
    sec = [(T, strain(T) / (T - t_ref) if abs(T - t_ref) > 1e-9 else inst(T)) for T in rows]
    return [(T, E(T)) for T in rows], sec


def encap_card(name: str, base: dict, t_ref: float = 25.0) -> dict:
    v = LAW.cfg()["encapsulant"]["variants"][name]
    E_T, cte_T = encap_tables(v, t_ref)
    c = dict(base)
    c.update({"status": "ASSUMPTION", "elastic_type": "iso",
              "E": {"value": dict(E_T)[min(dict(E_T), key=lambda T: abs(T - t_ref))],
                    "status": "ASSUMPTION"},
              "nu": {"value": float(v["nu"]), "status": "ASSUMPTION"},
              "cte": {"value": float(v["alpha1_per_K"]), "status": "ASSUMPTION"},
              "E_T": E_T, "cte_T": cte_T,
              "note": f"encapsulant variant {name}: {v['what']} ({v['source']})"})
    return c


def encap_hook(name: str):
    mat = LAW.cfg()["encapsulant"]["material"]

    def hook(m, st, tiles, _n=name):
        t_ref = st["structural_bc"]["t_ref"]["value"]
        st["materials"][mat] = encap_card(_n, st["materials"][mat], t_ref)
        n_el = int(sum(1 for x in m.elem_material if x == mat))
        return {"encapsulant_variant": _n, "encapsulant_material": mat,
                "encapsulant_elements": n_el}
    return hook


def bga_local_card(base: dict, t_ref: float = 25.0) -> dict:
    import board as BRD
    f = BRD.AREA_FRACTION
    rows = LAW.rows_C()
    c = dict(base)
    c.update({"status": "DERIVED", "elastic_type": "iso",
              "E": {"value": f * LAW.E_of_T(t_ref), "status": "DERIVED"},
              "nu": {"value": LAW.nu(), "status": "ASSUMPTION"},
              "cte": {"value": LAW.cte(), "status": "ASSUMPTION"},
              "E_T": [(T, f * LAW.E_of_T(T)) for T in rows],
              "note": "BGA layer from the local solder card (tcpmt_mech_laws), smeared by "
                      f"the ball area fraction {f:.5f}"})
    return c


def bga_local_hook():
    def hook(m, st, tiles):
        t_ref = st["structural_bc"]["t_ref"]["value"]
        old = st["materials"]["bga_homog"]
        st["materials"]["bga_homog"] = bga_local_card(old, t_ref)
        v = lambda x: x["value"] if isinstance(x, dict) else x       # noqa: E731
        return {"bga_card": "local solder card", "bga_E_25C_MPa":
                st["materials"]["bga_homog"]["E"]["value"], "bga_E_prod_MPa": v(old["E"]),
                "bga_cte": LAW.cte(), "bga_cte_prod": v(old["cte"])}
    return hook


def register(VARIANTS: dict, apply_hook):
    """Add the round-3 variants to final_closure_sensitivity.VARIANTS. apply_hook(fn)
    appends a BUILD_HOOK in the variant's process."""
    cfg = LAW.cfg()
    for name, v in cfg["encapsulant"]["variants"].items():
        VARIANTS[name] = dict(kind="mech", archs=("Z1", "Z2", "Z3"),
                              apply=(lambda n=name: apply_hook(encap_hook(n))),
                              gates=["mat.encapsulant_card"],
                              nature="declared range (encapsulant class, finding 7)",
                              what=f"out-of-cell encapsulant: {v['what']}")
    VARIANTS[cfg["bga_global"]["reconciled_variant"]] = dict(
        kind="mech", archs=("Z1", "Z2", "Z3"), apply=lambda: apply_hook(bga_local_hook()),
        gates=["mat.bga_card_consistency"], nature="model-form check (finding 11a)",
        what="homogenised BGA layer from the local solder card E(T), nu, CTE")
