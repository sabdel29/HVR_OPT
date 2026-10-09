#!/usr/bin/env python3
"""Content for the SK hynix deck. Every number comes from sources.py."""
from __future__ import annotations
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
import sources as S
from deck_engine import (deck, new, chrome, figure, takeaway, bullets, table,
                         textbox, notes, W, H, MARG, CW, TOP, BOT,
                         BLU, ORA, GRN, RED, PUR, INK, GRY, LGY, ACC, FILL)

T = S.TRANSIENT
P = S.POLICY
PNR = S.PUBLISHED_NOT_RERUN
Z1, Z2 = S.PAIR["Z1"], S.PAIR["Z2"]

MAIN, BACK = [], []
def main(f):  MAIN.append(f);  return f
def back(f):  BACK.append(f);  return f


# ============================================================ OPENING
@main
def s_title(s, n):
    bar = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(W), Inches(0.16))
    bar.fill.solid(); bar.fill.fore_color.rgb = BLU; bar.line.fill.background()
    bar.shadow.inherit = False
    bar2 = s.shapes.add_shape(1, Inches(0), Inches(0.16), Inches(W), Inches(0.08))
    bar2.fill.solid(); bar2.fill.fore_color.rgb = ORA; bar2.line.fill.background()
    bar2.shadow.inherit = False
    textbox(s, "Power delivery decisions are physical decisions",
            MARG, 1.55, CW, 1.5, 40, bold=True, color=INK, space=0.95)
    textbox(s, "Evaluating 2.5D/3D power delivery on the package it actually runs on, "
               "and on the timescale the system actually runs",
            MARG, 3.05, CW - 1.2, 1.0, 21, color=GRY, space=1.1)
    rule = s.shapes.add_shape(1, Inches(MARG), Inches(4.25), Inches(3.2), Inches(0.035))
    rule.fill.solid(); rule.fill.fore_color.rgb = ORA; rule.line.fill.background()
    rule.shadow.inherit = False
    textbox(s, "Mohamed Gharib", MARG, 4.55, CW, 0.42, 20, bold=True, color=INK)
    textbox(s, "with Inna Partin-Vaisband", MARG, 4.97, CW, 0.38, 16, color=GRY)
    textbox(s, "Prepared for SK hynix   ·   2026", MARG, 5.65, CW, 0.40, 17,
            bold=True, color=BLU)
    textbox(s, "Two bodies of work, one argument: transient electrothermal modelling "
               "for HBM power gating, and\nelectrothermal–mechanical co-design of "
               "distributed vertical power delivery.",
            MARG, 6.25, CW, 0.80, 14.5, color=LGY, space=1.2)
    notes(s, """
[~25 s]

Thank you for having me. I am going to put two pieces of work next to each other
today, and argue that they are the same argument told at two different timescales.

The claim in the title is the whole talk: a power delivery decision only means
something once you evaluate it on the physical package, and on the timescale the
system actually runs at.

TRANSITION: Let me start with what I am going to show you, and what I am not.

If asked: Who did what — the transient electrothermal work and the DVPD
electrothermal–mechanical work are both mine; the DVPD manuscript is co-authored
with Inna Partin-Vaisband.
""")


@main
def s_roadmap(s, n):
    chrome(s, "What this talk covers — and what it does not claim",
           "roadmap", "GRY", n)
    bullets(s, [
        "Part I — milliseconds: a transient electrothermal solver for workload and "
        "power-gating studies, verified against two independent codes",
        "Part II — architecture: where the voltage regulator sits in a 1 kW stack, "
        "evaluated electrically, thermally and mechanically on one geometry",
        "Part III — the common principle, and what it implies for 2.5D/3D packaging",
    ], top=TOP + 0.02, size=18, gap=0.26)
    y = TOP + 2.30
    box = s.shapes.add_shape(5, Inches(MARG), Inches(y), Inches(CW), Inches(2.10))
    box.fill.solid(); box.fill.fore_color.rgb = FILL["RED"]
    box.line.color.rgb = RED; box.line.width = Pt(1.6)
    box.shadow.inherit = False
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.22)
    tf.margin_top = tf.margin_bottom = Inches(0.14)
    for i, t in enumerate([
            "Stated once, up front — what is NOT claimed anywhere in this talk",
            "No experimental validation. The transient work is cross-solver "
            "verification against MOOSE and Ansys Icepak.",
            "No fatigue life, no damage metric, no mechanical pass/fail, and no "
            "manufacturing qualification.",
            "No optimiser result, and no claim that any architecture is the right "
            "one for your product."]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.08; p.space_after = Pt(5)
        r = p.add_run()
        r.text = t if i == 0 else "–  " + t
        r.font.size = Pt(17 if i == 0 else 15.5)
        r.font.bold = (i == 0); r.font.color.rgb = RED if i == 0 else INK
        r.font.name = "Calibri"
    notes(s, """
[~65 s]

Three parts. Part one is a fast transient electrothermal solver, and the setting
there is workload stepping and power gating — the millisecond behaviour. Part two
is an architecture question at steady state: where the regulator physically sits
in a kilowatt stack, and what that does electrically, thermally and mechanically.
Part three ties them together.

I want to put the limitations on the screen before the results rather than after,
because they bound everything that follows. The transient work is verified against
two other codes — it is not validated against measurement. The mechanical work
produces a response quantity; it is not a damage metric and it is not a life
prediction. And nothing here is an optimiser result, nor a recommendation about
what SK hynix should build.

KEY NUMBERS: none yet — this slide is the contract.

TRANSITION: Let me start with why any of this is hard, which is a current number.

If asked: Why no measurement — no hardware vehicle exists for either study; both
are modelling results and are reported as such.
""")


@main
def s_current(s, n):
    chrome(s, "At 1 V, the delivery network is the constraint", "the problem",
           "RED", n)
    figure(s, "p_current.png", top=TOP + 0.35, maxh=3.5)
    takeaway(s, "Converting closer to the load shortens the 1 V rail — which turns "
                "“where does conversion happen?” into a packaging question.", "RED")
    notes(s, f"""
[~75 s]

A kilowatt at one volt is about a thousand amps, into a die {S.DIE_MM:.1f} millimetres on
a side. At that current the thing that limits you is not converter efficiency —
it is I-squared-R in a one-volt rail crossing a few millimetres of package metal.
That term is comparable to the load itself.

The standard answer is to convert closer to the load so the high-current rail is
short. That is distributed vertical power delivery. But the moment you say
"closer", you have made a packaging decision, not a circuit decision — and that is
the whole of Part II.

KEY NUMBERS: 1 kW at 1 V is about 1000 A; die is {S.DIE_MM:.2f} mm square.

TRANSITION: Before the results, one slide on why a single kind of model is not
enough for this.

If asked: Why 1 V — it is the frozen operating point of this study, chosen to make
the delivery problem explicit; the argument is about the method, not that voltage.
""")


@main
def s_scope(s, n):
    chrome(s, "Different models answer different questions", "framing", "GRY", n)
    figure(s, "p_scope.png", top=TOP + 0.10, maxh=4.35)
    takeaway(s, "Each row is correct and useful. The architecture question needs "
                "several of them at once, on one geometry.", "GRY")
    notes(s, """
[~70 s]

This is not a criticism of anyone's tools. A circuit-level regulator model tells
you loss and efficiency and tells you nothing about the package. A steady package
thermal model resolves geometry but not the transient and not the mechanics. A
stand-alone mechanical FEA resolves the mechanics but is usually run downstream, on
a temperature field someone handed it.

The point of the bottom row is not that it is better physics. It is that the
architecture question — where should conversion happen — touches all four columns
at once, so it has to be evaluated on one geometry with the couplings live.

KEY NUMBERS: none — this is the framing slide.

TRANSITION: And there is a second axis besides which physics: which timescale.

If asked: Is coupled always necessary — no. If you only need efficiency, use the
circuit model. Coupling earns its cost only when the answer depends on the
interaction, which is exactly the case I will show.
""")


@main
def s_bridge_up(s, n):
    chrome(s, "Two timescales, one design principle", "the thesis", "GRY", n)
    figure(s, "p_bridge.png", top=TOP + 0.05, maxh=4.45)
    takeaway(s, "Same argument, two timescales: the physical package and the "
                "operating timescale decide whether a power delivery choice is good.",
             "GRY")
    notes(s, f"""
[~70 s]

Here is the thesis in one picture, and I will come back to it at the end.

On the left, milliseconds. The die heats and cools as the workload steps and as
blocks are power-gated. To study that you need to march a transient many times
over, and the cost of doing that is what Part I is about — {T['ratio_400']:.1f} times faster
matched stepping.

On the right, the architecture. Steady state, but now the question is where the
regulator physically is, and the answer moves temperature by {S.DT:+.2f} kelvin and moves
the local mechanical response by {S.RED_E:.1f} per cent.

Different timescales, different physics, same discipline: evaluate it on the real
package, at the timescale that matters.

KEY NUMBERS: {T['ratio_400']:.2f}× matched transient stepping; {S.DT:+.2f} K; {S.RED_U:.1f} % driver; {S.RED_E:.1f} % response.

TRANSITION: Part I — milliseconds.

If asked: Are the two studies on the same package — no. Different vehicles and
different problems. The shared thing is the method discipline, not the geometry.
""")


# ============================================================ PART I
@main
def s_part1(s, n):
    bar = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(W), Inches(0.10))
    bar.fill.solid(); bar.fill.fore_color.rgb = BLU; bar.line.fill.background()
    bar.shadow.inherit = False
    textbox(s, "PART I", MARG, 2.35, CW, 0.6, 20, bold=True, color=BLU)
    textbox(s, "Milliseconds", MARG, 2.85, CW, 1.1, 46, bold=True, color=INK)
    textbox(s, "Transient electrothermal modelling for workload stepping and "
               "power gating", MARG, 4.05, CW - 1.5, 0.9, 21, color=GRY, space=1.1)
    textbox(s, str(n), W - MARG - 0.9, 7.03, 0.9, 0.30, 11, color=LGY,
            align=PP_ALIGN.RIGHT)
    notes(s, """
[~18 s]

Part one. The millisecond timescale.

TRANSITION: Start with why the transient matters at all for HBM.

If asked: nothing — this is a divider.
""")


