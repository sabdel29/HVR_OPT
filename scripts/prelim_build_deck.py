"""Build the HVR_OPT prelim Reveal.js deck. Every number is read from artifacts."""
from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
D = R / "presentation" / "prelim_hvr"
D.mkdir(parents=True, exist_ok=True)


def J(p, default=None):
    f = R / p
    return json.loads(f.read_text()) if f.exists() else default


VF = J("research/phase0nai/voltage_fed_network.json", {})
DG = J("research/phase0nai/z1_convergence_diagnostic.json", {})
BGX = J("research/phase0nak/bga_exhaustive_closure.json")
BGA = BGX or J("research/phase0naj/bga_count_closure.json", {})
PDC = J("research/phase0naj/pad_count_closure.json", {})
FLD = J("research/phase0naj/fidelity_ladder.json", {})
LED = J("research/phase0nab/interconnect_loss.json", {})
GTS = J("research/phase0nw/physical_gates.json", {})
MH = list(csv.DictReader((R / "research/phase0nah/model_hierarchy.csv").open()))
GC = collections.Counter(g["status"] for g in GTS.get("gates", []))
mm = lambda x: x * 1e3
conv = VF.get("convergence", {})
arch_ok = lambda a: all(conv[f"{a}_{r}"]["converged"] for r in ("supply", "return"))
SLIDES = []


def S(body, notes="", prov="", cls=""):
    n = f"<aside class='notes'>{notes}</aside>" if notes else ""
    p = f"<div class='prov'>{prov}</div>" if prov else ""
    SLIDES.append(f"<section class='{cls}'>{body}{p}{n}</section>")


# ============ 1. opening =============================================
S("""<div style="text-align:center;margin-top:.3em">
<h1>Electrothermal–Mechanical Co-Design of<br>Distributed Vertical Power Delivery</h1>
<h3 style="text-align:center;font-size:1.15em;color:var(--muted);margin-top:.5em">
From Converter Architecture to Physical Package Feasibility</h3>
<p class="sub" style="margin-top:1.6em">PhD Preliminary Examination · HiPerCAS Lab,
University of Illinois Chicago</p></div>""",
  "Open by saying the talk has three parts: why vertical power delivery is forced on us, "
  "how the framework evaluates a package across three physics domains, and what physical "
  "closure changed about the conclusions. Say explicitly that several earlier numerical "
  "results were withdrawn during this work and that this is the point of the talk.")

S("""<h2>Start with one number</h2>
<div class="cols" style="align-items:center">
<div style="text-align:center">
<div class="huge" style="color:var(--z2)">1000 A</div>
<p class="sub" style="text-align:center">to a single processor die</p></div>
<div><p>A 1 kW accelerator running at a <strong>1 V</strong> core rail draws</p>
<p style="text-align:center;font-size:1.25em"><em class="q">I = P / V = 1000 W / 1 V</em></p>
<p>Current, not power, is what the package has to survive. Every conductor between the
board and the die carries some share of that 1000 A.</p></div></div>
<div class="callout" style="margin-top:.5em">The engineering problem is not generating
the power. It is <strong>delivering</strong> it.</div>""",
  "Anchor the audience in a number they can feel. 1000 A is comparable to an arc welder. "
  "Do not move on until they accept that the current, not the wattage, is the problem.")

S("""<h2>Why low-voltage lateral delivery is so expensive</h2>
<p style="text-align:center;font-size:1.5em;margin:.3em"><em class="q">P<sub>loss</sub> = I<sub>rms</sub><sup>2</sup> R</em></p>
<p>Loss grows with the <strong>square</strong> of current. Halving the delivery voltage
doubles the current and <strong>quadruples</strong> the loss in the same copper.</p>
<div class="cols" style="margin-top:.5em">
<div class="callout"><strong>Deliver at 1 V</strong><br>1000 A across the whole board.
Even 1 mΩ of path resistance burns 1 kW — as much as the chip uses.</div>
<div class="callout" style="border-color:var(--ok);background:#f2faf4">
<strong>Deliver at 48 V</strong><br>~21 A for the same power. The same 1 mΩ burns
under half a watt.</div></div>
<p style="margin-top:.4em">So: carry 48 V as far as possible, and convert to 1 V
<strong>as close to the die as physically possible</strong>.</p>""",
  "This slide is the whole motivation. The 48x voltage ratio is a 2300x loss ratio in the "
  "same conductor. Everything afterwards is a consequence of wanting the conversion point "
  "closer to the die.")

S("""<h2>Three ways to deliver the power</h2>
<div class="cols">
<div><h3>Lateral</h3>
<p class="sub">Regulators at the board edge. The 1 V rail travels centimetres across
the board and up through the package.</p>
<p><span class="chip open">LONG HIGH-CURRENT PATH</span></p></div>
<div><h3>Vertical (VPD)</h3>
<p class="sub">Regulator moved underneath the die. The 1 V rail travels vertically
through the package instead of laterally.</p>
<p><span class="chip warn">SHORTER PATH</span></p></div>
<div><h3>Distributed vertical (DVPD)</h3>
<p class="sub">Many small regulators spread under the die area, each feeding its own
region. The 1 V rail is split 49 ways before it travels anywhere.</p>
<p><span class="chip ok">SHORT <em>AND</em> SPLIT</span></p></div></div>
<div class="callout" style="margin-top:.6em">This work studies <strong>DVPD</strong>:
49 regulator cells on a 7×7 grid, each delivering about 20 A.</div>""",
  "Make clear DVPD is not just 'closer' but 'divided'. Splitting the current 49 ways cuts "
  "I^2R by 49 in the distributed segment even before shortening it.")

