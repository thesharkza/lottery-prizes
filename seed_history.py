import os
import pymongo
import certifi
from datetime import datetime

# ดึง URL จาก Environment Variable (GitHub Secrets) เพื่อความปลอดภัย
MONGO_URI = os.environ.get("MONGO_URI")

if not MONGO_URI:
    print("Error: ไม่พบ MONGO_URI กรุณาตรวจสอบการตั้งค่า Secrets")
    exit(1)

client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["lottery_db"]
collection = db["draws"]

print("กำลังเริ่มนำเข้าข้อมูลสถิติย้อนหลัง 30 ปีเข้าสู่ MongoDB...")

# ใส่ชุดข้อมูลประวัติศาสตร์ที่คุณเตรียมไว้ตรงนี้ (ตัวอย่าง)
historical_data = [
    {
        "draw_date_str": "16 พฤษภาคม 2539",
        "timestamp": datetime(1996, 5, 16),
        "prizes": {"FIRST": "123456", "TWO_DIGIT": "56", "THREE_FRONT": "-", "THREE_LAST": "111, 222"}
    },
    {
        "draw_date_str": "1 มิถุนายน 2539",
        "timestamp": datetime(1996, 6, 1),
        "prizes": {"FIRST": "789012", "TWO_DIGIT": "12", "THREE_FRONT": "-", "THREE_LAST": "555, 666"}
    }
    # ... ใส่เพิ่มให้ครบ 30 ปีตามข้อมูลที่คุณมี ...
]

success_count = 0
for item in historical_data:
    result = collection.update_one(
        {"draw_date_str": item["draw_date_str"]},
        {"$set": item},
        upsert=True
    )
    success_count += 1

print(f"🎉 สั่ง GitHub นำเข้าข้อมูลประวัติศาสตร์สำเร็จแล้วทั้งหมด {success_count} งวด!")