@main
def s_workload(s, n):
    chrome(s, "The vehicle: a GPU with six HBM stacks on an interposer",
           "why transient", "BLU", n)
    figure(s, "epeps/paper_fig2_module.png", top=TOP + 0.08, maxh=4.15)
    takeaway(s, "Power gating and workload steps are transient events — a "
                "steady-state answer cannot see the excursion that actually occurs.",
             "BLU")
    notes(s, """
[~75 s]

This is the vehicle for Part I: a 700 watt GPU with six HBM stacks either side on
an interposer, and a thermal-aware controller that decides what to gate.

The reason this has to be transient is that none of these blocks sits at one
operating point. Traffic arrives in bursts, the heavy HBM stacks come and go, and
the thermal response has its own time constants.

If you solve steady state at the average power you miss the excursion. If you
solve steady state at the peak you over-design, because the die never dwells there
long enough to get that hot. The honest answer needs the time history — and you
need it once per candidate gating policy, which is where the cost problem comes
from.

KEY NUMBERS: 700 W GPU; six HBM stacks, two marked heavy.

TRANSITION: So here is how the model is posed.

If asked: Is this a specific product — no, it is a representative 2.5D module used
for the study; the power split and the heavy/light assignment are study inputs.
""")


@main
def s_framework(s, n):
    chrome(s, "The thermal model sits inside the policy loop, not after it",
           "method", "BLU", n)
    figure(s, "epeps/f2_framework.png", top=TOP + 0.05, maxh=4.4)
    takeaway(s, "Every candidate gating action is simulated as a transient and "
                "screened BEFORE it is allowed — which is only affordable if a "
                "transient is cheap.", "BLU")
    notes(s, """
[~90 s]

This is the structure of the method, and it is the reason runtime matters rather
than being a benchmark curiosity.

A candidate power-gating action comes in. It goes through an electrical and inrush
model, which gives a distributed Joule heating map, which is handed to a transient
thermal oracle — a three-dimensional finite-volume solve. The oracle returns the
temperature history, and a feasibility screen either rejects the action or passes
it to the policy optimiser.

The important word is BEFORE. The screen sits between the model and the optimiser,
not after the fact. The optimiser never gets to choose an action that would cook
the stack, because infeasible actions are removed from its choice set.

That is a strictly better architecture than checking afterwards — but it is only
affordable if one transient solve is cheap, because you now need one per candidate
action per epoch. Which is the next slide.

KEY NUMBERS: one 3-D transient solve per candidate action, inside the loop.

TRANSITION: So how do you make a transient cheap enough to put in a loop?

If asked: Why not a reduced-order or RC model — you can, and people do; the cost
is that you have to trust the reduction across the whole action space. Here the
full solve is made cheap instead, so no reduction is needed.
""")


@main
def s_operator(s, n):
    chrome(s, "Where the speed comes from: the operator is reused",
           "mechanism", "BLU", n)
    figure(s, "epeps/f3_operator_reuse.png", top=TOP + 0.05, maxh=4.4)
    takeaway(s, "Build and factorise once, then every step is a solve against the "
                "existing factorisation — so cost per step falls as steps accumulate.",
             "BLU")
    notes(s, """
[~90 s]

This is the mechanism, and it is the honest reason for the number on the next
slide but one.

For a linear, constant-property transient on a fixed mesh, the system operator does
not change from step to step. So you assemble it once and factorise it once, and
then each subsequent timestep is a back-substitution against a factorisation you
already own. The expensive part is paid at step zero and amortised across every
step after it.

That immediately tells you the shape of the result: the advantage is not a constant
factor. It grows with the number of steps, and it is smallest — in fact negative —
when there is only one solve to do. I will show you both ends of that.

KEY NUMBERS: cost is dominated by one factorisation; per-step cost is a solve.

TRANSITION: Before any speed claim, the answers have to agree.

If asked: What breaks the reuse — anything that changes the operator: strong
temperature-dependent conductivity, a moving mesh, or a changing boundary
condition type. Those cases lose the amortisation.
""")


@main
def s_steady3(s, n):
    chrome(s, "Does it agree with codes I did not write?",
           "verification", "BLU", n)
    figure(s, "epeps/f5_steady_three_tool.png", top=TOP + 0.05, maxh=4.3)
    takeaway(s, f"Largest deviation from the finite-element reference is "
                f"{T['fv_max_K']:.3f} K (this work) and {T['icepak_max_K']:.3f} K "
                f"(Icepak, {T['icepak_cells']:,} cells). Verification, not validation.",
             "BLU")
    notes(s, f"""
[~85 s]

Steady state first, because if the codes disagree here then nothing about the
transient is interesting.

Against the finite-element reference, Ansys Icepak on about {T['icepak_cells']:,} cells sits
within {T['icepak_max_K']:.3f} kelvin, and my finite-volume solver within {T['fv_max_K']:.3f} kelvin, across
the GPU case and both HBM cases. Those are small numbers against a package that is
tens of kelvin above ambient.

I want to be exact about the word: this is verification. Three independent
implementations of the same stated physics give the same answer, which tells you
the implementations are right. It does not tell you the physics matches hardware,
because no hardware was measured. The figure says that too.

KEY NUMBERS: FV max {T['fv_max_K']:.3f} K; Icepak max {T['icepak_max_K']:.3f} K; Icepak {T['icepak_cells']:,} cells.

TRANSITION: The agreement is backed by explicit invariant checks, not just a
temperature comparison.

If asked: Why is Icepak closer — it meshes the exact physical die volume, whereas
my FV support is matched to the contract; the residual is a support-definition
difference, not a physics difference.
""")


@main
def s_checks(s, n):
    chrome(s, "The checks that back the agreement", "verification", "BLU", n)
    figure(s, "epeps/f4_verification_checks.png", top=TOP + 0.25, maxh=3.9)
    takeaway(s, "Agreement has to hold in the mathematics, the discretisation, the "
                "observable AND across independent codes — a single matching "
                "temperature is not evidence on its own.", "BLU")
    notes(s, """
[~70 s]

One matching temperature can happen by luck, so the agreement is decomposed into
four things that each have to hold.

Exact mathematics: there is an analytic three-dimensional block solution to check
against. Discrete integrity: control volumes conserve energy. Matched observable:
every code is asked for the same quantity over the same region and the same
support — this is where most cross-code comparisons quietly fail. And independent
codes: MOOSE and Ansys Icepak were written by other people.

Only when all four hold does an agreeing temperature mean anything.

KEY NUMBERS: four independent conditions; two independent third-party codes.

TRANSITION: Now the runtime, with its counter-case.

If asked: Which of the four is hardest — the matched observable. Comparing a
surface average against a point probe will produce a disagreement that looks like
physics and is not.
""")


@main
def s_runtime(s, n):
    chrome(s, f"{T['ratio_400']:.1f}× on matched transient stepping — and the case "
              f"where it loses", "result", "BLU", n)
    figure(s, "epeps/f6_runtime.png", top=TOP + 0.05, maxh=4.3)
    takeaway(s, f"{T['ratio_400']:.1f}× holds for repeated transient stepping "
                f"({T['fv_400_s']:.0f} s vs {T['moose_400_s']:.0f} s, "
                f"{T['crossover']['steps'][-1]} steps, one core). For ONE steady solve "
                f"the same code is {T['steady_ratio']:.0f}× SLOWER.", "BLU")
    notes(s, f"""
[~110 s]

This is the headline of Part I, and the red box is as important as the big number.

On a matched {T['crossover']['steps'][-1]}-step transient, one core, same problem size and same output
responsibility: {T['fv_400_s']:.0f} seconds against {T['moose_400_s']:.0f} seconds. That is {T['ratio_400']:.2f} times. The figure
also shows MOOSE on six ranks, so you can see the single-core comparison is not
hiding a parallelism story.

Now the counter-case, in red. For a single steady solve, my code takes about
{T['steady_fv_s']:.0f} seconds and MOOSE takes about {T['steady_moose_s']:.0f}. That is roughly {T['steady_ratio']:.0f} times SLOWER,
not faster. That is exactly what the amortisation argument predicts: if you only
solve once, you pay the factorisation and get nothing back for it.

So the claim is narrow and I want it heard narrowly: this is a repeated-transient
tool. If your workload is one steady point, use a general code.

The right panel shows the crossover — {T['crossover']['steps'][0]} steps gives about 2.3×, and it grows
monotonically to {T['ratio_400']:.1f}× at {T['crossover']['steps'][-1]}.

KEY NUMBERS: {T['fv_400_s']:.1f} s vs {T['moose_400_s']:.1f} s = {T['ratio_400']:.2f}×; steady {T['steady_fv_s']:.1f} s vs {T['steady_moose_s']:.1f} s = {T['steady_ratio']:.1f}× slower.

TRANSITION: So what does that buy you in practice?

If asked: Is the MOOSE configuration fair — it is a linear LU/MUMPS screen
configuration on the same mesh, interleaved with the FV runs so machine load is
shared; the load averages per point are recorded in the artifact.

If asked: Does it parallelise — the comparison is single core by construction; the
six-rank MOOSE bar is there so the reader can scale the claim themselves.
""")


