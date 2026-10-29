"""Exact-geometry re-renders of the kept AEDT reference models (no geometry from memory).

Stage 1 (AEDT, non-graphical, one tracked session per project):
    the project copy in the AEDT scratch tree is opened with its design name and every
    model body is exported with AEDT's own tessellation, oEditor.ExportModelMeshToFile
    (the call behind PyAEDT post.export_model_obj, one OBJ per object). AEDT's own
    bounding box, material and volume of each body are recorded beside it.
Stage 2 (VTK 9.6 offscreen/EGL):
    the OBJ files are read back, checked against AEDT's bounding boxes, and drawn as a
    clean isometric view with per-object colours from scripts/figstyle.py, labels with
    leader lines, a scale bar and the banner EXACT GEOMETRY RE-RENDERED FROM REFERENCE
    MODEL. A failed export is recorded and its render skipped.

    python aedt_geometry_rerender.py all            # export (AEDT) then render (VTK)
    python aedt_geometry_rerender.py render         # re-render from existing exports
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(R / "scripts"))
WORK = Path(os.environ.get("AEDT_WORK", Path.home() / "claude_scratch" / "aedt_work"))
SRC = Path.home() / "claude_scratch" / "hvr_work" / "aedt_ref"
RR = WORK / "rerender"
FIGS = R / "presentation" / "prelim_hvr" / "figs"
BANNER = "EXACT GEOMETRY RE-RENDERED FROM REFERENCE MODEL"

MODELS = {
    "thermal_column_Z1": {"project": "col_Z1_HV_S0.aedt", "design": "column",
                          "app": "Mechanical", "solution": "Thermal",
                          "out": "rerender_thermal_column_Z1"},
    "thermal_column_Z2": {"project": "col_Z2_HV_S0.aedt", "design": "column",
                          "app": "Mechanical", "solution": "Thermal",
                          "out": "rerender_thermal_column_Z2"},
    "mech_bilayer": {"project": "mech_bilayer2.aedt", "design": "structural",
                     "app": "Mechanical", "solution": "Structural",
                     "out": "rerender_mech_bilayer"},
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# =============================================================== stage 1: AEDT ====
def export(key):
    from ansys.aedt.core import Mechanical
    m = MODELS[key]
    proj = RR / m["project"]
    out = RR / key
    out.mkdir(parents=True, exist_ok=True)
    rec = {"key": key, "source_project_original": str(SRC / m["project"]),
           "source_project_sha256": sha(SRC / m["project"]),
           "opened_copy": str(proj), "opened_copy_sha256_before": sha(proj),
           "design": m["design"], "objects": {}, "errors": []}
    t0 = time.time()
    app = Mechanical(project=str(proj), design=m["design"], non_graphical=True,
                     new_desktop=True, version="2026.1", close_on_exit=True)
    try:
        rec["designs_in_project"] = list(app.design_list)
        rec["active_design"] = app.design_name
        rec["solution_type"] = app.solution_type
        rec["model_units"] = app.modeler.model_units
        solids = list(app.modeler.solid_names)
        sheets = list(app.modeler.sheet_names)
        rec["solids"], rec["sheets"] = solids, sheets
        for name in solids + sheets:
            o = app.modeler[name]
            info = {"kind": "solid" if name in solids else "sheet"}
            for attr in ("material_name", "color", "transparency", "bounding_box"):
                try:
                    v = getattr(o, attr)
                    info[attr] = list(v) if isinstance(v, tuple) else v
                except Exception as e:                        # pragma: no cover
                    info[attr] = None
                    rec["errors"].append(f"{name}.{attr}: {type(e).__name__}")
            if name in solids:
                try:
                    info["volume_model_units3"] = float(o.volume)
                except Exception:
                    info["volume_model_units3"] = None
            f = out / f"{name}.obj"
            try:
                app.modeler.oeditor.ExportModelMeshToFile(str(f), [name])
                info["obj"] = f.name if f.exists() and f.stat().st_size > 0 else None
                if info["obj"]:
                    info["obj_sha256"] = sha(f)
            except Exception as e:
                info["obj"] = None
                rec["errors"].append(f"{name}: export failed ({type(e).__name__})")
            rec["objects"][name] = info
        rec["export_method"] = ("AEDT oEditor.ExportModelMeshToFile(path, [object]) -- the "
                                "native call used by PyAEDT post.export_model_obj("
                                "export_as_multiple_objects=True); one OBJ per object")
    finally:
        rec["session_s"] = round(time.time() - t0, 1)
        app.release_desktop(close_projects=True, close_desktop=True)
    (out / "export.json").write_text(json.dumps(rec, indent=2, default=str))
    print(json.dumps({"key": key, "n_obj": sum(1 for v in rec["objects"].values() if v.get("obj")),
                      "errors": rec["errors"]}))


def run_exports(keys):
    from aedt_proc import run_tracked, scratch_env
    env = scratch_env(WORK)
    RR.mkdir(parents=True, exist_ok=True)
    runs = {}
    for k in keys:
        dst = RR / MODELS[k]["project"]
        if not dst.exists():
            dst.write_bytes((SRC / MODELS[k]["project"]).read_bytes())
        runs[k] = run_tracked(["/home/beams0/MGHARIB/envs/etm/bin/python", __file__,
                               "export", k], RR / f"export_{k}.log", timeout_s=900,
                              env=env, cwd=str(RR))
        print(k, {x: runs[k][x] for x in ("rc", "wall_s", "timed_out")}, flush=True)
    return runs


# =============================================================== stage 2: VTK =====
S2, S6 = math.sqrt(2.0), math.sqrt(6.0)
VIEW = (1.0, -1.0, 1.0)              # exact isometric, same octant as AEDT's default view
CUT = "front quadrant x > 0, y < 0 removed (capped cut faces at x = 0 and y = 0)"


def load_spec(key):
    """Layer list of the SAME benchmark run (tool_evidence/<stage>/setup.json); the AEDT
    bodies are named L<i>_<tile|gap|all> with i the index into this list."""
    if key.startswith("thermal_column"):
        f = R / "presentation" / "prelim_hvr" / "tool_evidence" / key / "setup.json"
        return json.loads(f.read_text())
    return None


def role(key, name, spec):
    """(figstyle MAT key, plain words, layer name, part) for one AEDT body."""
    if spec:
        i = int(name.split("_")[0][1:])
        ly = spec["layers"][i]["name"]
        part = name.split("_", 1)[1]                     # tile | gap | all
        if ly == "board":
            return "pcb", "board (FR4)", ly, part
        if ly == "bga":
            return "solder", "BGA layer (homogenised)", ly, part
        if ly in ("sub_lower", "tile_band"):
            return (("tsv", "Cu TSV tile", ly, part) if part == "tile" else
                    ("silicon", "silicon substrate", ly, part))
        if ly == "interface":
            return "solder", "microbump interface", ly, part
        if "attach_vr" in ly:                            # Cu pillars + solder caps in underfill
            return (("solder", "VR attach: Cu pillars in underfill", ly, part)
                    if part != "gap" else ("fill", "underfill ring", ly, part))
        if ly == "die":
            return "die", "compute die (silicon)", ly, part
        if ly == "tim":
            return "tim", "TIM", ly, part
        if "rdl" in ly:
            return (("rdl", "Cu RDL tier (10 µm)", ly, part) if part != "gap" else
                    ("fill", "underfill ring", ly, part))
        if part == "gap":
            return "fill", "underfill ring", ly, part
        if "gan_hs" in ly:
            return "gan", "GaN high-side tier", ly, part
        if "gan_ls" in ly:
            return "gan", "GaN low-side tier", ly, part
        if "caps" in ly:
            return "caps", "flying-capacitor tier", ly, part
        if "inductor" in ly:
            return "inductor", "inductor + C_out tier", ly, part
        return "silicon", ly, ly, part
    return {"si": ("silicon", "silicon", "si", ""),
            "org": ("pcb", "organic build-up", "org", ""),
            "patch": ("solder", "support patch (sheet)", "patch", "")}.get(
        name, ("silicon", name, name, ""))


def _poly(path, sc, to_mm):
    import vtk
    r = vtk.vtkOBJReader()
    r.SetFileName(str(path))
    r.Update()
    tf = vtk.vtkTransform()
    k = to_mm / sc
    tf.Scale(k, k, k)
    t = vtk.vtkTransformPolyDataFilter()
    t.SetInputConnection(r.GetOutputPort())
    t.SetTransform(tf)
    cl = vtk.vtkCleanPolyData()                     # AEDT writes vertices per face
    cl.SetInputConnection(t.GetOutputPort())
    cl.PointMergingOn()
    cl.SetTolerance(0.0)
    cl.Update()
    return r.GetOutput(), cl.GetOutput()


def _clip(pd, planes):
    import vtk
    pc = vtk.vtkPlaneCollection()
    for o, n in planes:
        pl = vtk.vtkPlane()
        pl.SetOrigin(*o)
        pl.SetNormal(*n)
        pc.AddItem(pl)
    c = vtk.vtkClipClosedSurface()
    c.SetInputData(pd)
    c.SetClippingPlanes(pc)
    c.GenerateFacesOn()
    c.Update()
    return c.GetOutput()


def _drop_seam(lines_pd, tol=1e-7):
    """Remove edge segments on the internal cut plane x = 0, y > 0, where the two
    clipped pieces of one body meet (they are not edges of the model)."""
    import numpy as np
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    pts = vtk_to_numpy(lines_pd.GetPoints().GetData()) if lines_pd.GetNumberOfPoints() else None
    out = vtk.vtkPolyData()
    out.SetPoints(lines_pd.GetPoints())
    ca = vtk.vtkCellArray()
    for i in range(lines_pd.GetNumberOfCells()):
        c = lines_pd.GetCell(i)
        ids = [c.GetPointId(j) for j in range(c.GetNumberOfPoints())]
        q = pts[ids]
        if np.all(np.abs(q[:, 0]) < tol) and np.all(q[:, 1] > -tol) and q[:, 1].mean() > tol:
            continue
        ca.InsertNextCell(len(ids), ids)
    out.SetLines(ca)
    return out


def _volume(pd):
    import vtk
    tri = vtk.vtkTriangleFilter()
    tri.SetInputData(pd)
    tri.Update()
    m = vtk.vtkMassProperties()
    m.SetInputData(tri.GetOutput())
    m.Update()
    return m.GetVolume()


def render(key):
    import numpy as np
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    import figstyle as FS
    d = RR / key
    ex = json.loads((d / "export.json").read_text())
    objs = {n: v for n, v in ex["objects"].items() if v.get("obj")}
    failed = [n for n, v in ex["objects"].items() if not v.get("obj")]
    spec = load_spec(key)
    to_mm = {"mm": 1.0, "um": 1e-3, "meter": 1e3}.get(ex.get("model_units", "mm"), 1.0)
    # ---- read; verify each OBJ against AEDT's own bounding box (and volume) ----------
    checks, raw = {}, {}
    for n, v in objs.items():
        r = vtk.vtkOBJReader()
        r.SetFileName(str(d / v["obj"]))
        r.Update()
        b = r.GetOutput().GetBounds()
        bb = v.get("bounding_box")
        aedt = [bb[0], bb[3], bb[1], bb[4], bb[2], bb[5]]
        best = min(((sc, max(abs(b[i] / sc - aedt[i]) for i in range(6)))
                    for sc in (1.0, 1e-3, 1e3)), key=lambda t: t[1])
        checks[n] = {"obj_bounds_raw": list(b), "aedt_bounding_box": bb,
                     "obj_scale_to_model_units": best[0], "max_abs_dev_model_units": best[1],
                     "n_triangles": r.GetOutput().GetNumberOfCells()}
    scs = {c["obj_scale_to_model_units"] for c in checks.values()}
    if len(scs) != 1:
        raise RuntimeError(f"{key}: inconsistent OBJ scale {scs}")
    sc = scs.pop()
    worst = max(c["max_abs_dev_model_units"] for c in checks.values())
    if worst > 1e-6:
        raise RuntimeError(f"{key}: exported mesh does not match AEDT bounding box ({worst})")
    cut = spec is not None
    W, H = 1600, 1120
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    ren.AutomaticLightCreationOff()
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetSize(W, H)
    rw.SetMultiSamples(8)
    rw.AddRenderer(ren)

    def hexrgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    meta, lo, hi = {}, np.full(3, 1e9), np.full(3, -1e9)
    for n, v in objs.items():
        k, word, ly, part = role(key, n, spec)
        _, pd = _poly(d / v["obj"], sc, to_mm)
        b = np.array(pd.GetBounds())
        lo, hi = np.minimum(lo, b[[0, 2, 4]]), np.maximum(hi, b[[1, 3, 5]])
        vol = _volume(pd) if v["kind"] == "solid" else None
        pieces = [pd]
        if cut and v["kind"] == "solid":
            a_ = _clip(pd, [((0, 0, 0), (-1, 0, 0))])                       # x <= 0
            b_ = _clip(pd, [((0, 0, 0), (1, 0, 0)), ((0, 0, 0), (0, 1, 0))])  # x>=0, y>=0
            pieces = [q for q in (a_, b_) if q.GetNumberOfCells() > 0]
        for q in pieces:
            mp = vtk.vtkPolyDataMapper()
            mp.SetInputData(q)
            mp.ScalarVisibilityOff()
            mp.SetResolveCoincidentTopologyToPolygonOffset()
            ac = vtk.vtkActor()
            ac.SetMapper(mp)
            pr = ac.GetProperty()
            pr.SetColor(*hexrgb(FS.MAT[k] if v["kind"] == "solid" else FS.OPEN))
            pr.SetInterpolationToFlat()
            pr.SetAmbient(0.52)
            pr.SetDiffuse(0.55)
            pr.SetSpecular(0.0)
            ren.AddActor(ac)
            fe = vtk.vtkFeatureEdges()
            fe.SetInputData(q)
            fe.BoundaryEdgesOn()
            fe.FeatureEdgesOn()
            fe.SetFeatureAngle(20)
            fe.ManifoldEdgesOff()
            fe.NonManifoldEdgesOff()
            fe.ColoringOff()
            fe.Update()
            edges = fe.GetOutput()
            if cut:
                edges = _drop_seam(edges)
            em = vtk.vtkPolyDataMapper()
            em.SetInputData(edges)
            em.ScalarVisibilityOff()
            ea = vtk.vtkActor()
            ea.SetMapper(em)
            ea.GetProperty().SetColor(*hexrgb(FS.INK))
            ea.GetProperty().SetLineWidth(1.3)
            ea.GetProperty().SetOpacity(0.6)
            ren.AddActor(ea)
        meta[n] = {"aedt_material": v.get("material_name"), "plain": word,
                   "layer": ly, "part": part, "figstyle_key": k, "kind": v["kind"],
                   "bounds_mm": [round(float(x), 6) for x in b],
                   "volume_obj_mm3": vol, "volume_aedt_model_units3": v.get("volume_model_units3")}
    c = 0.5 * (lo + hi)
    big = float(max(hi - lo))
    light = vtk.vtkLight()
    light.SetLightTypeToSceneLight()
    light.SetPosition(*(c + np.array([0.35, -1.0, 1.7]) * 40 * big))
    light.SetFocalPoint(*c)
    light.SetIntensity(1.0)
    ren.AddLight(light)
    cam = ren.GetActiveCamera()
    cam.ParallelProjectionOn()
    cam.SetFocalPoint(*c)
    cam.SetPosition(*(c + np.array(VIEW) / math.sqrt(3) * 40 * big))
    cam.SetViewUp(0, 0, 1)
    # fit: projected extents of the bounding box on the screen axes
    rr = np.array([1, 1, 0]) / S2
    uu = np.array([-1, 1, 2]) / S6
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                        for z in (lo[2], hi[2])])
    Ew = np.ptp(corners @ rr)
    Eh = np.ptp(corners @ uu)
    kpx = min((760.0 if cut else 900.0) / Ew, (H - 170.0) / Eh)
    cam.SetParallelScale(0.5 * H / kpx)
    ren.ResetCameraClippingRange()
    rw.Render()
    # world -> pixel map, fitted while the window exists (parallel projection: affine)
    pts = np.vstack([corners, c[None, :]])
    pix = []
    for p in pts:
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0)
        ren.WorldToDisplay()
        x_, y_, _ = ren.GetDisplayPoint()
        pix.append((x_, H - y_))
    A = np.hstack([pts, np.ones((len(pts), 1))])
    M, res, *_ = np.linalg.lstsq(A, np.array(pix), rcond=None)
    fit_err = float(np.abs(A @ M - np.array(pix)).max())
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.ReadFrontBufferOff()
    w2i.Update()
    im = w2i.GetOutput()
    arr = vtk_to_numpy(im.GetPointData().GetScalars()).reshape(H, W, -1)[::-1, :, :3].copy()
    proj = {"M": M.tolist(), "fit_err_px": fit_err, "px_per_mm_view_plane": kpx,
            "view_direction": VIEW, "parallel": True}
    rw.Finalize()
    return arr, meta, checks, failed, ex, proj, (lo, hi), sc, cut


def annotate(key, arr, meta, proj, lohi, cut):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    import figstyle as FS
    FR = "/usr/share/fonts/google-noto/NotoSans-Regular.ttf"
    FB = "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"
    H, W = arr.shape[:2]
    TOP, BOT = 96, 96
    M = np.array(proj["M"])
    img = Image.new("RGB", (W, H + TOP + BOT), "white")
    img.paste(Image.fromarray(arr.astype("uint8"), "RGB"), (0, TOP))
    d = ImageDraw.Draw(img)

    def rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def F(s, b=False):
        return ImageFont.truetype(FB if b else FR, s)

    def P(p):
        x, y = np.array([p[0], p[1], p[2], 1.0]) @ M
        return float(x), float(y) + TOP

    d.rectangle([0, 0, W, TOP - 1], fill=rgb(FS.INK))
    d.text((22, 12), BANNER, font=F(34, True), fill=(255, 255, 255))
    title = {"thermal_column_Z1": "AEDT matched unit-cell thermal model, Z1 HV-S0 "
                                  "(project col_Z1_HV_S0.aedt, design 'column')",
             "thermal_column_Z2": "AEDT matched unit-cell thermal model, Z2 HV-S0 "
                                  "(project col_Z2_HV_S0.aedt, design 'column')",
             "mech_bilayer": "AEDT matched bilayer warpage model "
                             "(project mech_bilayer2.aedt, design 'structural')"}[key]
    d.text((22, 58), title, font=F(22), fill=(222, 228, 234))
    lo, hi = lohi
    labels = []
    items = []          # (side, lines, anchor_xyz, objects)

    def group(pred):
        return [n for n, m in meta.items() if pred(m)]

    if cut:
        xa, ya = lo[0], lo[1]                   # cell is centred: outer faces at -p/2
        p = hi[0] - lo[0]
        tiles = group(lambda m: m["part"] == "tile")
        t = max(meta[n]["bounds_mm"][1] - meta[n]["bounds_mm"][0] for n in tiles) if tiles else p

        def zr(names):
            z0 = min(meta[n]["bounds_mm"][4] for n in names)
            z1 = max(meta[n]["bounds_mm"][5] for n in names)
            return z0, z1

        def outer(names, words):
            z0, z1 = zr(names)
            items.append(("L", words + [f"{(z1 - z0) * 1e3:.0f} µm" if z1 - z0 < 1 else
                                        f"{z1 - z0:.2f} mm"], (xa + 0.3 * p, ya, 0.5 * (z0 + z1)),
                          names))

        def inner(names, words):
            z0, z1 = zr(names)
            items.append(("R", words, (0.22 * t, 0.0, 0.5 * (z0 + z1)), names))

        for lyname, words in (("tim", ["TIM"]), ("die", ["compute die (silicon)"]),
                              ("bga", ["BGA layer (homogenised)"]), ("board", ["board (FR4)"])):
            g = group(lambda m, l=lyname: m["layer"] == l)
            if g:
                outer(g, words)
        sub = group(lambda m: m["layer"] in ("sub_lower", "tile_band") and m["part"] == "gap")
        if sub:
            outer(sub, ["silicon substrate"])
        ring = group(lambda m: m["part"] == "gap" and m["figstyle_key"] == "fill")
        if ring:
            z0, z1 = zr(ring)
            items.append(("L", ["underfill ring (converter tiers)", f"{(z1 - z0):.2f} mm"],
                          (xa + 0.12 * p, ya, 0.5 * (z0 + z1)), ring))
        for words, pred in ((["Cu TSV tile (substrate)"],
                             lambda m: m["figstyle_key"] == "tsv"),
                            (["inductor + C_out tier"], lambda m: m["plain"].startswith("inductor")),
                            (["flying-capacitor tier"], lambda m: m["plain"].startswith("flying")),
                            (["GaN low-side tier", "(modelled as silicon)"],
                             lambda m: m["plain"] == "GaN low-side tier"),
                            (["GaN high-side tier", "(modelled as silicon)"],
                             lambda m: m["plain"] == "GaN high-side tier")):
            g = group(lambda m, pr=pred: m["part"] == "tile" and pr(m))
            if g:
                inner(g, words)
        rdl = group(lambda m: m["figstyle_key"] == "rdl" and m["part"] == "tile")
        gls = group(lambda m: m["plain"] == "GaN low-side tier" and m["part"] == "tile")
        if rdl and gls:
            ztop = meta[gls[0]]["bounds_mm"][5]
            pick = min(rdl, key=lambda n: abs(meta[n]["bounds_mm"][4] - ztop))
            z0, z1 = zr([pick])
            items.append(("R", ["Cu RDL tiers, 10 µm each", f"({len(rdl)} in the tile; "
                                "this one above GaN LS)"],
                          (0.42 * t, 0.0, 0.5 * (z0 + z1)), rdl))
    else:
        si, org = meta.get("si"), meta.get("org")
        if si:
            b = si["bounds_mm"]
            items.append(("R", ["silicon ('si')", f"{(b[5] - b[4]) * 1e3:.0f} µm, upper"],
                          (b[1], b[2] + 0.62 * (b[3] - b[2]), 0.5 * (b[4] + b[5])), ["si"]))
        if org:
            b = org["bounds_mm"]
            items.append(("R", ["organic build-up ('org')", f"{(b[5] - b[4]) * 1e3:.0f} µm, lower"],
                          (b[1], b[2] + 0.38 * (b[3] - b[2]), 0.5 * (b[4] + b[5])), ["org"]))
        if "patch" in meta:
            b = meta["patch"]["bounds_mm"]
            items.append(("L", ["support patch ('patch', sheet)",
                                f"{(b[1] - b[0]) * 1e3:.0f} x {(b[3] - b[2]) * 1e3:.0f} µm at the "
                                "origin,", "on the underside (hidden)"],
                          (0.5 * (b[0] + b[1]), 0.5 * (b[2] + b[3]), b[4]), ["patch"], 120))

    # ---- layout: two columns, non-overlapping, leaders to each object's own face ------
    def measure(lines):
        fs = [F(23, True)] + [F(20)] * (len(lines) - 1)
        return fs, max(d.textlength(tx, font=f) for tx, f in zip(lines, fs)), \
            sum(f.size + 6 for f in fs)

    placed = []
    for side in ("L", "R"):
        grp = [it for it in items if it[0] == side]
        grp.sort(key=lambda it: P(it[2])[1])
        prev = TOP + 18
        rows = []
        for it in grp:
            fs, w, h = measure(it[1])
            want = P(it[2])[1] - h / 2 + (it[4] if len(it) > 4 else 0)
            rows.append([it, fs, w, h, want])
        tops = []
        for r_ in rows:
            tp = max(r_[4], prev)
            tops.append(tp)
            prev = tp + r_[3] + 16
        nxt = TOP + H - 20
        for i in range(len(rows) - 1, -1, -1):
            if tops[i] + rows[i][3] > nxt:
                tops[i] = nxt - rows[i][3]
            nxt = tops[i] - 16
        for r_, tp in zip(rows, tops):
            placed.append((r_, tp))
    boxes = []
    for (it, fs, w, h, _), tp in placed:
        side, lines, anchor, names = it[:4]
        x = 26 if side == "L" else W - 26 - w
        ax, ay = P(anchor)
        ex_ = x + w + 8 if side == "L" else x - 8
        ey = tp + fs[0].size / 2 + 4
        d.line([(ex_, ey), (ax, ay)], fill=(255, 255, 255), width=5)
        d.line([(ex_, ey), (ax, ay)], fill=rgb(FS.MUTED), width=2)
        d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=rgb(FS.INK), outline=(255, 255, 255),
                  width=2)
        yy = tp
        for tx, f in zip(lines, fs):
            d.text((x, yy), tx, font=f, fill=rgb(FS.INK), stroke_width=4,
                   stroke_fill=(255, 255, 255))
            yy += f.size + 6
        boxes.append((x, tp, x + w, tp + h))
        labels.append({"text": " / ".join(lines), "objects": names,
                       "anchor_mm": [round(float(v), 4) for v in anchor],
                       "anchor_px": [round(ax, 1), round(ay, 1)]})
    coll = [(i, j) for i in range(len(boxes)) for j in range(i + 1, len(boxes))
            if boxes[i][0] < boxes[j][2] and boxes[j][0] < boxes[i][2]
            and boxes[i][1] < boxes[j][3] and boxes[j][1] < boxes[i][3]]
    # ---- footer: caption line 1, scale bar line 2 (never on the same line) -----------
    kpx = proj["px_per_mm_view_plane"]
    nice = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
    L_mm = max(v for v in nice if v * kpx <= 0.25 * W)
    yb = TOP + H + 62
    x1 = W - 40
    x0 = x1 - L_mm * kpx
    d.line([(0, TOP + H), (W, TOP + H)], fill=rgb(FS.LINE), width=1)
    cap = ("Isometric parallel projection of the bodies exported from the AEDT project "
           "(AEDT's own tessellation); colours from figstyle.py by layer role.")
    if cut:
        cap += " Cut-away: front quadrant removed to show the tile inside the underfill ring."
    fcap = F(19)
    words, lines, cur = cap.split(" "), [], ""
    for w_ in words:
        tt = (cur + " " + w_).strip()
        if d.textlength(tt, font=fcap) <= W - 44:
            cur = tt
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    yy = TOP + H + 8
    for ln in lines[:2]:
        d.text((22, yy), ln, font=fcap, fill=rgb(FS.MUTED))
        yy += 25
    yb = max(yb, yy + 14)
    d.line([(x0, yb), (x1, yb)], fill=rgb(FS.INK), width=4)
    d.line([(x0, yb - 9), (x0, yb + 9)], fill=rgb(FS.INK), width=3)
    d.line([(x1, yb - 9), (x1, yb + 9)], fill=rgb(FS.INK), width=3)
    sl = f"{L_mm:g} mm (view-plane scale, like AEDT's ruler)"
    tw = d.textlength(sl, font=F(19))
    d.text((x0 - tw - 16, yb - 13), sl, font=F(19), fill=rgb(FS.INK))
    if yb + 14 > H + TOP + BOT:
        raise RuntimeError("footer overflow")
    return img, labels, L_mm, coll


def render_all(keys):
    out = {}
    for k in keys:
        d = RR / k
        rec = {"key": k}
        if not (d / "export.json").exists():
            rec["status"] = "SKIPPED: no export (AEDT export step failed or not run)"
            out[k] = rec
            print(k, rec["status"])
            continue
        try:
            arr, meta, checks, failed, ex, proj, lohi, sc, cut = render(k)
        except Exception as e:
            rec["status"] = f"SKIPPED: {type(e).__name__}: {str(e)[:200]}"
            out[k] = rec
            print(k, rec["status"])
            continue
        img, labels, L_mm, coll = annotate(k, arr, meta, proj, lohi, cut)
        png = FIGS / f"{MODELS[k]['out']}.png"
        img.save(png, optimize=True)
        files = {n: {"file": str(RR / k / v["obj"]), "sha256": v.get("obj_sha256")}
                 for n, v in ex["objects"].items() if v.get("obj")}
        side = {"figure": f"presentation/prelim_hvr/figs/{png.name}",
                "banner": BANNER,
                "source_project": ex["source_project_original"],
                "source_project_sha256": ex["source_project_sha256"],
                "opened_copy": ex["opened_copy"],
                "design": ex["design"], "designs_in_project": ex.get("designs_in_project"),
                "solution_type": ex.get("solution_type"), "model_units": ex.get("model_units"),
                "export_method": ex.get("export_method"),
                "exported_objects": sorted(files),
                "objects_not_exported": failed,
                "exported_geometry_files": files,
                "geometry_check": {"rule": "each OBJ's bounds equal AEDT's own bounding box "
                                           "of that body (max deviation recorded per object)",
                                   "obj_scale_to_model_units": sc, "per_object": checks},
                "view": {"projection": "parallel (orthographic), exact isometric",
                         "view_direction": VIEW,
                         "cutaway": CUT if cut else "none (whole model shown)",
                         "cutaway_method": ("vtkClipClosedSurface on each watertight AEDT body "
                                            "(points merged first), keeping x <= 0 and "
                                            "(x >= 0 and y >= 0); cut faces capped. A viewing "
                                            "operation only: no body is moved, resized or "
                                            "added.") if cut else None,
                         "world_to_pixel_fit_err_px": proj["fit_err_px"]},
                "objects": meta, "labels": labels, "label_box_collisions": coll,
                "label_sources": ("every label names AEDT bodies (see 'objects'); plain words "
                                  "from the AEDT material and, for the unit cells, from the "
                                  "layer list of the same benchmark run "
                                  "(tool_evidence/<stage>/setup.json; body L<i>_* = layer i)"),
                "scale_bar_mm": L_mm,
                "scale_bar_meaning": "length in the view plane (as AEDT's ruler); edges along "
                                     "x, y or z appear at sqrt(2/3) = 0.816 of it",
                "colours": "scripts/figstyle.py MAT palette (unmodified), by layer role",
                "renderer": "VTK 9.6.2 offscreen (EGL)",
                "generator": "scripts/reference_tools/aedt_geometry_rerender.py",
                "png_sha256": sha(png)}
        png.with_suffix(".json").write_text(json.dumps(side, indent=2) + "\n")
        rec["status"] = "RENDERED"
        out[k] = rec
        print(k, "rendered", png.name, "collisions", coll, "fit_err_px",
              round(proj["fit_err_px"], 4))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = [a for a in sys.argv[2:]] or list(MODELS)
    if cmd == "export":
        export(keys[0])
    elif cmd == "exports":
        run_exports(keys)
    elif cmd == "render":
        render_all(keys)
    else:
        run_exports(keys)
        render_all(keys)
