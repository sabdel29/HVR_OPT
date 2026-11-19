#!/usr/bin/env python3
"""Fingerprint of the 49-cell production builds (Z1, Z2, Z3), for the count generalization.

Generalizing the chain to another cell count and topology must leave every existing 49-cell
result byte-identical. This records, per architecture and mesh level, everything a result is
computed from:

  mesh       node/element counts, SHA-256 of coordinates, connectivity, element material,
             layer and tile tags, the layer list and the tile list
  materials  the stack's material dictionary after build() (TSV and RDL cards included) and
             every CalculiX material card the decks are written from
  ledgers    FL.ledger at fixed per-region temperatures and FL.self_consistent, for
             HV_S0 / HV_S1 / HV_S2, every row
  deposits   final_closure_physical_etm.deposits_from_ledger for each scenario
  regions    the temperature-region node sets of the E-T fixed point
  decks      SHA-256 of the thermal deck written by final_closure_physical_etm.write_thermal and
             of the structural deck written by final_closure_physical_etm.mechanics (the solve
             is intercepted after the deck is written), on deterministic synthetic inputs

    python -B fingerprint_49.py OUT.json [--archs Z1,Z2,Z3] [--refine 11,21]

Run once on the tree before the change and once after; compare_fingerprints() diffs them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(R / "scripts"))
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m", "scripts/phase0i",
           "scripts/phase0g", "scripts/phase0b"):
    sys.path.insert(0, str(R / _p))

#: distinct per-region temperatures so that a term evaluated at the wrong region shows up
TEMPS = {"conv": 101.0, "hs": 103.0, "ls": 99.0, "ind": 97.0, "caps": 95.0, "bga": 70.0,
         "sub": 90.0, "interface": 88.0, "attach": 93.0, "pcb_via": 80.0}
I_HV = 23.7
SCENARIOS = ("HV_S0", "HV_S1", "HV_S2")


def sha(b) -> str:
    if isinstance(b, str):
        b = b.encode()
    return hashlib.sha256(b).hexdigest()


def jdump(o) -> str:
    return json.dumps(o, sort_keys=True, default=repr)


class _Stop(Exception):
    pass


def fingerprint(arch: str, h_xy: float, refine: tuple) -> dict:
    import final_closure_ledger as FL
    import final_closure_physical_etm as E
    import production_et as PE
    t0 = time.time()
    m, mats, st, tiles, info = E.build(arch, h_xy, refine)
    out = {"arch": arch, "h_xy": h_xy, "refine": list(refine),
           "n_nodes": int(m.n_nodes), "n_elems": int(m.n_elems),
           "nodes_sha": sha(np.ascontiguousarray(m.nodes, dtype=np.float64).tobytes()),
           "elems_sha": sha(np.ascontiguousarray(m.elems, dtype=np.int64).tobytes()),
           "elem_material_sha": sha("\n".join(map(str, m.elem_material))),
           "elem_layer_sha": sha("\n".join(map(str, m.elem_layer))),
           "elem_tile_sha": sha(np.ascontiguousarray(np.asarray(m.elem_tile),
                                                     dtype=np.int64).tobytes()),
           "layers": [[L.name, repr(L.z0), repr(L.z1)] for L in m.layers],
           "tiles": [[repr(t.cx), repr(t.cy), repr(t.ax), repr(t.ay)] for t in tiles],
           "build_info": json.loads(jdump(info)),
           "stack_materials_sha": sha(jdump(st["materials"])),
           "material_cards": {k: sha(jdump([v.ccx_elastic(), v.ccx_conductivity(),
                                            repr(v.cte)]))
                              for k, v in sorted(mats.items())},
           "LAYERS": FL.LAYERS[arch],
           "temperature_regions": json.loads(jdump(E.temperature_regions(arch)))}
    regs = {}
    for k, (layers, in_t) in E.temperature_regions(arch).items():
        nd = E.region_nodes(m, tiles, layers, in_t)
        regs[k] = [int(len(nd)), sha(np.asarray(nd, dtype=np.int64).tobytes())]
    out["region_nodes"] = regs
    out["ledger"], out["self_consistent"], out["deposits"] = {}, {}, {}

    def unstamped(L):
        """review round 2 stamps each converter row with the converter lineage it was
        evaluated with (electrical.rules_of reads it back); the stamp is provenance, not a
        ledger value, so the fingerprint compares the ledger without it"""
        L = dict(L)
        L["rows"] = [{k: v for k, v in r.items() if k != "converter"} for r in L["rows"]]
        return L
    for scen in SCENARIOS:
        L = unstamped(FL.ledger(arch, scen, TEMPS, I_HV))
        out["ledger"][scen] = {"P_loss_w": repr(L["P_loss_w"]), "n_rows": len(L["rows"]),
                               "rows_sha": sha(jdump(L["rows"])),
                               "all_sha": sha(jdump({k: v for k, v in L.items()}))}
        S = unstamped(FL.self_consistent(arch, scen, TEMPS))
        out["self_consistent"][scen] = {"P_loss_w": repr(S["P_loss_w"]),
                                        "i_hv_avg_a": repr(S["i_hv_avg_a"]),
                                        "all_sha": sha(jdump(S))}
        dep = E.deposits_from_ledger(arch, S)
        out["deposits"][scen] = [[list(k[0]), bool(k[1]), repr(w)]
                                 for k, w in sorted(dep.items(), key=lambda kv: repr(kv[0]))]
    # ---- the decks, on deterministic synthetic inputs ---------------------------------
    dep = E.deposits_from_ledger(arch, FL.self_consistent(arch, "HV_S0", TEMPS))
    top = PE.ccxio.top_film_faces(m)
    h_face = np.linspace(5.0e3, 2.0e4, len(top))
    t_face = np.linspace(30.0, 45.0, len(top))
    xyz = m.nodes
    Tn = 25.0 + 60.0 * np.exp(-(xyz[:, 0] ** 2 + xyz[:, 1] ** 2) / 200.0) + 5.0 * xyz[:, 2]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        E.write_thermal(m, mats, st, dep, h_face, t_face, td / "th.inp", tiles, arch=arch)
        out["thermal_deck_sha"] = sha((td / "th.inp").read_bytes())
        orig = PE.ccxio.run_ccx

        def stop(*a, **k):
            raise _Stop()
        PE.ccxio.run_ccx = stop
        try:
            E.mechanics(m, mats, st, Tn, td / "mech", arch, tiles, E.PRODUCTION_SOLVER, 1)
        except _Stop:
            pass
        finally:
            PE.ccxio.run_ccx = orig
        out["structural_deck_sha"] = sha((td / "mech" / "structural.inp").read_bytes())
    out["wall_s"] = round(time.time() - t0, 1)
    return out


def compare_fingerprints(a: dict, b: dict) -> list:
    """Every differing leaf, as 'case: path'. Wall times are not compared."""
    diffs = []

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                if k == "wall_s":
                    continue
                if k not in x or k not in y:
                    diffs.append(f"{path}/{k}: present in only one")
                    continue
                walk(x[k], y[k], f"{path}/{k}")
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                diffs.append(f"{path}: length {len(x)} != {len(y)}")
                return
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, f"{path}[{i}]")
        elif x != y:
            diffs.append(f"{path}: {x!r} != {y!r}")

    walk(a, b, "")
    return diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--archs", default="Z1,Z2,Z3")
    ap.add_argument("--refine", default="11,21")
    args = ap.parse_args()
    res = {"env": {k: os.environ.get(k) for k in ("HVR_Z1_CONFIG",)}, "cases": {}}
    for arch in args.archs.split(","):
        for rf in args.refine.split(","):
            refine = (int(rf[0]), int(rf[1]))
            key = f"{arch}_h1.1_r{rf}"
            res["cases"][key] = fingerprint(arch, 1.1, refine)
            c = res["cases"][key]
            print(f"{key}: {c['n_nodes']} nodes {c['n_elems']} elems "
                  f"thermal {c['thermal_deck_sha'][:12]} structural "
                  f"{c['structural_deck_sha'][:12]} ({c['wall_s']} s)", flush=True)
            Path(args.out).write_text(json.dumps(res, indent=1))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
