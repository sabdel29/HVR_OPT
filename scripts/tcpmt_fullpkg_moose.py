"""TCPMT revision -- the MOOSE side of the complete-package thermal cross-check.

Everything MOOSE solves is read from the CalculiX deck that the production write_thermal
wrote, so the two solvers see the same nodes, elements, conductivities, volumetric sources
and film faces/coefficients to the last printed digit:

  parse_deck      the CalculiX thermal deck -> nodes, hexes, per-element material and source
  export_problem  blocks (one per material, split only where a source set cuts a material,
                  so every block carries ONE conductivity tensor and ONE source density) and
                  one sideset per film (face, T_sink, h)
  refine_uniform  every hex split n x n x n (n = 2: at its edge midpoints), a strictly nested
                  copy (every base node survives), blocks and film faces inherited
  write_gmsh      Gmsh 2.2 ASCII; libMesh GmshIO turns the 3-D physical groups into
                  subdomains and the quads into sidesets (then deletes the quads)
  moose_input     AnisoHeatConduction + AnisoHeatConductionMaterial (diagonal k_ortho),
                  BodyForce per source block, ConvectiveHeatFluxBC per film sideset
  run_moose       mpiexec -n <ranks> heat_transfer-opt; nodal T via NodalValueSampler (CSV)

Units throughout: mm, W, K (k in W/(mm K), h in W/(mm^2 K), q in W/mm^3), as in the deck.
"""
from __future__ import annotations

import csv
import os
import re
import subprocess
import time
from pathlib import Path

import numpy as np

MOOSE = Path("/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/heat_transfer-opt")
#: the OpenMPI the MOOSE build links against (ldd: /usr/lib64/openmpi/lib/libmpi_cxx.so.40)
MPIEXEC = Path("/usr/lib64/openmpi/bin/mpiexec")
#: libMesh NameBasedIO (moose/libmesh/src/mesh/namebased_io.C) dispatches FileMesh on the
#: extension; these are the volume-mesh formats it reads
FILEMESH_FORMATS = {
    ".msh": "Gmsh ASCII (GmshIO; versions >= 2.0, 2.2 used here; 3-D physical groups -> "
            "subdomains, lower-dimensional elements -> sidesets, then deleted)",
    ".e/.exo/.exd": "ExodusII (ExodusII_IO)", ".inp": "Abaqus (AbaqusIO)",
    ".unv": "I-deas universal", ".vtu/.pvtu": "VTK", ".xda/.xdr": "libMesh native",
    ".cpa/.cpr": "libMesh checkpoint", ".n/.nem": "Nemesis (distributed)",
}
#: CalculiX C3D8 faces used by the films, as 0-based corner indices with OUTWARD normals
FACE_NODES = {"F1": (0, 3, 2, 1), "F2": (4, 5, 6, 7)}


# ---------------------------------------------------------------------------
# the CalculiX deck
# ---------------------------------------------------------------------------

def _opts(parts):
    o = {}
    for p in parts:
        if "=" in p:
            a, b = p.split("=", 1)
            o[a.strip().upper()] = b.strip()
        elif p.strip():
            o[p.strip().upper()] = True
    return o


