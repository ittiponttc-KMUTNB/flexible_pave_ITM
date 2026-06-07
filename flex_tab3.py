"""
flex_tab3.py — Tab 3: PDF Report (1 หน้า A4)
Flexible Pavement Design V1 · AASHTO 1993
ใช้ reportlab สร้าง PDF รองรับภาษาไทย (Sarabun font)
"""
import streamlit as st
import os
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from flex_engine import (
    mr_from_cbr, get_zr, MATERIALS,
)

_AC_BD  = '#BF360C'
_AC_BDL = '#FFAB91'

# ============================================================
# Font Setup
# ============================================================
_FONT_DIR = os.path.dirname(os.path.abspath(__file__))
_FONT_REG  = os.path.join(_FONT_DIR, 'Sarabun-Regular.ttf')
_FONT_BOLD = os.path.join(_FONT_DIR, 'Sarabun-Bold.ttf')

def _register_fonts():
    try:
        if 'Sarabun' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('Sarabun',     _FONT_REG))
            pdfmetrics.registerFont(TTFont('Sarabun-Bold', _FONT_BOLD))
        return True
    except Exception:
        return False

# ============================================================
# Color helpers
# ============================================================
_RED    = colors.HexColor('#BF360C')
_DKRED  = colors.HexColor('#7B1D00')
_GREEN  = colors.HexColor('#1B5E20')
_LTGRN  = colors.HexColor('#E8F5E9')
_LTRED  = colors.HexColor('#FFEBEE')
_LTBLU  = colors.HexColor('#E3F2FD')
_LTYLW  = colors.HexColor('#FFF8E1')
_GREY   = colors.HexColor('#F5F5F5')
_MDGREY = colors.HexColor('#78909C')
_BLACK  = colors.black
_WHITE  = colors.white

# ============================================================
# Mr Reference Table (fixed — วัสดุที่ต้องการแสดง)
# ============================================================
_MR_REF = [
    ('ผิวทางลาดยาง PMA',      536500, 3700,  0.400),
    ('ผิวทางลาดยาง AC',       362500, 2500,  0.400),
    ('หินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (CTB)', 174000, 1200, 0.180),
    ('หินคลุกผสมซีเมนต์ UCS 24.5 ksc', 123250, 850, 0.150),
    ('หินคลุก CBR 80%',        50750,  350,   0.130),
    ('รองพื้นทางวัสดุมวลรวม CBR 25%',  21750, 150, 0.100),
    ('วัสดุคัดเลือก ก',        14504,  100,   0.080),
]

