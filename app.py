import streamlit as st
import pymongo
import certifi
import pandas as pd
import numpy as np
import os
import math
from collections import Counter
from datetime import datetime, timezone

# ====================================================================
#  1. ตั้งค่าหน้าจอโปรแกรมเป็นแบบกว้าง (Wide Layout) เหมาะแก่การดูสถิติ
# ====================================================================
st.set_page_config(
    page_title="ระบบคำนวณและวิเคราะห์สถิติหวย 30 ปี",
    page_icon="📊",
    layout="wide"
)

# ====================================================================
#  2. เชื่อมต่อฐานข้อมูล MongoDB
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


THAI_MONTHS_ORDER = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]
THAI_MONTH_TO_NUM = {name: idx + 1 for idx, name in enumerate(THAI_MONTHS_ORDER)}


def parse_thai_date_to_dt(thai_date_str):
    """แปลง '16 พฤษภาคม 2569' → datetime (สำหรับ sort ภายใน DataFrame)"""
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


@st.cache_data(ttl=600)  # ลด cache จาก 1 ชั่วโมงเหลือ 10 นาที
def load_all_lottery_data():
    """โหลดข้อมูลทั้งหมดจาก MongoDB แล้วเรียงตามวันที่งวดจริง"""
    try:
        client = get_database_client()
        db = client["lottery_db"]
        collection = db["draws"]

        # ดึงข้อมูลทั้งหมดโดยไม่ต้อง sort ที่ DB เพราะเราจะ sort เองตามวันที่งวด
        data = list(collection.find())

        if not data:
            return pd.DataFrame()

        rows = []
        for doc in data:
            prizes = doc.get("prizes", {})

            def extract_primary(val):
                """ดึงค่าหลักจาก list (เลือกค่าแรกที่ valid) สำหรับใช้คำนวณ last2/last3"""
                if isinstance(val, list):
                    for v in val:
                        s = str(v).strip()
                        if s and s != "-":
                            return s
                    return "-"
                s = str(val).strip()
                return s if s else "-"

            def list_to_csv(val):
                """แปลง list → CSV string เพื่อแสดงในตาราง"""
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

        # เรียงตามวันที่งวดจริง (จากเก่าไปใหม่)
        # งวดที่ parse ไม่ได้จะอยู่ท้ายสุด
        df_local = df_local.sort_values(
            by="_draw_dt",
            ascending=True,
            na_position="last"
        ).reset_index(drop=True)

        return df_local
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame()


def get_flat_series(dataframe, column_name):
    """แตก CSV string ในแต่ละ row เป็น series ของตัวเลขแต่ละตัว"""
    all_items = []
    for val in dataframe[column_name].dropna():
        val_str = str(val).strip()
        if val_str == "-":
            continue
        items = [i.strip() for i in val_str.split(",")]
        all_items.extend([i for i in items if i and i != "-"])
    return pd.Series(all_items)


def get_last_numbers_per_draw(dataframe, column_name):
    """
    ดึงเลข 'งวดล่าสุด' จากคอลัมน์ที่อาจมีหลายเลขต่อ 1 งวด (เช่นเลขท้าย 3 ตัว)
    ใช้สำหรับ Markov Chain ที่ต้องรู้ว่าแต่ละงวดออกเลขใดบ้าง
    คืนค่าเป็น list ของ list (1 งวด = 1 list ของเลข)
    """
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
#  Sidebar - ปุ่มรีเฟรช cache
# ====================================================================
st.sidebar.header("🗂️ คลังข้อมูลสะสม")
if st.sidebar.button("🔄 รีเฟรชข้อมูลล่าสุด", help="ล้าง cache และดึงข้อมูลใหม่จาก MongoDB"):
    st.cache_data.clear()
    st.rerun()

# โหลดข้อมูลเข้าสู่ตัวแปร DataFrame ของ Pandas
df = load_all_lottery_data()

