import os
import requests
import pymongo
import certifi
from datetime import datetime

MONGO_URI = os.environ.get("MONGO_URI")

if not MONGO_URI:
    print("Error: ไม่พบ MONGO_URI กรุณาตรวจสอบการตั้งค่า Secrets ใน GitHub")
    exit(1)

client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["lottery_db"]
collection = db["draws"]

def fetch_and_save_latest_lotto():
    print("กำลังดึงข้อมูลผลสลากกินแบ่งรัฐบาลงวดล่าสุดเพื่อสะสมลงฐานข้อมูล...")
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
            
            first_prize = next((item["number"] for item in prizes if item.get("id") == "prize1"), ["-"])
            three_front = next((item["number"] for item in running_numbers if item.get("id") == "front3"), ["-"])
            three_last = next((item["number"] for item in running_numbers if item.get("id") == "last3"), ["-"])
            two_bottom = next((item["number"] for item in running_numbers if item.get("id") == "last2"), ["-"])

            document = {
                "draw_date_str": draw_date_str,
                "timestamp": datetime.utcnow(), # เก็บรอบปัจจุบัน
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
                print(f"สะสมข้อมูลสำเร็จ! เพิ่มงวดใหม่เข้าคลัง: {draw_date_str}")
            else:
                print(f"อัปเดตข้อมูลสำเร็จ! (งวด {draw_date_str} ถูกบันทึกไว้ในคลังสถิติแล้ว)")
        else:
            print("ไม่สามารถดึงข้อมูลได้: สถานะ API ไม่สำเร็จ")
            exit(1)
            
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        exit(1)

if __name__ == "__main__":
    fetch_and_save_latest_lotto()
