"""TCPMT revision -- Z1 local input decoupling: requirement and circuit verification.

The S0 scenario takes the current in Z1's package 48 V network as smooth (k = I_rms/I_avg = 1)
on the premise of "sufficient local input capacitance". This module states what that takes.

WAVEFORM. The cell draws input current only in phase A (manuscript Fig. 2; HVR_FULL_OPT_EPC_V2
N3K3K_A2): S1 conducts L1's current, which ramps from I_L - dI/2 to I_L + dI/2 across the
on-interval because L1 sees V_mid - V_out = 15 V; dI is the uncoupled branch ripple
V_out (1 - D) T / L (coupling_k = 0 in the design). The pulse is scaled to the S0 ledger's
input current (23.84 A / 49 = 0.4865 A per cell): with I_L = 20.41/3 A the on-interval is
D_eff = I_avg / I_L = 0.0715 (losses lengthen the 0.0625 duty), edges 1 ns.

CIRCUIT (one cell with its 1/49 share of the network; exact when the 49 cells switch in
phase, which is what the scenario k describes):

    board node (ideal 48 V) --[49 R_loop, 49 L_loop]-- B --[C_B]-- gnd
                                                       B -->-- i_cell(t)
                                                       B --[L_conn + ESL/N, ESR(f)/N, N C]-- gnd

  R_loop  the package 48 V network at the converged S0 temperatures: both RDL sheets
          (package_network.json, 2.26 mOhm at 20 C), both BGA rails and the TSV field, as the
          S0 ledger evaluates them (3.12 mOhm)
  L_loop  loop inductance back to the board node, ESTIMATED (loop_inductance_estimate) and
          SWEPT (1 pH - 3 nH)
  C       DC-bias- and temperature-derated capacitance built from N real parts (datasheet
          R(f) and ESL at 48 V; tcpmt_decap_parts)
  C_B     the switch-node-side pad/device capacitance (2 nF), only so the time-domain model
          is well posed with two inductive branches at one node; the frequency-domain result
          is shown to be insensitive to it

Two independent solutions: periodic steady state in the frequency domain (each harmonic of
the measured-shape pulse through the exact transfer functions) and a time-domain state-space
integration (first-order-hold discretisation, many periods to steady state, plus the start-up
transient). They must agree; the comparison is recorded.

    python tcpmt_decap_circuit.py       writes the 'circuit' section of
                                        research/tcpmt_revision/input_decoupling.json
"""
from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

OUT = R / "research" / "tcpmt_revision"
JSON_OUT = OUT / "input_decoupling.json"
CASE_S0 = R / "research" / "final_closure" / "etm_Z1_HV_S0_h1.1_r21.json"
NETWORK = R / "research" / "final_closure" / "package_network.json"
N_CELL = 49
MU0 = 4e-7 * math.pi
T_EDGE_S = 1.0e-9           # switching edge (sensitivity 0.5 - 5 ns)
C_NODE_F = 2.0e-9           # switch-node-side capacitance, time-domain well-posedness only
N_HARM = 256                # harmonics carried (206 MHz); sensitivity recorded
L_SWEEP_PH = (1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0)
C_SWEEP_UF = tuple(float(x) for x in np.round(np.logspace(-2, np.log10(30.0), 49), 5))
RIPPLE_V = (0.5, 1.0, 2.0)


# ------------------------------------------------------------------ design and network
@lru_cache(maxsize=1)
def design():
    """Converter and operating-point numbers, all from the framework's own sources."""
    import rms_currents as RMS
    c = RMS.cell_currents()
    s0 = json.loads(CASE_S0.read_text())
    i_avg = s0["i_hv_avg_a"] / N_CELL
    i_l = c["i_cell_out_avg_a"] / c["K"]
    return {"f_sw_hz": float(c["f_sw_hz"]), "D": float(c["D"]), "L_H": c["L_nH"] * 1e-9,
            "v_mid": float(c["v_mid"]), "v_out": float(c["v_out"]), "v_in": float(c["v_in"]),
            "I_L_a": float(i_l), "I_in_avg_a": float(i_avg),
            "I_in_total_a": float(s0["i_hv_avg_a"]), "D_eff": float(i_avg / i_l),
            "coupling_k": float(c["coupling_k"]),
            "source": "rms_currents.cell_currents(); I_in from " + CASE_S0.name}