@main
def s_greedy(s, n):
    chrome(s, "What the speed buys: screening power-gating policies",
           "application", "BLU", n)
    figure(s, "epeps/f7_policy_greedy.png", top=TOP + 0.05, maxh=4.15)
    takeaway(s, f"A greedy policy reaches {P['greedy_oracle']:.2f} °C (oracle) / "
                f"{P['greedy_ansys']:.2f} °C (Ansys) — above the "
                f"{P['hbm_limit_C']:.0f} °C HBM limit used here.", "BLU")
    notes(s, f"""
[~80 s]

Here is why the speed matters rather than being a benchmark curiosity.

If evaluating one candidate policy costs you twenty minutes, you evaluate three. If
it costs ninety seconds, you evaluate hundreds, and you can put the thermal model
inside the policy loop instead of checking afterwards.

This is a greedy gating policy — take the best immediate move at each step. It
reaches about {P['greedy_oracle']:.2f} degrees on the oracle trace and {P['greedy_ansys']:.2f} on the Ansys
cross-check, against the {P['hbm_limit_C']:.0f} degree HBM limit used in this study. So greedy
violates, and it violates because it never looks ahead at the thermal consequence.

KEY NUMBERS: greedy {P['greedy_oracle']:.2f} °C oracle, {P['greedy_ansys']:.2f} °C Ansys; limit {P['hbm_limit_C']:.0f} °C.

TRANSITION: Thermally screening the same policy fixes it.

If asked: Is {P['hbm_limit_C']:.0f} °C a real HBM spec — it is the limit adopted in this study;
treat it as a parameter, not a datasheet value for any specific part.
""")


@main
def s_screened(s, n):
    chrome(s, "Thermally screened: the same workload, under the limit",
           "application", "BLU", n)
    figure(s, "epeps/f8_policy_screened.png", top=TOP + 0.05, maxh=4.15)
    takeaway(s, f"Screened policy holds {P['screened_oracle']:.2f} °C / "
                f"{P['screened_ansys']:.2f} °C — {PNR['violations_before']} violations "
                f"to {PNR['violations_after']} over {PNR['epochs']} epochs, at "
                f"{PNR['leakage_overhead_pct']:.1f} % leakage overhead.", "BLU")
    notes(s, f"""
[~80 s]

Same workload, same hardware model, but now the thermal model is consulted inside
the policy loop and moves that would cross the limit are screened out.

Peak goes to about {P['screened_oracle']:.2f} degrees on the oracle trace and {P['screened_ansys']:.2f} on the
Ansys cross-check — comfortably under {P['hbm_limit_C']:.0f}. Over {PNR['epochs']} epochs the violation
count goes from {PNR['violations_before']} to {PNR['violations_after']}, and the price is about
{PNR['leakage_overhead_pct']:.1f} per cent leakage overhead.

One piece of provenance I owe you: these two policy traces are the published EPEPS
2026 application result. They were produced before a later solver correction and
they have not been rerun. The verification and runtime numbers I showed you were
rerun; these were not. I am showing them as a published application result, not as
a fresh measurement.

KEY NUMBERS: {P['screened_oracle']:.2f} / {P['screened_ansys']:.2f} °C; {PNR['violations_before']}→{PNR['violations_after']} violations over {PNR['epochs']} epochs; {PNR['leakage_overhead_pct']:.1f} % overhead.

TRANSITION: Let me close Part I with the claim boundary.

If asked: Would the correction change these — the correction affected the solver
path, so the absolute temperatures could shift slightly; the qualitative result
(screening removes violations at modest overhead) is what I am standing behind.
""")


@main
def s_part1_claims(s, n):
    chrome(s, "Part I — the claim boundary", "what is and is not claimed", "BLU", n)
    rows = [["Claimed", "Not claimed"],
            [f"Cross-solver verification against MOOSE and Ansys Icepak, "
             f"≤ {T['fv_max_K']:.3f} K from the FE reference",
             "Experimental validation — no hardware was measured"],
            [f"{T['ratio_400']:.1f}× on matched repeated transient stepping, one core, "
             f"{T['crossover']['steps'][-1]} steps",
             f"A general speed claim — one steady solve is {T['steady_ratio']:.0f}× SLOWER"],
            ["Energy balance, mesh refinement and steady-limit checks hold",
             "That the modelled physics matches a real part"],
            ["Policy screening removes the violations in the published case",
             "That those traces were rerun after the solver correction"]]
    table(s, rows, top=TOP + 0.25, size=15.5, accent="BLU", colw=[1, 1])
    takeaway(s, "The speed-up is real and narrow. The verification is real and is "
                "not validation.", "BLU")
    notes(s, f"""
[~75 s]

Let me say the boundary once, plainly, so it carries into the second half.

What I am claiming: three codes agree on one stated physical contract; the
invariant checks hold; the solver is {T['ratio_400']:.1f} times faster on repeated transient
stepping; and in the published application, screening removed the violations.

What I am not claiming: anything about agreement with measurement, any speed
advantage outside repeated stepping, and any freshness for the two policy traces.

KEY NUMBERS: {T['fv_max_K']:.3f} K; {T['ratio_400']:.2f}×; {T['steady_ratio']:.1f}× slower on one steady solve.

TRANSITION: That is the millisecond half. Now the architecture half.

If asked: What would make it validation — a thermally instrumented vehicle with
known power maps; that is the natural next step and it has not been done.
""")


# ============================================================ PART II
@main
def s_part2(s, n):
    bar = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(W), Inches(0.10))
    bar.fill.solid(); bar.fill.fore_color.rgb = ORA; bar.line.fill.background()
    bar.shadow.inherit = False
    textbox(s, "PART II", MARG, 2.35, CW, 0.6, 20, bold=True, color=ORA)
    textbox(s, "Architecture", MARG, 2.85, CW, 1.1, 46, bold=True, color=INK)
    textbox(s, "Where the regulator sits in a 1 kW stack — electrically, thermally "
               "and mechanically, on one geometry",
            MARG, 4.05, CW - 1.5, 0.9, 21, color=GRY, space=1.1)
    textbox(s, str(n), W - MARG - 0.9, 7.03, 0.9, 0.30, 11, color=LGY,
            align=PP_ALIGN.RIGHT)
    notes(s, """
[~18 s]

Part two. Same discipline, different timescale — now the question is architectural
and the state is steady.

TRANSITION: The question itself, stated precisely.

If asked: nothing — divider.
""")


@main
def s_dvpd_q(s, n):
    chrome(s, "The question: two placements, everything else held fixed",
           "the question", "ORA", n)
    bullets(s, [
        "Same converter design, same tier partition, same cooling, same die, "
        "same 1 kW load",
        ("Z1 EMBEDDED — the regulator cell is embedded inside the package "
         f"substrate (h_sub = {S.H_SUB_MM['Z1']:.2f} mm)", 1),
        ("Z2 BACKSIDE — the regulator is a chiplet below a thinned substrate "
         f"(h_sub = {S.H_SUB_MM['Z2']:.2f} mm)", 1),
        "Both were frozen in configuration files BEFORE either was solved — one "
        "solve each, no sweep, no tuning",
        "Evaluated on one stack: converter loss → thermal field → thermoelastic "
        "deformation → local solder response",
    ], top=TOP + 0.10, size=18.5, gap=0.30)
    takeaway(s, "This is a controlled comparison of placement, not an optimisation "
                "and not a search over architectures.", "ORA")
    notes(s, f"""
[~70 s]

The question is deliberately narrow, because that is what makes it answerable.

Two placements. Z1 embeds the regulator inside the substrate, which is
{S.H_SUB_MM['Z1']:.2f} millimetres thick. Z2 puts it as a chiplet on the backside of a
substrate thinned to {S.H_SUB_MM['Z2']:.2f} millimetres. Everything else is held — same converter,
same tier partition, same cooling, same die, same kilowatt.

Both configurations were frozen in files before either was solved, and each got
exactly one solve. That matters because the result I am going to show is a
difference of a few per cent on a mechanical quantity, and if I had been free to
re-run and re-tune I could have produced whatever ordering I wanted.

KEY NUMBERS: h_sub {S.H_SUB_MM['Z1']:.2f} mm vs {S.H_SUB_MM['Z2']:.2f} mm; 1 kW; one solve each.

TRANSITION: First the converter that is common to both.

If asked: Why only two — this is a controlled pair, not a design space. There is
no optimiser here and no claim that either is best.
""")


