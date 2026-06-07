"""
flex_tab1.py — Tab 1: Traffic & W18
Flexible Pavement Design V1
มี 2 mode: Manual (กรอก W18 ตรง) และ JSON (import จาก ESAL Calculator)
"""
import streamlit as st
import json
from flex_engine import (
    get_zr, compute_esal_flex, compute_w18_sn_table, ZR_TABLE, MATERIALS,
)

_AC_BD  = '#BF360C'
_AC_BDL = '#FFAB91'

# ============================================================
# UI Helpers
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


def _card_title(text, color=_AC_BD, border=_AC_BDL):
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{color};'
        f'padding:2px 0 6px;border-bottom:2px solid {border};'
        f'margin-bottom:10px">{text}</div>', unsafe_allow_html=True)


def _hr(color='#FFCCBC'):
    st.markdown(
        f'<hr style="border:none;border-top:1px solid {color};margin:6px 0">',
        unsafe_allow_html=True)


# ============================================================
# Design Parameter Summary Box — pure HTML
# ============================================================
def _param_summary(W18, reliability, Zr, So, delta_psi, pt):
    st.markdown(
        f'<div style="background:#E8F5E9;border:1.5px solid #A5D6A7;'
        f'border-radius:8px;padding:10px 14px;margin-top:6px">'
        f'<div style="font-size:12px;font-weight:700;color:#2E7D32;margin-bottom:8px">'
        f'✅ พารามิเตอร์ออกแบบ → ส่งต่อ Tab 2 &amp; 3</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">'
        f'<div style="background:#FBE9E7;border-radius:7px;padding:8px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">W₁₈ (ESALs)</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:15px;font-weight:700;color:#BF360C">{W18:,.0f}</div>'
        f'</div>'
        f'<div style="background:#E3F2FD;border-radius:7px;padding:8px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">Reliability</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:15px;font-weight:700;color:#1565C0">{reliability}%</div>'
        f'</div>'
        f'<div style="background:#E8F5E9;border-radius:7px;padding:8px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">Zr</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:15px;font-weight:700;color:#2E7D32">{Zr:.3f}</div>'
        f'</div>'
        f'<div style="background:#F3E5F5;border-radius:7px;padding:8px;text-align:center">'
        f'<div style="font-size:10px;color:#78909C">ΔPSI</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:15px;font-weight:700;color:#6A1B9A">{delta_psi:.1f}</div>'
        f'<div style="font-size:10px;color:#78909C">P₀={pt+delta_psi:.1f} → Pt={pt:.1f}</div>'
        f'</div>'
        f'</div></div>',
        unsafe_allow_html=True)


# ============================================================
# W18–SN Mapping Cards
# ============================================================
def _w18_sn_cards(rows: list):
    """แสดง card W18 ต่อ SN — ไม่มีการเปรียบเทียบกับ W18_design"""
    st.markdown(
        '<div style="font-size:12px;font-weight:700;color:#BF360C;margin-bottom:8px">'
        '📊 ผลการคำนวณ ESAL — Flexible Pavement'
        '<span style="font-size:10px;font-weight:400;color:#78909C;margin-left:8px">'
        '(W₁₈ ที่ SN แต่ละค่า)</span></div>',
        unsafe_allow_html=True)

    cols_per_row = 4
    for batch_start in range(0, len(rows), cols_per_row):
        batch = rows[batch_start: batch_start + cols_per_row]
        cols  = st.columns(len(batch))
        for col, r in zip(cols, batch):
            sn  = r['SN']
            w18 = r['W18']
            with col:
                st.markdown(
                    f'<div style="background:#E8F5E9;border:1px solid #A5D6A7;'
                    f'border-radius:8px;padding:10px 8px;text-align:center;margin-bottom:6px">'
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:22px;'
                    f'font-weight:700;color:#2E7D32">{w18:,.0f}</div>'
                    f'<div style="font-size:10px;color:#78909C;margin-top:3px">'
                    f'ESAL — SN {sn:.1f} ✅</div>'
                    f'</div>',
                    unsafe_allow_html=True)

    st.markdown(
        '<div style="background:#E8F5E9;border:1.5px solid #A5D6A7;'
        'border-radius:8px;padding:8px 14px;margin-top:4px;font-size:12px">'
        '✅ ค่า ESAL บันทึกแล้ว → ใช้ได้ใน Tab Flexible Design</div>',
        unsafe_allow_html=True)