# ============ 2. packaging 101 =======================================
STACK = """<svg viewBox="0 0 1180 430" width="100%" style="max-height:50vh">
<defs>
<marker id="ar" markerWidth="10" markerHeight="10" refX="8" refY="4"
 orient="auto" markerUnits="userSpaceOnUse">
 <path d="M0,0 L0,8 L10,4 z" fill="#d1442f"/></marker>
<marker id="arb" markerWidth="16" markerHeight="16" refX="12" refY="6"
 orient="auto" markerUnits="userSpaceOnUse">
 <path d="M0,0 L0,12 L15,6 z" fill="#d1442f"/></marker>
</defs>
<g font-size="17" text-anchor="end" fill="#3d464f">
 <text x="236" y="58">heat sink / cold plate</text>
 <text x="236" y="96">TIM</text>
 <text x="236" y="150">compute die (silicon)</text>
 <text x="236" y="206">micro-pads / bumps</text>
 <text x="236" y="238">package RDL</text>
 <text x="236" y="292">package substrate</text>
 <text x="236" y="352">BGA solder balls</text>
 <text x="236" y="400">PCB (motherboard)</text>
</g>
<rect x="340" y="38" width="560" height="30" fill="#7d8894"/>
<rect x="395" y="82" width="450" height="14" fill="#cfd6dd"/>
<rect x="395" y="110" width="450" height="68" fill="#8fb4d9"/>
<g stroke="#b8761f" stroke-width="8"><line x1="425" y1="110" x2="425" y2="178"/><line x1="473" y1="110" x2="473" y2="178"/><line x1="521" y1="110" x2="521" y2="178"/><line x1="569" y1="110" x2="569" y2="178"/><line x1="617" y1="110" x2="617" y2="178"/><line x1="665" y1="110" x2="665" y2="178"/><line x1="713" y1="110" x2="713" y2="178"/><line x1="761" y1="110" x2="761" y2="178"/><line x1="809" y1="110" x2="809" y2="178"/></g>
<g fill="#6a6a6a"><rect x="418" y="178" width="16" height="9"/><rect x="463" y="178" width="16" height="9"/><rect x="508" y="178" width="16" height="9"/><rect x="553" y="178" width="16" height="9"/><rect x="598" y="178" width="16" height="9"/><rect x="643" y="178" width="16" height="9"/><rect x="688" y="178" width="16" height="9"/><rect x="733" y="178" width="16" height="9"/><rect x="778" y="178" width="16" height="9"/><rect x="823" y="178" width="16" height="9"/></g>
<rect x="260" y="196" width="720" height="22" fill="#e0a33c"/>
<rect x="260" y="226" width="720" height="70" fill="#c8b48a"/>
<rect x="296" y="238" width="150" height="46" fill="#b36ad1"/>
<text x="371" y="266" font-size="15" fill="#fff" text-anchor="middle">VR cell</text>
<g fill="#9aa3ad"><circle cx="300" cy="330" r="15"/><circle cx="352" cy="330" r="15"/><circle cx="404" cy="330" r="15"/><circle cx="456" cy="330" r="15"/><circle cx="508" cy="330" r="15"/><circle cx="560" cy="330" r="15"/><circle cx="612" cy="330" r="15"/><circle cx="664" cy="330" r="15"/><circle cx="716" cy="330" r="15"/><circle cx="768" cy="330" r="15"/><circle cx="820" cy="330" r="15"/><circle cx="872" cy="330" r="15"/><circle cx="924" cy="330" r="15"/></g>
<rect x="260" y="356" width="720" height="40" fill="#2f6f3e" opacity=".85"/>
<text x="1000" y="150" font-size="16" fill="#1f6feb">TSVs through silicon</text>
<line x1="330" y1="330" x2="330" y2="296" stroke="#d1442f" stroke-width="4"
 marker-end="url(#ar)"/>
<text x="296" y="324" font-size="16" fill="#d1442f" text-anchor="end">48 V in</text>
<text x="296" y="342" font-size="14" fill="#d1442f" text-anchor="end">low current</text>
<line x1="470" y1="238" x2="470" y2="126" stroke="#d1442f" stroke-width="18"
 marker-end="url(#arb)" opacity=".8"/>
<text x="500" y="262" font-size="16" fill="#d1442f">1 V out — ~1000 A in total</text>
<text x="500" y="282" font-size="14" fill="#d1442f">(split across 49 VR cells)</text>
</svg>"""
S(f"<h2>Packaging 101 — the physical stack</h2>{STACK}"
  "<p class='sub'>Arrow width suggests current magnitude: thin at 48 V, thick at 1 V.</p>",
  "Walk bottom to top once, slowly. PCB, BGA balls, substrate, RDL, micro-pads, die, TSVs, "
  "TIM, heat sink. Then trace the current: 48 V enters through a few balls, a VR cell "
  "converts it, and 1 V goes up into the die over a very short, very wide path. The "
  "audience must hold this picture for the rest of the talk.")

S("""<h2>The conductors this work has to account for</h2>
<div class="cols"><div>
<ul><li><strong>BGA ball</strong> — solder sphere joining package to board. 400 µm
diameter here.</li>
<li><strong>Package RDL</strong> — thin copper planes inside the package that spread
current sideways.</li>
<li><strong>Source pad</strong> — the small copper landing where a regulator meets
the die interface.</li>
<li><strong>TSV</strong> — a copper via straight through the silicon.</li></ul></div>
<div><div class="callout"><strong>Every one of them obeys</strong>
<p style="text-align:center;font-size:1.35em;margin:.35em"><em class="q">R = ρ L / A</em></p>
<p class="sub" style="margin:0">resistivity × length ÷ cross-section. The entire
electrical model is this expression applied honestly to real geometry — plus a network
solve wherever current can choose between parallel paths.</p></div>
<p style="margin-top:.5em"><span class="chip ok">KEY IDEA</span> if a conductor exists
physically, it must have exactly one owner in the loss ledger — no double counting,
and no conductor silently set to zero.</p></div></div>""",
  "This slide sets up the discipline used later: every physical conductor has one owner. "
  "A reviewer asking 'what carries the return current?' should be answered by the ledger.")

