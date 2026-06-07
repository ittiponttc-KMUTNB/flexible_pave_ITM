"""
flex_word_report.py — Word Report (ฉบับเต็ม) สำหรับ Flexible Pavement Design
AASHTO 1993 · ภาควิชาครุศาสตร์โยธา มจพ.

ใช้ python-docx + pythainlp (Zero-Width Space) ตาม thai-docx skill
Font: TH SarabunPSK 15pt · Alignment: LEFT เท่านั้น
"""

from io import BytesIO
from datetime import datetime

from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

try:
    from pythainlp.tokenize import word_tokenize as _wt
    def _zwsp(text: str) -> str:
        """แทรก Zero-Width Space ระหว่างคำไทย"""
        if not text:
            return text
        tokens = _wt(str(text), engine='newmm', keep_whitespace=True)
        return '\u200b'.join(tokens)
except ImportError:
    def _zwsp(text: str) -> str:
        return str(text)

# ── Constants ──────────────────────────────────────────────
FONT_TH   = 'TH SarabunPSK'
FONT_EQ   = 'Times New Roman'
FS_TITLE  = 20
FS_H1     = 18
FS_H2     = 16
FS_BODY   = 15
FS_EQ     = 11
FS_TABLE  = 14
HDR_COLOR = 'BDD7EE'   # สีฟ้าอ่อน header ตาราง
PASS_RGB  = RGBColor(0x00, 0x70, 0x00)
FAIL_RGB  = RGBColor(0xC0, 0x00, 0x00)

# ============================================================
# Helper — Font / Cell
# ============================================================

def _set_thai(run, size=FS_BODY, bold=False, color_rgb=None):
    run.font.name = FONT_TH
    run.font.size = Pt(size)
    run.bold      = bold
    try:
        run._element.rPr.rFonts.set(
            '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}cs',
            FONT_TH)
    except Exception:
        pass
    if color_rgb:
        run.font.color.rgb = color_rgb


def _set_eq(run, size=FS_EQ, bold=False, italic=True):
    run.font.name   = FONT_EQ
    run.font.size   = Pt(size)
    run.bold        = bold
    run.italic      = italic


def _add_para(doc, text, size=FS_BODY, bold=False,
              align=WD_ALIGN_PARAGRAPH.LEFT, color_rgb=None, indent_cm=0):
    para = doc.add_paragraph()
    para.alignment = align
    if indent_cm:
        para.paragraph_format.first_line_indent = Cm(indent_cm)
    run = para.add_run(_zwsp(str(text)))
    _set_thai(run, size, bold, color_rgb)
    return para


def _add_eq(doc, text, size=FS_EQ, bold=False, italic=True):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run(str(text))
    _set_eq(run, size, bold, italic)
    return para


def _hdr_shade(cell, fill=HDR_COLOR):
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  fill)
    cell._tc.get_or_add_tcPr().append(shd)


def _cell_text(cell, text, size=FS_TABLE, bold=False,
               align=WD_ALIGN_PARAGRAPH.LEFT, color_rgb=None):
    cell.text = ''
    para = cell.paragraphs[0]
    para.alignment = align
    run  = para.add_run(_zwsp(str(text)))
    _set_thai(run, size, bold, color_rgb)
    return run


def _add_hdr(doc, text, level=2):
    """เพิ่ม heading ด้วย TH SarabunPSK"""
    h = doc.add_heading('', level=level)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = h.add_run(_zwsp(text))
    size = {0: FS_TITLE, 1: FS_H1, 2: FS_H2}.get(level, FS_H2)
    _set_thai(run, size, bold=True)
    return h


def _short_mat(name: str) -> str:
    """ตัดคำนำหน้าที่ยาวออก"""
    for prefix in ['ผิวทางลาดยาง ', 'พื้นทาง', 'รองพื้นทาง']:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


# ============================================================
# Main Report Generator
# ============================================================