def parse_deck(path: Path) -> dict:
    """Nodes, C3D8 elements, materials, sources and films of a write_thermal deck."""
    node_rows, elem_rows, elem_set_of = [], [], []
    elsets, cond, section, dflux, films = {}, {}, {}, [], []
    kw, cur, ortho = None, None, False
    with path.open() as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("**"):
                continue
            if line.startswith("*"):
                parts = [p.strip() for p in line.split(",")]
                kw, o = parts[0].upper(), _opts(parts[1:])
                if kw == "*ELEMENT":
                    if o.get("TYPE") != "C3D8":
                        raise ValueError(f"unexpected element type {o.get('TYPE')}")
                    cur = o["ELSET"]
                elif kw == "*ELSET":
                    cur = o["ELSET"]
                    elsets[cur] = []
                elif kw == "*MATERIAL":
                    cur = o["NAME"]
                elif kw == "*CONDUCTIVITY":
                    ortho = str(o.get("TYPE", "")).upper() == "ORTHO"
                elif kw == "*SOLID SECTION":
                    section[o["ELSET"]] = o["MATERIAL"]
                continue
            v = [s for s in (x.strip() for x in line.split(",")) if s]
            if kw == "*NODE":
                node_rows.append((int(v[0]), float(v[1]), float(v[2]), float(v[3])))
            elif kw == "*ELEMENT":
                elem_rows.append([int(x) for x in v])
                elem_set_of.append(cur)
            elif kw == "*ELSET":
                elsets[cur].extend(int(x) for x in v)
            elif kw == "*CONDUCTIVITY":
                k = [float(x) for x in v]
                cond[cur] = k if ortho else k * 3
                if len(cond[cur]) != 3:
                    raise ValueError(f"conductivity card of {cur}: {line}")
            elif kw == "*DFLUX":
                if v[1].upper() != "BF":
                    raise ValueError(f"unexpected *DFLUX load {line}")
                dflux.append((v[0], float(v[2])))
            elif kw == "*FILM":
                films.append((int(v[0]), v[1].upper(), float(v[2]), float(v[3])))
    nr = np.array(node_rows)
    if not np.array_equal(nr[:, 0], np.arange(1, len(nr) + 1)):
        raise ValueError("node ids are not contiguous 1..N")
    er = np.array(elem_rows, dtype=np.int64)
    order = np.argsort(er[:, 0])
    if not np.array_equal(er[order, 0], np.arange(1, len(er) + 1)):
        raise ValueError("element ids are not contiguous 1..M")
    mat = np.array([section[s] for s in elem_set_of], dtype=object)[order]
    return {"xyz": nr[:, 1:], "hexes": er[order, 1:], "material": mat, "conductivity": cond,
            "elsets": {k: np.array(v, dtype=np.int64) for k, v in elsets.items()},
            "dflux": dflux, "films": films}


# ---------------------------------------------------------------------------
# blocks, sidesets, refinement
# ---------------------------------------------------------------------------

def export_problem(deck: dict, film_names) -> dict:
    """Blocks (material x source set) and film sidesets of a parsed deck.

    `film_names(face, T, h)` names each (face, T_sink, h) group of *FILM lines."""
    n_el = len(deck["hexes"])
    src = np.full(n_el, -1, dtype=np.int64)
    sources = []
    for k, (name, q) in enumerate(deck["dflux"]):
        ids = deck["elsets"][name]
        if np.any(src[ids - 1] >= 0):          # CalculiX would REPLACE, not add: refuse it
            raise ValueError(f"source set {name} overlaps another source set")
        src[ids - 1] = k
        sources.append({"set": name, "q_W_mm3": q, "n_elems": int(len(ids))})
    keys = sorted({(m, int(s)) for m, s in zip(deck["material"], src)},
                  key=lambda t: (t[0], t[1]))
    blocks, tag_of = [], {}
    for i, (m, s) in enumerate(keys):
        name = m.lower() if s < 0 else f"{m.lower()}__src{s + 1}"
        blocks.append({"name": name, "tag": 10 + i, "material": m,
                       "source": None if s < 0 else s})
        tag_of[(m, s)] = 10 + i
    etag = np.array([tag_of[(m, int(s))] for m, s in zip(deck["material"], src)],
                    dtype=np.int64)
    for b in blocks:
        b["n_elems"] = int((etag == b["tag"]).sum())
    groups = {}
    for e, face, t, h in deck["films"]:
        groups.setdefault((face, t, h), []).append(e)
    sidesets = []
    for i, ((face, t, h), es) in enumerate(sorted(groups.items())):
        sidesets.append({"name": film_names(face, t, h), "tag": 1 + i, "face": face,
                         "T_inf_C": t, "h_W_mm2K": h,
                         "elems": np.array(sorted(es), dtype=np.int64)})
    if len({s["name"] for s in sidesets}) != len(sidesets):
        raise ValueError(f"film groups do not map to distinct names: "
                         f"{[(s['face'], s['T_inf_C'], s['h_W_mm2K']) for s in sidesets]}")
    return {"xyz": deck["xyz"], "hexes": deck["hexes"], "etag": etag, "blocks": blocks,
            "sources": sources, "sidesets": sidesets, "conductivity": deck["conductivity"]}


def lattice_index(xyz):
    """(i, j, k) grid indices of every node of a tensor-lattice mesh, and the grid lines."""
    axes, idx = [], []
    for d in range(3):
        g = np.unique(xyz[:, d])
        i = np.searchsorted(g, xyz[:, d])
        if not np.array_equal(g[i], xyz[:, d]):
            raise ValueError("node coordinates are not on a tensor lattice")
        axes.append(g)
        idx.append(i)
    return np.column_stack(idx), axes


