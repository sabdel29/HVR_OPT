[Mesh]
  [f]
    type = FileMeshGenerator
    file = column.msh
  []
[]
[Variables]
  [T]
    initial_condition = 30.0665
  []
[]
[Kernels]
  [cond]
    type = AnisoHeatConduction
    variable = T
  []
  [src0]
    type = BodyForce
    variable = T
    value = 6.789980878210e+00
    block = 'die__gap die__tile'
  []
  [src1]
    type = BodyForce
    variable = T
    value = 1.103889939037e-01
    block = 'z1conv_1_gan_hs_EPC2014C__tile'
  []
  [src2]
    type = BodyForce
    variable = T
    value = 5.759213146760e-01
    block = 'z1conv_3_gan_ls_EPC2057__tile'
  []
  [src3]
    type = BodyForce
    variable = T
    value = 1.065270919059e-01
    block = 'z1conv_7_inductor_plus_cout__tile'
  []
  [src4]
    type = BodyForce
    variable = T
    value = 5.239274958813e-02
    block = 'z1conv_5_flying_caps__tile'
  []
  [src5]
    type = BodyForce
    variable = T
    value = 3.052148431940e-01
    block = 'z1conv_0_bottom_substrate_rdl__tile z1conv_2_interlayer_rdl__tile z1conv_4_interlayer_rdl__tile z1conv_6_interlayer_rdl__tile z1conv_8_output_rdl__tile'
  []
  [src6]
    type = BodyForce
    variable = T
    value = 1.200522790043e-02
    block = 'bga__gap bga__tile'
  []
  [src7]
    type = BodyForce
    variable = T
    value = 4.217881662438e-06
    block = 'sub_lower__tile'
  []
  [src8]
    type = BodyForce
    variable = T
    value = 1.608131926902e-02
    block = 'interface__tile'
  []
