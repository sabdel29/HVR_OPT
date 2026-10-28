# pkg_rdl_moose_Z2

Reference: MOOSE heat_transfer-opt solving the exact analogue div(k grad T) = -q of the DC sheet problem on an unstructured gmsh mesh.
04_field.png is rendered from MOOSE's own Exodus output of the finest mesh.
rdl.i is the MOOSE input as run; moose_log_tail.txt the end of its log.

- R_eff error vs finest MOOSE mesh: +0.108 %
- max pad drop error: +0.063 %
- runtime ratio (MOOSE m3 / production L3, medians): 2.49
