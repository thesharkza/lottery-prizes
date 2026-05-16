import os
import pymongo
import certifi
from datetime import datetime

# ใส่ URL Connection String ของคุณตรงนี้ หรือรันผ่าน Environment ตัวแปร
MONGO_URI = "mongodb+srv://thesharkza_db_user:รหัสผ่านจริงของคุณ@lotteryprizes1.qtijjai.mongodb.net/?appName=lotteryprizes1"

client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["lottery_db"]
collection = db["draws"]

print("กำลังเตรียมนำเข้าข้อมูลสถิติย้อนหลัง 30 ปี...")

# โครงสร้างชุดข้อมูลจำลองย้อนหลัง (คุณสามารถดาวน์โหลดประวัติหวย 30 ปีมาแปลงเป็น List แบบนี้แล้วสั่งรันได้เลยครับ)
historical_data = [
    {
        "draw_date_str": "16 พฤษภาคม 2539",
        "timestamp": datetime(1996, 5, 16),
        "prizes": {"FIRST": "123456", "TWO_DIGIT": "56", "THREE_FRONT": "-", "THREE_LAST": "111, 222, 333, 444"}
    },
    {
        "draw_date_str": "1 มิถุนายน 2539",
        "timestamp": datetime(1996, 6, 1),
        "prizes": {"FIRST": "789012", "TWO_DIGIT": "12", "THREE_FRONT": "-", "THREE_LAST": "555, 666, 777, 888"}
    }
    # ... สามารถนำประวัติข้อมูลที่คุณต้องการวิเคราะห์มาใส่เพิ่มเติมให้ครบถ้วนตรงนี้ได้เลยครับ ...
]

# สั่งบันทึกลงฐานข้อมูลแบบไม่ซ้ำงวดเดิม (Upsert)
success_count = 0
for item in historical_data:
    result = collection.update_one(
        {"draw_date_str": item["draw_date_str"]},
        {"$set": item},
        upsert=True
    )
    success_count += 1

print(f"🎉 นำเข้าข้อมูลประวัติศาสตร์เรียบร้อยแล้วทั้งหมด {success_count} งวด!")
