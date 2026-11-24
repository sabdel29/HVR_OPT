"""Joint response of every mechanical robustness variant: a screen at the reference case's
worst sites, validated by full dominance-bounded searches.

The robustness map judged its joint column on the largest ball displacement (du), the proxy
the critical-joint search disproved (tcpmt_mech_critical: the response is not monotone in
(|du_xy|, T)). Here every variant with a structural solution gets a joint response with the
production local model (tcpmt_mech_submodel: full cut-boundary kinematics of both pad faces,
ramped loads, the production law at its converged window):

  variants  the robustness map's variants on the ideal-decoupling reference (S0) under cooling
            A (final_closure_sensitivity NAME, Z1 / Z2, full and mechanics-only) and B
            (NAME@B, mechanics only), the newer decisions of the production state
            (tcpmt_review_variants: die power map, plate-interface feedback), the encapsulant
            classes and the local-card BGA layer on the production fields under A and B, and
            board size, mounting and clamp on the production fields (tcpmt_mech_board state:
            screws, pinned screws, edge, the clamp at the screws and on a backplate, the 3x
            board with a hot or cold ring, on screws and clamped);
  lattice   the full cut-boundary kinematics of every BGA lattice site of each variant,
            recomputed with the search's own code (tcpmt_mech_kinematics.site_kinematics) from
            the variant's converged structural field (its scratch work tree) on its own mesh
            (the variant applied before the mesh build) and the thermal field it was solved
            with; the recomputed sites must reproduce the candidates the variant stored
            (LATTICE_TOL_MM), so the record is the variant's;
  screen    each variant solved at the K worst sites of its reference case (the K largest
            responses of the reference's dominance-bounded search under the production law:
            solder_critical_v2.json for the production state, solder_critical_v2_S0.json for
            the S0 reference); its joint response is the maximum over those K sites. A clamp
            is held through the cycle: the cold half-cycle is the clamp-only state at the
            same site (tcpmt_mech_board: clamp_only, clamp_backplate_only,
            clamp_screws_ring_only);
  validate  the full dominance-bounded search of tcpmt_mech_critical on the variant's own
            lattice for a few variants of different kinds: is the variant's worst site inside
            the reference's top K?
  summarize -> tcpmt_revision/robustness_joint.json: per variant its screened response, site
            and rank among the K, the change against its reference, the orderings of the
            integrations under THE rule (|D + beta| > U95(D); U95 from each joint's own
            numerical U of the local model -- the production joints' L0 -> L3 and 4 -> 8 cycle
            changes, transferred provisionally to the reference state; beta = 0; a variant on
            another mesh than its reference is pending, as in the map), and the validation.

    python tcpmt_mech_joint_screen.py list
    python tcpmt_mech_joint_screen.py lattice [KEY ...]     (FC_POOL_MAX workers)
    python tcpmt_mech_joint_screen.py run [KEY ...]         (TCPMT_SOLDER_SLOTS x LOCAL_THREADS)
    python tcpmt_mech_joint_screen.py validate [KEY ...]
    python tcpmt_mech_joint_screen.py summarize
"""
from __future__ import annotations

import itertools
import json
import math
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts", "scripts/phase0nw"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
import tcpmt_mech_laws as LAW                                       # noqa: E402
import tcpmt_mech_production as MP                                  # noqa: E402

ROOT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research")   # campaign hook
TR = ROOT / "tcpmt_revision"
SENS = ROOT / "final_closure" / "sensitivity"
BOARD = TR / "board_study"
LAT = TR / "site_kinematics" / "variants"
OUT = TR / "robustness_joint.json"
K = int(os.environ.get("TCPMT_SCREEN_K", "20"))
STUDY = "joint_screen"
LATTICE_TOL_MM = 1e-8
#: the reference state's critical-joint search per state
CRIT = {"SDEC": TR / "solder_critical_v2.json", "S0": TR / "solder_critical_v2_S0.json"}
#: S0 cases that are references or bases themselves, or of the Z3 land side (not mapped)
S0_SKIP = ("z1_bottom_plate_tim", "z3_land_")
#: S0 cooling-A decisions whose integration is cooled from below: screened at the cooling-B
#: reference's worst sites (z2_cooled_tim IS the cooling-B reference of Z2)
S0_REF_TIER = {"z2_cooled": "B", "z2_cooled_tim": "B"}
#: board study solves judged as variants -> the clamp-only state of their cold half-cycle
BOARD_SOLVES = {"screws": None, "screws_pinned": None, "edge": None,
                "clamp_screws": ("main", "clamp_only"),
                "clamp_backplate": ("cold", "clamp_backplate_only"),
                "free_ring_hot": None, "free_ring_cold": None, "screws_ring_hot": None,
                "clamp_screws_ring_hot": ("cold", "clamp_screws_ring_only")}
LARGE = ("free_ring_hot", "free_ring_cold", "screws_ring_hot", "clamp_screws_ring_hot",
         "clamp_screws_ring_only")
