# PHASE 0M PARTS 23-26 --- COOLING-BOUNDARY AUDIT

## What is in the model now

| use | value | where | status |
|---|---|---|---|
| `h_top` | **166 000 W/m2K** | `results/phase0f/cooling_1kw_calibration.json` | INVERSE-CALIBRATED so the 1-kW package reaches 84 C |
| `h_bottom` | 10 W/m2K | `configs/phase0b/package_stack.yaml` | ASSUMPTION, "natural convection under the package carrier" |
| `T_inf` (top and bottom) | 25 C, uniform | same | ASSUMPTION |
| cooled surface | the TIM top face | `etm/ccxio.py::top_film_faces` | choice, not derived |
| substrate-side variant | h_bottom = 398 672 W/m2K | Phase 0F Sec. 4 | DID NOT CONVERGE; residual +6.96 K |

A calibrated film coefficient is not a cooling technology. It cannot be transferred to
another architecture, it carries no pumping cost, and it cannot produce a streamwise
temperature gradient because its sink temperature is a single number.

## What physical cooler does 166 000 W/m2K represent?

Derived from geometry and flow with `Nu = Nu(alpha)` from Shah and London for laminar
rectangular ducts, straight-fin efficiency, the caloric resistance `1/(2 m_dot c_p)`, and the
laminar friction factor `f Re = C(alpha)`:

| architecture | flow | Re | regime | h_channel | area amp. | **h_effective** | vs 166k | dT_coolant | T_j | dp | pump |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TOP_MICROCHANNEL_SI | 1.6 g/s | 75 | laminar | 34581 | 5.10 | **22827** | 0.14x | 168.2 K | 123.6 C | 32 kPa | 0.05 W |
| TOP_MICROCHANNEL_SI | 27.0 g/s | 1265 | laminar | 34581 | 5.10 | **115553** | 0.70x | 10.0 K | 44.5 C | 538 kPa | 14.70 W |
| TOP_MICROCHANNEL_SI | 50.0 g/s | 2342 | transitional | 95415 | 3.91 | **215115** | 1.30x | 5.4 K | 35.5 C | 1463 kPa | 74.06 W |
| TOP_MICROCHANNEL_CU | 1.6 g/s | 88 | laminar | 17036 | 5.12 | **20266** | 0.12x | 168.2 K | 136.0 C | 5 kPa | 0.01 W |
| TOP_MICROCHANNEL_CU | 27.0 g/s | 1482 | laminar | 17036 | 5.12 | **70478** | 0.42x | 10.0 K | 56.9 C | 83 kPa | 2.26 W |
| TOP_MICROCHANNEL_CU | 50.0 g/s | 2745 | transitional | 61324 | 4.46 | **186175** | 1.12x | 5.4 K | 37.1 C | 259 kPa | 13.09 W |
| SUBSTRATE_EMBEDDED | 1.6 g/s | 176 | laminar | 15838 | 2.42 | **15663** | 0.09x | 168.2 K | 168.7 C | 16 kPa | 0.03 W |
| SUBSTRATE_EMBEDDED | 27.0 g/s | 2965 | transitional | 84692 | 2.20 | **125399** | 0.76x | 10.0 K | 42.9 C | 574 kPa | 15.69 W |
| SUBSTRATE_EMBEDDED | 50.0 g/s | 5490 | turbulent | 167638 | 2.00 | **219014** | 1.32x | 5.4 K | 35.3 C | 1615 kPa | 81.75 W |
| TWO_SIDED | 1.6 g/s | 75 | laminar | 34581 | 5.10 | **22827** | 0.14x | 84.1 K | 74.3 C | 32 kPa | 0.05 W |
| TWO_SIDED | 27.0 g/s | 1265 | laminar | 34581 | 5.10 | **115553** | 0.70x | 5.0 K | 34.7 C | 538 kPa | 14.70 W |
| TWO_SIDED | 50.0 g/s | 2342 | transitional | 95415 | 3.91 | **215115** | 1.30x | 2.7 K | 30.2 C | 1463 kPa | 74.06 W |
| AGGRESSIVE_TUCKERMAN | 1.6 g/s | 75 | laminar | 34597 | 5.12 | **22838** | 0.14x | 168.2 K | 123.5 C | 32 kPa | 0.05 W |
| AGGRESSIVE_TUCKERMAN | 27.0 g/s | 1258 | laminar | 34597 | 5.12 | **115836** | 0.70x | 10.0 K | 44.4 C | 534 kPa | 14.59 W |
| AGGRESSIVE_TUCKERMAN | 50.0 g/s | 2329 | transitional | 94515 | 3.92 | **214504** | 1.29x | 5.4 K | 35.5 C | 1446 kPa | 73.16 W |