# ============================================================
# PDF Generator
# ============================================================
def generate_pdf(
    project_name: str,
    designer: str,
    W18: float,
    sn_used: float,
    reliability: int,
    So: float,
    p0: float,
    pt: float,
    cbr: float,
    calc_results: dict,
    design_check: dict,
) -> bytes:

    has_font = _register_fonts()
    fn       = 'Sarabun'      if has_font else 'Helvetica'
    fn_bold  = 'Sarabun-Bold' if has_font else 'Helvetica-Bold'

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm,  bottomMargin=1.5*cm,
    )
    W, H = A4

    # ── Styles ──────────────────────────────────────────────
    def S(name, font=fn, size=9, leading=12, color=_BLACK,
          align='LEFT', spaceBefore=0, spaceAfter=2, bold=False):
        return ParagraphStyle(
            name, fontName=fn_bold if bold else font,
            fontSize=size, leading=leading,
            textColor=color, alignment={'LEFT':0,'CENTER':1,'RIGHT':2}[align],
            spaceBefore=spaceBefore, spaceAfter=spaceAfter)

    s_title   = S('title',   size=14, leading=18, bold=True,  color=_RED,   align='LEFT')
    s_sub     = S('sub',     size=8,  leading=11, color=_MDGREY)
    s_proj    = S('proj',    size=9,  leading=12, bold=True)
    s_meta    = S('meta',    size=8,  leading=11, color=_MDGREY, align='RIGHT')
    s_sec     = S('sec',     size=8,  leading=11, bold=True, color=_MDGREY,
                  spaceBefore=6, spaceAfter=2)
    s_cell    = S('cell',    size=8,  leading=11)
    s_cellb   = S('cellb',   size=8,  leading=11, bold=True)
    s_cellr   = S('cellr',   size=8,  leading=11, align='RIGHT')
    s_cellbr  = S('cellbr',  size=8,  leading=11, bold=True,  align='RIGHT')
    s_cellc   = S('cellc',   size=8,  leading=11, align='CENTER')
    s_pass    = S('pass',    size=9,  leading=13, bold=True, color=_GREEN)
    s_fail    = S('fail',    size=9,  leading=13, bold=True, color=colors.HexColor('#C62828'))
    s_ratio   = S('ratio',   size=13, leading=16, bold=True, color=_GREEN)
    s_footer  = S('footer',  size=7,  leading=10, color=_MDGREY)
    s_footerr = S('footerr', size=7,  leading=10, color=_MDGREY, align='RIGHT')

    story = []
    mr_sub = mr_from_cbr(cbr)
    Zr     = get_zr(reliability)
    dp     = round(p0 - pt, 1)
    date_str = datetime.now().strftime('%d/%m/%Y')
    res    = calc_results
    chk    = design_check
    sn_req = res.get('total_sn_required') or 0.0
    sn_prov = res.get('total_sn_provided', 0.0)
    ratio  = round(sn_prov / sn_req, 3) if sn_req > 0 else 0.0
    passed = chk.get('passed', False)

    # ── Header ───────────────────────────────────────────────
    hdr_data = [[
        [Paragraph('Flexible Pavement Design Report', s_title),
         Paragraph('AASHTO 1993 · ภาควิชาครุศาสตร์โยธา มจพ.', s_sub)],
        [Paragraph(project_name or '—', s_proj),
         Paragraph(f'ผู้ออกแบบ: {designer or "—"}', s_meta),
         Paragraph(f'วันที่: {date_str}', s_meta)],
    ]]
    hdr_tbl = Table(hdr_data, colWidths=[10.00*cm, 7.40*cm])
    hdr_tbl.setStyle(TableStyle([
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW',  (0,0), (-1,-1), 1.5, _RED),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 6))

    # ── Param + Subgrade (2 คอลัมน์) ────────────────────────
    def kv_rows(pairs):
        rows = []
        for k, v in pairs:
            rows.append([Paragraph(k, s_cell), Paragraph(str(v), s_cellbr)])
        return rows

    param_pairs = [
        ('W\u2081\u2088 (ESALs) — SN ที่ใช้', f'{W18:,.0f}  (SN {sn_used:.1f})'),
        ('Reliability (R)', f'{reliability}%'),
        ('Zr', f'{Zr:.3f}'),
        ('Overall Std Dev (S\u2080)', f'{So:.2f}'),
        ('P\u2080 / Pt', f'{p0:.1f} / {pt:.1f}'),
        ('ΔPSI', f'{dp:.1f}'),
    ]
    sub_pairs = [
        ('CBR', f'{cbr:.1f}%'),
        ('Mr (psi)', f'{mr_sub:,.0f}'),
        ('Mr (MPa)', f'{mr_sub*0.006895:.1f}'),
        ('SN_required (รวม)', f'{sn_req:.2f}'),
        ('SN_provided (รวม)', f'{sn_prov:.2f}'),
    ]

    def mini_table(pairs, bg, col_widths=None):
        rows = kv_rows(pairs)
        t = Table(rows, colWidths=col_widths or [4.50*cm, 3.50*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg),
            ('FONTNAME',   (0,0), (-1,-1), fn),
            ('FONTSIZE',   (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LINEBELOW', (0,0), (-1,-2), 0.3,
             colors.HexColor('#E0E0E0')),
            ('ROUNDEDCORNERS', [4]),
        ]))
        return t

    p_tbl = mini_table(param_pairs, _LTYLW, [5.20*cm, 2.80*cm])
    s_tbl = mini_table(sub_pairs,   _LTBLU, [6.00*cm, 3.40*cm])

    def sec_label(text):
        return Paragraph(text, s_sec)

    two_col = Table(
        [[sec_label('พารามิเตอร์การออกแบบ'), sec_label('Subgrade')],
         [p_tbl, s_tbl]],
        colWidths=[8.00*cm, 9.40*cm])
    two_col.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (1,0), (1,-1), 12),
        ('RIGHTPADDING', (0,0), (0,-1), 12),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 8))

    # ── Layer Table ──────────────────────────────────────────
    story.append(sec_label('ชั้นทาง'))

    def p(text, style=s_cell): return Paragraph(text, style)
    def pc(text): return p(text, s_cellc)
    def pr(text): return p(text, s_cellr)

    # usable width = A4 - margins = 17.40 cm
    _UW = 17.40*cm
    col_w = [8.70*cm, 1.10*cm, 1.00*cm, 0.90*cm,
             1.10*cm, 1.10*cm, 1.30*cm, 1.20*cm, 1.00*cm]
    hdr_row = [
        p('วัสดุ', s_cellb),
        pc('D\n(cm)'), pc('a\u1d62'), pc('m\u1d62'),
        pc('ΔSN'), pc('ΣSN'), pc('SN_req'),
        pc('D_min\n(cm)'), pc('chk'),
    ]
    tbl_rows = [hdr_row]

    # ตัดคำนำหน้าที่ยาวออก
    def _short_mat(name):
        for prefix in ['ผิวทางลาดยาง ', 'พื้นทาง', 'รองพื้นทาง']:
            if name.startswith(prefix):
                return name[len(prefix):]
        return name

    for L in res.get('layers', []):
        mat_full = L.get('material', L.get('short_name', ''))
        mat_disp = _short_mat(mat_full)
        # ถ้า AC sublayer
        ac_sub = L.get('ac_sublayers')
        if ac_sub:
            w  = ac_sub.get('wearing_cm', 0)
            b  = ac_sub.get('binder_cm',  0)
            bc = ac_sub.get('base_cm',    0)
            mat_txt = f'{mat_disp}<br/><font size="7" color="#78909C">W {w:.0f}+B {b:.0f}+Base {bc:.0f} cm</font>'
        else:
            mat_txt = mat_disp

        dmin = L['min_thickness_cm']
        dmin_str = f"{dmin:.1f}" if dmin > 0 else '—'
        ok_p = (Paragraph('<b>OK</b>', ParagraphStyle('ok', fontName=fn_bold, fontSize=7, textColor=_GREEN, alignment=1, leading=9))
                if L['is_ok'] else
                Paragraph('<b>NG</b>', ParagraphStyle('ng', fontName=fn_bold, fontSize=7, textColor=colors.HexColor('#C62828'), alignment=1, leading=9)))

        tbl_rows.append([
            p(mat_txt, s_cell),
            pr(f"{L['design_thickness_cm']:.0f}"),
            pr(f"{L['a_i']:.2f}"),
            pr(f"{L['m_i']:.1f}"),
            pr(f"{L['sn_contribution']:.2f}"),
            pr(f"{L['cumulative_sn']:.2f}"),
            pr(f"{L['sn_required_at_layer']:.2f}"),
            pr(dmin_str),
            ok_p,
        ])

    total_d = sum(L['design_thickness_cm'] for L in res.get('layers', []))
    tbl_rows.append([
        p('รวม', s_cellb),
        pr(f'{total_d:.0f}'),
        pr(''), pr(''),
        pr(f'{sn_prov:.2f}'),
        pr(''), pr(''), pr(''), pr(''),
    ])

    layer_tbl = Table(tbl_rows, colWidths=col_w, repeatRows=1)
    n = len(tbl_rows)
    layer_tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#D84315')),
        ('TEXTCOLOR',   (0,0), (-1,0), _WHITE),
        ('FONTNAME',    (0,0), (-1,0), fn_bold),
        ('FONTSIZE',    (0,0), (-1,-1), 7),
        ('TOPPADDING',  (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
        ('LINEBELOW',   (0,1), (-1,-2), 0.3, colors.HexColor('#E0E0E0')),
        ('BACKGROUND',  (0,n-1), (-1,n-1), _GREY),
        ('FONTNAME',    (0,n-1), (-1,n-1), fn_bold),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,n-2),
         [_WHITE, colors.HexColor('#FAFAFA')]),
    ]))
    story.append(layer_tbl)
    story.append(Spacer(1, 8))

    # ── Verdict ──────────────────────────────────────────────
    v_bg   = _LTGRN if passed else _LTRED
    v_bc   = colors.HexColor('#2E7D32') if passed else colors.HexColor('#C62828')
    v_text = 'PASS — โครงสร้างผ่านการออกแบบ' if passed else 'FAIL — โครงสร้างไม่ผ่านการออกแบบ'
    v_sty  = s_pass if passed else s_fail
    r_sty  = ParagraphStyle('ratio2', fontName=fn_bold, fontSize=13,
                             textColor=v_bc, alignment=2, leading=16)

    verdict_data = [[
        [p(v_text, v_sty),
         p(f'SN_provided = {sn_prov:.2f}  ≥  SN_required = {sn_req:.2f}'
           if passed else
           f'SN_provided = {sn_prov:.2f}  <  SN_required = {sn_req:.2f}',
           s_cell)],
        p(f'Ratio = {ratio:.3f}', r_sty),
    ]]
    verdict_tbl = Table(verdict_data, colWidths=[13.10*cm, 4.30*cm])
    verdict_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), v_bg),
        ('BOX',           (0,0), (-1,-1), 1.2, v_bc),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [4]),
    ]))
    story.append(verdict_tbl)
    story.append(Spacer(1, 10))

    # ── Mr Reference Table ───────────────────────────────────
    story.append(sec_label('ตารางค่า Mr อ้างอิง (มาตรฐานกรมทางหลวง)'))

    ref_hdr = [p('วัสดุ', s_cellb),
               pc('Mr (psi)'), pc('Mr (MPa)'), pc('aᵢ')]
    ref_rows = [ref_hdr]
    for mat_name, mr_psi, mr_mpa, ai in _MR_REF:
        ref_rows.append([
            p(mat_name, s_cell),
            pr(f'{mr_psi:,}'),
            pr(f'{mr_mpa:,}'),
            pr(f'{ai:.3f}'),
        ])
    # เพิ่ม subgrade
    ref_rows.append([
        p(f'Subgrade (CBR={cbr:.1f}%)', s_cell),
        pr(f'{mr_sub:,}'),
        pr(f'{mr_sub*0.006895:.1f}'),
        pr('—'),
    ])

    ref_tbl = Table(ref_rows,
                    colWidths=[10.40*cm, 2.50*cm, 2.50*cm, 2.00*cm],
                    repeatRows=1)
    nr = len(ref_rows)
    ref_tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#78909C')),
        ('TEXTCOLOR',   (0,0), (-1,0), _WHITE),
        ('FONTNAME',    (0,0), (-1,-1), fn),
        ('FONTNAME',    (0,0), (-1,0),  fn_bold),
        ('FONTSIZE',    (0,0), (-1,-1), 7),
        ('TOPPADDING',  (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
        ('LINEBELOW',   (0,1), (-1,-2), 0.3, colors.HexColor('#E0E0E0')),
        ('BACKGROUND',  (0,nr-1),(-1,nr-1), _LTBLU),
        ('ROWBACKGROUNDS', (0,1),(-1,nr-2),
         [_WHITE, colors.HexColor('#FAFAFA')]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(ref_tbl)
    story.append(Spacer(1, 8))

    # ── Footer ───────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#E0E0E0')))
    story.append(Spacer(1, 3))
    ft_data = [[
        p('รศ.ดร.อิทธิพล มีผล · ภาควิชาครุศาสตร์โยธา · มจพ.', s_footer),
        p('Flexible Pavement Design V1 · AASHTO 1993 · หน้า 1/1', s_footerr),
    ]]
    ft_tbl = Table(ft_data, colWidths=[10.00*cm, 7.40*cm])
    ft_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(ft_tbl)

    doc.build(story)
    return buf.getvalue()


# ============================================================
# UI Helpers
# ============================================================
def _card_title(text):
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:#BF360C;'
        f'padding:2px 0 6px;border-bottom:2px solid #FFAB91;'
        f'margin-bottom:10px">{text}</div>',
        unsafe_allow_html=True)


# ============================================================
# Main Render
# ============================================================
def render_flex_tab3():

    res = st.session_state.get('flex_calc_results')
    chk = st.session_state.get('flex_design_check')

    if not res or not chk:
        st.info('⚠️ กรุณาออกแบบชั้นทางใน Tab 2 ก่อน — ผลการคำนวณจะแสดงที่นี่')
        return

    # ── Project info ─────────────────────────────────────────
    with st.container(border=True):
        _card_title('📋 ข้อมูลสำหรับรายงาน')
        c1, c2 = st.columns(2)
        with c1:
            proj = st.text_input(
                'ชื่อโครงการ',
                value=st.session_state.get('flex_project_name', ''),
                key='flex_report_project')
        with c2:
            designer = st.text_input(
                'ผู้ออกแบบ',
                value=st.session_state.get('flex_designer', ''),
                key='flex_designer',
                placeholder='เช่น รศ.ดร.อิทธิพล มีผล')

    # ── Summary ──────────────────────────────────────────────
    with st.container(border=True):
        _card_title('📊 สรุปผลการออกแบบ')
        sn_req  = res.get('total_sn_required') or 0
        sn_prov = res.get('total_sn_provided', 0)
        ratio   = round(sn_prov / sn_req, 3) if sn_req > 0 else 0
        passed  = chk.get('passed', False)

        c1, c2, c3, c4 = st.columns(4)
        def _mbox(col, lbl, val, bg, vc):
            with col:
                st.markdown(
                    f'<div style="background:{bg};border-radius:7px;'
                    f'padding:8px;text-align:center">'
                    f'<div style="font-size:10px;color:#78909C">{lbl}</div>'
                    f'<div style="font-family:IBM Plex Mono,monospace;'
                    f'font-size:18px;font-weight:700;color:{vc}">{val}</div>'
                    f'</div>', unsafe_allow_html=True)

        _mbox(c1, 'SN_required', f'{sn_req:.3f}',  '#FBE9E7', '#BF360C')
        _mbox(c2, 'SN_provided', f'{sn_prov:.3f}', '#E8F5E9', '#2E7D32')
        _mbox(c3, 'Ratio',       f'{ratio:.3f}',
              '#E8F5E9' if passed else '#FFEBEE',
              '#2E7D32' if passed else '#C62828')
        _mbox(c4, 'สถานะ',
              '✅ PASS' if passed else '❌ FAIL',
              '#E8F5E9' if passed else '#FFEBEE',
              '#2E7D32' if passed else '#C62828')

    # ── Export ───────────────────────────────────────────────
    with st.container(border=True):
        _card_title('📥 Export PDF')

        if st.button('🔄 สร้าง PDF', type='primary', use_container_width=True):
            with st.spinner('กำลังสร้าง PDF...'):
                try:
                    W18      = float(st.session_state.get('flex_w18', 0))
                    R        = int(st.session_state.get('flex_reliability', 90))
                    So       = float(st.session_state.get('flex_so', 0.45))
                    p0       = float(st.session_state.get('flex_p0', 4.2))
                    pt       = float(st.session_state.get('flex_pt', 2.5))
                    cbr      = float(st.session_state.get('flex_cbr', 4.0))
                    sn_sel   = st.session_state.get('flex_w18_sn_sel', '')
                    sn_used  = 5.0
                    if 'SN' in sn_sel:
                        try:
                            sn_used = float(sn_sel.split('SN')[1].split()[0])
                        except Exception:
                            pass

                    pdf_bytes = generate_pdf(
                        project_name  = proj,
                        designer      = designer,
                        W18           = W18,
                        sn_used       = sn_used,
                        reliability   = R,
                        So            = So,
                        p0            = p0,
                        pt            = pt,
                        cbr           = cbr,
                        calc_results  = res,
                        design_check  = chk,
                    )
                    st.session_state['flex_pdf_bytes'] = pdf_bytes
                    st.success('✅ PDF พร้อมดาวน์โหลด')
                except Exception as e:
                    st.error(f'❌ สร้าง PDF ไม่ได้: {e}')

        if st.session_state.get('flex_pdf_bytes'):
            fname = f"flex_pavement_{(proj or 'report').replace(' ','_')}.pdf"
            st.download_button(
                label='📥 ดาวน์โหลด PDF',
                data=st.session_state['flex_pdf_bytes'],
                file_name=fname,
                mime='application/pdf',
                use_container_width=True,
            )
