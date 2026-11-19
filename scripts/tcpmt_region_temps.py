"""Component- and material-region temperatures of a converged thermal solution (review round 2).

The feasibility stage needs the MAXIMUM temperature of every device tier inside the cell
footprints (the junction bound adds the device's R_thJC at its own dissipation), the processor
die, the converter encapsulant (converter-tier elements outside the cells), the build-up
dielectric (every RDL tier element) and the board. Two equivalent routes:

  region_maxima(m, Tn, arch, tiles)   from the mesh in memory -- called by the chain at the end of
                                      every E-T fixed point, so new case files carry the values
                                      (thermal.region_T_max_C)
  deck_region_maxima(inp, frd, case)  from a stored thermal deck (.inp) and its result (.frd),
                                      for case files written before the chain recorded them. The
                                      deck holds the nodes, the elements per material and one
                                      element set per heat deposit (E_SRC_k, with its body flux);
                                      each deposit set is identified by the watts it receives,
                                      matched to the case's own ledger rows grouped by deposit
                                      layer -- robust to every variant's tier order or material
                                      renames.
Both use node values of the region's elements (node_stats of the earlier feasibility module).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

DEVICE_KEYS = ("hs", "ls", "caps", "ind")


# ------------------------------------------------------------------ from the mesh (the chain)
def region_maxima(m, Tn, arch, tiles):
    """{region: max C} of a converged nodal field on its own mesh."""
    import final_closure_ledger as FL
    import final_closure_physical_etm as E
    import production_et as PE
    lay = FL.LAYERS[arch]

    def tmax(ids):
        if len(ids) == 0:
            return None
        nodes = np.unique(m.elems[np.asarray(ids) - 1].ravel())
        return float(np.nanmax(Tn[nodes - 1]))

    out = {}
    as_list = lambda v: list(v) if isinstance(v, (list, tuple)) else [v]       # noqa: E731
    for k in DEVICE_KEYS:
        if k in lay:
            out[f"{k}_in_cells"] = tmax(E._region_elems(m, as_list(lay[k]), True, tiles))
    # TCPMT round 3: every converter tier (mixed tiers hold several device classes)
    conv = list(lay.get("converter") or dict.fromkeys(
        x for k in DEVICE_KEYS + ("cout",) if k in lay for x in as_list(lay[k])))
    for ln in lay.get("converter", []):
        out[f"tier:{ln}_in_cells"] = tmax(E._region_elems(m, [ln], True, tiles))
    ids_c = np.concatenate([PE._layer_elems(m, x) for x in conv])
    ids_in = E._region_elems(m, conv, True, tiles)
    out["encapsulant"] = tmax(np.setdiff1d(ids_c, ids_in))
    out["rdl_all"] = tmax(np.concatenate([PE._layer_elems(m, x) for x in lay["rdl"]]))
    out["die"] = tmax(PE._layer_elems(m, lay["die"]))
    out["bga"] = tmax(PE._layer_elems(m, lay["bga"]))
    board = [L.name for L in m.layers if L.name.startswith(("board", "pcb"))]
    if board:
        out["board"] = tmax(np.concatenate([PE._layer_elems(m, x) for x in board]))
    out["source"] = "mesh (chain)"
    return out


# ------------------------------------------------------------------ from a stored deck
def read_temperatures(frd):
    """NDTEMP of a thermal .frd as an array indexed by node id."""
    ids, vals = [], []
    on = False
    with open(frd) as fh:
        for line in fh:
            k = line[:4].strip()
            if k == "-4":
                on = line[5:17].strip() == "NDTEMP"
            elif k == "-3":
                if on:
                    break
            elif on and k == "-1":
                ids.append(int(line[3:13]))
                vals.append(float(line[13:25]))
    t = np.full(max(ids) + 1, np.nan)
    t[np.asarray(ids)] = vals
    return t


def parse_deck(inp):
    """nodes (id -> xyz), elements (id -> 8 nodes), material element sets, E_SRC sets and their
    body fluxes of a thermal deck written by final_closure_physical_etm.write_thermal."""
    txt = Path(inp).read_text()
    blocks = re.split(r"(?m)^\*", txt)
    nodes = None
    elem_rows, mat_sets, src_sets, flux = [], {}, {}, {}

    def nums(body, dtype):
        return np.array([x for x in re.split(r"[,\s]+", body) if x], dtype=dtype)

    for b in blocks:
        head, _, body = b.partition("\n")
        hu = head.upper()
        if hu.startswith("NODE") and "FILE" not in hu and "PRINT" not in hu:
            a = nums(body, float).reshape(-1, 4)
            nodes = np.full((int(a[:, 0].max()) + 1, 3), np.nan)
            nodes[a[:, 0].astype(np.int64)] = a[:, 1:]
        elif hu.startswith("ELEMENT"):
            mset = re.search(r"ELSET=([^,\s]+)", head, re.I).group(1).upper()
            a = nums(body, np.int64).reshape(-1, 9)
            mat_sets[mset] = a[:, 0]
            elem_rows.append(a)
        elif hu.startswith("ELSET") and "E_SRC_" in hu:
            name = re.search(r"ELSET=([^,\s]+)", head, re.I).group(1).upper()
            src_sets[name] = nums(body, np.int64)
        elif hu.startswith("DFLUX"):
            for ln in body.splitlines():
                p = [x.strip() for x in ln.split(",")]
                if len(p) >= 3 and p[1].upper() == "BF":
                    flux[p[0].upper()] = float(p[2])
    rows = np.concatenate(elem_rows) if elem_rows else np.zeros((0, 9), np.int64)
    conn = np.zeros((int(rows[:, 0].max()) + 1, 8), np.int64)
    conn[rows[:, 0]] = rows[:, 1:]
    return {"nodes": nodes, "conn": conn, "mat_sets": mat_sets, "src_sets": src_sets,
            "flux": flux}


def _volumes(deck, ids):
    p = deck["nodes"][deck["conn"][ids]]              # (n, 8, 3), axis-aligned hexahedra
    ext = p.max(axis=1) - p.min(axis=1)
    return ext[:, 0] * ext[:, 1] * ext[:, 2]


def _tmax(deck, T, ids):
    if ids is None or len(ids) == 0:
        return None
    nodes = np.unique(deck["conn"][ids].ravel())
    return float(np.nanmax(T[nodes]))


def deposit_groups(case):
    """{deposit layer string: {'W', 'terms'}} of a case's ledger rows (the heat the deck got)."""
    g = {}
    for r in case.get("ledger_rows") or []:
        if (r.get("P_w") or 0.0) <= 0.0:
            continue
        x = g.setdefault(r["deposit_layer"], {"W": 0.0, "terms": []})
        x["W"] += float(r["P_w"])
        x["terms"].append(r["term"])
    return g