@main
def s_converter(s, n):
    chrome(s, "The converter, common to both architectures", "the vehicle",
           "ORA", n)
    figure(s, "p_converter.png", top=TOP + 0.20, maxh=4.15)
    takeaway(s, f"M = {S.CONVERTER['M']} cells, {S.CONVERTER['I_cell']:.3f} A and "
                f"{S.CONVERTER['A_cell']:.2f} mm² per cell. Identical in Z1 and Z2 — "
                f"the only thing that moves is where it sits.", "ORA")
    notes(s, f"""
[~85 s]

A word on the converter, because this audience will want to know it is not a toy.

48 volts in, 1 volt out, through a two-stage hybrid. A 3-to-1 switched-capacitor
stage with no magnetics takes 48 down to a 16 volt intermediate rail, and then a
{S.CONVERTER['N']}-phase buck takes 16 to 1. The reason for the intermediate rail is the duty
ratio: a single 48-to-1 stage would need a duty ratio no real switch will hold,
whereas from 16 volts you need D = {S.CONVERTER['D']:.4f}, which is reachable at
{S.CONVERTER['f_sw_kHz']:.0f} kilohertz.

The system is {S.CONVERTER['M']} such cells, each carrying {S.CONVERTER['I_cell']:.3f} amps in
{S.CONVERTER['A_cell']:.2f} square millimetres.

This whole design is identical in Z1 and Z2. I am not comparing converters.

KEY NUMBERS: 48→16→1 V; M = {S.CONVERTER['M']}; D = {S.CONVERTER['D']:.4f}; f_sw = {S.CONVERTER['f_sw_kHz']:.2f} kHz; {S.CONVERTER['A_cell']:.2f} mm²/cell.

TRANSITION: And the cooling, also identical.

If asked: Why GaN — the device set follows the sourced design; the switch-level
choice is upstream of this study and is not varied.
""")


@main
def s_cooling(s, n):
    chrome(s, "The cooling solution, also identical", "the vehicle", "ORA", n)
    figure(s, "p_cooling.png", top=TOP + 0.20, maxh=4.15)
    takeaway(s, f"{S.COOLING['channels']} microchannels, laminar at Re = "
                f"{S.COOLING['Re']:.0f}, {S.COOLING['dT_K']:.2f} K coolant rise, "
                f"{S.COOLING['P_pump_W']:.1f} W of pump power — counted, not ignored.",
             "ORA")
    notes(s, f"""
[~65 s]

Cooling is held fixed too: {S.COOLING['channels']} parallel microchannels, {S.COOLING['w_um']} by
{S.COOLING['h_um']} microns, water at {S.COOLING['T_in_C']:.0f} degrees inlet and {S.COOLING['m_dot_g_s']:.0f} grams per second.

Reynolds number is {S.COOLING['Re']:.0f}, so we are laminar with margin. Coolant rise is
{S.COOLING['dT_K']:.2f} kelvin, pressure drop {S.COOLING['dp_MPa']:.3f} megapascal, and pump power is
{S.COOLING['P_pump_W']:.1f} watts.

I put pump power on the slide deliberately. It is about {100*S.COOLING['P_pump_W']/Z1['P_elec']:.0f} per cent of the
converter loss it exists to remove, and it is a real part of the budget. It is
counted here, not quietly dropped.

KEY NUMBERS: {S.COOLING['channels']} channels; Re {S.COOLING['Re']:.1f}; h_eff {S.COOLING['h_eff_kW']:.1f} kW/m²K; ΔT {S.COOLING['dT_K']:.3f} K; Δp {S.COOLING['dp_MPa']:.4f} MPa; pump {S.COOLING['P_pump_W']:.3f} W.

TRANSITION: Now the thing that actually differs between the two.

If asked: Is the microchannel model conjugate CFD — no. It is a correlation-based
channel model. There is no conjugate CFD validation in this work, and that is a
stated limitation.
""")


@main
def s_rail(s, n):
    chrome(s, "Where the conversion sits decides which rail crosses the substrate",
           "the mechanism", "ORA", n)
    figure(s, "p_rail.png", top=TOP + 0.02, maxh=4.5)
    takeaway(s, f"Z1 sends {S.RAIL['Z1']['I']:.0f} A of 48 V rail through "
                f"{S.H_TSV_UM['Z1']:.0f} µm. Z2 sends {S.RAIL['Z2']['I']:.0f} A of 1 V "
                f"rail through {S.H_TSV_UM['Z2']:.0f} µm.", "ORA")
    notes(s, f"""
[~105 s]

This is the slide that explains everything downstream, so let me walk it.

On the left, Z1. The regulator cell is embedded in the substrate, near the top. So
the path from the board up to that cell is short — {S.H_TSV_UM['Z1']:.0f} microns, the part of the
substrate below the cell — and critically, what crosses it is the 48 volt INPUT,
which at system level is about {S.RAIL['Z1']['I']:.0f} amps. Above the cell it is microbumps to
the die at 1 volt, which is a very short hop.

On the right, Z2. The regulator is a chiplet below the substrate, so conversion
happens before the substrate. What crosses the substrate is now the 1 volt OUTPUT
— {S.RAIL['Z2']['I']:.0f} amps — and it crosses the full {S.H_TSV_UM['Z2']:.0f} microns.

Notice what I am NOT saying. I am not saying the via geometry is the same; it is
not, and the substrates are drawn here to a common scale so you can see that. The
point is the rail assignment. Statements like "the TSV carries 48 volts" or "the
TSV carries 1 volt" are both wrong as general claims — which one is true is set by
where conversion sits relative to the substrate.

KEY NUMBERS: Z1 {S.H_TSV_UM['Z1']:.0f} µm at {S.RAIL['Z1']['I']:.2f} A (48 V); Z2 {S.H_TSV_UM['Z2']:.0f} µm at {S.RAIL['Z2']['I']:.0f} A (1 V).

TRANSITION: So what does that cost?

If asked: Where does {S.RAIL['Z1']['I']:.1f} A come from — 1 kW at the converter efficiency used in
the path model, divided by 48 V. It is a system-level current, not per cell.
""")


@main
def s_tsvloss(s, n):
    chrome(s, "The vertical loss follows the rail, not the via", "result", "ORA", n)
    figure(s, "p_tsvloss.png", top=TOP + 0.20, maxh=4.15)
    takeaway(s, f"Z2's vertical loss is {Z2['P_tsv']:.3f} W. Z1's is below 0.2 mW — "
                f"with a path that is {S.H_TSV_UM['Z2']/S.H_TSV_UM['Z1']:.1f}× SHORTER "
                f"carrying {S.RAIL['Z2']['I']/S.RAIL['Z1']['I']:.0f}× less current.",
             "ORA")
    notes(s, f"""
[~80 s]

Here is the consequence. Z2's through-substrate loss is {Z2['P_tsv']:.3f} watts. Z1's is
below two tenths of a milliwatt — effectively zero.

And I want you to notice the direction, because it is the opposite of the naive
intuition. Z1's via is {S.H_TSV_UM['Z2']/S.H_TSV_UM['Z1']:.1f} times SHORTER. If this were a geometry story,
a shorter via would be the whole explanation. It is not. It is a current story:
{S.RAIL['Z2']['I']/S.RAIL['Z1']['I']:.0f} times less current, and the loss goes as current squared against a
via count that is itself allocated from the current.

So "TSV resistance" on its own is not an architecture metric. Geometry times
assigned rail times current times allocation policy is.

KEY NUMBERS: {Z2['P_tsv']:.4f} W vs |{Z1['P_tsv']:.5f}| W; {S.H_TSV_UM['Z2']/S.H_TSV_UM['Z1']:.2f}× path; {S.RAIL['Z2']['I']/S.RAIL['Z1']['I']:.1f}× current.

TRANSITION: One watt out of how many, though? Context matters.

If asked: Why report Z1 as a bound — the ledger value is a very small negative
number, which is a known small-signal artefact of adding an FV-derived transition
correction to a {S.H_TSV_UM['Z1']:.0f} µm bulk path. Reporting it as "below 0.2 mW" is honest; quoting
a negative loss would not be.
""")


@main
def s_loss(s, n):
    chrome(s, "In context: about 2 W out of about 137 W", "result", "ORA", n)
    figure(s, "p_loss.png", top=TOP + 0.15, maxh=4.2)
    takeaway(s, f"Z1 {Z1['P_elec']:.2f} W → Z2 {Z2['P_elec']:.2f} W. The TSV is only "
                f"part of it — the rest is thermal feedback, because the hotter "
                f"architecture is the more resistive one.", "ORA")
    notes(s, f"""
[~85 s]

Context, because a one-watt number means nothing without a denominator.

Total converter loss is {Z1['P_elec']:.2f} watts for Z1 and {Z2['P_elec']:.2f} for Z2 — a difference of
{Z2['P_elec']-Z1['P_elec']:.2f} watts, about {100*(Z2['P_elec']/Z1['P_elec']-1):.1f} per cent. Electrically, moving the regulator is
nearly free.

But look at the right panel, because this is the interesting part. The TSV
accounts for about forty per cent of that difference. The majority is switch
conduction and inductor DCR going up — and those went up because Z2 runs hotter,
and copper and channel resistance rise with temperature.

That is a coupled-model result. An uncoupled calculation would have given you the
TSV term and stopped, and would have under-predicted the penalty by more than half.

KEY NUMBERS: {Z1['P_elec']:.3f} → {Z2['P_elec']:.3f} W; Δ {Z2['P_elec']-Z1['P_elec']:.3f} W; TSV share ≈ 42 %.

TRANSITION: Electrically cheap. But is either architecture buildable?

If asked: Is 2 W significant at 1 kW — not on its own. It matters because it is a
visible signature of the coupling, and because it lands as heat in a place that
changes the mechanics.
""")


