# attach_rve

Reference: Ansys Electronics Desktop 2026 R1 Mechanical, steady conduction in one explicit unit cell of the periodic attach lattice (Cu pillar under its solder cap, underfill around it), on AEDT's default mesh and on a length-refined one.
Images 01_geometry_dense_kxy_auto.png, 01_geometry_dense_kxy_fine.png, 01_geometry_dense_kz_auto.png, 01_geometry_dense_kz_fine.png, 01_geometry_sparse_kxy_auto.png, 01_geometry_sparse_kxy_fine.png, 01_geometry_sparse_kz_auto.png, 01_geometry_sparse_kz_fine.png were exported from the AEDT sessions that produced the numbers.

| case | production | AEDT | error | auto -> refined mesh |
|---|---|---|---|---|
| dense_kz | 19.1406 | 19.0463 | +0.495 % | -0.0002 % |
| dense_kxy | 0.888644 | 0.885458 | +0.360 % | -0.0033 % |
| sparse_kz | 11.0291 | 10.8839 | +1.334 % | -0.0008 % |
| sparse_kxy | 0.746901 | 0.745621 | +0.172 % | -0.0037 % |

The card is compared at the unit cell's own infinite-lattice metal fraction; a variant's finite-lattice fraction differs from it only by the cell-edge strip.
