"""Minimal CalculiX .frd (ASCII) reader: nodes, C3D8 elements with material id, and
nodal result blocks (NDTEMP, DISP). Parsed arrays are cached as .npz next to the
figures (never written into the read-only project tree)."""
from __future__ import annotations

from pathlib import Path
import numpy as np

CACHE = Path(__file__).resolve().parents[1] / "cache"
CACHE.mkdir(exist_ok=True)


def read(path, blocks=("NDTEMP", "DISP")):
    path = Path(path)
    key = CACHE / (path.parent.name + "_" + path.stem + ".npz")
    if path.parent.parent.name != "fields":          # solver scratch: names repeat across runs
        import hashlib
        h = hashlib.md5(str(path.resolve()).encode()).hexdigest()[:10]
        key = CACHE / (path.parent.name + "_" + path.stem + "_" + h + ".npz")
    if key.exists():
        d = np.load(key, allow_pickle=True)
        return {k: d[k] for k in d.files}
    nid, xyz = [], []
    eid, emat, econ = [], [], []
    res = {}
    mode, cur, cur_rows, cur_ids = None, None, [], []
    mats = {}
    with open(path) as f:
        pend = None
        for line in f:
            tag = line[:6]
            if line.startswith("    1UMAT"):
                mats[int(line[9:14])] = line[14:].strip()
                continue
            if tag == "    2C":
                mode = "nodes"
                continue
            if tag == "    3C":
                mode = "elems"
                continue
            if line.startswith(" -4"):
                name = line[3:13].strip()
                mode = "res"
                cur = name if name in blocks else None
                cur_ids, cur_rows = [], []
                continue
            if line.startswith(" -3"):
                if mode == "res" and cur is not None:
                    res[cur] = (np.array(cur_ids), np.array(cur_rows))
                mode, cur = None, None
                continue
            if mode == "nodes" and line.startswith(" -1"):
                nid.append(int(line[3:13]))
                xyz.append((float(line[13:25]), float(line[25:37]), float(line[37:49])))
            elif mode == "elems":
                if line.startswith(" -1"):
                    pend = (int(line[3:13]), int(line[23:28]))
                elif line.startswith(" -2") and pend is not None:
                    con = [int(line[3 + 10 * i:13 + 10 * i]) for i in range(8)]
                    eid.append(pend[0])
                    emat.append(pend[1])
                    econ.append(con)
                    pend = None
            elif mode == "res" and cur is not None and line.startswith(" -1"):
                n = int(line[3:13])
                body = line[13:].rstrip("\n")
                vals = [float(body[12 * i:12 * i + 12]) for i in range(len(body) // 12)]
                cur_ids.append(n)
                cur_rows.append(vals)
    out = {"nid": np.array(nid), "xyz": np.array(xyz), "eid": np.array(eid),
           "emat": np.array(emat), "econ": np.array(econ),
           "mats": np.array([mats.get(i, "") for i in range(max(mats) + 1)] if mats else [])}
    for k, (ids, rows) in res.items():
        out[k + "_id"] = ids
        out[k] = rows
    np.savez_compressed(key, **out)
    return out
