"""
flex_tab2.py — Tab 2: Subgrade & Layer Setup
Flexible Pavement Design V1 · AASHTO 1993
"""
import streamlit as st
from flex_engine import (
    mr_from_cbr, MATERIALS, MATERIAL_NAMES,
    PRESETS, DRAINAGE_TABLE,
)

_AC_BD  = '#BF360C'
_AC_BDL = '#FFAB91'
_AC_BG  = '#FBE9E7'

# ── layer type label ─────────────────────────────────────────
_LAYER_TYPE_LABEL = {
    'surface':  '🔲 ผิวทาง',
    'base':     '🟫 พื้นทาง',
    'subbase':  '🟧 รองพื้นทาง',
    'selected': '🟨 วัสดุคัดเลือก',
    'none':     '—',
}

# ============================================================
# UI Helpers
# ============================================================
def _card_title(text, color=_AC_BD, border=_AC_BDL):
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{color};'
        f'padding:2px 0 6px;border-bottom:2px solid {border};'
        f'margin-bottom:10px">{text}</div>', unsafe_allow_html=True)


def _row(label, value, hi=False):
    c = _AC_BD if hi else '#4E342E'
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;'
        f'padding:3px 0;border-bottom:1px solid rgba(0,0,0,0.06);font-size:12px">'
        f'<span style="color:#78909C">{label}</span>'
        f'<span style="font-family:IBM Plex Mono,monospace;font-weight:600;color:{c}">'
        f'{value}</span></div>', unsafe_allow_html=True)


def _badge(text, bg='#E3F2FD', color='#1565C0'):
    st.markdown(
        f'<span style="background:{bg};color:{color};border-radius:5px;'
        f'padding:2px 8px;font-size:11px;font-weight:600">{text}</span>',
        unsafe_allow_html=True)


def _hr(color='#FFCCBC'):
    st.markdown(
        f'<hr style="border:none;border-top:1px solid {color};margin:6px 0">',
        unsafe_allow_html=True)


# ============================================================
# Session State Init
# ============================================================
def _init_layers(preset_layers: list | None = None):
    """สร้าง/reset layer list ใน session state"""
    if preset_layers:
        layers = []
        for pl in preset_layers:
            mat  = pl['material']
            mdat = MATERIALS.get(mat, {})
            layers.append({
                'material':      mat,
                'thickness_cm':  float(pl.get('thickness_cm', 15.0)),
                'layer_coeff':   mdat.get('layer_coeff', 0.10),
                'drainage_coeff': 1.0,
                'override_ai':   False,
            })
        st.session_state['flex_layers'] = layers
    elif 'flex_layers' not in st.session_state:
        # default: AC + CTB + GSB + SM
        default = PRESETS.get('AC + CTB + GSB + SM (มาตรฐานหลัก)')
        if default:
            _init_layers(default['layers'])
        else:
            st.session_state['flex_layers'] = [
                {'material': 'ผิวทางลาดยาง AC',
                 'thickness_cm': 15.0, 'layer_coeff': 0.40,
                 'drainage_coeff': 1.0, 'override_ai': False},
            ]


# ============================================================
# Drainage Helper
# ============================================================
def _get_mi(quality: str, saturation: str) -> float:
    return DRAINAGE_TABLE.get(quality, {}).get('values', {}).get(saturation, 1.0)