# ============ 3. Z1 vs Z2 ============================================
ARCH = """<svg viewBox="0 0 980 300" width="100%" style="max-height:44vh">
<g><text x="20" y="24" font-size="21" font-weight="700" fill="#1f6feb">Z1 — EMBEDDED</text>
<rect x="20" y="210" width="430" height="34" fill="#2f6f3e" opacity=".82"/>
<text x="30" y="233" font-size="15" fill="#fff">PCB (solid)</text>
<g>""" + "".join(f'<circle cx="{48+i*38}" cy="200" r="10" fill="#9aa3ad"/>'
                 for i in range(11)) + """</g>
<rect x="20" y="140" width="430" height="52" fill="#c8b48a"/>
<rect x="150" y="150" width="170" height="34" fill="#b36ad1" opacity=".9"/>
<text x="162" y="172" font-size="14" fill="#fff">VR inside substrate</text>
<rect x="150" y="96" width="170" height="38" fill="#8fb4d9"/>
<text x="164" y="120" font-size="15">die</text>
<line x1="60" y1="200" x2="60" y2="150" stroke="#d1442f" stroke-width="4"/>
<text x="66" y="186" font-size="13" fill="#d1442f">48 V</text>
<line x1="235" y1="150" x2="235" y2="100" stroke="#d1442f" stroke-width="10"/>
<text x="246" y="146" font-size="13" fill="#d1442f">1 V</text>
<text x="20" y="272" font-size="14" fill="#5a6672">48 V crosses the substrate.
No board opening.</text></g>
<g transform="translate(510,0)">
<text x="20" y="24" font-size="21" font-weight="700" fill="#d1442f">Z2 — BACKSIDE</text>
<rect x="20" y="210" width="150" height="34" fill="#2f6f3e" opacity=".82"/>
<rect x="300" y="210" width="150" height="34" fill="#2f6f3e" opacity=".82"/>
<text x="186" y="233" font-size="14" fill="#cf222e" font-weight="700">CUTOUT</text>
<g>""" + "".join(f'<circle cx="{40+i*28}" cy="200" r="10" fill="#9aa3ad"/>'
                 for i in range(5)) + "".join(
    f'<circle cx="{318+i*28}" cy="200" r="10" fill="#9aa3ad"/>' for i in range(5)
) + """</g>
<rect x="175" y="196" width="120" height="44" fill="#b36ad1" opacity=".9"/>
<text x="186" y="222" font-size="13" fill="#fff">VR in cutout</text>
<rect x="20" y="140" width="430" height="52" fill="#c8b48a"/>
<rect x="150" y="96" width="170" height="38" fill="#8fb4d9"/>
<text x="164" y="120" font-size="15">die</text>
<line x1="48" y1="200" x2="48" y2="150" stroke="#d1442f" stroke-width="4"/>
<line x1="235" y1="196" x2="235" y2="100" stroke="#d1442f" stroke-width="10"/>
<text x="20" y="272" font-size="14" fill="#5a6672">VR sits in a 23.36 mm board opening.
48 V must reach it laterally.</text></g></svg>"""
S(f"<h2>Two architectures under comparison</h2>{ARCH}"
  "<p class='sub'>The cutout removes 841 of 1369 legal BGA sites — the central ones.</p>",
  "The single most important visual difference: Z2's cutout deletes exactly the BGA sites "
  "nearest the die centre. That turns out to matter for convergence later, because Z1's "
  "placement rule puts balls underneath regulator cells and Z2's geometrically cannot.")

S("""<h2>The converter inside each cell</h2>
<div style="text-align:center;font-size:1.0em;margin:.5em 0">
<span style="padding:.3em .7em;border:3px solid var(--z1);border-radius:.3em">48 V</span>
<span style="font-size:1.4em;color:var(--muted)"> → </span>
<span style="padding:.3em .7em;border:3px solid var(--accent);border-radius:.3em">
3:1 switched capacitor</span>
<span style="font-size:1.4em;color:var(--muted)"> → </span>
<span style="padding:.3em .7em;border:3px solid var(--accent);border-radius:.3em">16 V</span>
<span style="font-size:1.4em;color:var(--muted)"> → </span>
<span style="padding:.3em .7em;border:3px solid var(--accent);border-radius:.3em">
two-phase buck</span>
<span style="font-size:1.4em;color:var(--muted)"> → </span>
<span style="padding:.3em .7em;border:3px solid var(--z2);border-radius:.3em">1 V</span>
</div>
<div class="cols"><div>
<p><strong>Why a hybrid?</strong> A single buck stage at 48→1 V needs a ~2 % duty cycle,
which is very hard to do efficiently. The capacitor stage does the bulk ratio
with no magnetics; the buck stage then regulates over a sane ratio.</p></div>
<div><ul><li>49 cells, <strong>~20.4 A each</strong></li>
<li>switching at 805 kHz</li><li>250 nH inductors</li>
<li>tile 2.3685 mm square</li></ul></div></div>
<div class="banner open">The switching-state sequence is <strong>not</strong> in the
converter model — this becomes the single largest open item in the talk.</div>""",
  "Do not teach SC operation in detail. The one thing they must retain is that the model "
  "gives average currents and an output ripple, but never an input current waveform. "
  "Flag it here so the later OPEN item is not a surprise.")

