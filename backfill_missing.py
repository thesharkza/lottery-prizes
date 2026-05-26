import os
import sys
import time
import requests
import pymongo
import certifi
from datetime import datetime, timezone

# ====================================================================
#  Backfill Script - ดึงงวดที่ขาดหายไปจาก API rayriffy เติมในฐานข้อมูล
#
#  สำหรับกรณีที่ applotto.py ไม่ทำงานเป็นเวลานาน หรือพึ่งแก้ ID schema
#  สคริปต์นี้จะ:
#    1. ดึงรายการงวดทั้งหมดจาก /list/[page]
#    2. เช็คใน MongoDB ว่ามีงวดไหนยังไม่มี
#    3. ดึงรายละเอียดงวดเหล่านั้นจาก /lotto/[id] แล้วบันทึก
#
#  วิธีรัน:
#    export MONGO_URI="mongodb+srv://..."
#    python backfill_missing.py
# ====================================================================

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    print("❌ Error: ไม่พบ MONGO_URI")
    sys.exit(1)

API_BASE = "https://lotto.api.rayriffy.com"
LIST_URL = f"{API_BASE}/list"
LOTTO_URL = f"{API_BASE}/lotto"

MAX_PAGES = 30  # จำนวนหน้าสูงสุดที่จะดึง (ป้องกัน infinite loop)
DELAY_BETWEEN_REQUESTS = 1  # วินาที เพื่อไม่ให้ rate limit
MAX_RETRIES = 3

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
    except Exception:
        return None


def normalize_prize_value(raw_value):
    if raw_value is None:
        return ["-"]
    if isinstance(raw_value, list):
        cleaned = [str(v).strip() for v in raw_value if v and str(v).strip()]
        return cleaned if cleaned else ["-"]
    val_str = str(raw_value).strip()
    return [val_str] if val_str else ["-"]


def find_by_id_list(items_list, id_candidates):
    if not items_list:
        return None
    for candidate_id in id_candidates:
        for item in items_list:
            if item.get("id") == candidate_id:
                return item.get("number")
    return None


def fetch_with_retry(url, max_retries=MAX_RETRIES):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"    ⚠️ ครั้งที่ {attempt}: {e}")
            if attempt < max_retries:
                time.sleep(3)
            else:
                return None
    return None


def get_all_draw_ids_from_api():
    """ดึงรายการงวดทั้งหมดจาก API ผ่าน endpoint /list/[page]"""
    print("🔍 กำลังดึงรายการงวดทั้งหมดจาก API...")
    all_draws = []  # list of dict: {id, date, url}

    for page in range(1, MAX_PAGES + 1):
        url = f"{LIST_URL}/{page}"
        print(f"  → page {page}: {url}")
        data = fetch_with_retry(url)

        if not data:
            print(f"    หยุดที่ page {page} (ดึงไม่สำเร็จ)")
            break

        if data.get("status") != "success":
            print(f"    หยุดที่ page {page} (status != success)")
            break

        page_draws = data.get("response", [])
        if not page_draws:
            print(f"    หยุดที่ page {page} (ไม่มีข้อมูลแล้ว)")
            break

        all_draws.extend(page_draws)
        print(f"    พบ {len(page_draws)} งวด (สะสม {len(all_draws)})")

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"✓ พบทั้งหมด {len(all_draws)} งวดจาก API")
    return all_draws


def fetch_lotto_detail(draw_id):
    """ดึงรายละเอียดงวดเฉพาะ"""
    url = f"{LOTTO_URL}/{draw_id}"
    data = fetch_with_retry(url)
    if not data or data.get("status") != "success":
        return None
    return data.get("response")


def main():
    print("=" * 60)
    print("🔄 Backfill Script - ดึงงวดที่ขาดหายไป")
    print(f"⏰ เวลาที่รัน: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["lottery_db"]
    collection = db["draws"]

    try:
        # 1. ดูว่าใน DB มีงวดอะไรอยู่แล้ว
        existing_dates = set()
        for doc in collection.find({}, {"draw_date_str": 1}):
            d = doc.get("draw_date_str")
            if d:
                existing_dates.add(d.strip())
        print(f"📊 ใน MongoDB มีอยู่แล้ว {len(existing_dates)} งวด")

        # 2. ดึงรายการงวดทั้งหมดจาก API
        all_draws = get_all_draw_ids_from_api()
        if not all_draws:
            print("❌ ไม่สามารถดึงรายการงวดได้")
            sys.exit(1)

        # 3. หางวดที่ยังไม่อยู่ใน DB
        missing_draws = []
        for d in all_draws:
            api_date = d.get("date", "").strip()
            if api_date and api_date not in existing_dates:
                missing_draws.append(d)

        print(f"\n🎯 พบงวดที่ขาดหายไป {len(missing_draws)} งวด:")
        for d in missing_draws:
            print(f"   - {d.get('date')} (id: {d.get('id')})")

        if not missing_draws:
            print("✅ ข้อมูลครบถ้วนแล้ว ไม่มีงวดใดต้อง backfill")
            return

        # 4. ดึงรายละเอียดและ insert ทีละงวด
        print(f"\n📥 เริ่ม backfill {len(missing_draws)} งวด...")
        success_count = 0
        error_count = 0

        for idx, draw_info in enumerate(missing_draws, 1):
            draw_id = draw_info.get("id")
            api_date = draw_info.get("date", "").strip()
            print(f"\n[{idx}/{len(missing_draws)}] กำลังดึง: {api_date} (id: {draw_id})")

            detail = fetch_lotto_detail(draw_id)
            if not detail:
                print(f"   ❌ ดึงรายละเอียดไม่ได้")
                error_count += 1
                continue

            # แกะข้อมูล
            draw_date_str = detail.get("date", api_date).strip()
            prizes = detail.get("prizes", [])
            running_numbers = detail.get("runningNumbers", [])

            first_prize = normalize_prize_value(find_by_id_list(prizes, PRIZE_FIRST_IDS))
            three_front = normalize_prize_value(find_by_id_list(running_numbers, RUNNING_FRONT3_IDS))
            three_last = normalize_prize_value(find_by_id_list(running_numbers, RUNNING_BACK3_IDS))
            two_bottom = normalize_prize_value(find_by_id_list(running_numbers, RUNNING_BACK2_IDS))

            # ตรวจสอบ
            first_prize_valid = (
                first_prize != ["-"] and
                all(len(s) == 6 and s.isdigit() for s in first_prize)
            )
            two_digit_valid = (
                two_bottom != ["-"] and
                all(len(s) == 2 and s.isdigit() for s in two_bottom)
            )

            if not first_prize_valid and not two_digit_valid:
                print(f"   ⚠️ ข้อมูลไม่สมบูรณ์ ข้าม")
                error_count += 1
                continue

            draw_timestamp = parse_thai_date(draw_date_str) or datetime.now(timezone.utc)

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

            collection.update_one(
                {"draw_date_str": draw_date_str},
                {"$set": document},
                upsert=True
            )
            print(f"   ✅ บันทึก {draw_date_str}: รางวัลที่ 1={first_prize}, ท้าย 2={two_bottom}")
            success_count += 1

            time.sleep(DELAY_BETWEEN_REQUESTS)

        print("\n" + "=" * 60)
        print(f"🎉 เสร็จสิ้น! สำเร็จ {success_count} งวด, ผิดพลาด {error_count} งวด")
        total = collection.count_documents({})
        print(f"📊 คลังข้อมูลปัจจุบัน: {total} งวด")
        print("=" * 60)

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
