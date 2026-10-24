"""PHASE 0N-W --- 1-D stack conservation, PCB backside to TIM top (brief section 10).

Every layer must be accounted for EXACTLY ONCE: no gaps, no double counting, and the
thicknesses must sum to the measured package height. Two defects this audit exists to
catch, both of which it did catch:

  * Z1 carried a separate microbump layer AND the production `interface` layer, which is
    itself the "microbumps + underfill" row. The package top came out at 5343 um.
  * Z2 was MISSING the 10 um top RDL (3000 -> 3010). The `interface` layer silently stood
    in for it, so the microbump row vanished and the package top came out at 3360 um.

Neither error changed the converter total, so neither was visible from the tier report.

Z2 NEEDS TWO COLUMNS. Its converter descends into the cutout, so the stack depends on
where you stand: in the periphery you pass through PCB and BGA, and over the opening you
pass through the HVR instead. Both columns must tile the z axis contiguously, and they
must meet at the same land-side interface.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts/phase0nw"))
from physical_package import measure_layers                          # noqa: E402

TOL_UM = 1e-6


def columns(mesh, cutout_mm: float | None) -> dict:
    """Ordered layer list for each lateral region, from the measured mesh.

    A layer belongs to a column if any of its elements fall in that region.
    """
    cen = mesh.elem_centroids()
    lay = np.array(mesh.elem_layer)
    inside = None
    if cutout_mm:
        inside = (np.abs(cen[:, 0]) < cutout_mm / 2) & (np.abs(cen[:, 1]) < cutout_mm / 2)

    full = measure_layers(mesh)
    if inside is None:
        return {"single": sorted(full.items(), key=lambda kv: kv[1]["z0_um"])}
    return {
        "cutout": sorted(((k, v) for k, v in full.items() if k in set(lay[inside])),
                         key=lambda kv: kv[1]["z0_um"]),
        "periphery": sorted(((k, v) for k, v in full.items() if k in set(lay[~inside])),
                            key=lambda kv: kv[1]["z0_um"]),
    }


def check_column(rows) -> dict:
    """Contiguity and conservation for one ordered column."""
    gaps, overlaps = [], []
    for (n0, a), (n1, b) in zip(rows, rows[1:]):
        d = b["z0_um"] - a["z1_um"]
        if d > TOL_UM:
            gaps.append((n0, n1, d))
        elif d < -TOL_UM:
            overlaps.append((n0, n1, -d))
    span = rows[-1][1]["z1_um"] - rows[0][1]["z0_um"]
    total = sum(v["t_um"] for _n, v in rows)
    return {"n_layers": len(rows), "span_um": span, "sum_t_um": total,
            "gaps": gaps, "overlaps": overlaps,
            "conserved": not gaps and not overlaps and abs(span - total) < 1e-6}


def audit(mesh, cutout_mm: float | None) -> dict:
    cols = columns(mesh, cutout_mm)
    return {name: {"rows": [(n, round(v["z0_um"], 3), round(v["z1_um"], 3),
                             round(v["t_um"], 3)) for n, v in rows],
                   **check_column(rows)}
            for name, rows in cols.items()}


def report(mesh, cutout_mm, label, datum_um=None):
    a = audit(mesh, cutout_mm)
    out = [f"### {label}"]
    for name, c in a.items():
        off = datum_um if datum_um is not None else 0.0
        out.append(f"\n**{name}** — {c['n_layers']} layers, span "
                   f"{c['span_um']:.1f} um, sum of thicknesses {c['sum_t_um']:.1f} um, "
                   f"conserved = {c['conserved']}")
        out.append("")
        out.append("| layer | z0 | z1 | t |")
        out.append("|---|---:|---:|---:|")
        for n, z0, z1, t in c["rows"]:
            out.append(f"| {n} | {z0-off:.1f} | {z1-off:.1f} | {t:.1f} |")
        if c["gaps"]:
            out.append(f"\n**GAPS:** {c['gaps']}")
        if c["overlaps"]:
            out.append(f"\n**OVERLAPS:** {c['overlaps']}")
    return "\n".join(out)