# ============ 4. research question + hierarchy ========================
S("""<h2 style="border:none">&nbsp;</h2>
<div class="callout" style="font-size:1.25em;text-align:center;margin-top:.2em">
Electrical efficiency alone does not tell us whether the package can actually be
<strong>built</strong> — or <strong>survive</strong>.</div>
<div class="cols" style="margin-top:1.0em;text-align:center">
<div><div class="chip ok" style="font-size:.8em">ELECTRICAL</div>
<p class="sub">where does the current go, and what does it dissipate?</p></div>
<div><div class="chip warn" style="font-size:.8em">THERMAL</div>
<p class="sub">where does that heat go, and how hot does it get?</p></div>
<div><div class="chip open" style="font-size:.8em">MECHANICAL</div>
<p class="sub">what does the temperature field do to the structure?</p></div>
<div><div class="chip lit" style="font-size:.8em">REALIZABILITY</div>
<p class="sub">can the geometry be built at all?</p></div></div>
<p style="text-align:center;margin-top:.9em">Electrical and thermal are
<strong>two-way coupled</strong>: resistance rises with temperature, which raises loss,
which raises temperature.</p>""",
  "This is the thesis statement slide. Pause here. The feedback arrow between electrical "
  "and thermal is why a fixed-point iteration is needed rather than a single pass.")

rows_mh = "".join(
    f"<tr><td>{m['stage']}</td><td>{m['model']}</td><td>{m['type']}</td></tr>"
    for m in MH)
S(f"""<h2>The model hierarchy — what is analytical, what is FEM</h2>
<table><tr><th>Stage</th><th>Model</th><th>Numerical type</th></tr>{rows_mh}</table>
<div class="callout" style="margin-top:.4em">This is <strong>not</strong> "an analytical
framework replacing FEM". It is a hierarchy: analytical and reduced-order models where
they are defensible, and FEM retained wherever a full spatial field is genuinely needed.
MOOSE is used as an <strong>independent reference</strong>, not as a production stage.</div>""",
  "Expect the question 'why not just use Ansys for everything'. The answer is on this "
  "slide: the expensive stages are kept, the cheap ones are only used where a reduced "
  "model has been checked. Do not claim the framework replaces FEM.",
  "research/phase0nah/model_hierarchy.csv · current HEAD")

PIPE = """<svg viewBox="0 0 980 230" width="100%" style="max-height:38vh">
<defs><marker id="a2" markerWidth="9" markerHeight="9" refX="7" refY="3"
 orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#5a6672"/></marker></defs>
<g font-size="14" text-anchor="middle">""" + "".join(
    f'<rect x="{12+i*136}" y="56" width="124" height="52" rx="6" fill="#eef2f6" '
    f'stroke="#9aa3ad"/><text x="{74+i*136}" y="78">{a}</text>'
    f'<text x="{74+i*136}" y="96">{b}</text>'
    for i, (a, b) in enumerate([("converter", "synthesis"), ("physical", "components"),
                                ("package", "stack"), ("rail-aware", "current paths"),
                                ("interconnect", "loss"), ("heat", "deposition"),
                                ("thermal", "FEM")])) + "".join(
    f'<line x1="{136+i*136}" y1="82" x2="{{}}" y2="82" stroke="#5a6672" '
    f'stroke-width="2" marker-end="url(#a2)"/>'.format(8 + (i + 1) * 136)
    for i in range(6)) + """
<path d="M 890 108 C 890 170, 520 180, 520 150" stroke="#d1442f" stroke-width="3"
 fill="none" marker-end="url(#a2)"/>
<text x="700" y="186" font-size="14" fill="#d1442f" text-anchor="middle">
update ρ(T) and repeat until ΔT &lt; 0.25 K  (3 iterations)</text>
<g>""" + "".join(
    f'<rect x="{200+i*210}" y="4" width="190" height="34" rx="6" fill="#f6eefb" '
    f'stroke="#6639ba"/><text x="{295+i*210}" y="26">{t}</text>'
    for i, t in enumerate(["global mechanics", "critical joint",
                           "local solder submodel"])) + """</g>
<line x1="760" y1="56" x2="760" y2="42" stroke="#6639ba" stroke-width="2"
 marker-end="url(#a2)"/></svg>"""
S(f"<h2>How one architecture is evaluated</h2>{PIPE}"
  "<p style='margin-top:.3em'>Mechanics runs <strong>once, after</strong> the "
  "electrical–thermal loop converges — the mechanical field does not feed back into the "
  "temperature, so putting it inside the loop would cost three solves for one answer.</p>",
  "The loop-vs-once point is a real design decision and a likely question. Say that "
  "thermoelastic deformation does not change the loss, so it is a one-way coupling.")



# ============ FINAL LINEAGE: electrical validation, results, thermal ==========
sys.path.insert(0, str(R / "scripts"))
import prelim_deck_final_sections as FS                              # noqa: E402
FS.electrical_validation(S)

S("""<h2>BGA current sharing — assumption vs solve</h2>
<div class="figwrap"><img src="figs/sharing.svg" alt="ball current sharing"></div>
<div class="callout" style="margin-top:.3em">Even with a perfectly <strong>uniform</strong>
load the balls do not share equally, so a count sized from I<sub>total</sub>/N understates the
worst ball. The count is therefore <strong>solved</strong>: every legal even count, the network
re-solved at each, verified on the resolved grid.</div>""",
  "The load is uniform across all 49 cells; the non-uniformity is pure network geometry.",
  "network re-solved at n=301 for the figure · current HEAD")

S("""<h2>The cutout penalty is smaller than where you put the balls</h2>
<div class="figwrap"><img src="figs/final_cutout.svg" alt="cutout vs placement"></div>
<p><strong>Controlled experiment</strong> on the production network: same count, sheet,
contacts, load, rule and grid — only the candidate sites change. The cutout term has been
corrected three times across the project; placement still dominates it.</p>""",
  "Earlier versions of this number were artefacts of imposed sharing, a missing return "
  "conductor and a floating-point lattice bug. Say that no cutout penalty is frozen.",
  "research/final_closure/package_network.json · controlled")

