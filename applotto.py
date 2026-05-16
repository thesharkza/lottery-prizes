import requests
import pymongo
from datetime import datetime

# 1. ตั้งค่าการเชื่อมต่อ MongoDB (นำ Connection String ของคุณมาใส่ที่นี่)
MONGO_URI = "mongodb+srv://<username>:<password>@cluster0.xxxx.mongodb.net/?retryWrites=true&w=majority"
client = pymongo.MongoClient(MONGO_URI)
db = client["lottery_db"]
collection = db["draws"]

def fetch_and_save_latest_lotto():
    print("กำลังดึงข้อมูลผลสลากกินแบ่งรัฐบาลงวดล่าสุด...")
    
    # 2. ดึงข้อมูลจาก Rayriffy API
    api_url = "https://lotto.api.rayriffy.com/latest"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            response_data = data["response"]
            
            # 3. จัดโครงสร้างข้อมูลให้เข้ากับ Schema ที่เราออกแบบไว้
            # ดึงวันที่งวด (เช่น "16 มีนาคม 2567")
            draw_date_str = response_data.get("date") 
            
            # สกัดหมายเลขรางวัล
            prizes = response_data.get("prizes",)
            running_numbers = response_data.get("runningNumbers",)
            
            first_prize = prizes["number"] if len(prizes) > 0 else
            three_front = running_numbers["number"] if len(running_numbers) > 0 else
            three_last = running_numbers[1]["number"] if len(running_numbers) > 1 else
            two_bottom = running_numbers[2]["number"] if len(running_numbers) > 2 else

            # สร้าง Document สำหรับ MongoDB
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
            # ใช้ update_one พร้อม upsert=True เพื่อป้องกันการบันทึกงวดเดียวกันซ้ำซ้อน
            result = collection.update_one(
                {"draw_date_str": draw_date_str}, # ค้นหาจากวันที่
                {"$set": document},               # อัปเดตหรือเพิ่มข้อมูลใหม่
                upsert=True
            )
            
            if result.upserted_id:
                print(f"บันทึกข้อมูลสำเร็จ! เพิ่มงวดใหม่: {draw_date_str}")
            else:
                print(f"อัปเดตข้อมูลสำเร็จ! (มีงวด {draw_date_str} ในระบบแล้ว)")
        else:
            print("ไม่สามารถดึงข้อมูลได้: สถานะ API ไม่สำเร็จ")
            
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    fetch_and_save_latest_lotto()
