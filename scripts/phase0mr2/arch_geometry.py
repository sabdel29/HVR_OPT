#!/usr/bin/env python3
"""Phase-0M-R2 Section 3 --- THE single source of TSV geometry for every domain.

Every domain -- electrical resistance, thermal homogenisation, mechanical homogenisation
and the feasibility checker -- must read the TSV vertical span from HERE. Three different
answers existed before this module:

    electrical   300 um for ARCH_Z2 (zpower)
    mechanical   280 um for ARCH_Z2 (etm.mesh `sub_lower`)
    feasibility  a hard-coded 100/300/1300 ladder tied to no architecture at all

`assert_consistent()` fails if any two disagree, so the mismatch cannot silently return.
"""
from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr", "scripts/phase0i", "scripts/phase0m", "scripts/phase0b",
          "scripts"):
    sys.path.insert(0, str(R / p))

CFG = R / "configs" / "phase0mr2" / "architecture_geometry.yaml"
OUT = R / "results" / "phase0mr2"

_C: dict | None = None


def cfg() -> dict:
    global _C
    if _C is None:
        _C = yaml.safe_load(CFG.read_text())
    return _C


class GeometryInconsistency(Exception):
    """Two domains disagree about the same physical dimension."""


@dataclass(frozen=True)
class TSVSpan:
    arch: str
    h_sub_um: float
    converter_cell_um: float
    z_start_um: float
    z_end_um: float
    length_um: float
    diameter_um: float
    r_drill_um: float
    liner_um: float
    r_cu_um: float
    pitch_um: float
    aspect_ratio: float
    aspect_ratio_max: float
    feasible_aspect: bool
    rail: str
    voltage_v: float
    rule: str

    def d_min_um(self) -> float:
        """Smallest diameter this span permits at the aspect-ratio ceiling."""
        return self.length_um / self.aspect_ratio_max


def span(arch: str) -> TSVSpan:
    c = cfg()
    m, a = c["meta"], c["architectures"][arch]
    L = a["tsv_z_end_um"] - a["tsv_z_start_um"]
    d = m["tsv_diameter_um"]
    ar = L / d
    return TSVSpan(
        arch=arch, h_sub_um=a["h_sub_mm"] * 1e3,
        converter_cell_um=a["converter_cell_um"],
        z_start_um=a["tsv_z_start_um"], z_end_um=a["tsv_z_end_um"], length_um=L,
        diameter_um=d, r_drill_um=d / 2.0, liner_um=m["liner_um"],
        r_cu_um=d / 2.0 - m["liner_um"], pitch_um=m["tsv_pitch_um"],
        aspect_ratio=ar, aspect_ratio_max=m["aspect_ratio_max"],
        feasible_aspect=ar <= m["aspect_ratio_max"] + 1e-12,
        rail=a["tsv_rail"], voltage_v=a["tsv_voltage_v"], rule=a["tsv_span_rule"])


def electrical_length_um(arch: str) -> float:
    """What zpower.evaluate_z computes, recomputed here from its own rule."""
    import zarch
    c = cfg()["architectures"][arch]
    h_um = c["h_sub_mm"] * 1e3
    rz = zarch.realizable(arch, c["h_sub_mm"])
    if arch == "ARCH_Z1_EMBEDDED":
        return max(h_um - (rz.t_cell_um or 0.0), 0.0)
    return h_um


def mechanical_length_um(arch: str, h_sub_mm: float | None = None) -> float:
    """The z-extent the meshed `tsv_homog` region actually occupies."""
    import numpy as np
    import production_et as PE
    h = h_sub_mm if h_sub_mm is not None else cfg()["architectures"][arch]["h_sub_mm"]
    m, _, _, _ = PE.build_global(arch, h)
    lay = np.asarray(m.elem_layer)
    mat = np.asarray(m.elem_material)
    sel = mat == "tsv_homog"
    if not sel.any():
        return 0.0
    names = set(lay[sel])
    z0 = min(L.z0 for L in m.layers if L.name in names)
    z1 = max(L.z1 for L in m.layers if L.name in names)
    return (z1 - z0) * 1e3


