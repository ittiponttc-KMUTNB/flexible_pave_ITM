"""
flex_tab2.py — Tab 2: Design (Subgrade + Layers + Results real-time)
Flexible Pavement Design V1 · AASHTO 1993
Layout: ซ้าย 60% = inputs | ขวา 40% = summary + cross-section
"""
import streamlit as st
from io import BytesIO
from flex_engine import (
    mr_from_cbr, get_zr, calc_layer_results, check_sn,
    plot_flex_structure, fig_to_bytes,
    MATERIALS, MATERIAL_NAMES, DRAINAGE_TABLE,
)

_AC_BD  = '#BF360C'
_AC_BDL = '#FFAB91'

# ============================================================
# UI Helpers
# ============================================================
def _card_title(text, color=_AC_BD, border=_AC_BDL):
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{color};'
        f'padding:2px 0 6px;border-bottom:2px solid {border};'
        f'margin-bottom:10px">{text}</div>', unsafe_allow_html=True)

def _hr(color='#FFCCBC'):
    st.markdown(
        f'<hr style="border:none;border-top:1px solid {color};margin:6px 0">',
        unsafe_allow_html=True)

def _badge(text, bg, color):
    return (f'<span style="background:{bg};color:{color};border-radius:4px;'
            f'padding:2px 8px;font-size:11px;font-weight:600;'
            f'font-family:IBM Plex Mono,monospace">{text}</span>')

# ============================================================
# Session State Init
# ============================================================
_DEFAULT_LAYERS = [
    {'material': 'ผิวทางลาดยาง AC',
     'thickness_cm': 15.0, 'layer_coeff': 0.40,
     'drainage_coeff': 1.0, 'override_ai': False,
     'ac_sub': False, 'wearing_cm': 5.0, 'binder_cm': 5.0, 'base_cm': 5.0},
    {'material': 'พื้นทางหินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (Cement Treated Base)',
     'thickness_cm': 15.0, 'layer_coeff': 0.18,
     'drainage_coeff': 1.0, 'override_ai': False,
     'ac_sub': False, 'wearing_cm': 0.0, 'binder_cm': 0.0, 'base_cm': 0.0},
    {'material': 'รองพื้นทางวัสดุมวลรวม CBR 25%',
     'thickness_cm': 15.0, 'layer_coeff': 0.10,
     'drainage_coeff': 1.0, 'override_ai': False,
     'ac_sub': False, 'wearing_cm': 0.0, 'binder_cm': 0.0, 'base_cm': 0.0},
    {'material': 'วัสดุคัดเลือก ก',
     'thickness_cm': 30.0, 'layer_coeff': 0.08,
     'drainage_coeff': 1.0, 'override_ai': False,
     'ac_sub': False, 'wearing_cm': 0.0, 'binder_cm': 0.0, 'base_cm': 0.0},
]

def _init_ss():
    if 'flex_layers' not in st.session_state:
        import copy
        st.session_state['flex_layers'] = copy.deepcopy(_DEFAULT_LAYERS)
    if 'flex_cbr' not in st.session_state:
        st.session_state['flex_cbr'] = 4.0
    if 'flex_subgrade_mr' not in st.session_state:
        st.session_state['flex_subgrade_mr'] = mr_from_cbr(4.0)

def _layer_base(mat):
    return {
        'material': mat,
        'thickness_cm': 15.0,
        'layer_coeff': MATERIALS[mat]['layer_coeff'],
        'drainage_coeff': 1.0,
        'override_ai': False,
        'ac_sub': False,
        'wearing_cm': 5.0, 'binder_cm': 5.0, 'base_cm': 5.0,
    }

# ============================================================
# Drainage helper
# ============================================================
def _get_mi(quality, saturation):
    return DRAINAGE_TABLE.get(quality, {}).get('values', {}).get(saturation, 1.0)

