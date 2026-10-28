
[Mesh]
  [f]
    type = FileMeshGenerator
    file = /tmp/moose_rdl_Z2/rdl_m3.msh
  []
[]
[Variables]
  [V]
  []
[]
[Kernels]
  [cond]
    type = HeatConduction
    variable = V
  []
  [contact]
    type = Reaction
    variable = V
    rate = 2.040816247119e+04
    block = 'ball0 ball1 ball2 ball3 ball4 ball5 ball6 ball7 ball8 ball9 ball10 ball11 ball12 ball13 ball14 ball15 ball16 ball17 ball18 ball19 ball20 ball21 ball22 ball23 ball24 ball25 ball26 ball27 ball28 ball29 ball30 ball31 ball32 ball33 ball34 ball35 ball36 ball37 ball38 ball39 ball40 ball41 ball42 ball43 ball44 ball45 ball46 ball47 ball48 ball49 ball50 ball51 ball52 ball53'
  []
  [draw]
    type = BodyForce
    variable = V
    value = -5.102040816327e-01
    block = 'pad0 pad1 pad2 pad3 pad4 pad5 pad6 pad7 pad8 pad9 pad10 pad11 pad12 pad13 pad14 pad15 pad16 pad17 pad18 pad19 pad20 pad21 pad22 pad23 pad24 pad25 pad26 pad27 pad28 pad29 pad30 pad31 pad32 pad33 pad34 pad35 pad36 pad37 pad38 pad39 pad40 pad41 pad42 pad43 pad44 pad45 pad46 pad47 pad48'
  []
[]
[Materials]
  [k]
    type = GenericConstantMaterial
    prop_names = 'thermal_conductivity'
    prop_values = '8.823529411765e+01'
  []
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  line_search = none
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  l_tol = 1e-12
  l_max_its = 300
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-30
  nl_max_its = 5
[]
[Postprocessors]
  [v0]
    type = ElementAverageValue
    variable = V
    block = pad0
  []
  [v1]
    type = ElementAverageValue
    variable = V
    block = pad1
  []
  [v2]
    type = ElementAverageValue
    variable = V
    block = pad2
  []
  [v3]
    type = ElementAverageValue
    variable = V
    block = pad3
  []
  [v4]
    type = ElementAverageValue
    variable = V
    block = pad4
  []
  [v5]
    type = ElementAverageValue
    variable = V
    block = pad5
  []
  [v6]
    type = ElementAverageValue
    variable = V
    block = pad6
  []
  [v7]
    type = ElementAverageValue
    variable = V
    block = pad7
  []
  [v8]
    type = ElementAverageValue
    variable = V
    block = pad8
  []
  [v9]
    type = ElementAverageValue
    variable = V
    block = pad9
  []
  [v10]
    type = ElementAverageValue
    variable = V
    block = pad10
  []
  [v11]
    type = ElementAverageValue
    variable = V
    block = pad11
  []
  [v12]
    type = ElementAverageValue
    variable = V
    block = pad12
  []
  [v13]
    type = ElementAverageValue
    variable = V
    block = pad13
  []
  [v14]
    type = ElementAverageValue
    variable = V
    block = pad14
  []
  [v15]
    type = ElementAverageValue
    variable = V
    block = pad15
  []
  [v16]
    type = ElementAverageValue
    variable = V
    block = pad16
  []
  [v17]
    type = ElementAverageValue
    variable = V
    block = pad17
  []
  [v18]
    type = ElementAverageValue
    variable = V
    block = pad18
  []
  [v19]
    type = ElementAverageValue
    variable = V
    block = pad19
  []
  [v20]
    type = ElementAverageValue
    variable = V
    block = pad20
  []
  [v21]
    type = ElementAverageValue
    variable = V
    block = pad21
  []
  [v22]
    type = ElementAverageValue
    variable = V
    block = pad22
  []
  [v23]
    type = ElementAverageValue
    variable = V
    block = pad23
  []
  [v24]
    type = ElementAverageValue
    variable = V
    block = pad24
  []
  [v25]
    type = ElementAverageValue
    variable = V
    block = pad25
  []
  [v26]
    type = ElementAverageValue
    variable = V
    block = pad26
  []
  [v27]
    type = ElementAverageValue
    variable = V
    block = pad27
  []
  [v28]
    type = ElementAverageValue
    variable = V
    block = pad28
  []
  [v29]
    type = ElementAverageValue
    variable = V
    block = pad29
  []
  [v30]
    type = ElementAverageValue
    variable = V
    block = pad30
  []
  [v31]
    type = ElementAverageValue
    variable = V
    block = pad31
  []
  [v32]
    type = ElementAverageValue
    variable = V
    block = pad32
  []
  [v33]
    type = ElementAverageValue
    variable = V
    block = pad33
  []
  [v34]
    type = ElementAverageValue
    variable = V
    block = pad34
  []
  [v35]
    type = ElementAverageValue
    variable = V
    block = pad35
  []
  [v36]
    type = ElementAverageValue
    variable = V
    block = pad36
  []
  [v37]
    type = ElementAverageValue
    variable = V
    block = pad37
  []
  [v38]
    type = ElementAverageValue
    variable = V
    block = pad38
  []
  [v39]
    type = ElementAverageValue
    variable = V
    block = pad39
  []
  [v40]
    type = ElementAverageValue
    variable = V
    block = pad40
  []
  [v41]
    type = ElementAverageValue
    variable = V
    block = pad41
  []
  [v42]
    type = ElementAverageValue
    variable = V
    block = pad42
  []
  [v43]
    type = ElementAverageValue
    variable = V
    block = pad43
  []
  [v44]
    type = ElementAverageValue
    variable = V
    block = pad44
  []
  [v45]
    type = ElementAverageValue
    variable = V
    block = pad45
  []
  [v46]
    type = ElementAverageValue
    variable = V
    block = pad46
  []
  [v47]
    type = ElementAverageValue
    variable = V
    block = pad47
  []
  [v48]
    type = ElementAverageValue
    variable = V
    block = pad48
  []
[]
[Outputs]
  csv = true
  exodus = true
[]
