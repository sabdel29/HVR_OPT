"""Task 2 -- cycle stabilisation of the six cooling-tier responses.

Each tier case (A: Z1, Z2, Z3; B: Z1, Z2, Z3) is solved at its critical joint at L0 with the
production settings for 16 cycles, exactly as final_closure_local_mesh.cycles() does
(_solve(..., 'L0', production dt0, split=True, 16)), and once more for 48 cycles to pin the
stabilised value where 16 cycles have not settled.

Why the response drifts: the production card hardens ISOTROPICALLY on a bilinear *PLASTIC
curve that saturates at an accumulated inelastic strain of 0.02, and PEEQ is a path length
that only grows. The threshold of the overstress law therefore rises cycle by cycle until
every core element has accumulated 0.02; joints with a small per-cycle increment need many
cycles to get there.

Comparisons use the declared ordering rule (local_mesh_policy.json): an ordering holds if the
relative gap exceeds 2 max(U_a, U_b), U = U_mesh + U_time + U_cyc, with U_cyc re-defined for a
stabilised value as its residual cycle-count uncertainty (below).

    python tcpmt_solder_cycles.py --run | --summarize
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_solder_common as C                                     # noqa: E402

STUDY = "cycles"
N16, NLONG = 16, 48


def tasks():
    t = []
    for n in (NLONG, N16):                                    # long runs first
        for tier, arch, case in C.tier_cases():
            c = C.critical(case)
            t.append(dict(study=STUDY, tag=f"{tier}_{arch}_N{n}", du_um=c["du_um"],
                          T_C=c["T_C"], n_cyc=n,
                          meta={"tier": tier, "arch": arch, "case": case,
                                "x_mm": c["x_mm"], "y_mm": c["y_mm"]}))
    return t


def aitken(seq):
    """Aitken delta-squared limit of the last three terms (None if not contracting)."""
    if len(seq) < 3:
        return None
    a, b, c = seq[-3:]
    d1, d2 = b - a, c - b
    if d1 == 0 or d2 == 0 or d2 / d1 <= 0 or d2 / d1 >= 1:
        return None
    return c - d2 * d2 / (d2 - d1)


def tail_fit(seq, n_last=20):
    """v_k = v_inf + a r^k fitted to the last n_last cycles (grid in r, linear in v_inf, a);
    returns v_inf, r and the rms residual, or None."""
    import numpy as np
    y = np.array(seq[-n_last:], dtype=float)
    k = np.arange(len(y), dtype=float)
    best = None
    for r in np.linspace(0.50, 0.995, 400):
        M = np.vstack([np.ones_like(k), r ** k]).T
        coef, *_ = np.linalg.lstsq(M, y, rcond=None)
        res = float(np.sqrt(np.mean((M @ coef - y) ** 2)))
        if best is None or res < best[2]:
            best = (float(coef[0]), float(r), res)
    return {"v_inf": best[0], "r": best[1], "rms_residual": best[2],
            "n_cycles_fitted": int(len(y))} if best else None


def u_parts(case, prod):
    """U_mesh, U_time for a tier case: the pass-5 values of the mesh-study case solved on the
    same case file (TCPMT round 3: the study's Z3 case is the coupled land-side case, i.e. the
    tier-A Z3 joint), otherwise the largest over the pass-5 production cases (no own mesh
    study). Matched by file, never by name, so a case the study does not hold cannot raise;
    parts the study left unresolved are skipped (None when none is resolved)."""
    name = C.CASES[case].name
    own = next((k for k, p in prod.items() if p.get("source") == name), None)
    if own and prod[own].get("U_mesh") is not None and prod[own].get("U_time") is not None:
        return prod[own]["U_mesh"], prod[own]["U_time"], f"own pass-5 ({own})"
    um = [p["U_mesh"] for p in prod.values() if p.get("U_mesh") is not None]
    ut = [p["U_time"] for p in prod.values() if p.get("U_time") is not None]
    return (max(um) if um else None, max(ut) if ut else None,
            "largest pass-5 production value (no own mesh study)")


def _usum(*parts):
    """Sum of uncertainty parts; None when any part is unknown."""
    return None if any(p is None for p in parts) else sum(parts)


def summarize():
    recs = C.load_records(STUDY)
    prod = C.production_uncertainty()
    offs = [abs(p["L0"] - p["L3"]) / p["L3"] for p in prod.values() if p["L0"] and p["L3"]]
    l0_offset = max(offs) if offs else None
    import tcpmt_solder_units_check as UC
    unum = UC.summarize()["cases"]
    out = {"what": "cycle stabilisation of the six tier responses (task 2)",
           "settings": {"level": "L0", "first_increment_s": C.INC0, "split_steps": True,
                        "n_cycles": [N16, NLONG], "procedure": "as "
                        "final_closure_local_mesh.cycles(): _solve(..., 'L0', dt0, True, n)"},
           "stabilised_value_rule": "the 48-cycle run's last-cycle increment; U_cyc(stab) = "
                                    "max(|v48 - v40|, |v48 - Aitken limit|, |v48 - v_inf of an "
                                    "exponential fit to cycles 29-48|) / v48; a 16-cycle value "
                                    "carries U_cyc = |v16 - v48| / v48 + U_cyc(stab)",
           "u_rule": "U = U_mesh + U_time + U_cyc; U_mesh, U_time from local_mesh_study.json "
                     "(own case, or the largest production value for cases without a mesh "
                     "study); 4-cycle U_cyc = |v16 - v4| / v16 as the policy defines it",
           "u_card_grid_rule": "U_stab_num adds the case's card-grid sensitivity |v(7-row "
                               "production card) - v(same card rebuilt on 2.5 C rows)| / "
                               "v(2.5 C rows) (tcpmt_solder_units_check.py): the solver's "
                               "linear-in-A interpolation between the 25 C-spaced rows, which "
                               "the policy U does not contain",
           "u_conservative_rule": "U_stab_num plus the largest L0 -> L3 offset of the "
                                  "production cases ("
                                  + ("not available" if l0_offset is None
                                     else f"{l0_offset:.4f}") + "), since the tier values "
                                  "are L0",
           "cases": {}}
    vals = {}
    for tier, arch, case in C.tier_cases():
        r16 = recs.get(f"{tier}_{arch}_N{N16}") or {}
        rl = recs.get(f"{tier}_{arch}_N{NLONG}") or {}
        pc16 = r16.get("per_cycle") or []
        pcl = rl.get("per_cycle") or []
        v4 = pc16[3] if len(pc16) > 3 else None
        v16 = pc16[-1] if len(pc16) == N16 else None
        vl = pcl[-1] if len(pcl) == NLONG else None
        um, ut, ub = u_parts(case, prod)
        row = {"case_file": C.rel(C.CASES[case]), "du_um": r16.get("du_um"),
               "T_C": r16.get("T_joint_C"), "per_cycle_16": pc16, "per_cycle_48": pcl,
               "errors": [r16.get("error"), rl.get("error")],
               "v4": v4, "v16": v16, "v48": vl,
               "mean_last3_16": (sum(pc16[-3:]) / 3 if v16 else None),
               "drift_per_cycle_at_16": ((pc16[-1] - pc16[-2]) / pc16[-1] if v16 else None),
               "change_4_to_16_rel": ((v16 - v4) / v4 if (v16 and v4) else None),
               "U_mesh": um, "U_time": ut, "U_basis": ub}
        if vl:
            lim = aitken(pcl)
            tf = tail_fit(pcl)
            row["aitken_limit_48"] = lim
            row["tail_fit_48"] = tf
            row["drift_last8_rel"] = (pcl[-1] - pcl[-9]) / pcl[-1]
            row["change_4_to_48_rel"] = (vl - v4) / v4 if v4 else None
            row["change_16_to_48_rel"] = (vl - v16) / v16 if v16 else None
            ucs = max(abs(pcl[-1] - pcl[-9]) / vl, abs(vl - lim) / vl if lim else 0.0,
                      abs(vl - tf["v_inf"]) / vl if tf else 0.0)
            row["U_cyc_stab"] = ucs
            row["stabilised"] = vl
            if v16:
                row["U_cyc_16"] = abs(v16 - vl) / vl + ucs
        if v4 and v16:
            row["U_cyc_4cycle"] = abs(v16 - v4) / v16
        row["U_4cycle"] = _usum(um, ut, row.get("U_cyc_4cycle"))
        row["U_16"] = _usum(um, ut, row.get("U_cyc_16"))
        row["U_stab"] = _usum(um, ut, row.get("U_cyc_stab"))
        un = (unum.get(f"{tier}_{arch}") or {}).get("card_grid_sensitivity_rel")
        row["U_card_grid"] = un
        row["U_stab_num"] = _usum(row["U_stab"], un)
        row["U_stab_conservative"] = _usum(row["U_stab_num"], l0_offset)
        out["cases"][f"{tier}_{arch}"] = row
        vals[(tier, arch)] = row
    comps = []
    for tier in ("A", "B"):
        for a, b in itertools.combinations(("Z1", "Z2", "Z3"), 2):
            ra, rb = vals[(tier, a)], vals[(tier, b)]
            entry = {"tier": tier, "pair": f"{a} vs {b}"}
            for lab, ka, ku in (("4cycle", "v4", "U_4cycle"), ("16cycle", "v16", "U_16"),
                                ("stabilised", "stabilised", "U_stab"),
                                ("stabilised_with_card_grid", "stabilised",
                                 "U_stab_num"),
                                ("stabilised_conservative", "stabilised",
                                 "U_stab_conservative")):
                va, vb, ua, ub_ = ra.get(ka), rb.get(ka), ra.get(ku), rb.get(ku)
                if None in (va, vb, ua, ub_):
                    entry[lab] = None
                    continue
                gap = abs(va - vb) / max(va, vb)
                entry[lab] = {"lower": a if va < vb else b, "gap_rel": gap,
                              "two_U": 2 * max(ua, ub_), "holds": gap > 2 * max(ua, ub_)}
            l4, ls = entry.get("4cycle"), entry.get("stabilised")
            entry["same_order"] = (l4["lower"] == ls["lower"]) if (l4 and ls) else None
            comps.append(entry)
    out["comparisons"] = comps
    return out


def main():
    if "--run" in sys.argv:
        C.run_tasks(tasks())
    if "--summarize" in sys.argv:
        from tcpmt_solder_collect import merge
        s = summarize()
        merge("stabilization", s)
        for k, r in s["cases"].items():
            print(k, r.get("v4"), r.get("v16"), r.get("v48"), r.get("U_cyc_stab"))
        for c in s["comparisons"]:
            print(c)


if __name__ == "__main__":
    main()