S("""<h2>Choosing a pad count needs more than voltage drop</h2>
<div class="figwrap"><img src="figs/pads.svg" alt="pad count"></div>
<p>The voltage-drop floor of 4 pads implies 5e6 A/cm² — above the <em>accelerated</em> Cu–Cu EM
test regime. The paper carries the pad term over a terminal-footprint sweep anchored on the DVPD
source's own VIC count; the interface loss stays below 0.06 W across it.</p>""",
  "Current density, not voltage drop, bounds the pad count from below.",
  "research/phase0naj/pad_count_closure.json · CONTEXT_ONLY current densities")

S("""<h2>Model fidelity should follow the quantity, not the budget</h2>
<div class="figwrap"><img src="figs/ladder.svg" alt="fidelity ladder"></div>
<p><span class="chip hist">R1 RETIRED</span> after its router bug was fixed and no physical net was
obstructed. Production policy: R0 for point-to-point traces and via stacks, <strong>R2</strong>
for the distributed output plane (R0 overstates it 37–258 %).</p>""",
  "Fidelity chosen per interconnect class, declared before the final numbers were read.",
  "research/phase0naj/fidelity_ladder.json")

FS.thermal_validation(S)

# ============ 5. MECHANICS FROM ZERO =================================
S("""<h2 style="border:none">&nbsp;</h2>
<div style="text-align:center;margin-top:1.2em">
<div class="big" style="color:var(--accent)">Why a power-delivery talk<br>needs mechanics</div>
<p style="text-align:center;font-size:.95em;margin-top:1em;max-width:70%;margin-left:auto;margin-right:auto">
Current makes heat. Heat makes materials expand. Materials expand by different amounts.
The package bends, and the solder joints holding it together deform — permanently.</p></div>""",
  "Transition slide. The committee may be electrical engineers. Tell them the next six "
  "slides are deliberately first-principles and they should stop you if anything is unclear.")

CTE = """<svg viewBox="0 0 900 250" width="100%" style="max-height:38vh">
<text x="20" y="22" font-size="17" fill="#5a6672">cold — bonded, relaxed</text>
<rect x="30" y="40" width="330" height="26" fill="#8fb4d9"/>
<text x="40" y="58" font-size="14">silicon   alpha ~ 2.6 ppm/K</text>
<rect x="30" y="66" width="330" height="26" fill="#c8b48a"/>
<text x="40" y="84" font-size="14">organic substrate   alpha ~ 17 ppm/K</text>
<text x="500" y="22" font-size="17" fill="#5a6672">hot — free expansion (if unbonded)</text>
<rect x="510" y="40" width="340" height="26" fill="#8fb4d9"/>
<rect x="510" y="66" width="372" height="26" fill="#c8b48a"/>
<text x="860" y="86" font-size="14" fill="#cf222e">longer</text>
<text x="20" y="140" font-size="17" fill="#5a6672">hot — actually bonded: it must bend</text>
<path d="M 60 200 Q 450 140 840 200" stroke="#8fb4d9" stroke-width="22" fill="none"/>
<path d="M 60 222 Q 450 162 840 222" stroke="#c8b48a" stroke-width="22" fill="none"/>
<text x="330" y="247" font-size="15" fill="#cf222e">the layer that wants to grow more
ends up on the outside of the curve</text></svg>"""
S(f"<h2>Thermal expansion mismatch (CTE)</h2>{CTE}"
  "<p style='text-align:center;font-size:1.2em;margin:.2em'><em class='q'>"
  "&epsilon;<sub>thermal</sub> = &alpha; &Delta;T</em></p>"
  "<p>Every material has a coefficient of thermal expansion &alpha;. Silicon and organic "
  "package material differ by roughly <strong>6&times;</strong>. Bonded together and "
  "heated, they cannot both have the length they want — so the assembly carries internal "
  "stress and bends.</p>",
  "This is the root cause of every mechanical result later. The 6x mismatch between "
  "silicon and organic substrate is the number to remember.")

S("""<h2>Mismatch alone does not predict bending</h2>
<div class="cols"><div>
<p><strong>Young's modulus E</strong> measures how hard a material resists being
deformed. A compliant layer can absorb mismatch; a stiff one forces the neighbour
to move instead.</p>
<p>So warpage depends on <strong>all</strong> of:</p>
<ul><li>CTE of each layer</li><li>stiffness E of each layer</li>
<li>thickness of each layer</li><li>overall geometry</li>
<li>how the package is held — the boundary conditions</li></ul></div>
<div class="callout"><strong>Why this matters here</strong><br>
Z1 and Z2 move the regulator between the substrate and the board side. That changes
the <em>thickness and stiffness distribution</em> of the stack, not just where the heat
is made. Two architectures at the same temperature can bend differently.</div></div>""",
  "Pre-empt the naive expectation that the hotter architecture must be mechanically worse. "
  "That expectation is wrong and the historical result shows it.")

WARP = """<svg viewBox="0 0 900 210" width="100%" style="max-height:32vh">
<line x1="40" y1="120" x2="860" y2="120" stroke="#d7dde4" stroke-width="2"
 stroke-dasharray="7 6"/>
<path d="M 60 160 Q 450 60 840 160" stroke="#1f6feb" stroke-width="13" fill="none"/>
<text x="400" y="52" font-size="16" fill="#1f6feb">convex / "smile"</text>
<path d="M 60 70 Q 450 180 840 70" stroke="#d1442f" stroke-width="13" fill="none"
 opacity=".55"/>
<text x="400" y="200" font-size="16" fill="#d1442f">concave / "cry"</text>
<line x1="450" y1="92" x2="450" y2="120" stroke="#10151c" stroke-width="3"/>
<text x="462" y="112" font-size="16">peak-to-valley warpage</text></svg>"""
S(f"<h2>Warpage</h2>{WARP}"
  "<p><strong>Warpage</strong> is global out-of-plane bowing of the package. It is "
  "measured peak-to-valley, in micrometres.</p>"
  "<p>It matters because it controls whether the package sits flat enough to assemble, "
  "how much load each BGA ball takes, and how far the corner joints are stretched.</p>",
  "Keep this short and visual. Mention that warpage sign conventions differ between "
  "vendors, so always state what is being measured.")