# ============================================================
# Left panel — Layer Table
# ============================================================
def _render_layers():
    import copy

    # ── Slider จำนวนชั้น ──────────────────────────────────
    n_target = st.slider(
        'จำนวนชั้นทาง', min_value=1, max_value=5,
        value=len(st.session_state['flex_layers']),
        key='flex_n_layers',
        help='เลื่อนเพื่อเพิ่ม/ลดจำนวนชั้น')

    layers = st.session_state['flex_layers']

    # ปรับ list ให้ตรงกับ slider
    while len(layers) < n_target:
        defaults = [
            'ผิวทางลาดยาง AC',
            'พื้นทางหินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (Cement Treated Base)',
            'รองพื้นทางวัสดุมวลรวม CBR 25%',
            'วัสดุคัดเลือก ก',
            'รองพื้นทางวัสดุมวลรวม CBR 25%',
        ]
        mat = defaults[len(layers)] if len(layers) < len(defaults) else 'รองพื้นทางวัสดุมวลรวม CBR 25%'
        layers.append(_layer_base(mat))
    while len(layers) > n_target:
        layers.pop()

    st.session_state['flex_layers'] = layers

    # ── Column header ─────────────────────────────────────
    st.markdown(
        '<div style="display:grid;grid-template-columns:0.35fr 3.8fr 1.0fr 1.1fr 1.1fr 1.2fr;'
        'gap:8px;padding:4px 8px 4px 8px;background:#F5F5F5;border-radius:6px;'
        'margin-bottom:4px;font-size:11px;font-weight:600;color:#78909C">'
        '<div></div>'
        '<div>วัสดุ</div>'
        '<div style="text-align:center">D (cm)</div>'
        '<div style="text-align:center">aᵢ</div>'
        '<div style="text-align:center">mᵢ</div>'
        '<div style="text-align:center"></div>'
        '</div>',
        unsafe_allow_html=True)

    # ── Layer cards ────────────────────────────────────────
    for i, L in enumerate(layers):
        mat      = L['material']
        mat_data = MATERIALS.get(mat, {})
        ltype    = mat_data.get('layer_type', 'base')
        is_ac    = ltype == 'surface'
        ai_def   = mat_data.get('layer_coeff', 0.10)

        with st.container(border=True):
            # ── single row: เลขชั้น | วัสดุ | หนา | a_i | m_i | [AC sublayer] ──
            h1, h2, h3, h4, h5, h6 = st.columns([0.35, 3.8, 1.0, 1.1, 1.1, 1.2])
            with h1:
                st.markdown(
                    f'<div style="font-size:12px;font-weight:700;color:{_AC_BD};'
                    f'padding-top:6px;text-align:center">{i+1}</div>',
                    unsafe_allow_html=True)
            with h2:
                new_mat = st.selectbox(
                    'วัสดุ', options=MATERIAL_NAMES,
                    index=MATERIAL_NAMES.index(mat) if mat in MATERIAL_NAMES else 0,
                    key=f'lmat_{i}', label_visibility='collapsed')
                if new_mat != mat:
                    L['material']    = new_mat
                    L['layer_coeff'] = MATERIALS[new_mat]['layer_coeff']
                    st.rerun()
            with h3:
                new_t = st.number_input(
                    'cm', min_value=1.0, max_value=200.0,
                    value=float(L['thickness_cm']),
                    step=1.0, format='%.0f',
                    key=f'lt_{i}', label_visibility='collapsed')
                L['thickness_cm'] = new_t
            with h4:
                # a_i — input ตรง, default จาก database, user แก้ได้
                new_ai = st.number_input(
                    'a_i', min_value=0.01, max_value=0.60,
                    value=float(L.get('layer_coeff', ai_def)),
                    step=0.005, format='%.3f',
                    key=f'lai_{i}', label_visibility='collapsed')
                L['layer_coeff'] = new_ai
            with h5:
                # m_i — input ตรง, max ต่างกันตาม layer type
                mi_max = 1.1 if is_ac else 1.4
                mi_val = min(float(L.get('drainage_coeff', 1.0)), mi_max)
                new_mi = st.number_input(
                    f'm_i', min_value=0.40, max_value=mi_max,
                    value=mi_val, step=0.05, format='%.2f',
                    key=f'lmi_{i}', label_visibility='collapsed')
                L['drainage_coeff'] = new_mi
            with h6:
                if is_ac:
                    ac_sub = st.checkbox(
                        'แบ่ง AC', value=L.get('ac_sub', False),
                        key=f'lacsub_{i}')
                    L['ac_sub'] = ac_sub

            # ── AC sublayer inputs ────────────────────────
            if is_ac and L.get('ac_sub'):
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    w = st.number_input('Wearing (cm)', 1.0, 50.0,
                                        float(L.get('wearing_cm', 5.0)),
                                        1.0, format='%.0f', key=f'lwear_{i}')
                    L['wearing_cm'] = w
                with sc2:
                    b = st.number_input('Binder (cm)', 0.0, 50.0,
                                        float(L.get('binder_cm', 5.0)),
                                        1.0, format='%.0f', key=f'lbind_{i}')
                    L['binder_cm'] = b
                with sc3:
                    base_cm = st.number_input('Base (cm)', 0.0, 50.0,
                                           float(L.get('base_cm', 5.0)),
                                           1.0, format='%.0f', key=f'lbase_{i}')
                    L['base_cm'] = base_cm
                total_ac = w + b + base_cm
                L['thickness_cm'] = total_ac
                st.markdown(
                    f'<div style="font-size:11px;color:#BF360C;font-family:'
                    f'IBM Plex Mono,monospace">W+B+Base = {w:.0f}+{b:.0f}+'
                    f'{base_cm:.0f} = {total_ac:.0f} cm</div>',
                    unsafe_allow_html=True)

            # ── badge row + pass/fail per layer ───────────
            ai   = L['layer_coeff']
            mi   = L['drainage_coeff']
            t    = L['thickness_cm']
            dsn  = round(ai * (t / 2.54) * mi, 3)
            mr_l = mat_data.get('mr_psi', 0)
            # pass/fail คำนวณจาก session state ถ้ามีผลแล้ว
            pf_html = ''
            calc_res = st.session_state.get('flex_calc_results')
            if calc_res and i < len(calc_res.get('layers', [])):
                lr = calc_res['layers'][i]
                d_min = lr['min_thickness_cm']
                d_des = lr['design_thickness_cm']
                if lr['is_ok']:
                    pf_html = _badge(
                        f'✅ ผ่าน (Dmin={d_min:.1f} ซม.)',
                        '#E8F5E9', '#1B5E20')
                else:
                    short = d_min - d_des
                    pf_html = _badge(
                        f'⚠️ ต้องการ Dmin={d_min:.1f} ซม. (กรอกอยู่ {d_des:.0f} ซม.)',
                        '#FFF8E1', '#E65100')
            st.markdown(
                f'{_badge(f"a_i={ai:.3f}", "#E3F2FD", "#0D47A1")}&nbsp;'
                f'{_badge(f"m_i={mi:.2f}", "#E8F5E9", "#1B5E20")}&nbsp;'
                f'{_badge(f"D={t:.0f} cm", "#FFF3CD", "#E65100")}&nbsp;'
                f'{_badge(f"ΔSN={dsn:.3f}", "#FBE9E7", "#BF360C")}&nbsp;'
                f'{_badge(f"Mr={mr_l:,} psi", "#F3E5F5", "#4A148C")}'
                + (f'&nbsp;&nbsp;{pf_html}' if pf_html else ''),
                unsafe_allow_html=True)

        layers[i] = L

    st.session_state['flex_layers'] = layers

