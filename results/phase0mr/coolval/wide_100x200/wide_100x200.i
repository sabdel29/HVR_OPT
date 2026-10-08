[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 3
    nx = 10 ny = 4 nz = 34
    xmin = 0 xmax = 0.0001 ymin = 0 ymax = 0.001 zmin = 0 zmax = 0.0003
  []
  [carve]
    type = ParsedSubdomainMeshGenerator
    input = gen
    combinatorial_geometry = 'x > 5e-05 & z > 0.0001'
    block_id = 9
  []
  [kill]
    type = BlockDeletionGenerator
    input = carve
    block = '9'
    new_boundary = 'wet'
  []
  [walltop]
    type = ParsedGenerateSideset
    input = kill
    combinatorial_geometry = 'z > 0.000299999999 & x < 5.0000001e-05'
    normal = '0 0 1'
    new_sideset_name = 'fintop'
  []
  [basess]
    type = ParsedGenerateSideset
    input = walltop
    combinatorial_geometry = 'z < 1e-12'
    normal = '0 0 -1'
    new_sideset_name = 'base'
  []
[]
[Variables/T]
  initial_condition = 0.0
[]
[Kernels/c]
  type = HeatConduction
  variable = T
[]
[Materials/m]
  type = HeatConductionMaterial
  thermal_conductivity = 130
[]
[BCs]
  [q_in]
    type = NeumannBC
    variable = T
    boundary = 'base'
    value = 10000
  []
  [conv_wet]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'wet'
    T_infinity = 0.0
    coefficient = 84692.3842
  []
  [conv_top]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'fintop'
    T_infinity = 0.0
    coefficient = 84692.3842
  []
[]
[Postprocessors]
  [T_base]
    type = SideAverageValue
    variable = T
    boundary = 'base'
  []
  [A_base]
    type = AreaPostprocessor
    boundary = 'base'
  []
  [Q_wet]
    type = SideDiffusiveFluxIntegral
    variable = T
    boundary = 'wet'
    diffusivity = thermal_conductivity
  []
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  nl_rel_tol = 1e-11
[]
[Outputs]
  csv = true
[]
