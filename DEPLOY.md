# คู่มือ Deploy ขึ้น Cloud ให้คนอื่นใช้ (Render.com)

คู่มือนี้พาขึ้นเว็บจริงแบบละเอียด ทีละขั้น สำหรับมือใหม่ ใช้ **Render.com** เพราะ
สมัครฟรี ไม่ต้องใส่บัตรเครดิต และรองรับ WebSocket (real-time) ของแอปนี้

> โค้ดเตรียมพร้อมขึ้น cloud ให้แล้ว (อ่านพอร์ตจาก `PORT`, รองรับ `DATABASE_URL`,
> บังคับ HTTPS ได้, มีไฟล์ `render.yaml` / `Procfile` / `.gitignore` ให้ครบ)

---

## ⚠️ อ่านก่อน 1 นาที: เรื่องข้อมูลถาวร (สำคัญมาก)

- **Render ฟรี** = เว็บใช้งานได้จริง แต่ไฟล์ในเครื่องจะถูก **รีเซ็ตทุกครั้งที่ deploy ใหม่
  หรือเว็บ sleep** (ฟรีจะหลับหลังไม่มีคนใช้ 15 นาที) → ฐานข้อมูล SQLite (`survey.db`)
  **ไม่ถาวร** เหมาะสำหรับ **ลองโชว์/เดโม**
- **ถ้าจะเก็บคำตอบจริงระยะยาว** ต้องต่อฐานข้อมูล **PostgreSQL** (มีขั้นตอนด้านล่าง หัวข้อ “ทำให้ข้อมูลถาวร”)

แนะนำ: ขึ้นฟรีก่อนเพื่อเห็นเว็บทำงานจริง แล้วค่อยต่อ Postgres เมื่อจะใช้เก็บข้อมูลจริง

---

## สิ่งที่ต้องมี
1. บัญชี **GitHub** (ฟรี — สมัครที่ github.com)
2. **Git** ติดตั้งบนเครื่อง (โหลดที่ git-scm.com — Windows ติดตั้งแบบกด Next ไปเรื่อยๆ ได้)
3. บัญชี **Render** (สมัครด้วย GitHub ได้เลย)

---

## ขั้นที่ 1 — เอาโค้ดขึ้น GitHub

1. ไปที่ github.com → กด **New repository** → ตั้งชื่อ เช่น `survey-studio` →
   เลือก **Private** หรือ Public ก็ได้ → **อย่า** ติ๊ก add README → กด Create

2. เปิด Command Prompt / PowerShell ในโฟลเดอร์ `D:\Dashborad` แล้วพิมพ์ทีละบรรทัด
   (แทน `USERNAME` และ `survey-studio` ด้วยของคุณ):
   ```bash
   git init
   git add .
   git commit -m "first commit"
   git branch -M main
   git remote add origin https://github.com/USERNAME/survey-studio.git
   git push -u origin main
   ```
   > ไฟล์ `.gitignore` จะกัน `venv/`, `survey.db`, `.secret_key` ไม่ให้อัปโหลดโดยอัตโนมัติ (ปลอดภัย)

3. รีเฟรชหน้า GitHub — จะเห็นไฟล์โปรเจกต์ขึ้นครบ

---

## ขั้นที่ 2 — สร้างเว็บบน Render (วิธีที่ง่ายที่สุด: Blueprint)

โปรเจกต์นี้มีไฟล์ `render.yaml` อยู่แล้ว Render จะตั้งค่าให้อัตโนมัติ

1. ไปที่ render.com → **Sign up** ด้วย GitHub
2. กด **New +** (มุมขวาบน) → เลือก **Blueprint**
3. เลือก repo `survey-studio` ที่เพิ่ง push ขึ้นไป → กด **Connect**
4. Render จะอ่าน `render.yaml` แล้วแสดงบริการ `survey-studio` (plan: Free) พร้อมตั้ง
   `SECRET_KEY` (สุ่มให้), `FORCE_HTTPS=1`, `PYTHON_VERSION` ให้เอง → กด **Apply / Create**
5. รอ build ~2–4 นาที (ดู log ได้ในหน้า Render) จนขึ้น **Live**

> **ทางเลือก (ตั้งเอง ไม่ใช้ Blueprint):** New + → **Web Service** → เลือก repo →
> ตั้งค่า **Build Command:** `pip install -r requirements.txt` · **Start Command:** `python app.py` ·
> **Instance Type:** Free → เพิ่ม Environment Variables: `PYTHON_VERSION=3.12.7`,
> `SECRET_KEY=`(กด Generate หรือใส่ข้อความสุ่มยาวๆ), `FORCE_HTTPS=1` → Create

---

## ขั้นที่ 3 — ตั้งค่า URL ให้ลิงก์แชร์/QR ถูกต้อง

1. เมื่อ Live แล้ว Render จะให้ URL เช่น `https://survey-studio.onrender.com`
2. ไปที่แท็บ **Environment** ของบริการ → เพิ่ม/แก้ตัวแปร:
   - `BASE_URL` = `https://survey-studio.onrender.com` (URL จริงของคุณ)
