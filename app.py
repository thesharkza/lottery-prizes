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
                
            rows.append({
                "งวดวันที่": doc.get("draw_date_str", "-"),
                "รางวัลที่ 1": parse_value(prizes.get("FIRST", "-")),
                "เลขท้าย 2 ตัว": parse_value(prizes.get("TWO_DIGIT", "-")),
                "เลขหน้า 3 ตัว": parse_value(prizes.get("THREE_FRONT", "-")),
                "เลขท้าย 3 ตัว": parse_value(prizes.get("THREE_LAST", "-")),
                "timestamp": doc.get("timestamp")
            })
            
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame()

# โหลดข้อมูลเข้าสู่ตัวแปร DataFrame ของ Pandas
df = load_all_lottery_data()

st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📊 ระบบคำนวณและวิเคราะห์สถิติสลากกินแบ่งรัฐบาล</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6B7280;'>ประมวลผลความน่าจะเป็นทางคณิตศาสตร์จากสถิติมวลรวมย้อนหลังและปัจจุบัน</p>", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ ไม่พบข้อมูลในฐานข้อมูล MongoDB ของคุณ กรุณารันไฟล์ seed_history.py เพื่อนำเข้าสถิติย้อนหลังก่อนครับ")
else:
    # สกัดชื่อเดือนภาษาไทยออกมาจากข้อความวันที่ (เช่น "16 พฤษภาคม 2539")
    def get_thai_month(date_text):
        parts = str(date_text).split()
        return parts[1] if len(parts) >= 2 else "ไม่ระบุ"
        
    df['เดือน'] = df['งวดวันที่'].apply(get_thai_month)
    
    # เมนูด้านข้างแสดงประวัติภาพรวม ข้อมูลสะสม
    st.sidebar.header("🗂️ คลังข้อมูลดิบ")
    st.sidebar.metric(label="จำนวนงวดสะสมทั้งหมดในระบบ", value=f"{len(df)} งวด")
    st.sidebar.write(f"📅 ประวัติตั้งแต่งวด: `{df['งวดวันที่'].iloc[0]}`")
    st.sidebar.write(f"📅 ถึงงวดล่าสุด: `{df['งวดวันที่'].iloc[-1]}`")
    
    # เตรียมข้อมูลสำหรับคำนวณหลักสิบและหลักหน่วยไว้ล่วงหน้า
    df_clean = df[df['เลขท้าย 2 ตัว'] != "-"]
    tens, units = [], []
    for num in df_clean['เลขท้าย 2 ตัว']:
        cleaned_num = str(num).strip()
        if len(cleaned_num) == 2 and cleaned_num.isdigit():
            tens.append(int(cleaned_num[0]))
            units.append(int(cleaned_num[1]))

    # แบ่งหน้าแสดงผลออกเป็น 4 แท็บสำหรับการวิเคราะห์รูปแบบต่างๆ
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 สถิติความถี่มวลรวม", "📅 สถิติเจาะลึกรายเดือน", "🔮 สูตรคำนวณแนวโน้มงวดถัดไป", "📋 ตารางประวัติทั้งหมด"])
    
    with tab1:
        st.header("🎯 อันดับตัวเลขที่ออกบ่อยที่สุด (Frequency Analysis)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔝 เลขท้าย 2 ตัวที่ออกบ่อยที่สุด (Top 10)")
            if not df_clean.empty:
                top_10_two = df_clean['เลขท้าย 2 ตัว'].value_counts().head(10)
                st.bar_chart(top_10_two)
                
                top_df = top_10_two.reset_index()
                top_df.columns = ["ตัวเลข", "จำนวนครั้งที่ออก"]
                st.dataframe(top_df, use_container_width=True)
                
        with col2:
            st.subheader("🔢 สถิติการออกแยกตามตำแหน่งหลัก")
            if tens and units:
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.write("**สถิติความถี่ของ หลักสิบ (0-9)**")
                    st.bar_chart(pd.Series(tens).value_counts().sort_index())
                with sc2:
                    st.write("**สถิติความถี่ของ หลักหน่วย (0-9)**")
                    st.bar_chart(pd.Series(units).value_counts().sort_index())
            else:
                st.write("ไม่มีข้อมูลตัวเลขที่สมบูรณ์พอในการแยกหลัก")

    with tab2:
        st.header("📅 วิเคราะห์แนวโน้มจำเพาะเดือน")
        st.write("คัดกรองสถิติเพื่อดูว่าในการออกรางวัลย้อนหลัง 30 ปี ตัวเลขใดที่มักจะออกบ่อยในเดือนนั้นๆ เป็นพิเศษ")
        
        selected_month = st.selectbox("เลือกเดือนที่ต้องการเปิดสถิติ:", df['เดือน'].unique())
        df_month = df[df['เดือน'] == selected_month]
        
        st.info(f"พบข้อมูลประวัติศาสตร์สลากที่เคยออกในเดือน **{selected_month}** ทั้งหมดจำนวน **{len(df_month)}** งวด")
        
        if not df_month.empty:
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.write(f"📊 **เลขท้าย 2 ตัวที่ถูกโฉลกกับเดือน {selected_month} (ออกบ่อยที่สุด)**")
                df_m_two = df_month[df_month['เลขท้าย 2 ตัว'] != "-"]
                if not df_m_two.empty:
                    st.dataframe(df_m_two['เลขท้าย 2 ตัว'].value_counts().head(10), use_container_width=True)
            with m_col2:
                st.write(f"📊 **เลขท้ายรางวัลที่ 1 (สองตัวท้าย) ที่ออกบ่อยที่สุดในเดือน {selected_month}**")
                df_m_first = df_month[df_month['รางวัลที่ 1'] != "-"]
                if not df_m_first.empty:
                    last_2_first = df_m_first['รางวัลที่ 1'].apply(lambda x: str(x)[-2:] if len(str(x))>=2 else None).dropna()
                    if not last_2_first.empty:
                        st.dataframe(last_2_first.value_counts().head(10), use_container_width=True)

    with tab3:
        st.header("🔮 ระบบประมวลผลคำนวณแนวโน้มด้วยสมการสถิติ")
        st.write("ใช้หลักคณิตศาสตร์สถิติวางโมเดลคำนวณชุดตัวเลขที่มีน้ำหนักน่าจะเป็นสูงสุดสำหรับงวดถัดไป")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("<div style='background-color:#FEF3C7; padding:20px; border-radius:10px; border-left:6px solid #D97706; min-height:220px;'>", unsafe_allow_html=True)
            st.subheader("🔥 สูตรเลขเด่นยอดนิยม (Hot Numbers)")
            st.write("คำนวณจากตัวเลขกลุ่มที่มีอัตราเร่งและสถิติการออกซ้ำสะสมสูงที่สุดในระบบ")
            if not df_clean.empty:
                hot_list = df_clean['เลขท้าย 2 ตัว'].value_counts().head(5).index.tolist()
                st.markdown(f"<h2 style='color:#B45309;'>{', '.join(hot_list)}</h2>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c2:
            st.markdown("<div style='background-color:#E0F2FE; padding:20px; border-radius:10px; border-left:6px solid #0284C7; min-height:220px;'>", unsafe_allow_html=True)
            st.subheader("❄️ สูตรเลขค้างแผง (Cold/Due Numbers)")
            st.write("คำนวณหาตัวเลขที่ไม่เคยออกเลย หรืออั้นไว้นานที่สุด ซึ่งมีโอกาสดีดกลับมาออกตามค่าเฉลี่ยสถิติ")
            
            if not df_clean.empty:
                all_nums = [f"{i:02d}" for i in range(100)]
                last_seen_index = {}
                for idx, row in df_clean.iterrows():
                    last_seen_index[row['เลขท้าย 2 ตัว']] = idx
                
                cold_scores = [(n, last_seen_index.get(n, -1)) for n in all_nums]
                cold_scores.sort(key=lambda x: x[1])
                cold_list = [item[0] for item in cold_scores[:5]]
                st.markdown(f"<h2 style='color:#0369A1;'>{', '.join(cold_list)}</h2>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c3:
            st.markdown("<div style='background-color:#DCFCE7; padding:20px; border-radius:10px; border-left:6px solid #16A34A; min-height:220px;'>", unsafe_allow_html=True)
            st.subheader("🎲 สูตรพิกัดหลักผสม (Probability Matrix)")
            st.write("จับคู่สถิติโดยนำค่าฐานนิยม (Mode) ของหลักสิบที่ออกบ่อยที่สุด มาแมตช์เข้าคู่กับหลักหน่วยที่ออกบ่อยที่สุด")
            
            if not df_clean.empty and tens and units:
                top_tens = [str(item[0]) for item in Counter(tens).most_common(2)]
                top_units = [str(item[0]) for item in Counter(units).most_common(2)]
                matrix_list = [f"{t}{u}" for t in top_tens for u in top_units]
                st.markdown(f"<h2 style='color:#15803D;'>{', '.join(matrix_list)}</h2>", unsafe_allow_html=True)
            else:
                st.write("กำลังประมวลผลโมเดลความน่าจะเป็น...")
            st.markdown("</div>", unsafe_allow_html=True)

    with tab4:
        st.header("📋 คลังข้อมูลดิบทั้งหมดย้อนหลัง 30 ปี")
        st.write("คุณสามารถใช้แถบค้นหา กรองงวดที่ต้องการ หรือกดปุ่มดาวน์โหลดข้อมูลทั้งหมดออกไปเป็นไฟล์ CSV ได้ผ่านตารางด้านล่างนี้")
        st.dataframe(df.sort_values(by="timestamp", ascending=False), use_container_width=True)
