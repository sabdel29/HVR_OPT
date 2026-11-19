"""TCPMT review variants (second review round).

MC2  mechanical -> thermal feedback through the top thermal interface. The production
     chain is one-way from the converged temperature field to the mechanics. The one
     feedback path an intact package has at first order is the bond line of the top TIM:
     the die warps, the cold plate stays flat, and the TIM fills the gap. The plate rests on
     the warped surface's highest point at the nominal 50-um bond line, so the local extra
     thickness is g(x, y) = max(u_z) - u_z(x, y) >= 0, in series with the film:
         h_eff = 1 / (1/h + g / k_TIM).
     The map comes from the previous mechanics solve (the tier's converged case for the
     first pass); E-T fixed point + mechanics repeat until the die warpage changes by less
     than 1 % and the loss by less than 0.05 W. Bounding: the TIM follows the free warpage
     (no plate compliance, no pump-out, no contact pressure dependence).

MC10 non-uniform die power. The production die load (1 kW) is uniform over the die. Here
     75 % of it is dissipated in the central half of the die area and 25 % in the rest (a
     3:1 flux ratio between core and periphery), the same total. A second, realistic map
     (hotmap): eight 1.5-mm hot spots at 8 x the background flux (HOTMAP), the same total.

Cooling model form: the caloric correction is production; `caloric` now runs the
superseded uniform-sink top-plate coefficient as variant plate_caloric_legacy_<tier>.

Both use the hooks of final_closure_physical_etm (TOP_FILM_HOOK, and replacements of
deposits_from_ledger / _region_elems inside this process only), so the production path is
unchanged. Cooling tiers: A = the same top plate (Z3 top-only), B = top plate plus the
identical bottom plate through a 50-um TIM (tcpmt_manuscript_macros.TIERS).

    python tcpmt_review_variants.py feedback ARCH TIER
    python tcpmt_review_variants.py hotspot  ARCH TIER
    python tcpmt_review_variants.py hotmap   ARCH TIER
    python tcpmt_review_variants.py caloric  ARCH TIER   (the legacy coefficient)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_sensitivity as S                               # noqa: E402
import final_closure_ledger as FL                                   # noqa: E402
from hvr_scratch import path as scratch                             # noqa: E402

E = S.E
SCEN = "HV_S0"
OUT = R / "research" / "tcpmt_revision" / "review_variants"
FIELDS = Path(os.environ.get("HVR_FIELDS",
                             "/home/beams0/SABDELZAHER/ETM_project/scratch/fields"))
#: the cooling tiers of the comparison: arch, tier -> sensitivity variant (None = production)
TIER_BASE = {("Z1", "A"): None, ("Z2", "A"): None, ("Z3", "A"): "z3_top_only",
             ("Z1", "B"): "z1_bottom_plate_tim", ("Z2", "B"): "z2_cooled_tim",
             ("Z3", "B"): "z3_plate_tim"}
HOT_AREA, HOT_POWER = 0.5, 0.75
FB_TOL_WARP, FB_TOL_P_W, FB_MAX_ITER = 0.01, 0.05, 5


def _long_ccx(timeout=43200):
    """Structural solves on the shared host can exceed the 2-h default; 12 h, as
    scratch/remech_long.py used for the r31 Z2 solve."""
    import production_et as PE
    orig = PE.ccxio.run_ccx
    if getattr(orig, "_long", False):
        return
    def run(job, threads=None, timeout_=timeout):
        return orig(job, threads, timeout_)
    run._long = True
    PE.ccxio.run_ccx = run


def base_case(arch, tier):
    v = TIER_BASE[(arch, tier)]
    return E.case_path(arch, SCEN) if v is None else S.case_file(arch, v)


def base_field(arch, tier):
    v = TIER_BASE[(arch, tier)]
    return FIELDS / (f"etm_{arch}_{SCEN}_r21" if v is None else f"etm_{arch}_{SCEN}__{v}")


def apply_tier(arch, tier):
    v = TIER_BASE[(arch, tier)]
    if v is not None:
        S.VARIANTS[v]["apply"]()


def _summary(m, L, th, hist, mech):
    rows = L["rows"]
    last = hist[-1]
    crit = mech["joint_search"]["critical"] if mech else None
    return {"P_loss_w": L["P_loss_w"],
            "T_max_C": th["T_max_C"], "T_die_mean_C": last.get("T_die_mean_C"),
            "die_T_max_C": th.get("die_T_max_C"), "die_T_mean_C": th.get("die_T_mean_C"),
            "T_hs_C": last.get("T_hs_C"), "T_ls_C": last.get("T_ls_C"),
            "q_top_W": th["q_top_W"], "q_bot_W": th["q_bot_W"],
            "q_bottom_plate_W": th.get("q_bottom_plate_W"), "q_extra_W": th.get("q_extra_W"),
            "energy_residual_rel": th["energy_residual_rel"],
            "die_warpage_pv_um": mech["die_warpage_pv_um"] if mech else None,
            "du_c_um": crit["du_um"] if crit else None,
            "T_joint_C": crit["T_C"] if crit else None,
            "critical_site_mm": [crit["x_mm"], crit["y_mm"]] if crit else None,
            "n_rows": len(rows)}


def run_et_seeded(arch, scen, h_xy, refine, temps0=None):
    """E.run_et with the region temperatures of the previous feedback pass as the first
    guess (same loop, tolerances and outputs; only the starting point differs)."""
    t0 = time.time()
    m, mats, st, tiles, minfo = E.build(arch, h_xy, refine)
    lay = FL.LAYERS[arch]
    regions = {k: E.region_nodes(m, tiles, *v) for k, v in E.temperature_regions(arch).items()}
    temps = {k: (60.0 if k == "bga" else 85.0) for k in regions}
    if temps0:
        temps.update({k: v for k, v in temps0.items() if k in temps})
    hist, th, L = [], None, None
    wd = E.WD / f"{arch}_{scen}_h{h_xy}{E.refine_tag(refine)}"
    for it in range(E.ET_MAX_ITER):
        L = FL.self_consistent(arch, scen, temps)
        dep = E.deposits_from_ledger(arch, L)
        th = E.solve_thermal(m, mats, st, dep, wd / f"et{it}", tiles, arch=arch)
        Tn = th["T_node"]
        new = {k: float(np.nanmean(Tn[nd - 1])) for k, nd in regions.items()}
        d_t = max(abs(new[k] - temps[k]) for k in temps)
        d_p = (abs(L["P_loss_w"] - hist[-1]["P_loss_w"]) / L["P_loss_w"]) if hist else 1.0
        hist.append({"iter": it, "P_loss_w": L["P_loss_w"], "T_max_C": th["T_max_C"],
                     "T_die_mean_C": E.layer_mean_T(m, Tn, [lay["die"]]),
                     "die_T_max_C": th["die_T_max_C"],
                     **{f"T_{k}_C": v for k, v in new.items()},
                     "max_dT_K": d_t, "dP_rel": d_p,
                     "energy_residual_rel": th["energy_residual_rel"],
                     "wall_s": th["wall_s"]})
        temps = new
        print(f"  {arch} {scen} it{it}: Ploss={L['P_loss_w']:.3f} W Tmax={th['T_max_C']:.2f} "
              f"dT={d_t:.3f} K", flush=True)
        if d_t < E.ET_TOL_K and d_p < E.ET_TOL_P_REL and it > 0:
            break
    return m, mats, st, tiles, minfo, L, th, hist, time.time() - t0, wd, temps


# ------------------------------------------------------------------ MC2: TIM feedback
class TimGap:
    """Per-face extra TIM thickness from a solved displacement field."""

    def __init__(self):
        self.faces = None
        self.g_m = None
        self.k = None
        self.stats = {}

    def load(self, m, frd, k_tim):
        import production_et as PE
        disp = PE.ccxio.read_frd(frd)["DISP"]
        if disp.shape[0] < m.n_nodes + 1:
            raise RuntimeError(f"{frd} has {disp.shape[0] - 1} nodes, mesh {m.n_nodes}")
        top = PE.ccxio.top_film_faces(m)
        uz = np.array([float(np.mean(disp[m.elems[int(e) - 1][4:], 2])) for e in top])
        g_mm = uz.max() - uz
        a = np.array([PE.ccxio.face_area(m, e) for e in top])
        self.faces, self.g_m, self.k = top, g_mm * 1e-3, float(k_tim)
        self.stats = {"source_frd": str(frd), "k_tim_W_mK": self.k,
                      "gap_pv_um": float(g_mm.max() * 1e3),
                      "gap_mean_um": float(np.sum(g_mm * a) / a.sum() * 1e3),
                      "R_tim_nominal_m2K_W": 50e-6 / self.k,
                      "R_extra_mean_m2K_W": float(np.sum(self.g_m * a) / a.sum() / self.k)}
        return self.stats

    def __call__(self, m, top, h_face):
        if self.faces is None or len(top) != len(self.faces) or np.any(top != self.faces):
            raise RuntimeError("top film faces differ from the gap map's faces")
        h = 1.0 / (1.0 / np.asarray(h_face, float) + self.g_m / self.k)
        self.stats["h_eff_over_h_min"] = float((h / h_face).min())
        self.stats["h_eff_over_h_mean"] = float((h / h_face).mean())
        return h


def _tim_k(st):
    c = st["materials"]["tim"]
    k = c.get("k")
    return float(k["value"] if isinstance(k, dict) else k)


def run_feedback(arch, tier):
    _long_ccx()
    apply_tier(arch, tier)
    E._raise_stack_limit()
    base = json.loads(base_case(arch, tier).read_text())
    holder = {}

    def hook_k(m, st, tiles):
        holder["k"] = _tim_k(st)
        return {"tim_k_W_mK": holder["k"]}
    E.BUILD_HOOKS.append(hook_k)
    gap = TimGap()
    E.TOP_FILM_HOOK = gap
    h, r = E.PRODUCTION_H_XY, E.PRODUCTION_REFINE
    m0, _, _, _, _ = E.build(arch, h, r)
    # the first map comes from the tier's converged case; check it IS that field
    fld = base_field(arch, tier)
    import production_et as PE
    tn = PE.ccxio.read_frd(fld / "thermal_converged.frd")["NDTEMP"][1:m0.n_nodes + 1, 0]
    if abs(float(np.nanmax(tn)) - base["thermal"]["T_max_C"]) > 1e-3:
        raise RuntimeError(f"{fld} is not the converged field of {base_case(arch, tier).name}")
    prev_frd = fld / "structural.frd"
    prev = {"P_loss_w": base["P_loss_w"],
            "die_warpage_pv_um": base["mechanics"]["die_warpage_pv_um"]}
    tag = f"tim_warp_fb_{tier}"
    OUT.mkdir(parents=True, exist_ok=True)
    iters = []
    temps0 = {k[2:-2]: v for k, v in base["et_history"][-1].items()
              if k.startswith("T_") and k.endswith("_C") and k not in ("T_max_C",
                                                                       "T_die_mean_C")}
    for it in range(1, FB_MAX_ITER + 1):
        st_gap = gap.load(m0, prev_frd, holder["k"])
        E.WD = scratch("fc_fb", f"{arch}_{tier}", f"it{it}")
        t0 = time.time()
        m, mats, st, tiles, minfo, L, th, hist, t_et, wd, temps0 = run_et_seeded(
            arch, SCEN, h, r, temps0)
        if m.n_nodes != m0.n_nodes:
            raise RuntimeError("mesh changed between the gap map and the solve")
        rec = {"iter": it, "gap": dict(st_gap), "et_history": hist, "et_wall_s": t_et,
               "ledger_rows": L["rows"], "P_loss_w": L["P_loss_w"],
               "thermal": {k: v for k, v in th.items() if k != "T_node"},
               "die_T_max_C": th["die_T_max_C"], "die_T_mean_C": th["die_T_mean_C"]}
        (OUT / f"etm_{arch}_{SCEN}__{tag}_it{it}.json").write_text(
            json.dumps(rec, indent=1, default=float))
        mech = E.mechanics(m, mats, st, th["T_node"], wd, arch, tiles,
                           E.PRODUCTION_SOLVER, 2)
        rec["gap"] = dict(gap.stats)
        rec["mechanics"] = mech
        rec["summary"] = _summary(m, L, th, hist, mech)
        rec["wall_s"] = time.time() - t0
        (OUT / f"etm_{arch}_{SCEN}__{tag}_it{it}.json").write_text(
            json.dumps(rec, indent=1, default=float))
        iters.append(rec)
        dw = abs(mech["die_warpage_pv_um"] - prev["die_warpage_pv_um"]) \
            / prev["die_warpage_pv_um"]
        dp = abs(L["P_loss_w"] - prev["P_loss_w"])
        print(f"{arch} {tier} feedback it{it}: P={L['P_loss_w']:.3f} W "
              f"warp={mech['die_warpage_pv_um']:.3f} um dwarp={dw:.4f} dP={dp:.4f} W",
              flush=True)
        prev = {"P_loss_w": L["P_loss_w"], "die_warpage_pv_um": mech["die_warpage_pv_um"]}
        prev_frd = wd / "structural.frd"
        if dw < FB_TOL_WARP and dp < FB_TOL_P_W:
            break
    last = iters[-1]
    seq_w = [base["mechanics"]["die_warpage_pv_um"]] + [x["summary"]["die_warpage_pv_um"]
                                                        for x in iters]
    seq_p = [base["P_loss_w"]] + [x["summary"]["P_loss_w"] for x in iters]

    def aitken(x):
        if len(x) < 3:
            return None
        a, b, c = x[-3:]
        d = (c - b) - (b - a)
        return c if abs(d) < 1e-12 else c - (c - b) ** 2 / d
    res = {"arch": arch, "scenario": SCEN, "tier": tier,
           "h_xy_mm": h, "refine": list(r),
           "variant": {"name": tag, "kind": "full",
                       "gates": ["coupling.mech_to_thermal"],
                       "nature": "bounding feedback (TIM follows the free warpage)",
                       "what": "top-TIM bond line follows the die warpage; E-T + "
                               "mechanics iterated to convergence"},
           "base_case": base_case(arch, tier).name,
           "base": {"P_loss_w": base["P_loss_w"], "T_max_C": base["thermal"]["T_max_C"],
                    "die_warpage_pv_um": base["mechanics"]["die_warpage_pv_um"],
                    "du_c_um": base["mechanics"]["joint_search"]["critical"]["du_um"],
                    "T_joint_C": base["mechanics"]["joint_search"]["critical"]["T_C"]},
           "iterations": [{"iter": x["iter"], "gap": x["gap"], **x["summary"]}
                          for x in iters],
           "converged": bool(dw < FB_TOL_WARP and dp < FB_TOL_P_W),
           "aitken": {"die_warpage_pv_um": aitken(seq_w), "P_loss_w": aitken(seq_p)},
           "ledger_rows": last["ledger_rows"], "P_loss_w": last["P_loss_w"],
           "thermal": last["thermal"], "et_history": last["et_history"],
           "die_T_max_C": last["thermal"]["die_T_max_C"],
           "die_T_mean_C": last["thermal"]["die_T_mean_C"],
           "mechanics": last["mechanics"]}
    S.case_file(arch, tag).write_text(json.dumps(res, indent=1, default=float))
    return res


# ------------------------------------------------------------------ MC10: die power map
def v_die_hotspot():
    orig_dep, orig_reg = E.deposits_from_ledger, E._region_elems
    info = {}

    def dep(arch, L):
        d = orig_dep(arch, L)
        key = ((FL.LAYERS[arch]["die"],), False)
        w = d.pop(key)
        rest = w - FL.P_LOAD_W
        if rest > 1e-12:
            d[key] = rest
        d[(key[0], "hot")] = HOT_POWER * FL.P_LOAD_W
        d[(key[0], "cool")] = (1.0 - HOT_POWER) * FL.P_LOAD_W
        return d

    def reg(m, layers, in_tiles, tiles):
        if in_tiles not in ("hot", "cool"):
            return orig_reg(m, layers, in_tiles, tiles)
        ids = orig_reg(m, layers, False, tiles)
        xy = m.nodes[np.unique(m.elems[ids - 1].ravel()) - 1][:, :2]
        cx, cy = 0.5 * (xy[:, 0].max() + xy[:, 0].min()), 0.5 * (xy[:, 1].max() + xy[:, 1].min())
        half = 0.5 * min(np.ptp(xy[:, 0]), np.ptp(xy[:, 1]))
        a = half * np.sqrt(HOT_AREA)
        cen = m.elem_centroids()[ids - 1]
        inside = (np.abs(cen[:, 0] - cx) <= a) & (np.abs(cen[:, 1] - cy) <= a)
        V = m.elem_volumes()[ids - 1]
        f = float(V[inside].sum() / V.sum())
        info.update({"die_half_mm": float(half), "hot_half_mm": float(a),
                     "hot_area_fraction_realized": f,
                     "flux_ratio_realized": (HOT_POWER / f) / ((1 - HOT_POWER) / (1 - f))})
        return ids[inside] if in_tiles == "hot" else ids[~inside]
    E.deposits_from_ledger = dep
    E._region_elems = reg

    def hook(m, st, tiles):
        return {"die_power_map": f"{HOT_POWER:.0%} of the die load in the central "
                                 f"{HOT_AREA:.0%} of the die area"}
    E.BUILD_HOOKS.append(hook)
    return info


def _register():
    S.VARIANTS["die_hotspot_A"] = dict(
        kind="full", archs=("Z1", "Z2"), apply=v_die_hotspot,
        gates=["load.die_power_map"], nature="declared alternative load map",
        what="75 % of the die load in the central half of the die area (cooling A)")
    S.VARIANTS["die_hotspot_B"] = dict(
        kind="full", archs=("Z1", "Z2", "Z3"), apply=None,
        gates=["load.die_power_map"], nature="declared alternative load map",
        what="75 % of the die load in the central half of the die area (cooling B)")


def run_hotspot(arch, tier):
    _long_ccx()
    _register()
    name = f"die_hotspot_{tier}"

    def apply():
        apply_tier(arch, tier)
        v_die_hotspot()
    S.VARIANTS[name]["apply"] = apply
    S.VARIANTS[name]["archs"] = (arch,)
    return S.run_full(arch, name)


# ------------------------------------------------------------------ die power map (realistic)
#: DECLARED realistic non-uniform die load (TCPMT revision): mm-scale hot spots at a fixed
#: flux contrast over a uniform background, the same 1 kW. Eight 1.5-mm square core hot spots
#: in a 4 x 2 array (centres x = +/-2.2, +/-6.5 mm; y = +/-3.5 mm; x is the coolant flow
#: direction) at 8 x the background flux: nominal hot area 3.6 % of the 500-mm^2 die,
#: background 160 W/cm^2, hot spots 1.28 kW/cm^2, 23 % of the load in the hot spots -- the
#: magnitudes reported for on-chip hot spots (sub-mm to ~2 mm at 5-10 x the background
#: flux). The contrast is held exactly on the mesh (the power split follows the realized
#: hot volume). The 3:1 core/periphery map (v_die_hotspot) stays a separate variant.
HOTMAP = {"side_mm": 1.5, "contrast": 8.0,
          "centres_mm": [(x, y) for y in (-3.5, 3.5) for x in (-6.5, -2.2, 2.2, 6.5)]}


def v_die_hotmap(spec=None):
    spec = dict(HOTMAP, **(spec or {}))
    orig_dep, orig_reg = E.deposits_from_ledger, E._region_elems
    info = {"spec": spec}

    def split(m, layers, tiles):
        ids = orig_reg(m, layers, False, tiles)
        cen = m.elem_centroids()[ids - 1]
        h = 0.5 * spec["side_mm"]
        hot = np.zeros(len(ids), bool)
        for cx, cy in spec["centres_mm"]:
            sel = (np.abs(cen[:, 0] - cx) <= h) & (np.abs(cen[:, 1] - cy) <= h)
            if not sel.any():
                raise RuntimeError(f"hot spot at ({cx}, {cy}) captures no die element")
            hot |= sel
        V = m.elem_volumes()[ids - 1]
        return ids, hot, float(V[hot].sum()), float(V[~hot].sum())

    state = {}

    def dep(arch, L):
        d = orig_dep(arch, L)
        key = ((FL.LAYERS[arch]["die"],), False)
        w = d.pop(key)
        rest = w - FL.P_LOAD_W
        if rest > 1e-12:
            d[key] = rest
        c = spec["contrast"]
        vh, vb = state["vh"], state["vb"]
        p_hot = FL.P_LOAD_W * c * vh / (c * vh + vb)
        d[(key[0], "hotmap_hot")] = p_hot
        d[(key[0], "hotmap_bg")] = FL.P_LOAD_W - p_hot
        info.update({"P_hot_W": p_hot, "hot_power_fraction": p_hot / FL.P_LOAD_W,
                     "hot_volume_fraction_realized": vh / (vh + vb),
                     "flux_hot_W_cm2": p_hot / (vh / state["t_die"]) * 100.0,
                     "flux_bg_W_cm2": (FL.P_LOAD_W - p_hot) / (vb / state["t_die"]) * 100.0})
        return d

    def reg(m, layers, in_tiles, tiles):
        if in_tiles not in ("hotmap_hot", "hotmap_bg"):
            return orig_reg(m, layers, in_tiles, tiles)
        ids, hot, _vh, _vb = split(m, layers, tiles)
        return ids[hot] if in_tiles == "hotmap_hot" else ids[~hot]

    def hook(m, st, tiles):
        die = [L for L in m.layers if L.name == "die"][0]
        ids, hot, vh, vb = split(m, ("die",), tiles)
        state.update(vh=vh, vb=vb, t_die=die.z1 - die.z0)
        return {"die_power_map": f"{len(spec['centres_mm'])} hot spots of {spec['side_mm']} mm "
                                 f"at {spec['contrast']:g} x the background flux (1 kW total)",
                "die_hot_elements": int(hot.sum())}
    E.deposits_from_ledger = dep
    E._region_elems = reg
    E.BUILD_HOOKS.append(hook)
    return info


def run_hotmap(arch, tier):
    _long_ccx()
    name = f"die_hotmap_{tier}"
    S.VARIANTS[name] = dict(
        kind="full", archs=(arch,), apply=None, gates=["load.die_power_map"],
        nature="declared realistic load map (mm-scale hot spots)",
        what=f"8 x 1.5-mm die hot spots at 8 x the background flux, 1 kW (cooling {tier})")

    def apply():
        apply_tier(arch, tier)
        return v_die_hotmap()
    S.VARIANTS[name]["apply"] = apply
    return S.run_full(arch, name)


# ------------------------------------------------------------------ cooling model form
def v_plate_local_h():
    """SUPERSEDED: the caloric correction is PRODUCTION (final_closure_physical_etm.
    TOP_PLATE_COEFF = "local"). Kept only so an old call cannot correct twice: it checks the
    production setting and changes nothing."""
    if E.TOP_PLATE_COEFF != "local":
        raise RuntimeError("plate_local_h asked while the top plate is not on the local "
                           "coefficient")
    return {"h_factor": 1.0, "note": "production already uses the local coefficient"}


def run_caloric(arch, tier):
    """The superseded top-plate coefficient (uniform-sink h with the streamwise sink, i.e. the
    caloric double count) as a variant of the tier's case."""
    _long_ccx()
    name = f"plate_caloric_legacy_{tier}"
    S.VARIANTS[name] = dict(
        kind="full", archs=(arch,), apply=None, gates=["therm.cooling_model_form"],
        nature="LEGACY_SETTING (caloric double count)",
        what="top-plate coefficient WITH the caloric resistance on the streamwise sink "
             f"(the pre-revision production form), cooling {tier}")

    def apply():
        apply_tier(arch, tier)
        return S.v_cooling_model(top="uniform_legacy")
    S.VARIANTS[name]["apply"] = apply
    return S.run_full(arch, name)