# ============================================================
# Tab 1 Render
# ============================================================
def render_flex_tab1():

    # ── apply pending values ก่อน widget render ───────────
    if '_flex_w18_pending' in st.session_state:
        st.session_state['flex_w18'] = st.session_state.pop('_flex_w18_pending')
    if '_flex_pt_pending' in st.session_state:
        st.session_state['flex_pt'] = st.session_state.pop('_flex_pt_pending')

    # ── ชื่อโครงการ ───────────────────────────────────────
    with st.container(border=True):
        _card_title('📋 ข้อมูลโครงการ')
        st.text_input(
            'ชื่อโครงการ',
            key='flex_project_name',
            placeholder='เช่น ทางหลวงหมายเลข 304 ตอน นครราชสีมา-กบินทร์บุรี')

    # ── Toggle Mode ───────────────────────────────────────
    with st.container(border=True):
        _card_title('🔀 เลือกวิธีป้อนข้อมูล W₁₈')
        mode = st.radio(
            'วิธีป้อน W₁₈',
            options=['manual', 'json'],
            format_func=lambda x: '✏️  กรอก W₁₈ ตรง (Manual)' if x == 'manual'
                                  else '📂  นำเข้าจาก ESAL Calculator (JSON)',
            key='flex_w18_mode',
            horizontal=True,
            label_visibility='collapsed')

    # ── Design Parameters ─────────────────────────────────
    with st.container(border=True):
        _card_title('⚙️ พารามิเตอร์การออกแบบ')

        c1, c2, c3 = st.columns(3)
        with c1:
            reliability = st.selectbox(
                'Reliability (%)',
                options=sorted(ZR_TABLE.keys()),
                index=list(sorted(ZR_TABLE.keys())).index(
                    st.session_state.get('flex_reliability', 90)),
                key='flex_reliability',
                help='ระดับความน่าเชื่อถือ — ทล. แนะนำ 90–95%')
        with c2:
            so = st.number_input(
                'Overall Standard Deviation (S₀)',
                0.25, 0.60,
                float(st.session_state.get('flex_so', 0.45)),
                0.05, key='flex_so', format='%.2f',
                help='Flexible: 0.40–0.50')
        with c3:
            p0 = st.number_input(
                'Initial Serviceability (P₀)',
                3.5, 5.0,
                float(st.session_state.get('flex_p0', 4.2)),
                0.1, key='flex_p0', format='%.1f')

        c4, c5, c6 = st.columns(3)
        with c4:
            pt = st.number_input(
                'Terminal Serviceability (Pt)',
                1.5, 3.5,
                float(st.session_state.get('flex_pt', 2.5)),
                0.5, key='flex_pt', format='%.1f',
                help='Pt=2.5 ทางหลัก / Pt=2.0 ทางรอง — ตาม ทล.')
        with c5:
            pt_val = float(st.session_state.get('flex_pt', 2.5))
            st.markdown(
                f'<div style="background:#FBE9E7;border:1px solid #FFAB91;'
                f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
                f'<div style="font-size:10px;color:#90A4AE">Pt (Terminal Serviceability)</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:20px;'
                f'font-weight:700;color:#BF360C">{pt_val:.1f}</div>'
                f'<div style="font-size:10px;color:#90A4AE">'
                f'{"ทางหลัก" if pt_val >= 2.5 else "ทางรอง"}</div>'
                f'</div>', unsafe_allow_html=True)
        with c6:
            p0_val = float(st.session_state.get('flex_p0', 4.2))
            pt_val = float(st.session_state.get('flex_pt', 2.5))
            d_psi  = p0_val - pt_val
            st.markdown(
                f'<div style="background:#FFF3CD;border:1px solid #FFECB3;'
                f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
                f'<div style="font-size:10px;color:#90A4AE">ΔPSI = P₀ − Pt</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:20px;'
                f'font-weight:700;color:#BF360C">{d_psi:.1f}</div>'
                f'<div style="font-size:10px;color:#90A4AE">({p0_val:.1f} − {pt_val:.1f})</div>'
                f'</div>', unsafe_allow_html=True)

        Zr = get_zr(int(reliability))
        st.markdown(
            f'<div style="background:#F3E5F5;border:1px solid #CE93D8;'
            f'border-radius:7px;padding:6px 10px;margin-top:6px;font-size:12px">'
            f'Zr = <b style="font-family:IBM Plex Mono,monospace;color:#6A1B9A">{Zr:.3f}</b>'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;'
            f'S₀ = <b style="font-family:IBM Plex Mono,monospace;color:#6A1B9A">{so:.2f}</b>'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;'
            f'ZR×S₀ = <b style="font-family:IBM Plex Mono,monospace;color:#6A1B9A">{Zr*so:.3f}</b>'
            f'</div>', unsafe_allow_html=True)

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
            pt=pt_final)


# ============================================================
# Manual Mode
# ============================================================
def _render_manual_mode():
    with st.container(border=True):
        _card_title('✏️ กรอกปริมาณจราจรสะสม W₁₈')

        c1, c2 = st.columns(2)
        with c1:
            w18 = st.number_input(
                'W₁₈ — Design ESALs',
                min_value=10_000.0, max_value=500_000_000.0,
                value=float(st.session_state.get('flex_w18', 1_000_000)),
                step=100_000.0, format='%.0f', key='flex_w18',
                help='ปริมาณจราจรสะสม 18-kip ESAL ตลอดอายุออกแบบ')
        with c2:
            st.markdown(
                f'<div style="background:#FBE9E7;border:1px solid #FFAB91;'
                f'border-radius:8px;padding:8px;text-align:center;margin-top:4px">'
                f'<div style="font-size:10px;color:#90A4AE">W₁₈ (ล้าน ESAL)</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:22px;'
                f'font-weight:700;color:#BF360C">{w18/1e6:.3f}</div>'
                f'<div style="font-size:10px;color:#90A4AE">×10⁶ 18-kip ESAL</div>'
                f'</div>', unsafe_allow_html=True)

        st.markdown(
            '<div style="font-size:11px;color:#78909C;margin-top:4px">'
            '📌 แนวทางกรมทางหลวง: ทางหลัก ≥ 1M · ทางรอง 0.5–1M · ทางเล็ก &lt; 0.5M'
            '</div>', unsafe_allow_html=True)


