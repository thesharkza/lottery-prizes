import streamlit as st
import pymongo
import certifi
import os

# ตั้งค่าหน้าเว็บสไตล์ Streamlit
st.set_page_config(page_title="ตรวจผลสลากกินแบ่งรัฐบาล", page_icon="🎫", layout="centered")

# ดึงข้อมูลการเชื่อมต่อจาก Secrets ของ Streamlit
MONGO_URI = st.secrets.get("MONGO_URI") or os.environ.get("MONGO_URI")

if not MONGO_URI:
    st.error("❌ ไม่พบ MONGO_URI กรุณาตั้งค่า Secrets ในระบบ Streamlit Cloud")
    st.stop()

@st.cache_resource
def get_database_client():
    return pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())

try:
    client = get_database_client()
    db = client["lottery_db"]
    collection = db["draws"]
    
    # ดึงงวดล่าสุดที่บันทึกไว้ใน MongoDB เรียงตามวันเวลาที่เพิ่มล่าสุด
    latest_draw = collection.find_one(sort=[("timestamp", pymongo.DESCENDING)])
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล: {e}")
    st.stop()

def format_numbers(val):
    if isinstance(val, list):
        return "  ".join(val)
    return str(val)

# ส่วนดีไซน์หน้าจอแสดงผล
st.markdown("<h1 style='text-align: center; color: #DC2626;'>🎫 ตรวจผลสลากกินแบ่งรัฐบาล</h1>", unsafe_allow_html=True)

if latest_draw:
    draw_date = latest_draw.get("draw_date_str", "ไม่ระบุงวด")
    prizes = latest_draw.get("prizes", {})
    
    st.markdown(f"<h3 style='text-align: center; color: #4B5563;'>งวดประจำวันที่: <span style='color: #2563EB;'>{draw_date}</span></h3>", unsafe_allow_html=True)
    st.write("---")
    
    # แสดงผลรางวัลที่ 1
    st.markdown("<p style='text-align: center; font-size: 20px; font-weight: bold; color: #6B7280; margin-bottom: 0;'>รางวัลที่ 1</p>", unsafe_allow_html=True)
    first_prize = format_numbers(prizes.get("FIRST", "-"))
    st.markdown(f"<h1 style='text-align: center; color: #DC2626; font-size: 60px; letter-spacing: 5px; font-weight: 800; margin-top: 0;'>{first_prize}</h1>", unsafe_allow_html=True)
    st.write("---")
    
    # แสดงผลเลขหน้า 3 ตัว และ เลขท้าย 3 ตัว
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<p style='text-align: center; font-size: 18px; font-weight: bold; color: #6B7280; margin-bottom: 0;'>เลขหน้า 3 ตัว</p>", unsafe_allow_html=True)
        three_front = format_numbers(prizes.get("THREE_FRONT", "-"))
        st.markdown(f"<h2 style='text-align: center; color: #2563EB; font-size: 35px; font-weight: bold; margin-top: 0;'>{three_front}</h2>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("<p style='text-align: center; font-size: 18px; font-weight: bold; color: #6B7280; margin-bottom: 0;'>เลขท้าย 3 ตัว</p>", unsafe_allow_html=True)
        three_last = format_numbers(prizes.get("THREE_LAST", "-"))
        st.markdown(f"<h2 style='text-align: center; color: #2563EB; font-size: 35px; font-weight: bold; margin-top: 0;'>{three_last}</h2>", unsafe_allow_html=True)
        
    st.write("---")
    
    # แสดงผลเลขท้าย 2 ตัว
    st.markdown("<p style='text-align: center; font-size: 18px; font-weight: bold; color: #6B7280; margin-bottom: 0;'>เลขท้าย 2 ตัว</p>", unsafe_allow_html=True)
    two_digit = format_numbers(prizes.get("TWO_DIGIT", "-"))
    st.markdown(f"<h1 style='text-align: center; color: #16A34A; font-size: 50px; font-weight: bold; margin-top: 0;'>{two_digit}</h1>", unsafe_allow_html=True)

else:
    st.warning("⚠️ ไม่พบข้อมูลสลากในฐานข้อมูลของคุณ กรุณากดสั่ง Run workflow ใน GitHub Actions เพื่อบันทึกข้อมูลรอบแรกก่อนครับ")

st.write("---")
st.markdown("<p style='text-align: center; font-size: 12px; color: #9CA3AF;'>Lottery Prizes Web App • ข้อมูลเรียลไทม์เชื่อมต่อตรงกับ MongoDB Atlas</p>", unsafe_allow_html=True)