@main
def s_tiers(s, n):
    chrome(s, "Realizability comes from conductor-plane topology, not layer count",
           "realizability", "ORA", n)
    figure(s, "p_tiers.png", top=TOP + 0.05, maxh=4.3)
    takeaway(s, f"Permuting two tiers takes the worst via aspect ratio from "
                f"{S.AR['baseline_T1']:.2f} to {S.AR['repartition_C1']:.3f} — same "
                f"parts, same areas, same {S.STACK_UM:.0f} µm stack height.", "ORA")
    notes(s, f"""
[~90 s]

A packaging audience will ask whether any of this can be built, so here is the
realizability argument.

The usual way people assess vertical interconnect is by counting material layers.
That is the wrong invariant. What sets whether a via is manufacturable is the
conductor-plane topology — which planes a net actually has to cross — and from
that you get an aspect ratio.

In the reference arrangement, the worst net has to cross a {S.AR['baseline_T1']:.2f} aspect ratio
via, which is not a comfortable build-up structure. Permute two tiers — move the
flying capacitors down and the low-side GaN up — and the worst aspect ratio becomes
{S.AR['repartition_C1']:.3f}. Same five component classes, same counts, same per-tier areas, same
{S.STACK_UM:.0f} micron stack height. It is a permutation, not a redesign.

The reason it works is that the high-current switch node now crosses only the
interlayer RDL instead of a 100 micron component tier.

And the limit: this is GEOMETRICALLY REALIZABLE and PROCESS-CONDITIONAL. Three
manufacturing inputs are still open — the microvia current allowable, the capture
pad diameter, and a vendor design rule. This is not a manufacturing qualification
and must not be read as one.

KEY NUMBERS: AR {S.AR['baseline_T1']:.3f} → {S.AR['repartition_C1']:.3f}; pitch 150 µm (source-bounded); stack {S.STACK_UM:.0f} µm.

TRANSITION: Now the mechanics — and first, three words that get conflated.

If asked: Is 150 µm pitch realistic — it is source-bounded from published
production practice for microvias to embedded dies; the via diameter, by contrast,
is open.
""")


@main
def s_mech_chain(s, n):
    chrome(s, "Three quantities that are routinely conflated", "mechanics",
           "PUR", n)
    figure(s, "p_mech_chain.png", top=TOP + 0.02, maxh=4.5)
    takeaway(s, "Warpage is not the driver. The driver is not the response. The "
                "response is not damage, and damage is not life.", "RED")
    notes(s, f"""
[~95 s]

This slide exists because in my experience these three get used interchangeably,
and they are not the same thing.

Global warpage is the shape of the whole package — {Z1['die_warp']:.2f} microns for Z1,
{Z2['die_warp']:.2f} for Z2. It is a package-level quantity and it is NOT what a solder joint
experiences.

What the critical joint experiences is a relative displacement across it — I call
it delta-u-c, the driver. That is {Z1['du_c']:.4f} microns for Z1 and {Z2['du_c']:.4f} for Z2.
Different quantity, different magnitude, and it does not track warpage
proportionally.

And then the response: how the solder actually responds to that driver, given its
constitutive behaviour and its temperature. That is delta-epsilon-in, an inelastic
strain increment per cycle.

Now the sentence I most want you to take away. A response is not damage. Damage is
not life. Life is not failure. I ran no fatigue model, I am not reporting a cycles
to failure, and I am not telling you either architecture is mechanically safe.

KEY NUMBERS: warpage {Z1['die_warp']:.3f}→{Z2['die_warp']:.3f} µm; driver {Z1['du_c']:.4f}→{Z2['du_c']:.4f} µm; response {Z1['d_eps']*1e2:.4f}→{Z2['d_eps']*1e2:.4f} ×10⁻².

TRANSITION: With that vocabulary, here is the result.

If asked: Why not compute life — a Coffin-Manson or energy-based life model would
need a damage correlation fitted for this joint and this loading; none is
available here, and inventing one would be the least defensible step in the chain.
""")


@main
def s_final(s, n):
    chrome(s, "The result: the hotter architecture has the lower local response",
           "the result", "ORA", n)
    figure(s, "p_final.png", top=TOP + 0.05, maxh=4.3)
    takeaway(s, f"Z2 runs {S.DT:+.2f} K hotter, yet carries {S.RED_U:.1f} % less "
                f"driver and {S.RED_E:.1f} % less response. Temperature and "
                f"mechanical response decouple.", "ORA")
    notes(s, f"""
[~115 s]

This is the central result of Part II, and it is the one I did not expect.

Four quantities, Z1 on the left of each panel, Z2 on the right.

Peak temperature goes UP: {Z1['T_max']:.2f} to {Z2['T_max']:.2f} degrees, so {S.DT:+.2f} kelvin. Z2 is the
hotter architecture, and it is hotter for a reason you already saw — it is
dissipating that extra watt in the substrate, in the path between the chiplet and
the die.

But the three mechanical panels all go DOWN. Die warpage falls about {100*(1-Z2['die_warp']/Z1['die_warp']):.1f} per
cent. The local driver falls {S.RED_U:.1f} per cent. And the local solder response falls
{S.RED_E:.1f} per cent.

So the architecture that is thermally worse is, on this metric, mechanically
gentler. If you had used peak temperature as a proxy for mechanical severity —
which is an extremely common shortcut — you would have ranked these two backwards.

That is the argument for coupling. Not that coupling is more rigorous in the
abstract, but that here it reverses the ordering.

Let me be careful about what survives. The ORDERING is robust. The absolute
magnitude of the solder response is conditional on a constitutive model evaluated
well outside its fitted stress window, and I will come back to that.

KEY NUMBERS: T_max {Z1['T_max']:.2f}→{Z2['T_max']:.2f} °C ({S.DT:+.2f} K); joint {Z1['T_joint']:.2f}→{Z2['T_joint']:.2f} °C ({S.DTJ:+.2f} K); driver ratio D_u = {S.D_U:.4f}; response ratio D_ε = {S.D_EPS:.4f}.

TRANSITION: Why does the response fall further than the driver?

If asked: Is {S.RED_E:.1f} % a big effect — as a response difference it is modest. I am not
claiming it is decisive. I am claiming it has the opposite sign to what a thermal
proxy predicts, and that is the point.

If asked: Does this mean Z2 lasts longer — no. That is exactly the inference I am
refusing to make. Lower response is not longer life.
""")


@main
def s_decomp(s, n):
    chrome(s, "Separating the two causes", "mechanism", "PUR", n)
    figure(s, "p_decomp.png", top=TOP + 0.15, maxh=4.2)
    takeaway(s, "The displacement reduction does the work; the hotter joint gives "
                "a little of it back. The two effects are separable and oppose "
                "each other.", "PUR")
    notes(s, f"""
[~85 s]

Two things change between Z1 and Z2: the displacement field, and the joint
temperature. They push in opposite directions, so I ran the two cross cases to
separate them.

Bar one is Z1. Bar four is Z2 — about {100*(S.DECOMP['z2']/S.DECOMP['z1']-1):.1f} per cent.

Bar two takes Z2's displacement but holds Z1's joint temperature: that alone gives
{100*(S.DECOMP['du_only']/S.DECOMP['z1']-1):.1f} per cent. So the displacement reduction is doing essentially all of
the work, and slightly more than the net result.

Bar three takes Z1's displacement at Z2's joint temperature: {100*(S.DECOMP['T_only']/S.DECOMP['z1']-1):+.2f} per cent. The
hotter joint — {S.DTJ:+.2f} kelvin at the joint — makes the solder marginally more
compliant and gives a little back.

So the net {S.RED_E:.1f} per cent is a large displacement benefit partly offset by a small
thermal penalty. That is a cleaner statement than a single number, and it is only
available because the two effects could be run independently.

KEY NUMBERS: Z1 {S.DECOMP['z1']*1e2:.3f}; displacement-only {S.DECOMP['du_only']*1e2:.3f}; temperature-only {S.DECOMP['T_only']*1e2:.3f}; Z2 {S.DECOMP['z2']*1e2:.3f} (×10⁻²).

TRANSITION: One more thing before I close this half — is the number numerically trustworthy?

If asked: Do the two effects superpose — not exactly; the sum of the two
individual deltas is close to but not identical to the combined result, which is
expected for a nonlinear creep response.
""")


@main
def s_cetol(s, n):
    chrome(s, "Numerical conditioning — stated honestly", "conditioning", "PUR", n)
    figure(s, "p_cetol.png", top=TOP + 0.15, maxh=4.2)
    takeaway(s, "Insensitive to further relaxation, with a ONE-SIDED bracket. "
                "No tighter tolerance converges, so the magnitude stays conditional.",
             "RED")
    notes(s, f"""
[~85 s]

A reviewer's first question about a creep result is whether the integration
tolerance drove it, so I tested it.

Five tolerances, everything else frozen. The three tight ones — 1e-5, 1e-4 and
1e-2 — do not converge at all. The solver makes cutback attempts and completes
zero increments. At 5e-2 and 1e-1 it converges, and the two converged runs are
bit-identical: same {S.CETOL[3]['incr']} increments, zero cutbacks, identical to all twelve
printed digits.

So doubling the tolerance changes the answer by exactly zero, which rules out the
"you got this by loosening the tolerance" objection.

But I have to tell you why they are identical, because it is not the flattering
reason. Once the tolerance is loose enough for the solve to start, it is no longer
the binding step-size control — the step schedule is. So the agreement shows
insensitivity to further relaxation; it does not show agreement with a tight
tolerance reference, because no tight tolerance converges here.

The bracket is one-sided, and the response MAGNITUDE stays conditional. The
underlying reason is constitutive: the joint is operating at fifteen to seventeen
times yield against a card fitted over a much lower stress window.

KEY NUMBERS: 2 of 5 tolerances converge; D_ε = {S.CETOL[3]['d_eps']:.6f} at both; {S.CETOL[3]['incr']} increments, 0 cutbacks.

TRANSITION: Let me put the Part II boundary up the same way I did for Part I.

If asked: Why not fix the constitutive model — it would need creep data for this
alloy at this stress level; that data is not available to me, and extrapolating
further would be worse than declaring the limit.
""")