# ============================================================
# Layer Card
# ============================================================
def _render_layer_card(idx: int, layer: dict, n_layers: int):
    """render card สำหรับแต่ละชั้น — return (updated_layer, delete_flag)"""
    mat       = layer['material']
    mat_data  = MATERIALS.get(mat, {})
    ltype     = mat_data.get('layer_type', 'base')
    ltype_lbl = _LAYER_TYPE_LABEL.get(ltype, '')

    delete_flag = False

    with st.container(border=True):
        # ── header row ──────────────────────────────────────
        hc1, hc2, hc3 = st.columns([5, 2, 1])
        with hc1:
            st.markdown(
                f'<div style="font-size:13px;font-weight:700;color:{_AC_BD}">'
                f'ชั้นที่ {idx + 1} &nbsp;'
                f'<span style="font-size:11px;font-weight:400;color:#78909C">'
                f'{ltype_lbl}</span></div>',
                unsafe_allow_html=True)
        with hc2:
            # ย้ายชั้น ↑↓
            mv1, mv2 = st.columns(2)
            with mv1:
                if st.button('↑', key=f'layer_up_{idx}',
                             disabled=(idx == 0), use_container_width=True):
                    layers = st.session_state['flex_layers']
                    layers[idx - 1], layers[idx] = layers[idx], layers[idx - 1]
                    st.rerun()
            with mv2:
                if st.button('↓', key=f'layer_dn_{idx}',
                             disabled=(idx == n_layers - 1), use_container_width=True):
                    layers = st.session_state['flex_layers']
                    layers[idx], layers[idx + 1] = layers[idx + 1], layers[idx]
                    st.rerun()
        with hc3:
            if st.button('🗑️', key=f'layer_del_{idx}',
                         help='ลบชั้นนี้', use_container_width=True):
                delete_flag = True

        _hr()

        # ── วัสดุ + ความหนา ──────────────────────────────────
        c1, c2 = st.columns([3, 2])
        with c1:
            mat_names = MATERIAL_NAMES
            cur_idx   = mat_names.index(mat) if mat in mat_names else 0
            new_mat   = st.selectbox(
                'วัสดุ',
                options=mat_names,
                index=cur_idx,
                key=f'layer_mat_{idx}',
                label_visibility='collapsed',
            )
            if new_mat != mat:
                layer['material']     = new_mat
                layer['layer_coeff']  = MATERIALS[new_mat]['layer_coeff']
                layer['override_ai']  = False
                st.rerun()

        with c2:
            new_t = st.number_input(
                'ความหนา (cm)',
                min_value=1.0, max_value=150.0,
                value=float(layer['thickness_cm']),
                step=1.0, format='%.0f',
                key=f'layer_t_{idx}',
                label_visibility='collapsed',
            )
            layer['thickness_cm'] = new_t

        # ── a_i (Layer Coefficient) ───────────────────────────
        ai_default = MATERIALS.get(layer['material'], {}).get('layer_coeff', 0.10)
        c3, c4 = st.columns([3, 2])
        with c3:
            override = st.checkbox(
                f'Override a_i (ค่า default = {ai_default:.3f})',
                value=layer.get('override_ai', False),
                key=f'layer_override_{idx}',
            )
            layer['override_ai'] = override
        with c4:
            if override:
                new_ai = st.number_input(
                    'a_i',
                    min_value=0.01, max_value=0.60,
                    value=float(layer.get('layer_coeff', ai_default)),
                    step=0.01, format='%.3f',
                    key=f'layer_ai_{idx}',
                    label_visibility='collapsed',
                )
                layer['layer_coeff'] = new_ai
            else:
                layer['layer_coeff'] = ai_default
                st.markdown(
                    f'<div style="background:#E3F2FD;border-radius:6px;'
                    f'padding:6px 10px;text-align:center;margin-top:2px">'
                    f'<span style="font-size:10px;color:#78909C">a_i (auto)</span><br>'
                    f'<span style="font-family:IBM Plex Mono,monospace;'
                    f'font-size:18px;font-weight:700;color:#1565C0">'
                    f'{ai_default:.3f}</span></div>',
                    unsafe_allow_html=True)

        # ── Drainage ──────────────────────────────────────────
        # ชั้น surface (AC/PMA) ใช้ m_i = 1.0 fixed
        if ltype == 'surface':
            layer['drainage_coeff'] = 1.0
            st.markdown(
                '<div style="font-size:11px;color:#78909C;margin-top:4px">'
                'Drainage m_i = 1.0 (ผิวทาง — fixed)</div>',
                unsafe_allow_html=True)
        else:
            with st.expander('⚙️ Drainage Coefficient (m_i)', expanded=False):
                dq_options  = list(DRAINAGE_TABLE.keys())
                sat_options = ['<1%', '1-5%', '5-25%', '>25%']

                dq_key  = f'layer_dq_{idx}'
                sat_key = f'layer_sat_{idx}'

                if dq_key not in st.session_state:
                    st.session_state[dq_key]  = 'Good'
                if sat_key not in st.session_state:
                    st.session_state[sat_key] = '1-5%'

                dc1, dc2 = st.columns(2)
                with dc1:
                    dq = st.selectbox(
                        'Drainage Quality',
                        options=dq_options,
                        index=dq_options.index(
                            st.session_state.get(dq_key, 'Good')),
                        key=dq_key,
                    )
                with dc2:
                    sat = st.selectbox(
                        '% Time Saturated',
                        options=sat_options,
                        index=sat_options.index(
                            st.session_state.get(sat_key, '1-5%')),
                        key=sat_key,
                    )

                mi = _get_mi(dq, sat)
                layer['drainage_coeff'] = mi
                desc = DRAINAGE_TABLE[dq]['description']
                st.markdown(
                    f'<div style="background:#E8F5E9;border-radius:6px;'
                    f'padding:6px 10px;margin-top:4px;font-size:12px">'
                    f'{desc} &nbsp;→&nbsp; '
                    f'<b style="font-family:IBM Plex Mono,monospace;color:#2E7D32">'
                    f'm_i = {mi:.2f}</b></div>',
                    unsafe_allow_html=True)

        # ── preview SN contribution ───────────────────────────
        ai  = layer['layer_coeff']
        mi  = layer['drainage_coeff']
        t   = layer['thickness_cm']
        sn  = round(ai * (t / 2.54) * mi, 3)
        mr  = MATERIALS.get(layer['material'], {}).get('mr_psi', 0)
        _hr()
        st.markdown(
            f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:2px">'
            f'<span style="background:#FBE9E7;border-radius:5px;padding:3px 8px;'
            f'font-size:11px">a_i = <b style="font-family:IBM Plex Mono,monospace">'
            f'{ai:.3f}</b></span>'
            f'<span style="background:#FBE9E7;border-radius:5px;padding:3px 8px;'
            f'font-size:11px">m_i = <b style="font-family:IBM Plex Mono,monospace">'
            f'{mi:.2f}</b></span>'
            f'<span style="background:#FBE9E7;border-radius:5px;padding:3px 8px;'
            f'font-size:11px">D = <b style="font-family:IBM Plex Mono,monospace">'
            f'{t:.0f} cm ({t/2.54:.2f}")</b></span>'
            f'<span style="background:#E8F5E9;border-radius:5px;padding:3px 8px;'
            f'font-size:11px;color:#2E7D32">ΔSN = <b style="font-family:IBM Plex Mono,monospace">'
            f'{sn:.3f}</b></span>'
            f'<span style="background:#E3F2FD;border-radius:5px;padding:3px 8px;'
            f'font-size:11px;color:#1565C0">Mr = <b style="font-family:IBM Plex Mono,monospace">'
            f'{mr:,} psi</b></span>'
            f'</div>',
            unsafe_allow_html=True)

    return layer, delete_flag


