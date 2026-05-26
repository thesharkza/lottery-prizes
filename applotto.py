import os
import sys
import time
import requests
import pymongo
import certifi
from datetime import datetime, timezone

# ====================================================================
#  ตัวดึงผลสลากกินแบ่งรัฐบาลงวดล่าสุด (Live Fetcher) V3
#
#  เปลี่ยนมาใช้ API ทางการของสำนักงานสลากกินแบ่งรัฐบาล (GLO)
#  เนื่องจาก rayriffy API หยุดให้บริการตั้งแต่ปลายปี 2567
#
#  Endpoint: POST https://www.glo.or.th/api/lottery/getLatestLottery
#
#  Response structure:
#  {
#    "response": {
#      "result": {
#        "date": "1",        # วันที่
#        "month": "5",       # เดือน (1-12)
#        "year": "2569",     # ปี พ.ศ.
#        "data": {
#           "first":  {"price": "...", "number": ["123456"]},
#           "near1":  {"price": "...", "number": ["123455","123457"]},
#           "second": {...},
#           "third":  {...},
#           "fourth": {...},
#           "fifth":  {...},
#           "last2":  {"price": "...", "number": ["02"]},
#           "last3f": {"price": "...", "number": ["701","884"]},  # หน้า 3 ตัว
#           "last3b": {"price": "...", "number": ["123","456"]}   # ท้าย 3 ตัว
#        }
#      }
#    }
#  }
# ====================================================================

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    print("❌ Error: ไม่พบ MONGO_URI กรุณาตรวจสอบการตั้งค่า Secrets ใน GitHub")
    sys.exit(1)

API_URL = "https://www.glo.or.th/api/lottery/getLatestLottery"
MAX_RETRIES = 3
RETRY_DELAY = 5

# เดือนภาษาไทย (index 1-12)
THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]


def normalize_prize_value(raw_value):
    """ทำให้ค่ารางวัลเป็น list of string เสมอ"""
    if raw_value is None:
        return ["-"]
    if isinstance(raw_value, list):
        cleaned = [str(v).strip() for v in raw_value if v and str(v).strip()]
        return cleaned if cleaned else ["-"]
    val_str = str(raw_value).strip()
    return [val_str] if val_str else ["-"]





def fetch_with_retry(url, max_retries=MAX_RETRIES):
    """พยายาม POST URL พร้อม retry"""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # บาง endpoint ของ GLO กรอง request ที่ไม่มี User-Agent
        "User-Agent": "Mozilla/5.0 (compatible; lottery-prizes/1.0; +github-actions)"
    }
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  → ครั้งที่ {attempt}/{max_retries}: POST {url}")
            response = requests.post(
                url,
                headers=headers,
                json={},  # GLO API รับ POST body ว่างได้
                timeout=30
            )
            print(f"     HTTP status: {response.status_code}")
            response.raise_for_status()

            try:
                return response.json()
            except ValueError:
                # response ไม่ใช่ JSON - แสดง raw text สำหรับ debug
                print(f"     ⚠️ response ไม่ใช่ JSON: {response.text[:500]}")
                raise

        except requests.RequestException as e:
            print(f"  ⚠️ พยายามครั้งที่ {attempt} ล้มเหลว: {e}")
            if attempt < max_retries:
                print(f"  ⏳ รอ {RETRY_DELAY} วินาที...")
                time.sleep(RETRY_DELAY)
            else:
                raise
    return None


def extract_number_from_prize_field(data_section, key):
    """
    ดึงค่า number จาก data[key]
    GLO API คืนค่าเป็น dict {"price": "...", "number": [...]}
    """
    if not data_section or key not in data_section:
        return None
    item = data_section[key]
    if isinstance(item, dict):
        return item.get("number")
    if isinstance(item, list):
        return item
    return None


