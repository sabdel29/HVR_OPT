[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 12 ny = 12 nz = 12
    xmin = 0 xmax = 0.0001 ymin = 0 ymax = 2e-05 zmin = 0 zmax = 2e-05
  []
[]
[Variables/V]
  initial_condition = 0.5
[]
[Kernels/cond]
  type = HeatConduction
  variable = V
[]
[Materials/m]
  type = HeatConductionMaterial
  thermal_conductivity = 58000000
[]
[BCs]
  [i]
    type = DirichletBC
    variable = V
    boundary = left
    value = 1.0
  []
  [o]
    type = DirichletBC
    variable = V
    boundary = right
    value = 0.0
  []
[]
[Postprocessors/Q_in]
  type = SideDiffusiveFluxIntegral
  variable = V
  boundary = left
  diffusivity = thermal_conductivity
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  nl_rel_tol = 1e-12
[]
[Outputs]
  csv = true
[]