@main
def s_part2_claims(s, n):
    chrome(s, "Part II — the claim boundary", "what is and is not claimed",
           "ORA", n)
    rows = [["Claimed", "Not claimed"],
            [f"Ordering is robust: Z2 is {S.DT:+.2f} K hotter with {S.RED_E:.1f} % lower "
             f"local response", "Any fatigue life, damage metric or pass/fail verdict"],
            ["GEOMETRICALLY REALIZABLE at a source-bounded 150 µm pitch",
             "Manufacturing qualification — 3 process inputs remain OPEN"],
            ["A controlled two-point comparison, frozen before solving",
             "An optimiser result, or that mechanics moves the system optimum"],
            ["Correlation-based channel cooling, counted in the budget",
             "Conjugate CFD validation; a full-wave HFSS attempt did not converge"],
            ["Insensitive to further tolerance relaxation",
             "A converged absolute magnitude — the bracket is one-sided"]]
    table(s, rows, top=TOP + 0.12, size=14.5, accent="ORA", colw=[1, 1])
    takeaway(s, "The ordering is the result. The magnitude is conditional. "
                "Neither architecture is qualified.", "ORA")
    notes(s, f"""
[~80 s]

Same discipline as before.

What I claim: on this frozen pair, the ordering holds — Z2 is hotter and has the
lower local response, and that ordering survives the tolerance ladder and the
decomposition. The geometry closes at a source-bounded pitch. The cooling is
counted.

What I do not claim: any life or damage number; any manufacturing qualification —
three process inputs are still open; any optimiser result; conjugate CFD
validation — and I should say plainly that a full-wave HFSS attempt on this
structure did not converge, so there is no full-wave electromagnetic result here
either.

KEY NUMBERS: {S.DT:+.2f} K; {S.RED_E:.1f} %; 3 OPEN process inputs; 2 of 5 tolerances converge.

TRANSITION: Which brings me back to where I started.

If asked: What would close the process inputs — a vendor design rule set for this
build-up technology, a microvia current allowable, and a capture pad diameter.
Those are data, not modelling.
""")


# ============================================================ PART III
@main
def s_bridge_back(s, n):
    chrome(s, "The same argument, at both timescales", "synthesis", "GRY", n)
    figure(s, "p_bridge.png", top=TOP + 0.05, maxh=4.45)
    takeaway(s, "In both halves, the answer changed once the evaluation was done "
                "on the physical package at the right timescale.", "GRY")
    notes(s, f"""
[~75 s]

Back to the picture I opened with, now with the evidence behind it.

On the left, the millisecond side. The reason a fast repeated transient matters is
that the question — what does this gating policy do to peak temperature — is a
transient question. Answer it at steady state and you either miss the excursion or
over-design. And we saw that concretely: greedy looked fine until it was evaluated
against the thermal response, and then it violated.

On the right, the architecture side. The reason the coupled evaluation matters is
that peak temperature and local mechanical response moved in OPPOSITE directions.
A thermal proxy would have ranked the two placements backwards.

Different physics, different timescale, same failure mode if you shortcut it: the
cheap proxy gives you a confident wrong ordering.

KEY NUMBERS: {T['ratio_400']:.1f}× matched stepping; {S.DT:+.2f} K with {S.RED_E:.1f} % lower response.

TRANSITION: So what does that mean for people doing this work on real parts?

If asked: Would you always couple — no. Couple when you have reason to think the
coupling changes the ordering. The contribution is partly knowing when that is.
""")


@main
def s_implications(s, n):
    chrome(s, "What this suggests for 2.5D/3D power delivery work", "implications",
           "GRY", n)
    bullets(s, [
        "Pick the invariant that actually constrains you — conductor-plane "
        "topology predicted buildability here; material-layer count did not",
        "State which rail crosses the vertical interconnect. “The TSV carries "
        "48 V” and “the TSV carries 1 V” are both wrong as general statements",
        "Peak temperature is a poor proxy for local mechanical severity — here the "
        "two moved in opposite directions",
        "Keep response, damage, life and failure as four separate words; most "
        "disagreements I have had trace to collapsing them",
        "If the study is a repeated transient, amortised operators are worth it; "
        "if it is one steady solve, they are not",
    ], top=TOP + 0.05, size=18, gap=0.32)
    takeaway(s, "These are observations about method from two specific studies — "
                "not recommendations about any particular product or architecture.",
             "RED")
    notes(s, """
[~95 s]

Let me generalise carefully, and then say what I am not generalising.

First, invariants. The thing that predicted whether a vertical interconnect was
buildable was conductor-plane topology, not how many material layers the stack
had. If you are screening stack-ups, that is the cheaper and more predictive
quantity.

Second, be explicit about rail assignment. I showed that the same vertical
structure gives essentially zero loss or a watt depending only on which rail
crosses it. Any statement of the form "the TSV carries X volts" needs the
architecture attached.

Third, peak temperature is a poor proxy for local mechanical severity. Here it had
the wrong sign.

Fourth — and this one is free — keep the four words separate. Response, damage,
life, failure.

Fifth, the amortisation point cuts both ways; know which regime you are in.

Now the disclaimer, and I mean it. These are observations from two specific
studies on two specific vehicles. I am not telling you which architecture to
build, I am not saying anything about what SK hynix does today, and nothing here
is a recommendation about a product.

KEY NUMBERS: none — this is the method summary.

TRANSITION: The limitations, consolidated in one place.

If asked: Does this transfer to HBM stacks specifically — the method does; the
numbers do not, because the vehicle is different. The DVPD study is a logic die
with a distributed regulator, not a memory stack.
""")


@main
def s_limits(s, n):
    chrome(s, "Limitations, in one place", "limitations", "RED", n)
    rows = [["Area", "Limitation"],
            ["Transient", "Cross-solver verification only — no experimental "
                          "validation of either study"],
            ["Transient", f"{T['ratio_400']:.1f}× applies to matched repeated stepping; "
                          f"one steady solve is ~{T['steady_ratio']:.0f}× slower"],
            ["Transient", "Policy traces are the published EPEPS result, produced "
                          "before a later solver correction and not rerun"],
            ["Realizability", "GEOMETRICALLY REALIZABLE / PROCESS-CONDITIONAL — "
                              "microvia current allowable, capture-pad diameter and "
                              "a vendor design rule remain OPEN"],
            ["Mechanics", "Δε_in is a response, not damage. No fatigue model, no "
                          "life, no mechanical pass/fail"],
            ["Mechanics", "Magnitude conditional: constitutive card evaluated far "
                          "outside its fitted stress window; tolerance bracket is "
                          "one-sided"],
            ["Thermal / EM", "Correlation-based channel cooling, no conjugate CFD; "
                             "a full-wave HFSS attempt did not converge"],
            ["Scope", "A frozen two-point comparison — not an optimiser result, and "
                      "no claim that mechanics moves the system optimum"]]
    table(s, rows, top=TOP + 0.02, size=13.5, accent="RED", colw=[1, 4.6])
    notes(s, f"""
[~85 s]

I would rather you heard all of these from me than found them afterwards.

The two biggest, in my view. First, neither study is validated against
measurement. Everything is cross-code verification and internal consistency.

Second, the mechanical magnitude is conditional. The ordering is robust — it
survived the decomposition and the tolerance ladder — but the absolute response
number rests on a constitutive card being used far outside the stress range it was
fitted over. I would defend the sign of the effect. I would not defend the third
digit.

And the two I get asked about most: realizability is geometric and
process-conditional with three inputs still open; and the full-wave HFSS attempt
did not converge, so there is no electromagnetic result here.

KEY NUMBERS: 3 OPEN process inputs; one-sided tolerance bracket; {T['steady_ratio']:.0f}× slower on one steady solve.

TRANSITION: Let me close.

If asked: Which limitation would you fix first — the constitutive data for the
solder, because it is the one that currently caps what the mechanical result can
be used for.
""")


@main
def s_summary(s, n):
    chrome(s, "Summary", "close", "GRY", n)
    bullets(s, [
        f"A repeated-transient electrothermal solver, verified against MOOSE and "
        f"Icepak to ≤ {T['fv_max_K']:.3f} K, {T['ratio_400']:.1f}× faster on matched "
        f"{T['crossover']['steps'][-1]}-step stepping — and ~{T['steady_ratio']:.0f}× "
        f"slower on one steady solve",
        f"A frozen two-point DVPD comparison on one geometry: Z2 runs {S.DT:+.2f} K "
        f"hotter yet carries {S.RED_U:.1f} % less driver and {S.RED_E:.1f} % less "
        f"local solder response",
        f"Buildability predicted by conductor-plane topology: a tier permutation "
        f"takes the worst via aspect ratio {S.AR['baseline_T1']:.2f} → "
        f"{S.AR['repartition_C1']:.3f} at constant parts, area and stack height",
        "Both halves make one point: evaluate power delivery on the physical "
        "package, at the timescale the system runs",
    ], top=TOP + 0.10, size=18.5, gap=0.34)
    takeaway(s, "A response is not damage, damage is not life, and a thermal proxy "
                "can rank two architectures backwards.", "GRY")
    notes(s, f"""
[~85 s]

To close.

Part one: a transient electrothermal solver that is verified against two
independent codes to within half a kelvin, and that is {T['ratio_400']:.1f} times faster when you
need to march the same transient many times — which is the case that matters for
gating policy studies. It is slower for a single steady solve, and I would rather
you remembered both halves of that sentence.

Part two: a controlled two-point comparison of where the regulator sits, frozen
before solving, evaluated on one geometry across four domains. The result is that
the hotter architecture is the one with the lower local mechanical response, which
is the opposite of what a thermal proxy predicts.

And the realizability result, which I think travels furthest: the right invariant
for buildability was conductor-plane topology, and a pure permutation moved the
worst aspect ratio by a factor of six.

The thread through all of it is the last line on the screen.

KEY NUMBERS: {T['fv_max_K']:.3f} K; {T['ratio_400']:.2f}×; {S.DT:+.2f} K; {S.RED_E:.1f} %; AR {S.AR['baseline_T1']:.2f}→{S.AR['repartition_C1']:.3f}.

TRANSITION: Happy to take questions — and there is backup material behind this.

If asked: What is next — an instrumented vehicle for validation, and solder creep
data at the operating stress level.
""")