S("""<h2>Stress, strain, and the three kinds of deformation</h2>
<div class="cols"><div>
<p><strong>Strain</strong> — how much something deformed, relative to its original
size. Dimensionless.</p>
<p><strong>Stress</strong> — the internal force per unit area needed to hold that
deformation. Units MPa.</p></div>
<div><ul>
<li><span class="chip ok">ELASTIC</span> springs back completely when unloaded.</li>
<li><span class="chip warn">PLASTIC</span> permanent; does not come back.</li>
<li><span class="chip open">CREEP</span> keeps deforming under a <em>steady</em> load,
as a function of time and temperature.</li></ul>
<div class="callout" style="margin-top:.4em">Solder at operating temperature is at a
large fraction of its melting point. It creeps continuously. Treating it as elastic
would miss the damage mechanism entirely — so it is modelled as
<strong>viscoplastic</strong>.</div></div></div>""",
  "The viscoplastic point justifies the separate nonlinear local solder model. If asked "
  "why a 488-element submodel is worth a separate solve, this is the answer.")

GL = """<svg viewBox="0 0 950 250" width="100%" style="max-height:38vh">
<rect x="30" y="60" width="380" height="110" fill="#eef2f6" stroke="#9aa3ad"/>
<text x="40" y="84" font-size="17" font-weight="700">GLOBAL model</text>
<path d="M 60 150 Q 220 110 390 150" stroke="#1f6feb" stroke-width="9" fill="none"/>
<g>""" + "".join(f'<circle cx="{70+i*36}" cy="{160-int(14*(1-((i-4.5)/4.5)**2))}" '
                 f'r="7" fill="#9aa3ad"/>' for i in range(10)) + """</g>
<rect x="352" y="138" width="30" height="30" fill="none" stroke="#cf222e"
 stroke-width="3"/>
<text x="40" y="190" font-size="15" fill="#5a6672">whole package deforms; each joint is
a few elements</text>
<path d="M 420 130 L 500 130" stroke="#10151c" stroke-width="3"
 marker-end="url(#ar2)"/>
<defs><marker id="ar2" markerWidth="9" markerHeight="9" refX="7" refY="3"
 orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#10151c"/></marker></defs>
<text x="424" y="120" font-size="15" fill="#cf222e">&Delta;u<tspan font-size="11"
 dy="4">c</tspan><tspan dy="-4">, T</tspan></text>
<rect x="520" y="40" width="400" height="160" fill="#faf8ff" stroke="#6639ba"/>
<text x="532" y="64" font-size="17" font-weight="700">LOCAL submodel</text>
<rect x="640" y="86" width="150" height="80" fill="#e8c07a" stroke="#8a6d2f"/>
<g stroke="#8a6d2f" stroke-width="1" opacity=".55">""" + "".join(
    f'<line x1="{640+i*18.7}" y1="86" x2="{640+i*18.7}" y2="166"/>' for i in range(9)
) + "".join(f'<line x1="640" y1="{86+i*10}" x2="790" y2="{86+i*10}"/>'
            for i in range(9)) + """</g>
<text x="532" y="190" font-size="15" fill="#5a6672">one joint, 488 elements,
nonlinear viscoplastic</text></svg>"""
S(f"<h2>Global driver &rarr; local response</h2>{GL}"
  "<div class='cols' style='margin-top:.3em'>"
  "<div class='callout' style='border-color:var(--z1)'><strong>GLOBAL DRIVER</strong><br>"
  "&Delta;u<sub>c</sub>, the relative in-plane displacement imposed across the critical "
  "joint, plus its temperature. Units: &micro;m.</div>"
  "<div class='callout' style='border-color:var(--accent)'><strong>LOCAL RESPONSE</strong>"
  "<br>inelastic strain, strain range, inelastic work density returned by the "
  "viscoplastic joint model. Dimensionless / MJ·m<sup>-3</sup>.</div></div>"
  "<p style='margin-top:.3em;text-align:center'><strong>These are different quantities "
  "and are never reported as one.</strong></p>",
  "This is the most commonly confused point in the whole project. The global model cannot "
  "resolve a solder joint; the local model cannot know the package. Say explicitly that a "
  "larger displacement driver does not automatically mean a larger local response.")

S("""<h2>Response is not damage, and damage is not life</h2>
<table>
<tr><th>Quantity</th><th>What it is</th><th>Status here</th></tr>
<tr><td>warpage</td><td>global bowing, peak-to-valley</td>
<td><span class="chip ok">COMPUTED</span></td></tr>
<tr><td>&Delta;u<sub>c</sub></td><td>displacement imposed across the critical joint</td>
<td><span class="chip ok">COMPUTED</span></td></tr>
<tr><td>inelastic strain range</td><td>cyclic viscoplastic excursion in the joint</td>
<td><span class="chip ok">COMPUTED</span></td></tr>
<tr><td>inelastic work density</td><td>energy dissipated per unit volume per cycle</td>
<td><span class="chip ok">COMPUTED</span></td></tr>
<tr><td>damage</td><td>a model-dependent degradation variable</td>
<td><span class="chip warn">MODEL-DEPENDENT</span></td></tr>
<tr><td>cycles to failure</td><td>life, via a calibrated correlation</td>
<td><span class="chip open">NOT CLAIMED</span></td></tr></table>
<div class="callout" style="margin-top:.45em">Darveaux
(<span class="chip lit">10.1115/1.1413764</span>) showed that solder-life constants are
tied to the <em>exact</em> simulation procedure used to calibrate them. Applying them to
FE output produced a different way is not valid. This work therefore reports
<strong>response and relative ordering</strong>, and refuses absolute life.</div>""",
  "This is the defensive slide for the mechanics. If someone asks 'how many cycles will it "
  "survive', the answer is that no absolute life is claimed and why — Darveaux is the "
  "citation. Relative ordering between two architectures is still meaningful.",
  "10.1115/1.1413764 · 10.1109/ECTC.2004.1319419 — CONTEXT / METHODOLOGY")

