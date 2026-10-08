"""CalculiX deck generation, execution and result parsing.

Thermal and structural passes share ONE mesh, so the temperature field transfers
node-to-node with zero interpolation error (spec validation item: "temperature
mapping conserves spatial location and does not smooth away hotspots").
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import W_M2K_TO_W_MM2K
from .mesh import Mesh


# ---------------------------------------------------------------------------
# deck helpers
# ---------------------------------------------------------------------------

def _fmt_set(name: str, ids: np.ndarray, kind: str = "ELSET") -> list[str]:
    out = [f"*{kind}, {kind}={name}"]
    for i in range(0, len(ids), 8):
        out.append(",".join(str(int(v)) for v in ids[i:i + 8]) + ",")
    if out[-1].endswith(","):
        out[-1] = out[-1][:-1]
    return out


def _nodes_block(m: Mesh) -> list[str]:
    return ["*NODE"] + [f"{i+1},{p[0]:.6f},{p[1]:.6f},{p[2]:.6f}"
                        for i, p in enumerate(m.nodes)]


def _elements_blocks(m: Mesh, etype: str) -> list[str]:
    """One *ELEMENT block per material so that *SOLID SECTION can bind directly."""
    lines: list[str] = []
    for mat in sorted(set(m.elem_material)):
        ids = m.elem_set(material=mat)
        lines.append(f"*ELEMENT, TYPE={etype}, ELSET=E_{mat.upper()}")
        for e in ids:
            row = m.elems[e - 1]
            lines.append(f"{int(e)}," + ",".join(str(int(v)) for v in row))
    return lines


def top_film_faces(m: Mesh) -> np.ndarray:
    """(elem_id, face) for the cold-plate contact = top face of the topmost TIM row."""
    ztop = m.zs[-1]
    ids = m.elem_set(layer="tim")
    keep = [e for e in ids if abs(m.nodes[m.elems[e - 1] - 1][:, 2].max() - ztop) < 1e-9]
    return np.array(keep, int)


def bottom_film_faces(m: Mesh) -> np.ndarray:
    """Elements whose bottom face lies on the lowest surface of the model.

    That surface is the substrate underside for BC-A, or the support-layer underside
    when the compliant support is present (BC-B).
    """
    zbot = float(m.zs.min())
    lowest = m.layers[0].name
    ids = m.elem_set(layer=lowest)
    keep = [e for e in ids if abs(m.nodes[m.elems[e - 1] - 1][:, 2].min() - zbot) < 1e-9]
    return np.array(keep, int)


def face_area(m: Mesh, eid: int) -> float:
    p = m.nodes[m.elems[eid - 1] - 1]
    return abs(p[1, 0] - p[0, 0]) * abs(p[3, 1] - p[0, 1])


# ---------------------------------------------------------------------------
# thermal deck
# ---------------------------------------------------------------------------

def write_thermal(m: Mesh, mats: dict, tiles, stack: dict, p_die: float,
                  h_top: float, path: Path) -> dict:
    g = stack["geometry"]
    tb = stack["thermal_bc"]
    t_coolant = tb["coolant_temp"]["value"]
    h_bot = tb["h_bottom"]["value"]
    t_amb = tb["ambient_bottom"]["value"]

    L = _nodes_block(m) + _elements_blocks(m, "C3D8")
    L += _fmt_set("NALL", np.arange(1, m.n_nodes + 1), "NSET")

    for mat in sorted(set(m.elem_material)):
        mm = mats[mat]
        L += [f"*MATERIAL, NAME={mat.upper()}"] + mm.ccx_conductivity()
        L += [f"*SOLID SECTION, ELSET=E_{mat.upper()}, MATERIAL={mat.upper()}"]

    # heat sources: volumetric body flux (W/mm^3)
    V = m.elem_volumes()
    die_ids = m.elem_set(layer="die")
    v_die = V[die_ids - 1].sum()
    L += _fmt_set("E_DIESRC", die_ids)

    tile_srcs = []
    for ti, t in enumerate(tiles):
        ids = m.elem_set(layer="tile_band", tile=ti)
        vv = V[ids - 1].sum()
        L += _fmt_set(f"E_TILE{ti}", ids)
        tile_srcs.append((ti, t.power_w, vv))

    top_ids, bot_ids = top_film_faces(m), bottom_film_faces(m)
    a_top = sum(face_area(m, e) for e in top_ids)
    a_bot = sum(face_area(m, e) for e in bot_ids)

    L += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL,{t_coolant}"]
    L += ["*STEP", "*HEAT TRANSFER, STEADY STATE", "*DFLUX",
          f"E_DIESRC,BF,{p_die / v_die:.9g}"]
    for ti, pw, vv in tile_srcs:
        L.append(f"E_TILE{ti},BF,{pw / vv:.9g}")
    # *FILM coefficients in W/(mm^2.K) for the mm consistent unit system
    h_top_mm, h_bot_mm = h_top * W_M2K_TO_W_MM2K, h_bot * W_M2K_TO_W_MM2K
    L += ["*FILM"]
    for e in top_ids:
        L.append(f"{int(e)},F2,{t_coolant},{h_top_mm:.9g}")
    for e in bot_ids:
        L.append(f"{int(e)},F1,{t_amb},{h_bot_mm:.9g}")
    L += ["*NODE FILE", "NT", "*END STEP"]

    path.write_text("\n".join(L) + "\n")
    return {"v_die_mm3": v_die, "a_top_mm2": a_top, "a_bot_mm2": a_bot,
            "h_top_W_m2K": h_top, "h_bot_W_m2K": h_bot,
            "top_face_elems": top_ids, "bot_face_elems": bot_ids,
            "q_die_w_per_mm3": p_die / v_die}


# ---------------------------------------------------------------------------
# structural deck
# ---------------------------------------------------------------------------

def write_structural(m: Mesh, mats: dict, temps: np.ndarray, stack: dict,
                     bc: str, path: Path, solver: str = "ITERATIVE CHOLESKY") -> dict:
    sb = stack["structural_bc"]
    t_ref = sb["t_ref"]["value"]

    L = _nodes_block(m) + _elements_blocks(m, "C3D8I")
    L += _fmt_set("NALL", np.arange(1, m.n_nodes + 1), "NSET")

    for mat in sorted(set(m.elem_material)):
        mm = mats[mat]
        L += [f"*MATERIAL, NAME={mat.upper()}"] + mm.ccx_elastic()
        L += [f"*EXPANSION, ZERO={t_ref}", f"{mm.cte:.9g}"]
        L += [f"*SOLID SECTION, ELSET=E_{mat.upper()}, MATERIAL={mat.upper()}"]

    zbot = float(m.zs.min())
    bot = m.node_ids_at_z(zbot)
    info: dict = {"bc": bc, "n_bottom_nodes": int(len(bot)), "z_bottom_mm": zbot}

    def _anchors(bot_ids):
        """Three nodes on the underside forming the standard 3-2-1 triad."""
        q = m.nodes[bot_ids - 1]
        return (int(bot_ids[np.lexsort((q[:, 1], q[:, 0]))][0]),      # min x, min y
                int(bot_ids[np.lexsort((q[:, 1], -q[:, 0]))][0]),     # max x, min y
                int(bot_ids[np.lexsort((-q[:, 1], q[:, 0]))][0]))     # min x, max y

    if bc == "BC_A":
        # 3-2-1 rigid-body suppression: removes exactly 6 DOF and leaves the package
        # free to warp. ANSYS/CalculiX guidance both warn that over-constrained supports
        # exaggerate thermal stress, so this is the PRIMARY global-warpage model.
        p = m.nodes[bot - 1]
        a = bot[np.lexsort((p[:, 1], p[:, 0]))][0]                    # min x, min y
        b = bot[np.lexsort((p[:, 1], -p[:, 0]))][0]                   # max x, min y
        c = bot[np.lexsort((-p[:, 1], p[:, 0]))][0]                   # min x, max y
        L += ["*BOUNDARY", f"{int(a)},1,3", f"{int(b)},2,3", f"{int(c)},3,3"]
        info["anchor_nodes"] = {"A_xyz": int(a), "B_yz": int(b), "C_z": int(c)}
        info["anchor_coords"] = {k: m.nodes[v - 1].tolist()
                                 for k, v in info["anchor_nodes"].items()}
        info["dofs_removed"] = 6
    elif bc == "BC_B":
        # Compliant BGA/board support: an explicit low-modulus layer carries the
        # package, and its underside (the board) is fully restrained. A Winkler-type
        # foundation that also carries shear, built from the same solid elements as
        # the rest of the model - no discrete spring elements, no CalculiX *SPRING quirks.
        if m.layers[0].name != "support":
            raise ValueError("BC_B requires the mesh to be built with support_layer=True")
        bcb = sb["variants"]["BC_B"]
        L += ["*BOUNDARY"] + [f"{int(n)},1,3" for n in bot]
        info["support_layer"] = {"thickness_mm": bcb["thickness"]["value"],
                                 "E_MPa": bcb["E"]["value"], "nu": bcb["nu"]["value"],
                                 "k_z_equiv_N_per_mm3": bcb["E"]["value"] / bcb["thickness"]["value"]}
        info["dofs_removed"] = int(3 * len(bot))
    elif bc == "BC_BZ":
        # Phase-0G: the foundation the BC_B docstring DESCRIBES -- a Winkler support that
        # carries normal load only. BC_B fixes all three DOF on the underside plane, which
        # also clamps the package IN-PLANE; a BGA field does not do that, it is compliant in
        # shear. Vertical restraint on the plane plus 3-2-1 for rigid-body suppression.
        A, B, _ = _anchors(bot)
        L += ["*BOUNDARY"] + [f"{int(n)},3,3" for n in bot]
        L += [f"{A},1,2", f"{B},2,2"]          # remove x, y translation and z rotation
        info["anchor_nodes"] = {"A_xy": A, "B_y": B}
        info["dofs_removed"] = int(len(bot) + 3)
        info["note"] = "vertical-only foundation; package free to expand in-plane"
    elif bc == "BC_BOARD":
        # Phase-0G: explicit assembly. The BGA field and the PCB are meshed as real layers,
        # so the only restraint needed is rigid-body suppression on the PCB underside.
        A, B, C = _anchors(bot)
        L += ["*BOUNDARY", f"{A},1,3", f"{B},2,3", f"{C},3,3"]
        info["anchor_nodes"] = {"A_xyz": A, "B_yz": B, "C_z": C}
        info["dofs_removed"] = 6
        info["note"] = "explicit BGA + PCB stack, free assembly (3-2-1 only)"
    else:
        raise ValueError(f"unknown BC variant {bc!r}")

    # Reaction printout restricted to the constrained nodes: with BC-A only the three
    # anchors carry reactions, and printing RF for every node produces a huge .dat.
    L += _fmt_set("NRF", np.array(sorted(info["anchor_nodes"].values()))
                  if bc in ("BC_A", "BC_BOARD") else bot, "NSET")

    L += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL,{t_ref}"]
    step = "*STATIC" if not solver else f"*STATIC, SOLVER={solver}"
    L += ["*STEP", step, "*TEMPERATURE"]
    L += [f"{i+1},{temps[i]:.6f}" for i in range(m.n_nodes)]
    L += ["*NODE FILE", "U", "*EL FILE", "S", "*NODE PRINT, NSET=NRF", "RF", "*END STEP"]
    info["solver"] = solver or "SPOOLES"

    path.write_text("\n".join(L) + "\n")
    return info


# ---------------------------------------------------------------------------
# run + parse
# ---------------------------------------------------------------------------

def run_ccx(job: Path, threads: int | None = None, timeout: int = 7200) -> str:
    try:                                   # SPOOLES recursion can exceed an 8 MB stack
        import resource
        resource.setrlimit(resource.RLIMIT_STACK,
                           (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    except Exception:
        pass
    env = dict(os.environ)
    env.setdefault("OMP_STACKSIZE", "512M")
    env["OMP_NUM_THREADS"] = str(threads or max(1, (os.cpu_count() or 4) // 2))
    r = subprocess.run(["ccx", job.stem], cwd=job.parent, env=env,
                       capture_output=True, text=True, timeout=timeout)
    log = r.stdout + r.stderr
    (job.parent / f"{job.stem}.log").write_text(log)
    if "*ERROR" in log or r.returncode != 0:
        tail = "\n".join(log.splitlines()[-25:])
        raise RuntimeError(f"CalculiX failed for {job.stem} (rc={r.returncode}):\n{tail}")
    return log


def read_frd(path: Path) -> dict[str, np.ndarray]:
    """Parse nodal result blocks from a CalculiX .frd file.

    Returns {block_name: (n_nodes+1, n_components) array indexed by node id}.
    """
    out: dict[str, list] = {}
    name, rows, max_node = None, [], 0
    with path.open() as fh:
        for line in fh:
            key = line[:4].strip()           # frd record tag; single leading space: " -4  NDTEMP"
            if key == "-4":
                if name and rows:
                    out[name] = rows
                name, rows = line[5:17].strip(), []
            elif key == "-3":
                if name and rows:
                    out[name] = rows
                name, rows = None, []
            elif key == "-1" and name:
                nid = int(line[3:13])
                rest = line[13:].rstrip("\n")
                vals = [float(rest[i:i + 12]) for i in range(0, len(rest), 12)
                        if rest[i:i + 12].strip()]
                rows.append((nid, vals))
                if nid > max_node:
                    max_node = nid
    if name and rows:
        out[name] = rows

    parsed: dict[str, np.ndarray] = {}
    for k, rows in out.items():
        nc = max(len(v) for _, v in rows)
        arr = np.full((max_node + 1, nc), np.nan)
        for nid, vals in rows:
            arr[nid, :len(vals)] = vals
        parsed[k] = arr
    return parsed