def create_flex_word_report(
    project_name: str,
    designer: str,
    W18: float,
    sn_used: float,
    reliability: int,
    Zr: float,
    So: float,
    p0: float,
    pt: float,
    cbr: float,
    mr_sub: float,
    calc_results: dict,
    design_check: dict,
    fig=None,
) -> BytesIO:
    """
    สร้าง Word Report ฉบับเต็ม 8 sections
    return: BytesIO ของ .docx
    """
    doc = Document()

    # ── Page setup A4 ──────────────────────────────────────
    sec = doc.sections[0]
    sec.page_width    = Cm(21.0)
    sec.page_height   = Cm(29.7)
    sec.left_margin   = Cm(2.5)
    sec.right_margin  = Cm(2.0)
    sec.top_margin    = Cm(2.5)
    sec.bottom_margin = Cm(2.0)

    # ── Normal style ──────────────────────────────────────
    doc.styles['Normal'].font.name = FONT_TH
    doc.styles['Normal'].font.size = Pt(FS_BODY)

    date_str   = datetime.now().strftime('%d/%m/%Y')
    delta_psi  = round(p0 - pt, 1)
    sn_req     = calc_results.get('total_sn_required') or 0.0
    sn_prov    = calc_results.get('total_sn_provided', 0.0)
    passed     = design_check.get('passed', False)
    ratio      = round(sn_prov / sn_req, 3) if sn_req > 0 else 0.0

    # ── Title ──────────────────────────────────────────────
    _add_hdr(doc, 'รายงานการออกแบบ Flexible Pavement', level=0)
    _add_para(doc, f'โครงการ: {project_name or "—"}', size=FS_H2, bold=True)
    _add_para(doc, f'ผู้ออกแบบ: {designer or "—"}   วันที่: {date_str}', size=FS_BODY)
    doc.add_paragraph()

    # ══════════════════════════════════════════════════════
    # 1. วิธีการออกแบบ
    # ══════════════════════════════════════════════════════
    _add_hdr(doc, '1. วิธีการออกแบบ', level=2)
    _add_para(doc,
        'การออกแบบโครงสร้างถนนใช้วิธี AASHTO 1993 Guide for Design of Pavement Structures '
        'ตามมาตรฐานกรมทางหลวง โดยใช้สมการหลักดังนี้:', indent_cm=1.25)
    _add_eq(doc,
        'log\u2081\u2080(W\u2081\u2088) = Z\u1d63\u00b7S\u2080 + 9.36\u00b7log\u2081\u2080(SN+1) \u2212 0.20 '
        '+ log\u2081\u2080(\u0394PSI/2.7) / [0.4 + 1094/(SN+1)\u2075\u00b7\u00b9\u2079] '
        '+ 2.32\u00b7log\u2081\u2080(M\u1d63) \u2212 8.07',
        size=FS_EQ, italic=True)
    doc.add_paragraph()

    # ══════════════════════════════════════════════════════
    # 2. ข้อมูลนำเข้า
    # ══════════════════════════════════════════════════════
    _add_hdr(doc, '2. ข้อมูลนำเข้า (Design Inputs)', level=2)

    input_rows = [
        ('Design ESALs (W\u2081\u2088)',       f'{W18:,.0f}',    '18-kip ESAL'),
        (f'Structural Number (SN ที่ใช้)',     f'{sn_used:.1f}', '\u2014'),
        ('Reliability (R)',                    f'{reliability}',  '%'),
        ('Z\u1d63',                            f'{Zr:.3f}',       '\u2014'),
        ('S\u2080',                            f'{So:.2f}',       '\u2014'),
        ('P\u2080',                            f'{p0:.1f}',       '\u2014'),
        ('P\u209c',                            f'{pt:.1f}',       '\u2014'),
        ('\u0394PSI',                          f'{delta_psi:.1f}','\u2014'),
        ('CBR ดินเดิม',                       f'{cbr:.1f}',      '%'),
        ('M\u1d63 = 1,500\u00d7CBR',          f'{mr_sub:,.0f}',  'psi'),
    ]
    t_input = doc.add_table(rows=1, cols=3)
    t_input.style = 'Table Grid'
    t_input.alignment = WD_TABLE_ALIGNMENT.LEFT
    for j, h in enumerate(['พารามิเตอร์', 'ค่า', 'หน่วย']):
        _cell_text(t_input.rows[0].cells[j], h, bold=True,
                   align=WD_ALIGN_PARAGRAPH.CENTER)
        _hdr_shade(t_input.rows[0].cells[j])
    for param, val, unit in input_rows:
        row = t_input.add_row()
        _cell_text(row.cells[0], param)
        _cell_text(row.cells[1], val,  align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[2], unit, align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    # ══════════════════════════════════════════════════════
    # 3. คุณสมบัติวัสดุชั้นทาง
    # ══════════════════════════════════════════════════════
    _add_hdr(doc, '3. คุณสมบัติวัสดุชั้นทาง', level=2)
    t_mat = doc.add_table(rows=1, cols=6)
    t_mat.style = 'Table Grid'
    t_mat.alignment = WD_TABLE_ALIGNMENT.LEFT
    for j, h in enumerate(['ชั้น', 'วัสดุ', 'a\u1d62', 'm\u1d62', 'M\u1d63 (psi)', 'M\u1d63 (MPa)']):
        _cell_text(t_mat.rows[0].cells[j], h, bold=True,
                   align=WD_ALIGN_PARAGRAPH.CENTER)
        _hdr_shade(t_mat.rows[0].cells[j])
    for L in calc_results.get('layers', []):
        row = t_mat.add_row()
        _cell_text(row.cells[0], str(L['layer_no']),     align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[1], _short_mat(L['material']))
        _cell_text(row.cells[2], f'{L["a_i"]:.2f}',     align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[3], f'{L["m_i"]:.2f}',     align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[4], f'{L["mr_psi"]:,}',    align=WD_ALIGN_PARAGRAPH.RIGHT)
        _cell_text(row.cells[5], f'{L["mr_mpa"]:,}',    align=WD_ALIGN_PARAGRAPH.RIGHT)

    # AC Sublayer
    for L in calc_results.get('layers', []):
        ac_sub = L.get('ac_sublayers') or L.get('ac_sub')
        if ac_sub and isinstance(ac_sub, dict):
            doc.add_paragraph()
            _add_para(doc, 'รายละเอียดชั้นย่อยผิวทาง AC:', bold=True)
            t_sub = doc.add_table(rows=1, cols=3)
            t_sub.style = 'Table Grid'
            for j, h in enumerate(['ชั้นย่อย', 'ความหนา (cm)', 'ความหนา (mm)']):
                _cell_text(t_sub.rows[0].cells[j], h, bold=True,
                           align=WD_ALIGN_PARAGRAPH.CENTER)
                _hdr_shade(t_sub.rows[0].cells[j])
            for label, key in [
                ('ผิวทาง Wearing Course', 'wearing_cm'),
                ('รองผิวทาง Binder Course', 'binder_cm'),
                ('พื้นทาง Base Course', 'base_cm'),
            ]:
                t_cm = ac_sub.get(key, 0)
                row  = t_sub.add_row()
                _cell_text(row.cells[0], label)
                _cell_text(row.cells[1], f'{t_cm:.1f}', align=WD_ALIGN_PARAGRAPH.CENTER)
                _cell_text(row.cells[2], f'{t_cm*10:.0f}', align=WD_ALIGN_PARAGRAPH.CENTER)
            break
    doc.add_paragraph()

    # ══════════════════════════════════════════════════════
    # 4. การคำนวณความหนาแต่ละชั้น
    # ══════════════════════════════════════════════════════
    _add_hdr(doc, '4. การคำนวณความหนาแต่ละชั้น', level=2)

    for L in calc_results.get('layers', []):
        ln       = L['layer_no']
        a_i      = L['a_i']
        m_i      = L['m_i']
        d_in     = L['design_thickness_inch']
        d_cm     = L['design_thickness_cm']
        sn_at    = L['sn_required_at_layer']
        d_min_cm = L['min_thickness_cm']
        sn_cont  = L['sn_contribution']
        sn_cum   = L['cumulative_sn']
        is_ok    = L['is_ok']

        doc.add_paragraph()
        _add_para(doc, f'ชั้นที่ {ln}: {_short_mat(L["material"])}',
                  bold=True, indent_cm=0)
        _add_para(doc,
            f'  \u2022 M\u1d63 = {L["mr_psi"]:,} psi = {L["mr_mpa"]:,} MPa\n'
            f'  \u2022 a\u208b{ln} = {a_i:.2f}   m\u208b{ln} = {m_i:.2f}')

        _add_para(doc, 'SN ที่ต้องการ (จากสมการ AASHTO 1993):', bold=True)
        _add_eq(doc, f'SN\u208b{ln}  =  {sn_at:.3f}', size=FS_EQ, bold=True)

        _add_para(doc, 'ความหนาขั้นต่ำ:', bold=True)
        if ln == 1:
            _add_eq(doc, f'D\u208b1 \u2265 SN\u208b1 / (a\u208b1 \u00d7 m\u208b1)', size=FS_EQ)
        else:
            _add_eq(doc,
                f'D\u208b{ln} \u2265 (SN\u208b{ln} \u2212 SN\u208b{ln-1}) / (a\u208b{ln} \u00d7 m\u208b{ln})',
                size=FS_EQ)
        _add_eq(doc,
            f'D\u208b{ln}(min)  =  {d_min_cm:.1f} cm' if d_min_cm > 0 else 'D\u208b{ln}(min)  =  \u2014',
            size=FS_EQ)

        _add_para(doc, 'ความหนาที่เลือกใช้:', bold=True)
        _add_eq(doc, f'D\u208b{ln}(design)  =  {d_cm:.0f} cm  ({d_in:.3f} in)',
                size=FS_EQ, bold=True, italic=False)

        _add_para(doc, 'SN Contribution:', bold=True)
        _add_eq(doc,
            f'\u0394SN\u208b{ln} = a\u208b{ln} \u00d7 D\u208b{ln} \u00d7 m\u208b{ln}'
            f'  =  {a_i:.2f} \u00d7 {d_in:.3f} \u00d7 {m_i:.2f}  =  {sn_cont:.3f}',
            size=FS_EQ)
        _add_eq(doc, f'\u03a3SN  =  {sn_cum:.3f}', size=FS_EQ, bold=True, italic=False)

        status_txt = ('OK \u2014 ความหนาเพียงพอ' if is_ok
                      else f'NG \u2014 ต้องเพิ่มอีก {d_min_cm - d_cm:.1f} cm')
        color = PASS_RGB if is_ok else FAIL_RGB
        p_st  = doc.add_paragraph()
        p_st.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_st  = p_st.add_run(f'สถานะ: {status_txt}')
        _set_thai(r_st, size=FS_EQ, bold=True, color_rgb=color)

    doc.add_paragraph()

    # ══════════════════════════════════════════════════════
    # 5. ตารางสรุป SN
    # ══════════════════════════════════════════════════════
    _add_hdr(doc, '5. ตารางสรุปการคำนวณ Structural Number', level=2)
    t_sn = doc.add_table(rows=1, cols=8)
    t_sn.style = 'Table Grid'
    t_sn.alignment = WD_TABLE_ALIGNMENT.LEFT
    for j, h in enumerate(['ชั้น', 'วัสดุ', 'a\u1d62', 'm\u1d62',
                            'D\u1d62 (นิ้ว)', 'D\u1d62 (ซม.)', '\u0394SN\u1d62', '\u03a3SN']):
        _cell_text(t_sn.rows[0].cells[j], h, bold=True,
                   align=WD_ALIGN_PARAGRAPH.CENTER)
        _hdr_shade(t_sn.rows[0].cells[j])
    for L in calc_results.get('layers', []):
        row = t_sn.add_row()
        _cell_text(row.cells[0], str(L['layer_no']),                    align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[1], _short_mat(L['material']))
        _cell_text(row.cells[2], f'{L["a_i"]:.2f}',                    align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[3], f'{L["m_i"]:.2f}',                    align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[4], f'{L["design_thickness_inch"]:.3f}',  align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[5], f'{L["design_thickness_cm"]:.0f}',    align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[6], f'{L["sn_contribution"]:.3f}',        align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[7], f'{L["cumulative_sn"]:.3f}',          align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    # ══════════════════════════════════════════════════════
    # 6. ผลการตรวจสอบ
    # ══════════════════════════════════════════════════════
    _add_hdr(doc, '6. ผลการตรวจสอบการออกแบบ', level=2)
    result_data = [
        ('SN Required (จากสมการ AASHTO)', f'{sn_req:.3f}'),
        ('SN Provided (จากชั้นทาง)',       f'{sn_prov:.3f}'),
        ('Ratio (SN_provided / SN_required)', f'{ratio:.3f}'),
        ('ผลการตรวจสอบ', 'ผ่าน (OK)' if passed else 'ไม่ผ่าน (NG)'),
    ]
    t_res = doc.add_table(rows=len(result_data), cols=2)
    t_res.style = 'Table Grid'
    t_res.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, (param, val) in enumerate(result_data):
        is_last = (i == len(result_data) - 1)
        color   = (PASS_RGB if passed else FAIL_RGB) if is_last else None
        _cell_text(t_res.rows[i].cells[0], param, bold=is_last)
        _cell_text(t_res.rows[i].cells[1], val,
                   align=WD_ALIGN_PARAGRAPH.CENTER,
                   bold=is_last, color_rgb=color)
        if is_last:
            _hdr_shade(t_res.rows[i].cells[0],
                       fill='C6EFCE' if passed else 'FFC7CE')
            _hdr_shade(t_res.rows[i].cells[1],
                       fill='C6EFCE' if passed else 'FFC7CE')
    doc.add_paragraph()

    summary = (
        f'สรุป: การออกแบบผ่านเกณฑ์ เนื่องจาก SN_provided ({sn_prov:.3f}) '
        f'\u2265 SN_required ({sn_req:.3f})'
        if passed else
        f'สรุป: การออกแบบไม่ผ่านเกณฑ์ เนื่องจาก SN_provided ({sn_prov:.3f}) '
        f'< SN_required ({sn_req:.3f}) กรุณาปรับเพิ่มความหนาชั้นทาง'
    )
    p_sum = _add_para(doc, summary, bold=True,
                      color_rgb=PASS_RGB if passed else FAIL_RGB)
    doc.add_paragraph()

    # ══════════════════════════════════════════════════════
    # 7. รูปตัดขวาง
    # ══════════════════════════════════════════════════════
    _add_hdr(doc, '7. รูปตัดขวางโครงสร้างถนน', level=2)
    if fig is not None:
        try:
            import matplotlib.pyplot as plt
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=150,
                        bbox_inches='tight', facecolor='white')
            buf.seek(0)
            doc.add_picture(buf, width=Inches(5.5))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            plt.close(fig)
        except Exception as e:
            _add_para(doc, f'[ไม่สามารถแทรกรูปได้: {e}]')
    else:
        _add_para(doc, '[ไม่มีรูปตัดขวาง — กรุณาออกแบบชั้นทางใน Tab 2 ก่อน]')
    doc.add_paragraph()

    # ══════════════════════════════════════════════════════
    # 8. สรุปโครงสร้างชั้นทาง
    # ══════════════════════════════════════════════════════
    _add_hdr(doc, '8. สรุปโครงสร้างชั้นทางที่ออกแบบ', level=2)
    total_d = sum(L['design_thickness_cm'] for L in calc_results.get('layers', []))
    t_sum = doc.add_table(rows=1, cols=4)
    t_sum.style = 'Table Grid'
    t_sum.alignment = WD_TABLE_ALIGNMENT.LEFT
    for j, h in enumerate(['ชั้น', 'วัสดุ', 'ความหนา (cm)', 'ความหนา (mm)']):
        _cell_text(t_sum.rows[0].cells[j], h, bold=True,
                   align=WD_ALIGN_PARAGRAPH.CENTER)
        _hdr_shade(t_sum.rows[0].cells[j])
    for L in calc_results.get('layers', []):
        d = L['design_thickness_cm']
        row = t_sum.add_row()
        _cell_text(row.cells[0], str(L['layer_no']),    align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[1], _short_mat(L['material']))
        _cell_text(row.cells[2], f'{d:.0f}',            align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell_text(row.cells[3], f'{d*10:.0f}',         align=WD_ALIGN_PARAGRAPH.CENTER)
    # footer รวม
    foot = t_sum.add_row()
    _cell_text(foot.cells[0], 'รวม', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _cell_text(foot.cells[1], '', bold=True)
    _cell_text(foot.cells[2], f'{total_d:.0f}', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _cell_text(foot.cells[3], f'{total_d*10:.0f}', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for j in range(4):
        _hdr_shade(foot.cells[j], fill='C6EFCE' if passed else 'FFF2CC')

    doc.add_paragraph()

    # ── Footer ─────────────────────────────────────────────
    _add_para(doc,
        'พัฒนาโดย รศ.ดร.อิทธิพล มีผล · ภาควิชาครุศาสตร์โยธา · มจพ. · '
        'Flexible Pavement Design V1 · AASHTO 1993',
        size=12, align=WD_ALIGN_PARAGRAPH.CENTER)

    # ── Save ───────────────────────────────────────────────
    buf_out = BytesIO()
    doc.save(buf_out)
    buf_out.seek(0)
    return buf_out