# ============================================================
# JSON Mode
# ============================================================
def _render_json_mode():
    with st.container(border=True):
        _card_title('📂 นำเข้า W₁₈ จาก ESAL Calculator')
        st.caption('อัปโหลดไฟล์ .json ที่ Save จาก ESAL Calculator (Flexible)')

        esal_file = st.file_uploader(
            'เลือกไฟล์ ESAL Project (.json)', type=['json'],
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

        ed = st.session_state.get('flex_esal_data')
        if ed:
            _show_esal_summary(ed)
        else:
            st.info('⬆️ อัปโหลดไฟล์ .json จาก ESAL Calculator เพื่อนำ W₁₈ มาใช้')


def _process_esal_json(raw: dict, filename: str):
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

    try:
        W18_total, tf = compute_esal_flex(
            traffic_data, pt_json, lane_factor, direction_factor, SN=5.0)
        # คำนวณ W18-SN table ล่วงหน้า cache ไว้ใน esal_data
        param_list = raw.get('param_list', None)   # SN list จาก JSON
        sn_table = compute_w18_sn_table(
            traffic_data, pt_json, lane_factor, direction_factor,
            sn_grid=param_list)
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
        'sn_table':         sn_table,   # ← W18-SN mapping
        'param_list':       raw.get('param_list', None),
    }
    st.session_state['_flex_w18_pending'] = float(W18_total)
    st.session_state['_flex_pt_pending']  = pt_json
    st.rerun()


def _show_esal_summary(ed: dict):
    W18     = ed['W18_computed']
    tf      = ed.get('truck_factors', {})
    n_years = ed['num_years']
    sn_tbl  = ed.get('sn_table', [])

    st.success(f'✅ โหลดสำเร็จ: {ed["filename"]}')

    # ── เตือนถ้า pt ใน JSON ไม่ตรงกับ Design Parameters ──
    pt_json    = ed['pt']
    pt_design  = float(st.session_state.get('flex_pt', 2.5))
    if abs(pt_json - pt_design) > 0.01:
        st.warning(
            f'⚠️ **pt ไม่ตรงกัน** — '
            f'JSON ใช้ pt = **{pt_json:.1f}** '
            f'แต่ Design Parameters ตั้งไว้ที่ pt = **{pt_design:.1f}**\n\n'
            f'W₁₈ ใน cards คำนวณด้วย pt = {pt_json:.1f} (ตาม JSON) '
            f'กรุณาตรวจสอบว่าต้องการใช้ค่าใด')
    _hr()

    # parameters
    c4, c5, c6 = st.columns(3)
    with c4:
        _row('Lane Factor',      f'{ed["lane_factor"]:.2f}')
        _row('Direction Factor', f'{ed["direction_factor"]:.2f}')
    with c5:
        _row('Pt (จาก JSON)', f'{ed["pt"]:.1f}')
        _row('ระยะออกแบบ', f'{n_years} ปี')
    with c6:
        param_list = ed.get('param_list')
        sn_str = ', '.join(str(s) for s in param_list) if param_list else 'Default grid'
        _row('SN ที่คำนวณ', sn_str)

    # ── W18–SN Mapping Cards (อ่านจาก JSON โดยตรง) ──────────────
    # ── W18–SN Mapping Cards ──────────────────────────────
    # ถ้า sn_table ไม่มีใน cache ให้คำนวณใหม่จาก param_list ใน JSON
    if not sn_tbl and ed.get('traffic_data'):
        try:
            sn_tbl = compute_w18_sn_table(
                ed['traffic_data'], ed['pt'],
                ed['lane_factor'], ed['direction_factor'],
                sn_grid=ed.get('param_list', None))
            st.session_state['flex_esal_data']['sn_table'] = sn_tbl
        except Exception:
            sn_tbl = []

    if sn_tbl:
        _hr()
        _w18_sn_cards(sn_tbl)

    # Truck Factors + Traffic table
    td = ed.get('traffic_data', [])
    if td:
        with st.expander('📋 ข้อมูลปริมาณจราจร', expanded=False):
            import pandas as pd
            df = pd.DataFrame(td[:5])
            st.dataframe(df, use_container_width=True, hide_index=True)
            if len(td) > 5:
                st.caption(f'แสดง 5 จาก {len(td)} ปี')
