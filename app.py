import streamlit as st
import pymongo
import certifi
import pandas as pd
import numpy as np
import os
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

            # 🛠️ แยกประเภทกลุ่มย่อยตามเงื่อนไขของคุณ
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

# ฟังก์ชันช่วยกระจายข้อมูลตัวเลข (เช่น "290, 742" ให้แยกนับเป็น "290" และ "742" อย่างถูกต้อง)
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
st.markdown("<p style='text-align: center; color: #6B7280;'>โปรแกรมคำนวณความน่าจะเป็นแยกประเภทตัวเลขอย่างละเอียดจากคลังประวัติศาสตร์</p>", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ ไม่พบข้อมูลในฐานข้อมูล MongoDB ของคุณ กรุณารันไฟล์ seed_history.py เพื่อนำเข้าสถิติย้อนหลังก่อนครับ")
else:
    # สกัดชื่อเดือนภาษาไทยออกมาจากข้อความวันที่
    def get_thai_month(date_text):
        parts = str(date_text).split()
        return parts[1] if len(parts) >= 2 else "ไม่ระบุ"
        
    df['เดือน'] = df['งวดวันที่'].apply(get_thai_month)
    
    # เมนูด้านข้างแสดงประวัติภาพรวม ข้อมูลสะสม
    st.sidebar.header("🗂️ คลังข้อมูลสะสม")
    st.sidebar.metric(label="จำนวนงวดสะสมในระบบ", value=f"{len(df)} งวด")
    st.sidebar.write(f"📅 เริ่มตั้งแต่งวด: `{df['งวดวันที่'].iloc[0]}`")
    st.sidebar.write(f"📅 ถึงงวดล่าสุด: `{df['งวดวันที่'].iloc[-1]}`")
    
    # รายชื่อประเภทตัวเลขทั้ง 5 กลุ่มตามที่ผู้ใช้กำหนด
    categories = [
        "เลขท้าย 2 ตัว", 
        "เลข 2 ตัวท้ายรางวัลที่ 1", 
        "เลขหน้า 3 ตัว", 
        "เลขท้าย 3 ตัว", 
        "เลข 3 ตัวท้ายรางวัลที่ 1"
    ]

    # แบ่งหน้าแสดงผลออกเป็น 4 แท็บสำหรับการวิเคราะห์รูปแบบต่างๆ
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 สถิติความถี่มวลรวม", "📅 สถิติเจาะลึกรายเดือน", "🔮 สูตรคำนวณแนวโน้มงวดถัดไป", "📋 ตารางประวัติทั้งหมด"])
    
    with tab1:
        st.header("🎯 อันดับตัวเลขที่ออกบ่อยที่สุด (Frequency Analysis)")
        
        # ให้ผู้ใช้เลือกประเภทที่ต้องการวิเคราะห์ความถี่
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
                
            # ส่วนคำนวณสถิติแยกรายหลัก (หลักร้อย/หลักสิบ/หลักหน่วย) อัตโนมัติสอดคล้องกับประเภทตัวเลข
            st.write("---")
            st.subheader(f"🔢 สถิติความถี่แยกตามตำแหน่งหลักของ [{selected_cat}]")
            
            # ตรวจสอบความยาวตัวเลขว่าเป็นแบบ 2 หลัก หรือ 3 หลัก
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
        else:
            st.info("ไม่มีข้อมูลเพียงพอในการประมวลผลหมวดหมู่นี้")

    with tab2:
        st.header("📅 วิเคราะห์แนวโน้มจำเพาะเจาะจงเดือน")
        st.write("คัดกรองข้อมูลสถิติ 30 ปี เพื่อดูพฤติกรรมการออกรางวัลที่มักจะเกิดซ้ำในเดือนนั้นๆ")
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            selected_month = st.selectbox("เลือกเดือนที่ต้องการเปิดสถิติ:", df['เดือน'].unique())
        with m_col2:
            selected_month_cat = st.selectbox("เลือกประเภทตัวเลขที่ต้องการกรอง:", categories, key="tab2_cat")
            
        df_month = df[df['month'] == selected_month if 'month' in df else df['เดือน'] == selected_month]
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
        else:
            st.write("ไม่มีข้อมูลตัวเลขในเดือนนี้")

    with tab3:
        st.header("🔮 ระบบประมวลผลและคำนวณเลขเด่นด้วยสมการสถิติ")
        st.write("เลือกประเภทที่คุณต้องการให้โปรแกรมรันสูตรคณิตศาสตร์เพื่อหาแนวโน้มน้ำหนักตัวเลขงวดถัดไป")
        
        formula_cat = st.selectbox("เลือกประเภทตัวเลขที่ต้องการให้โปรแกรมคำนวณ:", categories, key="tab3_cat")
        cat_flat_data = get_flat_series(df, formula_cat)
        
        if not cat_flat_data.empty:
            # คำนวณหาความยาวตัวเลข (2 ตัว หรือ 3 ตัว) ของกลุ่มที่เลือก
            sample_len = len(str(cat_flat_data.iloc[0]))
            
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown("<div style='background-color:#FEF3C7; padding:20px; border-radius:10px; border-left:6px solid #D97706; min-height:240px;'>", unsafe_allow_html=True)
                st.subheader("🔥 สูตรเลขเด่นยอดนิยม (Hot Numbers)")
                st.write(f"คำนวณจากชุดตัวเลข {formula_cat} ที่มีอัตราเร่งและการออกซ้ำสะสมสูงที่สุดในประวัติศาสตร์")
                hot_list = cat_flat_data.value_counts().head(5).index.tolist()
                st.markdown(f"<h2 style='color:#B45309; letter-spacing: 2px;'>{', '.join(hot_list)}</h2>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with c2:
                st.markdown("<div style='background-color:#E0F2FE; padding:20px; border-radius:10px; border-left:6px solid #0284C7; min-height:240px;'>", unsafe_allow_html=True)
                st.subheader("❄️ สูตรเลขค้างแผง (Cold Numbers)")
                st.write(f"คำนวณหาตัวเลขในหมวด {formula_cat} ที่อั้นไว้นานที่สุดหรือออกน้อยที่สุด ซึ่งมีแนวโน้มดีดกลับตามกฎค่าเฉลี่ยสถิติ")
                
                # สร้างเลขทั้งหมดที่เป็นไปได้ (00-99 หรือ 000-999)
                all_possible_nums = [f"{i:02d}" if sample_len == 2 else f"{i:03d}" for i in range(100 if sample_len == 2 else 1000)]
                
                # หาจุดที่เจอครั้งล่าสุด
                last_seen_dict = {}
                for idx, val in cat_flat_data.items():
                    last_seen_dict[str(val)] = idx
                    
                cold_scores = [(n, last_seen_dict.get(n, -1)) for n in all_possible_nums]
                cold_scores.sort(key=lambda x: x[1]) # เรียงงวดเก่าไปใหม่ ตัวที่ไม่ออกนานสุดจะอยู่บน
                cold_list = [item[0] for item in cold_scores[:5]]
                st.markdown(f"<h2 style='color:#0369A1; letter-spacing: 2px;'>{', '.join(cold_list)}</h2>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with c3:
                st.markdown("<div style='background-color:#DCFCE7; padding:20px; border-radius:10px; border-left:6px solid #16A34A; min-height:240px;'>", unsafe_allow_html=True)
                st.subheader("🎲 สูตรพิกัดหลักผสม (Probability Matrix)")
                st.write("วิเคราะห์แยกแต่ละตำแหน่ง (ร้อย/สิบ/หน่วย) นำตัวเลขที่มีค่าฐานนิยม (Mode) หรือออกบ่อยที่สุดของแต่ละหลักมาไขว้จับคู่กัน")
                
                if sample_len == 2:
                    tens = [str(n)[0] for n in cat_flat_data if len(str(n))==2 and str(n).isdigit()]
                    units = [str(n)[1] for n in cat_flat_data if len(str(n))==2 and str(n).isdigit()]
                    top_tens = [item[0] for item in Counter(tens).most_common(2)]
                    top_units = [item[0] for item in Counter(units).most_common(2)]
                    matrix_list = [f"{t}{u}" for t in top_tens for u in top_units]
                else:
                    hundreds = [str(n)[0] for n in cat_flat_data if len(str(n))==3 and str(n).isdigit()]
                    tens = [str(n)[1] for n in cat_flat_data if len(str(n))==3 and str(n).isdigit()]
                    units = [str(n)[2] for n in cat_flat_data if len(str(n))==3 and str(n).isdigit()]
                    top_h = [item[0] for item in Counter(hundreds).most_common(1)]
                    top_t = [item[0] for item in Counter(tens).most_common(2)]
                    top_u = [item[0] for item in Counter(units).most_common(2)]
                    matrix_list = [f"{h}{t}{u}" for h in top_h for t in top_t for u in top_u]
                    
                st.markdown(f"<h2 style='color:#15803D; letter-spacing: 2px;'>{', '.join(matrix_list)}</h2>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("กำลังเตรียมโมเดลข้อมูล...")

    with tab4:
        st.header("📋 ตารางประวัติพร้อมจำแนกประเภททั้งหมด")
        st.write("ตารางแสดงผลลัพธ์ข้อมูลดิบสถิติ 30 ปี โดยระบบได้ทำการแยกคอลัมน์พิเศษเพิ่มให้อัตโนมัติ เพื่อให้คุณสามารถค้นหา ตรวจสอบ หรือกรองดูพฤติกรรมตัวเลขได้อย่างสะดวก")
        # แสดงตารางเรียงจากงวดล่าสุดย้อนลงไปอดีต
        st.dataframe(df.sort_values(by="timestamp", ascending=False).drop(columns=['timestamp'], errors='ignore'), use_container_width=True)
