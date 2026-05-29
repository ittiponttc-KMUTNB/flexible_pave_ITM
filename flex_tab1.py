"""
flex_tab1.py — Tab 1: Traffic & W18
Flexible Pavement Design V1
มี 2 mode: Manual (กรอก W18 ตรง) และ JSON (import จาก ESAL Calculator)
"""
import streamlit as st
import json
from flex_engine import (
    get_zr, compute_esal_flex, ZR_TABLE, MATERIALS,
)

# ── สี helper ─────────────────────────────────────────────────
_AC_BG  = '#FBE9E7'
_AC_BD  = '#BF360C'
_AC_BDL = '#FFAB91'

# ============================================================
# UI Helpers (เหมือน Rigid)
# ============================================================
def _row(label, value, hi=False):
    c = '#BF360C' if hi else '#4E342E'
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;'
        f'padding:3px 0;border-bottom:1px solid rgba(0,0,0,0.06);font-size:12px">'
        f'<span style="color:#78909C">{label}</span>'
        f'<span style="font-family:IBM Plex Mono,monospace;font-weight:600;color:{c}">'
        f'{value}</span></div>', unsafe_allow_html=True)


def _mbox(label, value, unit='', vc='#BF360C', bg='#FBE9E7'):
    st.markdown(
        f'<div style="background:{bg};border:1px solid rgba(0,0,0,0.08);'
        f'border-radius:7px;padding:8px;text-align:center;margin-bottom:4px">'
        f'<div style="font-size:10px;color:#78909C;margin-bottom:2px">{label}</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:20px;'
        f'font-weight:700;color:{vc}">{value}</div>'
        f'<div style="font-size:10px;color:#78909C">{unit}</div></div>',
        unsafe_allow_html=True)


def _card_open(bg=_AC_BG, bd=_AC_BD):
    st.markdown(
        f'<div style="background:{bg};border:2px solid {bd};'
        f'border-left:5px solid {bd};border-radius:10px;'
        f'padding:10px 12px;margin-bottom:6px">', unsafe_allow_html=True)


def _card_close():
    st.markdown('</div>', unsafe_allow_html=True)


def _title(text, color=_AC_BD, border=_AC_BDL):
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{color};'
        f'padding:4px 0 5px;border-bottom:2px solid {border};'
        f'margin-bottom:8px">{text}</div>', unsafe_allow_html=True)


def _hr(color='#FFCCBC'):
    st.markdown(
        f'<hr style="border:none;border-top:1px solid {color};margin:6px 0">',
        unsafe_allow_html=True)


# ============================================================
# Mode Badge
# ============================================================
def _mode_badge(mode: str):
    if mode == 'manual':
        st.markdown(
            '<span class="fp-toggle-manual">✏️ Manual — กรอก W18 ตรง</span>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<span class="fp-toggle-json">📂 JSON — นำเข้าจาก ESAL Calculator</span>',
            unsafe_allow_html=True)