#: the integrations each group compares (the map's reference-state groups: Z1 against Z2 under
#: cooling A; the cooling-B and production-state groups: all three)
GROUP_ARCHS = {"S0_A": ("Z1", "Z2")}
#: the full searches that validate the screen: one variant of each kind (mounting,
#: encapsulant class, class-B mechanical card, thermal card)
VALIDATE = ("SDEC_A_Z2__board_screws_pinned", "SDEC_A_Z1__encap_emc_lowcte",
            "S0_A_Z2__conv_E160_a10", "S0_A_Z2__conv_k_tenth")


def production_law():
    return LAW.solder_cfg()["production_law"]


# ------------------------------------------------------------------ the variants
def _spec(key, group, arch, tier, ref, name, source, **kw):
    return dict(key=key, group=group, arch=arch, tier=tier, ref=ref, name=name, source=source,
                **kw)


def variants(include_cold=False):
    """Every judged variant (and, with include_cold, the clamp-only states their clamps
    need), as specs."""
    out = []
    for f in sorted(SENS.glob("etm_Z[123]_HV_S0__*.json")):
        arch, name = f.stem[4:6], f.stem.split("__", 1)[1]
        if any(name.startswith(s) for s in S0_SKIP):
            continue
        if name.endswith("__B"):
            v = name[:-3]
            out.append(_spec(f"S0_B_{arch}__{v}", "S0_B", arch, "B", f"S0_B_{arch}", v,
                             "sens", case_file=str(f), scen="HV_S0", variant=f"{v}@B"))
        elif arch in ("Z1", "Z2"):
            t = S0_REF_TIER.get(name, "A")
            out.append(_spec(f"S0_A_{arch}__{name}", "S0_A", arch, "A", f"S0_{t}_{arch}", name,
                             "sens", case_file=str(f), scen="HV_S0", variant=name))
    for f in sorted(SENS.glob("etm_Z[123]_HV_SDEC__*.json")):
        arch, name = f.stem[4:6], f.stem.split("__", 1)[1]
        tier = "B" if name.endswith("__B") else "A"
        v = name[:-3] if name.endswith("__B") else name
        if v.startswith(("sdec_", "plate_caloric")):
            continue                              # the cases themselves; a thermal-only form
        if v.startswith(("die_hotspot_", "tim_warp_fb_")):
            tier = v[-1]
            out.append(_spec(f"SDEC_{tier}_{arch}__{v}", f"SDEC_new_{tier}", arch, tier,
                             f"SDEC_{tier}_{arch}", v, "review", case_file=str(f),
                             scen="HV_SDEC", variant=v))
        else:
            out.append(_spec(f"SDEC_{tier}_{arch}__{v}", f"SDEC_mech_{tier}", arch, tier,
                             f"SDEC_{tier}_{arch}", v, "sens", case_file=str(f),
                             scen="HV_SDEC", variant=v + ("@B" if tier == "B" else "")))
    for f in sorted(BOARD.glob("SDEC_?_Z?.json")):
        st, tier, arch = f.stem.split("_")
        ref = f"SDEC_{tier}_{arch}"
        for name, cold in BOARD_SOLVES.items():
            ck = None
            if cold:
                ck = f"{ref}__board_{cold[1]}"
            out.append(_spec(f"{ref}__board_{name}", f"board_{tier}", arch, tier, ref, name,
                             "board", board_file=str(f), cold_key=ck))
        if include_cold:
            out.append(_spec(f"{ref}__board_clamp_only", "cold", arch, tier, ref,
                             "clamp_only", "board", board_file=str(f)))
            fc = BOARD / f"{f.stem}_cold.json"
            for name in ("clamp_backplate_only", "clamp_screws_ring_only"):
                out.append(_spec(f"{ref}__board_{name}", "cold", arch, tier, ref, name,
                                 "board", board_file=str(fc)))
    return out


def spec_of(key):
    return next((s for s in variants(True) if s["key"] == key), None)


# ------------------------------------------------------------------ lattice of a variant
def lat_path(key):
    return LAT / f"{key}.json"


def _scratch(*parts):
    from hvr_scratch import path as scratch
    return scratch(*parts)


def _bga_layer(a):
    cfg = LAW.cfg()
    ent = next(e for e in cfg["interconnects"][a] if e["sites"] == "bga_lattice")
    half = 0.5 * float(cfg["geometries"][ent["geometry"]]["pad"]) / 1e3
    return ent["layer"], half, int(cfg["local"].get("pad_fit_samples", 5))


