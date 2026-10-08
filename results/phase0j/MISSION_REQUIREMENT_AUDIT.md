# Phase 0J Sec. 13/14 — Required-life audit

Searched **separately** from the life-law literature, as Sec. 13 requires, because the two
halves of `N_f(x) >= N_required` come from different kinds of document and must not be
conflated.

## What was searched

| source | result |
|---|---|
| **June-2026 DVPD reference paper** (arXiv:2606.28837) | Read in full for reliability content. It discusses reliability **qualitatively only** — "strong electrical coupling … from a reliability standpoint", "fault containment a primary reliability concern", "efficiency and device reliability". **No cycle count, no required life, no mission profile.** |
| **ECTC-2024 reference paper** | No lifetime requirement. |
| **jedec.org** (JESD22-A104, JESD47) | **HTTP 403**, unchanged from Phase 0H. Standards not retrievable directly. |
| **ANSI webstore** | HTTP 403. |
| **opencompute.org** (OCP datacenter specifications) | HTTP 403. |
| **ipc.org** | HTTP 200, but no operating-life cycle requirement located. |
| OpenAlex, six targeted mission-profile queries (datacenter / server / HPC / power-cycling mission profiles, "thermal cycles per year", use-condition requirements) | No source-backed field mission requirement for a datacenter power-delivery package. |

## What WAS found, correctly categorised

Sec. 13 requires the four categories to be kept apart. Everything retrievable falls in
categories A and C — **none in category B**.

| # | category | what was found | source | may it be `N_required`? |
|---|---|---|---|---|
| **A** | **Qualification test requirement** | board-level temperature cycling **−40 to +125 °C, 1000 cycles**; package-level **−55 to +125 °C, 1000 cycles**; HTSL 150 °C / 500 h; THB 85 °C/85 % RH / 1000 h — the qual set an FCBGA product was reported to pass | IMAPS 2023, *Development of high performance FCBGA packages*, retrieved in full | **No.** An acceptance protocol, not a field allowable. Phase 0H category 2. |
| **C** | **Accelerated test condition** | JESD22-A104-B profile as applied in practice: **−40 to +125 °C, 45-min ramp, 15-min dwell, 3.6 °C/min** | Springer 2025 (*Interpretable data-driven framework…*), secondary description, retrieved in full | **No.** A stress condition, not a life requirement. |
| **C** | **Accelerated test condition** | JESD22-A104-B **ramp-rate guidance: ≤ 15 °C/min, preferred 10–14 °C/min** | George 2010 (UMD MS thesis), secondary description, retrieved in full | **No.** |
| **A** | **Experimental characteristic life** | SAC305 256 I/O BGA, ENIG finish, −40 to +185 °C: **η = 1390 cycles, β = 5.4**, N50 = 1300 (16/16 failures) | George 2010, **primary experimental data**, retrieved in full | **No.** This is a measured life under one accelerated condition, not a requirement. |
| **B** | **FIELD MISSION REQUIREMENT** | **NONE FOUND** | — | — |
| **D** | **User-declared design target** | **NONE DECLARED** — the brief forbids inventing one | — | — |

## Verdict

```
N_required = OPEN
```

**No source-backed field mission requirement exists for this system.** Sec. 14 forbids
promoting a qualification count or an accelerated-test condition into one, so the 1000-cycle
qualification figure is recorded above and **is not used as `N_required` anywhere in this
phase**.

A **PARAMETRIC MISSION SENSITIVITY** sweep is run instead over
10², 3×10², 10³, 3×10³, 10⁴, 3×10⁴, 10⁵ cycles (`mission_life_sensitivity.csv`). It is labelled
parametric sensitivity, **never qualification**, and it is a sweep of an unknown, not a
prediction.

## Why this is a structural result, not a search failure

Phase 0H already established the reason, and Phase 0J confirms it with network access that
Phase 0H lacked: **operating-life limits are set by product qualification programmes, which are
customer- and programme-specific and are not published**, while the public standards family
specifies *how to test*, not *how long a part must last in the field*. A required life for this
system would have to be **declared by its owner**, not discovered in the literature.

That is a statement about where the information lives, not about how hard the search was.
