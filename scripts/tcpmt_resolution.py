"""THE comparison rule of the TCPMT revision (round 3): one rule for every compared output, every
comparison of Table IV (tcpmt_uncertainty) and every robustness verdict (final_closure_classB,
Fig. 11 fig_robustness, tcpmt_mech_variants.judge_B, tcpmt_z3land_report).

RULE: a difference D = y_b - y_a is RESOLVED when its bias-corrected value exceeds the
uncertainty of the difference at about 95 % coverage,  |D + beta_D| > U95(D).

DISCRETIZATION, GCI type (Roache 1998, Verification and Validation in Computational Science and
Engineering; Oberkampf & Roy 2010, Verification and Validation in Scientific Computing, 8.6).
Rungs of the production nested refinement: r11 (h = 1), r21 (h = 1/2, PRODUCTION), r31 (h = 1/3).
  e21 = y21 - y11, e32 = y31 - y21
  observed order p_obs: the positive root of (1 - 2^-p) / (2^-p - 3^-p) = e21 / e32 (none when
                the steps do not shrink like any positive order)
  ASYMPTOTIC    monotone (e21 e32 > 0) and |p_obs - P_FORMAL| <= 0.10 P_FORMAL (P_FORMAL = 2,
                trilinear hexahedra, nodal temperature and displacement)  ->  Fs = 1.25, p = p_obs
  NOT ASYMPTOTIC monotone otherwise  ->  Fs = 3, p = min(max(p_obs, 0.5), P_FORMAL)
                (p = 0.5 when there is no positive order)
  OSCILLATORY   e21 e32 < 0  ->  Fs = 3, no signed estimate, U = Fs (max - min) / 2 over the rungs
  bias (signed, production -> extrapolated)  beta = e32 r^p / (r^p - 1),  r = h21 / h31 = 1.5
  U_mesh = Fs |beta|
  The difference D is put through the SAME procedure on its own rung sequence D_r = y_b,r - y_a,r:
  errors the two cases share on one mesh family cancel where they move together, without a
  separate "paired" estimate. Through-thickness (r11 -> r12, two rungs, z refined by 2): Fs = 3 at
  P_FORMAL, beta_tt = (D12 - D11) 4/3, U_tt = 3 |beta_tt|.

OTHER COMPONENTS, as 95 % half-widths combined in quadrature with the discretization terms:
  the E-T stop of each case (0.1 % of the loss, 0.25 K of a temperature), the matched-reference
  agreement of the solver applied to the difference (0.13 % of a temperature difference, 0.43 %
  of a displacement difference), the local response's own numerical U of each case.
  U95(D) = sqrt(U_mesh^2 + U_tt^2 + U_et,a^2 + U_et,b^2 + U_ref^2 [+ U_loc,a^2 + U_loc,b^2])

JOINT RESPONSE: the solder-law band (tcpmt_mech_law_band -> solder_law_band.json) is part of the
resolution: the comparison is evaluated under EVERY law of the band; RESOLVED when it is resolved
with one sign under all of them, LAW-CONDITIONAL when it is resolved under the production law
only (or the sign changes between laws), NOT RESOLVED otherwise.

NO TRANSFER WITHOUT A CHECK. A case with a ladder of its own (r11, r21, r31) carries its own
beta and U. A case without one carries no U of its own: it is MARKED, and the ladder runs the
campaign must add are listed. A laddered reference's beta and U may be transferred to it only
as a PROVISIONAL estimate, and only when the transfer check passes:
  mesh       the case was solved on the reference's production mesh (same element and node
             counts at the same h_xy and rung)            -- checked from the case files now
  r11 step   once the case's r11 rung exists, its r11 -> r21 step must agree with the
             reference's within the reference U_mesh; failing it, the transfer is refused
A verdict on a transferred U is reported as provisional; with no transferable reference the
verdict is PENDING.
"""
from __future__ import annotations

import math

P_FORMAL = 2.0
ASYMPTOTIC_TOL = 0.10
FS_ASYMPTOTIC = 1.25
FS_NOT_ASYMPTOTIC = 3.0
P_MIN = 0.5
H = {"r11": 1.0, "r21": 0.5, "r31": 1.0 / 3.0}
R32 = H["r21"] / H["r31"]
TT_RATIO = 2.0
COVERAGE = ("about 95 %: GCI-type discretization bands (Roache; Fs = 1.25 asymptotic, 3 "
            "otherwise) and the other components as 95 % half-widths, in quadrature")
RULE = ("resolved when |D + beta_D| > U95(D): D the difference at the production mesh, beta_D "
        "its signed discretization bias and U95(D) the uncertainty of the difference (" +
        COVERAGE + "); the joint response must be resolved under every law of the solder-law "
        "band; a case without a ladder of its own carries no U (provisional only with a "
        "checked transfer)")
#: verdict vocabulary
RESOLVED, NOT_RESOLVED, LAW_CONDITIONAL, PENDING = ("resolved", "not resolved",
                                                    "law-conditional", "pending")