def _field_and_mesh(s):
    """(mesh, U, Tn, stored candidates, provenance) of one variant in this (forked) process."""
    import numpy as np
    import final_closure_physical_etm as E
    import final_closure_sensitivity as S
    import production_et as PE
    import tcpmt_cases as TC
    import tcpmt_mech_kinematics as KIN
    a, t = s["arch"], s["tier"]
    E._raise_stack_limit()
    h, r = E.PRODUCTION_H_XY, E.PRODUCTION_REFINE
    prov = {}
    if s["source"] in ("sens", "review"):
        c = json.loads(Path(s["case_file"]).read_text())
        kind = (c.get("variant") or {}).get("kind")
        if s["scen"] == "HV_SDEC":
            S.set_state("SDEC")
        if s["source"] == "review":
            import tcpmt_review_variants as RV
            RV.set_scenario(s["scen"])
            RV.apply_tier(a, t)
            if s["name"].startswith("die_hotspot_"):
                RV.v_die_hotspot()
        elif kind == "mech":
            S.VARIANTS[s["name"]]["apply"]()
        else:
            S.VARIANTS[s["name"]]["apply"]()
        m = E.build(a, h, r)[0]
        if kind == "mech":
            base, tfrd, bname = S.thermal_base(a, t)
            pre = f"{s['scen']}_" if s["scen"] == "HV_SDEC" else ""
            sfrd = _scratch("fc_sens", pre + s["variant"].replace("@", "_"), a) / "structural.frd"
            prov.update(thermal_from=bname)
        else:
            cf = TC.converged_field(Path(s["case_file"]), c)
            if not cf or not cf.get("structural"):
                raise RuntimeError(f"{s['key']}: no converged structural field on disk")
            tfrd, sfrd = Path(cf["thermal"]), Path(cf["structural"])
        tn = PE.ccxio.read_frd(tfrd)["NDTEMP"][1:m.n_nodes + 1, 0]
        if kind != "mech" and abs(float(np.nanmax(tn)) - c["thermal"]["T_max_C"]) > 1e-3:
            raise RuntimeError(f"{s['key']}: {tfrd} is not the variant's converged field")
        stored = KIN.expand_sites(c["mechanics"]["interconnects"]["bga"]["candidates"])
        prov.update(case_file=MP.rel(s["case_file"]), kind=kind,
                    mesh=list(MP_mesh_sig(c)), inputs=[s["case_file"], str(tfrd), str(sfrd)])
    else:
        import tcpmt_mech_board as MB
        rec = json.loads(Path(s["board_file"]).read_text())
        me = (rec.get("mechanics") or {}).get(s["name"])
        if not me or "error" in me:
            raise RuntimeError(f"{s['key']}: no solve {s['name']} in {s['board_file']}")
        S.set_state("SDEC")
        base, tfrd, bname = S.thermal_base(a, t)
        m0, _mats, st, _tiles, _ = E.build(a, h, r)
        tn = PE.ccxio.read_frd(tfrd)["NDTEMP"][1:m0.n_nodes + 1, 0]
        if abs(float(np.nanmax(tn)) - base["thermal"]["T_max_C"]) > 1e-6:
            raise RuntimeError(f"{tfrd} is not the converged field of {bname}")
        m = m0
        if s["name"] in LARGE:
            os.environ["HVR_BOARD_EXTENT_FACTOR"] = f"{float(rec['board_extent_factor']):g}"
            os.environ["HVR_BOARD_FAR_H_MM"] = f"{float(MB.bcfg()['far_field_h_max_mm']):g}"
            try:
                m = E.build(a, h, r)[0]
            finally:
                os.environ.pop("HVR_BOARD_EXTENT_FACTOR", None)
                os.environ.pop("HVR_BOARD_FAR_H_MM", None)
            lx = st["geometry"]["power_substrate"]["size_x"]["value"]
            ly = st["geometry"]["power_substrate"]["size_y"]["value"]
            ring = "cold" if s["name"] == "free_ring_cold" else "hot"
            tn, _n = MB.map_field_to_large(m0, tn, m, lx, ly,
                                           st["structural_bc"]["t_ref"]["value"], ring)
        sfrd = _scratch("mech_board", f"SDEC_{t}_{a}", s["name"]) / "structural.frd"
        stored = KIN.expand_sites(me["interconnects"]["bga"]["candidates"])
        prov.update(board_file=MP.rel(s["board_file"]), thermal_from=bname,
                    mesh=[m.n_elems, m.n_nodes],
                    inputs=[s["board_file"], str(tfrd), str(sfrd)])
    xyz = KIN.read_frd_nodes(sfrd)
    # the .frd prints six significant digits: a relative check (the 3x board reaches 45 mm)
    if len(xyz) - 1 != m.n_nodes or np.nanmax(np.abs(xyz[1:] - m.nodes)
                                              / np.maximum(1.0, np.abs(m.nodes))) > 1e-5:
        raise RuntimeError(f"{s['key']}: {sfrd} is not on the rebuilt mesh "
                           f"({len(xyz) - 1} vs {m.n_nodes} nodes)")
    U = PE.ccxio.read_frd(sfrd)["DISP"][:, :3]
    prov.update(structural_frd=str(sfrd), thermal_frd=str(tfrd))
    return m, U, tn, stored, prov


