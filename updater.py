name: Auto Update Lottery Data

on:
  schedule:
    # ตั้งเวลาให้รันทุกวันที่ 1 และ 16 ของทุกเดือน เวลา 09:30 UTC (ซึ่งตรงกับ 16:30 น. เวลาไทย ผลหวยออกครบพอดี)
    - cron: '30 9 1,16 * *'
  workflow_dispatch: # ปุ่มนี้อนุญาตให้เรากดสั่งรันด้วยมือได้เองผ่านหน้าเว็บ GitHub

jobs:
  update-data:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests pymongo
          
      - name: Run updater script
        env:
          # ส่งรหัสผ่านฐานข้อมูลจาก GitHub Secrets ไปให้ Python
          MONGO_URI: ${{ secrets.MONGO_URI }}
        run: python updater.py