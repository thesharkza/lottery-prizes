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
    {
        "date": "2568-01-02",       # YYYY-MM-DD (ปี พ.ศ.)
        "first": "730209",           # รางวัลที่ 1 (6 หลัก)
        "last2": "51",               # เลขท้าย 2 ตัว
        "last3f": ["446", "065"],    # เลขหน้า 3 ตัว
        "last3b": ["376", "297"]     # เลขท้าย 3 ตัว
    },
    {
        "date": "2568-01-17",
        "first": "807779",
        "last2": "23",
        "last3f": ["699", "961"],
        "last3b": ["448", "477"]
    },
    {
        "date": "2568-02-01",
        "first": "558700",
        "last2": "51",
        "last3f": ["285", "418"],
        "last3b": ["685", "824"]
    },
    {
        "date": "2568-02-16",
        "first": "847377",
        "last2": "50",
        "last3f": ["268", "613"],
        "last3b": ["652", "001"]
    },
    {
        "date": "2568-03-01",
        "first": "818894",
        "last2": "54",
        "last3f": ["139", "530"],
        "last3b": ["656", "781"]
    },
    {
        "date": "2568-03-16",
        "first": "757563",
        "last2": "32",
        "last3f": ["595", "927"],
        "last3b": ["457", "309"]
    },
    {
        "date": "2568-04-01",
        "first": "669687",
        "last2": "36",
        "last3f": ["635", "760"],
        "last3b": ["180", "666"]
    },
    {
        "date": "2568-04-16",
        "first": "266227",
        "last2": "85",
        "last3f": ["413", "254"],
        "last3b": ["474", "760"]
    },
    {
        "date": "2568-05-02",
        "first": "213388",
        "last2": "06",
        "last3f": ["826", "116"],
        "last3b": ["167", "662"]
    },
    {
        "date": "2568-05-16",
        "first": "251309",
        "last2": "87",
        "last3f": ["109", "231"],
        "last3b": ["965", "631"]
    },
    {
        "date": "2568-06-01",
        "first": "559352",
        "last2": "20",
        "last3f": ["349", "134"],
        "last3b": ["307", "044"]
    },
    {
        "date": "2568-06-16",
        "first": "507392",
        "last2": "06",
        "last3f": ["243", "017"],
        "last3b": ["299", "736"]
    },
    {
        "date": "2568-07-01",
        "first": "949246",
        "last2": "91",
        "last3f": ["680", "169"],
        "last3b": ["918", "261"]
    },
    {
        "date": "2568-07-16",
        "first": "245324",
        "last2": "26",
        "last3f": ["243", "017"],
        "last3b": ["299", "736"]
    },
    {
        "date": "2568-08-01",
        "first": "811852",
        "last2": "50",
        "last3f": ["142", "525"],
        "last3b": ["512", "891"]
    },
    {
        "date": "2568-08-16",
        "first": "994865",
        "last2": "63",
        "last3f": ["247", "602"],
        "last3b": ["834", "989"]
    },
    {
        "date": "2568-09-01",
        "first": "506356",
        "last2": "31",
        "last3f": ["131", "012"],
        "last3b": ["022", "209"]
    },
    {
        "date": "2568-09-16",
        "first": "074646",
        "last2": "58",
        "last3f": ["512", "740"],
        "last3b": ["308", "703"]
    },
    {
        "date": "2568-10-01",
        "first": "876978",
        "last2": "77",
        "last3f": ["843", "532"],
        "last3b": ["280", "605"]
    },
    {
        "date": "2568-10-16",
        "first": "059696",
        "last2": "61",
        "last3f": ["531", "955"],
        "last3b": ["476", "889"]
    },
    {
        "date": "2568-11-01",
        "first": "345898",
        "last2": "87",
        "last3f": ["449", "328"],
        "last3b": ["111", "690"]
    },
    {
        "date": "2568-11-16",
        "first": "458145",
        "last2": "37",
        "last3f": ["242", "602"],
        "last3b": ["239", "389"]
    },
    {
        "date": "2568-12-01",
        "first": "461252",
        "last2": "22",
        "last3f": ["655", "389"],
        "last3b": ["137", "995"]
    },
    {
        "date": "2568-12-16",
        "first": "763895",
        "last2": "52",
        "last3f": ["431", "176"],
        "last3b": ["014", "449"]
    },
    {
        "date": "2569-01-02",       # YYYY-MM-DD (ปี พ.ศ.)
        "first": "837706",           # รางวัลที่ 1 (6 หลัก)
        "last2": "16",               # เลขท้าย 2 ตัว
        "last3f": ["347", "694"],    # เลขหน้า 3 ตัว
        "last3b": ["288", "765"]     # เลขท้าย 3 ตัว
    },
    {
        "date": "2569-01-17",
        "first": "878972",
        "last2": "02",
        "last3f": ["299", "815"],
        "last3b": ["662", "363"]
    },
    {
        "date": "2569-02-01",
        "first": "174629",
        "last2": "48",
        "last3f": ["917", "195"],
        "last3b": ["408", "041"]
    },
    {
        "date": "2569-02-16",
        "first": "340563",
        "last2": "07",
        "last3f": ["527", "241"],
        "last3b": ["578", "169"]
    },
    {
        "date": "2569-03-01",
        "first": "820866",
        "last2": "06",
        "last3f": ["479", "054"],
        "last3b": ["068", "837"]
    },
    {
        "date": "2569-03-16",
        "first": "833009",
        "last2": "64",
        "last3f": ["510", "983"],
        "last3b": ["439", "954"]
    },
    {
        "date": "2569-04-01",
        "first": "292514",
        "last2": "47",
        "last3f": ["406", "113"],
        "last3b": ["851", "098"]
    },
    {
        "date": "2569-04-16",
        "first": "309612",
        "last2": "77",
        "last3f": ["355", "108"],
        "last3b": ["868", "424"]
    },
    {
        "date": "2569-05-02",
        "first": "536077",
        "last2": "43",
        "last3f": ["267", "318"],
        "last3b": ["065", "153"]
    },
    {
        "date": "2569-05-16",
        "first": "107387",
        "last2": "08",
        "last3f": ["091", "298"],
        "last3b": ["602", "716"]
    },
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
