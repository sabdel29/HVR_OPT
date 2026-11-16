# complete-package thermal cross-check (TCPMT revision): the production CalculiX deck,
# exported block-for-block. Units mm, W, K.
[Mesh]
  [file]
    type = FileMeshGenerator
    file = fullpkg.msh
  []
[]
[Variables]
  [T]
    initial_condition = 25.0
  []
[]
[Kernels]
  [conduction]
    type = AnisoHeatConduction
    variable = T
  []
  [q_e_src_1]
    type = BodyForce
    variable = T
    value = 6.66707202
    block = 'silicon__src1'
  []
  [q_e_src_2]
    type = BodyForce
    variable = T
    value = 0.107016852
    block = 'silicon__src2'
  []
  [q_e_src_3]
    type = BodyForce
    variable = T
    value = 0.597230225
    block = 'silicon__src3'
  []
  [q_e_src_4]
    type = BodyForce
    variable = T
    value = 0.104420491
    block = 'hvr_effective__src4'
  []
  [q_e_src_5]
    type = BodyForce
    variable = T
    value = 0.0523927496
    block = 'hvr_effective__src5'
  []
  [q_e_src_6]
    type = BodyForce
    variable = T
    value = 0.131608982
    block = 'rdl_tier__src6'
  []
  [q_e_src_7]
    type = BodyForce
    variable = T
    value = 0.00655753712
    block = 'bga_homog__src7'
  []
  [q_e_src_8]
    type = BodyForce
    variable = T
    value = 4.22392382e-06
    block = 'tsv_tile__src8'
  []
  [q_e_src_9]
    type = BodyForce
    variable = T
    value = 0.016116286
    block = 'microbump__src9'
  []
[]
[Materials]
  [k_bga_homog]
    type = AnisoHeatConductionMaterial
    block = 'bga_homog__src7'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '0.00981748 0 0 0 0.00981748 0 0 0 0.00981748'
  []
  [k_board_fr4]
    type = AnisoHeatConductionMaterial
    block = 'board_fr4'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '0.0658592 0 0 0 0.0658592 0 0 0 0.000446083'
  []
  [k_hvr_effective]
    type = AnisoHeatConductionMaterial
    block = 'hvr_effective__src4 hvr_effective__src5'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '0.06 0 0 0 0.06 0 0 0 0.06'
  []
  [k_microbump]
    type = AnisoHeatConductionMaterial
    block = 'microbump microbump__src9'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '0.000891 0 0 0 0.000891 0 0 0 0.011739'
  []
  [k_rdl_tier]
    type = AnisoHeatConductionMaterial
    block = 'rdl_tier__src6'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '0.0342845 0 0 0 0.0342845 0 0 0 0.000620474'
  []
  [k_silicon]
    type = AnisoHeatConductionMaterial
    block = 'silicon silicon__src1 silicon__src2 silicon__src3'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '0.13 0 0 0 0.13 0 0 0 0.13'
  []
  [k_tim]
    type = AnisoHeatConductionMaterial
    block = 'tim'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '0.003 0 0 0 0.003 0 0 0 0.003'
  []
  [k_tsv_tile]
    type = AnisoHeatConductionMaterial
    block = 'tsv_tile tsv_tile__src8'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '0.156561 0 0 0 0.156561 0 0 0 0.179125'
  []
  [k_underfill_homog]
    type = AnisoHeatConductionMaterial
    block = 'underfill_homog'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '0.0007 0 0 0 0.0007 0 0 0 0.0007'
  []
[]
[BCs]
  [film_bottom]
    type = ConvectiveHeatFluxBC
    variable = T
    boundary = bottom
    T_infinity = 25.0
    heat_transfer_coefficient = 1e-05
  []
  [film_top]
    type = ConvectiveHeatFluxBC
    variable = T
    boundary = top
    T_infinity = 25.0
    heat_transfer_coefficient = 0.115553493
  []
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  line_search = none
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu mumps'
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
  nl_max_its = 4
[]
[Postprocessors]
  [Tmax]
    type = NodalExtremeValue
    variable = T
  []
  [intT_bottom]
    type = SideIntegralVariablePostprocessor
    variable = T
    boundary = bottom
  []
  [area_bottom]
    type = AreaPostprocessor
    boundary = bottom
  []
  [intT_top]
    type = SideIntegralVariablePostprocessor
    variable = T
    boundary = top
  []
  [area_top]
    type = AreaPostprocessor
    boundary = top
  []
  [volume]
    type = VolumePostprocessor
  []
[]
[VectorPostprocessors]
  [nodal]
    type = NodalValueSampler
    variable = T
    sort_by = id
    execute_on = FINAL
  []
[]
[Outputs]
  [out]
    type = CSV
    precision = 16
    execute_on = FINAL
  []
  perf_graph = true
[]
