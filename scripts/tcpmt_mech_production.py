"""TCPMT round 3 -- the mechanics revision in the PRODUCTION state of the design in force.

The mechanics revision (findings 1-11, scripts/tcpmt_mech_*) was written and validated on the
round-2 49-cell fields. The paper compares the PRODUCTION state (implemented input decoupling,
HV_SDEC; tcpmt_cases) of the design in force, Z1/Z2/Z3 x cooling A/B, Z3 on its coupled land
side. Every one of those case files already stores what the v2 local model needs:
final_closure_physical_etm.mechanics searches every configured interconnect layer
(tcpmt_mech_kinematics.interconnect_search: BGA on its legal lattice, the fine-pitch layers at
the mesh) and keeps the BGA candidates' full cut-boundary kinematics (u_x, u_y, u_z of both
faces and their in-plane gradients: translation, stretch, rotation) and the membrane/bending
split of du with the case. This module

  kin       turns a compared case file into the site-kinematics record the law band, the
            critical-joint check and the local checks read (site_kinematics/<LABEL>.json; no
            field is re-read), with the site coverage of the search (every legal site of the
            design's lattice, the full candidate set) and the identity of the case (sha1);
  guard     refuses a case whose BGA counts are not the ones in force (a re-run that has not
            landed: Z1's 48-V balls at the re-closure's adopted count, Z3's 1-V balls at the
            design record's count) -- the mechanics revision never reads a stale field;
  drivers   summarizes the interconnect layers of the compared cases (finding 4: driver
            gamma = |du_xy| / h and the layer shear strain gamma_def = du_x/dz + du_z/dx at the
            critical site of every layer, the governing layer) and the composition of the BGA
            driver (finding 9: membrane / bending / residual, rigid rotation / deforming part)
            -> interconnect_drivers.json;
  ladder    the same per-layer drivers on the production-state mesh ladder (r11 / r21 / r31
            case files) -> interconnect_mesh_ladder.json;
  check     every record built from a case file against that file as it is now.

Labels: <STATE>_<TIER>_<ARCH>, e.g. SDEC_A_Z1 (production state, cooling A, Z1).

    python tcpmt_mech_production.py kin [LABEL ...] [--state SDEC]
    python tcpmt_mech_production.py lattice [LABEL ...]   (every BGA lattice site, from the
                                                           case's converged fields)
    python tcpmt_mech_production.py drivers [--state SDEC]
    python tcpmt_mech_production.py ladder [--state SDEC]
    python tcpmt_mech_production.py check
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts", "scripts/phase0nw"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

ROOT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research")   # campaign hook
TR = ROOT / "tcpmt_revision"
FC = ROOT / "final_closure"
KIN_DIR = TR / "site_kinematics"
DRIVERS = TR / "interconnect_drivers.json"
LADDER = TR / "interconnect_mesh_ladder.json"
Z3_CONFIG = R / "configs" / "phase0nz" / "z3_board_backside.yaml"
TIERS = ("A", "B")
ARCHS = ("Z1", "Z2", "Z3")
#: the local model's state: the production state unless TCPMT_LOCAL_STATE names another one
#: (S0, S1: the references, from their own case files; 'round2': the round-2 field cases of
#: tcpmt_mech_kinematics.CASES, kept to reproduce the merged branch's numbers)
LOCAL_STATE = os.environ.get("TCPMT_LOCAL_STATE", "SDEC")
#: the integrations of the local model's state: all three unless TCPMT_LOCAL_ARCHS names a
#: subset (e.g. "Z1" for the count neighbours m25 / m49, whose design subroots hold only Z1)
LOCAL_ARCHS = tuple(a for a in os.environ.get("TCPMT_LOCAL_ARCHS", ",".join(ARCHS)).split(",")
                    if a in ARCHS)


def label(state, tier, arch):
    return f"{state}_{tier}_{arch}"


def parse(lab):
    """'SDEC_A_Z1' -> ('SDEC', 'A', 'Z1'); None for any other label."""
    m = re.fullmatch(r"(SDEC|S0|S1)_([AB])_(Z[123])", str(lab))
    return m.groups() if m else None


def labels(state=None):
    state = state or LOCAL_STATE
    return [label(state, t, a) for t in TIERS for a in ARCHS if a in LOCAL_ARCHS]


def case_path(lab):
    import tcpmt_cases as TC
    st, t, a = parse(lab)
    return TC.case_path(st, t, a)


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rel(p):
    import tcpmt_cases as TC
    return TC.rel(p)


def inputs_sha1(paths):
    """{absolute path: sha1} of the files a record is built from (the campaign validator's
    freshness check, scripts/campaign/validators.py `fresh`)."""
    return {str(Path(p).resolve()): sha1(p) for p in paths if p and Path(p).is_file()}


# ------------------------------------------------------------------ inputs in force
def _row_text(r):
    return " ".join(str(r.get(k) or "") for k in ("model", "note", "conductor"))


def z3_balls_per_rail():
    """The 1-V ball count per rail of the Z3 design record."""
    import yaml
    c = yaml.safe_load(Z3_CONFIG.read_text())
    return int(c["bga"]["power_field_1v"]["n_per_rail"])


def z1_adopted_per_rail():
    """Z1's 48-V ball count per rail at the re-closure's adopted count, or None when the
    re-closure has not adopted one (the network build's count is then in force)."""
    f = FC / "package_network_adopted.json"
    if not f.is_file():
        return None
    return (json.loads(f.read_text()).get("adopted_count") or {}).get("Z1")


def input_issue(arch, case):
    """None when the case was solved with the BGA counts in force, else what is stale. The
    48-V balls of Z1 follow the re-closure's adopted count (final_closure_ledger reads
    package_network_adopted.json when it exists); the 1-V balls of Z3 the design record's count
    (configs/phase0nz/z3_board_backside.yaml). Z2's coupled ledger depends on neither. A Z1
    case solved at another 48-V count stands for the adopted one when the re-closure recorded
    the change of the production cases' BGA feed terms below its threshold
    (final_closure_ledger.accepted_count: only which lattice sites carry 48 V differs, and the
    ball layer of the FE model is homogenized)."""
    rows = {r["term"]: r for r in case.get("ledger_rows") or []}
    if arch == "Z1":
        n = z1_adopted_per_rail()
        r = rows.get("P_pkg_RDL_HV_supply")
        if n is not None and r is not None:
            m = re.search(r"N=(\d+)/rail", _row_text(r))
            if not m or int(m.group(1)) != int(n):
                if m:
                    import final_closure_ledger as FL
                    if FL.accepted_count("Z1", int(m.group(1)), FC)[0] is not None:
                        return None
                return (f"Z1 48-V balls {m.group(1) if m else '?'} per rail in the case, the "
                        f"re-closure adopted {n}: the re-run has not landed")
    if arch == "Z3":
        n = z3_balls_per_rail()
        r = rows.get("P_BGA_1V_VDD")
        if r is not None:
            m = re.search(r"(\d+) per rail", _row_text(r))
            if not m or int(m.group(1)) != n:
                return (f"Z3 1-V balls {m.group(1) if m else '?'} per rail in the case, the "
                        f"design record has {n}: the re-run has not landed")
    return None


def load_case(lab, strict=True):
    """(path, case) of a compared case, guarded (design in force, coupled Z3, BGA counts in
    force); strict=False returns the issue instead of raising."""
    import tcpmt_cases as TC
    st, t, a = parse(lab)
    p = TC.case_path(st, t, a)
    if p is None:
        raise FileNotFoundError(f"{lab}: no case file (tcpmt_cases.expected_path "
                                f"{rel(TC.expected_path(st, t, a))})")
    c = json.loads(p.read_text())
    TC.guard(a, c, p)
    why = input_issue(a, c)
    if why and strict:
        raise RuntimeError(f"{lab} ({p.name}): {why}")
    return p, c


# ------------------------------------------------------------------ site kinematics
def lattice_sites(arch):
    import physical_coords as PCO
    import pkg_rdl_network as K
    try:
        cut = K.architecture_cutout_mm(arch)
    except KeyError:
        cut = None
    return PCO.bga_lattice_sites(cut), cut


def site_coverage(arch, me):
    """Does the critical-joint search cover the full site set of the design in force? The
    legal lattice of the package (and Z2's ring) against what the all-site search
    (joint_search) and the interconnect search evaluated, and the candidate set of the v2
    critical-joint check against the rule it is drawn by (over EVERY evaluated site)."""
    sites, cut = lattice_sites(arch)
    js = me.get("joint_search") or {}
    b = (me.get("interconnects") or {}).get("bga") or {}
    n = len(sites)
    out = {"lattice_sites": n, "cutout_mm": cut,
           "lattice_rule": "every legal site of the centred 0.8-mm lattice of the package "
                           "(physical_coords.bga_lattice_sites), less Z2's board opening",
           "joint_search": {"n_sites": js.get("n_sites"), "n_evaluated": js.get("n_evaluated")},
           "interconnect_search": {"n_sites": b.get("n_sites"),
                                   "n_evaluated": b.get("n_evaluated")},
           "n_candidates": len((b.get("candidates") or {}).get("x_mm") or []),
           "candidate_rule": "top 30 by |du_xy|, by |relative tilt|, by |eps_z| and by the "
                             "deforming du, the strict Pareto front in (|du_xy|, T) and the "
                             "four corners, drawn over every evaluated site "
                             "(tcpmt_mech_kinematics.candidate_sites)"}
    out["full"] = bool(n and js.get("n_sites") == n and js.get("n_evaluated") == n
                       and b.get("n_sites") == n and b.get("n_evaluated") == n)
    return out


def kin_record(lab):
    """The site-kinematics record of a compared case, from its own case file."""
    import tcpmt_mech_kinematics as KIN
    p, c = load_case(lab)
    st, t, a = parse(lab)
    me = c.get("mechanics") or {}
    if not me.get("interconnects"):
        raise RuntimeError(f"{lab}: the case stores no interconnect search "
                           f"({me.get('interconnect_error') or 'mechanics missing'})")
    ic = me["interconnects"]
    for name, v in ic.items():                    # the same T_C convenience key as the search
        if "critical" in v:
            v["critical"].setdefault("T_C", KIN.site_T(v["critical"]))
    js = me.get("joint_search") or {}
    return {"case": lab, "arch": a, "state": st, "tier": t,
            "scenario": c.get("scenario"), "design": (c.get("design") or {}).get("design"),
            "field": None, "case_file": rel(p), "case_sha1": sha1(p),
            "inputs_sha1": inputs_sha1([p]),
            "case_T_max_C": c["thermal"]["T_max_C"], "case_P_loss_w": c.get("P_loss_w"),
            "source": "the case file's mechanics block (final_closure_physical_etm.mechanics -> "
                      "tcpmt_mech_kinematics.interconnect_search on the converged structural "
                      "field of the case)",
            "legacy_critical": js.get("critical"), "interconnects": ic,
            "decomposition_bga_critical": me.get("decomposition_bga_critical"),
            "decomposition_legacy_critical": None,
            "site_coverage": site_coverage(a, me),
            "die_warpage_pv_um": me.get("die_warpage_pv_um")}


LATTICE_DIR = KIN_DIR / "lattice"
#: the recomputed stored candidates must reproduce the case file's (rounded to 1e-9 mm there)
LATTICE_TOL_MM = 1e-8


def lattice_path(lab):
    return LATTICE_DIR / f"{lab}.json"


def lattice_record(lab):
    """Finding 2 under the v2 BCs: the full cut-boundary kinematics of EVERY legal BGA lattice
    site of a compared case. The global interconnect search evaluates them all but the case
    file keeps only its candidates; the critical-joint check's screening rule
    (tcpmt_mech_critical: dominance in the deforming du, |du_z| and T) needs the rest. They are
    recomputed with the search's own code (tcpmt_mech_kinematics.site_kinematics, same layer,
    pad and fit) from the case's converged structural and thermal fields, after checking that
    the field's mesh is the production mesh and its T_max the case's, and the recomputed
    candidates must reproduce the case file's (LATTICE_TOL_MM): the record is the case's."""
    import numpy as np
    import final_closure_physical_etm as E
    import production_et as PE
    import pkg_rdl_network as K
    import tcpmt_cases as TC
    import tcpmt_mech_kinematics as KIN
    import tcpmt_mech_laws as LAW
    p, c = load_case(lab)
    _st, _t, a = parse(lab)
    cf = TC.converged_field(p, c)
    if not cf or not cf.get("structural"):
        raise RuntimeError(f"{lab}: no converged structural field on disk for {rel(p)}")
    E._raise_stack_limit()
    m, _mats, _stc, _tiles, _ = E.build(a, E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    xyz = KIN.read_frd_nodes(cf["structural"])
    if len(xyz) - 1 != m.n_nodes or np.nanmax(np.abs(xyz[1:] - m.nodes)) > 1e-5:
        raise RuntimeError(f"{lab}: {cf['structural']} is not on the production mesh")
    U = PE.ccxio.read_frd(cf["structural"])["DISP"][:, :3]
    Tn = PE.ccxio.read_frd(cf["thermal"])["NDTEMP"][1:m.n_nodes + 1, 0]
    if abs(float(np.nanmax(Tn)) - c["thermal"]["T_max_C"]) > 1e-3:
        raise RuntimeError(f"{lab}: {cf['thermal']} is not the case's converged field")
    cfg = LAW.cfg()
    ent = next(e for e in cfg["interconnects"][a] if e["sites"] == "bga_lattice")
    half = 0.5 * float(cfg["geometries"][ent["geometry"]]["pad"]) / 1e3
    cut = K.architecture_cutout_mm(a) if a != "Z3" else None
    sites = KIN.layer_sites(m, ent["layer"], "bga_lattice", cut)
    kin = KIN.site_kinematics(m, U, Tn, ent["layer"], sites, half,
                              int(cfg["local"].get("pad_fit_samples", 5)))
    ic = c["mechanics"]["interconnects"]["bga"]
    stored = KIN.expand_sites(ic["candidates"])
    idx = {(round(k["x_mm"], 6), round(k["y_mm"], 6)): k for k in kin}
    dev, missing = 0.0, []
    for s in stored:
        k = idx.get((round(s["x_mm"], 6), round(s["y_mm"], 6)))
        if k is None:
            missing.append([s["x_mm"], s["y_mm"]])
            continue
        dev = max([dev] + [abs(x - y) for f in ("u_bot_mm", "u_top_mm")
                           for x, y in zip(k[f], s[f])]
                  + [abs(x - y) for f in ("G_bot", "G_top")
                     for rk, rs in zip(k[f], s[f]) for x, y in zip(rk, rs)])
    if missing or dev > LATTICE_TOL_MM or len(kin) != ic.get("n_evaluated"):
        raise RuntimeError(f"{lab}: the recomputed lattice does not reproduce the case's search "
                           f"(missing {missing[:3]}, max deviation {dev:.2e} mm, "
                           f"{len(kin)} vs {ic.get('n_evaluated')} sites)")
    return {"case": lab, "arch": a, "case_file": rel(p), "case_sha1": sha1(p),
            "fields": {"structural": str(cf["structural"]), "thermal": str(cf["thermal"])},
            "inputs_sha1": inputs_sha1([p, cf["structural"], cf["thermal"]]),
            "n_sites": len(sites), "n_evaluated": len(kin), "layer": ent["layer"],
            "verification": {"n_stored_candidates": len(stored), "max_deviation_mm": dev,
                             "tolerance_mm": LATTICE_TOL_MM},
            "source": "tcpmt_mech_kinematics.site_kinematics on the case's converged structural "
                      "and thermal fields (tcpmt_cases.converged_field), production mesh",
            "sites": KIN.compact_sites(kin)}


def write_lattice(labs):
    LATTICE_DIR.mkdir(parents=True, exist_ok=True)
    for lab in labs:
        r = lattice_record(lab)
        lattice_path(lab).write_text(json.dumps(r, default=float) + "\n")
        print(f"{lab}: {r['n_evaluated']}/{r['n_sites']} lattice sites, stored candidates "
              f"reproduced to {r['verification']['max_deviation_mm']:.1e} mm", flush=True)


def load_lattice(lab):
    """The full-lattice kinematics of a compared case (expanded), or None."""
    import tcpmt_mech_kinematics as KIN
    f = lattice_path(lab)
    if not f.is_file():
        return None
    return KIN.expand_sites(json.loads(f.read_text())["sites"])


def write_kin(labs):
    KIN_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for lab in labs:
        r = kin_record(lab)
        (KIN_DIR / f"{lab}.json").write_text(json.dumps(r, default=float) + "\n")
        c = r["interconnects"]["bga"]["critical"]
        out[lab] = r
        print(f"{lab}: {r['case_file']} BGA crit ({c['x_mm']}, {c['y_mm']}) du_xy "
              f"{c['du_xy_um']:.3f} um du_z {c['du_z_um']:.3f} um T {c['T_C']:.1f} C; coverage "
              f"{r['site_coverage']['interconnect_search']['n_evaluated']}/"
              f"{r['site_coverage']['lattice_sites']} sites, "
              f"{r['site_coverage']['n_candidates']} candidates, full "
              f"{r['site_coverage']['full']}" +
              "".join(f"; {k}: gamma {v['gamma_max']:.2e}" for k, v in
                      r["interconnects"].items() if "gamma_max" in v), flush=True)
        if not r["site_coverage"]["full"]:
            raise RuntimeError(f"{lab}: the critical-joint search does not cover the full "
                               f"site set of the design in force: {r['site_coverage']}")
    return out


# ------------------------------------------------------------------ drivers (findings 4, 9)
def _layer_row(v):
    c = v["critical"]
    s = v.get("critical_by_shear_strain") or {}
    return {"label": v.get("label"), "geometry": v.get("geometry"), "h_um": v.get("h_um"),
            "n_sites": v.get("n_sites"), "n_evaluated": v.get("n_evaluated"),
            "site_kind": v.get("sites"),
            "critical": {"x_mm": c["x_mm"], "y_mm": c["y_mm"], "gamma": c["gamma"],
                         "gamma_def": c.get("gamma_def"), "du_xy_um": c["du_xy_um"],
                         "du_def_xy_um": c.get("du_def_xy_um"), "du_z_um": c["du_z_um"],
                         "eps_z": c["eps_z"], "T_C": c.get("T_C")},
            "gamma_max": v.get("gamma_max"), "gamma_def_max": v.get("gamma_def_max"),
            "critical_by_shear_strain": ({"x_mm": s.get("x_mm"), "y_mm": s.get("y_mm"),
                                          "gamma_def": s.get("gamma_def"),
                                          "T_C": s.get("T_C")} if s else None),
            "du_xy_um_max": v.get("du_xy_um_max"), "eps_z_range": v.get("eps_z_range")}


def drivers(state=None):
    """Findings 4 and 9 over the compared cases of one state."""
    import tcpmt_mech_kinematics as KIN
    out = {"what": "interconnect drivers per layer (finding 4) and the composition of the BGA "
                   "joint driver (finding 9) of the compared cases",
           "generator": "scripts/tcpmt_mech_production.py drivers",
           "state": state or LOCAL_STATE,
           "driver": "gamma = |du_xy| / h (relative in-plane displacement over the layer "
                     "height); layer shear strain gamma_def = |du_def| / h = du_x/dz + du_z/dx "
                     "(the rigid rotation of the joint, -h x the mean face tilt, removed)",
           "cases": {}}
    nb_add = nb_opp = 0
    for lab in labels(state):
        k = KIN.load_kinematics(lab)
        if not k:
            continue
        lay = {n: _layer_row(v) for n, v in k["interconnects"].items() if "critical" in v}
        d = k.get("decomposition_bga_critical") or {}
        sh = d.get("share_along_du") or {}
        if sh.get("bending") is not None:
            nb_add += sh["bending"] > 0
            nb_opp += sh["bending"] < 0
        nrm = lambda v: float(math.hypot(*v[:2])) if v else None        # noqa: E731
        fine = {n: r for n, r in lay.items() if n != "bga"}
        bga = lay.get("bga")
        out["cases"][lab] = {
            "case_file": k["case_file"], "case_sha1": k["case_sha1"],
            "site_coverage": k.get("site_coverage"), "layers": lay,
            "governing_layer_by_gamma": max(lay, key=lambda n: lay[n]["gamma_max"] or 0)
            if lay else None,
            "governing_layer_by_shear_strain": max(lay, key=lambda n: lay[n]["gamma_def_max"]
                                                   or 0) if lay else None,
            "fine_pitch_over_bga_gamma": ({n: (r["gamma_max"] / bga["gamma_max"])
                                           for n, r in fine.items()} if bga else None),
            "bga_split": {"x_mm": d.get("x_mm"), "y_mm": d.get("y_mm"),
                          "du_xy_um": d.get("du_xy_um"),
                          "membrane_um": nrm(d.get("membrane_um")),
                          "bending_um": nrm(d.get("bending_um")),
                          "residual_um": nrm(d.get("residual_um")), "share_along_du": sh,
                          "free_mismatch_um": nrm(d.get("free_expansion_estimate_um")),
                          "rigid_rotation_um": nrm(d.get("rigid_rotation_um")),
                          "deforming_xy_um": d.get("deforming_xy_um")}}
    out["inputs_sha1"] = inputs_sha1([case_path(lab) for lab in out["cases"]])
    out["claim_test"] = {
        "claim": "plate bending, not temperature, drives the joint",
        "cases_where_bending_adds_to_du": nb_add, "cases_where_bending_opposes_du": nb_opp,
        "reading": "membrane = in-plane thermal-expansion mismatch at the neutral planes; the "
                   "bending part opposes it where its share is negative; the joint's rigid "
                   "rotation is part of |du_xy| but strains nothing."}
    f = DRIVERS if (state or LOCAL_STATE) == "SDEC" else DRIVERS.with_name(
        f"interconnect_drivers_{state or LOCAL_STATE}.json")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def ladder(state=None, rungs=("r11", "r31")):
    """Per-layer drivers of each compared case on its own mesh ladder (the production-state
    rungs the campaign solves: sensitivity/ladder/<case>_<rung>.json beside the r21 case): is
    each layer's critical driver mesh-converged? A bimaterial corner (the die edge over the
    microbump row) is not, by construction; the BGA lattice driver is."""
    import tcpmt_uncertainty as TU
    out = {"what": "interconnect drivers on the production-state mesh ladder (finding 4)",
           "state": state or LOCAL_STATE, "cases": {}}
    for lab in labels(state):
        p = case_path(lab)
        if p is None:
            continue
        files = {"r21": p, **{r: f for r, f in TU.ladder_files(p).items() if r in rungs}}
        per = {}
        for r, f in files.items():
            if not Path(f).is_file():
                continue
            c = json.loads(Path(f).read_text())
            ic = (c.get("mechanics") or {}).get("interconnects") or {}
            per[r] = {n: {"gamma_max": v.get("gamma_max"), "gamma_def_max": v.get("gamma_def_max"),
                          "critical_mm": [v["critical"]["x_mm"], v["critical"]["y_mm"]],
                          "n_elems": (c.get("thermal") or {}).get("n_elems")}
                      for n, v in ic.items() if "critical" in v}
            per[r]["_file"] = rel(f)
            per[r]["_abs"] = str(Path(f).resolve())
            per[r]["_sha1"] = sha1(f)
        conv = {}
        for n in (per.get("r21") or {}):
            if n.startswith("_"):
                continue
            g = {r: (per.get(r) or {}).get(n, {}).get("gamma_max") for r in ("r11", "r21", "r31")}
            gd = {r: (per.get(r) or {}).get(n, {}).get("gamma_def_max")
                  for r in ("r11", "r21", "r31")}
            conv[n] = {"gamma": g, "gamma_def": gd,
                       "r31_over_r21": (g["r31"] / g["r21"]) if g.get("r31") and g.get("r21")
                       else None,
                       "r31_over_r21_def": (gd["r31"] / gd["r21"]) if gd.get("r31")
                       and gd.get("r21") else None}
            x = conv[n]["r31_over_r21"]
            conv[n]["converged_5pct"] = None if x is None else abs(x - 1.0) <= 0.05
        out["cases"][lab] = {"rungs": per, "layers": conv}
    out["inputs_sha1"] = {r["_abs"]: r["_sha1"] for c in out["cases"].values()
                          for r in c["rungs"].values()}
    f = LADDER if (state or LOCAL_STATE) == "SDEC" else LADDER.with_name(
        f"interconnect_mesh_ladder_{state or LOCAL_STATE}.json")
    f.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


# ------------------------------------------------------------------ provenance
def check():
    """Every record built from a compared case file against that case file as it is now
    (sha1) and against the BGA counts in force. Returns (ok, messages)."""
    msgs, ok = [], True
    cur = {}
    for lab in labels("SDEC"):
        p = case_path(lab)
        if p is None:
            msgs.append(f"MISSING {lab}: no case file")
            ok = False
            continue
        c = json.loads(p.read_text())
        cur[lab] = sha1(p)
        why = input_issue(parse(lab)[2], c)
        if why:
            ok = False
            msgs.append(f"STALE   {lab}: {why}")
    recs = []
    for f in sorted(KIN_DIR.glob("SDEC_*.json")):
        recs.append((f.name, f.stem, json.loads(f.read_text()).get("case_sha1")))
    for name, key in (("solder_law_band.json", "joints"), ("solder_critical_v2.json", "cases")):
        d = json.loads((TR / name).read_text()) if (TR / name).is_file() else {}
        for lab, v in (d.get(key) or {}).items():
            k = v.get("kinematics_case") or v.get("case") or lab
            recs.append((name, k, v.get("case_sha1")))
    for name, lab, s in recs:
        if lab not in cur:
            continue
        if s is None:
            msgs.append(f"NOHASH  {name} {lab}")
            continue
        if s != cur[lab]:
            ok = False
            msgs.append(f"CHANGED {name} {lab}: built from {s[:10]}, case now {cur[lab][:10]}")
    if ok:
        msgs.append(f"ok: {len(recs)} record entries match the {len(cur)} compared case files")
    return ok, msgs


def main():
    a = sys.argv[1:]
    state = a[a.index("--state") + 1] if "--state" in a else None
    rest = [x for i, x in enumerate(a) if x != "--state" and (i == 0 or a[i - 1] != "--state")]
    cmd = rest[0] if rest else "kin"
    if cmd == "kin":
        write_kin([x for x in rest[1:] if parse(x)] or labels(state))
    elif cmd == "lattice":
        write_lattice([x for x in rest[1:] if parse(x)] or labels(state))
    elif cmd == "drivers":
        d = drivers(state)
        for lab, c in d["cases"].items():
            print(lab, c["governing_layer_by_gamma"], c["governing_layer_by_shear_strain"],
                  {n: round(1e3 * r["gamma_max"], 3) for n, r in c["layers"].items()})
    elif cmd == "ladder":
        d = ladder(state)
        for lab, c in d["cases"].items():
            print(lab, {n: v["r31_over_r21"] for n, v in c["layers"].items()})
    elif cmd == "check":
        ok, msgs = check()
        print("\n".join(msgs))
        sys.exit(0 if ok else 1)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
