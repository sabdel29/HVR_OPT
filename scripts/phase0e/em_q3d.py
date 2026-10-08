#!/usr/bin/env python3
"""Phase-0E EM validation with ANSYS Q3D Extractor (licence restored 2026-09-06).

Structures (brief Sec. 9):
  EM-1  vertical TSV field with landing pads      -- ARCH_A / ARCH_B vertical tier
  EM-2  LV-side TSV + lateral landing-pad feed    -- current crowding at the pad
  EM-3  RDL source -> load sheet                  -- the compact sheet solver's target
  EM-4  RDL trace into a TSV                      -- crowding at the lateral/vertical join

Q3D solves the DC conduction problem directly and gives R(f) and L(f) from the AC RL
solution, which is what the brief asks for. Everything is compared against the compact
model in scripts/phase0e/stack.py; nothing here is tuned to match.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "results" / "phase0e" / "aedt"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "scripts" / "phase0e"))

RHO_CU = 17.0e-9          # the source's copper resistivity, used for BOTH models
SIGMA_CU = 1.0 / RHO_CU   # 5.882e7 S/m -- NOT the AEDT default 5.8e7


def _q3d(design: str, ng: bool = True):
    from ansys.aedt.core import Q3d
    q = Q3d(project=str(OUT / "phase0e_em.aedt"), design=design, version="2026.1",
            non_graphical=ng, new_desktop=False)
    q.modeler.model_units = "um"
    # Force the source's resistivity so any difference is physics, not a material default.
    if "cu_src" not in q.materials.material_keys:
        m = q.materials.add_material("cu_src")
        m.conductivity = SIGMA_CU
    return q


def _setup(q, name="s1", freq="1MHz"):
    """Q3D solves Cap / AC-RL / DC as separate sub-solutions; DC must be switched ON."""
    su = q.create_setup(name=name)
    su.props["AdaptiveFreq"] = freq
    su.props["SaveFields"] = True
    su.props["Enabled"] = True
    for blk, flag in (("Cap", False), ("AC", True), ("DC", True)):
        if blk in su.props and isinstance(su.props[blk], dict):
            su.props[blk]["MaxPass"] = 12
            if "Input" in su.props[blk] and isinstance(su.props[blk]["Input"], dict):
                su.props[blk]["Input"]["MaxPass"] = 12
    su.props["SolveTypeOption"] = "Resistance/Inductance"
    su.update()
    return su


def _face_at_z(obj, z_um, tol=1.0):
    """Pick the planar face whose centroid sits at a given z -- far more reliable than
    passing an axis direction, which can silently select the wrong face."""
    best, bd = None, 1e30
    for f in obj.faces:
        d = abs(f.center[2] - z_um)
        if d < bd:
            best, bd = f, d
    if bd > tol:
        raise RuntimeError(f"no face near z={z_um} (closest {bd:.2f} um)")
    return best


def _dump_messages(q, tag):
    try:
        msgs = q.logger.messages.global_level + q.logger.messages.project_level \
               + q.logger.messages.design_level
    except Exception:
        msgs = []
    for m in msgs[-25:]:
        print(f"   [AEDT/{tag}] {m}")


def em1_tsv_field(n_side=3, d_um=30.0, h_um=300.0, pitch_um=60.0, ng=True) -> dict:
    """N x N copper TSVs between two copper landing pads. DC resistance of the field."""
    q = _q3d("EM1_tsv_field", ng)
    pad_t = 5.0
    span = (n_side - 1) * pitch_um + d_um * 2
    vias = []
    for i in range(n_side):
        for j in range(n_side):
            x = (i - (n_side - 1) / 2) * pitch_um
            y = (j - (n_side - 1) / 2) * pitch_um
            vias.append(q.modeler.create_cylinder(orientation="Z",
                        origin=[x, y, 0], radius=d_um / 2, height=h_um,
                        name=f"via_{i}_{j}", material="cu_src"))
    bot = q.modeler.create_box([-span/2, -span/2, -pad_t], [span, span, pad_t],
                               name="pad_bot", material="cu_src")
    top = q.modeler.create_box([-span/2, -span/2, h_um], [span, span, pad_t],
                               name="pad_top", material="cu_src")
    q.modeler.unite([bot] + vias + [top])
    solid = q.modeler[bot.name]
    # Q3D needs a bounding region; without one the field solve aborts.
    q.modeler.create_air_region(x_pos=150, y_pos=150, z_pos=80,
                                x_neg=150, y_neg=150, z_neg=80)
    q.auto_identify_nets()
    f_bot = _face_at_z(solid, -pad_t)
    f_top = _face_at_z(solid, h_um + pad_t)
    src = q.source(assignment=f_bot.id, name="src")
    snk = q.sink(assignment=f_top.id, name="snk")
    print(f"   nets={q.net_names}  src_face={f_bot.id}@z={f_bot.center[2]:.1f} "
          f"snk_face={f_top.id}@z={f_top.center[2]:.1f}")
    su = _setup(q)
    print(f"   setup blocks: {[k for k in su.props if k in ('Cap','AC','DC')]}")
    t0 = time.time()
    ok = q.analyze_setup("s1")
    el = time.time() - t0
    print(f"   analyze returned {ok} in {el:.1f}s")
    if not ok:
        _dump_messages(q, "EM1")
        for lg in sorted(OUT.rglob("*.log")) + sorted(OUT.rglob("*.profile")):
            try:
                txt = lg.read_text(errors="ignore")
            except Exception:
                continue
            hits = [l for l in txt.splitlines()
                    if any(k in l.lower() for k in ("error", "fail", "cannot", "invalid"))]
            for h in hits[:12]:
                print(f"   [{lg.name}] {h.strip()[:160]}")
    def grab(expr):
        for ctx in ("Original", "AC RL", "DC RL", None):
            try:
                d = q.post.get_solution_data(expressions=expr,
                                             setup_sweep_name="s1 : LastAdaptive",
                                             context=ctx)
                if d and d.data_real():
                    return float(d.data_real()[0])
            except Exception:
                continue
        return float("nan")

    net = q.net_names[0] if q.net_names else "src"
    r_ac = grab(f"ACR({net},{net})")
    r_dc = grab(f"DCR({net},{net})")
    if r_ac != r_ac:
        r_ac = grab("ACR(src,src)")
    if r_dc != r_dc:
        r_dc = grab("DCR(src,src)")
    # The matrix export is the authoritative result path; expression parsing is a fallback.
    mfile = OUT / "em1_matrix.txt"
    try:
        q.export_matrix_data(str(mfile), problem_type="DC RL")
    except Exception as e:
        print(f"   matrix export (DC) failed: {e}")
        try:
            q.export_matrix_data(str(mfile))
        except Exception as e2:
            print(f"   matrix export failed: {e2}")
    if mfile.exists():
        print("   --- matrix export ---")
        for ln in mfile.read_text().splitlines()[:20]:
            print("   " + ln)
    q.save_project()
    q.release_desktop(close_projects=False, close_desktop=True)

    import math
    a = math.pi * (d_um * 1e-6) ** 2 / 4
    r_single = RHO_CU * (h_um * 1e-6) / a
    n = n_side ** 2
    return {"structure": "EM-1 TSV field", "n_via": n, "d_um": d_um, "h_um": h_um,
            "pitch_um": pitch_um, "r_single_analytic_ohm": r_single,
            "r_field_analytic_ohm": r_single / n,
            "r_q3d_ac_ohm": r_ac, "r_q3d_dc_ohm": r_dc, "solve_s": el}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--case", default="em1")
    a = ap.parse_args()
    r = {"em1": em1_tsv_field}[a.case]()
    print(json.dumps(r, indent=2))
    (OUT / f"{a.case}.json").write_text(json.dumps(r, indent=2))
