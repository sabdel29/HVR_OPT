# tsv_tile_rve

Reference: Ansys Electronics Desktop 2026 R1 Mechanical, steady conduction (exact analogue of DC conduction).
Images 01_geometry_kx.png, 01_geometry_kz.png were exported from the AEDT session that produced the numbers (native ExportModelImageToFile under a virtual display).
AEDT field plots fail over this PyAEDT/gRPC pairing, so no field image is shown; none is synthesised.

| observable | production | AEDT | error |
|---|---|---|---|
| tile effective kz (W/mK) | 179.156 | 177.891 | +0.711 % |
| tile effective kx (W/mK) | 156.579 | 156.182 | +0.255 % |

Runtimes: the production model is the median of repeated calls; the AEDT reference is the median of three re-solves after a warm-up (4 cores) where reference_retimed is present, otherwise its single first solve. See runtime.json.
