"""Fig. 5: rail assignment and where each integration gains or loses against Z1.

(a)   Current carried by each class of connection inside one regulator cell, coloured by
      rail (48 V red, 16 V neutral, 1 V violet).
(b,c) Package-internal loss of Z2 and of Z3 minus that of Z1 in the production state
      (implemented decoupling: two interleaved 6-phase clock groups and a ring of input
      capacitors), decomposed term by term (waterfall): the routing terms
      each integration removes or adds, and the electrothermal term -- the same converter
      dissipating more or less because it runs at a different temperature. The converter row
      is annotated with that temperature difference.
Cases: the case registry (scripts/tcpmt_cases.py), production state, cooling A; Z3 is the
coupled land-side case: its 1-V land-side and board-plane spreading rows
(P_sub_land_1V_spreading, P_PCB_plane_1V_spreading) are a separate row; the package input
capacitor ring's ESR row (P_Cin_ring_ESR) belongs to the 48-V package path.
Data: the converged case files' ledger_rows; segment currents from the routing model of the
design in force (routing.nets: the 48-V bus, the 16-V flying-capacitor loop and intermediate
rail, the switch node) and tcpmt_revision/input_decoupling.json (circuit.design) where
available. Rail colours only; no architecture colours in this figure (the two pairs fail
together under CVD).
"""
import matplotlib.pyplot as plt
import style as S

S.setup()
SCEN = S.TC.SCEN[S.PROD]
#: cooling A (the same top plate), production state, every integration from the registry
CJ = {}
for _a in ("Z1", "Z2", "Z3"):
    _p, _c = S.load_case(S.PROD, "A", _a)
    if _c is not None:
        CJ[_a] = _c
if "Z1" not in CJ:
    raise SystemExit(f"no Z1 case in the production state ({SCEN}, cooling A): "
                     f"{S.TC.expected_path(S.PROD, 'A', 'Z1')}")
L = [dict(r, arch=a, scenario=SCEN) for a, c in CJ.items() for r in c["ledger_rows"]]
FIN = {(a, SCEN): {"I_48_avg_a": c["i_hv_avg_a"]} for a, c in CJ.items()}


def tot(a, pred, s=SCEN):
    return sum(r["P_w"] or 0.0 for r in L if r["arch"] == a and r["scenario"] == s
               and pred(r["term"]))


def pre(*p):
    return lambda t: any(t.startswith(x) for x in p)


LAND = pre("P_sub_land", "P_PCB_plane")          # coupled 1-V spreading (Z3)
GROUPS = [
    ("48-V package path", pre("P_pkg_RDL_HV", "P_BGA_supply", "P_BGA_return", "P_Cin"), S.V48),
    ("TSV field", pre("P_TSV"), S.V1),
    ("Regulator attach", pre("P_VR_attach", "P_VR_PCB_attach", "P_board_attach"), S.V1),
    ("Board vias, 1-V BGA", lambda t: pre("P_board", "P_PCB", "P_pcb", "P_BGA_LV", "P_BGA_1V",
                                          "P_BGA_VDD", "P_BGA_GND")(t) and not LAND(t), S.V1),
    ("Land side + board plane", lambda t: LAND(t), S.V1),
    ("Intra-cell routing", pre("P_intraVR"), S.NEUTRAL),
    ("Converter", pre("P_conv_"), S.NEUTRAL),
]
archs = [a for a in ("Z2", "Z3") if any(r["arch"] == a and r["scenario"] == SCEN for r in L)]

fig = plt.figure(figsize=(S.COL_W, 3.45))
axA = fig.add_axes([0.40, 0.765, 0.56, 0.19])
wpan = 0.56 / len(archs) - (0.05 if len(archs) > 1 else 0)
axes = [fig.add_axes([0.40 + k * (wpan + 0.05), 0.10, wpan, 0.47]) for k in range(len(archs))]

# ---------------------------------------------------------------- (a) segment currents
N_VR = S.DR.n_vr()
_des = ((S.JP(S.TR / "input_decoupling.json") or {}).get("circuit") or {}).get("design") or {}


def _routing_currents():
    """per-cell currents the ledger's intra-VR model charges (routing.nets of the design in
    force): 48-V bus (sum over the N high-side feeds), flying-capacitor loop (RMS of one
    HS -> C_f link, AC only), 16-V intermediate rail (sum over the N HS -> LS links), switch
    node (sum over the K phases)"""
    import sys
    p = str(S.REPO / "scripts" / "phase0m")
    if p not in sys.path:
        sys.path.append(p)
    import routing as RT
    nets = RT.nets(RT.design_in_force())
    tot = (lambda f: sum(n.i_dc_a for n in nets if f(n.name)))
    return {"in": tot(lambda s: s.startswith("vin_to_hs")),
            "cf": max(n.i_rms_a for n in nets if "_to_cf" in n.name),
            "mid": tot(lambda s: s.startswith("hs") and "_to_ls" in s),
            "sw": tot(lambda s: s.startswith("ls") and "_to_L" in s)}


try:
    _rc = _routing_currents()
except Exception as e:                                          # noqa: BLE001
    print(f"NOTE: routing model unavailable ({e}); 16-V currents pending")
    _rc = {}
#: the 48-V bus at the production Z1 case's input current (the number the annotation gives)
I_IN_CELL = (FIN[("Z1", SCEN)]["I_48_avg_a"] / N_VR if FIN.get(("Z1", SCEN), {}).get("I_48_avg_a")
             else _des.get("I_in_avg_a") or _rc.get("in"))