def s0_temperatures():
    """The ledger temperatures of the final S0 ledger (the E-T iteration that produced the
    recorded 144.3 W: its input temperatures are the previous iteration's output)."""
    s0 = json.loads(CASE_S0.read_text())
    h = s0["et_history"][-2]
    keys = ("conv", "hs", "ls", "ind", "caps", "bga", "sub", "interface")
    return {k: float(h[f"T_{k}_C"]) for k in keys if f"T_{k}_C" in h}


@lru_cache(maxsize=1)
def network_resistance():
    """Package 48 V loop resistance (total-current basis), cold and at the converged S0
    temperatures, exactly as the S0 ledger evaluates its rows."""
    s0 = json.loads(CASE_S0.read_text())
    rows = {r["term"]: r for r in s0["ledger_rows"]}
    pn = json.loads(NETWORK.read_text())["loop"]["Z1"]
    hot = {k: float(rows[k]["R_ohm"]) for k in ("P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return",
                                                "P_BGA_supply", "P_BGA_return",
                                                "P_TSV_VDD", "P_TSV_GND")}
    return {"sheet_loop_20C_ohm": float(pn["r_loop_ohm"]),
            "sheet_supply_20C_ohm": float(pn["r_supply_ohm"]),
            "sheet_return_20C_ohm": float(pn["r_return_ohm"]),
            "rows_at_S0_temperature_ohm": hot,
            "loop_hot_ohm": float(sum(hot.values())),
            "loop_cold_ohm": float(pn["r_loop_ohm"] + (hot["P_BGA_supply"]
                                                       + hot["P_BGA_return"]) / 1.3),
            "note": "hot = sum of the S0 ledger's own R_ohm (sheets, BGA, TSV) at the converged "
                    "temperatures; cold uses the 20 C sheets (BGA rescaled approximately)"}


def loop_inductance_estimate():
    """Order-of-magnitude loop inductance of the package 48 V path back to the board node,
    total-current basis, from the geometry the framework uses:

      sheets   supply and return planes over each other (RDL dielectric h_d, 5-20 um):
               L = mu0 h_d N_sq, N_sq = R_loop / (2 R_sq) -- same 2-D flow as the resistance
      BGA      the supply balls are the 54 lattice sites nearest the centre (radius r1) and
               the return balls the next 54 (to r2), so between r1 and r2 the loop closes
               through the ball height and the board's vias to its 48 V plane pair:
               L = mu0 (h_ball + h_via) / (2 pi) ln(r2 / r1)
      board    plane-pair spreading from board decoupling at r_b: mu0 h_p/(2 pi) ln(r_b / r1)
    """
    import pkg_rdl_network as K
    pn = json.loads(NETWORK.read_text())
    loop = pn["loop"]["Z1"]
    r_sq = K.sheet_resistance_ohm_sq(5.0e-3, 0.30, 20.0)
    n_sq = loop["r_loop_ohm"] / (2.0 * r_sq)
    xy_s = np.array(pn["convergence"]["Z1_supply"]["ball_xy"])
    xy_r = np.array(pn["convergence"]["Z1_return"]["ball_xy"])
    r1 = float(np.sqrt((xy_s ** 2).sum(1)).max() + 0.2)          # supply cluster edge, mm
    r2 = float(np.sqrt((xy_r ** 2).sum(1)).max() + 0.2)          # return ring edge, mm
    out = {"R_sq_ohm": r_sq, "N_sq_effective": n_sq, "r_supply_cluster_mm": r1,
           "r_return_ring_mm": r2, "components_pH": {}}
    for h_d in (5e-6, 10e-6, 20e-6):
        out["components_pH"][f"sheets_h{h_d * 1e6:g}um"] = MU0 * h_d * n_sq * 1e12
    for h_v in (0.1e-3, 0.5e-3, 1.2e-3):
        out["components_pH"][f"bga_radial_via{h_v * 1e3:g}mm"] = (
            MU0 * (0.3e-3 + h_v) / (2 * math.pi) * math.log(r2 / r1) * 1e12)
    for r_b in (15.0, 25.0, 50.0):
        out["components_pH"][f"board_planes_to_r{r_b:g}mm"] = (
            MU0 * 0.1e-3 / (2 * math.pi) * math.log(r_b / r1) * 1e12)
    c = out["components_pH"]
    out["nominal_pH"] = (c["sheets_h10um"] + c["bga_radial_via0.5mm"]
                         + c["board_planes_to_r25mm"])
    out["plausible_band_pH"] = [c["sheets_h5um"] + c["bga_radial_via0.1mm"],
                                c["sheets_h20um"] + c["bga_radial_via1.2mm"]
                                + c["board_planes_to_r50mm"] + 500.0]
    out["note"] = ("nominal = sheets (10 um) + BGA with 0.5 mm of board via + planes to board "
                   "decoupling at 25 mm; the band's upper end adds 0.5 nH for board-capacitor "
                   "mounting/ESL. The sweep (1 pH - 3 nH) covers it with margin.")
    return out


