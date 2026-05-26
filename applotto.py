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
# ====================================================================

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    print("❌ Error: ไม่พบ MONGO_URI กรุณาตรวจสอบการตั้งค่า Secrets ใน GitHub")
    sys.exit(1)

API_URL = "https://lotto.api.rayriffy.com/latest"
MAX_RETRIES = 3
RETRY_DELAY = 5  # วินาที

# รายชื่อเดือนภาษาไทยสำหรับใช้แปลงข้อความวันที่
THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

THAI_MONTH_TO_NUM = {name: idx for idx, name in enumerate(THAI_MONTHS) if name}


def parse_thai_date(thai_date_str):
    """
    แปลงข้อความวันที่ภาษาไทย เช่น '16 พฤษภาคม 2569' → datetime object
    เพื่อใช้เก็บเป็น timestamp ของงวด ทำให้เรียงลำดับใน MongoDB ถูกต้อง
    """
    try:
        parts = str(thai_date_str).strip().split()
        if len(parts) < 3:
            return None
        day = int(parts[0])
        month_name = parts[1]
        year_th = int(parts[2])
        month_num = THAI_MONTH_TO_NUM.get(month_name)
        if not month_num:
            return None
        # แปลงปี พ.ศ. → ค.ศ.
        year_ce = year_th - 543
        return datetime(year_ce, month_num, day, tzinfo=timezone.utc)
    except Exception as e:
        print(f"⚠️ ไม่สามารถแปลงวันที่ '{thai_date_str}': {e}")
        return None


def normalize_prize_value(raw_value):
    """
    ทำให้ค่ารางวัลเป็น list เสมอ เพื่อให้โครงสร้างเหมือนกับ seed_history.py
    รองรับทั้ง list, string, และค่าว่าง
    """
    if raw_value is None:
        return ["-"]
    if isinstance(raw_value, list):
        cleaned = [str(v).strip() for v in raw_value if v and str(v).strip()]
        return cleaned if cleaned else ["-"]
    val_str = str(raw_value).strip()
    return [val_str] if val_str else ["-"]


def fetch_with_retry(url, max_retries=MAX_RETRIES):
    """พยายาม fetch URL พร้อม retry ถ้าล้มเหลว"""
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

        if not data or data.get("status") != "success":
            print(f"❌ API ตอบกลับสถานะไม่สำเร็จ: {data}")
            sys.exit(1)

        response_data = data["response"]
        draw_date_str = response_data.get("date", "").strip()

        if not draw_date_str:
            print("❌ ไม่พบฟิลด์ date ใน response")
            sys.exit(1)

        # แปลงวันที่ภาษาไทยเป็น datetime เพื่อใช้เป็น timestamp ของงวด
        draw_timestamp = parse_thai_date(draw_date_str)
        if not draw_timestamp:
            print(f"⚠️ ไม่สามารถแปลง '{draw_date_str}' เป็น datetime ได้")
            print("   ใช้เวลาปัจจุบันแทน (อาจทำให้การเรียงลำดับผิดพลาด)")
            draw_timestamp = datetime.now(timezone.utc)

        prizes = response_data.get("prizes", [])
        running_numbers = response_data.get("runningNumbers", [])

        first_prize_raw = next(
            (item.get("number") for item in prizes if item.get("id") == "prize1"),
            None
        )
        three_front_raw = next(
            (item.get("number") for item in running_numbers if item.get("id") == "front3"),
            None
        )
        three_last_raw = next(
            (item.get("number") for item in running_numbers if item.get("id") == "last3"),
            None
        )
        two_bottom_raw = next(
            (item.get("number") for item in running_numbers if item.get("id") == "last2"),
            None
        )

        # บังคับให้เป็น list เสมอ
        first_prize = normalize_prize_value(first_prize_raw)
        three_front = normalize_prize_value(three_front_raw)
        three_last = normalize_prize_value(three_last_raw)
        two_bottom = normalize_prize_value(two_bottom_raw)

        # ตรวจสอบความสมเหตุสมผลของข้อมูลก่อนเขียน DB
        if first_prize == ["-"] and two_bottom == ["-"]:
            print("❌ ข้อมูลที่ดึงมาว่างเปล่าทั้งรางวัลที่ 1 และเลขท้าย 2 ตัว")
            print("   อาจเป็นเพราะ API ยังไม่ได้อัปเดตผลรางวัล")
            sys.exit(1)

        print(f"📅 งวดที่ดึงได้: {draw_date_str}")
        print(f"   รางวัลที่ 1: {first_prize}")
        print(f"   เลขท้าย 2 ตัว: {two_bottom}")
        print(f"   เลขหน้า 3 ตัว: {three_front}")
        print(f"   เลขท้าย 3 ตัว: {three_last}")
        print(f"   Timestamp ที่จะบันทึก: {draw_timestamp.isoformat()}")

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
            print(f"✅ สะสมข้อมูลสำเร็จ! เพิ่มงวดใหม่เข้าคลัง: {draw_date_str}")
        elif result.modified_count > 0:
            print(f"♻️ อัปเดตข้อมูลสำเร็จ! แก้ไขข้อมูลงวด: {draw_date_str}")
        else:
            print(f"ℹ️ งวด {draw_date_str} มีอยู่แล้วในคลัง และข้อมูลตรงกัน ไม่ได้แก้ไข")

        # ตรวจสอบจำนวนงวดในคลัง
        total_count = collection.count_documents({})
        print(f"📊 ขณะนี้คลังข้อมูลมีทั้งหมด {total_count} งวด")

    except requests.RequestException as e:
        print(f"❌ ดึงข้อมูลจาก API ไม่สำเร็จหลัง retry: {e}")
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