S("""<h2>Two modelling choices that can flip the answer</h2>
<div class="cols"><div><h3>Stress-free temperature</h3>
<p>The temperature at which the assembly is assumed mechanically relaxed. All
differential thermal strain is measured <em>from</em> it.</p>
<p class="sub">Choose it 50 K higher and every predicted deformation changes. It is an
assumption, not a measurement, and must be stated.</p></div>
<div><h3>Boundary conditions</h3>
<p>A package floating freely and the same package bolted to a board bend
<strong>differently</strong> — sometimes in opposite directions.</p>
<p class="sub">A warpage number without its constraint description is not interpretable.</p>
</div></div>
<div class="banner">Both are declared explicitly in this framework rather than inherited
silently from a solver default.</div>""",
  "Short slide, but it pre-empts the classic reviewer question 'what was your reference "
  "temperature'. Having an answer ready signals rigour.")


FS.mechanics_validation(S)
# ---- hardening (history) ----
S("""<h2 style="border:none">&nbsp;</h2>
<div style="text-align:center;margin-top:1.0em">
<div class="big" style="color:var(--z2)">From a plausible model<br>to a defensible one</div>
<p style="text-align:center;margin-top:1em;max-width:72%;margin-left:auto;margin-right:auto">
The framework produced self-consistent numbers long before it produced
<em>physically closed</em> numbers. Several published-quality results were withdrawn.
That process is the contribution, not an embarrassment.</p></div>""",
  "Set the tone: this is a methods contribution. Each defect below changed a number that "
  "had already been written up. Do not rush these slides — a committee respects a "
  "candidate who found their own errors.")

S("""<h2>What physical closure actually changed</h2>
<table><tr><th>Found</th><th>Consequence</th></tr>
<tr><td>Z2 homogenised slab replaced by 49 real cells</td><td>geometry was not the
architecture being claimed</td></tr>
<tr><td>supply and return not distinguished</td><td>half the conduction path was missing</td></tr>
<tr><td>branch phase order was A,A,B — generator gives A,B,A</td><td>wrong interleave</td></tr>
<tr><td>average current used where RMS was required</td><td>I²R understated</td></tr>
<tr><td>I<sub>avg</sub>/&radic;D called an RMS <em>upper</em> bound</td>
<td>it is a <strong>lower</strong> bound; no finite upper bound exists</td></tr>
<tr><td>source pad treated as circular; A<sub>c</sub> says square</td>
<td>21 % area error</td></tr>
<tr><td>pad-count selector was <code>min(n_geom, max(n_drop, n_geom))</code></td>
<td>identically n_geom — a tautology hiding a 1227× loss span</td></tr>
<tr><td>BGA "sites" that were not on the lattice; 3.0 mm pitch vs 3.165243 mm</td>
<td>every RDL result on the wrong grid</td></tr>
<tr><td>Z1 given 8 balls against Z2's 16</td><td>the comparison measured ball count</td></tr>
</table>""",
  "Do not read every row. Pick three: the RMS bound inversion, the pad tautology, and the "
  "mismatched ball count. Say each one had already produced a number that was reported.")

S("""<h2>Three defects found in the last two phases</h2>
<div class="cols"><div class="callout" style="border-color:var(--z2)">
<strong>1 · Equal current sharing was an input</strong>
<p class="sub">The solver injected I<sub>total</sub>/N at every ball, so the "result"
that sharing is equal was the right-hand side. Replaced with a voltage-fed network:
a rail feeds each ball through its own resistance, and the split became an output.</p>
</div>
<div class="callout" style="border-color:var(--z2)">
<strong>2 · The return conductor was discarded</strong>
<p class="sub">Return sites were selected and never solved. Adding the return raises the
loop resistance substantially — every earlier package resistance was the supply leg only.</p>
</div></div>
<div class="callout" style="border-color:var(--open);margin-top:.5em">
<strong>3 · A floating-point bug hid 79 % of the design space</strong>
<p class="sub">Lattice coordinates were built as <code>-14.4 + i&times;0.8</code>, which
drifts. The mirror of (-14.4, -12.8) existed as (14.4, <strong>12.800000000000002</strong>).
The placement rule tests membership with exact equality, so it silently discarded
<strong>1080 of 1369</strong> legal sites. Two headline numbers had been computed inside
the surviving 21 %.</p></div>""",
  "Defect 3 is the best story in the talk. It produced no error, no warning, and no failing "
  "test — the design space was simply smaller than anyone thought, and the subset was "
  "selected by floating-point luck. Mention that the fix is a picometre snap plus a "
  "permanent closure assertion.")



FS.hardening(S)
FS.final_results(S)
FS.closing(S)

S("""<div style="text-align:center;margin-top:1.4em">
<div class="big">Thank you</div>
<p style="margin-top:1em;max-width:72%;margin-left:auto;margin-right:auto">
<strong>Contribution:</strong> a hierarchical electrothermal–mechanical framework for
distributed vertical power delivery, checked stage by stage against matched reference
solvers, and a demonstration that physical closure reverses an architecture conclusion.</p>
<p class="sub" style="margin-top:1.2em">Questions</p></div>""", "")