# ============================================================
# Right panel — calculate + summary + cross-section
# ============================================================
def _calc_and_render_right(layers, cbr, W18, Zr, So, delta_psi):
    mr_sub = mr_from_cbr(cbr)

    # ── คำนวณ ──────────────────────────────────────────────
    if not layers or W18 <= 0:
        st.info('กรอกข้อมูลครบแล้วจะแสดงผลที่นี่')
        return

    res = calc_layer_results(W18, Zr, So, delta_psi, mr_sub, layers)
    chk = check_sn(res['total_sn_required'], res['total_sn_provided'])

    # ── warnings ───────────────────────────────────────────
    for w in res['warnings']:
        st.warning(w)

    # ── PASS / FAIL banner ─────────────────────────────────
    if chk['passed']:
        st.markdown(
            f'<div style="background:#E8F5E9;border:2px solid #2E7D32;'
            f'border-radius:8px;padding:10px 14px;text-align:center;margin-bottom:8px">'
            f'<div style="font-size:15px;font-weight:700;color:#2E7D32">✅ PASS</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:12px;color:#2E7D32">'
            f'SN_provided ({res["total_sn_provided"]:.3f}) ≥ '
            f'SN_required ({res["total_sn_required"]:.3f})</div>'
            f'<div style="font-size:11px;color:#388E3C">margin = '
            f'+{chk["safety_margin"]:.3f}</div>'
            f'</div>', unsafe_allow_html=True)
    else:
        sn_req = res['total_sn_required'] or 0
        st.markdown(
            f'<div style="background:#FFEBEE;border:2px solid #C62828;'
            f'border-radius:8px;padding:10px 14px;text-align:center;margin-bottom:8px">'
            f'<div style="font-size:15px;font-weight:700;color:#C62828">❌ FAIL</div>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:12px;color:#C62828">'
            f'SN_provided ({res["total_sn_provided"]:.3f}) &lt; '
            f'SN_required ({sn_req:.3f})</div>'
            f'<div style="font-size:11px;color:#C62828">ขาด = '
            f'{abs(chk["safety_margin"]):.3f}</div>'
            f'</div>', unsafe_allow_html=True)

    # ── SN summary table ───────────────────────────────────
    rows_html = ''
    for L in res['layers']:
        ok_icon = '✅' if L['is_ok'] else '⚠️'
        rows_html += (
            f'<tr>'
            f'<td style="text-align:center">{L["layer_no"]}</td>'
            f'<td>{L["short_name"]}</td>'
            f'<td style="text-align:right;font-family:IBM Plex Mono,monospace">'
            f'{L["design_thickness_cm"]:.0f}</td>'
            f'<td style="text-align:right;font-family:IBM Plex Mono,monospace;'
            f'color:#BF360C">{L["sn_contribution"]:.3f}</td>'
            f'<td style="text-align:right;font-family:IBM Plex Mono,monospace">'
            f'{L["cumulative_sn"]:.3f}</td>'
            f'<td style="text-align:center">{ok_icon}</td>'
            f'</tr>'
        )
    sn_prov = res['total_sn_provided']
    sn_req  = res['total_sn_required'] or 0
    total_t = sum(L['design_thickness_cm'] for L in res['layers'])
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:#BF360C;color:white">'
        f'<th style="padding:4px 6px">#</th>'
        f'<th style="padding:4px 6px;text-align:left">วัสดุ</th>'
        f'<th style="padding:4px 6px;text-align:right">cm</th>'
        f'<th style="padding:4px 6px;text-align:right">ΔSN</th>'
        f'<th style="padding:4px 6px;text-align:right">ΣSN</th>'
        f'<th style="padding:4px 6px">ok?</th>'
        f'</tr></thead>'
        f'<tbody style="background:white">{rows_html}</tbody>'
        f'<tfoot><tr style="background:#FFF3CD;font-weight:700">'
        f'<td colspan="2" style="padding:4px 6px">รวม</td>'
        f'<td style="padding:4px 6px;text-align:right;font-family:IBM Plex Mono,monospace">'
        f'{total_t:.0f} cm</td>'
        f'<td colspan="2" style="padding:4px 6px;text-align:right;'
        f'font-family:IBM Plex Mono,monospace;color:#BF360C">'
        f'SN = {sn_prov:.3f} / {sn_req:.3f}</td>'
        f'<td></td></tr></tfoot>'
        f'</table>',
        unsafe_allow_html=True)

    _hr()

    # ── cross-section ──────────────────────────────────────
    try:
        fig = plot_flex_structure(
            res['layers'], subgrade_cbr=None,
            title=st.session_state.get('flex_project_name', '') or 'Flexible Pavement')
        buf = fig_to_bytes(fig)
        import matplotlib.pyplot as plt
        plt.close(fig)
        st.image(buf, use_container_width=True)
    except Exception as e:
        st.caption(f'ไม่สามารถแสดงรูปตัดขวาง: {e}')

    # ── บันทึกผลลัพธ์ → Tab 3 (Report) ──────────────────
    st.session_state['flex_calc_results'] = res
    st.session_state['flex_design_check'] = chk

