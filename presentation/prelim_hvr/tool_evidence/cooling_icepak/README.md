# cooling_icepak: matched conjugate CFD of the cold-plate correlation

Status: **EXECUTED**. Reference: Ansys Electronics Desktop 2026 R1 Icepak (steady, laminar conjugate CFD), PyAEDT 1.1.

Production model: the compact laminar microchannel correlation (`cooling_production.py` TOP_SI_MICROCHANNEL_27 -> `cooling.py` `Microchannel.solve()`): Shah & London fully developed Nu with three heated walls, straight-fin efficiency, R_total = R_conv + R_caloric + R_base.

Matched Icepak problem: one half pitch (25 um half fin + 25 um half channel) with symmetry walls on both sides, the full 22.36 mm length, silicon base 100 um under 300 um fins (k = 130 W/mK), water with exactly the correlation's constant properties, laminar steady flow, inlet mass flow 27 g/s / 223 / 2 at 25 C, outlet at gauge pressure 0, uniform heat flux Q/A_foot = 2.2931 MW/m2 on the base underside (Q = 1146.47 W, Z1 HV-S0 converged ledger), adiabatic lid and end faces.

Correlation: dT = Q R_total = 19.844 K, h_eff = 115,553 W/m2K (R_conv 0.01134, R_caloric 0.00443, R_base 0.00154 K/W; Re 1265, Nu 4.603). For exactly the CFD loading (Q/A_foot over one 100 um pitch) the same terms give 19.796 K.

| level | dx / dy / dz (um) | cells | iterations | CFD mean underside dT (K) | CFD h_eff (W/m2K) | CFD vs Q R_total | solve wall (min) |
|---|---|---|---|---|---|---|---|
| baseline | 200 / 4.17 / 10 | 53760 | 572 | 16.923 | 135,501 | -14.72 % | 1.8 |
| fine | 200 / 2.08 / 5 | 215040 | 1175 | 16.987 | 134,990 | -14.40 % | 10.6 |
| baseline_x | 100 / 4.17 / 10 | 107520 | 791 | 16.926 | 135,479 | -14.71 % | 3.4 |
| fine_x | 100 / 2.08 / 5 | 430080 | 1321 | 16.994 | 134,932 | -14.36 % | 21.8 |

dT is the area-mean temperature of the heated underside minus the 25 C inlet (Icepak field summary). Mesh change and convergence details are in result.json; timings (wall clock around analyze_setup, 4 cores, one solve per level, shared machine) in runtime.json.

- Mesh change of the mean underside dT, baseline -> fine (dy, dz halved): +0.377 %.
- Mesh change of the mean underside dT, baseline -> baseline_x (dx halved): +0.016 %.
- Mesh change of the mean underside dT, fine -> fine_x (dx halved): +0.043 %.
- Tightening the convergence criteria from flow 1e-5 / energy 1e-10 to 1e-06 / 1e-12 changed dT by at most 0.032 % (per level in result.json).
- Energy check (fine_x): convective heat from the silicon into the water 2.563667 W (fin flanks 2.42389 W, channel floor 0.13978 W) against 2.563668 W applied.
- Pressure drop (fine_x): CFD 567.7 kPa vs the correlation's fully developed 537.8 kPa (+5.6 %; developing-flow pressure loss is included in the CFD).
- Along the channel (fine_x, underside point monitors): wall-to-bulk difference 7.77 K at 0.5 mm, 10.21 K at 2 mm, 11.89 K at 6 mm, 12.44 K at 11.18 mm, 12.66 K at 21.5 mm, against the correlation's constant fully developed 14.73 K. The CFD value levels off over the second half of the channel yet stays below it at the outlet end, so the gap is not only the entrance effect; this points to the fully developed model itself (Nu table and its wall boundary condition, uniform-h fin efficiency) for the rest. This test does not separate those terms.
- A third cross-section level ('finer', ~860k cells) was defined but not run, to bound runtime; no order of convergence is claimed.

## Caveats

- The correlation is fully developed (Shah & London Nu, constant along the channel). At Re ~ 1265 and Pr ~ 3.6 the hydrodynamic entry length 0.05 Re D_h is ~5.4 mm and the thermal entry length 0.05 Re Pr D_h is ~19 mm, i.e. most of the 22.36 mm channel is thermally developing; the CFD includes that entrance enhancement and the correlation does not.
- Fin efficiency in the correlation assumes a uniform h on the fin flanks; the CFD resolves the true conjugate distribution.
- Constant fluid properties at the correlation's values (no temperature dependence of viscosity), so the comparison isolates the heat-transfer model, not property variation.
- One periodic channel with uniform flux: manifold maldistribution, header losses and the non-uniform heat map of the package are outside this test.

## Images

01_geometry.png, 01_geometry_side.png: exported from an AEDT Icepak session that opened the solved baseline project (native ExportModelImageToFile under a virtual display): 01_geometry.png is the default isometric view of the whole half-pitch domain, 01_geometry_side.png the side elevation (x-z). At AEDT's fit-all zoom the 22.36 mm length dominates, so the 50 um x 400 um cross-section is only a few pixels; an end-on export showed nothing but the axes and is not included.
Field plots are not exported (field-plot creation fails over this PyAEDT/gRPC pairing); none is synthesised.

