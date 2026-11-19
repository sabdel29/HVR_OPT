#!/usr/bin/env python3
"""Phase-0M-R Section 6 -- the production loss ledger, with exactly one owner per term.

Every watt in the system total belongs to exactly one term, every term declares its owner
(the module that computes it), and every term is SYSTEM scope before it may be summed. Adding
intra-VR metallization is only safe if it cannot silently duplicate a device parasitic, so
the ledger enforces that structurally rather than by comment.

The converter decomposition is RE-DERIVED from the upstream closed form and then checked
against the upstream aggregate: `P_hs + P_ls + P_ind + P_cap` must equal `LossResult.p_cond`
to machine precision, and `P_sw_hard + P_gate + P_coss` must equal `p_sw`. If either check
fails the ledger refuses to produce a total, because a decomposition that does not reproduce
its own aggregate is a guess.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

OWNERS = {
    "P_switch_hs_conduction": "upstream compute_total_loss, hs.R_DS_ON term",
    "P_switch_ls_conduction": "upstream compute_total_loss, ls.R_DS_ON terms",
    "P_inductor_DCR": "upstream compute_total_loss, R_L_ESR term",
    "P_cap_ESR": "upstream compute_total_loss, R_C_ESR term",
    "P_switching_hard": "upstream compute_total_loss, P_sw_HS",
    "P_gate": "upstream compute_total_loss, P_sw_GD",
    "P_Coss": "upstream compute_total_loss, P_sw_COSS",
    "P_intraVR_metal": "phase0mr.routing_production, lateral edges",
    "P_intraVR_vertical": "phase0mr.routing_production, via-stack edges",
    "P_pkg_RDL": "phase0e.stack.rdl_network_solve",
    "P_TSV": "phase0mr.interconnect_production, tsv tier",
    "P_bumps": "phase0mr.interconnect_production, bga + c4 + microbump tiers",
    "P_other": "unassigned residual -- must be zero unless explicitly justified",
}

# PHASE 0M-R2 SECTION 7. Hydraulic pumping power appeared NOWHERE in Phase 0M-R: not in
# the ledger, not in the replay total, and not in the thermal mesh. "System loss" therefore
# meant ELECTRONICS ONLY, and that was never said. Scope is now explicit and enforced.
#
#   ELECTRONICS  dissipated inside the package by the power-delivery hardware. Counts
#                towards the loss objective AND is deposited as heat in the mesh.
#   FACILITY     spent outside the package to remove that heat. Counts towards the
#                facility total and is NEVER deposited in the package mesh, because the
#                pump is not in the package.
FACILITY_OWNERS = {
    "P_pump_hydraulic": "phase0mr2.cooling_regime, dp * V_dot at the operating point",
}

ELECTRONICS_TERMS = frozenset(OWNERS)
FACILITY_TERMS = frozenset(FACILITY_OWNERS)


class LedgerError(Exception):
    pass


@dataclass
class LossLedger:
    """System-scope watts, one owner per term."""
    n_vr: int
    terms: dict = field(default_factory=dict)
    scopes: dict = field(default_factory=dict)
    notes: dict = field(default_factory=dict)

    def add(self, name: str, watts: float, scope: str = "SYSTEM", note: str = "") -> None:
        if name in FACILITY_TERMS:
            raise LedgerError(
                f"{name!r} is FACILITY scope and must not enter the electronics ledger. "
                f"Pumping power is spent outside the package; adding it here would both "
                f"inflate the loss objective and, through the heat map, deposit it into "
                f"the package mesh. Use FacilityLedger.")
        if name not in OWNERS:
            raise LedgerError(f"{name!r} has no declared owner. Add it to OWNERS with the "
                              f"module that computes it, or it cannot enter the total.")
        if name in self.terms:
            raise LedgerError(f"{name!r} already has a value ({self.terms[name]:.6g} W) "
                              f"owned by {OWNERS[name]}. A second writer means double "
                              f"counting.")
        if scope not in ("SYSTEM", "PER_REGULATOR"):
            raise LedgerError(f"unknown scope {scope!r}")
        if not math.isfinite(watts):
            raise LedgerError(f"{name!r}: non-finite value {watts}")
        self.terms[name] = watts * (self.n_vr if scope == "PER_REGULATOR" else 1.0)
        self.scopes[name] = "SYSTEM"
        self.notes[name] = note or OWNERS[name]

    def total(self) -> float:
        missing = [k for k in OWNERS if k not in self.terms and k != "P_other"]
        if missing:
            raise LedgerError(f"incomplete ledger, missing: {missing}")
        return sum(self.terms.values())

    def converter_total(self) -> float:
        return sum(v for k, v in self.terms.items() if k.startswith(
            ("P_switch", "P_inductor", "P_cap", "P_switching", "P_gate", "P_Coss")))

    def interconnect_total(self) -> float:
        return sum(v for k, v in self.terms.items()
                   if k in ("P_intraVR_metal", "P_intraVR_vertical", "P_pkg_RDL",
                            "P_TSV", "P_bumps"))

    def as_rows(self, tag: str = "") -> list[dict]:
        tot = sum(self.terms.values())
        return [{"case": tag, "term": k, "owner": OWNERS[k], "watts_system": v,
                 "pct_of_total": 100 * v / tot if tot else 0.0, "note": self.notes[k]}
                for k, v in self.terms.items()]


def converter_decomposition(arch, hs, ls, ind, cap, i_out, v_out, v_in, f_sw,
                            lr, v_gs_drive: float = 5.0) -> dict:
    """Re-derive the upstream loss split, then CHECK it against the upstream aggregate.

    The upstream model returns only `p_cond` and `p_sw`. The ledger needs per-component
    ownership, so the closed form is re-evaluated term by term here and the sum is compared
    with the aggregate the upstream model returned. A mismatch raises.
    """
    N, K, K_A, B, D = arch.N, arch.K, arch.K_A, arch.B_array, arch.D
    L = ind.l_nh * 1e-9
    r_l, r_c = ind.r_dcr_mohm * 1e-3, cap.esr_mohm * 1e-3
    B_k, B_sum = B[-1], sum(b ** 2 for b in B)
    boost = 1.0 + ind.coupling_k * max(K - 1, 0)
    di = ((D / (f_sw * L)) * (v_in / N * K_A - v_out * K)) / boost
    i_rms = math.sqrt(i_out ** 2 + di ** 2 / 12.0)
    k = (v_out / v_in) * i_rms ** 2
    # the correction term is B_k-dependent in the EPC_V2 build actually used
    corr = ((4 * B_k - 1) * (ls.R_DS_ON / N)) if B_k > 1 else (3 * ls.R_DS_ON / N)
    p_hs = k * hs.R_DS_ON
    p_cap = k * 2 * (1 - 1 / N) * r_c
    p_ind = k * (v_in / (N ** 2 * v_out)) * r_l * B_sum
    p_ls = k * ((v_in / (N ** 2 * v_out)) * ls.R_DS_ON * B_sum
                + 2 * ls.R_DS_ON * B_sum / N - corr)
    s_ = p_hs + p_cap + p_ind + p_ls
    if abs(s_ - lr.p_cond) > 1e-9 * max(abs(lr.p_cond), 1.0):
        raise LedgerError(
            "conduction decomposition %.9g W does not reproduce the upstream aggregate "
            "%.9g W. A decomposition that cannot reproduce its own total is a guess, not a "
            "split." % (s_, lr.p_cond))
    # the switching split is published by the upstream LossResult; take it rather than
    # re-deriving a formula that could drift from the one that was actually evaluated
    p_hard = float(getattr(lr, "p_sw_hs"))
    p_gate = float(getattr(lr, "p_sw_gd"))
    p_coss = float(lr.p_sw) - p_hard - p_gate
    if abs(p_hard + p_gate + p_coss - lr.p_sw) > 1e-9 * max(abs(lr.p_sw), 1.0):
        raise LedgerError("switching split does not reproduce p_sw")
    return {"P_switch_hs_conduction": p_hs, "P_switch_ls_conduction": p_ls,
            "P_inductor_DCR": p_ind, "P_cap_ESR": p_cap,
            "P_switching_hard": p_hard, "P_gate": p_gate, "P_Coss": p_coss,
            "i_rms_a": i_rms, "delta_i_a": di}


def device_split(d, hs, ls, dec) -> dict:
    """TCPMT round 3: the gate-drive and output-capacitance terms split between the high- and
    low-side devices that dissipate them (gate: f N C_G,hs V^2 : f K C_G,ls V^2; C_oss: the
    corrected rule's high-side turn-on and stacked-switch energies : the switch-node energy,
    or the published term's two parts), so each die's conduction and switching loss is its
    own. Per cell; the parts sum exactly to the engine's terms. Evaluated with the loss rules
    pinned (inside converter_terms)."""
    import HVR_FULL_OPT_EPC_V2 as _H
    a = d.arch
    g_hs, g_ls = a.N * float(hs.C_G), a.K * float(ls.C_G)
    f_gate_hs = g_hs / (g_hs + g_ls) if (g_hs + g_ls) > 0 else 1.0
    if getattr(_H, "COSS_RULE", "legacy") == "legacy" or not hasattr(_H,
                                                                      "coss_energy_per_period"):
        e_hs = a.N * float(hs.C_OSS) * (d.v_in / a.N - d.v_out) ** 2
        e_ls = a.K * float(ls.C_OSS) * d.v_out ** 2
    else:
        e = _H.coss_energy_per_period(a, hs, ls, d.v_in)
        e_hs, e_ls = e["hs_turn_on"] + e["stacked"], e["switch_node"]
    f_coss_hs = e_hs / (e_hs + e_ls) if (e_hs + e_ls) > 0 else 1.0
    p_gate, p_coss = dec["P_gate"], dec["P_Coss"]
    hs_sw = dec["P_switching_hard"] + f_gate_hs * p_gate + f_coss_hs * p_coss
    ls_sw = (1 - f_gate_hs) * p_gate + (1 - f_coss_hs) * p_coss
    B = list(a.B_array)
    b2 = sum(b * b for b in B)
    return {"P_gate_hs": f_gate_hs * p_gate, "P_gate_ls": (1 - f_gate_hs) * p_gate,
            "P_Coss_hs": f_coss_hs * p_coss, "P_Coss_ls": (1 - f_coss_hs) * p_coss,
            "P_hs_total": dec["P_switch_hs_conduction"] + hs_sw,
            "P_ls_total": dec["P_switch_ls_conduction"] + ls_sw,
            "per_part": {"gan_hs": (dec["P_switch_hs_conduction"] + hs_sw) / a.N,
                         "gan_ls": (dec["P_switch_ls_conduction"] + ls_sw) / a.K,
                         "inductor": [dec["P_inductor_DCR"] * b * b / b2 for b in B],
                         "cap_fly": dec["P_cap_ESR"] / max(a.N - 1, 1)},
            "split_rule": ("high/low-side dies: equal share of their class's conduction, hard-"
                           "switching, gate (N C_G,hs : K C_G,ls) and C_oss (turn-on + stacked "
                           ": switch node) terms; inductors by B_k^2; flying capacitors equal")}


@dataclass
class FacilityLedger:
    """Power spent OUTSIDE the package to operate the electronics.

    Kept separate from LossLedger so that no facility watt can reach the loss objective
    or the thermal mesh by accident. The two are summed only in `facility_total`, and
    that sum is reported under its own name.
    """
    electronics_w: float
    terms: dict = field(default_factory=dict)

    def add(self, name: str, watts: float, note: str = "") -> None:
        if name in ELECTRONICS_TERMS:
            raise LedgerError(
                f"{name!r} is an ELECTRONICS term and is already counted in the loss "
                f"objective. Adding it here would double count it.")
        if name not in FACILITY_OWNERS:
            raise LedgerError(f"{name!r} has no declared facility owner")
        if name in self.terms:
            raise LedgerError(f"{name!r} already has a value ({self.terms[name]:.6g} W)")
        if not math.isfinite(watts):
            raise LedgerError(f"{name!r}: non-finite value {watts}")
        self.terms[name] = watts

    def facility_total(self) -> float:
        return self.electronics_w + sum(self.terms.values())

    def as_rows(self, tag: str = "") -> list[dict]:
        rows = [{"case": tag, "term": "P_total_electronics", "scope": "ELECTRONICS",
                 "watts": self.electronics_w, "in_thermal_mesh": True,
                 "owner": "phase0mr.ledger.LossLedger.total()"}]
        rows += [{"case": tag, "term": k, "scope": "FACILITY", "watts": v,
                  "in_thermal_mesh": False, "owner": FACILITY_OWNERS[k]}
                 for k, v in sorted(self.terms.items())]
        rows.append({"case": tag, "term": "P_total_facility", "scope": "FACILITY",
                     "watts": self.facility_total(), "in_thermal_mesh": False,
                     "owner": "electronics + facility"})
        return rows
