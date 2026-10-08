#!/usr/bin/env python3
"""Phase-0M-R Section 2 -- the AUTHORITATIVE CURRENT-STATE CONTRACT.

DEFECT #53. Both reports are generated from results/CURRENT_SCIENTIFIC_STATUS.yaml, so
comparing them against EACH OTHER passes whenever they are stale in the same way. They were.
The section headed "Current scientific status (Phase 0M)" printed a Phase-0M verdict line
followed by six Phase-0H basis bullets and a Phase-0I next-gate rationale.

The fix is a single, explicit CONTRACT of what is true NOW, one field per question an
auditor would ask, each carrying its own evidence path. Every current-facing generated
section in both reports derives from it, and a test mutates a contract field to prove both
reports fail until regenerated.

This module OWNS the contract. It does not duplicate the source of truth: the contract lives
in the existing authoritative YAML under `current_state_contract`, and this file is the
generator and the validator for that block.
"""
from __future__ import annotations
import sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
Y = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"

FIELDS = (
    "current_phase", "current_verdict", "current_ET_coupling_level",
    "current_mechanical_capability", "current_solder_metric_status",
    "current_constitutive_status", "current_life_law_status",
    "current_required_life_status", "current_G2_status", "current_optimizer_status",
    "current_cooling_status", "current_routing_status",
    "current_current_crowding_status", "current_RDL_anisotropy_status",
    "current_component_partition_status", "current_next_work",
)


def load() -> dict:
    d = yaml.safe_load(Y.read_text())
    c = d.get("current_state_contract")
    if c is None:
        raise KeyError("current_state_contract is missing from the authoritative YAML")
    missing = [f for f in FIELDS if f not in c]
    if missing:
        raise KeyError(f"contract is missing required fields: {missing}")
    for f in FIELDS:
        v = c[f]
        if not isinstance(v, dict) or "state" not in v or "evidence" not in v:
            raise TypeError(f"contract field {f} must be a mapping with 'state' and "
                            f"'evidence'; got {type(v).__name__}")
        p = R / v["evidence"].split("::")[0].split(",")[0].strip()
        if not p.exists():
            raise FileNotFoundError(f"contract field {f}: evidence path does not exist: {p}")
    return c


def state(f: str) -> str:
    return load()[f]["state"]


def as_markdown() -> str:
    """The contract rendered as the current-state table both reports must carry."""
    c = load()
    L = ["<!-- BEGIN GENERATED: current_state_contract -->",
         "<!-- Generated from results/CURRENT_SCIENTIFIC_STATUS.yaml::current_state_contract",
         "     by scripts/phase0mr/state_contract.py. DO NOT EDIT BY HAND. -->", "",
         "| question | current answer | evidence |", "|---|---|---|"]
    for f in FIELDS:
        v = c[f]
        L.append(f"| {f.replace('current_', '').replace('_', ' ')} | "
                 f"**{v['state']}** | `{v['evidence']}` |")
    L += ["", f"*Contract version {c.get('contract_version', '?')}, "
              f"{c.get('date', '?')}. Every current-facing statement in this report and in "
              f"the standalone audit report is generated from this table. A statement that "
              f"contradicts it is a defect, not a difference of emphasis.*", "",
          "<!-- END GENERATED: current_state_contract -->", ""]
    return "\n".join(L)


def main() -> int:
    c = load()
    print(f"contract version {c.get('contract_version')} ({c.get('date')}), "
          f"{len(FIELDS)} fields, all evidence paths exist")
    for f in FIELDS:
        print(f"  {f:38s} {c[f]['state'][:74]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
