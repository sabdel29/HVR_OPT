# Visual tool inventory

What visual tooling this host actually has, how each tool was probed, and what the project
uses it for. Probed on 2026-10-27 on the study host; usage rows updated 2026-10-28 from the committed scripts (direct-fed Z2 figures added the same day). Every Python command runs in the
project environment (`export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH`, then `python`).
Developer and what-it-is statements, with official sources, are in
`research/final_closure/tool_provenance.json`. This file makes no developer claims.

| tool | available? | version | how probed (exact command → result) | used for in this project / why not |
|---|---|---|---|---|
| Python (Matplotlib) | yes | Matplotlib 3.10.8, Python 3.12.14 | `python -c "import matplotlib; print(matplotlib.__version__)"` → `3.10.8`; `python --version` → `Python 3.12.14` | Every conventional chart: the deck charts in `figs/` (`scripts/final_closure_slide_charts.py`, `scripts/prelim_make_figs.py`, `scripts/prelim_make_figs_final.py`), the tool-evidence comparison bars and MOOSE field contours (`scripts/final_closure_evidence.py`), and the manuscript figures. It draws solver results; it is not a solver. |
| Native SVG (Python-generated) | yes, needs no library | SVG 1.1 text | `grep -c "<svg" scripts/prelim_build_deck.py` → `6`; `python scripts/final_closure_tool_map.py --selftest` → `9/9 injected violations caught` | Schematic diagrams, all with the `scripts/figstyle.py` helpers: the six inline diagrams of the deck (`scripts/prelim_build_deck.py`), `figs/tool_map.svg` (`scripts/final_closure_tool_map.py`), the Z1/Z2 cross-sections, comparison, cell zoom, exploded view, the power-path figures (`z1_z2_power_path_final/48v/1v.svg`) and the VR-attach detail (`z2_vr_attach_detail.svg`) (`scripts/final_closure_package_figs.py`, from `architecture_geometry.json` and `z2_direct_feed_architecture.json`) and the RDL explanatory figures (`scripts/visualize_rdl_geometry.py`). |
| PyVista / VTK | PyVista **no**; VTK **yes** | VTK 9.6.2 | `python -c "import pyvista"` → `ModuleNotFoundError`; `python -c "import vtk; print(vtk.vtkVersion.GetVTKVersion())"` → `9.6.2`; headless render test with no display (`env -u DISPLAY python -c '<offscreen sphere → vtkPNGWriter>'`) → `vtkXOpenGLRenderWindow … bad X server connection`, then the window class is `vtkEGLRenderWindow` and the PNG is written | VTK reads MOOSE's Exodus result files (`vtkExodusIIReader`, last stored step) in `scripts/final_closure_evidence.py` (Matplotlib then draws those field contours) and `scripts/visualize_rdl_geometry.py`. VTK also RENDERS, off-screen: the MOOSE field under the RDL annotation (`figs/rdl_reference_annotated_Z*.png`) and the geometry exported from the AEDT projects (`figs/rerender_*.png`, `scripts/reference_tools/aedt_geometry_rerender.py`). PyVista is not installed. PyPI is reachable, but nothing was installed into the env. |
| ParaView / pvpython | **no** | — | `command -v paraview pvpython pvbatch` → nothing; `python -c "import paraview"` → `ModuleNotFoundError` | Not used. VTK, which ParaView uses as its engine, is used directly. |
| Blender | **no** | — | `command -v blender` → nothing; `python -c "import bpy"` → `ModuleNotFoundError` | Not used. |
| Inkscape | **no** | — | `command -v inkscape` → nothing | Not used. SVG is written as text and rasterised with rsvg-convert or Chrome. |
| Plotly + Kaleido | **no** | — | `python -c "import plotly"` and `python -c "import kaleido"` → `ModuleNotFoundError`; `command -v kaleido` → nothing | Not used. Matplotlib covers every static chart. |
| Graphviz | yes | dot 2.40.1 | `dot -V` → `dot - graphviz version 2.40.1 (0)` | Installed, but no repository script calls it. Automatic layout cannot place the fixed lanes and hand-placed arrows the diagrams need, so diagrams are native SVG. |
| Mermaid | **no** | — | `command -v mmdc` → nothing; `npm ls -g --depth=0` → no `@mermaid-js/mermaid-cli` (node v24.15.0 and npx are present) | Not used. |
| Chromium / Playwright | Chromium **no**; **Google Chrome yes**; Playwright **no** | Google Chrome 151.0.7922.71 | `command -v chromium chromium-browser` → nothing; `google-chrome --version` → `Google Chrome 151.0.7922.71`; `python -c "import playwright"` → `ModuleNotFoundError`; `command -v playwright` → nothing | Headless Chrome prints `print.html` to `HVR_OPT_Prelim.pdf` (`scripts/prelim_qa_slides.py`; the PDF records `HeadlessChrome/151.0.0.0`, `Skia/PDF m151`). It was also used to cross-check the tool-map render. Playwright is not needed because plain Chrome flags are enough. |
| ImageMagick | yes | 6.9.13-52 Q16 | `convert -version` → `Version: ImageMagick 6.9.13-52 (Beta) Q16 x86_64` | Not used by any committed script (used by hand only, to tile figures for visual QA). Rasterising is done with rsvg-convert or Chrome. |
| Gmsh | yes | 4.15.2 (CLI and Python API) | `gmsh --version` → `4.15.2`; `python -c "import gmsh; print(gmsh.__version__)"` → `4.15.2` | Used as a mesher, not as a visual tool. It generates the 2-D package-RDL meshes for the MOOSE reference (`scripts/reference_tools/moose_pkg_rdl_reference.py`). Its GUI and post-processor are not used. |
| Figma / Canva | **no access** | — | no command to run: this environment has no account, connector or API token | Not used, and no access is claimed. |

