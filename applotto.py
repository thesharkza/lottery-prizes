import os
import requests
import pymongo
import certifi
from datetime import datetime

# 1. ดึงข้อมูลการเชื่อมต่อจาก Environment Variable ที่ GitHub ส่งมาให้
MONGO_URI = os.environ.get("MONGO_URI")

if not MONGO_URI:
    print("Error: ไม่พบ MONGO_URI กรุณาตรวจสอบการตั้งค่า Secrets ใน GitHub")
    exit(1)

# 2. ตั้งค่าการเชื่อมต่อ MongoDB พร้อมเพิ่ม certifi ป้องกันปัญหา SSL
client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["lottery_db"]
collection = db["draws"]

def generate_html_page(draw_date_str, prizes_data):
    """ฟังก์ชันสร้างหน้าเว็บ index.html ดีไซน์สวยงามอัตโนมัติ"""
    print("กำลังสร้างหน้าเว็บผลสลากกินแบ่งรัฐบาล (index.html)...")
    
    # ดึงค่ารางวัลออกมาแสดงผล
    first = prizes_data.get("FIRST", "-")
    two_digit = prizes_data.get("TWO_DIGIT", "-")
    three_front = prizes_data.get("THREE_FRONT", "-")
    three_last = prizes_data.get("THREE_LAST", "-")

    # ตัวช่วยจัดรูปแบบแสดงผลเลข 3 ตัว (กรณีมาเป็นลิสต์)
    def format_number(val):
        if isinstance(val, list):
            return " , ".join(val)
        return str(val)

    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ผลสลากกินแบ่งรัฐบาล งวดล่าสุด</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Sarabun', sans-serif;
        }}
    </style>
</head>
<body class="bg-gray-50 text-gray-800 min-h-screen flex flex-col justify-between">

    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <header class="text-center mb-10">
            <h1 class="text-3xl md:text-4xl font-bold text-red-600 mb-2">ตรวจผลสลากกินแบ่งรัฐบาล</h1>
            <p class="text-xl text-gray-600 font-semibold">งวดประจำวันที่: <span class="text-blue-600 font-bold">{draw_date_str}</span></p>
            <p class="text-xs text-gray-400 mt-2">อัปเดตล่าสุด: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (เวลาไทย)</p>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            
            <div class="bg-white border-t-8 border-red-500 rounded-xl shadow-md p-6 text-center md:col-span-2">
                <h2 class="text-xl font-bold text-gray-500 uppercase tracking-wide mb-2">รางวัลที่ 1</h2>
                <div class="text-4xl md:text-6xl font-extrabold text-red-600 tracking-widest">{format_number(first)}</div>
            </div>

            <div class="bg-white border-t-8 border-blue-500 rounded-xl shadow-md p-6 text-center">
                <h2 class="text-xl font-bold text-gray-500 tracking-wide mb-2">เลขหน้า 3 ตัว</h2>
                <div class="text-3xl font-bold text-blue-600 tracking-wider">{format_number(three_front)}</div>
            </div>

            <div class="bg-white border-t-8 border-blue-500 rounded-xl shadow-md p-6 text-center">
                <h2 class="text-xl font-bold text-gray-500 tracking-wide mb-2">เลขท้าย 3 ตัว</h2>
                <div class="text-3xl font-bold text-blue-600 tracking-wider">{format_number(three_last)}</div>
            </div>

            <div class="bg-white border-t-8 border-green-500 rounded-xl shadow-md p-6 text-center md:col-span-2">
                <h2 class="text-xl font-bold text-gray-500 tracking-wide mb-2">เลขท้าย 2 ตัว</h2>
                <div class="text-4xl font-bold text-green-600 tracking-widest">{format_number(two_digit)}</div>
            </div>

        </div>
    </div>

    <footer class="bg-gray-800 text-gray-400 text-center py-4 text-sm">
        <p>&copy; {datetime.now().year} Lottery Prizes Hub. ข้อมูลจาก Rayriffy API</p>
    </footer>

</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("สร้างหน้าเว็บสำเร็จ!")

def fetch_and_save_latest_lotto():
    print("กำลังดึงข้อมูลผลสลากกินแบ่งรัฐบาลงวดล่าสุด...")
    
    api_url = "https://lotto.api.rayriffy.com/latest"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            response_data = data["response"]
            
            draw_date_str = response_data.get("date") 
            prizes = response_data.get("prizes", [])
            running_numbers = response_data.get("runningNumbers", [])
            
            # ค้นหารางวัลอย่างปลอดภัยโดยใช้ 'id'
            first_prize = next((item["number"] for item in prizes if item.get("id") == "prize1"), ["-"])
            three_front = next((item["number"] for item in running_numbers if item.get("id") == "front3"), ["-"])
            three_last = next((item["number"] for item in running_numbers if item.get("id") == "last3"), ["-"])
            two_bottom = next((item["number"] for item in running_numbers if item.get("id") == "last2"), ["-"])

            prizes_dict = {
                "FIRST": first_prize,
                "TWO_DIGIT": two_bottom,
                "THREE_FRONT": three_front,
                "THREE_LAST": three_last
            }

            document = {
                "draw_date_str": draw_date_str,
                "timestamp": datetime.utcnow(),
                "prizes": prizes_dict
            }

            # บันทึกลง MongoDB
            result = collection.update_one(
                {"draw_date_str": draw_date_str},
                {"$set": document},
                upsert=True
            )
            
            if result.upserted_id:
                print(f"บันทึกข้อมูลสำเร็จ! เพิ่มงวดใหม่: {draw_date_str}")
            else:
                print(f"อัปเดตข้อมูลสำเร็จ! (มีงวด {draw_date_str} ในระบบแล้ว)")
                
            # เรียกใช้ฟังก์ชันสร้างหน้าเว็บหลังจากดึงข้อมูลเสร็จสิ้น
            generate_html_page(draw_date_str, prizes_dict)

        else:
            print("ไม่สามารถดึงข้อมูลได้: สถานะ API ไม่สำเร็จ")
            exit(1)
            
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_save_latest_lotto()
