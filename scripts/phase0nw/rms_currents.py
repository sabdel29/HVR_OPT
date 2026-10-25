"""PHASE 0N-AC/AD/AE --- avg / RMS / peak currents, with what is and is not resolved.

KNOWN
  branch AVERAGE current          I_cell * B_i / sum(B) = 6.8027 A
  aggregate per-cell output ripple  the converter model's own expression
  per-cell output RMS             triangular RMS of the above

SCENARIO ONLY (named references, not bounds)
  16 V gated-square reference
  HV-S0  continuous 48 V input
  HV-S1  square pulse at the BUCK duty D = V_out*N/V_in
  HV-S2  square pulse at the OVERALL ratio V_out/V_in, which is the duty the DVPD
         source's Eq.(5) assumes

OPEN
  individual branch periodic waveform, branch RMS, branch peak
  actual 16 V rail waveform
  actual 48 V SC input waveform

There is NO RMS upper bound derivable from an average current, and I_avg/sqrt(D) is a
LOWER bound for a waveform of support D, not an upper one. Earlier versions of this
module said otherwise; see research/phase0nad/HVR_SWITCH_STATE_SOURCE_AUDIT.md for the
withdrawal and its evidence.
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


def phase_group_order(N: int, K: int, K_A: int) -> list:
    """Reproduce generate_B_array()'s INTERLEAVING to recover each branch's phase group.

    The order is NOT index-based. For N=3, K=3, K_A=2 the generator appends
    distA[0], distB[0], distA[1], giving ['A', 'B', 'A'] -- while the naive
    "A if k < K_A else B" gives ['A', 'A', 'B']. B_array alone is [1, 1, 1] and cannot
    distinguish them; only re-running the generator's interleave can.

    For the selected design this does not change any current magnitude, because all
    three B_i are equal. It WILL matter the moment an edge is mapped to a particular
    device or tier.
    """
    def distribute(branches, inductors):
        base, rem = branches // inductors, branches % inductors
        return [base + 1 if i < rem else base for i in range(inductors)]

    K_B = K - K_A
    distA, distB = distribute(math.ceil(N / 2), K_A), distribute(math.floor(N / 2), K_B)
    order, i, j = [], 0, 0
    if N % 2 == 0:
        while i < len(distA) or j < len(distB):
            if i < len(distA): order.append(("A", distA[i])); i += 1
            if j < len(distB): order.append(("B", distB[j])); j += 1
    elif K_A == 1:
        while i < len(distA) or j < len(distB):
            if j < len(distB): order.append(("B", distB[j])); j += 1
            if i < len(distA): order.append(("A", distA[i])); i += 1
    else:
        while i < len(distA) or j < len(distB):
            if i < len(distA): order.append(("A", distA[i])); i += 1
            if j < len(distB): order.append(("B", distB[j])); j += 1
    return order


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

    # PER-BRANCH RIPPLE IS WITHDRAWN. An earlier version decomposed the model's summed
    # output ripple into K_A*(V_mid - V_out) and (K - K_A)*(-V_out), each taken over the
    # on-interval D*T, and called those the branches' full-cycle ripples: 4.657 A and
    # 0.310 A. The algebra is right; the interpretation is not. A term's contribution to
    # the SUMMED ripple during one interval is not the periodic waveform of one inductor.
    #
    # Volt-second balance shows the gap: a conventional buck branch here ripples
    # (V_mid - V_out)*D*T/L = V_out*(1-D)*T/L = 4.657 A on BOTH ramps. The 0.310 A value
    # used (1-D) nowhere and described no complete cycle. Whether our phase-B inductors
    # behave conventionally depends on a switching sequence that the pinned source does
    # not contain -- see research/phase0nad/HVR_SWITCH_STATE_SOURCE_AUDIT.md. BOTH
    # values are therefore withdrawn and branch ripple is OPEN.
    t_on = D / f
    conv_ripple = (v_mid - v_out) / L * t_on / boost          # sanity check only
    conv_down = v_out / L * (1.0 - D) / f / boost
    if abs(conv_ripple - conv_down) > 1e-9 * conv_ripple:
        raise ValueError("volt-second balance broken in the conventional sanity check")

    b_sum = sum(B)
    groups = phase_group_order(N, K, K_A)
    if [g[1] for g in groups] != list(B):
        raise ValueError(f"reconstructed B {[g[1] for g in groups]} != source {B}")
    branches = []
    for k, b in enumerate(B):
        branches.append({
            "index": k, "phase": groups[k][0],
            "phase_provenance": "generate_B_array() interleave, re-run from the pinned "
                                "source; NOT inferred from the index",
            "b_i": b,
            "i_avg_a": i_out * b / b_sum,
            "i_avg_status": "KNOWN -- I_cell * B_i / sum(B)",
            "ripple_pp_a": None, "i_rms_a": None, "i_peak_a": None,
            "rms_status": "OPEN -- no switch-state sequence in the pinned source",
            "conventional_buck_ripple_sanity_a": conv_ripple,
            "rung": "OPEN"})

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
        "conventional_branch_ripple_sanity_a": conv_ripple,
        "branches": branches,
        "i_mid_avg_a": i_mid_avg, "i_mid_rms_scenario_a": i_mid_rms,
        "i_mid_status": "OPEN -- the square-pulse value is a SCENARIO",
    }


def hv_input_scenarios(i_hv_avg_a: float, duty_eff: float | None = None) -> dict:
    """48 V rail RMS SCENARIOS. There is NO upper bound, and S1 is not one.

    WHY I_avg/sqrt(D) IS A LOWER BOUND. For a nonnegative current whose support is
    exactly D*T, Cauchy-Schwarz on the support gives

        (int i dt)^2 <= (int i^2 dt) * (int 1 dt)
        (I_avg*T)^2  <= (I_rms^2*T) * (D*T)
        I_rms        >= I_avg / sqrt(D)

    with equality ONLY for a constant rectangular pulse. So I_avg/sqrt(D) is the MINIMUM
    RMS compatible with support D. A narrower, taller pulse of the same average has
    strictly higher RMS, without limit -- from an average current alone there is no
    finite RMS upper bound at all.

    A previous version called this an upper bound and reported a "bracket". It was
    neither a bound nor a bracket.
    """
    d = design()
    D = duty_eff if duty_eff is not None else d.arch.D
    return {
        "i_avg_a": i_hv_avg_a, "duty_used": D,
        "HV_S0": {"name": "continuous / DC current", "i_rms_a": i_hv_avg_a,
                  "rationale": "continuous 48 V draw; some hybrid topologies are "
                               "explicitly designed for this "
                               "(10.1109/JSSC.2024.3485210, CONTEXT_ONLY)"},
        "HV_S1": {"name": "constant square pulse at the buck duty",
                  "i_rms_a": i_hv_avg_a / math.sqrt(D),
                  "rationale": "MINIMUM RMS for support exactly D; NOT an upper bound"},
        "HV_S2": {"name": "square pulse at the overall ratio V_out/V_in",
                  "i_rms_a": i_hv_avg_a / math.sqrt(d.v_out / d.v_in),
                  "rationale": "the duty the DVPD source's Eq.(5) assumes -- it states "
                               "the relation is valid 'when the input current waveform "
                               "is nearly a square pulse with duty cycle proportional "
                               "to Vout/Vin', for buck-derived INCLUDING HYBRID "
                               "converters in CCM. Our 3:1 SC front end may or may not "
                               "behave that way; still a scenario."},
        "ratio_S1_over_S0": 1.0 / math.sqrt(D),
        "loss_ratio_S1_over_S0": 1.0 / D,
        "upper_bound_a": None,
        "upper_bound_status": "NONE EXISTS from average current alone",
        "status": "OPEN -- the 3:1 SC charge-transfer waveform is absent from the "
                  "pinned source; see "
                  "research/phase0nad/HVR_SWITCH_STATE_SOURCE_AUDIT.md",
    }


def dvpd_eq5_input_rms_reference_a(i_out_total_a: float, v_out: float,
                                   v_in: float) -> float:
    """DVPD Eq.(5): an INPUT-side RMS reference, I_out*sqrt(V_out/V_in).

    1000 A at 1 V from 48 V gives 144.3 A. That is an INPUT current. An earlier label
    called it "the 1 V output RMS" and compared it against our 1008 A output figure,
    which compared two different nodes of the converter.
    """
    return i_out_total_a * math.sqrt(v_out / v_in)


def summary() -> dict:
    import power_path as PP
    c = cell_currents()
    out = {"design": {k: v for k, v in c.items() if k != "branches"},
           "branches": c["branches"], "architectures": {}}
    for arch in ("Z1", "Z2"):
        rc = PP.rail_currents(arch)
        hv = hv_input_scenarios(rc["hv_total_a"])
        # SECTION L: the 49 TSV fields are ELECTRICALLY SEPARATE conductors, so
        # P_total = sum_m I_m,rms^2 R_m with NO cross terms. Inter-cell phase alignment
        # cannot affect that sum. Building a 1000 A + 49*dI aggregate and squaring it
        # would imply all 49 currents share one resistor, which they do not.
        i_cell_rms = triangular_rms(c["i_cell_out_avg_a"], c["ripple_out_pp_a"])
        out["architectures"][arch] = {
            "hv": hv,
            "lv_total_avg_a": rc["lv_total_a"],
            "i_cell_avg_a": c["i_cell_out_avg_a"],
            "ripple_cell_pp_a": c["ripple_out_pp_a"],
            "i_cell_rms_a": i_cell_rms,
            "cell_rms_over_avg": i_cell_rms / c["i_cell_out_avg_a"],
            "lv_form": "P = 49 * I_cell_rms^2 * (R_VDD + R_GND); fields are separate",
            "inter_cell_phase_matters": False,
            "inter_cell_phase_reason": (
                "no conductor is shared between cells, so no cross term I_m*I_n enters "
                "the Joule sum; phase alignment would only matter for a shared "
                "conductor"),
            "lv_rung": L1,
            "dvpd_eq5_input_rms_reference_a": dvpd_eq5_input_rms_reference_a(
                rc["lv_total_a"], c["v_out"], c["v_in"]),
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
    print(f"16 V mid     I_avg {d['i_mid_avg_a']:.4f} A  I_rms(scenario) {d['i_mid_rms_scenario_a']:.4f} A "
          f"(gated square, duty {d['D']})")
    print(f"\n{'branch':8s} {'phase':6s} {'B_i':>4s} {'I_avg':>8s}   rms status")
    for b in s["branches"]:
        print(f"{b['index']:<8d} {b['phase']:6s} {b['b_i']:4d} {b['i_avg_a']:8.4f}   "
              f"{b['rms_status']}")
    print(f"  conventional-buck branch ripple (SANITY ONLY): "
          f"{s['design']['conventional_branch_ripple_sanity_a']:.4f} A")
    for a, v in s["architectures"].items():
        h = v["hv"]
        print(f"\n{a}  48 V I_avg {h['i_avg_a']:.4f} A")
        print(f"     HV-S0 continuous      I_rms {h['HV_S0']['i_rms_a']:.4f} A")
        print(f"     HV-S1 square at D     I_rms {h['HV_S1']['i_rms_a']:.4f} A  "
              f"({h['ratio_S1_over_S0']:.2f}x -> {h['loss_ratio_S1_over_S0']:.0f}x in I^2R)")
        print(f"     upper bound: {h['upper_bound_status']}")
        print(f"     1 V per cell  I_avg {v['i_cell_avg_a']:.4f} A  ripple "
              f"{v['ripple_cell_pp_a']:.4f} A  I_rms {v['i_cell_rms_a']:.4f} A  "
              f"(rms/avg {v['cell_rms_over_avg']:.6f})")
        print(f"     DVPD Eq.(5) INPUT-side reference: "
              f"{v['dvpd_eq5_input_rms_reference_a']:.1f} A")
    out = R / "research" / "phase0nac"
    out.mkdir(parents=True, exist_ok=True)
    (out / "current_waveforms.json").write_text(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