def build_thai_date_str(date_str, month_str, year_str):
    """สร้างข้อความวันที่ภาษาไทย เช่น '16 พฤษภาคม 2569'"""
    try:
        day = int(date_str)
        month_num = int(month_str)
        year_th = int(year_str)
        if 1 <= month_num <= 12:
            return f"{day} {THAI_MONTHS[month_num]} {year_th}"
    except (ValueError, TypeError):
        pass
    return None


def build_datetime(date_str, month_str, year_str):
    """สร้าง datetime จากวันที่ที่ได้จาก GLO API (ปี พ.ศ.)"""
    try:
        day = int(date_str)
        month_num = int(month_str)
        year_th = int(year_str)
        year_ce = year_th - 543
        return datetime(year_ce, month_num, day, tzinfo=timezone.utc)
    except (ValueError, TypeError) as e:
        print(f"⚠️ สร้าง datetime ไม่สำเร็จ: {e}")
        return None


def fetch_and_save_latest_lotto():
    print("=" * 60)
    print("🎰 ดึงข้อมูลสลากกินแบ่งรัฐบาลงวดล่าสุดจาก GLO API")
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

        # GLO API คืนข้อมูลใน data.response.result
        response_obj = data.get("response", {})
        result = response_obj.get("result", {})

        if not result:
            print(f"❌ ไม่พบฟิลด์ response.result ใน API response")
            print(f"   Raw keys: {list(data.keys())}")
            print(f"   Response: {str(data)[:500]}")
            sys.exit(1)

        date_str = result.get("date")
        month_str = result.get("month")
        year_str = result.get("year")
        prize_data = result.get("data", {})

        # สร้างข้อความวันที่
        draw_date_str = build_thai_date_str(date_str, month_str, year_str)
        if not draw_date_str:
            print(f"❌ ไม่สามารถสร้างวันที่จาก date={date_str}, month={month_str}, year={year_str}")
            sys.exit(1)

        # สร้าง datetime
        draw_timestamp = build_datetime(date_str, month_str, year_str)
        if not draw_timestamp:
            draw_timestamp = datetime.now(timezone.utc)

        print(f"📅 งวดที่ดึงได้: {draw_date_str}")

        # Debug: แสดง keys ที่ได้จาก API
        print(f"   📌 prize data keys ที่ได้: {list(prize_data.keys())}")

        # ดึงข้อมูลรางวัล
        first_prize_raw = extract_number_from_prize_field(prize_data, "first")
        three_front_raw = extract_number_from_prize_field(prize_data, "last3f")
        three_last_raw = extract_number_from_prize_field(prize_data, "last3b")
        two_bottom_raw = extract_number_from_prize_field(prize_data, "last2")

        first_prize = normalize_prize_value(first_prize_raw)
        three_front = normalize_prize_value(three_front_raw)
        three_last = normalize_prize_value(three_last_raw)
        two_bottom = normalize_prize_value(two_bottom_raw)

        # ตรวจสอบความถูกต้อง
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
            print(f"   รางวัลที่ 1: {first_prize}")
            print(f"   เลขท้าย 2 ตัว: {two_bottom}")
            print(f"   เลขหน้า 3 ตัว: {three_front}")
            print(f"   เลขท้าย 3 ตัว: {three_last}")
            sys.exit(1)

        print(f"   ✓ รางวัลที่ 1: {first_prize}")
        print(f"   ✓ เลขท้าย 2 ตัว: {two_bottom}")
        print(f"   ✓ เลขหน้า 3 ตัว: {three_front}")
        print(f"   ✓ เลขท้าย 3 ตัว: {three_last}")

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

        result_db = collection.update_one(
            {"draw_date_str": draw_date_str},
            {"$set": document},
            upsert=True
        )

        if result_db.upserted_id:
            print(f"✅ เพิ่มงวดใหม่: {draw_date_str}")
        elif result_db.modified_count > 0:
            print(f"♻️ อัปเดตงวด: {draw_date_str}")
        else:
            print(f"ℹ️ งวด {draw_date_str} มีอยู่แล้ว และข้อมูลตรงกัน")

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