# ============================================================
# Design Parameter Summary Box
# ============================================================
def _param_summary(W18, reliability, Zr, So, delta_psi, pt):
    st.markdown(
        '<div style="background:#E8F5E9;border:1.5px solid #A5D6A7;'
        'border-radius:8px;padding:8px 14px;margin-top:6px">'
        '<div style="font-size:12px;font-weight:700;color:#2E7D32;'
        'margin-bottom:6px">✅ พารามิเตอร์ออกแบบ → ส่งต่อ Tab 2 & 3</div>',
        unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _mbox('W₁₈ (ESALs)', f'{W18:,.0f}', '', '#BF360C', '#FBE9E7')
    with c2:
        _mbox('Reliability', f'{reliability}%', '', '#1565C0', '#E3F2FD')
    with c3:
        _mbox('Zr', f'{Zr:.3f}', '', '#2E7D32', '#E8F5E9')
    with c4:
        _mbox('ΔPSI', f'{delta_psi:.1f}', f'P₀={pt+delta_psi:.1f}→Pt={pt:.1f}',
              '#6A1B9A', '#F3E5F5')
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# Tab 1 Render
# ============================================================
def render_flex_tab1():

    # ── ชื่อโครงการ ───────────────────────────────────────
    st.markdown('<div class="fp-card">', unsafe_allow_html=True)
    st.markdown('<div class="fp-card-title">📋 ข้อมูลโครงการ</div>',
                unsafe_allow_html=True)
    st.text_input(
        'ชื่อโครงการ',
        value=st.session_state.get('flex_project_name', ''),
        key='flex_project_name',
        placeholder='เช่น ทางหลวงหมายเลข 304 ตอน นครราชสีมา-กบินทร์บุรี')
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Toggle Mode ───────────────────────────────────────
    st.markdown('<div class="fp-card">', unsafe_allow_html=True)
    st.markdown('<div class="fp-card-title">🔀 เลือกวิธีป้อนข้อมูล W₁₈</div>',
                unsafe_allow_html=True)

    mode = st.radio(
        'วิธีป้อน W₁₈',
        options=['manual', 'json'],
        format_func=lambda x: '✏️  กรอก W₁₈ ตรง (Manual)' if x == 'manual'
                              else '📂  นำเข้าจาก ESAL Calculator (JSON)',
        index=0 if st.session_state.get('flex_w18_mode', 'manual') == 'manual' else 1,
        key='flex_w18_mode',
        horizontal=True,
        label_visibility='collapsed',
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Design Parameters (ใช้ทั้ง 2 mode) ───────────────
    st.markdown('<div class="fp-card">', unsafe_allow_html=True)
    st.markdown('<div class="fp-card-title">⚙️ พารามิเตอร์การออกแบบ</div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        reliability = st.selectbox(
            'Reliability (%)',
            options=sorted(ZR_TABLE.keys()),
            index=list(sorted(ZR_TABLE.keys())).index(
                st.session_state.get('flex_reliability', 90)),
            key='flex_reliability',
            help='ระดับความน่าเชื่อถือในการออกแบบ — ทล. แนะนำ 90–95%')
    with c2:
        so = st.number_input(
            'Overall Standard Deviation (S₀)',
            0.25, 0.60,
            float(st.session_state.get('flex_so', 0.45)),
            0.05, key='flex_so', format='%.2f',
            help='ค่าเบี่ยงเบนมาตรฐาน — Flexible: 0.40–0.50')
    with c3:
        p0 = st.number_input(
            'Initial Serviceability (P₀)',
            3.5, 5.0,
            float(st.session_state.get('flex_p0', 4.2)),
            0.1, key='flex_p0', format='%.1f')

    c4, c5 = st.columns(2)
    with c4:
        pt = st.number_input(
            'Terminal Serviceability (Pt)',
            1.5, 3.5,
            float(st.session_state.get('flex_pt', 2.5)),
            0.5, key='flex_pt', format='%.1f',
            help='Pt=2.5 ทางหลัก / Pt=2.0 ทางรอง — ตาม ทล.')
    with c5:
        p0_val  = float(st.session_state.get('flex_p0', 4.2))
        pt_val  = float(st.session_state.get('flex_pt', 2.5))
        d_psi   = p0_val - pt_val
        st.markdown(
            f'<div style="background:#FFF3CD;border:1px solid #FFECB3;'
            f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
            f'<div style="font-size:10px;color:#90A4AE">ΔPSI = P₀ − Pt</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:20px;'
            f'font-weight:700;color:#BF360C">{d_psi:.1f}</div>'
            f'<div style="font-size:10px;color:#90A4AE">'
            f'({p0_val:.1f} − {pt_val:.1f})</div></div>',
            unsafe_allow_html=True)

    Zr = get_zr(int(reliability))
    st.markdown(
        f'<div style="background:#F3E5F5;border:1px solid #CE93D8;'
        f'border-radius:7px;padding:6px 10px;margin-top:6px;font-size:12px">'
        f'Zr = <b style="font-family:IBM Plex Mono,monospace;color:#6A1B9A">'
        f'{Zr:.3f}</b>'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;'
        f'S₀ = <b style="font-family:IBM Plex Mono,monospace;color:#6A1B9A">'
        f'{so:.2f}</b>'
        f'&nbsp;&nbsp;|&nbsp;&nbsp;'
        f'ZR×S₀ = <b style="font-family:IBM Plex Mono,monospace;color:#6A1B9A">'
        f'{Zr*so:.3f}</b></div>',
        unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── W18 Input Block ───────────────────────────────────
    if mode == 'manual':
        _render_manual_mode()
    else:
        _render_json_mode()

    # ── สรุปพารามิเตอร์ → ส่งต่อ ─────────────────────────
    W18 = float(st.session_state.get('flex_w18', 1_000_000))
    if W18 > 0:
        p0_final = float(st.session_state.get('flex_p0', 4.2))
        pt_final = float(st.session_state.get('flex_pt', 2.5))
        _param_summary(
            W18=W18,
            reliability=int(st.session_state.get('flex_reliability', 90)),
            Zr=get_zr(int(st.session_state.get('flex_reliability', 90))),
            So=float(st.session_state.get('flex_so', 0.45)),
            delta_psi=p0_final - pt_final,
            pt=pt_final,
        )


# ============================================================
# Manual Mode
# ============================================================
def _render_manual_mode():
    st.markdown('<div class="fp-card">', unsafe_allow_html=True)
    st.markdown('<div class="fp-card-title">✏️ กรอกปริมาณจราจรสะสม W₁₈</div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        w18 = st.number_input(
            'W₁₈ — Design ESALs',
            min_value=10_000.0,
            max_value=500_000_000.0,
            value=float(st.session_state.get('flex_w18', 1_000_000)),
            step=100_000.0,
            format='%.0f',
            key='flex_w18',
            help='ปริมาณจราจรสะสม 18-kip ESAL ตลอดอายุออกแบบ')
    with c2:
        st.markdown(
            f'<div style="background:#FBE9E7;border:1px solid #FFAB91;'
            f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
            f'<div style="font-size:10px;color:#90A4AE">W₁₈ (ล้าน ESAL)</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:22px;'
            f'font-weight:700;color:#BF360C">{w18/1e6:.3f}</div>'
            f'<div style="font-size:10px;color:#90A4AE">×10⁶ 18-kip ESAL</div>'
            f'</div>',
            unsafe_allow_html=True)

    # คำแนะนำ range
    st.markdown(
        '<div style="font-size:11px;color:#78909C;margin-top:4px">'
        '📌 แนวทางกรมทางหลวง: '
        'ทางหลัก ≥ 1M · ทางรอง 0.5–1M · ทางเล็ก < 0.5M</div>',
        unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# JSON Mode
# ============================================================
def _render_json_mode():
    st.markdown('<div class="fp-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="fp-card-title">📂 นำเข้า W₁₈ จาก ESAL Calculator</div>',
        unsafe_allow_html=True)
    st.caption('อัปโหลดไฟล์ .json ที่ Save จาก ESAL Calculator (Flexible)')

    esal_file = st.file_uploader(
        'เลือกไฟล์ ESAL Project (.json)',
        type=['json'],
        key='flex_esal_uploader',
        help='ไฟล์ที่ได้จากปุ่ม 💾 บันทึก Project ใน ESAL Calculator')

    if esal_file is not None:
        fid = f'{esal_file.name}_{esal_file.size}'
        if st.session_state.get('flex_esal_file_id') != fid:
            st.session_state['flex_esal_file_id'] = fid
            try:
                raw = json.load(esal_file)
                _process_esal_json(raw, esal_file.name)
            except Exception as e:
                st.error(f'❌ อ่านไฟล์ไม่ได้: {e}')
                st.session_state['flex_esal_data'] = None

    # แสดงผลถ้ามีข้อมูล
    ed = st.session_state.get('flex_esal_data')
    if ed:
        _show_esal_summary(ed)
    else:
        st.info('⬆️ อัปโหลดไฟล์ .json จาก ESAL Calculator เพื่อนำ W₁₈ มาใช้')

    st.markdown('</div>', unsafe_allow_html=True)


def _process_esal_json(raw: dict, filename: str):
    """validate + คำนวณ W18 จาก JSON"""

    # ── รองรับทั้ง pavement_type: flexible และ rigid ──────
    ptype = raw.get('pavement_type', '').lower()
    if ptype == 'rigid':
        st.warning('⚠️ ไฟล์นี้เป็น Rigid Pavement — W₁₈ จะถูกคำนวณใหม่สำหรับ Flexible')

    if 'traffic_data' not in raw:
        st.error('❌ ไฟล์ JSON ไม่ถูกต้อง (ขาด traffic_data)')
        st.session_state['flex_esal_data'] = None
        return

    traffic_data     = raw['traffic_data']
    pt_json          = float(raw.get('pt',               2.5))
    lane_factor      = float(raw.get('lane_factor',      0.9))
    direction_factor = float(raw.get('direction_factor', 0.5))

    # คำนวณ W18 ที่ SN=5 (default estimate สำหรับ Flexible)
    # ผู้ใช้สามารถ override ได้ใน Tab 3
    try:
        W18_total, tf = compute_esal_flex(
            traffic_data, pt_json, lane_factor, direction_factor, SN=5.0)
    except Exception as e:
        st.error(f'❌ คำนวณ W18 ไม่ได้: {e}')
        st.session_state['flex_esal_data'] = None
        return

    st.session_state['flex_esal_data'] = {
        'traffic_data':     traffic_data,
        'pt':               pt_json,
        'lane_factor':      lane_factor,
        'direction_factor': direction_factor,
        'filename':         filename,
        'num_years':        len(traffic_data),
        'W18_computed':     W18_total,
        'truck_factors':    tf,
    }
    # อัปเดต W18 ใน session state ให้ Tab อื่นใช้
    st.session_state['flex_w18']  = float(W18_total)
    st.session_state['flex_pt']   = pt_json
    st.rerun()


def _show_esal_summary(ed: dict):
    """แสดงสรุปข้อมูลจาก ESAL JSON"""
    W18     = ed['W18_computed']
    tf      = ed.get('truck_factors', {})
    n_years = ed['num_years']

    st.success(f'✅ โหลดสำเร็จ: {ed["filename"]}')
    _hr()

    # สรุปหลัก
    c1, c2, c3 = st.columns(3)
    with c1:
        _mbox('W₁₈ (คำนวณจาก JSON)', f'{W18:,.0f}', 'ESALs')
    with c2:
        _mbox('W₁₈ (ล้าน ESAL)', f'{W18/1e6:.3f}', '×10⁶')
    with c3:
        _mbox('ระยะออกแบบ', f'{n_years}', 'ปี')

    _hr()

    # parameters จาก JSON
    c4, c5, c6 = st.columns(3)
    with c4:
        _row('Lane Factor',      f'{ed["lane_factor"]:.2f}')
        _row('Direction Factor', f'{ed["direction_factor"]:.2f}')
    with c5:
        _row('Pt (จาก JSON)', f'{ed["pt"]:.1f}')
        _row('SN ที่ใช้คำนวณ', '5.0 (default)')
    with c6:
        st.markdown(
            '<div style="font-size:10px;color:#90A4AE;margin-bottom:4px">'
            'หมายเหตุ: W₁₈ คำนวณที่ SN=5 (preliminary estimate)<br>'
            'ค่าจริงจะถูก iterate ใน Tab 3</div>',
            unsafe_allow_html=True)

    # Truck Factors
    if tf:
        _hr()
        st.markdown(
            '<div style="font-size:11px;font-weight:600;color:#78909C;'
            'margin-bottom:4px">Truck Factors (LEF@SN=5, Pt='
            f'{ed["pt"]:.1f})</div>',
            unsafe_allow_html=True)
        cols = st.columns(len(tf))
        for i, (code, val) in enumerate(tf.items()):
            with cols[i]:
                _mbox(code, f'{val:.4f}', '', '#BF360C', '#FBE9E7')

    # Traffic table (แสดง 5 ปีแรก)
    td = ed.get('traffic_data', [])
    if td:
        _hr()
        st.markdown(
            '<div style="font-size:11px;font-weight:600;color:#78909C;'
            'margin-bottom:4px">ข้อมูลปริมาณจราจร (5 ปีแรก)</div>',
            unsafe_allow_html=True)
        import pandas as pd
        df = pd.DataFrame(td[:5])
        st.dataframe(df, use_container_width=True, hide_index=True)
        if len(td) > 5:
            st.caption(f'แสดง 5 จาก {len(td)} ปี')

    # ── Override W18 ─────────────────────────────────────
    _hr()
    st.markdown(
        '<div style="font-size:12px;font-weight:600;color:#BF360C;'
        'margin-bottom:4px">🔧 ปรับแก้ W₁₈ (ถ้าต้องการ)</div>',
        unsafe_allow_html=True)

    c_ov1, c_ov2 = st.columns([2, 1])
    with c_ov1:
        w18_override = st.number_input(
            'W₁₈ ที่ใช้ออกแบบ (override ได้)',
            min_value=10_000.0,
            max_value=500_000_000.0,
            value=float(st.session_state.get('flex_w18', W18)),
            step=100_000.0,
            format='%.0f',
            key='flex_w18',
            help='ค่าเริ่มต้นคือ W18 ที่คำนวณจาก JSON — แก้ไขได้')
    with c_ov2:
        st.markdown(
            f'<div style="background:#FBE9E7;border:1px solid #FFAB91;'
            f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
            f'<div style="font-size:10px;color:#90A4AE">W₁₈ ที่ใช้</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
            f'font-weight:700;color:#BF360C">'
            f'{st.session_state.get("flex_w18", W18)/1e6:.3f}M</div>'
            f'</div>',
            unsafe_allow_html=True)

    if abs(st.session_state.get('flex_w18', W18) - W18) > 1000:
        st.caption(
            f'⚠️ W₁₈ ถูกแก้ไขจากค่า JSON ({W18:,.0f}) '
            f'เป็น {st.session_state["flex_w18"]:,.0f}')