def MP_mesh_sig(c):
    import tcpmt_uncertainty as TU
    return TU.mesh_signature(c) or ()


def _lattice_one(s):
    """Fork-safe worker: the variant's full-lattice kinematics, verified against its stored
    candidates."""
    import pkg_rdl_network as Kn
    import tcpmt_mech_kinematics as KIN
    t0 = time.time()
    try:
        m, U, tn, stored, prov = _field_and_mesh(s)
        a = s["arch"]
        layer, half, nfit = _bga_layer(a)
        cut = Kn.architecture_cutout_mm(a) if a != "Z3" else None
        sites = KIN.layer_sites(m, layer, "bga_lattice", cut)
        kin = KIN.site_kinematics(m, U, tn, layer, sites, half, nfit)
        idx = {(round(k["x_mm"], 6), round(k["y_mm"], 6)): k for k in kin}
        dev, missing = 0.0, []
        for q in stored:
            k = idx.get((round(q["x_mm"], 6), round(q["y_mm"], 6)))
            if k is None:
                missing.append([q["x_mm"], q["y_mm"]])
                continue
            dev = max([dev] + [abs(x - y) for f in ("u_bot_mm", "u_top_mm")
                               for x, y in zip(k[f], q[f])]
                      + [abs(x - y) for f in ("G_bot", "G_top")
                         for rk, rq in zip(k[f], q[f]) for x, y in zip(rk, rq)])
        if missing or dev > LATTICE_TOL_MM:
            raise RuntimeError(f"recomputed lattice does not reproduce the stored candidates "
                               f"(missing {missing[:3]}, max deviation {dev:.2e} mm)")
        rec = {"key": s["key"], "spec": s, "n_sites": len(sites), "n_evaluated": len(kin),
               "layer": layer, "provenance": {k: v for k, v in prov.items() if k != "inputs"},
               "inputs_sha1": MP.inputs_sha1(prov["inputs"]),
               "verification": {"n_stored_candidates": len(stored), "max_deviation_mm": dev,
                                "tolerance_mm": LATTICE_TOL_MM},
               "sites": KIN.compact_sites(kin), "wall_s": time.time() - t0}
        LAT.mkdir(parents=True, exist_ok=True)
        lat_path(s["key"]).write_text(json.dumps(rec, default=float) + "\n")
        return s["key"], None, dev, time.time() - t0
    except Exception as e:                        # recorded, never silent
        return s["key"], str(e)[-400:], None, time.time() - t0


def _fresh_lattice(s):
    f = lat_path(s["key"])
    if not f.is_file():
        return False
    rec = json.loads(f.read_text())
    ins = rec.get("inputs_sha1") or {}
    return bool(ins) and all(Path(p).is_file() and MP.sha1(p) == h for p, h in ins.items())


def _source(s):
    return Path(s["case_file"] if s["source"] in ("sens", "review") else s["board_file"])


def lattice(keys=None, force=False, only_cold=False):
    specs = [s for s in variants(True) if (not keys or s["key"] in keys)
             and (not only_cold or s["group"] == "cold")]
    missing = [s["key"] for s in specs if not _source(s).is_file()]
    specs = [s for s in specs if _source(s).is_file()]
    todo = [s for s in specs if force or not _fresh_lattice(s)]
    print(f"{len(specs)} variants ({len(missing)} without a source record yet), "
          f"{len(todo)} lattices to compute", flush=True)
    errs = {}
    n = max(1, min(len(todo), int(os.environ.get("FC_POOL_MAX", "4"))))
    if todo:
        with mp.get_context("fork").Pool(n, maxtasksperchild=1) as pool:
            for key, err, dev, wall in pool.imap_unordered(_lattice_one, todo):
                print(f"  {key}: " + (f"ERROR {err}" if err else
                                      f"reproduced to {dev:.1e} mm") + f" ({wall:.0f} s)",
                      flush=True)
                if err:
                    errs[key] = err
    f = TR / ("robustness_joint_lattice_cold.json" if only_cold
              else "robustness_joint_lattice.json")
    f.write_text(json.dumps({"n_specs": len(specs), "n_computed": len(todo) - len(errs),
                             "errors": errs, "without_source": missing}, indent=1) + "\n")
    return errs


def load_lattice(key):
    import tcpmt_mech_kinematics as KIN
    f = lat_path(key)
    if not f.is_file():
        return None
    return KIN.expand_sites(json.loads(f.read_text())["sites"])


# ------------------------------------------------------------------ reference worst sites
def _state_of(ref):
    return ref.split("_")[0]


def ref_rows(ref):
    """The reference case's solved sites under the production law, largest response first."""
    f = CRIT[_state_of(ref)]
    if not f.is_file():
        return None
    c = (json.loads(f.read_text()).get("cases") or {}).get(ref) or {}
    rows = [r for r in c.get("candidates") or [] if r.get("d_eps") is not None]
    return sorted(rows, key=lambda r: -r["d_eps"])