# ------------------------------------------------------------------ waveform
def phase_a_current(mode="ramp_deff", n=2 ** 14, t_edge=T_EDGE_S, d=None):
    """One period of the cell's 48 V input current (A) on n samples, average = I_in_avg.

    ramp_deff  the inductor ramp over the loss-lengthened on-interval D_eff (nominal)
    ramp_D     the same ramp over the nominal D = 0.0625, scaled up to the same average
    rect_D     the scenario S1 shape: a flat pulse at D (k = 1/sqrt(D) = 4)
    """
    d = d or design()
    T = 1.0 / d["f_sw_hz"]
    t = np.arange(n) * T / n
    duty = d["D"] if mode in ("ramp_D", "rect_D") else d["D_eff"]
    ton = duty * T
    if mode == "rect_D":
        i = np.where(t < ton, 1.0, 0.0)
    else:
        di = d["v_out"] * (1.0 - duty) * T / d["L_H"]
        ramp = d["I_L_a"] - di / 2 + di * t / ton
        i = np.where(t < ton, ramp, 0.0)
        rise = t < t_edge
        i[rise] *= t[rise] / t_edge
        fall = (t >= ton) & (t < ton + t_edge)
        i[fall] = (d["I_L_a"] + di / 2) * (1.0 - (t[fall] - ton) / t_edge)
    i *= d["I_in_avg_a"] / i.mean()
    return t, i


def harmonics(i):
    """Complex peak amplitudes: i(t) = Re sum_n I_n exp(j n w t), I_0 = mean."""
    n = len(i)
    F = np.fft.rfft(i) / n
    F[1:] *= 2.0
    return F


def k_of(I):
    return float(np.sqrt(abs(I[0]) ** 2 + np.sum(np.abs(I[1:]) ** 2) / 2.0) / abs(I[0]))


def charge_requirement(mode="ramp_deff"):
    """Charge the local capacitor must swing if the network delivers only the average:
    q(t) = int (I_avg - i) dt; C = Q_pp / dV."""
    d = design()
    t, i = phase_a_current(mode)
    dt = t[1] - t[0]
    q = np.cumsum(d["I_in_avg_a"] - i) * dt
    qpp = float(q.max() - q.min())
    T = 1.0 / d["f_sw_hz"]
    duty = d["D"] if mode != "ramp_deff" else d["D_eff"]
    return {"waveform": mode, "Q_pp_C": qpp,
            "closed_form_Q_C": d["I_in_avg_a"] * (1.0 - duty) * T,
            "C_req_uF": {f"{v:g}V": qpp / v * 1e6 for v in RIPPLE_V},
            "C_req_total_uF": {f"{v:g}V": N_CELL * qpp / v * 1e6 for v in RIPPLE_V}}


