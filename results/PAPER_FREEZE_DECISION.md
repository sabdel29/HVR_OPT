# PAPER-FREEZE DECISION

Decided at the close of Phase 0M-R3C, the last planned technical gate.

## 1. The one-sentence contribution

> A physically audited electrothermal-mechanical co-design framework for distributed vertical power delivery that exposes architecture-dependent reliability RESPONSE, interconnect and assembly realizability constraints, and identifies when mechanics is design-relevant but not yet an active synthesis constraint.

## 2. The five strongest current claims

1. **The framework itself**, audited across twenty-two falsification gates with sixty-four registered defects, each corrected at source and negative-tested.
2. **Vertical placement changes the local solder response by 16.3 %**, backside lower, D_driver = 1.1947 on a frozen repartitioned pair with one production ETM solve per architecture.
3. **T_max ranking is not the response ranking** --- the hotter architecture carries the lower response, +8.14 K against -16.3 %.
4. **Rail-aware vertical current paths change intra-VR interconnect loss by orders of magnitude**, so interconnect is not common mode across partitions.
5. **Routing and assembly realizability can invalidate a numerically attractive architecture** --- and a pure permutation of the existing components drops the worst build-up aspect ratio from 5.05 to 0.83.

## 3. Conditional claims

| claim | conditional on |
|---|---|
| the 16.3 % MAGNITUDE | a variable-consistent SnAgCu Norton surrogate evaluated far outside its 7.51-15.92 MPa fitted window. The ORDERING is robust; the magnitude is an envelope |
| geometric realizability of the frozen pair | a source-BOUNDED microvia pitch; the diameter, capture pad, current allowable and vendor rule are OPEN |
| the relative-life envelope 1.19-1.22 | two sourced Coffin-Manson exponents; C cancels in the ratio |
| ARCH_Z4 ordering | an unsourced power-die construction |
| absolute temperatures | a cooler validated only at its laminar production point; conjugate CFD NOT COMPLETED |

## 4. Withdrawn historical claims

* the 35.8 % / 12.4 % separation as a CURRENT architecture result (it is the Phase-0I figure for a different, non-realizable set)
* "validated relative life"
* "Z2 outlives Z1" and every damage/life wording for the FE response
* the 1.558 relative-life ratio, the 1.25-9.18 parametric span, 16.2 W/um and 2.03 W/um exchange rates, the 188.8 % placement spread
* "the sourced 34 um via"; "22.8 % more vias" (it is 22.8 % fewer)
* the 673 um `ls_to_L` span, and the three-stacked-microvia count
* "1000 A cannot be fed laterally"
* the Phase-0M-R3 pair as a "current repaired realizable pair"

## 5. What must NOT be claimed

* any absolute lifetime, cycle count or margin against a requirement
* that either architecture is manufacturable, qualified or PROVEN_REALIZABLE
* that mechanics CHANGES the optimal DVPD architecture --- it has not been shown to be an active synthesis constraint
* that the FE output is damage, or that a damage law, life model or allowable exists
* that the framework is an optimizer, or that G2 has been tested

## 6. Open items that block publication

**None.** Every open item bears on absolute magnitude or on manufacturability, neither of which the paper claims.

## 7. Future work only

high-stress SAC305 characterisation; N_required; an admissible mechanical allowable and G2; conjugate CFD; cohesive delamination and crack growth; moisture; full process qualification of the package rules; the microvia current allowable and vendor design rule; the two remaining package clearances.

## 8. Is another technical phase scientifically necessary before submission?

**No.** Phase 0M-R3C found no fundamental model contradiction. The deciding ordering survived the entire interconnect correction at +0.04 %, which is the strongest evidence available that the result does not depend on the assumptions that were wrong. Framework development stops here.

## Scope statement for the manuscript

The paper is **not** framed as "mechanics changes the optimal DVPD architecture". It is framed as a framework paper whose negative results are part of the contribution:

* regulator count is mechanically inert over the swept range;
* the footprint/mechanics opposition disappears in a mounted assembly;
* global warpage is a poor proxy for local solder response;
* physical architecture and assembly state can reverse apparent conclusions;
* rail-aware current paths change interconnect loss by orders of magnitude;
* routing and process realizability can invalidate a numerically attractive architecture;
* T_max ranking need not equal local mechanical-response ranking.