# ============================================================
# Layer Summary Table
# ============================================================
def _render_layer_summary(layers: list, cbr: float):
    """ตารางสรุปทุกชั้น + SN รวม"""
    if not layers:
        return

    total_sn   = 0.0
    total_cm   = 0.0
    rows_html  = ''
    for i, layer in enumerate(layers):
        ai   = layer['layer_coeff']
        mi   = layer['drainage_coeff']
        t    = layer['thickness_cm']
        sn   = ai * (t / 2.54) * mi
        total_sn += sn
        total_cm += t
        mat  = MATERIALS.get(layer['material'], {})
        sname = mat.get('short_name', layer['material'][:8])
        rows_html += (
            f'<tr>'
            f'<td style="text-align:center">{i+1}</td>'
            f'<td>{sname}</td>'
            f'<td style="text-align:right">{ai:.3f}</td>'
            f'<td style="text-align:right">{mi:.2f}</td>'
            f'<td style="text-align:right">{t:.0f} cm</td>'
            f'<td style="text-align:right;font-weight:600;color:#BF360C">'
            f'{sn:.3f}</td>'
            f'</tr>'
        )

    mr_sub = round(1500 * cbr if cbr < 10 else 1000 + 555 * cbr)
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:12px">'
        f'<thead><tr style="background:#BF360C;color:white">'
        f'<th style="padding:5px 8px;text-align:center">ชั้น</th>'
        f'<th style="padding:5px 8px;text-align:left">วัสดุ</th>'
        f'<th style="padding:5px 8px;text-align:right">a_i</th>'
        f'<th style="padding:5px 8px;text-align:right">m_i</th>'
        f'<th style="padding:5px 8px;text-align:right">ความหนา</th>'
        f'<th style="padding:5px 8px;text-align:right">ΔSN</th>'
        f'</tr></thead>'
        f'<tbody style="background:white">{rows_html}</tbody>'
        f'<tfoot><tr style="background:#FFF3CD;font-weight:700">'
        f'<td colspan="4" style="padding:5px 8px">รวม</td>'
        f'<td style="padding:5px 8px;text-align:right">{total_cm:.0f} cm</td>'
        f'<td style="padding:5px 8px;text-align:right;color:#BF360C">'
        f'{total_sn:.3f}</td>'
        f'</tr></tfoot>'
        f'</table>',
        unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:11px;color:#78909C;margin-top:4px">'
        f'Subgrade: CBR = {cbr:.1f}% → Mr = {mr_sub:,} psi'
        f'</div>', unsafe_allow_html=True)