# ------------------------------------------------------------------ frequency domain
class Shunt:
    """N parallel capacitors of one part type plus a shared connection inductance."""

    def __init__(self, c_f, esr_fn, esl_h, l_conn_h, label=""):
        self.c, self.esr_fn, self.esl, self.l_conn, self.label = c_f, esr_fn, esl_h, l_conn_h, label

    def z(self, f):
        f = np.asarray(f, float)
        w = 2 * np.pi * f
        with np.errstate(divide="ignore"):
            return self.esr_fn(f) + 1j * w * (self.esl + self.l_conn) + 1.0 / (1j * w * self.c)


def generic_shunt(c_uf, l_conn_h=0.3e-9, ref=None, t_factor=1.0):
    """C_uF (derated) built from N = C / C_ref parts of the reference type (default: the 1206
    100 V X7S part, the best capacitance per volume at 48 V in tcpmt_decap_parts), each with
    its datasheet R(f) and ESL at 48 V."""
    import tcpmt_decap_parts as PA
    data = PA.load()
    rec = data["parts"][ref or "GRM31CC72A475KE11"]
    c_ref = PA.c_at_bias(rec, 48.0) * t_factor * 1e-6
    n = (c_uf * 1e-6) / c_ref
    _f0, esl_srf, esl_hf = PA.srf_esl(rec)
    esl = esl_srf
    return Shunt(c_uf * 1e-6, lambda f: PA.esr_at(rec, np.maximum(f, 1e3)) / n, esl / n,
                 l_conn_h, label=f"{n:.3g} x {rec['part']}")


def solve_fd(I_cell, f_sw, r_net, l_net, shunt, c_node=0.0, n_harm=N_HARM):
    """Per-cell network current, capacitor current and node ripple for each harmonic."""
    n = np.arange(len(I_cell))[: n_harm + 1]
    I = I_cell[: n_harm + 1]
    f = n * f_sw
    w = 2 * np.pi * f
    zn = r_net + 1j * w * l_net
    zs = shunt.z(np.where(f > 0, f, 1.0))
    yb = 1j * w * c_node
    # node B: (V_B - V_board)/zn + V_B/zs + V_B*yb + I = 0  (AC part, V_board AC = 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        vb = -I / (1.0 / zn + 1.0 / zs + yb)
    vb[0] = -I[0] * r_net                         # DC: the capacitor blocks, network carries all
    i_net = -vb / zn
    i_net[0] = I[0]
    i_cap = vb / zs
    i_cap[0] = 0.0
    return {"f": f, "I_cell": I, "I_net": i_net, "I_cap": i_cap, "V_B": vb}


def summarize_fd(sol, shunt, f_sw, n_t=4096):
    I_net, I_cap, vb = sol["I_net"], sol["I_cap"], sol["V_B"]
    k_net = k_of(I_net)
    t = np.arange(n_t) / n_t / f_sw
    n = np.arange(len(vb))
    ph = np.exp(1j * 2 * np.pi * f_sw * np.outer(t, n))
    v_t = np.real(ph[:, 1:] @ vb[1:])
    v_sw = np.real(ph[:, 1:21] @ vb[1:21])            # switching ripple, <= 20 f_sw
    i_cap_rms = float(np.sqrt(np.sum(np.abs(I_cap[1:]) ** 2) / 2.0))
    esr = shunt.esr_fn(np.maximum(sol["f"][1:], 1e3))
    p_esr = float(np.sum(np.abs(I_cap[1:]) ** 2 / 2.0 * esr))
    return {"k_net": k_net, "ripple_sw_pp_V": float(v_sw.max() - v_sw.min()),
            "ripple_pp_V": float(v_t.max() - v_t.min()),
            "I_cap_rms_A": i_cap_rms, "P_esr_cell_W": p_esr, "P_esr_total_W": N_CELL * p_esr,
            "I_net_rms_A": float(np.sqrt(abs(I_net[0]) ** 2 + np.sum(np.abs(I_net[1:]) ** 2) / 2))}