[]
[Materials]
  [m_board__gap]
    type = AnisoHeatConductionMaterial
    block = 'board__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '6.585922500000e-02 0 0 0 6.585922500000e-02 0 0 0 4.460832839999e-04'
  []
  [m_board__tile]
    type = AnisoHeatConductionMaterial
    block = 'board__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '6.585922500000e-02 0 0 0 6.585922500000e-02 0 0 0 4.460832839999e-04'
  []
  [m_bga__gap]
    type = AnisoHeatConductionMaterial
    block = 'bga__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '9.817477042468e-03 0 0 0 9.817477042468e-03 0 0 0 9.817477042468e-03'
  []
  [m_bga__tile]
    type = AnisoHeatConductionMaterial
    block = 'bga__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '9.817477042468e-03 0 0 0 9.817477042468e-03 0 0 0 9.817477042468e-03'
  []
  [m_sub_lower__gap]
    type = AnisoHeatConductionMaterial
    block = 'sub_lower__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '1.300000000000e-01 0 0 0 1.300000000000e-01 0 0 0 1.300000000000e-01'
  []
  [m_sub_lower__tile]
    type = AnisoHeatConductionMaterial
    block = 'sub_lower__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '1.565608166239e-01 0 0 0 1.565608166239e-01 0 0 0 1.791247651249e-01'
  []
  [m_tile_band__gap]
    type = AnisoHeatConductionMaterial
    block = 'tile_band__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '1.300000000000e-01 0 0 0 1.300000000000e-01 0 0 0 1.300000000000e-01'
  []
  [m_tile_band__tile]
    type = AnisoHeatConductionMaterial
    block = 'tile_band__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '1.565608166239e-01 0 0 0 1.565608166239e-01 0 0 0 1.791247651249e-01'
  []
  [m_z1conv_0_bottom_substrate_rdl__gap]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_0_bottom_substrate_rdl__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '7.000000000000e-04 0 0 0 7.000000000000e-04 0 0 0 7.000000000000e-04'
  []
  [m_z1conv_0_bottom_substrate_rdl__tile]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_0_bottom_substrate_rdl__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '3.428454136258e-02 0 0 0 3.428454136258e-02 0 0 0 6.204741529454e-04'
  []
  [m_z1conv_1_gan_hs_EPC2014C__gap]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_1_gan_hs_EPC2014C__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '7.000000000000e-04 0 0 0 7.000000000000e-04 0 0 0 7.000000000000e-04'
  []
  [m_z1conv_1_gan_hs_EPC2014C__tile]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_1_gan_hs_EPC2014C__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '1.300000000000e-01 0 0 0 1.300000000000e-01 0 0 0 1.300000000000e-01'
  []
  [m_z1conv_2_interlayer_rdl__gap]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_2_interlayer_rdl__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '7.000000000000e-04 0 0 0 7.000000000000e-04 0 0 0 7.000000000000e-04'
  []
  [m_z1conv_2_interlayer_rdl__tile]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_2_interlayer_rdl__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '3.428454136258e-02 0 0 0 3.428454136258e-02 0 0 0 6.204741529454e-04'
  []
  [m_z1conv_3_gan_ls_EPC2057__gap]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_3_gan_ls_EPC2057__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '7.000000000000e-04 0 0 0 7.000000000000e-04 0 0 0 7.000000000000e-04'
  []
  [m_z1conv_3_gan_ls_EPC2057__tile]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_3_gan_ls_EPC2057__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '1.300000000000e-01 0 0 0 1.300000000000e-01 0 0 0 1.300000000000e-01'
  []
  [m_z1conv_4_interlayer_rdl__gap]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_4_interlayer_rdl__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '7.000000000000e-04 0 0 0 7.000000000000e-04 0 0 0 7.000000000000e-04'
  []
  [m_z1conv_4_interlayer_rdl__tile]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_4_interlayer_rdl__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '3.428454136258e-02 0 0 0 3.428454136258e-02 0 0 0 6.204741529454e-04'
  []
  [m_z1conv_5_flying_caps__gap]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_5_flying_caps__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '7.000000000000e-04 0 0 0 7.000000000000e-04 0 0 0 7.000000000000e-04'
  []
  [m_z1conv_5_flying_caps__tile]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_5_flying_caps__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '6.000000000000e-02 0 0 0 6.000000000000e-02 0 0 0 6.000000000000e-02'
  []
  [m_z1conv_6_interlayer_rdl__gap]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_6_interlayer_rdl__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '7.000000000000e-04 0 0 0 7.000000000000e-04 0 0 0 7.000000000000e-04'
  []
  [m_z1conv_6_interlayer_rdl__tile]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_6_interlayer_rdl__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '3.428454136258e-02 0 0 0 3.428454136258e-02 0 0 0 6.204741529454e-04'
  []
  [m_z1conv_7_inductor_plus_cout__gap]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_7_inductor_plus_cout__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '7.000000000000e-04 0 0 0 7.000000000000e-04 0 0 0 7.000000000000e-04'
  []
  [m_z1conv_7_inductor_plus_cout__tile]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_7_inductor_plus_cout__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '6.000000000000e-02 0 0 0 6.000000000000e-02 0 0 0 6.000000000000e-02'
  []
  [m_z1conv_8_output_rdl__gap]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_8_output_rdl__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '7.000000000000e-04 0 0 0 7.000000000000e-04 0 0 0 7.000000000000e-04'
  []
  [m_z1conv_8_output_rdl__tile]
    type = AnisoHeatConductionMaterial
    block = 'z1conv_8_output_rdl__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '3.428454136258e-02 0 0 0 3.428454136258e-02 0 0 0 6.204741529454e-04'
  []
  [m_interface__gap]
    type = AnisoHeatConductionMaterial
    block = 'interface__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '8.910000000000e-04 0 0 0 8.910000000000e-04 0 0 0 1.173900000000e-02'
  []
  [m_interface__tile]
    type = AnisoHeatConductionMaterial
    block = 'interface__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '8.910000000000e-04 0 0 0 8.910000000000e-04 0 0 0 1.173900000000e-02'
  []
  [m_die__gap]
    type = AnisoHeatConductionMaterial
    block = 'die__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '1.300000000000e-01 0 0 0 1.300000000000e-01 0 0 0 1.300000000000e-01'
  []
  [m_die__tile]
    type = AnisoHeatConductionMaterial
    block = 'die__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '1.300000000000e-01 0 0 0 1.300000000000e-01 0 0 0 1.300000000000e-01'
  []
  [m_tim__gap]
    type = AnisoHeatConductionMaterial
    block = 'tim__gap'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '3.000000000000e-03 0 0 0 3.000000000000e-03 0 0 0 3.000000000000e-03'
  []
  [m_tim__tile]
    type = AnisoHeatConductionMaterial
    block = 'tim__tile'
    temperature = T
    specific_heat = 1
    thermal_conductivity = '3.000000000000e-03 0 0 0 3.000000000000e-03 0 0 0 3.000000000000e-03'
  []