Three results, all of which the Robin boundary hides:

1. **At the source's stated 1.6 g/s the coolant temperature rise is 168 K.** Water cannot
   carry 1125 W at that flow. The flow needed for a 10 K rise is **26.9 g/s, 16.8x** the
   stated value. Whatever 1.6 g/s refers to in the source, it is not the total flow that
   removes the whole package loss with a single-phase coolant.
2. **No laminar architecture reaches h = 166 000 W/m2K.** The best laminar case gets 0.70x.
   Reaching the calibrated value needs the transitional/turbulent regime at 50 g/s, which
   costs **74 W of pumping --- 7.4 % of the load --- and 1.46 MPa of pressure drop.** The
   framework charges neither anywhere.
3. **Two-sided cooling is the largest single lever.** At the same 1.6 g/s per side it reaches
   T_j = 74.3 C where one-sided reaches 123.6 C, because each side carries half the heat and
   the caloric term halves.

The caloric resistance `1/(2 m_dot c_p)` DOMINATES the thermal path at low flow: at 1.6 g/s
it is 0.0747 K/W against 0.013 K/W for convection and conduction combined. A single Robin
coefficient absorbs it into `h` and makes it look like a surface property.

## Part 25 --- can one uniform Robin coefficient represent embedded microchannels?

**No.** Three reasons, in order of size:

* the fluid warms along the channel, and a single sink temperature cannot represent that;
* entrance effects raise the local Nusselt number near the inlet, which a constant `h` cannot;
* the heat generation is spatially non-uniform (a 1 kW die plus 49 converter tiles), so the
  local `h (T_wall - T_f)` balance varies along the flow even at constant `h`.

## Part 26 --- does the cooling ARCHITECTURE change the mechanics?

The same global thermal/mechanical model was run four times, changing ONLY the sink-temperature
field: uniform, then a linear streamwise gradient equal to the coolant rise each mass flow
produces at 1125 W. Total heat removed is unchanged; the MEAN sink temperature is held, so
this isolates the gradient from the level.

| case | sink gradient | T_max | die warpage | vs uniform |
|---|---|---|---|---|
| uniform | 0.00 K | 50.822 C | 4.1986 um | 0.00 % |
| mdot27 | 9.97 K | 52.844 C | 4.2623 um | 1.52 % |
| mdot10 | 26.91 K | 56.282 C | 4.3705 um | 4.10 % |
| mdot5 | 53.81 K | 62.166 C | 4.5426 um | 8.19 % |

**A physically real coolant temperature rise moves the die warpage by 1.5 to 8.2 % and the
peak temperature by 2 to 11 K, and the uniform Robin boundary sets both to zero.** The
sensitivity is to a physical cooling variable --- mass flow --- not to `h`.

(The vehicle is the Phase-0B controlled case at its own load, so the absolute temperatures
are not the 1-kW operating point; the imposed sink gradients are the ones 1125 W produces at
each flow, and the warpage response to an imposed boundary gradient is what is being measured.)

## Part 24 --- the cooling design variables that should exist

`coolant inlet temperature`, `mass flow`, `channel width`, `channel height`, `channel pitch`,
`channel location (top / substrate / both)`, `cold-plate or lid thickness`, `TIM thickness`,
`TIM conductivity`. `h` is DERIVED from these, never chosen. `pressure drop` and `pumping
power` are charged, because at the calibrated operating point they are 7.4 % of the load.

## Icepak

Not revisited. The Phase-0E attempt converged but returned exactly 5000 K on every object ---
a solver clamp, meaning the external cooling boundary never took effect. **No Icepak
validation is claimed and none may be claimed until that setup is understood and repaired.**