def observed_order(y11, y21, y31, h=(H["r11"], H["r21"], H["r31"])):
    """Observed order of three nested rungs, or None (non-monotone, or no positive order)."""
    e21, e32 = y21 - y11, y31 - y21
    if e21 == 0 or e32 == 0 or e21 * e32 < 0:
        return None
    target = e21 / e32
    f = lambda p: (h[0] ** p - h[1] ** p) / (h[1] ** p - h[2] ** p) - target
    lo, hi = 1e-3, 20.0
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(lo) * f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def gci(y11, y21, y31):
    """Production-rung (r21) discretization of a three-rung ladder: the class, the order used,
    Fs, the signed bias beta (production -> extrapolated) and U_mesh = Fs |beta|."""
    if None in (y11, y21, y31):
        return None
    e21, e32 = y21 - y11, y31 - y21
    base = {"y11": y11, "y21": y21, "y31": y31, "e21": e21, "e32": e32}
    if e21 * e32 < 0 or (e32 == 0 and e21 != 0):
        rng = max(y11, y21, y31) - min(y11, y21, y31)
        return {**base, "class": "oscillatory", "p_obs": None, "p": None,
                "Fs": FS_NOT_ASYMPTOTIC, "beta": 0.0, "beta_estimated": False,
                "U": FS_NOT_ASYMPTOTIC * 0.5 * rng, "y_corrected": y21}
    if e32 == 0:
        return {**base, "class": "converged", "p_obs": None, "p": None, "Fs": FS_ASYMPTOTIC,
                "beta": 0.0, "beta_estimated": True, "U": 0.0, "y_corrected": y21}
    p_obs = observed_order(y11, y21, y31)
    if p_obs is not None and abs(p_obs - P_FORMAL) <= ASYMPTOTIC_TOL * P_FORMAL:
        cls, p, fs = "asymptotic", p_obs, FS_ASYMPTOTIC
    else:
        cls = "not asymptotic"
        p = P_MIN if p_obs is None else min(max(p_obs, P_MIN), P_FORMAL)
        fs = FS_NOT_ASYMPTOTIC
    beta = e32 * R32 ** p / (R32 ** p - 1.0)
    return {**base, "class": cls, "p_obs": p_obs, "p": p, "Fs": fs, "beta": beta,
            "beta_estimated": True, "U": fs * abs(beta), "y_corrected": y21 + beta}


def gci_two_rung(y_coarse, y_fine, ratio=TT_RATIO):
    """Two-rung estimate (the through-thickness split): Fs = 3 at the formal order; the error of
    the COARSE value (the production z resolution)."""
    if None in (y_coarse, y_fine):
        return None
    beta = (y_fine - y_coarse) * ratio ** P_FORMAL / (ratio ** P_FORMAL - 1.0)
    return {"class": "two rungs", "p": P_FORMAL, "Fs": FS_NOT_ASYMPTOTIC, "beta": beta,
            "U": FS_NOT_ASYMPTOTIC * abs(beta)}


def quad(*u):
    """Quadrature sum of 95 % half-widths (None entries skipped)."""
    return math.sqrt(sum(float(x) ** 2 for x in u if x is not None))


def judge(d, beta, u95):
    """The rule on one difference: corrected value, ratio, resolved flag and the sign."""
    if d is None or u95 is None:
        return {"D": d, "bias": beta, "D_corrected": None, "U95": u95, "ratio": None,
                "resolved": None}
    ds = d + (beta or 0.0)
    return {"D": d, "bias": beta or 0.0, "D_corrected": ds, "U95": u95,
            "ratio": (abs(ds) / u95) if u95 > 0 else math.inf,
            "resolved": abs(ds) > u95}


def lower_of(a, b, d_corrected):
    """The case with the lower value when D = y_b - y_a is resolved."""
    return a if d_corrected > 0 else b


def law_band(per_law, production_law):
    """Joint-response resolution over the solder-law band. per_law: {law: (D, U95)}."""
    res = {law: judge(d, 0.0, u) for law, (d, u) in per_law.items() if d is not None}
    if not res or production_law not in res:
        return {"verdict": None, "per_law": res}
    signs = {math.copysign(1.0, r["D_corrected"]) for r in res.values()}
    all_res = all(r["resolved"] for r in res.values())
    if all_res and len(signs) == 1:
        v = RESOLVED
    elif res[production_law]["resolved"]:
        v = LAW_CONDITIONAL
    else:
        v = NOT_RESOLVED
    return {"verdict": v, "per_law": res, "laws": sorted(res),
            "sign_changes": len(signs) > 1,
            "worst_ratio": min(r["ratio"] for r in res.values())}


def transfer_check(case_mesh, ref_mesh, case_r11_step=None, ref_r11_step=None, ref_u_mesh=None):
    """May a laddered reference's beta / U stand (provisionally) for a case without a ladder?
    case_mesh / ref_mesh: (n_elems, n_nodes, h_xy, refine) of the production-mesh solves."""
    if not case_mesh or not ref_mesh or None in case_mesh or None in ref_mesh:
        return {"ok": False, "status": "refused: mesh of the case or reference not recorded"}
    if tuple(case_mesh) != tuple(ref_mesh):
        return {"ok": False, "status": f"refused: mesh differs from the reference "
                                       f"({case_mesh[:2]} vs {ref_mesh[:2]} elements, nodes)"}
    if case_r11_step is None:
        return {"ok": True, "status": "mesh identical; r11 step check pending (provisional)",
                "provisional": True}
    agree = ref_r11_step is not None and ref_u_mesh is not None and \
        abs(case_r11_step - ref_r11_step) <= ref_u_mesh
    return {"ok": bool(agree), "provisional": True,
            "status": ("mesh identical; r11 step agrees with the reference within its U_mesh"
                       if agree else "refused: r11 step differs from the reference by more "
                                     "than its U_mesh")}


def verdict_label(resolved, d_corrected, a, b, provisional=False):
    """'Z1 lower' / 'Z2 lower' / 'unresolved' (the robustness map's vocabulary)."""
    if resolved is None:
        return PENDING
    v = f"{lower_of(a, b, d_corrected)} lower" if resolved else "unresolved"
    return v
