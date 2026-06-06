"""
flex_app.py — Flexible Pavement Design V1
AASHTO 1993 — มาตรฐานกรมทางหลวง
พัฒนาโดย รศ.ดร.อิทธิพล มีผล · ภาควิชาครุศาสตร์โยธา · มจพ.

Run: streamlit run flex_app.py
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from flex_tab1 import render_flex_tab1
from flex_tab2 import render_flex_tab2

# ============================================================
# CSS — Theme เดียวกับ Rigid Pavement (app.py)
# เพิ่ม accent สีส้ม (#E65100) สำหรับ Flexible
# ============================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Sarabun:wght@300;400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #EEF2F7 !important;
    font-family: 'Sarabun', sans-serif;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { padding-top: 0.5rem; }

/* ── Header ── */
.fp-header {
    background: #BF360C;
    border-radius: 10px;
    padding: 14px 20px 10px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.fp-header-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 15px; color: #FFFFFF;
    font-weight: 600; letter-spacing: 0.05em;
}
.fp-header-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; color: #FFCCBC; margin-top: 3px;
}
.fp-badge {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 6px; padding: 4px 12px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; color: #FFFFFF;
}

/* ── Cards ── */
.fp-card {
    background: #FFF8E1;
    border: 1px solid #FFECB3;
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 6px;
}
.fp-card-title {
    font-size: 13px; font-weight: 600; color: #BF360C;
    margin-bottom: 10px; padding-bottom: 6px;
    border-bottom: 1px solid #FFECB3;
}

/* ── Metrics ── */
.fp-metric {
    background: #FFF3CD;
    border: 1px solid #FFECB3;
    border-radius: 8px;
    padding: 8px 10px; text-align: center;
}
.fp-metric-label { font-size: 11px; color: #90A4AE; margin-bottom: 3px; }
.fp-metric-val {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 18px; font-weight: 600; color: #BF360C;
}

/* ── Status ── */
.fp-status-ok {
    background: #E8F5E9; border: 1px solid #A5D6A7;
    border-radius: 8px; padding: 7px 12px;
    font-size: 13px; color: #2E7D32; font-weight: 600;
}
.fp-status-fail {
    background: #FFEBEE; border: 1px solid #EF9A9A;
    border-radius: 8px; padding: 7px 12px;
    font-size: 13px; color: #C62828; font-weight: 600;
}
.fp-status-info {
    background: #FBE9E7; border: 1px solid #FFAB91;
    border-radius: 8px; padding: 7px 12px;
    font-size: 13px; color: #BF360C;
}

/* ── Tabs ── */
div[data-testid="stTabs"] button {
    font-weight: 600 !important; color: #546E7A !important;
    font-size: 13px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #BF360C !important;
    border-bottom: 3px solid #BF360C !important;
}

/* ── Section label ── */
.fp-section-label {
    font-size: 11px; font-weight: 600; color: #90A4AE;
    letter-spacing: 0.07em; text-transform: uppercase;
    margin-bottom: 6px; margin-top: 8px;
}

/* ── Toggle badge ── */
.fp-toggle-manual {
    display:inline-block;
    background:#FBE9E7;border:1.5px solid #BF360C;
    border-radius:20px;padding:2px 12px;
    font-size:12px;font-weight:700;color:#BF360C;
    margin-bottom:6px;
}
.fp-toggle-json {
    display:inline-block;
    background:#E8F5E9;border:1.5px solid #2E7D32;
    border-radius:20px;padding:2px 12px;
    font-size:12px;font-weight:700;color:#2E7D32;
    margin-bottom:6px;
}
</style>
"""

# ============================================================
# SESSION STATE DEFAULTS
# ============================================================
_DEFAULTS = {
    # project
    'flex_project_name': '',
    # Tab 1
    'flex_w18_mode':      'manual',   # 'manual' | 'json'
    'flex_w18':           1_000_000.0,
    'flex_reliability':   90,
    'flex_so':            0.45,
    'flex_p0':            4.2,
    'flex_pt':            2.5,
    'flex_esal_data':     None,
    'flex_esal_file_id':  None,
    # Tab 2
    'flex_cbr':           4.0,
    # Tab 3 (ใส่ default ไว้ก่อน)
    'flex_calc_results':  None,
    'flex_design_check':  None,
}

# ============================================================
# MAIN
# ============================================================
def main():
    st.set_page_config(
        page_title='Flexible Pavement Design V1 — AASHTO 1993',
        page_icon='🛤️',
        layout='wide',
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Session State Init ─────────────────────────────────
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Header ────────────────────────────────────────────
    proj = st.session_state.get('flex_project_name', '') or '— ยังไม่ระบุโครงการ'
    st.markdown(f'''
    <div class="fp-header">
        <div>
            <div class="fp-header-title">🛤️ Flexible Pavement Design — AASHTO 1993</div>
            <div class="fp-header-sub">ภาควิชาครุศาสตร์โยธา · มจพ. · Version 1.0</div>
        </div>
        <div class="fp-badge">📁 {proj}</div>
    </div>''', unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        '🚦 Tab 1 — Traffic & W18',
        '🌍 Tab 2 — Subgrade & Layers',
        '🏗️ Tab 3 — Design',
        '📄 Tab 4 — Report',
    ])

    with tab1:
        render_flex_tab1()

    with tab2:
        render_flex_tab2()

    with tab3:
        st.info('Tab 3 — Design (กำลังพัฒนา)')

    with tab4:
        st.info('Tab 4 — Report (กำลังพัฒนา)')

    st.markdown('---')
    st.caption('พัฒนาโดย รศ.ดร.อิทธิพล มีผล · ภาควิชาครุศาสตร์โยธา · มจพ.')


if __name__ == '__main__':
    main()