def top_k(ref, k=K):
    rows = ref_rows(ref)
    return rows[:k] if rows else None


def _key(x, y):
    return (round(x, 6), round(y, 6))


def tag(key, x, y):
    return f"{key}_x{x:+06.2f}_y{y:+06.2f}"


def _site_map(key):
    lat = load_lattice(key)
    return {_key(k["x_mm"], k["y_mm"]): k for k in lat} if lat else None


def tasks_for(s, sites):
    """Local solves of variant s at sites [(x, y)]."""
    import tcpmt_mech_submodel as SUB          # noqa: F401  (card resolution at solve time)
    sm = _site_map(s["key"])
    cm = _site_map(s["cold_key"]) if s.get("cold_key") else None
    if sm is None or (s.get("cold_key") and cm is None):
        return None
    out = []
    for x, y in sites:
        k = sm.get(_key(x, y))
        if k is None:
            continue
        t = dict(study=STUDY, tag=tag(s["key"], x, y), kin=k, law=production_law(),
                 meta={"variant": s["key"], "ref": s["ref"], "x_mm": x, "y_mm": y})
        if cm is not None:
            t["kin_cold"] = cm[_key(x, y)]
            t["meta"]["cold"] = s["cold_key"]
        out.append(t)
    return out


def run(keys=None, log=None, groups=None, reverse=False):
    import tcpmt_mech_submodel as SUB
    ts, skipped = [], []
    for s in variants():
        if keys and s["key"] not in keys:
            continue
        if groups and s["group"] not in groups:
            continue
        tk = top_k(s["ref"])
        if not tk:
            print(f"  {s['key']}: no reference search for {s['ref']}", flush=True)
            continue
        t = tasks_for(s, [(r["x_mm"], r["y_mm"]) for r in tk])
        if t is None:
            print(f"  {s['key']}: no lattice", flush=True)
            skipped.append(s["key"])
            continue
        ts += t
    print(f"{len(ts)} screen tasks", flush=True)
    if reverse:             # a helper from the other end: solve() skips what the other finished
        ts = ts[::-1]
    recs = SUB.run_tasks(ts)
    if log:
        d = TR / "robustness_joint_runs"
        d.mkdir(parents=True, exist_ok=True)
        ok = sum(1 for t in ts if (recs.get(t["tag"]) or {}).get("d_peeq_per_cycle"))
        (d / f"{log}.json").write_text(json.dumps(
            {"n_tasks": len(ts), "n_solved": ok, "n_failed": len(ts) - ok,
             "variants_without_lattice": skipped, "K": K}, indent=1) + "\n")


# ------------------------------------------------------------------ validation searches
def full_search(key, max_rounds=None):
    """The dominance-bounded search of tcpmt_mech_critical on the variant's own lattice
    (production law): base candidates of the variant's lattice, its Pareto front in the
    screening features, the reference's top K, then every site whose bound exceeds the
    maximum, until none does."""
    import tcpmt_mech_critical as CR
    import tcpmt_mech_kinematics as KIN
    import tcpmt_mech_submodel as SUB
    s = spec_of(key)
    lat = load_lattice(key)
    if s is None or lat is None:
        return {"error": "no spec or lattice"}
    for k in lat:
        k.setdefault("tilt_rel", [k["G_top"][2][0] - k["G_bot"][2][0],
                                  k["G_top"][2][1] - k["G_bot"][2][1]])
    c = CR.ccfg()
    base = KIN.candidate_sites(lat, int(c["n_top"]))
    front = CR.lattice_front(lat)
    tk = top_k(s["ref"]) or []
    pick = {}
    for k in base + front:
        pick.setdefault(CR.key(k), k)
    lk = {CR.key(k): k for k in lat}
    for r in tk:
        if _key(r["x_mm"], r["y_mm"]) in lk:
            pick.setdefault(_key(r["x_mm"], r["y_mm"]), lk[_key(r["x_mm"], r["y_mm"])])
    closed, rounds = False, 0
    for rnd in range(int(max_rounds or c["max_rounds"])):
        rounds = rnd + 1
        recs = SUB.run_tasks(tasks_for(s, [(k["x_mm"], k["y_mm"]) for k in pick.values()]))
        rows = []
        for k in pick.values():
            r = recs.get(tag(key, k["x_mm"], k["y_mm"])) or {}
            rows.append({"x_mm": k["x_mm"], "y_mm": k["y_mm"], "du_xy_um": k["du_xy_um"],
                         "du_z_um": k["du_z_um"], "T_C": SUB.site_temperature(k),
                         "du_def_xy_um": k.get("du_def_xy_um"),
                         "d_eps": r.get("d_peeq_per_cycle")})
        solved = {CR.key(r): (CR._screen_key(r), r["d_eps"]) for r in rows
                  if r["d_eps"] is not None}
        m, w = CR.margin_of(rows)
        sc = CR.screen(lat, solved, m)
        print(f"  {key} round {rnd}: {len(solved)} solved, margin {m:.3f}, max "
              f"{sc['max_solved']:.4e}, bound {sc['max_bound']:.4e}, {len(sc['need'])} to add",
              flush=True)
        if not sc["need"]:
            closed = True
            break
        for k in sc["need"]:
            pick.setdefault(CR.key(k), k)
    done = [r for r in rows if r["d_eps"] is not None]
    best = max(done, key=lambda r: r["d_eps"])
    tkeys = [_key(r["x_mm"], r["y_mm"]) for r in tk]
    return {"key": key, "closed": closed, "rounds": rounds, "n_lattice": len(lat),
            "n_solved": len(done), "margin_rel": m, "largest_reversal_rel": w,
            "max_site_mm": [best["x_mm"], best["y_mm"]], "max_d_eps": best["d_eps"],
            "max_in_top_k": _key(best["x_mm"], best["y_mm"]) in tkeys,
            "max_rank_in_reference": (tkeys.index(_key(best["x_mm"], best["y_mm"])) + 1
                                      if _key(best["x_mm"], best["y_mm"]) in tkeys else None),
            "n_top_k": len(tkeys)}


