import streamlit as st
import pymongo
import certifi
import pandas as pd
import numpy as np
import os
import math
from collections import Counter

# 1. ตั้งค่าหน้าจอโปรแกรมเป็นแบบกว้าง (Wide Layout) เหมาะแก่การดูสถิติ
st.set_page_config(page_title="ระบบคำนวณและวิเคราะห์สถิติหวย 30 ปี", page_icon="📊", layout="wide")

# 2. เชื่อมต่อฐานข้อมูล MongoDB
MONGO_URI = st.secrets.get("MONGO_URI") or os.environ.get("MONGO_URI")

if not MONGO_URI:
    st.error("❌ ไม่พบ MONGO_URI กรุณาตั้งค่า Secrets ใน Streamlit Cloud")
    st.stop()

@st.cache_resource
def get_database_client():
    return pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())

@st.cache_data(ttl=3600)
def load_all_lottery_data():
    try:
        client = get_database_client()
        db = client["lottery_db"]
        collection = db["draws"]
        
        # ดึงข้อมูลทั้งหมดจากอดีตจนถึงปัจจุบัน เรียงจากงวดเก่าไปใหม่งวดล่าสุด
        cursor = collection.find().sort("timestamp", pymongo.ASCENDING)
        data = list(cursor)
        
        if not data:
            return pd.DataFrame()
            
        rows = []
        for doc in data:
            prizes = doc.get("prizes", {})
            
            def parse_value(val):
                if isinstance(val, list):
                    return ", ".join(val)
                return str(val)
                
            first_prize = parse_value(prizes.get("FIRST", "-")).strip()
            two_digit = parse_value(prizes.get("TWO_DIGIT", "-")).strip()
            three_front = parse_value(prizes.get("THREE_FRONT", "-")).strip()
            three_last = parse_value(prizes.get("THREE_LAST", "-")).strip()

            if len(first_prize) == 6 and first_prize.isdigit():
                last2_of_first = first_prize[-2:]
                last3_of_first = first_prize[-3:]
            else:
                last2_of_first = "-"
                last3_of_first = "-"
                
            rows.append({
                "งวดวันที่": doc.get("draw_date_str", "-"),
                "รางวัลที่ 1": first_prize,
                "เลขท้าย 2 ตัว": two_digit,
                "เลข 2 ตัวท้ายรางวัลที่ 1": last2_of_first,
                "เลขหน้า 3 ตัว": three_front,
                "เลขท้าย 3 ตัว": three_last,
                "เลข 3 ตัวท้ายรางวัลที่ 1": last3_of_first,
                "timestamp": doc.get("timestamp")
            })
            
        return pd.DataFrame(rows)
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

# โหลดข้อมูลเข้าสู่ตัวแปร DataFrame ของ Pandas
df = load_all_lottery_data()