def resonance(r_net, l_net, shunt, f_lo=1e4, f_hi=3e8, n=4000):
    """Peak of |I_net / I_cell| over frequency (the current gain of the network branch)."""
    f = np.logspace(np.log10(f_lo), np.log10(f_hi), n)
    zn = r_net + 1j * 2 * np.pi * f * l_net
    zs = shunt.z(f)
    h = np.abs(zs / (zs + zn))
    i = int(np.argmax(h))
    f_lc = 1.0 / (2 * np.pi * math.sqrt((l_net + shunt.esl + shunt.l_conn) * shunt.c))
    return {"f_peak_MHz": float(f[i] / 1e6), "gain_peak": float(h[i]),
            "f_LC_MHz": float(f_lc / 1e6), "amplifying": bool(h[i] > 1.0 + 1e-9)}


# ------------------------------------------------------------------ time domain
def solve_td(i_period, f_sw, r_net, l_net, c, esr, l_s, c_node=C_NODE_F, periods=60,
             v_in=48.0, startup=False):
    """State-space x = [i_net, i_cap, v_c, v_B], exact first-order-hold update (the source is
    linear between samples):  x[k+1] = Phi x[k] + G0 u[k] + G1 (u[k+1] - u[k]), with Phi,
    G0, G1 from one matrix exponential of the augmented system. Returns the last period
    (steady state) and the first period when startup=True (capacitor pre-charged to the
    input voltage, load applied at t = 0)."""
    from scipy.linalg import expm
    A = np.array([[-r_net / l_net, 0.0, 0.0, -1.0 / l_net],
                  [0.0, -esr / l_s, -1.0 / l_s, 1.0 / l_s],
                  [0.0, 1.0 / c, 0.0, 0.0],
                  [1.0 / c_node, -1.0 / c_node, 0.0, 0.0]])
    B = np.array([[1.0 / l_net, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, -1.0 / c_node]])
    n = len(i_period)
    dt = 1.0 / f_sw / n
    M = np.zeros((8, 8))
    M[:4, :4], M[:4, 4:6], M[4:6, 6:8] = A * dt, B * dt, np.eye(2)
    E = expm(M)
    Phi, G0, G1 = E[:4, :4], E[:4, 4:6], E[:4, 6:8]
    # initial state: DC operating point with the average load
    i0 = float(np.mean(i_period))
    x = np.array([i0, 0.0, v_in - r_net * i0, v_in - r_net * i0])
    if startup:
        x = np.array([0.0, 0.0, v_in, v_in])
    src = np.concatenate([i_period, i_period[:1]])
    u = np.stack([np.full(n + 1, v_in), src], axis=1)
    du = u[1:] - u[:-1]
    drive = u[:-1] @ G0.T + du @ G1.T
    first, hist_k = None, []
    for p in range(periods):
        X = np.empty((n, 4))
        for k in range(n):
            X[k] = x
            x = Phi @ x + drive[k]
        if p == 0:
            first = X.copy()
        hist_k.append(float(np.sqrt(np.mean(X[:, 0] ** 2)) / np.mean(X[:, 0])))
    i_net, i_cap, v_c, v_b = X.T
    return {"i_net": i_net, "i_cap": i_cap, "v_B": v_b, "first_period": first,
            "k_by_period": hist_k,
            "k_net": hist_k[-1], "ripple_pp_V": float(v_b.max() - v_b.min()),
            "I_cap_rms_A": float(np.sqrt(np.mean(i_cap ** 2))),
            "P_esr_cell_W": float(esr * np.mean(i_cap ** 2))}


# ------------------------------------------------------------------ studies
def nominal_network(hot=True):
    nr = network_resistance()
    return N_CELL * (nr["loop_hot_ohm"] if hot else nr["loop_cold_ohm"])


def sweep(mode="ramp_deff", hot=True, l_conn_h=0.3e-9):
    d = design()
    _t, i = phase_a_current(mode)
    I = harmonics(i)
    r = nominal_network(hot)
    rows = []
    for lp in L_SWEEP_PH:
        for c_uf in C_SWEEP_UF:
            sh = generic_shunt(c_uf, l_conn_h)
            sol = solve_fd(I, d["f_sw_hz"], r, N_CELL * lp * 1e-12, sh)
            row = {"L_loop_pH": lp, "C_uF_per_cell": c_uf}
            row.update(summarize_fd(sol, sh, d["f_sw_hz"]))
            row.update(resonance(r, N_CELL * lp * 1e-12, sh))
            rows.append(row)
    return rows


