import os
import sys
import pymongo
import certifi
from datetime import datetime, timezone

# ====================================================================
#  Manual Add Script - เพิ่มงวดที่ขาดด้วยมือเข้า MongoDB
#
#  วิธีใช้:
#    1. เปิดไฟล์นี้ในเครื่อง / GitHub UI / Codespaces
#    2. แก้รายการ DRAWS_TO_ADD ด้านล่าง โดยใส่ข้อมูลงวดที่ขาด
#    3. รัน: python manual_add.py
#       หรือ Run workflow "Manual Add Missing Draws" ใน Actions
#
#  รูปแบบข้อมูล:
#    {
#        "date": "2569-05-16",    # YYYY-MM-DD (ปี พ.ศ.)
#        "first": "123456",        # รางวัลที่ 1 (6 หลัก)
#        "last2": "78",            # เลขท้าย 2 ตัว
#        "last3f": ["701", "884"], # เลขหน้า 3 ตัว (มี 2 ตัว)
#        "last3b": ["123", "456"]  # เลขท้าย 3 ตัว (มี 2 ตัว)
#    }
#
#  📍 หาผลรางวัลย้อนหลังได้จาก:
#    - https://news.sanook.com/lotto/   (เลือกงวดย้อนหลัง)
#    - https://www.glo.or.th            (เว็บทางการ → ตรวจผลรางวัล)
# ====================================================================

# ====================================================================
#  ⚠️ แก้ตรงนี้: ใส่ข้อมูลงวดที่ขาดทั้งหมด แล้วรันสคริปต์
# ====================================================================
DRAWS_TO_ADD = [
    # งวด 16 มกราคม 2568 - ตัวอย่าง (แก้เป็นเลขจริง)
    # {
    #     "date": "2568-01-16",
    #     "first": "123456",
    #     "last2": "78",
    #     "last3f": ["701", "884"],
    #     "last3b": ["123", "456"]
    # },
    # {
    #     "date": "2568-02-01",
    #     "first": "654321",
    #     "last2": "00",
    #     "last3f": ["111", "222"],
    #     "last3b": ["333", "444"]
    # },
    # ... เพิ่มงวดอื่น ๆ ตามนี้
]
# ====================================================================

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]


def parse_buddhist_date(date_str):
    """แปลง '2569-05-16' (ปี พ.ศ.) → datetime UTC + ข้อความวันที่ภาษาไทย"""
    parts = date_str.split("-")
    if len(parts) != 3:
        raise ValueError(f"รูปแบบวันที่ '{date_str}' ผิด ต้องเป็น YYYY-MM-DD")
    year_th = int(parts[0])
    month_num = int(parts[1])
    day = int(parts[2])

    if not (1 <= month_num <= 12):
        raise ValueError(f"เดือน {month_num} ไม่ถูกต้อง")
    if not (1 <= day <= 31):
        raise ValueError(f"วัน {day} ไม่ถูกต้อง")

    year_ce = year_th - 543
    dt = datetime(year_ce, month_num, day, tzinfo=timezone.utc)
    thai_str = f"{day} {THAI_MONTHS[month_num]} {year_th}"
    return dt, thai_str


def validate_draw(draw):
    """ตรวจสอบความถูกต้องของข้อมูลงวด"""
    errors = []

    first = str(draw.get("first", "")).strip()
    if not (len(first) == 6 and first.isdigit()):
        errors.append(f"first '{first}' ต้องเป็นเลข 6 หลัก")

    last2 = str(draw.get("last2", "")).strip()
    if not (len(last2) == 2 and last2.isdigit()):
        errors.append(f"last2 '{last2}' ต้องเป็นเลข 2 หลัก")

    for key in ["last3f", "last3b"]:
        val = draw.get(key, [])
        if not isinstance(val, list):
            errors.append(f"{key} ต้องเป็น list")
            continue
        for v in val:
            v_str = str(v).strip()
            if not (len(v_str) == 3 and v_str.isdigit()):
                errors.append(f"{key} '{v_str}' ต้องเป็นเลข 3 หลัก")

    return errors


def main():
    MONGO_URI = os.environ.get("MONGO_URI")
    if not MONGO_URI:
        print("❌ Error: ไม่พบ MONGO_URI")
        sys.exit(1)

    if not DRAWS_TO_ADD:
        print("⚠️ ไม่มีข้อมูลใน DRAWS_TO_ADD")
        print("   กรุณาแก้ไฟล์ manual_add.py และใส่ข้อมูลงวดที่ต้องการเพิ่ม")
        sys.exit(0)

    print("=" * 60)
    print(f"📝 Manual Add - เพิ่ม {len(DRAWS_TO_ADD)} งวดเข้าฐานข้อมูล")
    print(f"⏰ เวลาที่รัน: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["lottery_db"]
    collection = db["draws"]

    success_count = 0
    error_count = 0
    skip_count = 0

    try:
        for idx, draw in enumerate(DRAWS_TO_ADD, 1):
            print(f"\n[{idx}/{len(DRAWS_TO_ADD)}] {draw.get('date', '?')}")

            # ตรวจสอบความถูกต้อง
            errors = validate_draw(draw)
            if errors:
                print(f"   ❌ ข้อมูลไม่ถูกต้อง:")
                for e in errors:
                    print(f"      - {e}")
                error_count += 1
                continue

            try:
                dt, thai_str = parse_buddhist_date(draw["date"])
            except Exception as e:
                print(f"   ❌ {e}")
                error_count += 1
                continue

            # เตรียม document
            first_str = str(draw["first"]).strip()
            last2_str = str(draw["last2"]).strip()
            last3f = [str(v).strip() for v in draw["last3f"]]
            last3b = [str(v).strip() for v in draw["last3b"]]

            document = {
                "draw_date_str": thai_str,
                "timestamp": dt,
                "last_synced_at": datetime.now(timezone.utc),
                "prizes": {
                    "FIRST": [first_str],
                    "TWO_DIGIT": [last2_str],
                    "THREE_FRONT": last3f,
                    "THREE_LAST": last3b
                }
            }

            result = collection.update_one(
                {"draw_date_str": thai_str},
                {"$set": document},
                upsert=True
            )

            if result.upserted_id:
                print(f"   ✅ เพิ่มงวดใหม่: {thai_str}")
                print(f"      รางวัลที่ 1: {first_str} | ท้าย 2: {last2_str}")
                print(f"      หน้า 3: {last3f} | ท้าย 3: {last3b}")
                success_count += 1
            elif result.modified_count > 0:
                print(f"   ♻️ อัปเดตงวด: {thai_str}")
                success_count += 1
            else:
                print(f"   ℹ️ งวด {thai_str} มีอยู่แล้วและข้อมูลตรงกัน")
                skip_count += 1

        print("\n" + "=" * 60)
        print(f"🎉 สรุป: สำเร็จ {success_count} | ข้าม {skip_count} | ผิดพลาด {error_count}")
        total = collection.count_documents({})
        print(f"📊 คลังข้อมูลปัจจุบัน: {total} งวด")
        print("=" * 60)

        if error_count > 0:
            sys.exit(1)

    finally:
        client.close()


if __name__ == "__main__":
    main()