# ------------------------------------------------------------------ implemented decoupling
def run_sdec(arch, tier):
    """The physically implemented input decoupling (tcpmt_decap_framework: 7 interleaved
    clock phases + a ring of 56 x 1206 100-V capacitors) for any architecture and tier: the
    package 48-V network (Z1 only) at k_eq, the cell-internal VIN->HS runs at the bare-pulse
    k_open (the hot loop, common to every integration), ring ESR as a ledger row (Z1)."""
    import tcpmt_decap_framework as DF
    _long_ccx()
    rk = DF.recommended_k()
    DF._register(rk["k_eq"], DF.k_open(), rk["P_ring_esr_W"])
    name = f"sdec_{tier}"
    S.VARIANTS[name] = dict(
        kind="full", archs=(arch,), apply=None, gates=["decap.implemented"],
        nature="PHYSICAL_DESIGN (implemented input decoupling, hot loop)",
        what=f"implemented decoupling: k_eq = {rk['k_eq']:.3f}, cell-internal VIN runs at "
             f"k_open = {DF.k_open():.3f} (cooling {tier})")

    def apply():
        apply_tier(arch, tier)
    S.VARIANTS[name]["apply"] = apply
    S.SCEN = DF.SCEN_KEY
    S.case_file = lambda a, v, scen=DF.SCEN_KEY: S.OUT / f"etm_{a}_{scen}__{v}.json"
    return S.run_full(arch, name)


