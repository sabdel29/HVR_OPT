#!/usr/bin/env python3
"""Phase-0K Sec.8 -- map a mission profile to a reliability demand. Invents nothing.

The tool REFUSES to produce a number from an unpopulated contract. Illustrative examples are
emitted separately and are labelled ILLUSTRATIVE ONLY -- NOT PROJECT REQUIREMENTS.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
CFG = R / "configs" / "phase0k" / "mission_profile.yaml"
OUT = R / "results" / "phase0k"
PLACEHOLDER = {"USER_REQUIRED", "UNKNOWN", "NOT_APPLICABLE", "NOT_POPULATED", "UNPOPULATED"}
DAYS = 365.25


def is_set(v) -> bool:
    """A field counts as set only if it is present AND not a placeholder.

    `None` (key absent, or an empty YAML value) must be treated as NOT set -- otherwise a
    missing key reads as populated and the tool invents a number from nothing, which is the
    one thing this module exists to prevent.
    """
    if v is None:
        return False
    return not (isinstance(v, str) and v.strip() in PLACEHOLDER)


def simple_demand(years, cycles_per_day) -> float:
    """N_required for a single repeated excursion type."""
    return years * DAYS * cycles_per_day


def evaluate(cfg: dict):
    """Return (N_required, provenance) or (None, reason)."""
    if not is_set(cfg.get("mission_source")):
        return None, "mission_source is USER_REQUIRED -- a number without provenance is invalid"
    if not is_set(cfg.get("mission_type")):
        return None, "mission_type is USER_REQUIRED -- Sec.4 category A/B/C must be declared"
    if str(cfg["mission_type"]).upper() == "QUALIFICATION":
        return None, ("mission_type is QUALIFICATION. Sec.22 forbids using a qualification "
                      "count as N_required unless the owner explicitly adopts it as the design "
                      "target, in which case declare it as PRODUCT_DESIGN_REQUIREMENT")
    bins = cfg.get("mission_bins")
    if isinstance(bins, list) and bins:
        return None, ("multi-bin spectrum supplied -- Sec.7 requires bins to be retained "
                      "separately and evaluated against N_f per bin, then combined by the "
                      "source-backed Miner/time-fraction rule. Use evaluate_bins().")
    need = ["service_life_years", "cold_boots_per_day"]
    miss = [k for k in need if not is_set(cfg.get(k))]
    if miss:
        return None, f"unpopulated required fields: {', '.join(miss)}"
    per_day = float(cfg["cold_boots_per_day"])
    for k in ("full_shutdowns_per_day", "high_power_events_per_day"):
        if is_set(cfg.get(k)):
            per_day += float(cfg[k])
    n = simple_demand(float(cfg["service_life_years"]), per_day)
    return n, f"{cfg['mission_type']} declared by {cfg['mission_source']}"


def evaluate_bins(bins, years, nf_by_bin):
    """Miner / time-fraction summation. nf_by_bin maps bin name -> predicted N_f."""
    D = 0.0
    for b in bins:
        n_i = float(b["cycles_per_day"]) * years * DAYS
        D += n_i / float(nf_by_bin[b["name"]])
    return D


def main() -> int:
    cfg = yaml.safe_load(CFG.read_text())
    n, why = evaluate(cfg)
    print("=== live mission contract ===")
    print(f"  configs/phase0k/mission_profile.yaml -> "
          f"{'N_required = %.0f' % n if n else 'NO REQUIREMENT'}")
    print(f"  reason: {why}")

    rows = []
    for lab, yrs, boots, wl in (
            ("A: 5 y, 1 cold boot/day, no workload cycling", 5, 1, 0),
            ("B: 5 y, 1 cold boot/day + 4 deep workload cycles/day", 5, 1, 4),
            ("C: 7 y, 2 cold boots/week, 1 deep workload cycle/day", 7, 2 / 7, 1),
            ("D: 10 y, 1 cold boot/month, 24 deep workload cycles/day", 10, 1 / 30.4, 24),
            ("E: 3 y, continuous duty, never powered down", 3, 0, 0)):
        tot = boots + wl
        rows.append({"label": "ILLUSTRATIVE ONLY -- NOT PROJECT REQUIREMENTS",
                     "scenario": lab, "service_life_years": yrs,
                     "cold_boots_per_day": round(boots, 4),
                     "deep_workload_cycles_per_day": wl,
                     "total_deep_excursions_per_day": round(tot, 4),
                     "N_required": round(simple_demand(yrs, tot)) if tot else 0,
                     "note": ("no deep thermal excursion at all -- solder fatigue from this "
                              "mechanism is then not life-limiting" if not tot else "")})
    f = OUT / "mission_requirement_examples.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}")
    print(f"\n{'scenario':56} {'N_required':>11}")
    for r in rows:
        print(f"  {r['scenario']:54} {r['N_required']:>11}")
    print("\n  ILLUSTRATIVE ONLY. None of these is a project requirement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