3. กด **Save Changes** → Render จะ deploy ใหม่รอบเดียว
   (ถ้าไม่ตั้ง ลิงก์แชร์กับ QR code จะยังชี้ไป localhost)

เสร็จแล้ว! เปิด URL นั้น → **สมัครสมาชิกใหม่** (บัญชี `demo` มีเฉพาะตอนรันในเครื่อง —
บนเว็บจริงไม่มี และไม่ควรสร้าง เพราะรหัสผ่านเป็นที่รู้กันทั่วไป) → สร้างฟอร์ม →
กด **แชร์** เอาลิงก์/QR ส่งให้คนอื่นตอบได้เลย ✅

---

## ทำให้ข้อมูลถาวร (สำหรับเก็บคำตอบจริง)

### วิธี A — ใช้ PostgreSQL ฟรีของ Render (แนะนำ)
1. New + → **PostgreSQL** → plan **Free** → **Region เดียวกับ web service**
   (ถ้าไม่เคยเลือกไว้ = Oregon) → Create (ฐานข้อมูลฟรี 1 GB)
2. เปิดหน้าฐานข้อมูลที่สร้าง → คัดลอก **Internal Database URL**
   (ขึ้นต้นด้วย `postgres://...`)
3. ไปที่ **web service** → Environment → เพิ่ม:
   - `DATABASE_URL` = (วาง Internal Database URL ที่คัดลอกมา)
4. Save → Render จะ deploy ใหม่เอง ตอนนี้คำตอบถูกเก็บใน Postgres แล้ว
   (ไดรเวอร์ `psycopg2-binary` อยู่ใน requirements.txt แล้ว — โค้ดสลับไปใช้
   Postgres อัตโนมัติเมื่อมี `DATABASE_URL` และสร้างตารางให้เองตอนบูต)
   > ⚠️ Postgres ฟรีของ Render **หมดอายุ 30 วันหลังสร้าง** — Render จะเมลเตือน
   > แล้วให้เวลาอีก 14 วันเพื่ออัปเกรดเป็นแบบจ่ายเงิน ไม่งั้นข้อมูลถูกลบถาวร
   > → ก่อนครบกำหนด ให้ **Export คำตอบเป็น Excel/CSV** จากหน้า Dashboard เก็บไว้เสมอ

### วิธี B — ใช้ SQLite บนดิสก์ถาวร (ต้องเป็น plan จ่ายเงิน)
1. อัปเกรด web service เป็น **Starter ($7/เดือน)**
2. Settings → **Disks** → Add Disk → Mount Path: `/var/data` (เช่น 1 GB)
3. Environment → เพิ่ม `DATABASE_URL` = `sqlite:////var/data/survey.db`
   (สังเกต 4 ขีด `////` = path เต็ม) → Save

---

## อัปเดตเว็บภายหลัง

แก้โค้ดในเครื่องแล้วสั่ง:
```bash
git add .
git commit -m "อธิบายสิ่งที่แก้"
git push
```
Render จะ **deploy ให้อัตโนมัติ** ทุกครั้งที่ push ขึ้น GitHub

---

## แก้ปัญหาที่พบบ่อย (Troubleshooting)

- **เปิดเว็บครั้งแรกช้า ~1 นาที:** ปกติของ plan ฟรี (เว็บ sleep หลังไม่มีคน 15 นาที แล้วตื่นเมื่อมีคนเข้า)
- **Build ไม่ผ่าน:** เช็กว่าตั้ง `PYTHON_VERSION=3.12.7` แล้ว (กันปัญหา package บาง
  ตัวไม่มีไฟล์สำหรับ Python เวอร์ชันใหม่มาก)
- **แอป crash / เปิดไม่ขึ้น:** เปิดแท็บ **Logs** ใน Render อ่าน error บรรทัดล่างสุด
- **ข้อมูลหายหลัง deploy:** เป็นเพราะยังใช้ SQLite บนฟรีเทียร์ → ทำตามหัวข้อ “ทำให้ข้อมูลถาวร”
- **real-time ไม่อัปเดต:** Render ฟรีรองรับ WebSocket อยู่แล้ว ถ้ามีปัญหา Socket.IO จะ
  สลับไปโหมด polling ให้เอง (Dashboard ยังอัปเดตได้ แค่ช้าลงเล็กน้อย)

---

## ทางเลือกแพลตฟอร์มอื่น
- **Railway.app** — ใช้ง่ายคล้าย Render แต่มีเครดิตทดลองแล้วต้องจ่าย
- **Fly.io** — มี volume เก็บ SQLite ถาวรได้ แต่ต้องใช้ command line มากกว่า
- **PythonAnywhere** — ฟรี แต่รองรับ WebSocket ได้ไม่ดี (real-time อาจไม่ทำงาน)

Render เป็นตัวเริ่มต้นที่สมดุลสุดสำหรับแอปนี้
