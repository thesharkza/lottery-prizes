import streamlit as st
import pymongo
import pandas as pd

st.set_page_config(page_title="Thai Lotto Analytics", layout="wide")

# ดึงข้อมูลการเชื่อมต่อจาก Streamlit Secrets
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets)

client = init_connection()
db = client["lottery_db"]
collection = db["draws"]

st.title("📊 แดชบอร์ดสถิติสลากกินแบ่งรัฐบาล")

# ค้นหาข้อมูลทั้งหมดจาก MongoDB และจัดเรียงจากงวดล่าสุดไปเก่าสุด
cursor = collection.find().sort("_id", -1)
data = list(cursor)

if len(data) == 0:
    st.warning("ยังไม่มีข้อมูลในระบบ รอให้ระบบอัปเดตข้อมูลสักครู่นะครับ")
else:
    st.success(f"เชื่อมต่อฐานข้อมูลสำเร็จ! พบข้อมูลทั้งหมด {len(data)} งวด")
    
    # แปลงข้อมูล JSON ให้อยู่ในรูปแบบตาราง (Table)
    df_list =
    for d in data:
        prizes = d.get("prizes", {})
        df_list.append({
            "งวดวันที่": d.get("draw_date_str", "-"),
            "รางวัลที่ 1": prizes.get("FIRST", "-"),
            "เลขหน้า 3 ตัว": ", ".join(prizes.get("THREE_FRONT",)) if isinstance(prizes.get("THREE_FRONT"), list) else prizes.get("THREE_FRONT", "-"),
            "เลขท้าย 3 ตัว": ", ".join(prizes.get("THREE_LAST",)) if isinstance(prizes.get("THREE_LAST"), list) else prizes.get("THREE_LAST", "-"),
            "เลขท้าย 2 ตัว": prizes.get("TWO_DIGIT", "-")
        })
    
    df = pd.DataFrame(df_list)
    st.dataframe(df, use_container_width=True)
