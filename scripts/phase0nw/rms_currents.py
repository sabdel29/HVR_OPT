"""PHASE 0N-AC --- avg / RMS / peak currents per rail, with an explicit fidelity ladder.

WHY THIS EXISTS. The previous phase computed I^2 R using I_avg = P_in/48. Average current
closes ENERGY balance; RMS current closes CONDUCTION loss. They coincide only for a DC
waveform, and nothing had demonstrated that for any conductor here.

THE LADDER (brief section 5):

  RMS-L0  LOWER_BOUND_DC      I_rms = |I_avg|. Reproduces the Phase-0N-AB numbers and is
                              a strict lower bound for any non-DC waveform.
  RMS-L1  ANALYTIC            derived from the design's own duty, inductance, switching
                              frequency and branch grouping. Used where the waveform
                              shape is actually determined by those quantities.
  RMS-L2  TIME_DOMAIN         requires the SC switch-state sequence. NOT BUILT -- see
                              below.

WHAT L1 CAN AND CANNOT REACH.

The buck side is fully determined: the framework's own ledger already derives the
output ripple from D, f_sw, L, N, K and K_A, and a triangular inductor current has the
closed-form RMS sqrt(I_dc^2 + dI_pp^2/12). Branch currents follow from the B array and
the phase grouping. These are L1.

The 48 V INPUT current is NOT determined by those quantities. It is set by the 3:1
switched-capacitor stage's charge-transfer waveform, which depends on switch-state
timing, phase shift, dead time and flying-capacitor impedance -- none of which exists in
this framework. Inventing a sequence to produce an RMS number would be fabrication, so
the 48 V RMS is returned as a BRACKET with the DC lower bound and a square-pulse upper
bound, and its status stays OPEN.

That matters because the 48 V rail is exactly where the BGA, the HV package RDL and the
Z1 substrate TSVs live.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0mr", "scripts/phase0f", "scripts/phase0d", "scripts/phase0i",
           "scripts/phase0nw", "scripts/phase0m", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

L0, L1, L2 = "RMS_L0_DC", "RMS_L1_ANALYTIC", "RMS_L2_TIME_DOMAIN"


def design():
    import replay_production as RP
    return RP.compiled_design()


def triangular_rms(i_dc: float, di_pp: float) -> float:
    """Closed form for a triangular ripple on a DC level."""
    return math.sqrt(i_dc ** 2 + di_pp ** 2 / 12.0)


def _numeric_triangular_rms(i_dc: float, di_pp: float, n: int = 200_001) -> float:
    """Independent numerical integration, for the analytic form to be tested against."""
    t = [k / (n - 1) for k in range(n)]
    i = [i_dc + di_pp * (2 * x - 1) / 2 if x < 0.5 else i_dc + di_pp * (1 - 2 * (x - 0.5)) / 2
         for x in t]
    return math.sqrt(sum(v * v for v in i) / n)


def gated_square_rms(i_on: float, duty: float) -> float:
    """A current that is i_on for a fraction `duty` of the period and zero otherwise."""
    return i_on * math.sqrt(duty)


def cell_currents() -> dict:
    """Per-cell buck-side currents at RMS-L1, from the design's own parameters."""
    d = design()
    a = d.arch
    N, K, K_A, B, D = a.N, a.K, a.K_A, list(a.B_array), a.D
    L = d.inductor.l_nh * 1e-9
    f = d.f_sw_hz
    i_out = d.i_out_a
    v_in, v_out = d.v_in, d.v_out
    v_mid = v_in / N                      # 3:1 SC output, 16 V
    boost = 1.0 + d.inductor.coupling_k * max(K - 1, 0)

    # total output ripple -- the framework's own expression, reused rather than restated
    di_out = ((D / (f * L)) * (v_in / N * K_A - v_out * K)) / boost

    # per-branch ripple: phase A branches see (V_mid - V_out) during the on-time,
    # phase B branches see (-V_out). Their signed sum must reproduce di_out.
    t_on = D / f
    di_A = (v_mid - v_out) / L * t_on / boost
    di_B = (v_out) / L * t_on / boost
    check = K_A * di_A - (K - K_A) * di_B
    if abs(check - di_out) > 1e-9 * max(abs(di_out), 1.0):
        raise ValueError(f"branch ripples {check} do not reproduce the ledger's "
                         f"output ripple {di_out}")

    b_sum = sum(B)
    i_branch_avg = [i_out * b / b_sum for b in B]
    branches = []
    for k, i_avg in enumerate(i_branch_avg):
        phase = "A" if k < K_A else "B"
        dpp = di_A if phase == "A" else di_B
        branches.append({
            "index": k, "phase": phase, "i_avg_a": i_avg, "ripple_pp_a": dpp,
            "i_rms_a": triangular_rms(i_avg, dpp), "i_peak_a": i_avg + dpp / 2,
            "waveform": "triangular (CCM)", "rung": L1})

    i_out_rms = triangular_rms(i_out, di_out)
    # 16 V mid-node: the buck input, a gated square at duty D
    i_mid_avg = i_out * D
    i_mid_rms = gated_square_rms(i_out, D)
    return {
        "N": N, "K": K, "K_A": K_A, "K_B": K - K_A, "B": B, "D": D,
        "f_sw_hz": f, "L_nH": d.inductor.l_nh, "coupling_k": d.inductor.coupling_k,
        "v_in": v_in, "v_mid": v_mid, "v_out": v_out,
        "i_cell_out_avg_a": i_out, "ripple_out_pp_a": di_out,
        "i_cell_out_rms_a": i_out_rms,
        "ripple_A_pp_a": di_A, "ripple_B_pp_a": di_B,
        "branches": branches,
        "i_mid_avg_a": i_mid_avg, "i_mid_rms_a": i_mid_rms,
        "i_mid_rung": L1,
    }


