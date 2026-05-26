import os
import sys
import time
import requests
import pymongo
import certifi
from datetime import datetime, timezone

# ====================================================================
#  ตัวดึงผลสลากกินแบ่งรัฐบาลงวดล่าสุด (Live Fetcher)
#  อ่านจาก rayriffy API แล้วบันทึกลง MongoDB
#
#  ⚠️ สำคัญ: rayriffy API ใช้ ID ดังนี้ (ไม่ใช่ prize1, front3, last3, last2):
#    - prizes:
#         "prizeFirst"  = รางวัลที่ 1
#    - runningNumbers:
#         "runningNumberFrontThree" = เลขหน้า 3 ตัว
#         "runningNumberBackThree"  = เลขท้าย 3 ตัว
#         "runningNumberBackTwo"    = เลขท้าย 2 ตัว
#  อ้างอิง: https://github.com/rayriffy/thai-lotto-api
# ====================================================================

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    print("❌ Error: ไม่พบ MONGO_URI กรุณาตรวจสอบการตั้งค่า Secrets ใน GitHub")
    sys.exit(1)

API_URL = "https://lotto.api.rayriffy.com/latest"
MAX_RETRIES = 3
RETRY_DELAY = 5  # วินาที

# Mapping สำหรับการแกะข้อมูลจาก response
#   เก็บไว้เป็น list เพื่อรองรับ schema เก่า/ใหม่ของ API
PRIZE_FIRST_IDS = ["prizeFirst", "prize1"]
RUNNING_FRONT3_IDS = ["runningNumberFrontThree", "front3"]
RUNNING_BACK3_IDS = ["runningNumberBackThree", "last3"]
RUNNING_BACK2_IDS = ["runningNumberBackTwo", "last2"]

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

THAI_MONTH_TO_NUM = {name: idx for idx, name in enumerate(THAI_MONTHS) if name}


def parse_thai_date(thai_date_str):
    """แปลง '16 พฤษภาคม 2569' → datetime object"""
    try:
        parts = str(thai_date_str).strip().split()
        if len(parts) < 3:
            return None
        day = int(parts[0])
        month_num = THAI_MONTH_TO_NUM.get(parts[1])
        if not month_num:
            return None
        year_ce = int(parts[2]) - 543
        return datetime(year_ce, month_num, day, tzinfo=timezone.utc)
    except Exception as e:
        print(f"⚠️ ไม่สามารถแปลงวันที่ '{thai_date_str}': {e}")
        return None


def normalize_prize_value(raw_value):
    """ทำให้ค่ารางวัลเป็น list เสมอ"""
    if raw_value is None:
        return ["-"]
    if isinstance(raw_value, list):
        cleaned = [str(v).strip() for v in raw_value if v and str(v).strip()]
        return cleaned if cleaned else ["-"]
    val_str = str(raw_value).strip()
    return [val_str] if val_str else ["-"]


def find_by_id_list(items_list, id_candidates):
    """ค้นหา item ใน list ที่ id ตรงกับตัวใดตัวหนึ่งใน id_candidates"""
    if not items_list:
        return None
    for candidate_id in id_candidates:
        for item in items_list:
            if item.get("id") == candidate_id:
                return item.get("number")
    return None