VAL = TR / "robustness_joint_validation"
#: the kinds of mechanical variant the validation covers (one full search per kind)
_MECH_CARDS = ("conv_E", "attach_stiff", "attach_uf", "bga_card_local")
KINDS = (("mounting", lambda v: v["group"].startswith("board")),
         ("encapsulant class", lambda v: v["name"].startswith("encap_")),
         ("mechanical card", lambda v: v["name"].startswith(_MECH_CARDS)),
         ("thermal decision", lambda v: not (v["group"].startswith("board")
                                             or v["name"].startswith(("encap_",) + _MECH_CARDS))))


def pick():
    """The validation rule: in each kind, the screened variant whose maximum lies DEEPEST among
    its reference's K worst sites (ties: the largest change against the reference) -- the
    variant most likely to have its worst site outside the K. Needs the screen's summary."""
    d = json.loads(OUT.read_text())
    taken, out = set(), {}
    for kind, test in KINDS:
        rows = [(v["rank_in_reference"], abs(v["change_rel"]), key) for key, v in
                d["variants"].items() if v.get("complete") and key not in taken and test(v)]
        if rows:
            r = max(rows)
            out[kind] = {"key": r[2], "rank_in_reference": r[0], "change_rel_abs": r[1]}
            taken.add(r[2])
    (TR / "robustness_joint_validation_picks.json").write_text(json.dumps(
        {"rule": pick.__doc__.split("\n\n")[0].strip(), "picks": out}, indent=1) + "\n")
    return out


KIND_SLUG = {"mounting": "mounting", "encapsulant class": "encapsulant",
             "mechanical card": "mechcard", "thermal decision": "thermal"}
VALK = TR / "robustness_joint_validation_by_kind"


def validate_kind(slug):
    """The full search of the variant the validation rule picked for one kind."""
    picks = json.loads((TR / "robustness_joint_validation_picks.json").read_text())["picks"]
    kind = next(k for k, v in KIND_SLUG.items() if v == slug)
    key = picks[kind]["key"]
    r = validate([key])[key]
    VALK.mkdir(parents=True, exist_ok=True)
    (VALK / f"{slug}.json").write_text(json.dumps(dict(r, kind=kind, pick=picks[kind]),
                                                  indent=1, default=float) + "\n")
    return r


def validate(keys=None):
    out = {}
    VAL.mkdir(parents=True, exist_ok=True)
    for key in list(keys or VALIDATE):
        out[key] = full_search(key)
        (VAL / f"{key}.json").write_text(json.dumps(out[key], indent=1, default=float) + "\n")
        print(key, {k: out[key].get(k) for k in ("closed", "n_solved", "max_site_mm",
                                                  "max_d_eps", "max_in_top_k",
                                                  "max_rank_in_reference")}, flush=True)
    return out


# ------------------------------------------------------------------ summary
def _u_rel():
    """Numerical U (relative) of each production joint of the local model, per (tier, arch);
    the reference state's joints take the production joint's of the same cooling and
    integration (provisional transfer)."""
    import tcpmt_uncertainty as TU
    eps, u_t, own, basis, band = TU.local_u()
    return u_t, basis


def _judge(a, b, va, vb, ua, ub):
    import tcpmt_resolution as RULE
    if None in (va, vb, ua, ub):
        return {"verdict": RULE.PENDING, "resolved": None}
    u95 = RULE.quad(ua * va, ub * vb)
    j = RULE.judge(vb - va, 0.0, u95)
    j["verdict"] = RULE.verdict_label(j["resolved"], j["D_corrected"], a, b)
    return j