@main
def s_questions(s, n):
    bar = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(W), Inches(0.10))
    bar.fill.solid(); bar.fill.fore_color.rgb = GRY; bar.line.fill.background()
    bar.shadow.inherit = False
    textbox(s, "Questions", MARG, 2.55, CW, 1.2, 48, bold=True, color=INK)
    textbox(s, "Backup slides follow: frozen pair tables, loss ledger, routing "
               "feasibility,\ntolerance ladder, mesh convergence, platform and "
               "reproducibility.",
            MARG, 3.85, CW - 1.0, 1.2, 19, color=GRY, space=1.25)
    textbox(s, "mgharib5/HVR_OPT   ·   tag paper-freeze-r3c", MARG, 5.35, CW, 0.4,
            15, color=LGY)
    textbox(s, str(n), W - MARG - 0.9, 7.03, 0.9, 0.30, 11, color=LGY,
            align=PP_ALIGN.RIGHT)
    notes(s, """
[~15 s]

Thank you — happy to take questions. There are backup slides with the full tables
behind this if anything needs digging into.

If asked: anything — see the backup deck.
""")


# ============================================================ BACKUP
def _bk(s, title, n):
    chrome(s, title, f"backup B{n}", "GRY", None, tag="backup")


@back
def b_pair(s, n):
    _bk(s, "B1 — The frozen pair, every reported quantity", n)
    rows = [["Quantity", "Z1 embedded", "Z2 backside", "Δ"],
            ["P_electronics (W)", f"{Z1['P_elec']:.3f}", f"{Z2['P_elec']:.3f}",
             f"{Z2['P_elec']-Z1['P_elec']:+.3f}"],
            ["T_max (°C)", f"{Z1['T_max']:.2f}", f"{Z2['T_max']:.2f}", f"{S.DT:+.2f}"],
            ["T_mean (°C)", f"{Z1['T_mean']:.2f}", f"{Z2['T_mean']:.2f}",
             f"{Z2['T_mean']-Z1['T_mean']:+.2f}"],
            ["T_joint (°C)", f"{Z1['T_joint']:.3f}", f"{Z2['T_joint']:.3f}",
             f"{S.DTJ:+.2f}"],
            ["die warpage P-V (µm)", f"{Z1['die_warp']:.3f}", f"{Z2['die_warp']:.3f}",
             f"{Z2['die_warp']-Z1['die_warp']:+.3f}"],
            ["pkg warpage P-V (µm)", f"{Z1['pkg_warp']:.3f}", f"{Z2['pkg_warp']:.3f}",
             f"{Z2['pkg_warp']-Z1['pkg_warp']:+.3f}"],
            ["driver Δu_c (µm)", f"{Z1['du_c']:.4f}", f"{Z2['du_c']:.4f}",
             f"{S.RED_U:.2f} % less"],
            ["response Δε_in (×10⁻²)", f"{Z1['d_eps']*1e2:.4f}",
             f"{Z2['d_eps']*1e2:.4f}", f"{S.RED_E:.2f} % less"],
            ["P_TSV (W)", f"{Z1['P_tsv']:.5f}", f"{Z2['P_tsv']:.5f}", "—"],
            ["h_sub (mm)", f"{S.H_SUB_MM['Z1']:.2f}", f"{S.H_SUB_MM['Z2']:.2f}", "—"],
            ["TSV path (µm)", f"{S.H_TSV_UM['Z1']:.0f}", f"{S.H_TSV_UM['Z2']:.0f}", "—"],
            ["wall time (s)", f"{Z1['wall_s']:.1f}", f"{Z2['wall_s']:.1f}", "—"]]
    table(s, rows, top=TOP + 0.02, size=12.5, accent="ORA", colw=[2.1, 1, 1, 1.1])
    notes(s, f"D_u = {S.D_U:.4f}, D_ε = {S.D_EPS:.4f}. "
             f"Source: results/phase0mr3c/final_etm_replay.csv, "
             f"final_local_response.csv, local_submodel_inputs.csv.")


@back
def b_ledger(s, n):
    _bk(s, "B2 — Full converter loss ledger", n)
    terms = [k for k in S.LOSS["Z1"] if S.LOSS["Z1"][k] or S.LOSS["Z2"][k]]
    rows = [["Term (W)", "Z1", "Z2", "Z2 − Z1"]]
    for k in terms:
        a, b = S.LOSS["Z1"][k], S.LOSS["Z2"][k]
        rows.append([k.replace("P_", ""), f"{a:.4f}", f"{b:.4f}", f"{b-a:+.4f}"])
    rows.append(["TOTAL", f"{Z1['P_elec']:.3f}", f"{Z2['P_elec']:.3f}",
                 f"{Z2['P_elec']-Z1['P_elec']:+.3f}"])
    table(s, rows, top=TOP + 0.02, size=12, accent="ORA", colw=[2.2, 1, 1, 1])
    notes(s, "Scope ELECTRONICS, per-system. Source: "
             "results/phase0mr3c/final_loss_ledger.csv. The aggregate "
             "P_total_electronics row is excluded to avoid double counting.")


@back
def b_nets(s, n):
    _bk(s, "B3 — Routing feasibility, per net", n)
    rows = [["Net", "depth (µm)", "I agg (A)", "AR", "n req", "n avail"]]
    for cand in ("baseline_T1", "repartition_C1"):
        for net, d in S.NETS[cand].items():
            rows.append([f"{cand.split('_')[0][:4]} · {net}",
                         f"{d['depth']:.0f}", f"{d.get('i', float('nan')):.3f}"
                         if d.get('i') is not None else "—",
                         f"{d['ar']:.3f}", d.get("n_req", "—"), d.get("n_av", "—")])
    table(s, rows, top=TOP + 0.02, size=12, accent="ORA",
          colw=[2.2, 1, 1, 0.8, 0.8, 0.9])
    notes(s, f"Worst AR {S.AR['baseline_T1']:.3f} → {S.AR['repartition_C1']:.3f} at "
             f"150 µm pitch. n_required is FRAMEWORK PROVISIONING at "
             f"J_design = 1e8 A/m², a design-side allocation — NOT a manufacturing "
             f"qualification. Source: results/phase0mr3c/routing_feasibility.csv.")


@back
def b_cetol(s, n):
    _bk(s, "B4 — Integration-tolerance ladder, every attempt", n)
    rows = [["CETOL", "converged", "increments", "D_ε"]]
    for c in S.CETOL:
        rows.append([f"{c['cetol']:g}", "yes" if c["converged"] else "NO",
                     c["incr"] or "0",
                     f"{c['d_eps']:.6f}" if c["d_eps"] else "—"])
    table(s, rows, top=TOP + 0.02, size=14, accent="PUR", colw=[1, 1, 1, 1.2])
    takeaway(s, "Bracket is ONE-SIDED. Once CETOL is loose enough to start, the "
                "step schedule binds — not the tolerance.", "RED")
    notes(s, "Source: results/phase0mr3c/cetol_final_pair.csv, "
             "manuscript/CETOL_FINAL_PAIR_ROBUSTNESS.md. The two converged runs are "
             "bit-identical in Δε_in, strain range and inelastic work for both "
             "architectures, with zero cutbacks.")


@back
def b_decomp(s, n):
    _bk(s, "B5 — Response decomposition, the two cross cases", n)
    d = S.DECOMP
    rows = [["Case", "Δε_in (×10⁻²)", "vs Z1"],
            ["Z1 — reference", f"{d['z1']*1e2:.4f}", "—"],
            ["Z2 displacement at Z1 joint temperature", f"{d['du_only']*1e2:.4f}",
             f"{100*(d['du_only']/d['z1']-1):+.2f} %"],
            ["Z1 displacement at Z2 joint temperature", f"{d['T_only']*1e2:.4f}",
             f"{100*(d['T_only']/d['z1']-1):+.2f} %"],
            ["Z2 — both", f"{d['z2']*1e2:.4f}", f"{100*(d['z2']/d['z1']-1):+.2f} %"]]
    table(s, rows, top=TOP + 0.10, size=14, accent="PUR", colw=[3, 1.2, 1])
    notes(s, "Source: results/phase0mr3c/local_response_decomposition.csv. The two "
             "effects oppose and do not superpose exactly, as expected for a "
             "nonlinear creep response.")