def fetch_with_retry(url, max_retries=MAX_RETRIES):
    """พยายาม fetch URL พร้อม retry"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  → ครั้งที่ {attempt}/{max_retries}: กำลังเรียก {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"  ⚠️ พยายามครั้งที่ {attempt} ล้มเหลว: {e}")
            if attempt < max_retries:
                print(f"  ⏳ รอ {RETRY_DELAY} วินาทีแล้วลองใหม่...")
                time.sleep(RETRY_DELAY)
            else:
                raise
    return None


def fetch_and_save_latest_lotto():
    print("=" * 60)
    print("🎰 เริ่มดึงข้อมูลสลากกินแบ่งรัฐบาลงวดล่าสุด")
    print(f"⏰ เวลาที่รัน (UTC): {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["lottery_db"]
    collection = db["draws"]

    try:
        data = fetch_with_retry(API_URL)

        if not data:
            print("❌ API ไม่ตอบกลับข้อมูลใดๆ")
            sys.exit(1)

        if data.get("status") != "success":
            print(f"❌ API ตอบกลับสถานะ: {data.get('status')}")
            print(f"   Response: {data.get('response', 'N/A')}")
            sys.exit(1)

        response_data = data.get("response", {})
        draw_date_str = response_data.get("date", "").strip()

        if not draw_date_str:
            print("❌ ไม่พบฟิลด์ date ใน response")
            print(f"   Raw response keys: {list(response_data.keys())}")
            sys.exit(1)

        print(f"📅 งวดที่ดึงได้: {draw_date_str}")

        # แปลงวันที่ภาษาไทยเป็น datetime
        draw_timestamp = parse_thai_date(draw_date_str)
        if not draw_timestamp:
            print(f"⚠️ ไม่สามารถแปลง '{draw_date_str}' เป็น datetime ได้")
            draw_timestamp = datetime.now(timezone.utc)

        prizes = response_data.get("prizes", [])
        running_numbers = response_data.get("runningNumbers", [])

        # Debug: แสดง ID ทั้งหมดที่ API ส่งมา (ช่วย debug เวลา schema เปลี่ยน)
        prize_ids = [p.get("id") for p in prizes]
        running_ids = [r.get("id") for r in running_numbers]
        print(f"   📌 prizes IDs ที่ได้: {prize_ids}")
        print(f"   📌 runningNumbers IDs ที่ได้: {running_ids}")

        # ค้นหาด้วย ID ที่ถูกต้อง (พร้อม fallback)
        first_prize_raw = find_by_id_list(prizes, PRIZE_FIRST_IDS)
        three_front_raw = find_by_id_list(running_numbers, RUNNING_FRONT3_IDS)
        three_last_raw = find_by_id_list(running_numbers, RUNNING_BACK3_IDS)
        two_bottom_raw = find_by_id_list(running_numbers, RUNNING_BACK2_IDS)

        # บังคับให้เป็น list เสมอ
        first_prize = normalize_prize_value(first_prize_raw)
        three_front = normalize_prize_value(three_front_raw)
        three_last = normalize_prize_value(three_last_raw)
        two_bottom = normalize_prize_value(two_bottom_raw)

        # ตรวจสอบว่า parse ข้อมูลออกมาได้บ้าง
        if (first_prize == ["-"] and two_bottom == ["-"] and
                three_front == ["-"] and three_last == ["-"]):
            print("❌ ไม่สามารถแกะข้อมูลรางวัลใดๆ ได้")
            print(f"   ID ที่ค้นหา - prizeFirst: {PRIZE_FIRST_IDS}")
            print(f"   ID ที่ค้นหา - runningNumberBackTwo: {RUNNING_BACK2_IDS}")
            print(f"   แต่ใน API มีจริง: prizes={prize_ids}, running={running_ids}")
            print("   ⚠️ API schema อาจเปลี่ยน กรุณาอัปเดต ID ในโค้ด")
            sys.exit(1)

        # ตรวจสอบความถูกต้องของข้อมูล
        first_prize_valid = (
            first_prize != ["-"] and
            all(len(s) == 6 and s.isdigit() for s in first_prize)
        )
        two_digit_valid = (
            two_bottom != ["-"] and
            all(len(s) == 2 and s.isdigit() for s in two_bottom)
        )

        if not first_prize_valid and not two_digit_valid:
            print("❌ ข้อมูลรางวัลไม่สมเหตุสมผล")
            print(f"   รางวัลที่ 1 ที่ได้: {first_prize}")
            print(f"   เลขท้าย 2 ตัวที่ได้: {two_bottom}")
            sys.exit(1)

        print(f"   ✓ รางวัลที่ 1: {first_prize}")
        print(f"   ✓ เลขท้าย 2 ตัว: {two_bottom}")
        print(f"   ✓ เลขหน้า 3 ตัว: {three_front}")
        print(f"   ✓ เลขท้าย 3 ตัว: {three_last}")
        print(f"   ✓ Timestamp: {draw_timestamp.isoformat()}")

        document = {
            "draw_date_str": draw_date_str,
            "timestamp": draw_timestamp,
            "last_synced_at": datetime.now(timezone.utc),
            "prizes": {
                "FIRST": first_prize,
                "TWO_DIGIT": two_bottom,
                "THREE_FRONT": three_front,
                "THREE_LAST": three_last
            }
        }

        result = collection.update_one(
            {"draw_date_str": draw_date_str},
            {"$set": document},
            upsert=True
        )

        if result.upserted_id:
            print(f"✅ สะสมข้อมูลสำเร็จ! เพิ่มงวดใหม่: {draw_date_str}")
        elif result.modified_count > 0:
            print(f"♻️ อัปเดตข้อมูลสำเร็จ! งวด: {draw_date_str}")
        else:
            print(f"ℹ️ งวด {draw_date_str} มีอยู่แล้วและข้อมูลตรงกัน")

        total_count = collection.count_documents({})
        print(f"📊 คลังข้อมูลปัจจุบัน: {total_count} งวด")

    except requests.RequestException as e:
        print(f"❌ ดึงข้อมูลจาก API ไม่สำเร็จ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    fetch_and_save_latest_lotto()