def assert_consistent(arch: str, tol_pct: float = 0.5,
                      mech: float | None = None) -> dict:
    """Electrical, mechanical and contract spans must be the same length.

    Raises GeometryInconsistency otherwise. This is the guard that makes the Phase-0M-R
    state -- 300 um electrically and 280 um mechanically for the same via -- impossible
    to reintroduce.
    """
    s = span(arch)
    e = electrical_length_um(arch)
    m = mechanical_length_um(arch) if mech is None else mech
    out = {"arch": arch, "contract_um": s.length_um, "electrical_um": e,
           "mechanical_um": m}
    for name, v in (("electrical", e), ("mechanical", m)):
        if s.length_um <= 0:
            raise GeometryInconsistency(f"{arch}: contract span is {s.length_um}")
        d = 100.0 * abs(v - s.length_um) / s.length_um
        out[f"{name}_delta_pct"] = d
        if d > tol_pct:
            raise GeometryInconsistency(
                f"{arch}: the {name} model uses {v:.1f} um for the TSV span but the "
                f"architecture contract says {s.length_um:.1f} um ({d:.2f} % apart). "
                f"One physical via cannot have two lengths.")
    out["consistent"] = True
    return out


def field(arch: str, current_a: float, j_design: float = 1.0e8,
          t_c: float = 85.0, footprint_mm2: float | None = None) -> dict:
    """The via field for one architecture, from the ONE geometry source."""
    from interconnect import TSVGeometry
    import tsv_production as TP
    s = span(arch)
    g = TSVGeometry(r_m=s.r_drill_um * 1e-6, h_m=s.length_um * 1e-6,
                    p_m=s.pitch_um * 1e-6, t_liner_m=s.liner_um * 1e-6)
    fp = (footprint_mm2 if footprint_mm2 is not None else 274.89) * 1e-6
    e = TP.evaluate(g, current_a, TP.BUDGET, footprint_m2=fp, t_c=t_c)
    e.update(arch=arch, tsv_length_um=s.length_um, aspect_ratio=s.aspect_ratio,
             aspect_ratio_max=s.aspect_ratio_max, feasible_aspect_contract=s.feasible_aspect,
             d_min_at_ar_max_um=s.d_min_um(), rail=s.rail, voltage_v=s.voltage_v,
             span_rule=s.rule)
    return e


def main() -> int:
    rows_g, rows_f = [], []
    for arch in cfg()["architectures"]:
        s = span(arch)
        rec = asdict(s)
        try:
            rec.update(assert_consistent(arch))
            rec["consistency"] = "OK"
        except GeometryInconsistency as exc:
            rec["consistency"] = f"MISMATCH: {exc}"
        except Exception as exc:                                   # noqa: BLE001
            rec["consistency"] = f"NOT CHECKED: {type(exc).__name__}: {exc}"
        rec["d_min_at_ar_max_um"] = s.d_min_um()
        rows_g.append(rec)
        i = 1000.0 if s.rail == "LV" else 1000.0 / 0.889 / 48.0
        try:
            rows_f.append(field(arch, i))
        except Exception as exc:                                   # noqa: BLE001
            rows_f.append({"arch": arch, "error": f"{type(exc).__name__}: {exc}"})
        print(f"  {arch:22s} L={s.length_um:7.1f} um  AR={s.aspect_ratio:5.2f}  "
              f"d_min@AR10={s.d_min_um():6.1f} um  rail={s.rail:2s}  "
              f"{'OK' if s.feasible_aspect else 'ASPECT VIOLATION'}  "
              f"{rec['consistency'][:60]}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("tsv_geometry_by_architecture.csv", rows_g),
                       ("tsv_feasibility_by_architecture.csv", rows_f)):
        k = sorted({x for r in rows for x in r})
        with open(OUT / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
    print(f"wrote {OUT/'tsv_geometry_by_architecture.csv'} and feasibility")
    return 0


if __name__ == "__main__":
    sys.exit(main())
