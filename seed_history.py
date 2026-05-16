import os
import pymongo
import certifi
import pandas as pd
import ast
from datetime import datetime

# ดึง URL จาก Environment Variable (GitHub Secrets) เพื่อความปลอดภัย
MONGO_URI = os.environ.get("MONGO_URI")

if not MONGO_URI:
    print("Error: ไม่พบ MONGO_URI กรุณาตรวจสอบการตั้งค่า Secrets ใน GitHub")
    exit(1)

# ตั้งค่าการเชื่อมต่อ MongoDB
client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["lottery_db"]
collection = db["draws"]

print("กำลังเริ่มอ่านไฟล์สถิติย้อนหลัง lotto.csv ผ่าน Pandas...")

# รายชื่อเดือนภาษาไทยสำหรับใช้แปลงรูปแบบวันที่
thai_months = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

try:
    # ใช้ dtype=str เพื่อป้องกันไม่ให้เลขท้ายที่ขึ้นต้นด้วย 0 โดนตัดออก (เช่น 00, 05)
    df_history = pd.read_csv("lotto.csv", dtype=str)
    
    success_count = 0
    
    for index, row in df_history.iterrows():
        raw_date = str(row['date']) # ดึงค่าวันที่รูปแบบ YYYY-MM-DD
        
        try:
            date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
            # แปลงปี ค.ศ. เป็น พ.ศ. และเปลี่ยนเลขเดือนเป็นข้อความเดือนภาษาไทย
            day = date_obj.day
            month_str = thai_months[date_obj.month]
            year_th = date_obj.year + 543
            draw_date_str = f"{day} {month_str} {year_th}"
        except Exception as e:
            print(f"ข้ามแถวที่ {index} เนื่องจากรูปแบบวันที่ผิดพลาด: {e}")
            continue

        # ฟังก์ชันช่วยแกะข้อความลิสต์ เช่น "['290', '742']" ให้กลายเป็น Python List ที่ถูกต้อง
        def parse_list_string(val):
            if pd.isna(val) or not val or val == "[]":
                return ["-"]
            try:
                parsed = ast.literal_eval(val)
                if isinstance(parsed, list):
                    return parsed if len(parsed) > 0 else ["-"]
                return [str(parsed)]
            except:
                return [str(val)]

        prize_1st = str(row['prize_1st']) if pd.notna(row['prize_1st']) else "-"
        prize_2digits = str(row['prize_2digits']) if pd.notna(row['prize_2digits']) else "-"
        
        # แกะข้อมูลเลขหน้าและเลขท้าย 3 ตัวจากคอลัมน์ของไฟล์คุณ
        three_front = parse_list_string(row['prize_pre_3digit'])
        three_last = parse_list_string(row['prize_sub_3digits'])

        # จัดโครงสร้างข้อมูลให้เหมือนกับที่แอปพลิเคชัน Streamlit และบอทหลักต้องการ
        document = {
            "draw_date_str": draw_date_str,
            "timestamp": date_obj,
            "prizes": {
                "FIRST": [prize_1st] if prize_1st != "-" else ["-"],
                "TWO_DIGIT": [prize_2digits] if prize_2digits != "-" else ["-"],
                "THREE_FRONT": three_front,
                "THREE_LAST": three_last
            }
        }

        # บันทึกลง MongoDB แบบ Upsert (ถ้างวดไหนมีแล้วจะอัปเดตทับ ถ้ายกงวดใหม่จะเพิ่มเข้าคลัง)
        collection.update_one(
            {"draw_date_str": draw_date_str},
            {"$set": document},
            upsert=True
        )
        success_count += 1

    print(f"🎉 นำเข้าข้อมูลประวัติศาสตร์จากไฟล์ lotto.csv สำเร็จทั้งหมด {success_count} งวด!")

except Exception as e:
    print(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