# ============================================================
# Main
# ============================================================
def render_flex_tab2():
    _init_ss()

    # ── พารามิเตอร์จาก Tab 1 ──────────────────────────────
    R         = int(st.session_state.get('flex_reliability', 90))
    So        = float(st.session_state.get('flex_so', 0.45))
    p0        = float(st.session_state.get('flex_p0', 4.2))
    pt        = float(st.session_state.get('flex_pt', 2.5))
    Zr        = get_zr(R)
    delta_psi = p0 - pt

    # ── W18 selector ──────────────────────────────────────
    ed       = st.session_state.get('flex_esal_data')
    sn_tbl   = ed.get('sn_table', []) if ed else []
    w18_mode = st.session_state.get('flex_w18_mode', 'manual')

    if sn_tbl and w18_mode == 'json':
        # JSON mode: มี sn_table → ให้เลือก SN
        options     = [f"SN {r['SN']:.1f}  →  W₁₈ = {r['W18']:,.0f}" for r in sn_tbl]
        sel_key     = 'flex_w18_sn_sel'
        saved_sel   = st.session_state.get(sel_key, options[0])
        sel_idx     = options.index(saved_sel) if saved_sel in options else 0
        with st.container(border=True):
            st.markdown(
                '<div style="font-size:12px;font-weight:700;color:#BF360C;'
                'margin-bottom:6px">📌 เลือก W₁₈ จาก SN (Tab 1)</div>',
                unsafe_allow_html=True)
            chosen = st.radio(
                'เลือก W₁₈',
                options=options,
                index=sel_idx,
                key=sel_key,
                horizontal=True,
                label_visibility='collapsed')
            chosen_idx = options.index(chosen)
            W18 = float(sn_tbl[chosen_idx]['W18'])
            st.session_state['flex_w18'] = W18
    else:
        W18 = float(st.session_state.get('flex_w18', 0))

    if W18 <= 0:
        st.warning('⚠️ กรุณากรอก W₁₈ ใน Tab 1 ก่อน')
        return

    # ── status bar ─────────────────────────────────────────
    st.markdown(
        f'<div style="background:#F3E5F5;border:1px solid #CE93D8;'
        f'border-radius:7px;padding:6px 14px;font-size:12px;margin-bottom:10px">'
        f'W₁₈ = <b style="font-family:IBM Plex Mono,monospace;color:#6A1B9A">'
        f'{W18:,.0f}</b>'
        f'&nbsp;|&nbsp; R = <b style="color:#6A1B9A">{R}%</b>'
        f'&nbsp;|&nbsp; Zr = <b style="font-family:IBM Plex Mono,monospace;'
        f'color:#6A1B9A">{Zr:.3f}</b>'
        f'&nbsp;|&nbsp; ΔPSI = <b style="font-family:IBM Plex Mono,monospace;'
        f'color:#6A1B9A">{delta_psi:.1f}</b>'
        f'&nbsp;|&nbsp; S₀ = <b style="font-family:IBM Plex Mono,monospace;'
        f'color:#6A1B9A">{So:.2f}</b>'
        f'</div>', unsafe_allow_html=True)

    # ── 2 columns layout ───────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        # Subgrade
        with st.container(border=True):
            _card_title('🌍 Subgrade')
            c1, c2, c3 = st.columns(3)
            with c1:
                cbr = st.number_input(
                    'CBR (%)', 1.0, 30.0,
                    float(st.session_state.get('flex_cbr', 4.0)),
                    0.5, format='%.1f', key='flex_cbr')
            with c2:
                mr = mr_from_cbr(cbr)
                st.markdown(
                    f'<div style="background:#FBE9E7;border-radius:7px;'
                    f'padding:7px;text-align:center;margin-top:2px">'
                    f'<div style="font-size:10px;color:#78909C">Mr (psi)</div>'
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
                    f'font-weight:700;color:{_AC_BD}">{mr:,.0f}</div></div>',
                    unsafe_allow_html=True)
            with c3:
                st.markdown(
                    f'<div style="background:#E3F2FD;border-radius:7px;'
                    f'padding:7px;text-align:center;margin-top:2px">'
                    f'<div style="font-size:10px;color:#78909C">Mr (MPa)</div>'
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:18px;'
                    f'font-weight:700;color:#1565C0">{mr*0.006895:.1f}</div></div>',
                    unsafe_allow_html=True)
            st.session_state['flex_subgrade_mr'] = mr

        # Layers
        with st.container(border=True):
            _card_title('🏗️ ชั้นทาง')
            _render_layers()

    with right:
        with st.container(border=True):
            _card_title('📊 ผลการออกแบบ')
            _calc_and_render_right(
                st.session_state['flex_layers'],
                float(st.session_state.get('flex_cbr', 4.0)),
                W18, Zr, So, delta_psi)
