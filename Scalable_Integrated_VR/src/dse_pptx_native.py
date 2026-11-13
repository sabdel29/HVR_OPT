"""
dse_pptx_native.py
 
Creates fully native, editable PowerPoint bar charts for both DSE cases.
Each case produces ONE slide with TWO native charts side by side:
  Left  : Horizontal bar chart — Efficiency (%) per topology
  Right : Horizontal bar chart — Ripple budget utilisation (%) per topology
 
Both charts are fully editable in PowerPoint (right-click → Edit Data).
"""
 
import sys, os
import numpy as np
from lxml import etree
import copy
 
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.dml.color import RGBColor
from pptx.util import Pt
 
# ── Reuse DSE results from main script ───────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 
# Run the DSE silently and collect results
import importlib, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import dse_study_cases as dse
 
results1 = dse.results1
results2 = dse.results2
 
# ── Colours (as RGB tuples) ────────────────────────────────────────────────────
COL_GREEN   = RGBColor(0x10, 0xB9, 0x81)
COL_YELLOW  = RGBColor(0xF5, 0x9E, 0x0B)
COL_ORANGE  = RGBColor(0xF9, 0x73, 0x16)
COL_RED     = RGBColor(0xEF, 0x44, 0x44)
COL_GREY    = RGBColor(0xCB, 0xD5, 0xE1)
COL_BLUE    = RGBColor(0x37, 0x80, 0xFF)
COL_PURPLE  = RGBColor(0x8B, 0x5C, 0xF6)
COL_TEXT    = RGBColor(0x1E, 0x29, 0x3B)
COL_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
COL_BG      = RGBColor(0xF0, 0xF4, 0xF8)
 
# ── XML namespace helpers ─────────────────────────────────────────────────────
C_NS = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
ct   = lambda tag: f'{{{C_NS}}}{tag}'
at   = lambda tag: f'{{{A_NS}}}{tag}'
 
def rgb_hex(r):
    return f'{r[0]:02X}{r[1]:02X}{r[2]:02X}'
 
def set_bar_color(series, color):
    """Set a single series' bar fill colour via python-pptx API."""
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = color
 
def eff_color(eff):
    """Green → yellow → orange → red based on efficiency."""
    if eff >= 96:  return COL_GREEN
    if eff >= 93:  return COL_YELLOW
    if eff >= 90:  return COL_ORANGE
    return COL_RED
 
def add_title(chart, text, size_pt=12):
    chart.has_title = True
    chart.chart_title.text_frame.text = text
    r = chart.chart_title.text_frame.paragraphs[0].runs[0]
    r.font.bold = True
    r.font.size = Pt(size_pt)
    r.font.color.rgb = COL_TEXT
 
def style_cat_axis(axis):
    axis.tick_labels.font.bold = True
    axis.tick_labels.font.size = Pt(9)
 