def deck_region_maxima(inp, frd, case, p_load_w=1000.0, rel_tol=1e-5):
    """{region: max C} from a stored deck and its converged result, the deposit sets identified
    by their watts against the case's ledger."""
    deck = parse_deck(inp)
    T = read_temperatures(frd)
    watts = {}
    for name, ids in deck["src_sets"].items():
        if name in deck["flux"]:
            watts[name] = float(_volumes(deck, ids).sum() * deck["flux"][name])
    groups = deposit_groups(case)
    term_key = {"P_conv_hs": "hs", "P_conv_ls": "ls", "P_conv_cap_esr": "caps",
                "P_conv_inductor_dcr": "ind"}
    found, notes = {}, []
    used = set()
    pending = []
    for layer, g in groups.items():
        keys = {term_key[t] for t in g["terms"] if t in term_key}
        if not keys:
            continue
        hit = [n for n, w in watts.items() if abs(w - g["W"]) <= rel_tol * max(g["W"], 1e-9)
               and n not in used]
        if len(hit) != 1:
            pending.append((layer, g, keys, len(hit)))
            continue
        used.add(hit[0])
        for k in keys:
            found[k] = deck["src_sets"][hit[0]]
    # a deposit that ALSO received heat outside the ledger (a sensitivity's EXTRA_DEPOSITS, e.g.
    # the feed heat in the deepest converter tier): the unmatched set with the smallest excess
    for layer, g, keys, nhit in pending:
        cand = sorted((w - g["W"], n) for n, w in watts.items()
                      if n not in used and w > g["W"] * (1 + rel_tol)
                      and abs(w - p_load_w) > rel_tol * p_load_w)
        if nhit == 0 and cand:
            n = cand[0][1]
            used.add(n)
            for k in keys:
                found[k] = deck["src_sets"][n]
            notes.append(f"{layer}: matched {n} with {cand[0][0]:.4g} W of heat beyond the ledger")
        else:
            notes.append(f"{layer}: {nhit} deposit sets match {g['W']:.6g} W")
    # the die: the set(s) carrying the processor load (one set, or the hot-spot pair)
    die = [n for n, w in watts.items() if abs(w - p_load_w) <= rel_tol * p_load_w and n not in used]
    if not die:
        rest = [n for n in watts if n not in used]
        pair = [(a, b) for i, a in enumerate(rest) for b in rest[i + 1:]
                if abs(watts[a] + watts[b] - p_load_w) <= rel_tol * p_load_w]
        die = list(pair[0]) if len(pair) == 1 else []
    out = {f"{k}_in_cells": _tmax(deck, T, found.get(k)) for k in DEVICE_KEYS}
    out["die"] = (_tmax(deck, T, np.concatenate([deck["src_sets"][n] for n in die]))
                  if die else None)
    rdl = [s for n, s in deck["mat_sets"].items() if n.startswith("E_RDL")]
    out["rdl_all"] = _tmax(deck, T, np.concatenate(rdl)) if rdl else None
    board = [s for n, s in deck["mat_sets"].items() if n.startswith(("E_BOARD", "E_PCB"))]
    out["board"] = _tmax(deck, T, np.concatenate(board)) if board else None
    bga = [s for n, s in deck["mat_sets"].items() if n.startswith("E_BGA")]
    out["bga"] = _tmax(deck, T, np.concatenate(bga)) if bga else None
    # encapsulant: converter-tier elements (z-span of the device sets) outside the cells,
    # excluding the RDL tiers
    dev = [found[k] for k in DEVICE_KEYS if k in found]
    if dev:
        dev_ids = np.unique(np.concatenate(dev))
        zc = deck["nodes"][deck["conn"][dev_ids]][:, :, 2]
        z0, z1 = float(zc.min()), float(zc.max())
        all_ids = np.concatenate(list(deck["mat_sets"].values()))
        cz = deck["nodes"][deck["conn"][all_ids]][:, :, 2].mean(axis=1)
        inside = all_ids[(cz > z0) & (cz < z1)]
        rdl_ids = np.concatenate(rdl) if rdl else np.zeros(0, np.int64)
        enc = np.setdiff1d(np.setdiff1d(inside, dev_ids), rdl_ids)
        out["encapsulant"] = _tmax(deck, T, enc)
        if out["encapsulant"] is None:
            # the run deposited the device heat over WHOLE tiers (no out-of-cell element is
            # left outside the deposit sets): the encapsulant shares the device-tier maxima
            out["encapsulant"] = max(v for k, v in out.items()
                                     if k.endswith("_in_cells") and v is not None)
            notes.append("device heat deposited over whole tiers in this run: encapsulant "
                         "taken as the device-tier maximum")
    else:
        out["encapsulant"] = None
    out["T_max_field_C"] = float(np.nanmax(T[1:]))
    out["source"] = f"deck {Path(inp).name} + {Path(frd).name} ({Path(inp).parent})"
    if notes:
        out["notes"] = notes
    return out