# ------------------------------------------------------------------ rated flying capacitors
CF_RATED_UM = 830.0          # 0603 MLCC (0.8 mm nominal) + its attach (decap agent, flying_caps.json)
CF_RATED_ESR_MOHM = 7.3      # mean of C1 (7.8) and C2 (6.8) at 805 kHz, datasheet R(f)


def v_z1_rated_cf(order="rep", cf_um=None, esr_mohm=None):
    """Z1 with flying capacitors of a rated part (GRM188D71H105KE01, 0603, 1 uF, 50 V, X7T):
    the tier grows from the 100-um assumption to 830 um and the capacitor ESR from 2.5 to
    7.3 mOhm; order 'ref' also swaps LS and C_f (the reference order)."""
    import yaml
    import physical_package as PP
    from dataclasses import replace
    sys.path.insert(0, str(R / "scripts" / "phase0nw"))
    import z1_package as Z1P
    cfg = yaml.safe_load(Z1P.Z1_CFG.read_text())
    t = cfg["converter"]["tiers_from_substrate_upward"]
    names = [x["name"] for x in t]
    i_cf = names.index("flying_caps")
    cf_um = CF_RATED_UM if cf_um is None else float(cf_um)
    esr_mohm = CF_RATED_ESR_MOHM if esr_mohm is None else float(esr_mohm)
    dz = cf_um - float(t[i_cf]["um"])
    t[i_cf]["um"] = cf_um
    t[i_cf]["status"] = "RATED_PART"
    cfg["converter"]["total_um"] = float(cfg["converter"]["total_um"]) + dz
    ex = cfg["expected"]
    ex["package_top_um"] = float(ex["package_top_um"]) + dz
    if "converter_span_um" in ex:
        ex["converter_span_um"] = [float(ex["converter_span_um"][0]),
                                   float(ex["converter_span_um"][1]) + dz]
    i_ls = names.index("gan_ls_EPC2057")
    if order == "ref":
        t[i_ls], t[i_cf] = t[i_cf], t[i_ls]
    tmp = scratch("fc_sens", f"z1_rated_cf_{order}_{cf_um:.0f}") / f"z1_physical_rated_cf_{order}.yaml"
    tmp.write_text(yaml.safe_dump(cfg, sort_keys=False))
    load = PP.load_z1_package_config
    PP.load_z1_package_config = lambda path=None: load(path or tmp)
    Z1P.Z1_CFG = tmp
    Z1P.Z1_TIERS = tuple((x["name"], float(x["um"])) for x in t)
    Z1P.Z1_CONV_UM = sum(u for _n, u in Z1P.Z1_TIERS)
    tiers = [(next((c for key, c in FL._TIER_CLASS if x["name"].startswith(key)), "rdl"),
              float(x["um"])) for x in t]
    ct = FL.cell_tiers
    FL.cell_tiers = lambda arch: list(tiers) if arch == "Z1" else ct(arch)
    if order == "ref":
        lay = dict(FL.LAYERS["Z1"])
        lay["ls"] = f"z1conv_{i_cf}_gan_ls_EPC2057"
        lay["caps"] = f"z1conv_{i_ls}_flying_caps"
        FL.LAYERS["Z1"] = lay
    import replay_production as RPX
    d = RPX.compiled_design()
    RPX._DESIGN_CACHE["d"] = replace(d, capacitor=replace(d.capacitor, esr_mohm=esr_mohm))

    def hook(m, st, tiles):
        """The rated 0603 MLCC tier carries its own derived card (case A1), at this height."""
        import tcpmt_converter_cards as CC
        c = CC.cards_for(CC.TierContents.from_design(), cfly_a1_um=cf_um,
                         strict=False)["conv_cfly_a1"]
        st["materials"]["conv_cfly_a1"] = json.loads(json.dumps(c))
        mat = np.array(m.elem_material, dtype=object)
        lay = np.array(m.elem_layer, dtype=object)
        sel = (lay == FL.LAYERS["Z1"]["caps"]) & (mat == "conv_cfly_a0")
        if not sel.any():
            raise RuntimeError("A1: no flying-capacitor element carries the A0 card")
        mat[sel] = "conv_cfly_a1"
        m.elem_material = mat
        return {"cfly_card": "conv_cfly_a1", "cfly_a1_elements": int(sel.sum()),
                "cfly_a1_k_ortho": c["k_ortho"]["value"]}
    E.BUILD_HOOKS.append(hook)
    return {"cf_um": cf_um, "dz_um": dz, "esr_mohm": esr_mohm, "order": order}


