import streamlit as st
import pymongo
import certifi
import pandas as pd
import numpy as np
import os
import math
from collections import Counter
from datetime import datetime, timezone
import plotly.graph_objects as go

# ====================================================================
#  1. ตั้งค่าหน้าจอโปรแกรมเป็นแบบกว้าง (Wide Layout)
# ====================================================================
st.set_page_config(
    page_title="ระบบคำนวณและวิเคราะห์สถิติหวย",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================================================================
#  2. Modern Minimal Theme - CSS Custom
# ====================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans Thai', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* หัวเรื่องหลัก */
    .main-title {
        font-size: 36px;
        font-weight: 700;
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 50%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    }

    .main-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 15px;
        margin-bottom: 32px;
        font-weight: 400;
    }

    /* KPI Cards */
    .kpi-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px 24px;
        height: 100%;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }

    .kpi-card:hover {
        border-color: #6366f1;
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.08);
        transform: translateY(-2px);
    }

    .kpi-label {
        font-size: 13px;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 8px;
        text-transform: none;
        letter-spacing: 0;
    }

    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
        margin-bottom: 4px;
    }

    .kpi-sub {
        font-size: 12px;
        color: #94a3b8;
        font-weight: 400;
    }

    .kpi-accent {
        color: #6366f1 !important;
    }

    /* Chart Container */
    .chart-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
    }

    .chart-title {
        font-size: 17px;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 4px;
    }

    .chart-subtitle {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 16px;
    }

    /* Section Headers */
    .section-header {
        font-size: 22px;
        font-weight: 600;
        color: #0f172a;
        margin: 24px 0 16px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* Consensus Highlight Card */
    .consensus-card {
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 50%, #8b5cf6 100%);
        border-radius: 20px;
        padding: 28px 32px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.2);
    }

    .consensus-title {
        font-size: 14px;
        font-weight: 500;
        opacity: 0.85;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }

    .consensus-numbers {
        font-size: 36px;
        font-weight: 700;
        margin: 12px 0;
        letter-spacing: -0.5px;
    }

    .consensus-desc {
        font-size: 13px;
        opacity: 0.9;
        font-weight: 400;
        line-height: 1.6;
    }

    /* Model Card (สำหรับ 7 โมเดล) */
    .model-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 20px;
        height: 100%;
        transition: all 0.2s ease;
    }

    .model-card:hover {
        border-color: var(--accent, #6366f1);
        box-shadow: 0 4px 16px rgba(0,0,0,0.04);
    }

    .model-icon {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        margin-bottom: 12px;
    }

    .model-title {
        font-size: 15px;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 6px;
    }

    .model-desc {
        font-size: 12px;
        color: #64748b;
        margin-bottom: 12px;
        line-height: 1.5;
        min-height: 36px;
    }

    .model-result {
        font-size: 16px;
        font-weight: 600;
        color: #4f46e5;
        padding-top: 8px;
        border-top: 1px solid #f1f5f9;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #f1f5f9;
        padding: 4px;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        color: #64748b;
    }

    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #4f46e5 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }

    /* Disclaimer Box */
    .warning-box {
        background: #fffbeb;
        border-left: 4px solid #f59e0b;
        border-radius: 10px;
        padding: 14px 18px;
        font-size: 13px;
        color: #78350f;
        margin: 16px 0;
        line-height: 1.6;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

</style>
""", unsafe_allow_html=True)

# ====================================================================
#  3. เชื่อมต่อฐานข้อมูล MongoDB
# ====================================================================
MONGO_URI = st.secrets.get("MONGO_URI") if hasattr(st, "secrets") else None
if not MONGO_URI:
    MONGO_URI = os.environ.get("MONGO_URI")

if not MONGO_URI:
    st.error("❌ ไม่พบ MONGO_URI กรุณาตั้งค่า Secrets ใน Streamlit Cloud")
    st.stop()


@st.cache_resource
def get_database_client():
    return pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())


# ====================================================================
#  4. ค่าคงที่และฟังก์ชันช่วย
# ====================================================================
THAI_MONTHS_ORDER = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]
THAI_MONTH_TO_NUM = {name: idx + 1 for idx, name in enumerate(THAI_MONTHS_ORDER)}

# ✨ Theme Constants (Modern Minimal)
COLOR_PRIMARY = "#4f46e5"      # indigo-600
COLOR_PRIMARY_LIGHT = "#818cf8"  # indigo-400
COLOR_SECONDARY = "#06b6d4"     # cyan-500
COLOR_ACCENT = "#8b5cf6"        # violet-500
COLOR_SUCCESS = "#10b981"       # emerald-500
COLOR_TEXT = "#0f172a"          # slate-900
COLOR_TEXT_MUTED = "#64748b"    # slate-500
COLOR_GRID = "#f1f5f9"          # slate-100
COLOR_BG_TRANSPARENT = "rgba(0,0,0,0)"

# ✨ Default Plotly Layout (Modern Minimal)
def get_minimal_layout(height=380, show_legend=False):
    """Layout มาตรฐานสำหรับกราฟทุกตัว — สบายตา ขาวสะอาด"""
    return dict(
        height=height,
        margin=dict(l=40, r=40, t=10, b=40),
        paper_bgcolor=COLOR_BG_TRANSPARENT,
        plot_bgcolor=COLOR_BG_TRANSPARENT,
        font=dict(family="IBM Plex Sans Thai, sans-serif", size=12, color=COLOR_TEXT_MUTED),
        xaxis=dict(
            gridcolor=COLOR_GRID,
            zeroline=False,
            showline=False,
            tickfont=dict(color=COLOR_TEXT_MUTED, size=11)
        ),
        yaxis=dict(
            gridcolor=COLOR_GRID,
            zeroline=False,
            showline=False,
            tickfont=dict(color=COLOR_TEXT_MUTED, size=11)
        ),
        showlegend=show_legend,
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e2e8f0",
            font=dict(family="IBM Plex Sans Thai, sans-serif", color=COLOR_TEXT, size=13)
        )
    )


def parse_thai_date_to_dt(thai_date_str):
    try:
        parts = str(thai_date_str).strip().split()
        if len(parts) < 3:
            return None
        day = int(parts[0])
        month_num = THAI_MONTH_TO_NUM.get(parts[1])
        if not month_num:
            return None
        year_ce = int(parts[2]) - 543
        return datetime(year_ce, month_num, day)
    except Exception:
        return None


@st.cache_data(ttl=600)
def load_all_lottery_data():
    """โหลดข้อมูลทั้งหมดจาก MongoDB"""
    try:
        client = get_database_client()
        db = client["lottery_db"]
        collection = db["draws"]

        data = list(collection.find())
        if not data:
            return pd.DataFrame()

        rows = []
        for doc in data:
            prizes = doc.get("prizes", {})

            def extract_primary(val):
                if isinstance(val, list):
                    for v in val:
                        s = str(v).strip()
                        if s and s != "-":
                            return s
                    return "-"
                s = str(val).strip()
                return s if s else "-"

            def list_to_csv(val):
                if isinstance(val, list):
                    items = [str(v).strip() for v in val if v and str(v).strip() and str(v).strip() != "-"]
                    return ", ".join(items) if items else "-"
                s = str(val).strip()
                return s if s else "-"

            first_prize_primary = extract_primary(prizes.get("FIRST"))
            two_digit_str = list_to_csv(prizes.get("TWO_DIGIT"))
            three_front_str = list_to_csv(prizes.get("THREE_FRONT"))
            three_last_str = list_to_csv(prizes.get("THREE_LAST"))

            if len(first_prize_primary) == 6 and first_prize_primary.isdigit():
                last2_of_first = first_prize_primary[-2:]
                last3_of_first = first_prize_primary[-3:]
            else:
                last2_of_first = "-"
                last3_of_first = "-"

            draw_date_str = doc.get("draw_date_str", "-")
            draw_dt = parse_thai_date_to_dt(draw_date_str)

            rows.append({
                "งวดวันที่": draw_date_str,
                "รางวัลที่ 1": first_prize_primary,
                "เลขท้าย 2 ตัว": two_digit_str,
                "เลข 2 ตัวท้ายรางวัลที่ 1": last2_of_first,
                "เลขหน้า 3 ตัว": three_front_str,
                "เลขท้าย 3 ตัว": three_last_str,
                "เลข 3 ตัวท้ายรางวัลที่ 1": last3_of_first,
                "_draw_dt": draw_dt
            })

        df_local = pd.DataFrame(rows)
        df_local = df_local.sort_values(by="_draw_dt", ascending=True, na_position="last").reset_index(drop=True)
        return df_local
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame()


def get_flat_series(dataframe, column_name):
    all_items = []
    for val in dataframe[column_name].dropna():
        val_str = str(val).strip()
        if val_str == "-":
            continue
        items = [i.strip() for i in val_str.split(",")]
        all_items.extend([i for i in items if i and i != "-"])
    return pd.Series(all_items)


def get_last_numbers_per_draw(dataframe, column_name):
    draws = []
    for val in dataframe[column_name].dropna():
        val_str = str(val).strip()
        if val_str == "-":
            draws.append([])
            continue
        items = [i.strip() for i in val_str.split(",") if i.strip() and i.strip() != "-"]
        draws.append(items)
    return draws


# ====================================================================
#  5. ✨ ฟังก์ชันสร้างกราฟ Modern Minimal
# ====================================================================



def make_horizontal_bar(labels, values, height=440, label_suffix="ครั้ง"):
    """กราฟแท่งแนวนอน Modern Minimal — แท่งหนา สมดุลกับจำนวนข้อมูล"""
    # กรองรายการที่มี value = 0 ออก
    filtered = [(l, v) for l, v in zip(labels, values) if v > 0]
    if not filtered:
        fig = go.Figure()
        fig.add_annotation(
            text="ไม่มีข้อมูล",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="IBM Plex Sans Thai, sans-serif", size=14, color=COLOR_TEXT_MUTED)
        )
        layout = get_minimal_layout(height=height)
        layout["xaxis"]["visible"] = False
        layout["yaxis"]["visible"] = False
        fig.update_layout(**layout)
        return fig

    labels = [x[0] for x in filtered]
    values = [x[1] for x in filtered]
    n = len(values)

    # ✨ ปรับ height ตามจำนวนแท่งจริง — แต่ละแท่งสูง ~36px เพื่อให้หนาพอ
    PER_BAR_HEIGHT = 36
    MIN_HEIGHT = 220
    PADDING = 60  # margin top/bottom
    dynamic_height = max(MIN_HEIGHT, n * PER_BAR_HEIGHT + PADDING)
    # ถ้าจำนวนแท่งมาก ไม่ให้สูงเกิน height ที่กำหนดมา
    actual_height = min(dynamic_height, height) if n >= 8 else dynamic_height

    # ไล่ shade จากเข้ม → อ่อน
    colors = []
    for i in range(n):
        ratio = i / max(n - 1, 1)
        r = int(0x4f + ratio * (0x81 - 0x4f))
        g = int(0x46 + ratio * (0x8c - 0x46))
        b = int(0xe5 + ratio * (0xf8 - 0xe5))
        colors.append(f"rgb({r},{g},{b})")

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=values,
        textposition="outside",
        textfont=dict(family="IBM Plex Sans Thai, sans-serif", size=13, color=COLOR_TEXT, weight=600),
        hovertemplate=f"<b>%{{y}}</b><br>ออก %{{x}} {label_suffix}<extra></extra>",
        cliponaxis=False
    ))

    layout = get_minimal_layout(height=actual_height)
    layout["yaxis"]["autorange"] = "reversed"
    layout["yaxis"]["type"] = "category"
    layout["yaxis"]["tickfont"] = dict(family="IBM Plex Sans Thai, sans-serif", size=14, color=COLOR_TEXT, weight=600)
    layout["xaxis"]["showticklabels"] = False
    # ✨ ลด bargap อย่างเฉียบ — แท่งหนา
    layout["bargap"] = 0.15
    # ขยาย range เพื่อ text outside
    max_v = max(values)
    layout["xaxis"]["range"] = [0, max_v * 1.15]
    layout["margin"]["l"] = 55
    layout["margin"]["r"] = 60
    layout["margin"]["t"] = 20
    layout["margin"]["b"] = 20
    fig.update_layout(**layout)
    return fig


def make_digit_bars(digit_counts, position_name):
    """กราฟแท่งความถี่ตามหลัก 0-9 — ซ่อนเลขที่ไม่มีออกมา และจัดเรียงตามความถี่"""
    # กรองเฉพาะเลขที่มีการออก (count > 0) และเรียงจากมากไปน้อย
    items = [(d, c) for d, c in digit_counts.items() if c > 0]
    items.sort(key=lambda x: (-x[1], x[0]))  # เรียงจากมากสุด, ถ้าเท่ากันก็เรียงตามตัวเลข

    if not items:
        # ไม่มีข้อมูล - แสดง empty state
        fig = go.Figure()
        fig.add_annotation(
            text="ไม่มีข้อมูล",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="IBM Plex Sans Thai, sans-serif", size=14, color=COLOR_TEXT_MUTED)
        )
        layout = get_minimal_layout(height=240)
        layout["xaxis"]["visible"] = False
        layout["yaxis"]["visible"] = False
        fig.update_layout(**layout)
        return fig

    digits = [d for d, _ in items]
    counts = [c for _, c in items]
    max_count = max(counts)

    # ไล่สี gradient ตามความถี่ (เข้ม = บ่อยสุด, อ่อน = น้อยสุด)
    colors = []
    for c in counts:
        ratio = c / max_count if max_count > 0 else 0
        # blend จากอ่อน (#c7d2fe) → เข้ม (#4f46e5)
        r = int(0xc7 - ratio * (0xc7 - 0x4f))
        g = int(0xd2 - ratio * (0xd2 - 0x46))
        b = int(0xfe - ratio * (0xfe - 0xe5))
        colors.append(f"rgb({r},{g},{b})")

    fig = go.Figure(go.Bar(
        x=[str(d) for d in digits],
        y=counts,
        marker=dict(color=colors, line=dict(width=0)),
        text=counts,
        textposition="outside",
        textfont=dict(family="IBM Plex Sans Thai, sans-serif", size=12, color=COLOR_TEXT),
        hovertemplate=f"<b>{position_name} %{{x}}</b><br>ออก %{{y}} ครั้ง<extra></extra>",
        cliponaxis=False
    ))
    layout = get_minimal_layout(height=240)
    # ปรับ bargap น้อยลงเพื่อให้แท่งกว้างขึ้น
    layout["bargap"] = 0.2 if len(digits) >= 5 else 0.35
    layout["yaxis"]["showticklabels"] = False
    # ขยาย y-range เพื่อให้ text outside ไม่โดนตัด
    layout["yaxis"]["range"] = [0, max_count * 1.18]
    # ทำให้ x-axis แสดงเฉพาะตัวเลขที่มี
    layout["xaxis"]["type"] = "category"
    layout["xaxis"]["tickfont"] = dict(family="IBM Plex Sans Thai, sans-serif", size=13, color=COLOR_TEXT)
    fig.update_layout(**layout)
    return fig


def make_monthly_trend(months_data, label="ความถี่"):
    """กราฟแท่งแสดงงวดสะสมแต่ละเดือน — ซ่อนเดือนที่ไม่มีงวดออกเลย"""
    # กรองเฉพาะเดือนที่มีงวด > 0
    filtered = [(m, v) for m, v in months_data.items() if v > 0]
    if not filtered:
        fig = go.Figure()
        fig.add_annotation(
            text="ไม่มีข้อมูล",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="IBM Plex Sans Thai, sans-serif", size=14, color=COLOR_TEXT_MUTED)
        )
        layout = get_minimal_layout(height=300)
        layout["xaxis"]["visible"] = False
        layout["yaxis"]["visible"] = False
        fig.update_layout(**layout)
        return fig

    months = [x[0] for x in filtered]
    counts = [x[1] for x in filtered]
    max_count = max(counts)

    # gradient color ตามค่า
    colors = []
    for c in counts:
        ratio = c / max_count if max_count > 0 else 0
        r = int(0xc7 - ratio * (0xc7 - 0x4f))
        g = int(0xd2 - ratio * (0xd2 - 0x46))
        b = int(0xfe - ratio * (0xfe - 0xe5))
        colors.append(f"rgb({r},{g},{b})")

    fig = go.Figure(go.Bar(
        x=months,
        y=counts,
        marker=dict(color=colors, line=dict(width=0)),
        text=counts,
        textposition="outside",
        textfont=dict(family="IBM Plex Sans Thai, sans-serif", size=12, color=COLOR_TEXT),
        hovertemplate=f"<b>เดือน %{{x}}</b><br>{label} %{{y}} งวด<extra></extra>",
        cliponaxis=False
    ))
    layout = get_minimal_layout(height=320)
    layout["bargap"] = 0.3
    layout["yaxis"]["range"] = [0, max_count * 1.15]
    layout["yaxis"]["showticklabels"] = False
    fig.update_layout(**layout)
    return fig


def make_heatmap_calendar(df_calendar):
    """Heatmap แสดงงวดที่ออกในแต่ละเดือนของปี"""
    fig = go.Figure(go.Heatmap(
        z=df_calendar.values,
        x=df_calendar.columns,
        y=df_calendar.index,
        colorscale=[
            [0, "#f1f5f9"],
            [0.5, "#a5b4fc"],
            [1, "#4f46e5"]
        ],
        hovertemplate="<b>%{y} - %{x}</b><br>งวดที่ออก %{z} ครั้ง<extra></extra>",
        showscale=True,
        colorbar=dict(
            thickness=10,
            len=0.6,
            tickfont=dict(family="IBM Plex Sans Thai, sans-serif", size=10, color=COLOR_TEXT_MUTED),
            title=dict(text="จำนวน", font=dict(size=11, color=COLOR_TEXT_MUTED))
        )
    ))
    fig.update_layout(**get_minimal_layout(height=300))
    return fig


def make_consensus_bar(consensus_data):
    """กราฟ Top 10 จากคะแนนโหวตรวม — ซ่อนตัวเลขที่คะแนน = 0"""
    filtered = [(num, score) for num, score in consensus_data if score > 0]
    if not filtered:
        fig = go.Figure()
        fig.add_annotation(
            text="ไม่มีข้อมูล",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="IBM Plex Sans Thai, sans-serif", size=14, color=COLOR_TEXT_MUTED)
        )
        layout = get_minimal_layout(height=320)
        layout["xaxis"]["visible"] = False
        layout["yaxis"]["visible"] = False
        fig.update_layout(**layout)
        return fig

    labels = [x[0] for x in filtered]
    scores = [x[1] for x in filtered]
    max_score = max(scores)

    fig = go.Figure(go.Bar(
        x=labels,
        y=scores,
        marker=dict(
            color=scores,
            colorscale=[[0, "#c7d2fe"], [1, COLOR_PRIMARY]],
            line=dict(width=0)
        ),
        text=scores,
        textposition="outside",
        textfont=dict(family="IBM Plex Sans Thai, sans-serif", size=12, color=COLOR_TEXT),
        hovertemplate="<b>เลข %{x}</b><br>คะแนนโหวตรวม %{y}<extra></extra>",
        cliponaxis=False
    ))
    layout = get_minimal_layout(height=320)
    layout["bargap"] = 0.35
    layout["yaxis"]["range"] = [0, max_score * 1.18]
    layout["yaxis"]["showticklabels"] = False
    layout["xaxis"]["type"] = "category"
    layout["xaxis"]["tickfont"] = dict(family="IBM Plex Sans Thai, sans-serif", size=13, color=COLOR_TEXT)
    fig.update_layout(**layout)
    return fig


# ====================================================================
#  6. ฟังก์ชันสร้าง KPI Cards
# ====================================================================
def render_kpi_card(label, value, sub_text="", accent=False):
    accent_class = "kpi-accent" if accent else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {accent_class}">{value}</div>
        <div class="kpi-sub">{sub_text}</div>
    </div>
    """


# ====================================================================
#  7. Sidebar
# ====================================================================
with st.sidebar:
    st.markdown("### 📊 คลังข้อมูลสะสม")

    if st.button("🔄 รีเฟรชข้อมูลล่าสุด", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

# โหลดข้อมูล
df = load_all_lottery_data()

# ====================================================================
#  8. หัวเรื่องหลัก
# ====================================================================
st.markdown('<div class="main-title">📊 ระบบคำนวณและวิเคราะห์สถิติสลากกินแบ่งรัฐบาล</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">แดชบอร์ดวิเคราะห์เชิงสถิติศาสตร์ ผสานพลังกรรมการ 7 โมเดลคณิตศาสตร์</div>', unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ ไม่พบข้อมูลในฐานข้อมูล กรุณารัน seed_history.py เพื่อนำเข้าสถิติย้อนหลัง")
    st.stop()

# เพิ่มคอลัมน์ "เดือน" สำหรับใช้ในหลายที่
def get_thai_month(date_text):
    parts = str(date_text).split()
    return parts[1] if len(parts) >= 2 else "ไม่ระบุ"

df['เดือน'] = df['งวดวันที่'].apply(get_thai_month)

# ====================================================================
#  9. ✨ KPI Cards (4 cards) แสดงตลอด ทุก Tab
# ====================================================================
# คำนวณค่าสำหรับ KPI
total_draws = len(df)
first_draw = df['งวดวันที่'].iloc[0] if len(df) > 0 else "-"
latest_draw = df['งวดวันที่'].iloc[-1] if len(df) > 0 else "-"

# หาเลขท้าย 2 ตัวที่ออกบ่อยที่สุด
flat_2digit = get_flat_series(df, "เลขท้าย 2 ตัว")
top_2digit = flat_2digit.value_counts().head(1)
top_2digit_num = top_2digit.index[0] if len(top_2digit) > 0 else "-"
top_2digit_count = int(top_2digit.iloc[0]) if len(top_2digit) > 0 else 0

# หาเดือนที่ออกบ่อยที่สุด
top_month = df['เดือน'].value_counts().head(1)
top_month_name = top_month.index[0] if len(top_month) > 0 else "-"
top_month_count = int(top_month.iloc[0]) if len(top_month) > 0 else 0

# Sidebar - แสดง 5 งวดล่าสุด
with st.sidebar:
    st.metric(label="งวดสะสมทั้งหมด", value=f"{total_draws:,} งวด")
    st.caption(f"📅 ตั้งแต่: {first_draw}")
    st.caption(f"📅 ถึง: {latest_draw}")

    st.markdown("---")
    st.markdown("##### 🔍 5 งวดล่าสุด")
    recent_5 = df[['งวดวันที่', 'เลขท้าย 2 ตัว']].tail(5).iloc[::-1]
    for _, row in recent_5.iterrows():
        st.markdown(f"<small>📌 <b>{row['งวดวันที่']}</b><br>เลขท้าย 2 ตัว: <code>{row['เลขท้าย 2 ตัว']}</code></small>", unsafe_allow_html=True)

# KPI Cards Row
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(render_kpi_card(
        "📚 งวดสะสมทั้งหมด",
        f"{total_draws:,}",
        f"ตั้งแต่ {first_draw}"
    ), unsafe_allow_html=True)
with k2:
    st.markdown(render_kpi_card(
        "📅 งวดล่าสุด",
        latest_draw.split()[0] + " " + latest_draw.split()[1][:3] + ".",
        latest_draw,
        accent=True
    ), unsafe_allow_html=True)
with k3:
    st.markdown(render_kpi_card(
        "🎯 เลขท้าย 2 ตัวเด่นสุด",
        top_2digit_num,
        f"ออกมาแล้ว {top_2digit_count} ครั้ง",
        accent=True
    ), unsafe_allow_html=True)
with k4:
    st.markdown(render_kpi_card(
        "📆 เดือนที่ออกบ่อยสุด",
        top_month_name,
        f"{top_month_count} งวด"
    ), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ====================================================================
#  10. Tabs
# ====================================================================
categories = [
    "เลขท้าย 2 ตัว",
    "เลข 2 ตัวท้ายรางวัลที่ 1",
    "เลขหน้า 3 ตัว",
    "เลขท้าย 3 ตัว",
    "เลข 3 ตัวท้ายรางวัลที่ 1"
]

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 สถิติความถี่มวลรวม",
    "📅 สถิติรายเดือน",
    "🔮 โมเดลคณิตศาสตร์",
    "📋 ตารางประวัติทั้งหมด"
])

# ----------------------------------------------------------------
#  TAB 1: สถิติความถี่มวลรวม
# ----------------------------------------------------------------
with tab1:
    st.markdown('<div class="section-header">🎯 อันดับตัวเลขที่ออกบ่อยที่สุด</div>', unsafe_allow_html=True)

    selected_cat = st.selectbox(
        "เลือกประเภทตัวเลขที่ต้องการดูสถิติ",
        categories,
        key="tab1_cat"
    )

    flat_data = get_flat_series(df, selected_cat)

    if not flat_data.empty:
        sample_len = len(str(flat_data.iloc[0]))
        total_items = len(flat_data)
        unique_count = flat_data.nunique()
        avg_freq = total_items / unique_count if unique_count > 0 else 0

        # KPI ของ Tab นี้
        sub_k1, sub_k2, sub_k3 = st.columns(3)
        with sub_k1:
            st.markdown(render_kpi_card(
                f"จำนวนข้อมูล {selected_cat}",
                f"{total_items:,}",
                f"จาก {total_draws} งวด"
            ), unsafe_allow_html=True)
        with sub_k2:
            st.markdown(render_kpi_card(
                "ตัวเลขที่เคยออก",
                f"{unique_count}",
                f"จากความเป็นไปได้ทั้งหมด"
            ), unsafe_allow_html=True)
        with sub_k3:
            st.markdown(render_kpi_card(
                "ความถี่เฉลี่ย",
                f"{avg_freq:.1f}",
                "ครั้งต่อเลข",
                accent=True
            ), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # กราฟแท่ง Top 10
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-title">🔝 Top 10 {selected_cat}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-subtitle">จัดอันดับตามจำนวนครั้งที่ออกทั้งหมด</div>', unsafe_allow_html=True)
            top_10 = flat_data.value_counts().head(10)
            fig = make_horizontal_bar(top_10.index.tolist(), top_10.values.tolist(), height=440)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-title">📋 อันดับแบบละเอียด</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-subtitle">ตารางเรียงตามความถี่</div>', unsafe_allow_html=True)
            top_df = flat_data.value_counts().reset_index()
            top_df.columns = ["ตัวเลข", "จำนวนครั้ง"]
            top_df['อัตรา %'] = (top_df['จำนวนครั้ง'] / total_items * 100).round(2)
            st.dataframe(top_df, use_container_width=True, hide_index=True, height=400)
            st.markdown('</div>', unsafe_allow_html=True)

        # ความถี่แยกตามตำแหน่งหลัก
        st.markdown(f'<div class="section-header">🔢 ความถี่แยกตามตำแหน่งหลัก</div>', unsafe_allow_html=True)

        if sample_len == 2:
            tens = [int(str(n)[0]) for n in flat_data if len(str(n)) == 2 and str(n).isdigit()]
            units = [int(str(n)[1]) for n in flat_data if len(str(n)) == 2 and str(n).isdigit()]
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<div class="chart-title">🔵 หลักสิบ (0-9)</div>', unsafe_allow_html=True)
                st.markdown('<div class="chart-subtitle">ความถี่ของหลักซ้ายของเลข 2 ตัว</div>', unsafe_allow_html=True)
                fig = make_digit_bars(Counter(tens), "หลักสิบ")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
            with sc2:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<div class="chart-title">🟣 หลักหน่วย (0-9)</div>', unsafe_allow_html=True)
                st.markdown('<div class="chart-subtitle">ความถี่ของหลักขวาของเลข 2 ตัว</div>', unsafe_allow_html=True)
                fig = make_digit_bars(Counter(units), "หลักหน่วย")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
        elif sample_len == 3:
            hundreds = [int(str(n)[0]) for n in flat_data if len(str(n)) == 3 and str(n).isdigit()]
            tens = [int(str(n)[1]) for n in flat_data if len(str(n)) == 3 and str(n).isdigit()]
            units = [int(str(n)[2]) for n in flat_data if len(str(n)) == 3 and str(n).isdigit()]
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<div class="chart-title">🔵 หลักร้อย</div>', unsafe_allow_html=True)
                fig = make_digit_bars(Counter(hundreds), "หลักร้อย")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
            with sc2:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<div class="chart-title">🟣 หลักสิบ</div>', unsafe_allow_html=True)
                fig = make_digit_bars(Counter(tens), "หลักสิบ")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
            with sc3:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown('<div class="chart-title">🟢 หลักหน่วย</div>', unsafe_allow_html=True)
                fig = make_digit_bars(Counter(units), "หลักหน่วย")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------
#  TAB 2: สถิติรายเดือน
# ----------------------------------------------------------------
with tab2:
    st.markdown('<div class="section-header">📅 วิเคราะห์แนวโน้มรายเดือน</div>', unsafe_allow_html=True)

    available_months = [m for m in THAI_MONTHS_ORDER if m in df['เดือน'].unique()]

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        selected_month = st.selectbox("เลือกเดือน", available_months if available_months else df['เดือน'].unique())
    with m_col2:
        selected_month_cat = st.selectbox("เลือกประเภทตัวเลข", categories, key="tab2_cat")

    df_month = df[df['เดือน'] == selected_month]
    month_flat_data = get_flat_series(df_month, selected_month_cat)
    n_draws_in_month = len(df_month)

    # KPI ของ Tab นี้
    sub_k1, sub_k2, sub_k3 = st.columns(3)
    with sub_k1:
        st.markdown(render_kpi_card(
            f"📆 งวดในเดือน {selected_month}",
            f"{n_draws_in_month}",
            "งวด"
        ), unsafe_allow_html=True)
    with sub_k2:
        if not month_flat_data.empty:
            top_in_month = month_flat_data.value_counts().head(1)
            st.markdown(render_kpi_card(
                f"🔥 เลขเด่นในเดือน",
                top_in_month.index[0],
                f"ออกมาแล้ว {int(top_in_month.iloc[0])} ครั้ง",
                accent=True
            ), unsafe_allow_html=True)
        else:
            st.markdown(render_kpi_card("🔥 เลขเด่นในเดือน", "-", "ไม่มีข้อมูล"), unsafe_allow_html=True)
    with sub_k3:
        unique_in_month = month_flat_data.nunique()
        st.markdown(render_kpi_card(
            "💎 เลขที่เคยออกในเดือน",
            f"{unique_in_month}",
            f"ตัวเลขแตกต่าง"
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not month_flat_data.empty:
        # Top 10 ในเดือน + ตาราง
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-title">🔝 Top 10 {selected_month_cat} ในเดือน {selected_month}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-subtitle">เฉพาะงวดที่ออกในเดือน {selected_month} ของทุกปี</div>', unsafe_allow_html=True)
            top_10_m = month_flat_data.value_counts().head(10)
            fig = make_horizontal_bar(top_10_m.index.tolist(), top_10_m.values.tolist(), height=440)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-title">📋 ตารางอันดับ</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-subtitle">เรียงตามความถี่</div>', unsafe_allow_html=True)
            m_top_df = month_flat_data.value_counts().reset_index()
            m_top_df.columns = ["ตัวเลข", "จำนวนครั้ง"]
            st.dataframe(m_top_df, use_container_width=True, hide_index=True, height=400)
            st.markdown('</div>', unsafe_allow_html=True)

    # แนวโน้มการออกของแต่ละเดือนตลอดทั้งปี
    st.markdown(f'<div class="section-header">📈 แนวโน้มการออกของแต่ละเดือน (จำนวนงวดสะสม)</div>', unsafe_allow_html=True)

    monthly_counts = {}
    for month_name in THAI_MONTHS_ORDER:
        count = len(df[df['เดือน'] == month_name])
        monthly_counts[month_name] = count

    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">📊 จำนวนงวดสะสมในแต่ละเดือนของปี</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-subtitle">รวมจากข้อมูลย้อนหลังทั้งหมด เพื่อดูว่าเดือนไหนมีงวดออกมากที่สุด</div>', unsafe_allow_html=True)
    fig = make_monthly_trend(monthly_counts, label="มีงวดออก")
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------
#  TAB 3: โมเดลคณิตศาสตร์ + Consensus
# ----------------------------------------------------------------
with tab3:
    st.markdown('<div class="section-header">🔮 แดชบอร์ดโมเดลคณิตศาสตร์ผสานพลัง 7 โมเดล</div>', unsafe_allow_html=True)

    # Disclaimer
    st.markdown("""
    <div class="warning-box">
        <b>⚠️ คำเตือนทางสถิติ:</b> ผลสลากกินแบ่งเป็นเหตุการณ์สุ่มอิสระ (Independent Events)
        ตัวเลขที่ค้างนานไม่ได้มีโอกาสออกสูงขึ้นในงวดถัดไป (Gambler's Fallacy)
        โมเดลที่แสดงด้านล่างเป็นการวิเคราะห์ pattern ในข้อมูลย้อนหลังเพื่อความบันเทิงเท่านั้น
        ไม่สามารถใช้พยากรณ์ผลรางวัลในอนาคตได้จริง โปรดเล่นพนันอย่างมีสติ
    </div>
    """, unsafe_allow_html=True)

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        formula_cat = st.selectbox("1. ประเภทตัวเลขที่ต้องการวิเคราะห์", categories, key="tab3_cat")
    with f_col2:
        available_months = [m for m in THAI_MONTHS_ORDER if m in df['เดือน'].unique()]
        target_month = st.selectbox(
            "2. เงื่อนไขเดือนสำหรับสูตรเบย์",
            available_months if available_months else df['เดือน'].unique(),
            key="tab3_month"
        )

    cat_flat_data = get_flat_series(df, formula_cat)
    cat_per_draw = get_last_numbers_per_draw(df, formula_cat)

    if not cat_flat_data.empty:
        sample_len = len(str(cat_flat_data.iloc[0]))
        total_items_count = len(cat_flat_data)
        total_draws_count = len(df)

        all_possible_nums = [
            f"{i:02d}" if sample_len == 2 else f"{i:03d}"
            for i in range(100 if sample_len == 2 else 1000)
        ]
        total_possible_types = len(all_possible_nums)

        last_seen_idx = {}
        for idx, val in enumerate(cat_flat_data):
            last_seen_idx[str(val)] = idx

        scoring_data = {}
        for num in all_possible_nums:
            last_idx = last_seen_idx.get(num, -1)
            cur_overdue = total_items_count - 1 - last_idx if last_idx != -1 else total_items_count
            scoring_data[num] = {
                "freq": int(cat_flat_data.value_counts().get(num, 0)),
                "overdue_draws": cur_overdue,
                "bayes_lift": 0.0,
                "poisson_prob": 0.0,
                "chisq_contrib": 0.0,
                "overdue_index": 0.0,
                "ema_momentum": 0.0,
                "voting_score": 0
            }

        voting_scores = {n: 0 for n in all_possible_nums}

        # --- 1. Bayes ---
        df_m = df[df['เดือน'] == target_month]
        m_flat = get_flat_series(df_m, formula_cat)
        total_m_items = len(m_flat)
        m_value_counts = m_flat.value_counts() if total_m_items > 0 else pd.Series(dtype=int)

        bayes_results = []
        for num in all_possible_nums:
            p_num = scoring_data[num]["freq"] / total_items_count if total_items_count > 0 else 0
            p_num_given_m = (m_value_counts.get(num, 0) / total_m_items) if total_m_items > 0 else 0
            lift = (p_num_given_m / p_num) if p_num > 0 else 0
            scoring_data[num]["bayes_lift"] = lift
            bayes_results.append((num, lift))
        bayes_results.sort(key=lambda x: x[1], reverse=True)
        top_bayes = [f"{item[0]}" for item in bayes_results[:3]]
        for rank, item in enumerate(bayes_results[:10]):
            voting_scores[item[0]] += (10 - rank)

        # --- 2. Poisson ---
        poisson_results = []
        for num in all_possible_nums:
            occurrences = scoring_data[num]["freq"]
            lam_per_draw = occurrences / total_draws_count if total_draws_count > 0 else 0
            overdue_draws = scoring_data[num]["overdue_draws"]
            if lam_per_draw > 0:
                prob_to_appear = 1.0 - math.exp(-lam_per_draw * (overdue_draws + 1))
            else:
                prob_to_appear = 0
            scoring_data[num]["poisson_prob"] = prob_to_appear
            poisson_results.append((num, prob_to_appear))
        poisson_results.sort(key=lambda x: x[1], reverse=True)
        top_poisson = [f"{item[0]}" for item in poisson_results[:3]]
        for rank, item in enumerate(poisson_results[:10]):
            voting_scores[item[0]] += (10 - rank)

        # --- 3. Chi-Square ---
        expected_freq = total_items_count / total_possible_types
        chisq_results = []
        for num in all_possible_nums:
            observed_freq = scoring_data[num]["freq"]
            chisq_contrib = ((observed_freq - expected_freq) ** 2) / expected_freq if expected_freq > 0 else 0
            actual_contrib = chisq_contrib if observed_freq > expected_freq else 0
            scoring_data[num]["chisq_contrib"] = actual_contrib
            chisq_results.append((num, actual_contrib))
        chisq_results.sort(key=lambda x: x[1], reverse=True)
        top_chisq = [f"{item[0]}" for item in chisq_results[:3]]
        for rank, item in enumerate(chisq_results[:10]):
            voting_scores[item[0]] += (10 - rank)

        # --- 4. Regression to Mean ---
        regression_results = []
        for num in all_possible_nums:
            overdue_draws = scoring_data[num]["overdue_draws"]
            overdue_index = overdue_draws / total_possible_types if total_possible_types > 0 else 0
            scoring_data[num]["overdue_index"] = overdue_index
            regression_results.append((num, overdue_index))
        regression_results.sort(key=lambda x: x[1], reverse=True)
        top_regression = [f"{item[0]}" for item in regression_results[:3]]
        for rank, item in enumerate(regression_results[:10]):
            voting_scores[item[0]] += (10 - rank)

        # --- 5. Markov Chain ---
        top_markov_list = []
        last_draw_numbers = []
        for draw_nums in reversed(cat_per_draw):
            if draw_nums:
                last_draw_numbers = draw_nums
                break

        if last_draw_numbers and len(cat_per_draw) > 1:
            next_nums_collected = []
            for i in range(len(cat_per_draw) - 1):
                current_draw = cat_per_draw[i]
                if any(n in last_draw_numbers for n in current_draw):
                    next_nums_collected.extend(cat_per_draw[i + 1])

            if next_nums_collected:
                markov_counts = Counter(next_nums_collected)
                markov_sorted = markov_counts.most_common(10)
                top_markov_list = [f"{item[0]}" for item in markov_sorted[:3]]
                for rank, item in enumerate(markov_sorted):
                    voting_scores[item[0]] += (10 - rank)

        top_markov = top_markov_list if top_markov_list else ["-"]
        last_num_display = ", ".join(last_draw_numbers) if last_draw_numbers else "-"

        # --- 6. EMA ---
        alpha_decay = 0.05
        ema_scores = {n: 0.0 for n in all_possible_nums}
        for idx, val in enumerate(cat_flat_data):
            v_str = str(val)
            if v_str in ema_scores:
                dist = total_items_count - 1 - idx
                ema_scores[v_str] += alpha_decay * ((1 - alpha_decay) ** dist)
        for num, score in ema_scores.items():
            scoring_data[num]["ema_momentum"] = score
        ema_results = sorted(ema_scores.items(), key=lambda x: x[1], reverse=True)
        top_ema = [f"{item[0]}" for item in ema_results[:3]]
        for rank, item in enumerate(ema_results[:10]):
            voting_scores[item[0]] += (10 - rank)

        # --- 7. Digit Sum & Parity ---
        def get_digit_sum(n_str):
            return sum(int(c) for c in n_str if c.isdigit())

        def get_parity_pattern(n_str):
            return "-".join(["คี่" if int(c) % 2 != 0 else "คู่" for c in n_str if c.isdigit()])

        hist_sums = [get_digit_sum(str(n)) for n in cat_flat_data]
        hist_parities = [get_parity_pattern(str(n)) for n in cat_flat_data]

        top_3_sums = [item[0] for item in Counter(hist_sums).most_common(3)] if hist_sums else []
        most_common_parity = Counter(hist_parities).most_common(1)[0][0] if hist_parities else ""

        balanced_nums = []
        for num in all_possible_nums:
            digit_sum = get_digit_sum(num)
            parity = get_parity_pattern(num)
            if digit_sum in top_3_sums and parity == most_common_parity:
                balanced_nums.append((num, scoring_data[num]["freq"]))
        balanced_nums.sort(key=lambda x: x[1], reverse=True)
        top_balanced = [f"{item[0]}" for item in balanced_nums[:3]]
        for rank, item in enumerate(balanced_nums[:10]):
            voting_scores[item[0]] += (10 - rank)

        # --- Consensus ---
        consensus_results = sorted(voting_scores.items(), key=lambda x: x[1], reverse=True)
        top_consensus = consensus_results[:10]

        # ============= DISPLAY =============
        # 🎯 Consensus Highlight Card
        top_5_consensus = consensus_results[:5]
        numbers_str = " · ".join([item[0] for item in top_5_consensus])
        st.markdown(f"""
        <div class="consensus-card">
            <div class="consensus-title">🎯 มติเอกฉันท์สูงสุด (Ensemble Consensus)</div>
            <div class="consensus-numbers">{numbers_str}</div>
            <div class="consensus-desc">
                ตัวเลขที่กรรมการทั้ง 7 สูตรคณิตศาสตร์เห็นพ้องว่ามีโครงสร้างสถิติสมบูรณ์ที่สุด<br>
                สำหรับหมวด <b>{formula_cat}</b> (เรียงจากคะแนนมากสุด)
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Top 10 Consensus Chart
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">📊 Top 10 ตัวเลขจากคะแนนโหวตรวม</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-subtitle">คะแนนสูงสุดจากการรวมผลของ 7 โมเดล</div>', unsafe_allow_html=True)
        fig = make_consensus_bar(top_consensus)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

        # 🔍 7 Model Cards
        st.markdown('<div class="section-header">🔍 รายละเอียดแต่ละโมเดล</div>', unsafe_allow_html=True)

        models_data = [
            {
                "icon": "📅", "color": "#10b981", "bg": "#d1fae5",
                "title": "Bayes' Theorem",
                "desc": f"คัดเลขที่น่าจะออกในเดือน {target_month} โดยเทียบกับความน่าจะเป็นทั่วไป",
                "result": ", ".join(top_bayes)
            },
            {
                "icon": "🔥", "color": "#dc2626", "bg": "#fee2e2",
                "title": "Chi-Square",
                "desc": "ค้นหาเลขที่ออกบ่อยกว่าค่าเฉลี่ยสุ่มอย่างมีนัยสำคัญ",
                "result": ", ".join(top_chisq)
            },
            {
                "icon": "🔮", "color": "#2563eb", "bg": "#dbeafe",
                "title": "Poisson Distribution",
                "desc": "คำนวณโอกาสที่ตัวเลขจะออกในงวดหน้าจากอัตราการเกิด",
                "result": ", ".join(top_poisson)
            },
            {
                "icon": "❄️", "color": "#d97706", "bg": "#fef3c7",
                "title": "Regression to Mean",
                "desc": "เลขที่ค้างค้างนานสุด รอจังหวะกลับสู่ค่าเฉลี่ย",
                "result": ", ".join(top_regression)
            },
            {
                "icon": "⛓️", "color": "#475569", "bg": "#f1f5f9",
                "title": "Markov Chain",
                "desc": f"เลขที่มักออกตามหลังเลข {last_num_display} ในประวัติศาสตร์",
                "result": ", ".join(top_markov)
            },
            {
                "icon": "📈", "color": "#7c3aed", "bg": "#ede9fe",
                "title": "EMA Momentum",
                "desc": "เน้นเลขที่ออกบ่อยในช่วงงวดล่าสุด (เลขมาแรง)",
                "result": ", ".join(top_ema)
            },
            {
                "icon": "🎯", "color": "#0d9488", "bg": "#ccfbf1",
                "title": "Digit Sum & Parity",
                "desc": f"เลขที่มีผลรวมหลัก {top_3_sums} และโครงสร้าง {most_common_parity}",
                "result": ", ".join(top_balanced) if top_balanced else "-"
            },
        ]

        cols = st.columns(4)
        for i, model in enumerate(models_data[:4]):
            with cols[i]:
                st.markdown(f"""
                <div class="model-card" style="--accent: {model['color']};">
                    <div class="model-icon" style="background: {model['bg']}; color: {model['color']};">
                        {model['icon']}
                    </div>
                    <div class="model-title">{model['title']}</div>
                    <div class="model-desc">{model['desc']}</div>
                    <div class="model-result" style="color: {model['color']};">{model['result']}</div>
                </div>
                """, unsafe_allow_html=True)

        cols2 = st.columns(4)
        for i, model in enumerate(models_data[4:]):
            with cols2[i]:
                st.markdown(f"""
                <div class="model-card" style="--accent: {model['color']};">
                    <div class="model-icon" style="background: {model['bg']}; color: {model['color']};">
                        {model['icon']}
                    </div>
                    <div class="model-title">{model['title']}</div>
                    <div class="model-desc">{model['desc']}</div>
                    <div class="model-result" style="color: {model['color']};">{model['result']}</div>
                </div>
                """, unsafe_allow_html=True)

        # ตารางรวม Metrics
        st.markdown('<div class="section-header">📋 ตารางดัชนีคะแนนรวม</div>', unsafe_allow_html=True)

        summary_rows = []
        for num in all_possible_nums:
            summary_rows.append({
                "ตัวเลข": num,
                "🏆 คะแนนโหวต": voting_scores.get(num, 0),
                "ออกมา (ครั้ง)": scoring_data[num]["freq"],
                "ค้าง (งวด)": scoring_data[num]["overdue_draws"],
                "Bayes Lift": round(scoring_data[num]["bayes_lift"], 3),
                "Poisson Prob": f"{scoring_data[num]['poisson_prob']*100:.1f}%",
                "Chi-Sq": round(scoring_data[num]["chisq_contrib"], 3),
                "RTM Index": round(scoring_data[num]["overdue_index"], 2),
                "EMA": round(scoring_data[num]["ema_momentum"], 4),
                "ผลรวมหลัก": get_digit_sum(num),
                "พิกัด": get_parity_pattern(num)
            })

        summary_df = pd.DataFrame(summary_rows).sort_values(by="🏆 คะแนนโหวต", ascending=False)
        st.dataframe(summary_df, use_container_width=True, hide_index=True, height=500)

# ----------------------------------------------------------------
#  TAB 4: ตารางประวัติทั้งหมด
# ----------------------------------------------------------------
with tab4:
    st.markdown('<div class="section-header">📋 ตารางประวัติทั้งหมด</div>', unsafe_allow_html=True)

    st.caption(
        f"แสดงข้อมูลทั้งหมด {total_draws:,} งวด เรียงจากใหม่ → เก่า "
        "พร้อมจำแนกประเภทเลขท้าย 2/3 ตัวจากรางวัลที่ 1 อัตโนมัติ"
    )

    # ค้นหา
    search_col, _ = st.columns([2, 3])
    with search_col:
        search_term = st.text_input("🔍 ค้นหาตามวันที่ หรือเลข", placeholder="เช่น 16 พฤษภาคม 2569 หรือ 735867")

    df_display = df.sort_values(by="_draw_dt", ascending=False, na_position="last").drop(
        columns=['_draw_dt', 'เดือน'], errors='ignore'
    )

    if search_term:
        mask = df_display.astype(str).apply(lambda row: row.str.contains(search_term, case=False, na=False)).any(axis=1)
        df_display = df_display[mask]
        st.caption(f"พบ {len(df_display)} งวดที่ตรงกับ '{search_term}'")

    st.dataframe(df_display, use_container_width=True, hide_index=True, height=600)