@back
def b_crossover(s, n):
    _bk(s, "B6 — Transient crossover, step by step", n)
    c = T["crossover"]
    rows = [["steps", "this work FV (s)", "MOOSE (s)", "ratio"]]
    for i, st in enumerate(c["steps"]):
        rows.append([st, f"{c['fv_total_s'][i]:.1f}", f"{c['moose_total_s'][i]:.1f}",
                     f"{c['moose_total_s'][i]/c['fv_total_s'][i]:.2f}×"])
    rows.append(["1 steady solve", f"{T['steady_fv_s']:.1f}",
                 f"{T['steady_moose_s']:.1f}", f"{1/T['steady_ratio']:.3f}×"])
    table(s, rows, top=TOP + 0.08, size=14, accent="BLU", colw=[1.4, 1.3, 1, 1])
    takeaway(s, "The advantage grows with step count — and inverts for a single "
                "steady solve.", "BLU")
    notes(s, f"One core, interleaved runs so machine load is shared; per-point load "
             f"averages are recorded in the artifact. MOOSE deck: "
             f"{c['moose_deck']}. Source: OTAPM revision_jetcas_2026-09-19 "
             f"results/ectc_package/perf_tables.json.")


@back
def b_threetool(s, n):
    _bk(s, "B7 — Steady three-tool comparison", n)
    figure(s, "epeps/f5_steady_three_tool.png", top=TOP + 0.05, maxh=4.5)
    notes(s, f"FV max deviation {T['fv_max_K']:.4f} K, Icepak max {T['icepak_max_K']:.4f} K "
             f"against the MOOSE finite-element reference. Icepak mesh "
             f"{T['icepak_cells']:,} cells. Verification, not validation.")


@back
def b_meshladder(s, n):
    _bk(s, "B8 — Mesh refinement ladder", n)
    figure(s, "epeps/b3_mesh_ladder.png", top=TOP + 0.20, maxh=4.2)
    notes(s, "Reproduced from the published EPEPS 2026 material. The answer stops "
             "moving under refinement; the reported configuration sits on the flat "
             "part of the ladder.")


@back
def b_ladder(s, n):
    _bk(s, "B9 — Policy outcome summary (published, not rerun)", n)
    figure(s, "epeps/f9_workload.png", top=TOP + 0.10, maxh=4.1)
    takeaway(s, PNR["provenance"], "RED", size=14.5)
    notes(s, f"{PNR['violations_before']} thermal-limit violations under the "
             f"energy-greedy policy, {PNR['violations_after']} under the "
             f"feasibility-screened policy, over {PNR['epochs']} epochs, at "
             f"{PNR['leakage_overhead_pct']:.1f} % mean idle-leakage overhead. "
             f"Produced before the post-publication solver correction and NOT rerun.")


@back
def b_models(s, n):
    _bk(s, "B10 — Notation and vocabulary", n)
    rows = [["Term", "Meaning in this talk"],
            ["DVPD", "distributed vertical power delivery — convert close to the "
                     "load so the high-current rail is short"],
            ["Z1 / Z2", "the two frozen placements: regulator embedded in the "
                        "substrate / as a backside chiplet"],
            ["h_sub", "package substrate thickness"],
            ["TSV path", "the part of the substrate the vertical interconnect "
                         "actually crosses — not the same as h_sub for Z1"],
            ["warpage (P-V)", "peak-to-valley out-of-plane deformation of the "
                              "whole die or package"],
            ["Δu_c  (driver)", "relative displacement across the critical solder "
                               "joint — what the joint actually sees"],
            ["Δε_in  (response)", "inelastic strain increment per thermal cycle — "
                                  "a RESPONSE, not damage and not life"],
            ["D_u , D_ε", "Z1/Z2 ratios of driver and response"],
            ["CETOL", "CalculiX creep strain-increment tolerance (*VISCO)"],
            ["aspect ratio (AR)", "via depth ÷ via diameter — the buildability "
                                  "measure for a build-up microvia"],
            ["matched stepping", "same problem size, same mesh, same output "
                                 "responsibility, same step count"],
            ["oracle", "the transient thermal model consulted inside the policy "
                       "loop"]]
    table(s, rows, top=TOP + 0.02, size=12.5, accent="GRY", colw=[1.3, 3.5])
    notes(s, "Kept in backup because the audience spans packaging, PI, thermal "
             "and architecture; these are the terms most often used differently "
             "across those groups.")


@back
def b_converter(s, n):
    _bk(s, "B11 — Converter design point", n)
    C = S.CONVERTER
    rows = [["Parameter", "Value"],
            ["input / intermediate / output", f"{C['V_in']:.0f} V → {C['V_mid']:.0f} V "
                                              f"→ {C['V_out']:.0f} V"],
            ["first stage", f"{C['V_in']/C['V_mid']:.0f}:1 switched capacitor"],
            ["second stage", f"{C['N']}-phase buck"],
            ["cells M", f"{C['M']}"],
            ["current per cell", f"{C['I_cell']:.3f} A"],
            ["area per cell", f"{C['A_cell']:.2f} mm²"],
            ["duty ratio D", f"{C['D']:.4f}"],
            ["switching frequency", f"{C['f_sw_kHz']:.2f} kHz"],
            ["die", f"{S.DIE_MM:.2f} × {S.DIE_MM:.2f} mm"],
            ["stack height", f"{S.STACK_UM:.0f} µm"]]
    table(s, rows, top=TOP + 0.02, size=13.5, accent="ORA", colw=[2, 1.6])
    notes(s, "Identical in Z1 and Z2. Source: the frozen pair configs and the "
             "compiled converter design in the R3C replay.")


@back
def b_cooling(s, n):
    _bk(s, "B12 — Microchannel cooling design point", n)
    C = S.COOLING
    rows = [["Parameter", "Value"],
            ["channels", f"{C['channels']}"],
            ["channel w × h", f"{C['w_um']} × {C['h_um']} µm"],
            ["coolant", f"water, {C['T_in_C']:.0f} °C inlet"],
            ["mass flow", f"{C['m_dot_g_s']:.1f} g/s"],
            ["Reynolds number", f"{C['Re']:.1f}  (laminar)"],
            ["effective coefficient", f"{C['h_eff_kW']:.1f} kW/m²K"],
            ["coolant temperature rise", f"{C['dT_K']:.3f} K"],
            ["pressure drop", f"{C['dp_MPa']:.4f} MPa"],
            ["pump power", f"{C['P_pump_W']:.3f} W"],
            ["pump power / converter loss",
             f"{100*C['P_pump_W']/Z1['P_elec']:.1f} %"]]
    table(s, rows, top=TOP + 0.02, size=13.5, accent="BLU", colw=[2, 1.6])
    notes(s, "Correlation-based channel model. There is NO conjugate CFD "
             "validation in this work — stated as a limitation, not hidden.")


@back
def b_realiz(s, n):
    _bk(s, "B13 — What “geometrically realizable” means here", n)
    rows = [["Input", "Status"],
            ["microvia pitch (150 µm)", "SOURCE_BOUNDED — published production "
                                        "practice for microvias to embedded dies"],
            ["stacking topology", "SOURCE_BOUNDED — one via level per net"],
            ["landing area", "SOURCE_BOUNDED — from the device datasheet"],
            ["microvia diameter (120 µm)", "OPEN — no substrate diameter rule was "
                                           "reachable"],
            ["microvia current allowable", "OPEN"],
            ["capture-pad diameter", "OPEN"],
            ["vendor design rule", "OPEN"],
            ["cavity sidewall / cooler standoff", "OPEN (2 package clearances)"]]
    table(s, rows, top=TOP + 0.02, size=13, accent="RED", colw=[1.6, 3.2])
    takeaway(s, "Verdict: GEOMETRICALLY REALIZABLE / PROCESS-CONDITIONAL. "
                "PROVEN_REALIZABLE is not available and is not claimed.", "RED")
    notes(s, "Source: configs/phase0mr3c/frozen_pair_Z1.yaml and _Z2.yaml, "
             "manufacturing_status block, verbatim.")


@back
def b_prov(s, n):
    _bk(s, "B14 — Provenance of the policy result", n)
    rows = [["Item", "Value"],
            ["epochs", f"{PNR['epochs']}"],
            ["violations before screening", f"{PNR['violations_before']}"],
            ["violations after screening", f"{PNR['violations_after']}"],
            ["leakage overhead", f"{PNR['leakage_overhead_pct']:.1f} %"],
            ["greedy peak (oracle / Ansys)",
             f"{P['greedy_oracle']:.2f} / {P['greedy_ansys']:.2f} °C"],
            ["screened peak (oracle / Ansys)",
             f"{P['screened_oracle']:.2f} / {P['screened_ansys']:.2f} °C"],
            ["HBM limit used", f"{P['hbm_limit_C']:.0f} °C"]]
    table(s, rows, top=TOP + 0.05, size=13.5, accent="BLU", colw=[2, 1.6])
    takeaway(s, PNR["provenance"], "RED", size=14.5)
    notes(s, "These traces were NOT rerun after the post-publication solver "
             "correction. The verification and runtime numbers in the main deck "
             "WERE rerun. Stated explicitly so the two are not conflated.")


@back
def b_platform(s, n):
    _bk(s, "B15 — Platform and reproducibility", n)
    pl = S.PLATFORM
    rows = [["Item", "Value"]]
    for k in ("host", "os", "cpu", "logical_cpus", "ram", "python", "numpy",
              "scipy", "calculix", "moose", "gpu_used", "solver_threads"):
        if k in pl:
            rows.append([k.replace("_", " "), str(pl[k])])
    table(s, rows, top=TOP + 0.02, size=12.5, accent="GRY", colw=[1.4, 3])
    notes(s, "Source: results/phase0mr3c/platform.json. Repository "
             "github.com/mgharib5/HVR_OPT, tag paper-freeze-r3c. "
             "REPRODUCE.md gives the build recipe and per-artifact runtimes.")
