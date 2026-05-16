import streamlit as st
import pymongo
import certifi
import pandas as pd
import numpy as np
import os
from collections import Counter

# ตั้งค่าหน้าจอโปรแกรมเป็นแบบกว้าง (Wide Layout) เหมาะแก่การดูสถิติ
st.set_page_config(page_title="ระบบคำนวณและวิเคราะห์สถิติหวย 30 ปี", page_icon="📊", layout="wide")

# เชื่อมต่อฐานข้อมูล MongoDB
MONGO_URI = st.secrets.get("MONGO_URI") or os.environ.get("MONGO_URI")

if not MONGO_URI:
    st.error("❌ ไม่พบ MONGO_URI กรุณาตั้งค่า Secrets ใน Streamlit Cloud")
    st.stop()

# สำหรับเชื่อมต่อโครงข่ายฐานข้อมูล ให้เก็บเป็น Resource ติดเครื่องไว้
@st.cache_resource
def get_database_client():
    return pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())

# 🛠️ จุดที่แก้ไข: เปลี่ยนมาใช้ @st.cache_data และตั้งค่า ttl=3600 (1 ชั่วโมง) เพื่อให้อัปเดตข้อมูลอัตโนมัติ
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
            
        # ใช้ Pandas จัดการข้อมูลให้อยู่ในรูปแบบตาราง (DataFrame) เพื่อให้คำนวณง่าย
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

# [โค้ดส่วนแสดงผลและดีไซน์ด้านล่างปล่อยไว้เหมือนเดิมได้เลยครับ...]