[]
[BCs]
  [top]
    type = ConvectiveHeatFluxBC
    variable = T
    boundary = top
    T_infinity = 30.0664853
    heat_transfer_coefficient = 1.155534926155e-01
  []
  [bot]
    type = ConvectiveHeatFluxBC
    variable = T
    boundary = bottom
    T_infinity = 25
    heat_transfer_coefficient = 1.000000000000e-05
  []
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  line_search = none
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  l_tol = 1e-11
  l_max_its = 300
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-30
  nl_max_its = 5
[]
[Postprocessors]
  [Tmax]
    type = NodalExtremeValue
    variable = T
  []
  [avg_board__gap]
    type = ElementAverageValue
    variable = T
    block = 'board__gap'
  []
  [avg_board__tile]
    type = ElementAverageValue
    variable = T
    block = 'board__tile'
  []
  [avg_bga__gap]
    type = ElementAverageValue
    variable = T
    block = 'bga__gap'
  []
  [avg_bga__tile]
    type = ElementAverageValue
    variable = T
    block = 'bga__tile'
  []
  [avg_sub_lower__gap]
    type = ElementAverageValue
    variable = T
    block = 'sub_lower__gap'
  []
  [avg_sub_lower__tile]
    type = ElementAverageValue
    variable = T
    block = 'sub_lower__tile'
  []
  [avg_tile_band__gap]
    type = ElementAverageValue
    variable = T
    block = 'tile_band__gap'
  []
  [avg_tile_band__tile]
    type = ElementAverageValue
    variable = T
    block = 'tile_band__tile'
  []
  [avg_z1conv_0_bottom_substrate_rdl__gap]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_0_bottom_substrate_rdl__gap'
  []
  [avg_z1conv_0_bottom_substrate_rdl__tile]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_0_bottom_substrate_rdl__tile'
  []
  [avg_z1conv_1_gan_hs_EPC2014C__gap]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_1_gan_hs_EPC2014C__gap'
  []
  [avg_z1conv_1_gan_hs_EPC2014C__tile]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_1_gan_hs_EPC2014C__tile'
  []
  [avg_z1conv_2_interlayer_rdl__gap]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_2_interlayer_rdl__gap'
  []
  [avg_z1conv_2_interlayer_rdl__tile]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_2_interlayer_rdl__tile'
  []
  [avg_z1conv_3_gan_ls_EPC2057__gap]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_3_gan_ls_EPC2057__gap'
  []
  [avg_z1conv_3_gan_ls_EPC2057__tile]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_3_gan_ls_EPC2057__tile'
  []
  [avg_z1conv_4_interlayer_rdl__gap]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_4_interlayer_rdl__gap'
  []
  [avg_z1conv_4_interlayer_rdl__tile]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_4_interlayer_rdl__tile'
  []
  [avg_z1conv_5_flying_caps__gap]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_5_flying_caps__gap'
  []
  [avg_z1conv_5_flying_caps__tile]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_5_flying_caps__tile'
  []
  [avg_z1conv_6_interlayer_rdl__gap]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_6_interlayer_rdl__gap'
  []
  [avg_z1conv_6_interlayer_rdl__tile]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_6_interlayer_rdl__tile'
  []
  [avg_z1conv_7_inductor_plus_cout__gap]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_7_inductor_plus_cout__gap'
  []
  [avg_z1conv_7_inductor_plus_cout__tile]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_7_inductor_plus_cout__tile'
  []
  [avg_z1conv_8_output_rdl__gap]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_8_output_rdl__gap'
  []
  [avg_z1conv_8_output_rdl__tile]
    type = ElementAverageValue
    variable = T
    block = 'z1conv_8_output_rdl__tile'
  []
  [avg_interface__gap]
    type = ElementAverageValue
    variable = T
    block = 'interface__gap'
  []
  [avg_interface__tile]
    type = ElementAverageValue
    variable = T
    block = 'interface__tile'
  []
  [avg_die__gap]
    type = ElementAverageValue
    variable = T
    block = 'die__gap'
  []
  [avg_die__tile]
    type = ElementAverageValue
    variable = T
    block = 'die__tile'
  []
  [avg_tim__gap]
    type = ElementAverageValue
    variable = T
    block = 'tim__gap'
  []
  [avg_tim__tile]
    type = ElementAverageValue
    variable = T
    block = 'tim__tile'
  []
[]
[Outputs]
  csv = true
  exodus = true
[]
