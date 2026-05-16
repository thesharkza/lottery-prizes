import streamlit as st
import pymongo

# ฟังก์ชันสำหรับเชื่อมต่อฐานข้อมูล (ใช้ Cache เพื่อให้เชื่อมต่อแค่ครั้งเดียว)
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets)

# เรียกใช้งานการเชื่อมต่อ
client = init_connection()

# สร้างหรือเลือก Database ชื่อ 'lottery_db' และ Collection ชื่อ 'draws'
db = client["lottery_db"]
collection = db["draws"]

st.title("📊 แดชบอร์ดสถิติสลากกินแบ่งรัฐบาล")
st.success("เชื่อมต่อ MongoDB Atlas สำเร็จแล้ว!")

# ตัวอย่างการดึงจำนวนข้อมูล (ตอนนี้อาจจะยังเป็น 0)
count = collection.count_documents({})
st.write(f"ปัจจุบันมีข้อมูลในระบบทั้งหมด: {count} งวด")