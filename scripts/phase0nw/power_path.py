"""PHASE 0N-Y --- the complete rail-aware physical power path, 48 V board to 1 V die.

THE QUESTION THIS ANSWERS: does every horizontal and vertical conductor from the board
input to the die load have EXACTLY ONE electrical loss owner?

Structure first, numbers second. Every segment is enumerated with its rail, direction,
physical tier and ledger owner, and the graph is checked for three failures that a loss
table alone cannot show:

  * an UNOWNED segment -- a real conductor with no ledger term, so its loss is silently
    zero;
  * a DOUBLE-OWNED segment -- two terms covering one conductor, so its loss is counted
    twice (research/phase0ns/lateral_rdl_loss.json already caught one of these: the Z2
    residual lateral 1 V strip was not an additional term because the RDL network solve
    already contained that path);
  * a BROKEN CHAIN -- a path whose segments do not actually connect source to load.

RAIL ASSIGNMENT IS THE POINT. The same geometric segment carries wildly different
current depending on which side of the conversion it sits on:

    Z1   48 V at ~23.7 A crosses the substrate, converts INSIDE the substrate,
         then 1 V at ~1000 A goes up through microbumps to the die.
    Z2   48 V at ~23.7 A reaches the cells laterally on the land side, converts BELOW
         the substrate, then 1 V at ~1000 A crosses the substrate itself.

So "the TSV field" means 23.7 A in one architecture and 1000 A in the other, and a
segment table that does not carry the rail cannot express that.

LOSS VALUES ARE NOT FILLED IN HERE. Each segment carries a `loss_status`: RECOMPUTED
when a physical value exists for the new geometry, HISTORICAL_REFERENCE when only the
Phase-0M-R3C value exists, or OPEN. Phase-0M-R3C numbers are references, never physical
results, and the gate registry keeps the corresponding gates open.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0i", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

# ---------------------------------------------------------------------------- ledger
# One owner per conductor. These are the ONLY legal owners; a segment naming anything
# else is rejected, which is what stops a new term quietly appearing beside an old one.
LEDGER_OWNERS = (
    # converter intrinsic -- devices and passives, never interconnect
    "P_switch_hs_conduction", "P_switch_ls_conduction", "P_switching_hard",
    "P_gate", "P_Coss", "P_inductor_DCR", "P_cap_ESR",
    # intra-VR interconnect
    "P_intraVR_metal", "P_intraVR_vertical",
    # package vertical
    "P_BGA_supply", "P_BGA_return",
    "P_microbump_supply", "P_microbump_return",
    "P_TSV_VDD", "P_TSV_GND",
    # package lateral, split by rail because an ohm at 48 V and an ohm at 1 V are not
    # the same architectural object
    "P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return",
    "P_pkg_RDL_LV_supply", "P_pkg_RDL_LV_return",
)
CONVERTER_INTRINSIC = LEDGER_OWNERS[:7]
INTERCONNECT_OWNERS = LEDGER_OWNERS[7:]

LOSS_STATUS = ("RECOMPUTED", "HISTORICAL_REFERENCE", "OPEN")


@dataclass(frozen=True)
class Segment:
    seg_id: str
    frm: str
    to: str
    arch: str
    location: str           # physical tier / region
    orientation: str        # 'vertical' | 'horizontal'
    rail_v: float
    i_dc_a: float
    owner: str
    loss_status: str
    note: str = ""
    i_rms_a: float | None = None
    conductor: str = "copper"
    length_mm: float | None = None
    width_mm: float | None = None
    thickness_mm: float | None = None
    count: int | None = None
    r_ohm: float | None = None
    p_w: float | None = None
    t_C: float | None = None

    def __post_init__(self):
        if self.owner not in LEDGER_OWNERS:
            raise ValueError(f"{self.seg_id}: '{self.owner}' is not a ledger owner")
        if self.loss_status not in LOSS_STATUS:
            raise ValueError(f"{self.seg_id}: bad loss_status {self.loss_status!r}")
        if self.orientation not in ("vertical", "horizontal"):
            raise ValueError(f"{self.seg_id}: bad orientation {self.orientation!r}")


def _cells():
    from physical_package import load_physical_package_config
    return load_physical_package_config(R / "configs/phase0nt/z2_2p4mm_cutout.yaml").cells


def rail_currents():
    """System and per-cell currents on each rail, from the power ledger."""
    import tsv_fields as TSV
    from physical_package import load_physical_package_config
    cfg = load_physical_package_config(R / "configs/phase0nt/z2_2p4mm_cutout.yaml")
    hv = TSV.z1_rail_report(cfg)["i_total_a"]        # (P_load + P_loss)/48
    lv = 1000.0
    return {"hv_total_a": hv, "lv_total_a": lv, "cells": cfg.cells,
            "hv_cell_a": hv / cfg.cells, "lv_cell_a": lv / cfg.cells}


def z1_segments() -> list:
    """Z1: convert INSIDE the substrate. 48 V crosses the substrate, 1 V goes to the die."""
    c = rail_currents()
    HV, LV, HVc, LVc, n = (c["hv_total_a"], c["lv_total_a"], c["hv_cell_a"],
                           c["lv_cell_a"], c["cells"])
    S, OPEN, HIST = Segment, "OPEN", "HISTORICAL_REFERENCE"
    return [
        S("Z1-S01", "PCB 48 V plane", "package underside", "Z1", "bga", "vertical",
          48.0, HV, "P_BGA_supply", OPEN, count=16,
          note="annular package; must use surviving-site coordinates, not a full board"),
        S("Z1-S02", "package underside", "substrate underside", "Z1", "board/bga pad",
          "horizontal", 48.0, HV, "P_pkg_RDL_HV_supply", OPEN,
          note="48 V spreading from the BGA ring to the TSV field footprint"),
        S("Z1-S03", "substrate underside", "bottom-substrate RDL", "Z1", "sub_lower",
          "vertical", 48.0, HV, "P_TSV_VDD", OPEN, count=None,
          note="48 V through-substrate field; LOW current -- this is the architectural "
               "distinction from Z2"),
        S("Z1-S04", "bottom-substrate RDL", "HVR cell input", "Z1",
          "z1conv_0_bottom_substrate_rdl", "horizontal", 48.0, HVc,
          "P_intraVR_metal", HIST, count=n,
          note="per-cell 48 V input bus; historical reference only"),
        S("Z1-S05", "HVR cell input", "HVR cell output", "Z1", "z1conv_1..7",
          "vertical", 48.0, HVc, "P_intraVR_vertical", HIST, count=n,
          note="inter-tier via stacks inside the cell; rail changes along the chain "
               "(48 V in, ~16 V mid, 1 V out) so one representative current is wrong"),
        S("Z1-S06", "HVR cell output", "output RDL", "Z1", "z1conv_8_output_rdl",
          "horizontal", 1.0, LVc, "P_intraVR_metal", HIST, count=n,
          note="1 V collection at ~20.4 A/cell"),
        S("Z1-S07", "output RDL", "microbump field", "Z1", "z1conv_8_output_rdl",
          "horizontal", 1.0, LV, "P_pkg_RDL_LV_supply", OPEN,
          note="1 V spreading from 49 cells to the die POL grid"),
        S("Z1-S08", "microbump field", "die POL", "Z1", "interface", "vertical",
          1.0, LV, "P_microbump_supply", OPEN),
        # ---- return path. NOT assumed symmetric with supply. -----------------------
        S("Z1-R01", "die ground", "microbump field", "Z1", "interface", "vertical",
          1.0, LV, "P_microbump_return", OPEN),
        S("Z1-R02", "microbump field", "output RDL ground", "Z1",
          "z1conv_8_output_rdl", "horizontal", 1.0, LV, "P_pkg_RDL_LV_return", OPEN),
        S("Z1-R03", "output RDL ground", "HVR cell return", "Z1", "z1conv_1..8",
          "vertical", 1.0, LVc, "P_intraVR_vertical", HIST, count=n),
        S("Z1-R04", "HVR cell return", "substrate GND field", "Z1",
          "z1conv_0_bottom_substrate_rdl", "horizontal", 48.0, HVc,
          "P_intraVR_metal", HIST, count=n),
        S("Z1-R05", "substrate GND field", "package underside", "Z1", "sub_lower",
          "vertical", 48.0, HV, "P_TSV_GND", OPEN),
        S("Z1-R06", "package underside", "BGA return", "Z1", "board/bga pad",
          "horizontal", 48.0, HV, "P_pkg_RDL_HV_return", OPEN),
        S("Z1-R07", "BGA return", "PCB ground", "Z1", "bga", "vertical",
          48.0, HV, "P_BGA_return", OPEN, count=16),
    ]


def z2_segments() -> list:
    """Z2: convert BELOW the substrate. 48 V spreads laterally, 1 V crosses the substrate."""
    c = rail_currents()
    HV, LV, HVc, LVc, n = (c["hv_total_a"], c["lv_total_a"], c["hv_cell_a"],
                           c["lv_cell_a"], c["cells"])
    S, OPEN, HIST = Segment, "OPEN", "HISTORICAL_REFERENCE"
    return [
        S("Z2-S01", "PCB 48 V plane", "package periphery", "Z2", "bga", "vertical",
          48.0, HV, "P_BGA_supply", OPEN, count=16,
          note="PERIPHERAL only -- 841 of 1369 sites are removed by the cutout"),
        S("Z2-S02", "package periphery", "HVR cell input", "Z2",
          "conv_0_land_side_attach_rdl", "horizontal", 48.0, HV,
          "P_pkg_RDL_HV_supply", OPEN,
          note="48 V spreading ACROSS the opening to 49 land-side cells. This path has "
               "no Z1 counterpart and is the longest HV lateral run in either design"),
        S("Z2-S03", "HVR cell input", "HVR cell output", "Z2", "conv_7..1", "vertical",
          48.0, HVc, "P_intraVR_vertical", HIST, count=n,
          note="inter-tier via stacks; rail changes along the chain"),
        S("Z2-S04", "HVR cell output", "cell output RDL", "Z2", "conv_2/4/6 rdl",
          "horizontal", 1.0, LVc, "P_intraVR_metal", HIST, count=n),
        S("Z2-S05", "cell output RDL", "substrate underside", "Z2",
          "conv_0_land_side_attach_rdl", "horizontal", 1.0, LVc,
          "P_intraVR_metal", HIST, count=n,
          note="1 V collection to the TSV footprint"),
        S("Z2-S06", "substrate underside", "top RDL", "Z2", "sub_lower", "vertical",
          1.0, LV, "P_TSV_VDD", OPEN,
          note="1 V through-substrate field at ~1000 A -- 42x the Z1 rail current, so "
               "~1781x the Joule loss through the same geometry"),
        S("Z2-S07", "top RDL", "microbump field", "Z2", "z2_top_rdl", "horizontal",
          1.0, LV, "P_pkg_RDL_LV_supply", OPEN),
        S("Z2-S08", "microbump field", "die POL", "Z2", "interface", "vertical",
          1.0, LV, "P_microbump_supply", OPEN),
        # ---- return ----------------------------------------------------------------
        S("Z2-R01", "die ground", "microbump field", "Z2", "interface", "vertical",
          1.0, LV, "P_microbump_return", OPEN),
        S("Z2-R02", "microbump field", "top RDL ground", "Z2", "z2_top_rdl",
          "horizontal", 1.0, LV, "P_pkg_RDL_LV_return", OPEN),
        S("Z2-R03", "top RDL ground", "substrate GND field", "Z2", "sub_lower",
          "vertical", 1.0, LV, "P_TSV_GND", OPEN),
        S("Z2-R04", "substrate GND field", "HVR cell return", "Z2",
          "conv_0_land_side_attach_rdl", "horizontal", 1.0, LVc,
          "P_intraVR_metal", HIST, count=n),
        S("Z2-R05", "HVR cell return", "land-side return plane", "Z2", "conv_1..7",
          "vertical", 48.0, HVc, "P_intraVR_vertical", HIST, count=n),
        S("Z2-R06", "land-side return plane", "package periphery", "Z2",
          "conv_0_land_side_attach_rdl", "horizontal", 48.0, HV,
          "P_pkg_RDL_HV_return", OPEN),
        S("Z2-R07", "package periphery", "PCB ground", "Z2", "bga", "vertical",
          48.0, HV, "P_BGA_return", OPEN, count=16),
    ]


def graph(arch: str) -> list:
    return {"Z1": z1_segments, "Z2": z2_segments}[arch]()


def ownership_table() -> dict:
    """Which owner term covers which segments, per architecture."""
    out = {}
    for arch in ("Z1", "Z2"):
        m = {}
        for s in graph(arch):
            m.setdefault(s.owner, []).append(s.seg_id)
        out[arch] = m
    return out


def check(arch: str) -> dict:
    """Ownership and rail-assignment checks for one architecture."""
    segs = graph(arch)
    ids = [s.seg_id for s in segs]
    problems = []

    if len(set(ids)) != len(ids):
        problems.append("duplicate segment ids")

    # every interconnect owner must appear; an absent owner means an unmodelled conductor
    used = {s.owner for s in segs}
    missing = [o for o in INTERCONNECT_OWNERS if o not in used]
    if missing:
        problems.append(f"interconnect owners with no segment: {missing}")

    # converter-intrinsic owners must NOT appear here: devices are not interconnect
    intrinsic = [s.seg_id for s in segs if s.owner in CONVERTER_INTRINSIC]
    if intrinsic:
        problems.append(f"converter-intrinsic owner used for a conductor: {intrinsic}")

    # rail sanity: the 1 kA rail must never appear on a 48 V segment and vice versa
    c = rail_currents()
    for s in segs:
        if s.rail_v == 48.0 and s.i_dc_a > 2 * c["hv_total_a"]:
            problems.append(f"{s.seg_id}: {s.i_dc_a} A on a 48 V segment")
        if s.rail_v == 1.0 and s.i_dc_a > c["lv_total_a"] * 1.01:
            problems.append(f"{s.seg_id}: {s.i_dc_a} A exceeds the 1 V rail current")

    # the supply chain must reach the die, and the return must leave it
    supply = [s for s in segs if s.seg_id.split("-")[1].startswith("S")]
    ret = [s for s in segs if s.seg_id.split("-")[1].startswith("R")]
    if not supply or "die" not in supply[-1].to.lower():
        problems.append("supply chain does not terminate at the die")
    if not ret or "die" not in ret[0].frm.lower():
        problems.append("return chain does not start at the die")
    for a, b in zip(supply, supply[1:]):
        if a.to != b.frm:
            problems.append(f"supply chain broken: {a.seg_id} -> {b.seg_id} "
                            f"({a.to!r} != {b.frm!r})")

    return {"arch": arch, "n_segments": len(segs), "problems": problems,
            "ok": not problems,
            "n_open": sum(1 for s in segs if s.loss_status == "OPEN"),
            "n_historical": sum(1 for s in segs
                                if s.loss_status == "HISTORICAL_REFERENCE"),
            "n_recomputed": sum(1 for s in segs if s.loss_status == "RECOMPUTED")}


def write_csv(out_dir=None) -> list:
    out_dir = Path(out_dir) if out_dir else (R / "research" / "phase0ny")
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    cols = ["seg_id", "frm", "to", "arch", "location", "orientation", "rail_v",
            "i_dc_a", "i_rms_a", "t_C", "conductor", "length_mm", "width_mm",
            "thickness_mm", "count", "r_ohm", "p_w", "owner", "loss_status", "note"]
    for arch in ("Z1", "Z2"):
        p = out_dir / f"power_path_{arch}.csv"
        with p.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for s in graph(arch):
                w.writerow({k: asdict(s)[k] for k in cols})
        paths.append(p)
    summary = {"rail_currents": rail_currents(),
               "ownership": ownership_table(),
               "checks": {a: check(a) for a in ("Z1", "Z2")},
               "ledger_owners": list(LEDGER_OWNERS)}
    (out_dir / "power_path_summary.json").write_text(json.dumps(summary, indent=1))
    return paths


if __name__ == "__main__":
    c = rail_currents()
    print(f"HV rail {c['hv_total_a']:.4f} A system, {c['hv_cell_a']:.4f} A/cell")
    print(f"LV rail {c['lv_total_a']:.1f} A system, {c['lv_cell_a']:.4f} A/cell\n")
    for arch in ("Z1", "Z2"):
        r = check(arch)
        print(f"{arch}: {r['n_segments']} segments  ok={r['ok']}  "
              f"OPEN {r['n_open']}  historical {r['n_historical']}  "
              f"recomputed {r['n_recomputed']}")
        for p in r["problems"]:
            print("   PROBLEM:", p)
    for p in write_csv():
        print("wrote", p.relative_to(R))
