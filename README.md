# 📊 ระบบคำนวณและวิเคราะห์สถิติสลากกินแบ่งรัฐบาล

แอปพลิเคชัน Streamlit สำหรับวิเคราะห์สถิติผลสลากกินแบ่งรัฐบาลไทยย้อนหลัง พร้อมโมเดลคณิตศาสตร์ 7 รูปแบบ

> ⚠️ **คำเตือน**: ผลสลากเป็นเหตุการณ์สุ่มอิสระ โมเดลที่แสดงในแอปนี้ไม่สามารถใช้พยากรณ์ผลในอนาคตได้จริง ใช้เพื่อความบันเทิงเท่านั้น

## โครงสร้างไฟล์

- `app.py` — แอป Streamlit หลัก
- `applotto.py` — ดึงผลสลากงวดล่าสุดจาก API บันทึกลง MongoDB
- `seed_history.py` — นำเข้าข้อมูลย้อนหลังจาก `lotto.csv`
- `lotto.csv` — ข้อมูลย้อนหลัง
- `requirements.txt` — Python dependencies
- `.github/workflows/fetch_lotto.yml` — ดึงผลอัตโนมัติทุกงวด

## การติดตั้งและรันบนเครื่อง

```bash
pip install -r requirements.txt

# ตั้งค่า MongoDB URI
export MONGO_URI="mongodb+srv://..."

# นำเข้าข้อมูลย้อนหลัง (รันครั้งเดียว)
python seed_history.py

# ดึงผลงวดล่าสุด (รันทุกงวด)
python applotto.py

# รันแอป
streamlit run app.py
```

## การ Deploy บน Streamlit Cloud

1. Push โค้ดขึ้น GitHub
2. ไปที่ [Streamlit Cloud](https://share.streamlit.io) สร้าง app ใหม่
3. ใน Settings → Secrets ใส่:
   ```toml
   MONGO_URI = "mongodb+srv://..."
   ```

## การตั้งค่า GitHub Actions

ใน Repository Settings → Secrets and variables → Actions เพิ่ม secret ชื่อ `MONGO_URI`

Workflow จะรันอัตโนมัติตามตารางในวันที่ 1 และ 16 ของทุกเดือน เพื่อดึงผลสลากงวดล่าสุดเข้า MongoDB

## โมเดลคณิตศาสตร์ที่ใช้

1. **Bayes' Theorem** — ความน่าจะเป็นแบบเงื่อนไขตามเดือน
2. **Poisson Distribution** — โอกาสออกในงวดถัดไปจาก rate ต่อ 1 งวด
3. **Chi-Square** — ค่าเบี่ยงเบนจากค่าคาดหวัง
4. **Regression to the Mean** — ดัชนีการอั้นค้าง
5. **Markov Chain** — ความน่าจะเป็นของเลขถัดไปจากเลขล่าสุด
6. **EMA Weighting** — น้ำหนักงวดล่าสุดเชิงเลขชี้กำลัง
7. **Digit Sum & Parity Filter** — สมดุลผลรวมหลักและพิกัดคู่-คี่