#: corner offsets of a lattice cell in the HEX8 (CalculiX = libMesh = Gmsh) order
CORNERS = np.array([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)], dtype=np.int64)


def refine_uniform(P: dict, n=2) -> dict:
    """Split every hex into n x n x n equal children (n = 2: at its edge midpoints); n may
    also be a per-axis triple (nx, ny, nz), e.g. (2, 2, 1) in-plane only.

    Child q = a + nx b + nx ny c of parent p (a, b, c the x, y, z child offsets) gets the
    1-based id (p - 1) nx ny nz + q + 1; every base node survives as a refined node."""
    f = np.array((n, n, n) if np.isscalar(n) else tuple(n), dtype=np.int64)
    ijk, axes = lattice_index(P["xyz"])
    base = ijk[P["hexes"][:, 0] - 1]
    expect = base[:, None, :] + CORNERS[None, :, :]
    if not np.array_equal(ijk[P["hexes"] - 1], expect):
        raise ValueError("an element is not a single lattice cell in HEX8 order")
    ax2 = []
    for g, k in zip(axes, f):                     # exact base lines, then k - 1 inserts
        t = np.arange(k) / k
        ax2.append(np.append((g[:-1, None] * (1.0 - t)[None, :]
                              + g[1:, None] * t[None, :]).ravel(), g[-1]))
    n2 = np.array([len(a) for a in ax2], dtype=np.int64)
    child_off = np.array([(a, b, c) for c in range(f[2]) for b in range(f[1])
                          for a in range(f[0])], dtype=np.int64)
    nc = int(np.prod(f))
    cb = (f * base)[:, None, :] + child_off[None, :, :]        # (M, nc, 3) child base index
    cn = cb[:, :, None, :] + CORNERS[None, None, :, :]         # (M, nc, 8, 3) child corners
    key = (cn[..., 0] * n2[1] + cn[..., 1]) * n2[2] + cn[..., 2]
    del cb, cn
    ukey, inv = np.unique(key.ravel(), return_inverse=True)
    del key
    kk = ukey % n2[2]
    jj = (ukey // n2[2]) % n2[1]
    ii = ukey // (n2[1] * n2[2])
    xyz = np.column_stack([ax2[0][ii], ax2[1][jj], ax2[2][kk]])
    hexes = inv.reshape(-1, 8) + 1
    etag = np.repeat(P["etag"], nc)
    parent = np.repeat(np.arange(1, len(P["hexes"]) + 1), nc)
    sides = []
    for s in P["sidesets"]:
        c = 0 if s["face"] == "F1" else f[2] - 1               # bottom face: c = 0 children
        sel = np.array([a + f[0] * b + f[0] * f[1] * c
                        for b in range(f[1]) for a in range(f[0])])
        ch = ((s["elems"] - 1)[:, None] * nc + sel[None, :]).ravel() + 1
        sides.append({**s, "elems": np.sort(ch)})
    base_key = ((f[0] * ijk[:, 0]) * n2[1] + f[1] * ijk[:, 1]) * n2[2] + f[2] * ijk[:, 2]
    base_node_in_fine = np.searchsorted(ukey, base_key) + 1
    if not np.array_equal(ukey[base_node_in_fine - 1], base_key):
        raise ValueError("a base node is missing from the refined mesh")
    return {**P, "xyz": xyz, "hexes": hexes, "etag": etag, "sidesets": sides,
            "parent": parent, "base_node_in_fine": base_node_in_fine,
            "factor": [int(v) for v in f]}


def elem_volumes(xyz, hexes):
    p0, p6 = xyz[hexes[:, 0] - 1], xyz[hexes[:, 6] - 1]
    d = p6 - p0
    if np.any(d <= 0):
        raise ValueError("non-positive brick extent")
    return d[:, 0] * d[:, 1] * d[:, 2]


def face_areas(xyz, hexes, elems):
    p0, p6 = xyz[hexes[elems - 1, 0] - 1], xyz[hexes[elems - 1, 6] - 1]
    return (p6[:, 0] - p0[:, 0]) * (p6[:, 1] - p0[:, 1])


# ---------------------------------------------------------------------------
# Gmsh 2.2 and the MOOSE input
# ---------------------------------------------------------------------------

def write_gmsh(P: dict, path: Path) -> dict:
    xyz, hexes = P["xyz"], P["hexes"]
    quads, qtag = [], []
    for s in P["sidesets"]:
        q = hexes[s["elems"] - 1][:, list(FACE_NODES[s["face"]])]
        quads.append(q)
        qtag.append(np.full(len(q), s["tag"], dtype=np.int64))
    quads = np.concatenate(quads)
    qtag = np.concatenate(qtag)
    nq, nh = len(quads), len(hexes)
    with path.open("w") as f:
        f.write("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n")
        f.write(f"{len(P['sidesets']) + len(P['blocks'])}\n")
        for s in P["sidesets"]:
            f.write(f'2 {s["tag"]} "{s["name"]}"\n')
        for b in P["blocks"]:
            f.write(f'3 {b["tag"]} "{b["name"]}"\n')
        f.write(f"$EndPhysicalNames\n$Nodes\n{len(xyz)}\n")
        np.savetxt(f, np.column_stack([np.arange(1, len(xyz) + 1), xyz]),
                   fmt=["%d", "%.17g", "%.17g", "%.17g"])
        f.write(f"$EndNodes\n$Elements\n{nq + nh}\n")
        np.savetxt(f, np.column_stack([np.arange(1, nq + 1), np.full(nq, 3), np.full(nq, 2),
                                       qtag, qtag, quads]), fmt="%d")
        np.savetxt(f, np.column_stack([np.arange(nq + 1, nq + nh + 1), np.full(nh, 5),
                                       np.full(nh, 2), P["etag"], P["etag"], hexes]),
                   fmt="%d")
        f.write("$EndElements\n")
    return {"n_nodes": int(len(xyz)), "n_hex": int(nh), "n_quad": int(nq),
            "bytes": path.stat().st_size}


def moose_input(P: dict, mesh_name: str, solver: str = "hypre") -> str:
    """The MOOSE input: every number is the deck's own (repr round-trips the decimal)."""
    nl = "\n"
    by_mat = {}
    for b in P["blocks"]:
        by_mat.setdefault(b["material"], []).append(b["name"])
    mats = []
    for m, names in sorted(by_mat.items()):
        kx, ky, kz = P["conductivity"][m]
        mats.append(f"""  [k_{m.lower()}]
    type = AnisoHeatConductionMaterial
    block = '{" ".join(names)}'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '{kx!r} 0 0 0 {ky!r} 0 0 0 {kz!r}'
  []""")
    kers = ["""  [conduction]
    type = AnisoHeatConduction
    variable = T
  []"""]
    for k, s in enumerate(P["sources"]):
        names = [b["name"] for b in P["blocks"] if b["source"] == k]
        kers.append(f"""  [q_{s['set'].lower()}]
    type = BodyForce
    variable = T
    value = {s['q_W_mm3']!r}
    block = '{" ".join(names)}'
  []""")
    bcs, pps = [], ["""  [Tmax]
    type = NodalExtremeValue
    variable = T
  []"""]
    for s in P["sidesets"]:
        bcs.append(f"""  [film_{s['name']}]
    type = ConvectiveHeatFluxBC
    variable = T
    boundary = {s['name']}
    T_infinity = {s['T_inf_C']!r}
    heat_transfer_coefficient = {s['h_W_mm2K']!r}
  []""")
        pps.append(f"""  [intT_{s['name']}]
    type = SideIntegralVariablePostprocessor
    variable = T
    boundary = {s['name']}
  []
  [area_{s['name']}]
    type = AreaPostprocessor
    boundary = {s['name']}
  []""")
    pps.append("""  [volume]
    type = VolumePostprocessor
  []""")
    if solver == "mumps":                       # direct LU
        petsc = """  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu mumps'"""
    elif solver == "hypre":                     # BoomerAMG-preconditioned GMRES, tight
        petsc = """  petsc_options_iname = '-ksp_type -pc_type -pc_hypre_type -ksp_gmres_restart'
  petsc_options_value = 'gmres hypre boomeramg 300'
  l_tol = 1e-12
  l_max_its = 2000"""
    else:
        raise ValueError(solver)
    t0 = P["sidesets"][0]["T_inf_C"]
    return f"""# complete-package thermal cross-check (TCPMT revision): the production CalculiX deck,
# exported block-for-block. Units mm, W, K.
[Mesh]
  [file]
    type = FileMeshGenerator
    file = {mesh_name}
  []
[]
[Variables]
  [T]
    initial_condition = {t0!r}
  []
[]
[Kernels]
{nl.join(kers)}
[]
[Materials]
{nl.join(mats)}
[]
[BCs]
{nl.join(bcs)}
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  line_search = none
{petsc}
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
  nl_max_its = 4
[]
[Postprocessors]
{nl.join(pps)}
[]
[VectorPostprocessors]
  [nodal]
    type = NodalValueSampler
    variable = T
    sort_by = id
    execute_on = FINAL
  []
[]
[Outputs]
  [out]
    type = CSV
    precision = 16
    execute_on = FINAL
  []
  perf_graph = true
[]
"""


def run_moose(wd: Path, inp: str, ranks: int, timeout: int = 14400) -> dict:
    for f in wd.glob(f"{Path(inp).stem}_out*"):
        f.unlink()
    cmd = [str(MOOSE), "-i", inp, "--color", "off"]
    if ranks > 1:
        cmd = [str(MPIEXEC), "-n", str(ranks), "--bind-to", "none"] + cmd
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    t0 = time.time()
    r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, env=env, timeout=timeout)
    wall = time.time() - t0
    log = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)
    (wd / f"{Path(inp).stem}.log").write_text(log)
    if r.returncode != 0:
        raise RuntimeError(f"MOOSE failed (rc={r.returncode}):\n{log[-3000:]}")
    m = re.findall(r"Finished Executing\s+\[\s*([0-9.]+) s\]", log)
    nlres = [float(x) for x in re.findall(r"\d+ Nonlinear \|R\| = ([0-9.eE+-]+)", log)]
    lits = [int(x) for x in re.findall(r"(\d+) Linear \|R\|", log)]
    perf = {}
    for ln in log.splitlines():                  # PerfGraph rows: | section | calls | ...
        c = [x.strip() for x in ln.split("|")]
        if len(c) > 8 and c[1] in ("FEProblem::solve", "HeatTransferTestApp (main)",
                                    "HeatTransferApp (main)"):
            perf[c[1]] = float(c[7])
    return {"wall_s": wall, "moose_reported_s": float(m[-1]) if m else None,
            "solve_s": perf.get("FEProblem::solve"), "nonlinear_residuals": nlres,
            "linear_its_last": max(lits) if lits else None, "ranks": ranks,
            "log_tail": log[-4000:]}