def screened(s, recs):
    """The variant's responses at the reference's top K and their maximum."""
    tk = top_k(s["ref"]) or []
    vals = []
    for i, r in enumerate(tk):
        rec = recs.get(tag(s["key"], r["x_mm"], r["y_mm"])) or {}
        vals.append({"rank_in_reference": i + 1, "x_mm": r["x_mm"], "y_mm": r["y_mm"],
                     "reference_d_eps": r["d_eps"], "d_eps": rec.get("d_peeq_per_cycle"),
                     "error": rec.get("error")})
    done = [v for v in vals if v["d_eps"] is not None]
    if not tk or len(done) < len(tk):
        return {"complete": False, "n_solved": len(done), "n_sites": len(tk), "values": vals}
    best = max(done, key=lambda v: v["d_eps"])
    return {"complete": True, "n_sites": len(tk), "d_eps": best["d_eps"],
            "site_mm": [best["x_mm"], best["y_mm"]],
            "rank_in_reference": best["rank_in_reference"],
            "at_last_rank": best["rank_in_reference"] == len(tk),
            "reference_d_eps": tk[0]["d_eps"],
            "change_rel": best["d_eps"] / tk[0]["d_eps"] - 1.0, "values": vals}


def summarize():
    import tcpmt_mech_submodel as SUB
    import tcpmt_uncertainty as TU
    recs = SUB.load_records(STUDY)
    u_t, ubasis = _u_rel()
    specs = variants()
    out = {"what": "joint response of the mechanical robustness variants: the production local "
                   "model at the K worst sites of each variant's reference case (production "
                   "law at its converged window), the maximum over those sites",
           "K": K, "production_law": production_law(),
           "window": LAW.stored_window(production_law())[0],
           "reference_searches": {k: MP.rel(v) for k, v in CRIT.items() if v.is_file()},
           "rule": "D = y_Z2 - y_Z1 (b - a); resolved when |D + beta| > U95(D); beta = 0; "
                   "U95 = quadrature of each joint's numerical U of the local model (own "
                   "L0 -> L3 and 4 -> 8 cycle changes of the production joints, transferred "
                   "provisionally to the reference state's joints and to the variants); a "
                   "variant on another mesh than its reference is pending (the map's "
                   "transfer check); production law only (the law band is not re-run for "
                   "the variants)",
           "u_basis": ubasis, "references": {}, "variants": {}, "groups": {},
           "inputs_sha1": {}}
    refs = sorted({s["ref"] for s in specs})
    ref_mesh = {}
    for ref in refs:
        tk = top_k(ref)
        st, t, a = ref.split("_")
        import tcpmt_cases as TC
        p = TC.case_path(st, t, a)
        ref_mesh[ref] = TU.mesh_signature(json.loads(p.read_text())) if p else None
        out["references"][ref] = {"d_eps": tk[0]["d_eps"] if tk else None,
                                  "site_mm": [tk[0]["x_mm"], tk[0]["y_mm"]] if tk else None,
                                  "top_k_mm": [[r["x_mm"], r["y_mm"]] for r in tk or []],
                                  "top_k_d_eps": [r["d_eps"] for r in tk or []],
                                  "U_rel": u_t.get((t, a)), "mesh": ref_mesh[ref]}
    for f in CRIT.values():
        if f.is_file():
            out["inputs_sha1"][str(f.resolve())] = MP.sha1(f)
    for s in specs:
        sc = screened(s, recs)
        lf = lat_path(s["key"])
        lrec = json.loads(lf.read_text()) if lf.is_file() else {}
        mesh = (lrec.get("provenance") or {}).get("mesh")
        same_mesh = (mesh is not None and ref_mesh.get(s["ref"]) is not None
                     and list(mesh)[:2] == list(ref_mesh[s["ref"]])[:2])
        out["variants"][s["key"]] = dict(
            {k: s[k] for k in ("group", "arch", "tier", "ref", "name", "source")},
            same_mesh_as_reference=same_mesh, lattice=MP.rel(lf) if lf.is_file() else None,
            lattice_verification=lrec.get("verification"), **sc)
        out["inputs_sha1"].update(lrec.get("inputs_sha1") or {})
    # orderings per group (Z1 / Z2 / Z3 where present); an integration the variant does not
    # touch keeps the base case of its group (unchanged by definition, as in the map)
    by_group = {}
    for key, v in out["variants"].items():
        by_group.setdefault(v["group"], {}).setdefault(v["name"], {})[v["arch"]] = v

    def ref_val(ref):
        r = out["references"].get(ref)
        if r is None:
            tk = top_k(ref)
            r = {"d_eps": tk[0]["d_eps"] if tk else None}
        return r.get("d_eps")
    for g, per_name in by_group.items():
        res = {}
        for name, per in per_name.items():
            v0 = next(iter(per.values()))
            tier, refst = v0["tier"], v0["ref"].split("_")[0]
            vals, refv, mesh_ok, urel = {}, {}, {}, {}
            for a in ("Z1", "Z2", "Z3"):
                if a in per:
                    ref = per[a]["ref"]
                    # the ordering's baseline is the group's reference pair (for an S0
                    # decision cooled from below, the cooling-A reference: the map's row
                    # baseline), whatever reference supplied the screened sites
                    vals[a] = per[a].get("d_eps")
                    refv[a] = ref_val(f"{refst}_{tier}_{a}") if g == "S0_A" else ref_val(ref)
                    mesh_ok[a] = per[a]["same_mesh_as_reference"]
                elif not g.startswith("board") and a in GROUP_ARCHS.get(g, ("Z1", "Z2", "Z3")):
                    ref = f"{refst}_{tier}_{a}"
                    if ref_val(ref) is None:
                        continue
                    vals[a] = refv[a] = ref_val(ref)
                    mesh_ok[a] = True
                else:
                    continue
                _st, rt, _a = ref.split("_")
                urel[a] = u_t.get((rt, a))
            ords = {}
            for a, b in itertools.combinations(("Z1", "Z2", "Z3"), 2):
                if a not in vals or b not in vals or None in (vals[a], vals[b], refv[a],
                                                              refv[b]):
                    continue
                if a not in per and b not in per:
                    continue                      # neither integration is changed
                jv = _judge(a, b, vals[a], vals[b], urel[a], urel[b])
                jb = _judge(a, b, refv[a], refv[b], urel[a], urel[b])
                pend = not (mesh_ok.get(a) and mesh_ok.get(b))
                ords[f"eps:{a}/{b}"] = {
                    "variant": [vals[a], vals[b]], "base": [refv[a], refv[b]],
                    "base_lower": a if refv[a] < refv[b] else b,
                    "variant_lower": a if vals[a] < vals[b] else b,
                    "same_direction": (refv[a] < refv[b]) == (vals[a] < vals[b]),
                    "verdict": "pending" if pend else jv["verdict"],
                    "verdict_if_transferred": jv["verdict"],
                    "base_verdict": jb["verdict"], "U95": jv.get("U95"),
                    "D_corrected": jv.get("D_corrected"), "provisional": True,
                    **({"note": "variant mesh differs from its reference's"} if pend else {})}
            res[name] = {"values": vals, "reference": refv, "orderings": ords}
        out["groups"][g] = res
    vfiles = sorted(VAL.glob("*.json")) if VAL.is_dir() else []
    if vfiles:
        v = {f.stem: json.loads(f.read_text()) for f in vfiles}
        out["validation"] = v
        out["validation_all_in_top_k"] = all(x.get("max_in_top_k") for x in v.values()) \
            if v else None
        kinds = {}
        if VALK.is_dir():
            for f in VALK.glob("*.json"):
                r = json.loads(f.read_text())
                kinds[r.get("key")] = r.get("kind")
        for key, x in v.items():
            x["kind"] = kinds.get(key)
            sv = out["variants"].get(key) or {}
            if x.get("max_d_eps") and sv.get("d_eps"):
                x["screen_over_full"] = sv["d_eps"] / x["max_d_eps"]
        for f in vfiles:
            out["inputs_sha1"][str(f.resolve())] = MP.sha1(f)
    out["n_variants"] = len(out["variants"])
    out["n_complete"] = sum(1 for v in out["variants"].values() if v.get("complete"))
    out["n_at_last_rank"] = sum(1 for v in out["variants"].values() if v.get("at_last_rank"))
    out["max_rank_used"] = max((v.get("rank_in_reference") or 0)
                               for v in out["variants"].values())
    out["complete"] = out["n_complete"] == out["n_variants"]
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "list"
    keys = [x for i, x in enumerate(a) if i > 0 and not x.startswith("--")
            and a[i - 1] not in ("--log", "--groups", "--kind")]
    if cmd == "list":
        for s in variants(True):
            print(s["key"], s["group"], s["ref"], s.get("cold_key") or "")
    elif cmd == "lattice":
        errs = lattice(keys or None, "--force" in a, "--cold" in a)
        if errs:
            print(f"{len(errs)} lattice errors", flush=True)
            sys.exit(1)
    elif cmd == "run":
        run(keys or None, a[a.index("--log") + 1] if "--log" in a else None,
            a[a.index("--groups") + 1].split(",") if "--groups" in a else None,
            "--reverse" in a)
    elif cmd == "validate":
        if "--kind" in a:
            validate_kind(a[a.index("--kind") + 1])
        else:
            validate(keys or None)
    elif cmd == "pick":
        for kind, r in pick().items():
            print(kind, r)
    elif cmd == "summarize":
        s = summarize()
        print(json.dumps({k: s.get(k) for k in ("n_variants", "n_complete", "n_at_last_rank",
                                                "max_rank_used", "validation_all_in_top_k")},
                         indent=1))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