def c_for_k(rows, k_target):
    """Smallest swept C (interpolated, log) reaching k_net <= k_target, per L_loop."""
    out = {}
    for lp in L_SWEEP_PH:
        rr = [r for r in rows if r["L_loop_pH"] == lp]
        cs = np.array([r["C_uF_per_cell"] for r in rr])
        ks = np.array([r["k_net"] for r in rr])
        # the first C beyond which every larger C also meets the target (resonance-safe)
        idx = None
        for j in range(len(ks)):
            if np.all(ks[j:] <= k_target):
                idx = j
                break
        if idx is None:
            out[f"{lp:g}"] = None
        elif idx == 0:
            out[f"{lp:g}"] = float(cs[0])
        else:
            c0, c1, k0, k1 = cs[idx - 1], cs[idx], ks[idx - 1], ks[idx]
            x = (k0 - k_target) / (k0 - k1)
            out[f"{lp:g}"] = float(np.exp(np.log(c0) + x * (np.log(c1) - np.log(c0))))
    return out


def verification(c_uf=1.0, l_loop_ph=100.0, l_conn_h=0.3e-9):
    """Frequency- vs time-domain agreement at one point, with a constant ESR (the time-domain
    model cannot carry ESR(f)); and the frequency-domain sensitivity to C_B, N_HARM, edges."""
    d = design()
    f = d["f_sw_hz"]
    r = nominal_network(True)
    sh_g = generic_shunt(c_uf, l_conn_h)
    esr_c = float(sh_g.esr_fn(np.array([2 * f]))[0])
    sh = Shunt(sh_g.c, lambda x: np.full_like(np.asarray(x, float), esr_c), sh_g.esl,
               sh_g.l_conn)
    t, i = phase_a_current("ramp_deff", n=2 ** 13)
    I = harmonics(i)
    fd = summarize_fd(solve_fd(I, f, r, N_CELL * l_loop_ph * 1e-12, sh, c_node=C_NODE_F,
                               n_harm=len(I) - 1), sh, f)
    td = solve_td(i, f, r, N_CELL * l_loop_ph * 1e-12, sh.c, esr_c, sh.esl + sh.l_conn,
                  periods=40)
    st = solve_td(i, f, r, N_CELL * l_loop_ph * 1e-12, sh.c, esr_c, sh.esl + sh.l_conn,
                  periods=3, startup=True)
    fp = st["first_period"]
    sens = {}
    t2, i2 = phase_a_current("ramp_deff")
    I2 = harmonics(i2)
    base = summarize_fd(solve_fd(I2, f, r, N_CELL * l_loop_ph * 1e-12, sh_g), sh_g, f)
    sens["no_C_B"] = base["k_net"]
    sens["C_B_2nF"] = summarize_fd(solve_fd(I2, f, r, N_CELL * l_loop_ph * 1e-12, sh_g,
                                            c_node=C_NODE_F), sh_g, f)["k_net"]
    sens["N_harm_64"] = summarize_fd(solve_fd(I2, f, r, N_CELL * l_loop_ph * 1e-12, sh_g,
                                              n_harm=64), sh_g, f)["k_net"]
    sens["N_harm_2048"] = summarize_fd(solve_fd(I2, f, r, N_CELL * l_loop_ph * 1e-12, sh_g,
                                                n_harm=2048), sh_g, f)["k_net"]
    for te in (0.5e-9, 2e-9, 5e-9):
        _t3, i3 = phase_a_current("ramp_deff", t_edge=te)
        sens[f"edge_{te * 1e9:g}ns"] = summarize_fd(solve_fd(
            harmonics(i3), f, r, N_CELL * l_loop_ph * 1e-12, sh_g), sh_g, f)["k_net"]
    return {"point": {"C_uF_per_cell": c_uf, "L_loop_pH": l_loop_ph,
                      "L_conn_nH": l_conn_h * 1e9, "ESR_const_mohm": esr_c * 1e3,
                      "C_B_nF": C_NODE_F * 1e9},
            "frequency_domain": fd,
            "time_domain": {k: td[k] for k in ("k_net", "ripple_pp_V", "I_cap_rms_A",
                                               "P_esr_cell_W")},
            "time_domain_k_by_period_last5": td["k_by_period"][-5:],
            "rel_diff_k": abs(td["k_net"] - fd["k_net"]) / fd["k_net"],
            "rel_diff_ripple": abs(td["ripple_pp_V"] - fd["ripple_pp_V"]) / fd["ripple_pp_V"],
            "rel_diff_Icap": abs(td["I_cap_rms_A"] - fd["I_cap_rms_A"]) / fd["I_cap_rms_A"],
            "startup_first_period": {"i_net_peak_A": float(fp[:, 0].max()),
                                     "v_B_min_V": float(fp[:, 3].min()),
                                     "v_B_max_V": float(fp[:, 3].max())},
            "fd_sensitivity_k_net": sens}


