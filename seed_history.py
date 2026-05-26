import os
import sys
import pymongo
import certifi
import pandas as pd
import ast
from datetime import datetime, timezone

# ====================================================================
#  Script นำเข้าข้อมูลประวัติสลากกินแบ่งรัฐบาลย้อนหลังจาก lotto.csv
#  เข้า MongoDB collection "draws" แบบ upsert
# ====================================================================

# ดึง URL จาก Environment Variable (GitHub Secrets) เพื่อความปลอดภัย
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    print("❌ Error: ไม่พบ MONGO_URI กรุณาตรวจสอบการตั้งค่า Secrets ใน GitHub")
    sys.exit(1)

# ตั้งค่าการเชื่อมต่อ MongoDB
client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["lottery_db"]
collection = db["draws"]

print("=" * 60)
print("📚 เริ่มอ่านไฟล์สถิติย้อนหลัง lotto.csv ผ่าน Pandas...")
print("=" * 60)

# รายชื่อเดือนภาษาไทยสำหรับใช้แปลงรูปแบบวันที่
THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]


def parse_list_string(val):
    """
    แกะข้อความรูปแบบ list string เช่น "['290', '742']" เป็น Python list
    """
    if pd.isna(val) or not val or str(val).strip() == "[]":
        return ["-"]
    try:
        parsed = ast.literal_eval(str(val))
        if isinstance(parsed, list):
            cleaned = [str(v).strip() for v in parsed if v and str(v).strip()]
            return cleaned if cleaned else ["-"]
        return [str(parsed).strip()]
    except (ValueError, SyntaxError):
        # ถ้าแกะไม่ได้ ส่งคืนเป็น string ดิบ
        return [str(val).strip()]


try:
    # ใช้ dtype=str เพื่อป้องกันไม่ให้เลขท้ายที่ขึ้นต้นด้วย 0 โดนตัดออก (เช่น 00, 05)
    df_history = pd.read_csv("lotto.csv", dtype=str)

    success_count = 0
    skip_count = 0
    error_count = 0

    for index, row in df_history.iterrows():
        raw_date = str(row['date'])

        try:
            date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
            # เพิ่ม timezone (UTC) เพื่อให้สอดคล้องกับ applotto.py
            date_obj = date_obj.replace(tzinfo=timezone.utc)

            day = date_obj.day
            month_str = THAI_MONTHS[date_obj.month]
            year_th = date_obj.year + 543
            draw_date_str = f"{day} {month_str} {year_th}"
        except Exception as e:
            print(f"⚠️ ข้ามแถวที่ {index} เนื่องจากรูปแบบวันที่ผิดพลาด: {e}")
            skip_count += 1
            continue

        try:
            prize_1st = str(row['prize_1st']).strip() if pd.notna(row['prize_1st']) else "-"
            prize_2digits = str(row['prize_2digits']).strip() if pd.notna(row['prize_2digits']) else "-"

            # แกะข้อมูลเลขหน้าและเลขท้าย 3 ตัวจากคอลัมน์ของไฟล์ csv
            three_front = parse_list_string(row['prize_pre_3digit'])
            three_last = parse_list_string(row['prize_sub_3digits'])

            # จัดโครงสร้างข้อมูลให้เหมือนกับที่ applotto.py และ app.py ต้องการ
            document = {
                "draw_date_str": draw_date_str,
                "timestamp": date_obj,  # ใช้วันที่งวดเป็น timestamp
                "prizes": {
                    "FIRST": [prize_1st] if prize_1st != "-" else ["-"],
                    "TWO_DIGIT": [prize_2digits] if prize_2digits != "-" else ["-"],
                    "THREE_FRONT": three_front,
                    "THREE_LAST": three_last
                }
            }

            # บันทึกลง MongoDB แบบ Upsert
            collection.update_one(
                {"draw_date_str": draw_date_str},
                {"$set": document},
                upsert=True
            )
            success_count += 1
        except Exception as e:
            print(f"❌ ผิดพลาดในแถวที่ {index} ({draw_date_str}): {e}")
            error_count += 1
            continue

    print("=" * 60)
    print(f"🎉 นำเข้าข้อมูลสำเร็จ: {success_count} งวด")
    if skip_count:
        print(f"⏭️ ข้ามไป: {skip_count} แถว")
    if error_count:
        print(f"❌ ผิดพลาด: {error_count} แถว")

    # สรุปสถิติคลังหลัง seed
    total_count = collection.count_documents({})
    print(f"📊 ขณะนี้คลังข้อมูลมีทั้งหมด {total_count} งวด")
    print("=" * 60)

except FileNotFoundError:
    print("❌ ไม่พบไฟล์ lotto.csv ในไดเร็กทอรีปัจจุบัน")
    sys.exit(1)
except Exception as e:
    print(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    client.close()