def read_moose(wd: Path, stem: str) -> dict:
    pp = list(csv.DictReader((wd / f"{stem}_out.csv").open()))[-1]
    pp = {k: float(v) for k, v in pp.items()}
    vf = sorted(wd.glob(f"{stem}_out_nodal_*.csv"))
    if not vf:
        raise RuntimeError("MOOSE wrote no nodal CSV")
    with vf[-1].open() as fh:
        head = fh.readline().strip().split(",")
    a = np.loadtxt(vf[-1], delimiter=",", skiprows=1)
    col = {h: i for i, h in enumerate(head)}
    # every rank samples the nodes it holds, so partition-boundary nodes appear more than
    # once: keep one row per libMesh node id, after checking the copies agree exactly
    nid = a[:, col["id"]].astype(np.int64)
    u, first, inv = np.unique(nid, return_index=True, return_inverse=True)
    spread = float(np.max(np.abs(a[:, col["T"]] - a[first, col["T"]][inv])))
    if spread != 0.0:
        raise ValueError(f"duplicate nodal samples disagree by {spread}")
    a = a[first]
    return {"pp": pp, "xyz": a[:, [col["x"], col["y"], col["z"]]], "T": a[:, col["T"]],
            "file": vf[-1].name, "n_rows": int(len(nid)), "n_nodes": int(len(u))}


def map_to_nodes(xyz_ref, xyz_q, T_q, tol=1e-7):
    """T at the reference nodes from a sample at the same points (any order)."""
    from scipy.spatial import cKDTree
    if len(xyz_q) != len(xyz_ref):
        raise ValueError(f"{len(xyz_q)} sampled nodes for {len(xyz_ref)} mesh nodes")
    d, i = cKDTree(xyz_q).query(xyz_ref)
    if d.max() > tol:
        raise ValueError(f"node map: largest distance {d.max():.3e} mm exceeds {tol}")
    if len(np.unique(i)) != len(i):
        raise ValueError("node map is not one-to-one")
    return T_q[i], float(d.max())