# ============================================================
# Main Render
# ============================================================
def render_flex_tab2():

    _init_layers()

    # ── 1. Subgrade ───────────────────────────────────────
    with st.container(border=True):
        _card_title('🌍 Subgrade')
        c1, c2, c3 = st.columns(3)
        with c1:
            cbr = st.number_input(
                'CBR (%)',
                min_value=1.0, max_value=30.0,
                value=float(st.session_state.get('flex_cbr', 4.0)),
                step=0.5, format='%.1f',
                key='flex_cbr',
                help='CBR ของดินทางเดิม (In-situ CBR)')
        with c2:
            mr = mr_from_cbr(cbr)
            st.markdown(
                f'<div style="background:#FBE9E7;border-radius:8px;'
                f'padding:8px;text-align:center;margin-top:4px">'
                f'<div style="font-size:10px;color:#78909C">Mr (psi)</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:20px;'
                f'font-weight:700;color:{_AC_BD}">{mr:,.0f}</div>'
                f'<div style="font-size:10px;color:#78909C">'
                f'{"1,500×CBR" if cbr < 10 else "1,000+555×CBR"}</div>'
                f'</div>', unsafe_allow_html=True)
        with c3:
            mr_mpa = round(mr * 0.006895, 1)
            st.markdown(
                f'<div style="background:#E3F2FD;border-radius:8px;'
                f'padding:8px;text-align:center;margin-top:4px">'
                f'<div style="font-size:10px;color:#78909C">Mr (MPa)</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:20px;'
                f'font-weight:700;color:#1565C0">{mr_mpa:.1f}</div>'
                f'<div style="font-size:10px;color:#78909C">1 psi = 0.006895 MPa</div>'
                f'</div>', unsafe_allow_html=True)

        st.session_state['flex_subgrade_mr'] = mr

    # ── 2. Preset Structure ───────────────────────────────
    with st.container(border=True):
        _card_title('📐 โครงสร้างมาตรฐาน (Preset)')
        preset_names = list(PRESETS.keys())
        sel = st.selectbox(
            'เลือก Preset',
            options=preset_names,
            index=0,
            key='flex_preset_select',
            label_visibility='collapsed',
        )
        if sel != '— เลือกโครงสร้างมาตรฐาน —':
            preset = PRESETS[sel]
            st.caption(f'📌 {preset["description"]}')
            if st.button(f'✅ โหลด Preset: {sel}',
                         key='flex_load_preset',
                         type='primary'):
                _init_layers(preset['layers'])
                st.session_state['flex_preset_select'] = '— เลือกโครงสร้างมาตรฐาน —'
                st.rerun()

    # ── 3. Layer Cards ────────────────────────────────────
    with st.container(border=True):
        _card_title('🏗️ กำหนดชั้นทาง')

        layers      = st.session_state.get('flex_layers', [])
        n           = len(layers)
        delete_idx  = None

        for i, layer in enumerate(layers):
            updated_layer, do_del = _render_layer_card(i, layer, n)
            layers[i] = updated_layer
            if do_del:
                delete_idx = i

        # ลบชั้น
        if delete_idx is not None:
            layers.pop(delete_idx)
            st.session_state['flex_layers'] = layers
            st.rerun()

        st.session_state['flex_layers'] = layers

        _hr()

        # ปุ่มเพิ่มชั้น
        ca, cb = st.columns([1, 3])
        with ca:
            if st.button('➕ เพิ่มชั้น', key='flex_add_layer',
                         use_container_width=True):
                layers.append({
                    'material':       'รองพื้นทางวัสดุมวลรวม CBR 25%',
                    'thickness_cm':   15.0,
                    'layer_coeff':    0.10,
                    'drainage_coeff': 1.0,
                    'override_ai':    False,
                })
                st.session_state['flex_layers'] = layers
                st.rerun()
        with cb:
            st.markdown(
                f'<div style="font-size:11px;color:#78909C;margin-top:8px">'
                f'มี {n} ชั้น | ↑↓ เรียงลำดับ | 🗑️ ลบชั้น</div>',
                unsafe_allow_html=True)

    # ── 4. Summary ────────────────────────────────────────
    if layers:
        with st.container(border=True):
            _card_title('📊 สรุปโครงสร้างชั้นทาง')
            cbr_val = float(st.session_state.get('flex_cbr', 4.0))
            _render_layer_summary(layers, cbr_val)

            _hr()

            # ส่งต่อ Tab 3
            total_sn = sum(
                L['layer_coeff'] * (L['thickness_cm'] / 2.54) * L['drainage_coeff']
                for L in layers)
            w18      = float(st.session_state.get('flex_w18', 0))
            mr_sub   = float(st.session_state.get('flex_subgrade_mr', mr_from_cbr(cbr_val)))

            st.markdown(
                f'<div style="background:#E8F5E9;border:1.5px solid #A5D6A7;'
                f'border-radius:8px;padding:10px 14px">'
                f'<div style="font-size:12px;font-weight:700;color:#2E7D32;'
                f'margin-bottom:6px">✅ ข้อมูลพร้อมส่ง Tab 3</div>'
                f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">'
                f'<div style="background:#FBE9E7;border-radius:7px;padding:8px;text-align:center">'
                f'<div style="font-size:10px;color:#78909C">SN_provided (preview)</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
                f'font-weight:700;color:{_AC_BD}">{total_sn:.3f}</div>'
                f'</div>'
                f'<div style="background:#E3F2FD;border-radius:7px;padding:8px;text-align:center">'
                f'<div style="font-size:10px;color:#78909C">W₁₈ (design)</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
                f'font-weight:700;color:#1565C0">{w18:,.0f}</div>'
                f'</div>'
                f'<div style="background:#FFF3CD;border-radius:7px;padding:8px;text-align:center">'
                f'<div style="font-size:10px;color:#78909C">Mr_subgrade</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
                f'font-weight:700;color:#E65100">{mr_sub:,.0f} psi</div>'
                f'</div>'
                f'</div></div>',
                unsafe_allow_html=True)