def hv_input_bracket(i_hv_avg_a: float, duty_eff: float | None = None) -> dict:
    """The 48 V rail RMS, as a BRACKET. The SC waveform is not established.

    lower  DC: I_rms = I_avg, true only if the 48 V draw is continuous
    upper  a gated square pulse at the buck duty: I_rms = I_avg / sqrt(D)

    The upper bound is deliberately crude. It assumes the input conducts only during the
    buck on-time, which a multi-phase SC stage with charge-transfer smoothing would not
    do -- 10.1109/JSSC.2024.3485210 demonstrates hybrid topologies specifically designed
    to make the input current continuous. So the true value is somewhere inside, and the
    bracket is wide because the sequence is genuinely unknown, not because the bound is
    careless.
    """
    d = design()
    D = duty_eff if duty_eff is not None else d.arch.D
    lo = i_hv_avg_a
    hi = i_hv_avg_a / math.sqrt(D)
    return {"i_avg_a": i_hv_avg_a, "duty_used": D,
            "i_rms_lower_a": lo, "i_rms_upper_a": hi,
            "ratio_upper_over_avg": hi / lo,
            "rung": L0 + " (lower) / bounded square pulse (upper)",
            "status": "OPEN -- the 3:1 SC charge-transfer waveform is not in the "
                      "framework; no switch-state timing, phase shift or dead time",
            "why_not_eq5": (
                "10.1109/TCPMT.2026.3724907 Eq.(5) scales I_in,rms with "
                "I_out sqrt(V_out/V_in) for a buck-derived input. Our converter puts a "
                "3:1 SC stage in front, so the 48 V node does not see the buck's gated "
                "waveform directly. Eq.(5) is used as an order-of-magnitude SANITY "
                "CHECK, not as our value.")}


def eq5_reference(i_out_total_a: float, v_out: float, v_in: float) -> float:
    """DVPD Eq.(5)-style scaling, for comparison ONLY."""
    return i_out_total_a * math.sqrt(v_out / v_in)


def summary() -> dict:
    import power_path as PP
    c = cell_currents()
    out = {"design": {k: v for k, v in c.items() if k != "branches"},
           "branches": c["branches"], "architectures": {}}
    for arch in ("Z1", "Z2"):
        rc = PP.rail_currents(arch)
        hv = hv_input_bracket(rc["hv_total_a"])
        # the 1 V substrate rail: 49 cells in parallel, ripple partially cancelling.
        # Worst case (no interleaving credit) is cells adding in phase.
        lv_avg = rc["lv_total_a"]
        lv_ripple_worst = c["ripple_out_pp_a"] * 49
        lv_rms_worst = triangular_rms(lv_avg, lv_ripple_worst)
        out["architectures"][arch] = {
            "hv": hv,
            "lv_avg_a": lv_avg,
            "lv_ripple_pp_worst_a": lv_ripple_worst,
            "lv_rms_worst_a": lv_rms_worst,
            "lv_rms_over_avg_worst": lv_rms_worst / lv_avg,
            "lv_rung": L1 + " (worst case, no interleaving credit)",
            "eq5_reference_total_a": eq5_reference(lv_avg, c["v_out"], c["v_in"]),
        }
    return out


def main():
    s = summary()
    d = s["design"]
    print(f"N={d['N']} K={d['K']} K_A={d['K_A']} K_B={d['K_B']} B={d['B']} D={d['D']}")
    print(f"f_sw {d['f_sw_hz']/1e3:.2f} kHz  L {d['L_nH']} nH  "
          f"V 48 -> {d['v_mid']:.1f} -> {d['v_out']:.0f}\n")
    print(f"cell output  I_avg {d['i_cell_out_avg_a']:.4f} A  ripple_pp "
          f"{d['ripple_out_pp_a']:.4f} A  I_rms {d['i_cell_out_rms_a']:.4f} A  "
          f"(rms/avg {d['i_cell_out_rms_a']/d['i_cell_out_avg_a']:.5f})")
    print(f"16 V mid     I_avg {d['i_mid_avg_a']:.4f} A  I_rms {d['i_mid_rms_a']:.4f} A "
          f"(gated square, duty {d['D']})")
    print(f"\n{'branch':8s} {'phase':6s} {'I_avg':>8s} {'ripple':>8s} {'I_rms':>8s} {'I_peak':>8s}")
    for b in s["branches"]:
        print(f"{b['index']:<8d} {b['phase']:6s} {b['i_avg_a']:8.4f} "
              f"{b['ripple_pp_a']:8.4f} {b['i_rms_a']:8.4f} {b['i_peak_a']:8.4f}")
    for a, v in s["architectures"].items():
        h = v["hv"]
        print(f"\n{a}  48 V  I_avg {h['i_avg_a']:.4f} A -> RMS BRACKET "
              f"[{h['i_rms_lower_a']:.4f}, {h['i_rms_upper_a']:.4f}] A "
              f"({h['ratio_upper_over_avg']:.2f}x)  STATUS OPEN")
        print(f"     1 V  I_avg {v['lv_avg_a']:.1f} A  I_rms(worst) "
              f"{v['lv_rms_worst_a']:.3f} A  ratio {v['lv_rms_over_avg_worst']:.6f}")
        print(f"     Eq.(5) reference for the 1 V output: "
              f"{v['eq5_reference_total_a']:.2f} A (sanity check only)")
    out = R / "research" / "phase0nac"
    out.mkdir(parents=True, exist_ok=True)
    (out / "current_waveforms.json").write_text(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