def style_val_axis(axis, title_text, min_val=None, max_val=None):
    axis.has_title = True
    axis.axis_title.text_frame.text = title_text
    for r in axis.axis_title.text_frame.paragraphs[0].runs:
        r.font.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = COL_TEXT
    axis.tick_labels.font.bold = True
    axis.tick_labels.font.size = Pt(9)
    if min_val is not None:
        axis.minimum_scale = min_val
    if max_val is not None:
        axis.maximum_scale = max_val
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  BUILD ONE SLIDE FOR ONE DSE CASE
# ═══════════════════════════════════════════════════════════════════════════════
def build_slide(prs, results, slide_title):
    """Add one slide with two native horizontal bar charts."""
 
    # Sort: feasible by eff desc, then infeasible
    feasible   = sorted([r for r in results if r.feasible],
                        key=lambda r: r.eff, reverse=True)
    infeasible = [r for r in results if not r.feasible]
    ordered    = feasible + infeasible
 
    labels = [f"N={r.arch.N}, K={r.arch.K}" for r in ordered]
 
    # ── Efficiency data ───────────────────────────────────────────────────────
    eff_vals  = [round(r.eff,  1) if r.feasible else 0.0 for r in ordered]
    loss_vals = [round(r.loss, 3) if r.feasible else 0.0 for r in ordered]
 
    # ── Ripple data (normalised to limit, %) ──────────────────────────────────
    DI_LIM, DV_LIM = 40.0, 5.0
    di_util = [round(r.di_pct / DI_LIM * 100, 1) if r.feasible else 0 for r in ordered]
    dv_util = [round(r.dv_pct / DV_LIM * 100, 1) if r.feasible else 0 for r in ordered]
 
    # ── Blank slide ───────────────────────────────────────────────────────────
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = COL_BG
 
    # Slide title text box
    txb = slide.shapes.add_textbox(Inches(0.3), Inches(0.08),
                                   Inches(12.7), Inches(0.45))
    tf = txb.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.text = slide_title
    p.runs[0].font.bold  = True
    p.runs[0].font.size  = Pt(14)
    p.runs[0].font.color.rgb = COL_TEXT
 
    # Sub-title
    txb2 = slide.shapes.add_textbox(Inches(0.3), Inches(0.50),
                                    Inches(12.7), Inches(0.30))
    tf2 = txb2.text_frame
    tf2.paragraphs[0].text = (
        "System: Vin=48V, Vout=1V, Iout=20A  |  "
        "Target J = 1 A/mm²  |  Ripple: ΔI<40%, ΔV<5%  |  "
        "★ = Optimal topology"
    )
    tf2.paragraphs[0].runs[0].font.size  = Pt(8.5)
    tf2.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    tf2.paragraphs[0].runs[0].font.bold  = False
 
    # ── CHART 1: Efficiency ───────────────────────────────────────────────────
    cd1 = ChartData()
    cd1.categories = labels
    cd1.add_series('Efficiency (%)', eff_vals)
 
    cf1 = slide.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED,
        Inches(0.20), Inches(0.85),
        Inches(8.10), Inches(6.45),
        cd1,
    )
    ch1 = cf1.chart
 
    add_title(ch1, 'Efficiency (%) & Loss (W) per Topology')
 
    # Colour each bar individually based on efficiency
    # python-pptx doesn't support per-point colouring via API directly,
    # so we do it via XML on the data point elements
    ser_elem = ch1._element.findall(f'.//{ct("ser")}')[0]
    dpts = ser_elem.findall(ct('dPt'))
    # If no dPt exist yet, create them
    for idx, r in enumerate(ordered):
        col = eff_color(r.eff) if r.feasible else COL_GREY
        hex_col = f'{col[0]:02X}{col[1]:02X}{col[2]:02X}'
        dpt_xml = (
            f'<c:dPt xmlns:c="{C_NS}" xmlns:a="{A_NS}">'
            f'  <c:idx val="{idx}"/>'
            f'  <c:invertIfNegative val="0"/>'
            f'  <c:spPr>'
            f'    <a:solidFill><a:srgbClr val="{hex_col}"/></a:solidFill>'
            f'    <a:ln><a:noFill/></a:ln>'
            f'  </c:spPr>'
            f'</c:dPt>'
        )
        ser_elem.insert(2 + idx, etree.fromstring(dpt_xml))
 
    # Axes
    style_val_axis(ch1.value_axis, 'Efficiency (%)', min_val=80, max_val=100)
    style_cat_axis(ch1.category_axis)
    ch1.category_axis.tick_labels.font.size = Pt(9)
    ch1.value_axis.tick_labels.font.size    = Pt(9)
 
    # Plot area background white
    pa = ch1._element.find(f'.//{ct("plotArea")}')
    sppr_xml = (
        f'<c:spPr xmlns:c="{C_NS}" xmlns:a="{A_NS}">'
        f'  <a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>'
        f'  <a:ln><a:solidFill><a:srgbClr val="CBD5E1"/>'
        f'  </a:solidFill></a:ln>'
        f'</c:spPr>'
    )
    existing = pa.find(ct('spPr'))
    if existing is not None:
        pa.remove(existing)
    pa.append(etree.fromstring(sppr_xml))
 
    ch1.has_legend = False
 
    # Data labels — show value
    dLbls_xml = (
        f'<c:dLbls xmlns:c="{C_NS}" xmlns:a="{A_NS}">'
        f'  <c:numFmt formatCode="0.0&quot;%&quot;" sourceLinked="0"/>'
        f'  <c:spPr><a:noFill/></c:spPr>'
        f'  <c:txPr><a:bodyPr/><a:lstStyle/>'
        f'  <a:p><a:pPr><a:defRPr b="1" sz="800"/></a:pPr></a:p>'
        f'  </c:txPr>'
        f'  <c:showLegendKey val="0"/>'
        f'  <c:showVal val="1"/>'
        f'  <c:showCatName val="0"/>'
        f'  <c:showSerName val="0"/>'
        f'  <c:showPercent val="0"/>'
        f'  <c:showBubbleSize val="0"/>'
        f'  <c:dLblPos val="outEnd"/>'
        f'</c:dLbls>'
    )
    ser_elem.append(etree.fromstring(dLbls_xml))
 
    # ── CHART 2: Ripple utilisation ───────────────────────────────────────────
    cd2 = ChartData()
    cd2.categories = labels
    cd2.add_series('ΔI Utilisation (% of limit)', di_util)
    cd2.add_series('ΔV Utilisation (% of limit)', dv_util)
 
    cf2 = slide.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED,
        Inches(8.50), Inches(0.85),
        Inches(4.65), Inches(6.45),
        cd2,
    )
    ch2 = cf2.chart
 
    add_title(ch2, 'Ripple Budget Utilisation\n(100% = at limit)')
 
    # ΔI series — blue
    ch2.series[0].format.fill.solid()
    ch2.series[0].format.fill.fore_color.rgb = RGBColor(0x37, 0x80, 0xFF)
 
    # ΔV series — purple
    ch2.series[1].format.fill.solid()
    ch2.series[1].format.fill.fore_color.rgb = RGBColor(0x8B, 0x5C, 0xF6)
 
    style_val_axis(ch2.value_axis, 'Budget Used (%)', min_val=0, max_val=115)
    style_cat_axis(ch2.category_axis)
    ch2.category_axis.tick_labels.font.size = Pt(9)
    ch2.value_axis.tick_labels.font.size    = Pt(9)
 
    # Legend
    ch2.has_legend = True
    ch2.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch2.legend.include_in_layout = False
 
    # Add 100% reference line via XML (series + secondary axis trick)
    # Simplest reliable approach: add a constant series at 100 as a line
    bc2  = ch2._element.find(f'.//{ct("barChart")}')
    ax_elems = bc2.findall(ct('axId'))
    cat_id   = ax_elems[0].get('val')
    pri_id   = ax_elems[1].get('val')
 
    # Build constant-100 series data
    n = len(labels)
    num_cache = ''.join(
        f'<c:pt idx="{i}"><c:v>100</c:v></c:pt>' for i in range(n)
    )
    limit_ser_xml = (
        f'<c:ser xmlns:c="{C_NS}" xmlns:a="{A_NS}">'
        f'  <c:idx val="2"/>'
        f'  <c:order val="2"/>'
        f'  <c:tx><c:strRef><c:f></c:f>'
        f'    <c:strCache><c:ptCount val="1"/>'
        f'    <c:pt idx="0"><c:v>Constraint (100%)</c:v></c:pt>'
        f'    </c:strCache></c:strRef></c:tx>'
        f'  <c:spPr>'
        f'    <a:noFill/>'
        f'    <a:ln w="19050">'
        f'      <a:solidFill><a:srgbClr val="EF4444"/></a:solidFill>'
        f'      <a:prstDash val="dash"/>'
        f'    </a:ln>'
        f'  </c:spPr>'
        f'  <c:marker><c:symbol val="none"/></c:marker>'
        f'  <c:val><c:numRef><c:f></c:f>'
        f'    <c:numCache><c:formatCode>General</c:formatCode>'
        f'    <c:ptCount val="{n}"/>'
        f'    {num_cache}'
        f'    </c:numCache></c:numRef></c:val>'
        f'  <c:smooth val="0"/>'
        f'</c:ser>'
    )
 
    # Add a lineChart with the constraint series
    lc_xml = (
        f'<c:lineChart xmlns:c="{C_NS}">'
        f'  <c:grouping val="standard"/>'
        f'  <c:varyColors val="0"/>'
        f'  {limit_ser_xml}'
        f'  <c:smooth val="0"/>'
        f'  <c:axId val="{cat_id}"/>'
        f'  <c:axId val="{pri_id}"/>'
        f'</c:lineChart>'
    )
    pa2 = ch2._element.find(f'.//{ct("plotArea")}')
    pa2.insert(list(pa2).index(bc2) + 1, etree.fromstring(lc_xml))
 
    # ── Optimal design annotation box ─────────────────────────────────────────
    if feasible:
        b = feasible[0]
        note = (f"★ Optimal: N={b.arch.N}, K={b.arch.K}\n"
                f"HS: {b.hs}   LS: {b.ls}\n"
                f"L = {b.L*1e9:.0f} nH   fsw = {b.f_sw/1e6:.2f} MHz\n"
                f"Area = {b.area:.1f} mm²   "
                f"η = {b.eff:.1f}%   Loss = {b.loss:.3f} W")
        txb3 = slide.shapes.add_textbox(
            Inches(0.22), Inches(7.05), Inches(8.0), Inches(0.40))
        tf3 = txb3.text_frame
        tf3.paragraphs[0].text = note
        tf3.paragraphs[0].runs[0].font.bold  = True
        tf3.paragraphs[0].runs[0].font.size  = Pt(8.5)
        tf3.paragraphs[0].runs[0].font.color.rgb = COL_TEXT
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)
 
build_slide(prs, results1,
            "Case 1: Planar Integration — No Vertical Stacking  |  48V→1V, 20A, ≤20 mm²")
build_slide(prs, results2,
            "Case 2: 3D Vertical Stacking (Embedded Package)  |  48V→1V, 20A, ≤20 mm²")
 
prs.save('dse_native.pptx')
print("Saved: dse_native.pptx")