Other tools probed:

| tool | version | probe | role |
|---|---|---|---|
| rsvg-convert (librsvg) | 2.62.3 in the etm env (the one the pipeline calls); `/bin/rsvg-convert` is 2.42.7 | `rsvg-convert --version` in each PATH | SVG to PNG: the exploded view (`scripts/final_closure_package_figs.py`), the RDL annotation layer (`scripts/visualize_rdl_geometry.py`) and visual checks of `figs/tool_map.svg` (`--png OUT.png`); SVG to vector PDF for the manuscript's architecture figures (`scripts/final_closure_manuscript_figure.py`). |
| Reveal.js | 5.1.0 (vendored) | `grep '"version"' presentation/prelim_hvr/vendor/reveal.js/package.json` | Slide framework of `index.html`. |
| cairosvg | CLI 2.9.0, not usable from the env | `~/.local/bin/cairosvg --version` → `2.9.0`, but its interpreter is another user's (`#!/home/beams/AMICELI/miniconda3/bin/python3`); `python -c "import cairosvg"` → `No module named 'cffi'` (user-site copy); `python -s -c "import cairosvg"` → `ModuleNotFoundError` | Not used. |
| pdftoppm | 20.11.0 | `pdftoppm -v` | Renders the deck PDF pages for the QA contact sheets (`scripts/prelim_qa_slides.py`). |
| PyMuPDF, python-pptx, Pillow | 1.28.2, 1.0.2, 12.3.0 | `python -c "import pymupdf; print(pymupdf.__version__)"` and likewise for the others | Pillow is used: screenshot crops and overlays (`scripts/reference_tools/aedt_annotate_screenshots.py`), the RDL and re-render images, the QA footer check (`scripts/prelim_qa_slides.py`) and the figure tests. PyMuPDF and python-pptx are present but imported by no script. |
| LibreOffice, Firefox, ffmpeg | 6.4.7.2, 140.13.0esr, 9.0.1 | `libreoffice --version`, `firefox --version`, `ffmpeg -version` | Present, not used. |

## Priority rule adopted

1. **Diagrams: native SVG written by Python** with the `scripts/figstyle.py` helpers and
   colours. The source is reviewable text, placement is exact, and a generator can check
   every label against the artifacts. `figs/tool_map.svg` reads tool names, versions and
   status from `tool_provenance.json`, and it fails if a box names an unknown tool, a line
   overflows, boxes overlap or an arrow crosses a box.
2. **3-D geometry and fields: VTK.** It is the only 3-D toolkit installed, because PyVista
   and ParaView are absent, and headless rendering works. Current state: VTK reads the MOOSE
   Exodus fields and renders the RDL field image and the re-renders of exported AEDT geometry;
   the other field images are 2-D Matplotlib contours of VTK-read data. The AEDT screenshots
   are exported by AEDT itself (`ExportModelImageToFile`), not drawn by us.
3. **Conventional plots: Matplotlib only.**
4. **Rasterising: rsvg-convert** (SVG to PNG) **and headless Chrome** (deck HTML to PDF,
   and SVG screenshots as a second renderer).

## What we did not have

There was no Figma or Canva access (no account, connector or API), so no figure was made
or edited in a design tool. ParaView, Blender, Inkscape, PyVista, Plotly/Kaleido,
Playwright, the Mermaid CLI and Chromium are not installed. Nothing was added to the
project environment, although PyPI is reachable. Every visual in the deck is therefore
Matplotlib, native SVG, a VTK render (MOOSE field; geometry exported from AEDT), or an image
exported by the reference tool itself (AEDT).

## Issue found during this inventory (resolved)

`scripts/figstyle.py` set `FONT = "Source Sans 3, Segoe UI, Helvetica, Arial, sans-serif"`
without quotes. A CSS family name that contains a number token (`3`) must be quoted, so the
whole `font-family` declaration was invalid and both headless Chrome and rsvg-convert 2.62
fell back to the default **serif** font (checked on the same text with both renderers:
unquoted gives serif, quoted gives sans; `/bin/rsvg-convert` 2.42.7 is lenient). `FONT` is
now quoted (`'Source Sans 3', 'Segoe UI', Arial, Helvetica, sans-serif`).
`scripts/final_closure_tool_map.py` and `scripts/visualize_rdl_geometry.py` still re-quote
the list in their own `<g>` wrappers, as a guard.
