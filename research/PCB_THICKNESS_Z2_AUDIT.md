# PCB thickness audit for the Z2 land-side cutout

Phase 0N-S Tasks 1, 2, 10, 20. The 1.6 mm board was always a framework **ASSUMPTION**
(`board.py` FR-4 envelope), never a requirement. This audit treats board thickness as a
design variable and tests closure on the **full interface stack**, not on nominal
thickness.

## 1. Fabrication evidence

| source | type | what it gives |
|---|---|---|
| IPC-2221A (generic standard for printed board design) | **standard** | board thickness is a design parameter; ≈0.8–2.4 mm is typical, no universal 1.6 mm |
| UGPCB 18-layer server PCB product page | **vendor product** | an 18-layer server/HPC board offered at **2.4 mm ±10 %** — the closest match to our application |
| Schweizer Electronic, standard multilayer | **vendor capability** | standard **0.6–3.2 mm**; higher-standard **0.2–4.2 mm** |
| PCBWay capabilities | **vendor capability** | rigid thicknesses incl. 2.0, 2.4, 2.6, 2.8, 3.0, **3.2 mm** |
| JLCPCB PCB design resources | **vendor capability** | rigid capability through **3.2 mm** |
| Isola 370HR / IS410 | **laminate vendor** | laminate available through **3.2 mm** |
| Würth Elektronik DEVICE.embedding design guide | **vendor process guide** | max final PCB thickness **3.2 mm**; max embedded component height **2663 µm** |

**None of these is peer-reviewed.** They are fabrication and vendor evidence, and they
establish availability, not suitability for this package.

## 2. What must clear, and what is allowed for

Land-side HVR four-tier stack: **1953 µm** nominal,
**2083 µm** at the EPC2014C maximum (815 µm).

| allowance | µm | class | basis |
|---|---:|---|---|
| land-side attach RDL | 10 | **SOURCE_BACKED** | ECTC-2024 10 um interlayer RDL |
| cell-to-substrate attach solder + underfill | 30 | **BOUNDED** | same order as the 10 um microbump + underfill the package already uses; no source |
| bottom keep-out below the deepest device | 50 | **BOUNDED** | anchored on H_TSV_MIN_UM = 50 um, the only keep-out length the framework names |
| assembly / placement tolerance | 50 | **BOUNDED** | engineering allowance; no source |
| **total** | **140** | | |

Backside TIM + spreader, if case-B cooling is used: **500 µm** further (BOUNDED).

Required depth: **2093 µm** nominal,
**2223 µm** at the device maximum.

## 3. Closure, evaluated at the **worst-case** board (−10 %)

Available depth = (board thickness × 0.9) + 300 µm BGA.

| board | −10 % (µm) | available (µm) | margin, nominal | margin, max device | margin, max + TIM | verdict |
|---|---:|---:|---:|---:|---:|---|
| **1.6 mm** | 1440 | 1740 | -353 | -483 | -983 | FAILS |
| **2.0 mm** | 1800 | 2100 | +7 | -123 | -623 | closes nominal only |
| **2.4 mm** | 2160 | 2460 | +367 | +237 | -263 | CLOSES at max device |
| **3.2 mm** | 2880 | 3180 | +1087 | +957 | +457 | CLOSES at max device; TIM fits inside |
| **4.2 mm** | 3780 | 4080 | +1987 | +1857 | +1357 | CLOSES at max device; TIM fits inside |

## 4. Selection

**Primary: 2.4 mm.** It closes at the device maximum with **+237 µm**, it is the thickness of an
actual 18-layer server board product, and it sits inside standard multilayer capability. A
backside TIM + spreader does **not** fit inside the board depth
(-263 µm), so with case-B cooling the spreader must protrude below the
board — which ARM's FIG. 3 contemplates, dissipating into ambient through the cutout.

**Robustness case: 3.2 mm.** +957 µm at the device maximum and the TIM fits inside
(+457 µm). It is **not** chosen as primary: extra thickness is not free, and a thicker
frame is a different mechanical restraint (§6).

**1.6 mm fails** by 483 µm at the device maximum — the historical board cannot host this
architecture. **2.0 mm is not viable**: +7 µm nominal collapses to -123 µm at the
device maximum, i.e. it depends on every device being at nominal height.

**4.2 mm is reported but not adopted** — Schweizer lists it as higher-standard capability,
not standard.

## 5. Electrical manufacturability (Task 10)

| item | 2.4 mm | 3.2 mm |
|---|---|---|
| fabrication source | UGPCB 18-layer server board at this exact thickness | Schweizer/PCBWay/JLCPCB standard; Isola laminate |
| PTH aspect ratio at 0.3 mm drill | 8:1 | **10.7:1** — at or beyond routine plating |
| PTH aspect ratio at 0.2 mm drill | 12:1 | **16:1** — specialist |
| backdrill | likely for high-speed nets | more stub, more likely |
| connector/press-fit | standard parts suit 2.4 mm | press-fit pin length must be re-specified |

**The package TSV process does not transfer to motherboard PTHs** and no package via rule
was applied here. The **cutout itself is routed/milled NPTH geometry**, not a plated hole,
so it carries no aspect-ratio constraint — but it does remove board area that routing and
stiffening must work around, which this audit does not model.

## 6. Mechanical consequence — explicitly NOT computed here

A thicker annular frame changes bending stiffness, package warpage, BGA displacement and
the critical joint. `D ∝ Et³` is **intuition only** and is not used as a result: the board
has a 23.36 mm central cutout and a discrete ball field, so plate scaling does not
apply. **Both 2.4 mm and 3.2 mm must be run in FEA before any mechanical statement is
made.** That run is not part of this commit (see §7).

## 7. Status

Geometric and fabrication closure for 2.4 mm is **established**. The ETM implementation —
annular PCB mesh, surviving ball field, discrete land-side cells, explicit supply/return
via fields, mesh convergence, critical-joint search and the local solder rerun — is **not
done**, and no new ETM numbers exist. The Task G/18 gate therefore remains closed.
