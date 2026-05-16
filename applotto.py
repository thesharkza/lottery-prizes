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

def fetch_and_save_latest_lotto():
    print("กำลังดึงข้อมูลผลสลากกินแบ่งรัฐบาลงวดล่าสุด...")
    
    # 3. ดึงข้อมูลจาก Rayriffy API
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
            
            # ค้นหารางวัลอย่างปลอดภัยโดยใช้ 'id' ป้องกันความผิดพลาดของข้อมูล
            first_prize = next((item["number"] for item in prizes if item.get("id") == "prize1"), "-")
            three_front = next((item["number"] for item in running_numbers if item.get("id") == "front3"), "-")
            three_last = next((item["number"] for item in running_numbers if item.get("id") == "last3"), "-")
            two_bottom = next((item["number"] for item in running_numbers if item.get("id") == "last2"), "-")

            document = {
                "draw_date_str": draw_date_str,
                "timestamp": datetime.utcnow(),
                "prizes": {
                    "FIRST": first_prize,
                    "TWO_DIGIT": two_bottom,
                    "THREE_FRONT": three_front,
                    "THREE_LAST": three_last
                }
            }

            # 4. บันทึกลง MongoDB
            result = collection.update_one(
                {"draw_date_str": draw_date_str},
                {"$set": document},
                upsert=True
            )
            
            if result.upserted_id:
                print(f"บันทึกข้อมูลสำเร็จ! เพิ่มงวดใหม่: {draw_date_str}")
            else:
                print(f"อัปเดตข้อมูลสำเร็จ! (มีงวด {draw_date_str} ในระบบแล้ว)")
        else:
            print("ไม่สามารถดึงข้อมูลได้: สถานะ API ไม่สำเร็จ")
            exit(1)
            
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_save_latest_lotto()