def run_ratedcf(tier, order="rep", cf_um=None, esr_mohm=None, tag="cf"):
    """Case A1 (rated commercial MLCC). tag 'cf': nominal part height (830 um, ESR 7.3 mOhm,
    mean of C1/C2); tag 'cfmax': the documented MAXIMUM part height 1.0 mm + 30-um mounting
    (1030 um) and the corrected synthesis's ESR at 32 V (7.8 mOhm, Murata data)."""
    _long_ccx()
    cf = CF_RATED_UM if cf_um is None else cf_um
    esr = CF_RATED_ESR_MOHM if esr_mohm is None else esr_mohm
    name = f"z1_rated_{tag}_{order}_{tier}"
    S.VARIANTS[name] = dict(
        kind="full", archs=("Z1",), apply=None, gates=["geom.flying_cap_rated"],
        nature="PHYSICAL_DESIGN (case A1: rated flying capacitors)",
        what=f"flying-cap tier {cf:.0f} um (rated 0603 MLCC), ESR {esr} mOhm, "
             f"{'reference' if order == 'ref' else 'repartitioned'} order, cooling {tier}")

    def apply():
        apply_tier("Z1", tier)
        v_z1_rated_cf(order, cf, esr)
    S.VARIANTS[name]["apply"] = apply
    return S.run_full("Z1", name)

if __name__ == "__main__":
    mode, arch, tier = sys.argv[1], sys.argv[2], sys.argv[3]
    if (arch, tier) not in TIER_BASE:
        raise SystemExit(f"unknown case {arch} {tier}")
    if mode == "feedback":
        r = run_feedback(arch, tier)
        print(json.dumps(r["iterations"], indent=1, default=float))
    elif mode == "hotspot":
        print(run_hotspot(arch, tier))
    elif mode == "hotmap":
        print(run_hotmap(arch, tier))
    elif mode == "caloric":
        print(run_caloric(arch, tier))
    elif mode == "sdec":
        print(run_sdec(arch, tier))
    elif mode in ("ratedcf", "ratedcfref"):
        print(run_ratedcf(tier, "ref" if mode == "ratedcfref" else "rep"))
    elif mode in ("ratedcfmax", "ratedcfmaxref"):
        print(run_ratedcf(tier, "ref" if mode == "ratedcfmaxref" else "rep", 1030.0, 7.8,
                          "cfmax"))
    else:
        raise SystemExit("mode is feedback or hotspot")