st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📊 ระบบคำนวณและวิเคราะห์สถิติสลากกินแบ่งรัฐบาล</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6B7280;'>แดชบอร์ดตัดสินใจเชิงสถิติศาสตร์ ผสานพลังกรรมการ 7 โมเดลคณิตศาสตร์ สรุปมติเอกฉันท์</p>", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ ไม่พบข้อมูลในฐานข้อมูล MongoDB ของคุณ กรุณารันไฟล์ seed_history.py เพื่อนำเข้าสถิติย้อนหลังก่อนครับ")
else:
    def get_thai_month(date_text):
        parts = str(date_text).split()
        return parts[1] if len(parts) >= 2 else "ไม่ระบุ"
        
    df['เดือน'] = df['งวดวันที่'].apply(get_thai_month)
    
    st.sidebar.header("🗂️ คลังข้อมูลสะสม")
    st.sidebar.metric(label="จำนวนงวดสะสมในระบบ", value=f"{len(df)} งวด")
    st.sidebar.write(f"📅 เริ่มตั้งแต่งวด: `{df['งวดวันที่'].iloc[0]}`")
    st.sidebar.write(f"📅 ถึงงวดล่าสุด: `{df['งวดวันที่'].iloc[-1]}`")
    
    categories = [
        "เลขท้าย 2 ตัว", 
        "เลข 2 ตัวท้ายรางวัลที่ 1", 
        "เลขหน้า 3 ตัว", 
        "เลขท้าย 3 ตัว", 
        "เลข 3 ตัวท้ายรางวัลที่ 1"
    ]

    tab1, tab2, tab3, tab4 = st.tabs(["🎯 สถิติความถี่มวลรวม", "📅 สถิติเจาะลึกรายเดือน", "🔮 โมเดลคณิตศาสตร์เพื่อการตัดสินใจ", "📋 ตารางประวัติทั้งหมด"])
    
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

    with tab2:
        st.header("📅 วิเคราะห์แนวโน้มจำเพาะเจาะจงเดือน")
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            selected_month = st.selectbox("เลือกเดือนที่ต้องการเปิดสถิติ:", df['เดือน'].unique())
        with m_col2:
            selected_month_cat = st.selectbox("เลือกประเภทตัวเลขที่ต้องการกรอง:", categories, key="tab2_cat")
            
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

    with tab3:
        st.header("🔮 แดชบอร์ดผสานพลังโมเดลคณิตศาสตร์และมติเอกฉันท์รวม")
        
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            formula_cat = st.selectbox("1. เลือกประเภทตัวเลขหลักที่ต้องการวิเคราะห์:", categories, key="tab3_cat")
        with f_col2:
            target_month = st.selectbox("2. เลือกเงื่อนไขเดือนสำหรับคำนวณสูตรเบย์:", df['เดือน'].unique(), key="tab3_month")
            
        cat_flat_data = get_flat_series(df, formula_cat)
        
        if not cat_flat_data.empty:
            sample_len = len(str(cat_flat_data.iloc[0]))
            total_items_count = len(cat_flat_data)
            all_possible_nums = [f"{i:02d}" if sample_len == 2 else f"{i:03d}" for i in range(100 if sample_len == 2 else 1000)]
            total_possible_types = len(all_possible_nums)
            
            last_seen_idx = {}
            for idx, val in enumerate(cat_flat_data):
                last_seen_idx[str(val)] = idx
                
            # สร้างระบบนับคะแนนโหวต (Consensus Voting System) - เต็มก้อนละ 10 แต้มสำหรับที่ 1
            voting_scores = {n: 0 for n in all_possible_nums}
            
            # --- 1. สูตรเบย์ ---
            df_m = df[df['เดือน'] == target_month]
            m_flat = get_flat_series(df_m, formula_cat)
            total_m_items = len(m_flat)
            bayes_results = []
            for num in all_possible_nums:
                p_num = cat_flat_data.value_counts().get(num, 0) / total_items_count if total_items_count > 0 else 0
                p_num_given_m = m_flat.value_counts().get(num, 0) / total_m_items if total_m_items > 0 else 0
                lift = (p_num_given_m / p_num) if p_num > 0 else 0
                bayes_results.append((num, lift))
            bayes_results.sort(key=lambda x: x[1], reverse=True)
            top_bayes = [f"{item[0]} (x{item[1]:.2f})" for item in bayes_results[:3]]
            for rank, item in enumerate(bayes_results[:10]):
                voting_scores[item[0]] += (10 - rank) # อันดับ 1 ได้ 10 คะแนน, อันดับ 10 ได้ 1 คะแนน

            # --- 2. สูตรพัวซอง ---
            poisson_results = []
            for num in all_possible_nums:
                occurrences = cat_flat_data.value_counts().get(num, 0)
                lam = occurrences / total_items_count if total_items_count > 0 else 0
                last_idx = last_seen_idx.get(num, -1)
                overdue_draws = total_items_count - 1 - last_idx if last_idx != -1 else total_items_count
                prob_to_appear = 1.0 - math.exp(-lam * (overdue_draws + 1)) if lam > 0 else 0
                poisson_results.append((num, prob_to_appear))
            poisson_results.sort(key=lambda x: x[1], reverse=True)
            top_poisson = [f"{item[0]} ({item[1]*100:.1f}%)" for item in poisson_results[:3]]
            for rank, item in enumerate(poisson_results[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 3. สูตรไคสแควร์ ---
            expected_freq = total_items_count / total_possible_types
            chisq_results = []
            for num in all_possible_nums:
                observed_freq = cat_flat_data.value_counts().get(num, 0)
                chisq_contrib = ((observed_freq - expected_freq) ** 2) / expected_freq if expected_freq > 0 else 0
                chisq_results.append((num, chisq_contrib if observed_freq > expected_freq else 0))
            chisq_results.sort(key=lambda x: x[1], reverse=True)
            top_chisq = [f"{item[0]} (เด่น: {item[1]:.2f})" for item in chisq_results[:3]]
            for rank, item in enumerate(chisq_results[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 4. สูตรการถอยกลับสู่ค่าเฉลี่ย ---
            regression_results = []
            theoretical_period = total_possible_types
            for num in all_possible_nums:
                last_idx = last_seen_idx.get(num, -1)
                overdue_draws = total_items_count - 1 - last_idx if last_idx != -1 else total_items_count
                overdue_index = overdue_draws / theoretical_period
                regression_results.append((num, overdue_index))
            regression_results.sort(key=lambda x: x[1], reverse=True)
            top_regression = [f"{item[0]} ({item[1]:.2f} เท่า)" for item in regression_results[:3]]
            for rank, item in enumerate(regression_results[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 5. ห่วงโซ่มาร์คอฟ ---
            top_markov_list = []
            if len(cat_flat_data) > 1:
                last_num_in_history = str(cat_flat_data.iloc[-1])
                next_nums = []
                for i in range(len(cat_flat_data) - 1):
                    if str(cat_flat_data.iloc[i]) == last_num_in_history:
                        next_nums.append(str(cat_flat_data.iloc[i+1]))
                if next_nums:
                    markov_counts = Counter(next_nums)
                    markov_sorted = markov_counts.most_common(10)
                    top_markov_list = [f"{item[0]}" for item in markov_sorted[:3]]
                    for rank, item in enumerate(markov_sorted):
                        voting_scores[item[0]] += (10 - rank)
            top_markov = top_markov_list if top_markov_list else ["-"]

            # --- 6. ค่าน้ำหนักความเร่งเฉลี่ย (EMA) ---
            alpha_decay = 0.05
            ema_scores = {n: 0.0 for n in all_possible_nums}
            for idx, val in enumerate(cat_flat_data):
                v_str = str(val)
                if v_str in ema_scores:
                    dist = total_items_count - 1 - idx
                    ema_scores[v_str] += alpha_decay * ((1 - alpha_decay) ** dist)
            ema_results = sorted(ema_scores.items(), key=lambda x: x[1], reverse=True)
            top_ema = [f"{item[0]} ({item[1]:.3f})" for item in ema_results[:3]]
            for rank, item in enumerate(ema_results[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 7. สมดุลผลรวมและคู่คี่ ---
            def get_digit_sum(n_str):
                return sum(int(c) for c in n_str if c.isdigit())
            def get_parity_pattern(n_str):
                return "-".join(["คี่" if int(c) % 2 != 0 else "คู่" for c in n_str if c.isdigit()])

            hist_sums = [get_digit_sum(str(n)) for n in cat_flat_data]
            hist_parities = [get_parity_pattern(str(n)) for n in cat_flat_data]
            top_3_sums = [item[0] for item in Counter(hist_sums).most_common(3)]
            most_common_parity = Counter(hist_parities).most_common(1)[0][0] if hist_parities else ""

            balanced_nums = []
            for num in all_possible_nums:
                if get_digit_sum(num) in top_3_sums and get_parity_pattern(num) == most_common_parity:
                    balanced_nums.append((num, cat_flat_data.value_counts().get(num, 0)))
            balanced_nums.sort(key=lambda x: x[1], reverse=True)
            top_balanced = [f"{item[0]}" for item in balanced_nums[:3]]
            for rank, item in enumerate(balanced_nums[:10]):
                voting_scores[item[0]] += (10 - rank)

            # --- 🌟 ส่วนการประมวลผลระบบมติเอกฉันท์รวม (Consensus Winner) 🌟 ---
            consensus_results = sorted(voting_scores.items(), key=lambda x: x[1], reverse=True)
            top_master_consensus = [f"🎯 {item[0]} (คะแนนโหวตรวม: {item[1]} แต้ม)" for item in consensus_results[:5]]

            # ---------------- DISPLAY UI ----------------
            st.write("---")
            # โชว์ป้ายประกาศ Master Consensus ตัวใหญ่สุดยอดไว้บนสุดแผงตัดสินใจ
            st.markdown(f"""<div style="background-color:#F8FAFC; padding:25px; border-radius:15px; border:3px solid #334155; text-align:center; margin-bottom:30px;">
                <h2 style="color:#0F172A; margin-top:0; font-size:28px;">🎯 มติเอกฉันท์สูงสุดผสานพลัง 7 โมเดล (Ensemble Consensus Model)</h2>
                <p style="color:#475569; font-size:15px; max-w:800px; margin:0 auto 15px auto;">นี่คือตัวเลือกที่มีคะแนนวิเคราะห์รวมสูงสุดจากระบบโหวตสถิติ โดยรวบรวมตัวเลขที่กรรมการทั้ง 7 สูตรคณิตศาสตร์ (Bayes, Poisson, Chi-Sq, Regression, Markov, EMA, Balanced) เห็นพ้องต้องกันว่ามีโครงสร้างสถิติสมบูรณ์ที่สุดสำหรับหมวด <b>{formula_cat}</b></p>
                <div style="display:flex; justify-content:center; gap:15px; flex-wrap:wrap; font-size:20px; font-weight:bold; color:#1E3A8A;">
                    {' &nbsp;|&nbsp; '.join(top_master_consensus)}
                </div>
            </div>""", unsafe_allow_html=True)
            
            # แถวที่ 1
            row1_c1, row1_c2 = st.columns(2)
            with row1_c1:
                st.markdown(f"""<div style="background-color:#F0FDF4; padding:20px; border-radius:12px; border-left:6px solid #16A34A; min-height:220px; margin-bottom:20px;">
                    <h3 style="color:#16A34A; margin-top:0;">📅 ตัวเลือก 1: ตามเงื่อนไขเดือน (Bayes' Theorem)</h3>
                    <p style="color:#4B5563; font-size:14px;">คัดเลขที่มีตัวเร่งน้ำหนักความน่าจะเป็นพุ่งสูงขึ้นเป็นพิเศษ เมื่อระบุเงื่อนไขเฉพาะเจาะจงว่าเข้าสู่เดือน <b>{target_month}</b></p>
                    <h4 style="color:#15803D; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
                    <p style="font-size:16px; font-weight:bold; color:#14532D;">{', '.join(top_bayes)}</p>
                </div>""", unsafe_allow_html=True)
            with row1_c2:
                st.markdown(f"""<div style="background-color:#FEF2F2; padding:20px; border-radius:12px; border-left:6px solid #DC2626; min-height:220px; margin-bottom:20px;">
                    <h3 style="color:#DC2626; margin-top:0;">🔥 ตัวเลือก 2: เลขแข็งแกร่งสะสม (Chi-Square Anomaly)</h3>
                    <p style="color:#4B5563; font-size:14px;">ค้นหาค่าความเบี่ยงเบนเชิงบวกของตัวเลขที่ทำสถิติออกถล่มทลายบ่อยครั้งกว่าค่าเฉลี่ยสุ่มมาตรฐานอย่างมีนัยสำคัญ (เลขเด่นตลอดกาล)</p>
                    <h4 style="color:#991B1B; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
                    <p style="font-size:16px; font-weight:bold; color:#7F1D1D;">{', '.join(top_chisq)}</p>
                </div>""", unsafe_allow_html=True)

            # แถวที่ 2
            row2_c1, row2_c2 = st.columns(2)
            with row2_c1:
                st.markdown(f"""<div style="background-color:#EFF6FF; padding:20px; border-radius:12px; border-left:6px solid #2563EB; min-height:220px; margin-bottom:20px;">
                    <h3 style="color:#2563EB; margin-top:0;">🔮 ตัวเลือก 3: อัตราเร่งงวดถัดไป (Poisson Distribution)</h3>
                    <p style="color:#4B5563; font-size:14px;">คำนวณความหนาแน่นความน่าจะเป็นว่าตัวเลขใดสุกงอมเต็มที่ตามหน่วยเวลา และมีโอกาสจะยอมสุ่มหมุนออกมาในงวดหน้ามากที่สุด</p>
                    <h4 style="color:#1E40AF; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
                    <p style="font-size:16px; font-weight:bold; color:#1E3A8A;">{', '.join(top_poisson)}</p>
                </div>""", unsafe_allow_html=True)
            with row2_c2:
                st.markdown(f"""<div style="background-color:#FFFBEB; padding:20px; border-radius:12px; border-left:6px solid #D97706; min-height:220px; margin-bottom:20px;">
                    <h3 style="color:#D97706; margin-top:0;">❄️ ตัวเลือก 4: ดีดกลับสู่สมดุล (Regression to the Mean)</h3>
                    <p style="color:#4B5563; font-size:14px;">ใช้กฎของจำนวนมากกรองตัวเลขที่มีค่าดรรชนีการอั้นค้างสะสมสูงสุดยาวนานที่สุด เพื่อรอจังหวะดีดตัวกลับมารักษาค่าเฉลี่ยสุ่ม</p>
                    <h4 style="color:#92400E; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
                    <p style="font-size:16px; font-weight:bold; color:#78350F;">{', '.join(top_regression)}</p>
                </div>""", unsafe_allow_html=True)

            # แถวที่ 3
            row3_c1, row3_c2 = st.columns(2)
            with row3_c1:
                st.markdown(f"""<div style="background-color:#FAFAF9; padding:20px; border-radius:12px; border-left:6px solid #78716C; min-height:220px; margin-bottom:20px;">
                    <h3 style="color:#78716C; margin-top:0;">⛓️ ตัวเลือก 5: ลำดับการเปลี่ยนสถานะ (Markov Chains)</h3>
                    <p style="color:#4B5563; font-size:14px;">คำนวณ Matrix ความน่าจะเป็นว่า จากงวดล่าสุดที่ออกเลข <b>{str(cat_flat_data.iloc[-1])}</b> ในอดีต 30 ปี วงล้อมักจะเปลี่ยนสถานะเหวี่ยงไปออกเลขใดต่อมากที่สุด</p>
                    <h4 style="color:#44403C; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
                    <p style="font-size:16px; font-weight:bold; color:#1C1917;">{', '.join(top_markov)}</p>
                </div>""", unsafe_allow_html=True)
            with row3_c2:
                st.markdown(f"""<div style="background-color:#F5F3FF; padding:20px; border-radius:12px; border-left:6px solid #7C3AED; min-height:220px; margin-bottom:20px;">
                    <h3 style="color:#7C3AED; margin-top:0;">📈 ตัวเลือก 6: โมเมนตัมน้ำหนักงวดล่าสุด (EMA Weighting)</h3>
                    <p style="color:#4B5563; font-size:14px;">ให้ความสำคัญกับปัจจุบันมากกว่าอดีต โดยเพิ่มสัดส่วนคะแนนถ่วงน้ำหนักเร่งความเร็วให้งวดที่อยู่ใกล้เคียงปัจจุบัน เพื่อหาเลขที่กำลังฟอร์มตัวเป็นขาขึ้น</p>
                    <h4 style="color:#6D28D9; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
                    <p style="font-size:16px; font-weight:bold; color:#4C1D95;">{', '.join(top_ema)}</p>
                </div>""", unsafe_allow_html=True)

            # แถวที่ 4
            st.markdown(f"""<div style="background-color:#F0FDFA; padding:20px; border-radius:12px; border-left:6px solid #0D9488; min-height:160px; margin-bottom:20px;">
                <h3 style="color:#0D9488; margin-top:0;">🎯 ตัวเลือก 7: สมดุลผลรวมหลักและพิกัดคู่-คี่ (Digit Sum & Parity Filter)</h3>
                <p style="color:#4B5563; font-size:14px;">คัดกรองตัวเลขตามกฎ Normal Distribution โดยเลือกเฉพาะตัวเลขที่มีผลรวมแต้มหลัก (เช่น {', '.join([str(s) for s in top_3_sums])}) และโครงสร้างพิกัดรูปแบบ (<b>{most_common_parity}</b>) ที่สถิติประวัติศาสตร์ 30 ปีระบุว่าออกบ่อยที่สุด</p>
                <h4 style="color:#0F766E; margin-bottom:5px;">🔝 อันดับแนะนำสูงสุด:</h4>
                <p style="font-size:16px; font-weight:bold; color:#115E59;">{', '.join(top_balanced)}</p>
            </div>""", unsafe_allow_html=True)

            # ตารางรวมสรุป Metrics ทั้งหมด 7 อัลกอริทึม + คะแนนโหวตรวม
            st.write("---")
            st.subheader(f"📋 แผ่นตารางดัชนีคะแนนรวมสำหรับการตัดสินใจเชิงคณิตศาสตร์ [{formula_cat}]")
            
            summary_rows = []
            bayes_dict = dict(bayes_results)
            poisson_dict = dict(poisson_results)
            chisq_dict = dict(chisq_results)
            regr_dict = dict(regression_results)
            overdue_dict = {item[0]: item[2] for item in regression_results}
            ema_dict = dict(ema_results)
            freq_dict = cat_flat_data.value_counts().to_dict()
            
            for num in all_possible_nums:
                summary_rows.append({
                    "ตัวเลข": num,
                    "คะแนนโหวตรวม (Consensus)": voting_scores.get(num, 0),
                    "ออกทั้งหมด (ครั้ง)": freq_dict.get(num, 0),
                    "ค้างปัจจุบัน (งวด)": overdue_dict.get(num, 0),
                    "ดัชนีสูตรเบย์ (Lift)": round(bayes_dict.get(num, 0), 3),
                    "โอกาสพัวซอง (Probability)": f"{poisson_dict.get(num, 0)*100:.1f}%",
                    "ค่าเบี่ยงเบนไคสแควร์": round(chisq_dict.get(num, 0), 3),
                    "ดัชนีอั้นสะสม (RTM Index)": round(regr_dict.get(num, 0), 2),
                    "โมเมนตัม EMA": round(ema_dict.get(num, 0), 4),
                    "ผลรวมหลัก": get_digit_sum(num),
                    "พิกัดคู่-คี่": get_parity_pattern(num)
                })
                
            # เรียงตารางตามคะแนนโหวตมติเอกฉันท์จากมากไปน้อย เพื่อให้ง่ายต่อการดูภาพรวม
            st.dataframe(pd.DataFrame(summary_rows).sort_values(by="คะแนนโหวตรวม (Consensus)", ascending=False), use_container_width=True)
        else:
            st.info("กำลังเตรียมโมเดลคำนวณข้อมูล...")

    with tab4:
        st.header("📋 ตารางประวัติพร้อมจำแนกประเภททั้งหมด")
        st.write("ตารางแสดงผลลัพธ์ข้อมูลดิบสถิติ 30 ปี โดยระบบได้ทำการแยกคอลัมน์พิเศษเพิ่มให้อัตโนมัติ เพื่อให้คุณสามารถค้นหา ตรวจสอบ หรือกรองดูพฤติกรรมตัวเลขได้อย่างสะดวก")
        st.dataframe(df.sort_values(by="timestamp", ascending=False).drop(columns=['timestamp'], errors='ignore'), use_container_width=True)