I_SW = _rc.get("sw") or (S.DR.topology()[1] * _des["I_L_a"] if _des.get("I_L_a") else None)
seg = [("48-V input bus", I_IN_CELL, S.V48),
       ("16-V high side to $C_\\mathrm{f}$", _rc.get("cf"), S.NEUTRAL),
       ("16-V intermediate rail", _rc.get("mid"), S.NEUTRAL),
       ("1-V switch node to $L$", I_SW, S.V1)]
axA.set_xscale("log")
axA.set_xlim(0.2, 60)
axA.set_ylim(len(seg) - 0.45, -0.55)
axA.grid(axis="x", which="major", color=S.GRID, lw=0.5)
axA.grid(axis="y", visible=False)
for i, (lab, v, col) in enumerate(seg):
    if v is None:
        S.pending(axA, 0.25, i, lab, "routing model / input_decoupling.json",
                  transform=axA.transData)
        continue
    axA.barh(i, v - 0.2, left=0.2, height=0.62, color=col, lw=0, zorder=2)
    axA.text(v * 1.28, i, f"{v:.2f} A" if v < 10 else f"{v:.1f} A", va="center", ha="left",
             fontsize=6.6, color=S.INK)
axA.set_yticks(range(len(seg)), [s[0] for s in seg])
axA.tick_params(axis="y", length=0, labelsize=6.8)
axA.set_xlabel("DC-average current per regulator cell (A)", labelpad=1.5)
axA.spines["left"].set_visible(False)
S.panel(axA, "a", "Rail currents in one cell", x=-0.70, y=1.06)
i48 = FIN[("Z1", SCEN)]["I_48_avg_a"]
i1 = S.DR.P_LOAD_W / S.DR.V_OUT
axA.text(60, -0.5, f"DC averages (ledger: RMS)\n×{N_VR} cells: {i48:.1f} A at 48 V,\n"
         + (f"{i1 / 1e3:.1f} kA" if i1 >= 1e3 else f"{i1:.0f} A") + " at 1 V",
         transform=axA.transData, ha="right", va="top", fontsize=6.5, color=S.INK2,
         linespacing=1.0)


def T_ls(a):
    return CJ[a]["et_history"][-1]["T_ls_C"]


def fmt(d):
    return (f"{d:+.2f}" if abs(d) < 10 else f"{d:+.1f}").replace("-", "−")


# ---------------------------------------------------------------- (b,c) waterfalls
def present(a, p):
    return any(r["arch"] == a and r["scenario"] == SCEN and p(r["term"]) for r in L)


rows_all = {}
for a in archs:
    ds = [(n, (tot(a, p) - tot("Z1", p)) if (present(a, p) or present("Z1", p)) else None, c)
          for n, p, c in GROUPS]
    net = tot(a, lambda t: True) - tot("Z1", lambda t: True)
    rows_all[a] = ds + [("Net vs. Z1", net, S.INK)]
def window(rows):
    """Each panel on its own scale: the cumulative waterfall path and the net must fit."""
    cum, pts = 0.0, [0.0]
    for _, d, _ in rows[:-1]:
        if d is not None:
            cum += d
            pts.append(cum)
    pts.append(rows[-1][1] or 0.0)
    lo, hi = min(pts), max(pts)
    w = hi - lo
    return (lo - 0.12 * w, hi + 0.55 * w)


for k, (ax, a) in enumerate(zip(axes, archs)):
    rows = rows_all[a]
    xl = window(rows)
    ax.set_xlim(*xl)
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.axvline(0, color=S.AXIS, lw=0.6, zorder=1)
    ax.grid(axis="x", color=S.GRID, lw=0.5)
    ax.grid(axis="y", visible=False)
    cum = 0.0
    for i, (lab, d, col) in enumerate(rows):
        last = i == len(rows) - 1
        if d is None:                       # structurally absent in both integrations
            ax.text(xl[1], i, "\u2013", va="center", ha="right", fontsize=6.5, color=S.INK2)
            continue
        if not last:
            left = cum if d >= 0 else cum + d
            ax.barh(i, abs(d), left=left, height=0.6, color=col, lw=0, zorder=2)
            if i < len(rows) - 2:
                ax.plot([cum + d] * 2, [i + 0.3, i + 0.7], color=S.MUTED, lw=0.5, zorder=1)
            cum += d
        else:
            ax.barh(i, d, left=0, height=0.6, color=col, lw=0, zorder=2)
        ax.text(xl[1], i, fmt(d), va="center", ha="right", fontsize=6.5, color=S.INK,
                fontweight="bold" if last else "normal")
    # the low-side device tier carries most of the conversion loss: its temperature
    # difference is the electrothermal mechanism behind the converter row
    dT = T_ls(a) - T_ls("Z1")
    ic = [r[0] for r in rows].index("Converter")
    ax.text(xl[1], ic + 0.52, f"({dT:+.1f} K)".replace("-", "−"), va="center", ha="right",
            fontsize=6.5, color=S.INK2)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows] if k == 0 else [])
    ax.tick_params(axis="y", length=0, labelsize=6.6)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("$\\Delta P$ (W)", labelpad=1.5)
    S.panel(ax, "bcd"[k], f"{a} $-$ Z1", y=1.02)
fig.text(0.40, 0.615, "Loss difference, cooling A (implemented decoupling)", ha="left",
         va="bottom",
         fontsize=7, color=S.INK)
S.save(fig, "fig5_loss_swap")
