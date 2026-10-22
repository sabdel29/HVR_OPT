# Z2 BGA budget — power feasibility vs package-I/O feasibility

Phase 0N-S Task 7.

## 1. What was established, and what it does not prove

The 48 V input is **23.43 A** at system level and the 1 V output never touches the BGA — it
rises through the substrate TSVs. So:

| | balls |
|---|---:|
| 48 V supply at `J_design` = 1 × 10⁸ A/m² | 2 |
| 48 V supply at a conservative 1.5 A/ball | 16 |
| equal ground/return allocation | +16 |
| **total power + return, conservative** | **32** |
| sites remaining after a 23.36 mm cutout (1.0 mm clearance) | 528 |
| utilisation | **6.1 %** |

**This proves only that power-delivery BGA capacity is not limiting.**

## 2. What is NOT established

> **Power-delivery BGA capacity is established; complete package-I/O BGA capacity is
> outside the current model.**

The framework models a power-delivery network. It does **not** represent compute-die
signal I/O, clocks, control, memory or high-speed interfaces, and it has no pin budget for
them. The remaining 496 sites are therefore *unallocated*, not *free*: a real 1 kW
accelerator package spends most of its ball field on exactly the I/O this model omits.

Xu 2019 is directly relevant and is peer-reviewed: moving the VR to the package bottom
**changes the BGA pinout** and creates **area congestion on the package bottom**, to the
point that some decoupling capacitors had to be relocated to the package top. Our cutout
removes **841 of 1369** sites — 61 % of the ball field — and that is before any signal
allocation.

**Whether a 23.36 mm cutout is compatible with a real package's I/O budget is an open
question this work cannot answer.** It should not be presented as closed.

## 3. Mitigation already in the precedent

ARM US20260059645A1 contemplates feeding input power through **external high-current
connectors** rather than balls, explicitly "freeing substrate balls for output current",
and allows **metal pillars** instead of balls for higher current. Both would relax the
budget. Neither is modelled here.
