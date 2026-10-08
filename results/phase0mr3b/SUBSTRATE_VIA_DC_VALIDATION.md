# PHASE 0M-R3B SECTION 5 --- 3-D DC VALIDATION OF THE VIA CHAIN

The analytical model puts each segment's `rho L / A` in series. The real path spreads into a capture land at every level and re-converges into the next via, so the series value is a lower bound. One representative column was solved in 3-D on the framework's own conservative finite-volume DC code.

## Control

A plain copper bar returns `rho L / A` to **-0.000 %**. Current conservation is checked on every solve and holds at machine precision (worst case 4e-11 % of the injected current).

## The chain

| case | mesh | R analytical | R 3-D | 3-D / analytical |
|---|---|---|---|---|
| via_chain_d120_pad180 | 16 | 2.3298e-04 Ohm | 2.9087e-04 Ohm | 1.2485 |
| via_chain_d120_pad180 | 24 | 2.3298e-04 Ohm | 2.6154e-04 Ohm | 1.1226 |
| via_chain_d120_pad180 | 32 | 2.3298e-04 Ohm | 2.6546e-04 Ohm | 1.1394 |
| via_chain_d120_pad180 | 48 | 2.3298e-04 Ohm | 2.7128e-04 Ohm | 1.1644 |
| via_chain_d120_pad180 | 64 | 2.3298e-04 Ohm | 2.7094e-04 Ohm | 1.1629 |
| via_chain_d70_pad110 | 16 | 6.9298e-04 Ohm | 7.7621e-04 Ohm | 1.1201 |
| via_chain_d70_pad110 | 24 | 6.9298e-04 Ohm | 8.1979e-04 Ohm | 1.1830 |
| via_chain_d70_pad110 | 32 | 6.9298e-04 Ohm | 8.2545e-04 Ohm | 1.1912 |
| via_chain_d70_pad110 | 48 | 6.9298e-04 Ohm | 8.0675e-04 Ohm | 1.1642 |
| via_chain_d70_pad110 | 64 | 6.9298e-04 Ohm | 8.0404e-04 Ohm | 1.1603 |

Both geometries converge, and to the same answer:

| geometry | converged ratio | mesh drift, two finest |
|---|---|---|
| via_chain_d120_pad180 | **1.1629** | 0.13 % |
| via_chain_d70_pad110 | **1.1603** | 0.34 % |

**The series model understates the vertical path by about 16 %**, and the penalty is insensitive to via diameter -- it is the land spreading, not the via. No global crowding multiplier is introduced; this is a measured, geometry-specific correction for one structure.

Q3D remains unlicensed. HFSS was not used: this is a DC extraction and HFSS would answer a different question.