def lconn_sensitivity(l_loop_ph=None):
    """k_net at the nominal loop inductance for three connection inductances."""
    d = design()
    l_loop_ph = l_loop_ph or loop_inductance_estimate()["nominal_pH"]
    _t, i = phase_a_current("ramp_deff")
    I = harmonics(i)
    r = nominal_network(True)
    out = {"L_loop_pH": l_loop_ph}
    for lc in (0.1, 0.3, 1.0):
        out[f"L_conn_{lc:g}nH"] = {
            f"{c:g}uF": summarize_fd(solve_fd(I, d["f_sw_hz"], r, N_CELL * l_loop_ph * 1e-12,
                                              generic_shunt(c, lc * 1e-9)),
                                     generic_shunt(c, lc * 1e-9), d["f_sw_hz"])["k_net"]
            for c in (0.56, 1.0, 3.0)}
    return out


def main():
    d = design()
    nr = network_resistance()
    lest = loop_inductance_estimate()
    out = {"design": d, "network_resistance": nr, "loop_inductance_estimate": lest}
    wf = {}
    for mode in ("ramp_deff", "ramp_D", "rect_D"):
        _t, i = phase_a_current(mode)
        wf[mode] = {"k_open": k_of(harmonics(i)), "I_peak_A": float(i.max()),
                    "I_avg_A": float(i.mean())}
    out["waveform"] = wf
    out["charge_balance"] = {m: charge_requirement(m) for m in ("ramp_deff", "rect_D")}
    rows = sweep("ramp_deff", hot=True)
    out["sweep"] = {"basis": "per cell, 49 cells in phase; R_net = 49 x hot loop; "
                             "C from N parts of GRM31CC72A475KE11 data at 48 V; "
                             "L_conn = 0.3 nH", "rows": rows}
    out["C_required_uF_per_cell"] = {f"k<={kt:g}": c_for_k(rows, kt)
                                     for kt in (1.05, 1.1, 1.2, 1.5, 2.0)}
    rows_cold = sweep("ramp_deff", hot=False)
    out["C_required_uF_per_cell_cold_network"] = {f"k<={kt:g}": c_for_k(rows_cold, kt)
                                                  for kt in (1.1, 1.2, 1.5)}
    out["verification"] = verification()
    out["L_conn_sensitivity_k_net"] = lconn_sensitivity()
    OUT.mkdir(parents=True, exist_ok=True)
    doc = json.loads(JSON_OUT.read_text()) if JSON_OUT.exists() else {}
    doc["circuit"] = out
    JSON_OUT.write_text(json.dumps(doc, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("waveform", "charge_balance",
                                          "C_required_uF_per_cell")}, indent=1,
                     default=lambda x: round(x, 4)))
    print(json.dumps(out["verification"], indent=1, default=float))
    print("L estimate:", json.dumps(lest, default=float))


if __name__ == "__main__":
    main()
