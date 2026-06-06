"""
flex_engine.py — Flexible Pavement Design Engine
AASHTO 1993 — ไม่มี UI ทั้งหมด
พัฒนาโดย รศ.ดร.อิทธิพล มีผล · ภาควิชาครุศาสตร์โยธา · มจพ.
"""
import math
import numpy as np
from io import BytesIO
import matplotlib
try:
    matplotlib.use('Agg')
except Exception:
    pass
import matplotlib.pyplot as plt
import matplotlib.patches as patches

matplotlib.rcParams['font.family']       = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. Reliability / Zr Table
# ============================================================
ZR_TABLE = {
    50: -0.000, 60: -0.253, 70: -0.524, 75: -0.674,
    80: -0.841, 85: -1.037, 90: -1.282, 91: -1.340,
    92: -1.405, 93: -1.476, 94: -1.555, 95: -1.645,
    96: -1.751, 97: -1.881, 98: -2.054, 99: -2.327,
}

def get_zr(reliability: int) -> float:
    return ZR_TABLE.get(int(reliability), -1.282)

def mr_from_cbr(cbr: float) -> float:
    """MR (psi) จาก CBR — กรมทางหลวง"""
    return 1500.0 * cbr if cbr <= 10 else 1000.0 + 555.0 * cbr

# ============================================================
# 2. AASHTO 1993 Flexible — Core Equation
# ============================================================