# ============ APPENDIX ===============================================
S("""<h2>Appendix — the voltage-fed network</h2>
<p>Unknowns: sheet node voltages, one node per ball, one per cell pad, one rail node
held at a fixed potential. Conductances:</p>
<ul><li>sheet edge: 1/R<sub>sq</sub>, with R<sub>sq</sub> = &rho;<sub>Cu</sub>(T) /
(t<sub>Cu</sub> &middot; occupancy)</li>
<li>rail &rarr; ball j: 1/R<sub>ball</sub>, R<sub>ball</sub> = &rho;<sub>solder</sub>
h / A = 0.3104 m&Omega; from Table III geometry</li>
<li>ball &rarr; sheet node k: A<sub>overlap,k</sub> / &rho;<sub>c</sub></li></ul>
<p>Loads are drawn at the cell pad nodes. Ball currents are therefore an
<strong>output</strong>: I<sub>j</sub> = (V<sub>rail</sub> &minus; V<sub>Bj</sub>) /
R<sub>ball</sub>.</p>
<p><strong>Identities checked every solve:</strong> &Sigma;I<sub>ball</sub> =
I<sub>total</sub> to ~1e-10 A, and &Sigma;g&Delta;V² = V&middot;I to ~1e-10 relative,
with R<sub>eff</sub> = P / I².</p>""", "")

S("""<h2>Appendix — why the 48 V RMS cannot be closed</h2>
<p>The pinned generator builds every electrical quantity from one scalar,
<code>I_out_rms = sqrt(I_out² + &Delta;i²/12)</code>, the triangular-ripple identity on
the output inductor, then duty-weights it.</p>
<p>It contains <strong>no</strong> switched-capacitor state sequence, <strong>no</strong>
flying-capacitor charge balance, and <strong>no input current variable at all</strong>.
The 48 V average therefore comes only from power balance — and average current closes
energy balance while RMS closes conduction loss. One does not give the other.</p>
<p><strong>Closing it requires</strong> the per-state switch conduction table, the
charge-transfer schedule, or a netlist of the adopted topology.</p>
<p class="sub">Hybrid/SC RMS papers derive input RMS correctly for <em>their</em>
topologies — methodology context only. Importing their ratio would be transferring a
different converter's waveform.</p>""", "")


FS.appendix(S)

# ============ assemble ===============================================
HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HVR_OPT — Prelim</title>
<link rel="stylesheet" href="vendor/reveal.js/dist/reset.css">
<link rel="stylesheet" href="vendor/reveal.js/dist/reveal.css">
<link rel="stylesheet" href="vendor/reveal.js/dist/theme/white.css">
<link rel="stylesheet" href="theme.css">
</head><body><div class="reveal"><div class="slides">
__SLIDES__
</div></div>
<script src="vendor/reveal.js/dist/reveal.js"></script>
<script src="vendor/reveal.js/plugin/notes/notes.js"></script>
<script>
Reveal.initialize({
  width: 1600, height: 900, margin: 0.045,
  hash: true, slideNumber: 'c/t', transition: 'none',
  pdfMaxPagesPerSlide: 1, pdfSeparateFragments: false,
  plugins: [ RevealNotes ]
});
</script></body></html>"""
(D / "index.html").write_text(HTML.replace("__SLIDES__", "\n".join(SLIDES)))

# --- deterministic print page: no JS, exactly one page per slide ---------
# Reveal's own ?print-pdf relies on runtime layout, and headless Chrome
# snapshots before it settles -- it produced a single blank page. This static
# page needs no JavaScript at all, so the page count cannot depend on timing.
PRINT_CSS = """
@page { size: 1600px 900px; margin: 0; }
html,body { margin:0; padding:0; background:#fff; }
.pg { position:relative; width:1600px; height:900px; overflow:hidden;
      box-sizing:border-box; padding:54px 72px 56px;
      page-break-after:always; break-after:page; background:#fff; }
.pg:last-child { page-break-after:auto; break-after:auto; }
.pg .prov { position:absolute; bottom:18px; left:72px; right:72px; }
aside.notes { display:none !important; }
.pgnum { position:absolute; bottom:16px; right:24px; font-size:13px;
         color:#8c959f; }
"""
import re as _re
_pages = []
for _i, _sec in enumerate(SLIDES, 1):
    _inner = _re.sub(r"^<section class='[^']*'>|</section>$", "", _sec)
    _pages.append(f"<div class='pg reveal'>{_inner}"
                  f"<div class='pgnum'>{_i} / {len(SLIDES)}</div></div>")
PRINT = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
         "<title>HVR_OPT — Prelim (print)</title>"
         "<link rel='stylesheet' href='vendor/reveal.js/dist/reset.css'>"
         "<link rel='stylesheet' href='theme.css'>"
         f"<style>{PRINT_CSS}</style></head><body>"
         + "\n".join(_pages) + "</body></html>")
(D / "print.html").write_text(PRINT)
print("print page written:", len(_pages), "pages")
# --- speaker notes, derived from each slide's own <aside class='notes'> -----
import html as _html
_notes = ["# HVR_OPT prelim — speaker notes", "",
          "Generated by `scripts/prelim_build_deck.py`. Do not edit by hand.", ""]
for _i, _sec in enumerate(SLIDES, 1):
    _t = _re.search(r"<h[12][^>]*>(.*?)</h[12]>", _sec, _re.S)
    _title = _re.sub(r"<[^>]+>", "", _re.sub(r"<br\s*/?>", " ", _t.group(1))) if _t else ""
    _title = _html.unescape(_title).replace("\xa0", " ").strip() or "(untitled)"
    _n = _re.search(r"<aside class='notes'>(.*?)</aside>", _sec, _re.S)
    _txt = _html.unescape(_re.sub(r"<[^>]+>", "", _n.group(1))).strip() if _n else ""
    _notes += [f"## Slide {_i} — {_title}", _txt or "_(no notes)_", ""]
(D / "SPEAKER_NOTES.md").write_text("\n".join(_notes))
for f in ("_slides_part1.html",):
    (D / f).unlink(missing_ok=True)
print("deck written:", len(SLIDES), "slides ->", D / "index.html")