st.markdown(
    "<h1 style='text-align: center; color: #1E3A8A;'>📊 ระบบคำนวณและวิเคราะห์สถิติสลากกินแบ่งรัฐบาล</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; color: #6B7280;'>แดชบอร์ดตัดสินใจเชิงสถิติศาสตร์ ผสานพลังกรรมการ 7 โมเดลคณิตศาสตร์ สรุปมติเอกฉันท์</p>",
    unsafe_allow_html=True
)

if df.empty:
    st.warning("⚠️ ไม่พบข้อมูลในฐานข้อมูล MongoDB ของคุณ กรุณารันไฟล์ seed_history.py เพื่อนำเข้าสถิติย้อนหลังก่อนครับ")
else:
    def get_thai_month(date_text):
        parts = str(date_text).split()
        return parts[1] if len(parts) >= 2 else "ไม่ระบุ"

    df['เดือน'] = df['งวดวันที่'].apply(get_thai_month)

    st.sidebar.metric(label="จำนวนงวดสะสมในระบบ", value=f"{len(df)} งวด")
    st.sidebar.write(f"📅 เริ่มตั้งแต่งวด: `{df['งวดวันที่'].iloc[0]}`")
    st.sidebar.write(f"📅 ถึงงวดล่าสุด: `{df['งวดวันที่'].iloc[-1]}`")

    # เพิ่มข้อมูล debug ใน sidebar เพื่อตรวจสอบการดึงงวดล่าสุด
    with st.sidebar.expander("🔍 ตรวจสอบ 5 งวดล่าสุดที่อยู่ในระบบ"):
        recent_5 = df[['งวดวันที่', 'รางวัลที่ 1', 'เลขท้าย 2 ตัว']].tail(5).iloc[::-1]
        st.dataframe(recent_5, use_container_width=True, hide_index=True)

    categories = [
        "เลขท้าย 2 ตัว",
        "เลข 2 ตัวท้ายรางวัลที่ 1",
        "เลขหน้า 3 ตัว",
        "เลขท้าย 3 ตัว",
        "เลข 3 ตัวท้ายรางวัลที่ 1"
    ]

    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 สถิติความถี่มวลรวม",
        "📅 สถิติเจาะลึกรายเดือน",
        "🔮 โมเดลคณิตศาสตร์เพื่อการตัดสินใจ",
        "📋 ตารางประวัติทั้งหมด"
    ])

    # ----------------------------------------------------------------
    #  TAB 1: สถิติความถี่มวลรวม
    # ----------------------------------------------------------------
    with tab1:
        st.header("🎯 อันดับตัวเลขที่ออกบ่อยที่สุด (Frequency Analysis)")
        selected_cat = st.selectbox("เลือกประเภทตัวเลขที่ต้องการดูสถิติ:", categories, key="tab1_cat")
        flat_data = get_flat_series(df, selected_cat)

        if not flat_data.empty:
            col1, col2 = st.columns([3, 2])
            with col1:
                st.subheader(f"🔝 แผนภูมิแท่ง {selected_cat} ที่ออกบ่อยที่สุด (Top 15)")
                top_15 = flat_data.value_counts().head(15)
                st.bar_chart(top_15)
            with col2:
                st.subheader("📋 ตารางอันดับแบบละเอียด")
                top_df = flat_data.value_counts().reset_index()
                top_df.columns = ["ตัวเลข", "จำนวนครั้งที่ออก"]
                st.dataframe(top_df, use_container_width=True)

            st.write("---")
            st.subheader(f"🔢 สถิติความถี่แยกตามตำแหน่งหลักของ [{selected_cat}]")
            sample_len = len(str(flat_data.iloc[0]))

            if sample_len == 2:
                tens = [int(str(n)[0]) for n in flat_data if len(str(n)) == 2 and str(n).isdigit()]
                units = [int(str(n)[1]) for n in flat_data if len(str(n)) == 2 and str(n).isdigit()]
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.write("**ความถี่ของ หลักสิบ (0-9)**")
                    st.bar_chart(pd.Series(tens).value_counts().sort_index())
                with sc2:
                    st.write("**ความถี่ของ หลักหน่วย (0-9)**")
                    st.bar_chart(pd.Series(units).value_counts().sort_index())
            elif sample_len == 3:
                hundreds = [int(str(n)[0]) for n in flat_data if len(str(n)) == 3 and str(n).isdigit()]
                tens = [int(str(n)[1]) for n in flat_data if len(str(n)) == 3 and str(n).isdigit()]
                units = [int(str(n)[2]) for n in flat_data if len(str(n)) == 3 and str(n).isdigit()]
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    st.write("**ความถี่ของ หลักร้อย (0-9)**")
                    st.bar_chart(pd.Series(hundreds).value_counts().sort_index())
                with sc2:
                    st.write("**ความถี่ของ หลักสิบ (0-9)**")
                    st.bar_chart(pd.Series(tens).value_counts().sort_index())
                with sc3:
                    st.write("**ความถี่ของ หลักหน่วย (0-9)**")
                    st.bar_chart(pd.Series(units).value_counts().sort_index())

    # ----------------------------------------------------------------
    #  TAB 2: สถิติเจาะลึกรายเดือน
    # ----------------------------------------------------------------
    with tab2:
        st.header("📅 วิเคราะห์แนวโน้มจำเพาะเจาะจงเดือน")
        m_col1, m_col2 = st.columns(2)

        # เรียงเดือนตามลำดับปฏิทินไทยจริง
        available_months = [m for m in THAI_MONTHS_ORDER if m in df['เดือน'].unique()]

        with m_col1:
            selected_month = st.selectbox(
                "เลือกเดือนที่ต้องการเปิดสถิติ:",
                available_months if available_months else df['เดือน'].unique()
            )
        with m_col2:
            selected_month_cat = st.selectbox(
                "เลือกประเภทตัวเลขที่ต้องการกรอง:",
                categories,
                key="tab2_cat"
            )

        df_month = df[df['เดือน'] == selected_month]
        month_flat_data = get_flat_series(df_month, selected_month_cat)

        st.info(f"พบประวัติศาสตร์สลากที่เคยออกในเดือน **{selected_month}** ทั้งหมดจำนวน **{len(df_month)}** งวด")

        if not month_flat_data.empty:
            mc1, mc2 = st.columns([3, 2])
            with mc1:
                st.write(f"📊 **กราฟอันดับสถิติ {selected_month_cat} ที่ออกบ่อยที่สุดในเดือน {selected_month}**")
                st.bar_chart(month_flat_data.value_counts().head(10))
            with mc2:
                st.write(f"📋 **ตารางอันดับเด่นประจำเดือน {selected_month}**")
                m_top_df = month_flat_data.value_counts().reset_index()
                m_top_df.columns = ["ตัวเลข", "จำนวนครั้งที่ออก"]
                st.dataframe(m_top_df, use_container_width=True)

    # ----------------------------------------------------------------
    #  TAB 3: โมเดลคณิตศาสตร์
    # ----------------------------------------------------------------
    with tab3:
        st.header("🔮 แดชบอร์ดผสานพลังโมเดลคณิตศาสตร์และมติเอกฉันท์รวม")

        # ⚠️ Disclaimer
        st.warning(
            "⚠️ **คำเตือนทางสถิติ**: ผลสลากกินแบ่งเป็นเหตุการณ์สุ่มอิสระ (Independent Events) "
            "ตัวเลขที่ค้างนานไม่ได้มีโอกาสออกสูงขึ้นในงวดถัดไป (Gambler's Fallacy) "
            "โมเดลที่แสดงด้านล่างเป็นการวิเคราะห์ pattern ในข้อมูลย้อนหลังเพื่อความบันเทิงเท่านั้น "
            "ไม่สามารถใช้พยากรณ์ผลรางวัลในอนาคตได้จริง โปรดเล่นพนันอย่างมีสติ"
        )

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            formula_cat = st.selectbox("1. เลือกประเภทตัวเลขหลักที่ต้องการวิเคราะห์:", categories, key="tab3_cat")
        with f_col2:
            target_month = st.selectbox(
                "2. เลือกเงื่อนไขเดือนสำหรับคำนวณสูตรเบย์:",
                available_months if available_months else df['เดือน'].unique(),
                key="tab3_month"
            )

        cat_flat_data = get_flat_series(df, formula_cat)
        cat_per_draw = get_last_numbers_per_draw(df, formula_cat)  # list of list per draw

        if not cat_flat_data.empty:
            sample_len = len(str(cat_flat_data.iloc[0]))
            total_items_count = len(cat_flat_data)
            total_draws = len(df)  # จำนวนงวดจริง (ไม่ใช่จำนวนเลข)

            all_possible_nums = [
                f"{i:02d}" if sample_len == 2 else f"{i:03d}"
                for i in range(100 if sample_len == 2 else 1000)
            ]
            total_possible_types = len(all_possible_nums)

            last_seen_idx = {}
            for idx, val in enumerate(cat_flat_data):
                last_seen_idx[str(val)] = idx

            # ----------------------------------------------------
            #  โครงสร้างเซฟตี้ป้องกัน IndexError
            # ----------------------------------------------------
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

            # --- 1. สูตรเบย์ (Bayes' Theorem) ---
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
            top_bayes = [f"{item[0]} (x{item[1]:.2f})" for item in bayes_results[:3]]
            for rank, item in enumerate(bayes_results[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 2. สูตรพัวซอง (Poisson Distribution) - แก้ให้ถูกต้อง ---
            # rate λ = อัตราการเกิดต่อ "1 งวด" (ไม่ใช่ต่อ 1 item flat)
            poisson_results = []
            for num in all_possible_nums:
                occurrences = scoring_data[num]["freq"]
                # λ = ความถี่ที่ตัวเลขนี้ออกต่อ 1 งวด (เฉลี่ย)
                lam_per_draw = occurrences / total_draws if total_draws > 0 else 0
                overdue_draws = scoring_data[num]["overdue_draws"]
                # ความน่าจะเป็นที่จะออกอย่างน้อย 1 ครั้งใน (overdue+1) งวดถัดไป
                if lam_per_draw > 0:
                    prob_to_appear = 1.0 - math.exp(-lam_per_draw * (overdue_draws + 1))
                else:
                    prob_to_appear = 0
                scoring_data[num]["poisson_prob"] = prob_to_appear
                poisson_results.append((num, prob_to_appear))
            poisson_results.sort(key=lambda x: x[1], reverse=True)
            top_poisson = [f"{item[0]} ({item[1]*100:.1f}%)" for item in poisson_results[:3]]
            for rank, item in enumerate(poisson_results[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 3. สูตรไคสแควร์ (Chi-Square Anomaly) ---
            expected_freq = total_items_count / total_possible_types
            chisq_results = []
            for num in all_possible_nums:
                observed_freq = scoring_data[num]["freq"]
                if expected_freq > 0:
                    chisq_contrib = ((observed_freq - expected_freq) ** 2) / expected_freq
                else:
                    chisq_contrib = 0
                # นับเฉพาะตัวที่ออก "มากกว่า" ค่าคาดหวัง (เลขเด่น)
                actual_contrib = chisq_contrib if observed_freq > expected_freq else 0
                scoring_data[num]["chisq_contrib"] = actual_contrib
                chisq_results.append((num, actual_contrib))
            chisq_results.sort(key=lambda x: x[1], reverse=True)
            top_chisq = [f"{item[0]} (เด่น: {item[1]:.2f})" for item in chisq_results[:3]]
            for rank, item in enumerate(chisq_results[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 4. Regression to the Mean ---
            regression_results = []
            theoretical_period = total_possible_types
            for num in all_possible_nums:
                overdue_draws = scoring_data[num]["overdue_draws"]
                overdue_index = overdue_draws / theoretical_period if theoretical_period > 0 else 0
                scoring_data[num]["overdue_index"] = overdue_index
                regression_results.append((num, overdue_index))
            regression_results.sort(key=lambda x: x[1], reverse=True)
            top_regression = [f"{item[0]} ({item[1]:.2f} เท่า)" for item in regression_results[:3]]
            for rank, item in enumerate(regression_results[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 5. Markov Chain - แก้ให้ทำงานระดับ "งวด" จริง ---
            # ใช้ cat_per_draw แทนที่จะใช้ flat data
            # งวดล่าสุด = งวดสุดท้ายในลำดับเวลา → หาเลขทั้งหมดที่ออกในงวดนั้น
            top_markov_list = []
            last_draw_numbers = []

            # หางวดล่าสุดที่มีเลขออก (skip งวดที่ว่าง)
            for draw_nums in reversed(cat_per_draw):
                if draw_nums:
                    last_draw_numbers = draw_nums
                    break

            if last_draw_numbers and len(cat_per_draw) > 1:
                # เก็บเลขในงวดถัดไปทุกครั้งที่งวดก่อนหน้าออกเลขใดเลขหนึ่งใน last_draw_numbers
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

            # --- 6. EMA Weighting ---
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
            top_ema = [f"{item[0]} ({item[1]:.3f})" for item in ema_results[:3]]
            for rank, item in enumerate(ema_results[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 7. Digit Sum & Parity Filter ---
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

            # --- ระบบมติเอกฉันท์รวม (Ensemble Consensus) ---
            consensus_results = sorted(voting_scores.items(), key=lambda x: x[1], reverse=True)
            top_master_consensus = [
                f"🎯 {item[0]} (คะแนนโหวตรวม: {item[1]} แต้ม)"
                for item in consensus_results[:5]
            ]

            # ============================ DISPLAY UI ============================
            st.write("---")
            st.markdown(
                f"""<div style="background-color:#F8FAFC; padding:25px; border-radius:15px; border:3px solid #334155; text-align:center; margin-bottom:30px;">
<h2 style="color:#0F172A; margin-top:0; font-size:28px;">🎯 มติเอกฉันท์สูงสุดผสานพลัง 7 โมเดล (Ensemble Consensus Model)</h2>
<p style="color:#475569; font-size:15px; max-width:800px; margin:0 auto 15px auto;">นี่คือตัวเลือกที่มีคะแนนวิเคราะห์รวมสูงสุดจากระบบโหวตสถิติ โดยรวบรวมตัวเลขที่กรรมการทั้ง 7 สูตรคณิตศาสตร์ (Bayes, Poisson, Chi-Sq, Regression, Markov, EMA, Balanced) เห็นพ้องต้องกันว่ามีโครงสร้างสถิติสมบูรณ์ที่สุดสำหรับหมวด <b>{formula_cat}</b></p>
<div style="display:flex; justify-content:center; gap:15px; flex-wrap:wrap; font-size:20px; font-weight:bold; color:#1E3A8A;">
{' &nbsp;|&nbsp; '.join(top_master_consensus)}
</div>
</div>""",
                unsafe_allow_html=True
            )

            # แถวที่ 1
            row1_c1, row1_c2 = st.columns(2)
            with row1_c1:
                st.markdown(
                    f"""<div style="background-color:#F0FDF4; padding:20px; border-radius:12px; border-left:6px solid #16A34A; min-height:220px; margin-bottom:20px;">
<h3 style="color:#16A34A; margin-top:0;">📅 ตัวเลือก 1: ตามเงื่อนไขเดือน (Bayes' Theorem)</h3>
<p style="color:#4B5563; font-size:14px;">คัดเลขที่มีตัวเร่งน้ำหนักความน่าจะเป็นพุ่งสูงขึ้นเป็นพิเศษ เมื่อระบุเงื่อนไขเฉพาะเจาะจงว่าเข้าสู่เดือน <b>{target_month}</b></p>
<h4 style="color:#15803D; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
<p style="font-size:16px; font-weight:bold; color:#14532D;">{', '.join(top_bayes)}</p>
</div>""",
                    unsafe_allow_html=True
                )
            with row1_c2:
                st.markdown(
                    f"""<div style="background-color:#FEF2F2; padding:20px; border-radius:12px; border-left:6px solid #DC2626; min-height:220px; margin-bottom:20px;">
<h3 style="color:#DC2626; margin-top:0;">🔥 ตัวเลือก 2: เลขแข็งแกร่งสะสม (Chi-Square Anomaly)</h3>
<p style="color:#4B5563; font-size:14px;">ค้นหาค่าความเบี่ยงเบนเชิงบวกของตัวเลขที่ทำสถิติออกถล่มทลายบ่อยครั้งกว่าค่าเฉลี่ยสุ่มมาตรฐานอย่างมีนัยสำคัญ (เลขเด่นตลอดกาล)</p>
<h4 style="color:#991B1B; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
<p style="font-size:16px; font-weight:bold; color:#7F1D1D;">{', '.join(top_chisq)}</p>
</div>""",
                    unsafe_allow_html=True
                )

            # แถวที่ 2
            row2_c1, row2_c2 = st.columns(2)
            with row2_c1:
                st.markdown(
                    f"""<div style="background-color:#EFF6FF; padding:20px; border-radius:12px; border-left:6px solid #2563EB; min-height:220px; margin-bottom:20px;">
<h3 style="color:#2563EB; margin-top:0;">🔮 ตัวเลือก 3: อัตราเร่งงวดถัดไป (Poisson Distribution)</h3>
<p style="color:#4B5563; font-size:14px;">คำนวณความหนาแน่นความน่าจะเป็นว่าตัวเลขใดสุกงอมเต็มที่ตามหน่วยเวลา และมีโอกาสจะยอมสุ่มหมุนออกมาในงวดหน้ามากที่สุด</p>
<h4 style="color:#1E40AF; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
<p style="font-size:16px; font-weight:bold; color:#1E3A8A;">{', '.join(top_poisson)}</p>
</div>""",
                    unsafe_allow_html=True
                )
            with row2_c2:
                st.markdown(
                    f"""<div style="background-color:#FFFBEB; padding:20px; border-radius:12px; border-left:6px solid #D97706; min-height:220px; margin-bottom:20px;">
<h3 style="color:#D97706; margin-top:0;">❄️ ตัวเลือก 4: ดีดกลับสู่สมดุล (Regression to the Mean)</h3>
<p style="color:#4B5563; font-size:14px;">ใช้กฎของจำนวนมากกรองตัวเลขที่มีค่าดรรชนีการอั้นค้างสะสมสูงสุดยาวนานที่สุด เพื่อรอจังหวะดีดตัวกลับมารักษาค่าเฉลี่ยสุ่ม</p>
<h4 style="color:#92400E; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
<p style="font-size:16px; font-weight:bold; color:#78350F;">{', '.join(top_regression)}</p>
</div>""",
                    unsafe_allow_html=True
                )

            # แถวที่ 3
            row3_c1, row3_c2 = st.columns(2)
            with row3_c1:
                st.markdown(
                    f"""<div style="background-color:#FAFAF9; padding:20px; border-radius:12px; border-left:6px solid #78716C; min-height:220px; margin-bottom:20px;">
<h3 style="color:#78716C; margin-top:0;">⛓️ ตัวเลือก 5: ลำดับการเปลี่ยนสถานะ (Markov Chains)</h3>
<p style="color:#4B5563; font-size:14px;">คำนวณ Matrix ความน่าจะเป็นว่า จากงวดล่าสุดที่ออกเลข <b>{last_num_display}</b> ในอดีต วงล้อมักจะเปลี่ยนสถานะเหวี่ยงไปออกเลขใดต่อมากที่สุด</p>
<h4 style="color:#44403C; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
<p style="font-size:16px; font-weight:bold; color:#1C1917;">{', '.join(top_markov)}</p>
</div>""",
                    unsafe_allow_html=True
                )
            with row3_c2:
                st.markdown(
                    f"""<div style="background-color:#F5F3FF; padding:20px; border-radius:12px; border-left:6px solid #7C3AED; min-height:220px; margin-bottom:20px;">
<h3 style="color:#7C3AED; margin-top:0;">📈 ตัวเลือก 6: โมเมนตัมน้ำหนักงวดล่าสุด (EMA Weighting)</h3>
<p style="color:#4B5563; font-size:14px;">ให้ความสำคัญกับปัจจุบันมากกว่าอดีต โดยเพิ่มสัดส่วนคะแนนถ่วงน้ำหนักเร่งความเร็วให้งวดที่อยู่ใกล้เคียงปัจจุบัน เพื่อหาเลขที่กำลังฟอร์มตัวเป็นขาขึ้น</p>
<h4 style="color:#6D28D9; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
<p style="font-size:16px; font-weight:bold; color:#4C1D95;">{', '.join(top_ema)}</p>
</div>""",
                    unsafe_allow_html=True
                )

            # แถวที่ 4
            st.markdown(
                f"""<div style="background-color:#F0FDFA; padding:20px; border-radius:12px; border-left:6px solid #0D9488; min-height:160px; margin-bottom:20px;">
<h3 style="color:#0D9488; margin-top:0;">🎯 ตัวเลือก 7: สมดุลผลรวมหลักและพิกัดคู่-คี่ (Digit Sum & Parity Filter)</h3>
<p style="color:#4B5563; font-size:14px;">คัดกรองตัวเลขตามกฎ Normal Distribution โดยเลือกเฉพาะตัวเลขที่มีผลรวมแต้มหลัก (เช่น {', '.join([str(s) for s in top_3_sums])}) และโครงสร้างพิกัดรูปแบบ (<b>{most_common_parity}</b>) ที่สถิติประวัติศาสตร์ระบุว่าออกบ่อยที่สุด</p>
<h4 style="color:#0F766E; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
<p style="font-size:16px; font-weight:bold; color:#115E59;">{', '.join(top_balanced)}</p>
</div>""",
                unsafe_allow_html=True
            )

            # ตารางรวม Metrics ทั้งหมด
            st.write("---")
            st.subheader(f"📋 แผ่นตารางดัชนีคะแนนรวมสำหรับการตัดสินใจเชิงคณิตศาสตร์ [{formula_cat}]")

            summary_rows = []
            for num in all_possible_nums:
                summary_rows.append({
                    "ตัวเลข": num,
                    "คะแนนโหวตรวม (Consensus)": voting_scores.get(num, 0),
                    "ออกทั้งหมด (ครั้ง)": scoring_data[num]["freq"],
                    "ค้างปัจจุบัน (งวด)": scoring_data[num]["overdue_draws"],
                    "ดัชนีสูตรเบย์ (Lift)": round(scoring_data[num]["bayes_lift"], 3),
                    "โอกาสพัวซอง (Probability)": f"{scoring_data[num]['poisson_prob']*100:.1f}%",
                    "ค่าเบี่ยงเบนไคสแควร์": round(scoring_data[num]["chisq_contrib"], 3),
                    "ดัชนีอั้นสะสม (RTM Index)": round(scoring_data[num]["overdue_index"], 2),
                    "โมเมนตัม EMA": round(scoring_data[num]["ema_momentum"], 4),
                    "ผลรวมหลัก": get_digit_sum(num),
                    "พิกัดคู่-คี่": get_parity_pattern(num)
                })

            st.dataframe(
                pd.DataFrame(summary_rows).sort_values(
                    by="คะแนนโหวตรวม (Consensus)",
                    ascending=False
                ),
                use_container_width=True
            )
        else:
            st.info("กำลังเตรียมโมเดลคำนวณข้อมูล...")

    # ----------------------------------------------------------------
    #  TAB 4: ตารางประวัติทั้งหมด
    # ----------------------------------------------------------------
    with tab4:
        st.header("📋 ตารางประวัติพร้อมจำแนกประเภททั้งหมด")
        st.write(
            "ตารางแสดงผลลัพธ์ข้อมูลดิบสถิติย้อนหลัง โดยระบบได้ทำการแยกคอลัมน์พิเศษเพิ่มให้อัตโนมัติ "
            "เพื่อให้คุณสามารถค้นหา ตรวจสอบ หรือกรองดูพฤติกรรมตัวเลขได้อย่างสะดวก"
        )

        # เรียงจากใหม่ → เก่า โดยใช้ _draw_dt
        df_display = df.sort_values(by="_draw_dt", ascending=False, na_position="last").drop(
            columns=['_draw_dt', 'เดือน'], errors='ignore'
        )
        st.dataframe(df_display, use_container_width=True, hide_index=True)