def _brentq(f, a, b, xtol=1e-10, maxiter=200):
    """Brent's method root-finding (ไม่พึ่ง scipy)"""
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError("f(a) and f(b) must have different signs")
    if abs(fa) < xtol:
        return a
    if abs(fb) < xtol:
        return b
    c, fc = a, fa
    d = e = b - a
    for _ in range(maxiter):
        if fb * fc > 0:
            c, fc = a, fa
            d = e = b - a
        if abs(fc) < abs(fb):
            a, b, c = b, c, b
            fa, fb, fc = fb, fc, fb
        tol1 = 2.0 * 2.2e-16 * abs(b) + 0.5 * xtol
        m = 0.5 * (c - b)
        if abs(m) <= tol1 or fb == 0.0:
            return b
        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p = 2.0 * m * s
                q = 1.0 - s
            else:
                q = fa / fc
                r = fb / fc
                p = s * (2.0 * m * q * (q - r) - (b - a) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0:
                q = -q
            else:
                p = -p
            if 2.0 * p < min(3.0 * m * q - abs(tol1 * q), abs(e * q)):
                e, d = d, p / q
            else:
                d = m
                e = m
        else:
            d = m
            e = m
        a, fa = b, fb
        b += d if abs(d) > tol1 else (tol1 if m > 0 else -tol1)
        fb = f(b)
    return b


def aashto_flex_residual(SN: float, W18: float, Zr: float, So: float,
                          delta_psi: float, Mr: float) -> float:
    """
    AASHTO 1993 Flexible Design Equation (residual form = 0)
    log(W18) = ZR*S0 + 9.36*log(SN+1) - 0.20
             + log(ΔPSI/(4.2-1.5)) / (0.40 + 1094/(SN+1)^5.19)
             + 2.32*log(MR) - 8.07
    """
    term1 = Zr * So
    term2 = 9.36 * math.log10(SN + 1) - 0.20
    num   = math.log10(delta_psi / (4.2 - 1.5))
    den   = 0.4 + 1094.0 / ((SN + 1) ** 5.19)
    term3 = num / den
    term4 = 2.32 * math.log10(Mr) - 8.07
    return (term1 + term2 + term3 + term4) - math.log10(W18)


def calc_sn_required(W18: float, Zr: float, So: float,
                     delta_psi: float, Mr: float) -> float | None:
    """คำนวณ SN ที่ต้องการ จาก W18, Zr, So, ΔPSI, Mr"""
    def f(SN):
        return aashto_flex_residual(SN, W18, Zr, So, delta_psi, Mr)
    try:
        return round(_brentq(f, 0.01, 25.0, xtol=1e-8), 4)
    except (ValueError, RuntimeError):
        return None


def calc_w18_supported(SN: float, Zr: float, So: float,
                       delta_psi: float, Mr: float) -> float:
    """คำนวณ W18 ที่ SN ที่กำหนดรองรับได้"""
    term1 = Zr * So
    term2 = 9.36 * math.log10(SN + 1) - 0.20
    num   = math.log10(delta_psi / (4.2 - 1.5))
    den   = 0.4 + 1094.0 / ((SN + 1) ** 5.19)
    term3 = num / den
    term4 = 2.32 * math.log10(Mr) - 8.07
    return 10 ** (term1 + term2 + term3 + term4)

# ============================================================
# 3. Multilayer SN Calculation
# ============================================================

def calc_layer_results(W18: float, Zr: float, So: float,
                       delta_psi: float, subgrade_mr: float,
                       layers: list, ac_sublayers=None) -> dict:
    """
    คำนวณ SN multilayer ตาม AASHTO 1993
    layers: list of dict มี keys: material, thickness_cm, layer_coeff, drainage_coeff
    return: dict ผลลัพธ์ครบทุก layer
    """
    results = {
        'layers': [],
        'sn_values': [],
        'subgrade_mr': subgrade_mr,
        'total_sn_required': None,
        'total_sn_provided': 0.0,
        'warnings': [],
    }

    active = [l for l in layers
              if l.get('material') != 'ไม่ใช้วัสดุคัดเลือก (ใช้ดินทางทรพ)']
    if not active:
        results['warnings'].append('⚠️ ไม่มีชั้นทางที่ active')
        return results

    n = len(active)

    # ตรวจ Mr ลำดับชั้น (ชั้นบนควรมี Mr สูงกว่าชั้นล่าง)
    for i in range(n - 1):
        mr_i   = MATERIALS[active[i]['material']]['mr_psi']
        mr_i1  = MATERIALS[active[i + 1]['material']]['mr_psi']
        if mr_i < mr_i1:
            results['warnings'].append(
                f'⚠️ ชั้น {i+1} Mr={mr_i:,} psi < ชั้น {i+2} Mr={mr_i1:,} psi '
                f'— ปกติชั้นบนควร Mr สูงกว่า'
            )

    # คำนวณ SN_i required ที่แต่ละ interface
    sn_values = []
    for i in range(n):
        mr_below = (subgrade_mr if i == n - 1
                    else MATERIALS[active[i + 1]['material']]['mr_psi'])
        sn_i = calc_sn_required(W18, Zr, So, delta_psi, mr_below)
        if sn_i is None:
            results['warnings'].append(
                f'⚠️ คำนวณ SN ชั้น {i+1} ไม่ได้ — W18 อาจสูงเกินไป'
            )
        sn_values.append({'layer_index': i + 1,
                          'mr_below': mr_below,
                          'sn_required': sn_i})

    results['sn_values'] = sn_values
    results['total_sn_required'] = calc_sn_required(
        W18, Zr, So, delta_psi, subgrade_mr)

    if results['total_sn_required'] is None:
        results['warnings'].append(
            '⚠️ คำนวณ SN_required ไม่ได้ — ลองปรับ W18, R หรือ CBR')

    # สะสม SN
    cumulative_sn = 0.0
    for i, layer in enumerate(active):
        mat  = MATERIALS[layer['material']]
        a_i  = layer.get('layer_coeff',   mat['layer_coeff'])
        m_i  = layer.get('drainage_coeff', 1.0)
        sn_at_layer = (sn_values[i]['sn_required']
                       if sn_values[i]['sn_required'] is not None else 0.0)

        if a_i > 0 and m_i > 0:
            remaining         = max(0.0, sn_at_layer - cumulative_sn)
            min_thick_inch    = remaining / (a_i * m_i)
            min_thick_cm      = min_thick_inch * 2.54
        else:
            min_thick_inch = 0.0
            min_thick_cm   = 0.0

        d_cm   = float(layer['thickness_cm'])
        d_inch = d_cm / 2.54
        sn_contrib = a_i * d_inch * m_i
        cumulative_sn += sn_contrib

        results['layers'].append({
            'layer_no':              i + 1,
            'material':              layer['material'],
            'short_name':            mat['short_name'],
            'english_name':          mat.get('english_name', mat['short_name']),
            'mr_psi':                mat['mr_psi'],
            'mr_mpa':                mat['mr_mpa'],
            'a_i':                   round(a_i, 3),
            'm_i':                   round(m_i, 2),
            'sn_required_at_layer':  round(sn_at_layer, 3),
            'min_thickness_inch':    round(min_thick_inch, 2),
            'min_thickness_cm':      round(min_thick_cm,   1),
            'design_thickness_cm':   d_cm,
            'design_thickness_inch': round(d_inch, 3),
            'sn_contribution':       round(sn_contrib, 4),
            'cumulative_sn':         round(cumulative_sn, 3),
            'is_ok':                 d_cm >= min_thick_cm,
            'color':                 mat['color'],
            'ac_sublayers':          (ac_sublayers if i == 0
                                      and ac_sublayers is not None else None),
        })

    results['total_sn_provided'] = round(cumulative_sn, 3)
    return results


def check_sn(sn_required: float | None,
             sn_provided: float) -> dict:
    """ตรวจสอบ pass/fail"""
    if sn_required is None:
        return {'passed': False, 'safety_margin': 0.0,
                'message': 'คำนวณ SN_required ไม่ได้'}
    margin = round(sn_provided - sn_required, 3)
    passed = sn_provided >= sn_required
    sym    = '≥' if passed else '<'
    return {
        'passed':        passed,
        'safety_margin': margin,
        'message':       f'SN_provided ({sn_provided:.2f}) {sym} SN_required ({sn_required:.2f})',
    }

# ============================================================
# 4. Material Database — ตาม ทล. + V6
# ============================================================
MATERIALS = {
    # ── ผิวทาง ──────────────────────────────────────────────
    'ผิวทางลาดยาง AC': {
        'layer_coeff': 0.40, 'drainage_coeff': 1.0,
        'mr_psi': 362500, 'mr_mpa': 2500,
        'layer_type': 'surface', 'color': '#1C1C1C',
        'short_name': 'AC', 'english_name': 'Asphalt Concrete',
    },
    'ผิวทางลาดยาง PMA': {
        'layer_coeff': 0.40, 'drainage_coeff': 1.0,
        'mr_psi': 536500, 'mr_mpa': 3700,
        'layer_type': 'surface', 'color': '#2C2C2C',
        'short_name': 'PMA', 'english_name': 'Polymer Modified Asphalt',
    },
    # ── พื้นทาง ─────────────────────────────────────────────
    'พื้นทางหินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (Cement Treated Base)': {
        'layer_coeff': 0.18, 'drainage_coeff': 1.0,
        'mr_psi': 174000, 'mr_mpa': 1200,
        'layer_type': 'base', 'color': '#78909C',
        'short_name': 'CTB', 'english_name': 'Cement Treated Base',
    },
    'พื้นทางหินคลุกผสมซีเมนต์ UCS 24.5 ksc.': {
        'layer_coeff': 0.15, 'drainage_coeff': 1.0,
        'mr_psi': 123250, 'mr_mpa': 850,
        'layer_type': 'base', 'color': '#607D8B',
        'short_name': 'MOD.CRB', 'english_name': 'Mod.Crushed Rock Base',
    },
    'พื้นทางหินคลุก CBR 80%': {
        'layer_coeff': 0.13, 'drainage_coeff': 1.0,
        'mr_psi': 50750, 'mr_mpa': 350,
        'layer_type': 'base', 'color': '#795548',
        'short_name': 'CAB', 'english_name': 'Crushed Rock Base',
    },
    'พื้นทางดินซีเมนต์ UCS 17.5 ksc.': {
        'layer_coeff': 0.13, 'drainage_coeff': 1.0,
        'mr_psi': 50750, 'mr_mpa': 350,
        'layer_type': 'base', 'color': '#8D6E63',
        'short_name': 'SCB', 'english_name': 'Soil Cement Base',
    },
    'พื้นทางวัสดุหมุนเวียน (Recycling)': {
        'layer_coeff': 0.15, 'drainage_coeff': 1.0,
        'mr_psi': 123250, 'mr_mpa': 850,
        'layer_type': 'base', 'color': '#5D4037',
        'short_name': 'RAP', 'english_name': 'Recycled Asphalt Pavement',
    },
    # ── รองพื้นทาง ───────────────────────────────────────────
    'รองพื้นทางวัสดุมวลรวม CBR 25%': {
        'layer_coeff': 0.10, 'drainage_coeff': 1.0,
        'mr_psi': 21750, 'mr_mpa': 150,
        'layer_type': 'subbase', 'color': '#FFB74D',
        'short_name': 'GSB', 'english_name': 'Aggregate Subbase',
    },
    # ── วัสดุคัดเลือก ────────────────────────────────────────
    'วัสดุคัดเลือก ก': {
        'layer_coeff': 0.08, 'drainage_coeff': 1.0,
        'mr_psi': 14504, 'mr_mpa': 100,
        'layer_type': 'selected', 'color': '#FFF176',
        'short_name': 'SM-A', 'english_name': 'Selected Material',
    },
    # ── ไม่ใช้ ───────────────────────────────────────────────
    'ไม่ใช้วัสดุคัดเลือก (ใช้ดินทางทรพ)': {
        'layer_coeff': 0.00, 'drainage_coeff': 1.0,
        'mr_psi': 0, 'mr_mpa': 0,
        'layer_type': 'none', 'color': '#D7CCC8',
        'short_name': 'NONE', 'english_name': 'None',
    },
}

MATERIAL_NAMES = [k for k in MATERIALS if k != 'ไม่ใช้วัสดุคัดเลือก (ใช้ดินทางทรพ)']
MATERIAL_NAMES_WITH_NONE = list(MATERIALS.keys())

# ── ชื่อย่อสำหรับรายงาน ──────────────────────────────────────
SHORT_NAME_MAP = {
    'พื้นทางหินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (Cement Treated Base)':
        'หินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (CTB)',
    'พื้นทางหินคลุกผสมซีเมนต์ UCS 24.5 ksc.': 'หินคลุกผสมซีเมนต์ UCS ≥ 24.5 ksc',
    'พื้นทางหินคลุก CBR 80%':                  'หินคลุก CBR ≥ 80%',
    'พื้นทางดินซีเมนต์ UCS 17.5 ksc.':         'ดินซีเมนต์ UCS ≥ 17.5 ksc',
    'พื้นทางวัสดุหมุนเวียน (Recycling)':        'วัสดุหมุนเวียน (Recycling)',
    'รองพื้นทางวัสดุมวลรวม CBR 25%':            'รองพื้นทางวัสดุมวลรวม CBR ≥ 25%',
    'ผิวทางลาดยาง AC':                          'ผิวทางลาดยาง AC',
    'ผิวทางลาดยาง PMA':                         'ผิวทางลาดยาง PMA',
    'วัสดุคัดเลือก ก':                          'วัสดุคัดเลือก ก',
}

def short_name(mat: str) -> str:
    return SHORT_NAME_MAP.get(mat, mat)

# ============================================================
# 5. Preset Structures — ทล.
# ============================================================
PRESETS = {
    '— เลือกโครงสร้างมาตรฐาน —': None,
    'AC + CTB + GSB + SM (มาตรฐานหลัก)': {
        'description': 'ผิวทาง AC / พื้นทาง CTB / รองพื้นทาง GSB / วัสดุคัดเลือก',
        'layers': [
            {'material': 'ผิวทางลาดยาง AC', 'thickness_cm': 15.0},
            {'material': 'พื้นทางหินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (Cement Treated Base)',
             'thickness_cm': 15.0},
            {'material': 'รองพื้นทางวัสดุมวลรวม CBR 25%', 'thickness_cm': 15.0},
            {'material': 'วัสดุคัดเลือก ก', 'thickness_cm': 30.0},
        ],
    },
    'AC + MOD.CRB + GSB + SM': {
        'description': 'ผิวทาง AC / หินคลุกผสมซีเมนต์ / รองพื้นทาง GSB / วัสดุคัดเลือก',
        'layers': [
            {'material': 'ผิวทางลาดยาง AC', 'thickness_cm': 15.0},
            {'material': 'พื้นทางหินคลุกผสมซีเมนต์ UCS 24.5 ksc.', 'thickness_cm': 20.0},
            {'material': 'รองพื้นทางวัสดุมวลรวม CBR 25%', 'thickness_cm': 15.0},
            {'material': 'วัสดุคัดเลือก ก', 'thickness_cm': 30.0},
        ],
    },
    'AC + CAB + GSB + SM': {
        'description': 'ผิวทาง AC / หินคลุก CBR 80% / รองพื้นทาง GSB / วัสดุคัดเลือก',
        'layers': [
            {'material': 'ผิวทางลาดยาง AC', 'thickness_cm': 15.0},
            {'material': 'พื้นทางหินคลุก CBR 80%', 'thickness_cm': 20.0},
            {'material': 'รองพื้นทางวัสดุมวลรวม CBR 25%', 'thickness_cm': 15.0},
            {'material': 'วัสดุคัดเลือก ก', 'thickness_cm': 30.0},
        ],
    },
    'AC + SCB + GSB + SM': {
        'description': 'ผิวทาง AC / ดินซีเมนต์ / รองพื้นทาง GSB / วัสดุคัดเลือก',
        'layers': [
            {'material': 'ผิวทางลาดยาง AC', 'thickness_cm': 15.0},
            {'material': 'พื้นทางดินซีเมนต์ UCS 17.5 ksc.', 'thickness_cm': 20.0},
            {'material': 'รองพื้นทางวัสดุมวลรวม CBR 25%', 'thickness_cm': 15.0},
            {'material': 'วัสดุคัดเลือก ก', 'thickness_cm': 30.0},
        ],
    },
    'AC + CTB + GSB (ไม่ใช้ SM)': {
        'description': 'ผิวทาง AC / พื้นทาง CTB / รองพื้นทาง GSB',
        'layers': [
            {'material': 'ผิวทางลาดยาง AC', 'thickness_cm': 15.0},
            {'material': 'พื้นทางหินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (Cement Treated Base)',
             'thickness_cm': 20.0},
            {'material': 'รองพื้นทางวัสดุมวลรวม CBR 25%', 'thickness_cm': 20.0},
        ],
    },
    'PMA + CTB + GSB + SM': {
        'description': 'ผิวทาง PMA / พื้นทาง CTB / รองพื้นทาง GSB / วัสดุคัดเลือก',
        'layers': [
            {'material': 'ผิวทางลาดยาง PMA', 'thickness_cm': 15.0},
            {'material': 'พื้นทางหินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (Cement Treated Base)',
             'thickness_cm': 15.0},
            {'material': 'รองพื้นทางวัสดุมวลรวม CBR 25%', 'thickness_cm': 15.0},
            {'material': 'วัสดุคัดเลือก ก', 'thickness_cm': 30.0},
        ],
    },
    'AC + RAP + GSB + SM': {
        'description': 'ผิวทาง AC / วัสดุหมุนเวียน / รองพื้นทาง GSB / วัสดุคัดเลือก',
        'layers': [
            {'material': 'ผิวทางลาดยาง AC', 'thickness_cm': 15.0},
            {'material': 'พื้นทางวัสดุหมุนเวียน (Recycling)', 'thickness_cm': 20.0},
            {'material': 'รองพื้นทางวัสดุมวลรวม CBR 25%', 'thickness_cm': 15.0},
            {'material': 'วัสดุคัดเลือก ก', 'thickness_cm': 30.0},
        ],
    },
}

# ============================================================
# 6. Drainage Table
# ============================================================
DRAINAGE_TABLE = {
    'Excellent': {
        'description': 'ระบายน้ำดีเยี่ยม (< 2 ชม.)',
        'values': {'<1%': 1.40, '1-5%': 1.35, '5-25%': 1.30, '>25%': 1.20},
    },
    'Good': {
        'description': 'ระบายน้ำดี (1 วัน)',
        'values': {'<1%': 1.35, '1-5%': 1.25, '5-25%': 1.15, '>25%': 1.00},
    },
    'Fair': {
        'description': 'ระบายน้ำพอใช้ (1 สัปดาห์)',
        'values': {'<1%': 1.25, '1-5%': 1.15, '5-25%': 1.05, '>25%': 0.80},
    },
    'Poor': {
        'description': 'ระบายน้ำไม่ดี (1 เดือน)',
        'values': {'<1%': 1.15, '1-5%': 1.05, '5-25%': 0.80, '>25%': 0.60},
    },
    'Very Poor': {
        'description': 'ระบายน้ำไม่ดีมาก (ไม่ระบาย)',
        'values': {'<1%': 1.05, '1-5%': 0.80, '5-25%': 0.60, '>25%': 0.40},
    },
}

# ============================================================
# 7. ESAL Engine (Flexible) — LEF ตาม AASHTO 1993
# ============================================================
_TON_TO_KIP = 2.2046

_VEHICLE_AXLES = {
    'MB':  [(4,  1, 1), (11, 1, 1)],
    'HB':  [(5,  1, 1), (20, 2, 1)],
    'MT':  [(4,  1, 1), (11, 1, 1)],
    'HT':  [(5,  1, 1), (20, 2, 1)],
    'TR':  [(5,  1, 1), (20, 2, 1), (11, 1, 1), (11, 1, 1)],
    'STR': [(5,  1, 1), (20, 2, 1), (20, 2, 1)],
}


def _ealf_flex(L1_ton: float, L2: int, SN: float, pt: float) -> float:
    """
    EALF สำหรับ Flexible Pavement (AASHTO 1993 Appendix D)
    L1_ton: น้ำหนักเพลา (ตัน), L2: axle type factor,
    SN: Structural Number, pt: terminal serviceability
    """
    L1  = L1_ton * _TON_TO_KIP  # kip
    Gt  = math.log10((4.5 - pt) / (4.5 - 1.5))
    Bx  = 0.4 + 0.081 * (L1 + L2) ** 3.23 / ((SN + 1) ** 5.19 * L2 ** 3.23)
    B18 = 0.4 + 0.081 * (18 + 1) ** 3.23 / ((SN + 1) ** 5.19 * 1.0 ** 3.23)
    return 10 ** (4.79 * math.log10(L1 + L2)
                  - 4.79 * math.log10(19)
                  - 4.33 * math.log10(L2)
                  + Gt * (1 / B18 - 1 / Bx))


def compute_esal_flex(traffic_data: list, pt: float,
                      lane_factor: float, direction_factor: float,
                      SN: float) -> tuple[int, dict]:
    """
    คำนวณ W18 สะสมสำหรับ Flexible Pavement
    return: (W18_total, truck_factors)
    """
    tf = {
        code: sum(
            _ealf_flex(L1, L2, SN, pt) * cnt
            for L1, L2, cnt in axles
        )
        for code, axles in _VEHICLE_AXLES.items()
    }
    acc = sum(
        row.get(code, 0) * tf[code] * lane_factor * direction_factor * 365
        for row in traffic_data
        for code in tf
    )
    return (round(acc), tf)

# ============================================================
# 8. Visualization — Cross-section
# ============================================================
_LAYER_COLORS = {
    'ผิวทางลาดยาง AC':    '#1C1C1C',
    'ผิวทางลาดยาง PMA':   '#2C2C2C',
    'พื้นทางหินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (Cement Treated Base)': '#78909C',
    'พื้นทางหินคลุกผสมซีเมนต์ UCS 24.5 ksc.': '#607D8B',
    'พื้นทางหินคลุก CBR 80%':                  '#795548',
    'พื้นทางดินซีเมนต์ UCS 17.5 ksc.':         '#8D6E63',
    'พื้นทางวัสดุหมุนเวียน (Recycling)':        '#5D4037',
    'รองพื้นทางวัสดุมวลรวม CBR 25%':            '#FFB74D',
    'วัสดุคัดเลือก ก':                          '#FFF176',
    'ดินเดิม / Subgrade':                       '#BCAAA4',
}
_DARK_LAYERS = {'ผิวทางลาดยาง AC', 'ผิวทางลาดยาง PMA',
                'พื้นทางหินคลุกปรับปรุงคุณภาพด้วยปูนซีเมนต์ (Cement Treated Base)',
                'พื้นทางหินคลุกผสมซีเมนต์ UCS 24.5 ksc.',
                'พื้นทางวัสดุหมุนเวียน (Recycling)'}


def plot_flex_structure(layer_results: list, subgrade_cbr: float | None = None,
                        title: str = 'Flexible Pavement Structure') -> plt.Figure:
    """วาดรูปตัดขวางโครงสร้าง Flexible Pavement
    subgrade_cbr=None → ไม่แสดงชั้น Subgrade
    """
    valid = [l for l in layer_results if l.get('design_thickness_cm', 0) > 0]
    if not valid:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.text(0.5, 0.5, 'No valid layers', ha='center', va='center')
        ax.axis('off')
        return fig

    # เพิ่มชั้น subgrade ถ้าระบุ CBR
    if subgrade_cbr is not None:
        display_layers = valid + [{
            'material':             'ดินเดิม / Subgrade',
            'design_thickness_cm':  30,
            'a_i': 0, 'm_i': 1.0, 'sn_contribution': 0,
            'cumulative_sn': 0,
            'short_name': f'Subgrade (CBR={subgrade_cbr:.1f}%)',
            'mr_psi': 0, 'mr_mpa': 0,
        }]
    else:
        display_layers = valid

    total = sum(l['design_thickness_cm'] for l in display_layers)
    min_disp = max(total * 0.07, 5)
    disp = [max(l['design_thickness_cm'], min_disp) for l in display_layers]
    scale = total / sum(disp)
    disp = [d * scale for d in disp]
    tot_d = sum(disp)

    fig_h = max(5, min(10, total / 12))
    fig, ax = plt.subplots(figsize=(8, fig_h))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    w, xc = 3.5, 6
    xs_l = xc - w / 2
    y = tot_d

    for i, layer in enumerate(display_layers):
        t   = layer['design_thickness_cm']
        n   = layer['material']
        dh  = disp[i]
        yb  = y - dh
        col = _LAYER_COLORS.get(n, '#CCCCCC')
        ax.add_patch(patches.Rectangle(
            (xs_l, yb), w, dh, lw=1.5, ec='black', fc=col))

        yc  = yb + dh / 2
        tc  = 'white' if n in _DARK_LAYERS else 'black'
        fs_v = max(8, min(13, dh * 0.55))
        fs_l = max(7, min(11, dh * 0.45))

        # ชื่อย่อ (ซ้าย)
        sn_label = (layer.get('short_name') or
                    MATERIALS.get(n, {}).get('short_name', n[:8]))
        ax.text(xs_l - 0.3, yc, sn_label,
                ha='right', va='center', fontsize=fs_l, fontweight='bold')

        # ความหนา (กลาง)
        ax.text(xc, yc, f'{t:.0f} cm',
                ha='center', va='center', fontsize=fs_v,
                fontweight='bold', color=tc)

        # SN contribution (ขวา) — ไม่แสดงสำหรับ subgrade
        if layer.get('sn_contribution', 0) > 0:
            ax.text(xs_l + w + 0.3, yc,
                    f'ΔSN = {layer["sn_contribution"]:.3f}',
                    ha='left', va='center', fontsize=max(7, fs_l - 1),
                    color='#1565C0')
        elif n == 'ดินเดิม / Subgrade':
            ax.text(xs_l + w + 0.3, yc,
                    f'CBR = {subgrade_cbr:.1f}%',
                    ha='left', va='center', fontsize=max(7, fs_l - 1),
                    color='#5D4037')
        y = yb

    # arrow total (ไม่รวม subgrade)
    valid_total = sum(l['design_thickness_cm'] for l in valid)
    y_top = tot_d
    y_bot = tot_d - sum(disp[:len(valid)])
    ax.annotate('', xy=(xs_l + w + 3.5, y_bot),
                xytext=(xs_l + w + 3.5, y_top),
                arrowprops=dict(arrowstyle='<->', color='red', lw=2))
    ax.text(xs_l + w + 4.0, (y_top + y_bot) / 2,
            f'รวม\n{valid_total:.0f} cm',
            ha='left', va='center', fontsize=11,
            color='red', fontweight='bold')

    mg = total * 0.06
    ax.set_xlim(0, 14)
    ax.set_ylim(-mg, tot_d + mg)
    ax.axis('off')
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
    plt.tight_layout()
    return fig


def plot_sensitivity_cbr(W18: float, Zr: float, So: float,
                         delta_psi: float, current_cbr: float) -> plt.Figure:
    """Sensitivity: SN required vs CBR"""
    cbr_range = np.linspace(2, 20, 60)
    sn_vals   = []
    for cbr in cbr_range:
        mr  = mr_from_cbr(cbr)
        sn  = calc_sn_required(W18, Zr, So, delta_psi, mr)
        sn_vals.append(sn if sn else np.nan)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(cbr_range, sn_vals, 'b-', lw=2.5, label='SN required')

    c_mr = mr_from_cbr(current_cbr)
    c_sn = calc_sn_required(W18, Zr, So, delta_psi, c_mr)
    if c_sn:
        ax.plot(current_cbr, c_sn, 'ro', ms=10,
                label=f'CBR={current_cbr:.1f}%, SN={c_sn:.2f}')
        ax.annotate(f'CBR={current_cbr:.1f}%\nSN={c_sn:.2f}',
                    xy=(current_cbr, c_sn),
                    xytext=(current_cbr + 1.5, c_sn + 0.3),
                    fontsize=9, color='red',
                    arrowprops=dict(arrowstyle='->', color='red', lw=1.2))

    ax.set_xlabel('CBR (%)', fontsize=11)
    ax.set_ylabel('SN Required', fontsize=11)
    ax.set_title('Sensitivity: SN Required vs CBR', fontsize=11, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=2)
    plt.tight_layout()
    return fig


def plot_sensitivity_w18(Zr: float, So: float, delta_psi: float,
                         Mr: float, current_w18: float) -> plt.Figure:
    """Sensitivity: SN required vs W18"""
    w18_range = np.logspace(5, 8.5, 60)
    sn_vals   = [calc_sn_required(w, Zr, So, delta_psi, Mr) or np.nan
                 for w in w18_range]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.semilogx(w18_range, sn_vals, 'g-', lw=2.5, label='SN required')

    c_sn = calc_sn_required(current_w18, Zr, So, delta_psi, Mr)
    if c_sn:
        ax.semilogx(current_w18, c_sn, 'ro', ms=10,
                    label=f'W18={current_w18/1e6:.2f}M, SN={c_sn:.2f}')
        ax.annotate(f'W18={current_w18/1e6:.2f}M\nSN={c_sn:.2f}',
                    xy=(current_w18, c_sn),
                    xytext=(current_w18 * 0.15, c_sn + 0.4),
                    fontsize=9, color='red',
                    arrowprops=dict(arrowstyle='->', color='red', lw=1.2))

    ax.set_xlabel('W18 (ESALs)', fontsize=11)
    ax.set_ylabel('SN Required', fontsize=11)
    ax.set_title('Sensitivity: SN Required vs W18', fontsize=11, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def fig_to_bytes(fig: plt.Figure) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    return buf.read()

# ============================================================
# 9. W18–SN Mapping Table (สำหรับ JSON mode)
# ============================================================

# SN ที่ใช้คำนวณ mapping — ครอบคลุมช่วง Flexible จริง
_SN_GRID = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5,
            6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0]


def compute_w18_sn_table(traffic_data: list, pt: float,
                         lane_factor: float, direction_factor: float,
                         sn_grid: list | None = None) -> list[dict]:
    """
    คำนวณ W18 ที่ SN แต่ละค่าใน sn_grid
    return: list of {'SN': float, 'W18': int}
    """
    grid = sn_grid if sn_grid is not None else _SN_GRID
    rows = []
    for sn in grid:
        w18, _ = compute_esal_flex(traffic_data, pt, lane_factor,
                                   direction_factor, SN=sn)
        rows.append({'SN': sn, 'W18': w18})
    return rows
