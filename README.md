# Survey Studio — ระบบสร้างแบบสอบถาม + Dashboard วิเคราะห์ผล (สไตล์ Google Forms)

เว็บแอปหลายผู้ใช้ (multi-user): แต่ละคนล็อกอินเข้ามาสร้างแบบสอบถามได้อิสระ ส่งลิงก์ให้คนตอบ
(ฝั่งคนตอบไม่ต้องล็อกอิน) แล้วดูผลแบบละเอียดในหน้า Dashboard ที่อัปเดต **เรียลไทม์** เมื่อมีคำตอบใหม่

- **Backend:** Python Flask + Flask-SocketIO + Flask-Login
- **Database:** SQLite
- **Frontend:** HTML/CSS/JavaScript (vanilla) + Chart.js
- **Realtime:** WebSocket ผ่าน Socket.IO
- **ความปลอดภัย:** hash รหัสผ่าน (scrypt), CSRF protection, rate limiting, authorization ทุก route

---

## เริ่มใช้งานเร็ว (Quick start)

ต้องมี **Python 3.9 ขึ้นไป** ติดตั้งอยู่ก่อน ([ดาวน์โหลด](https://www.python.org/downloads/) — ตอนติดตั้งบน Windows ให้ติ๊ก "Add Python to PATH")

### ทุกระบบปฏิบัติการ (แนะนำ)
เปิด Terminal/Command Prompt ในโฟลเดอร์นี้แล้วพิมพ์:
```bash
python run.py
```
สคริปต์เดียวจบ — สร้าง venv, ติดตั้ง, seed, เปิดเซิร์ฟเวอร์ (ใช้ได้ทั้ง Windows/macOS/Linux)

### Windows (ดับเบิลคลิก)
ดับเบิลคลิกไฟล์ **`run.bat`** ได้เลย (มันเรียก `run.py` ให้อัตโนมัติ)

### macOS / Linux (ทางเลือก)
```bash
chmod +x run.sh && ./run.sh
```

สคริปต์จะสร้าง virtual environment, ติดตั้ง dependencies, ใส่ข้อมูลตัวอย่าง แล้วเปิดเซิร์ฟเวอร์ให้อัตโนมัติ
จากนั้นเปิดเบราว์เซอร์ไปที่ **http://localhost:5000**

> **บัญชีเดโม:** `demo` / `demo1234` (มีฟอร์มตัวอย่าง + 24 คำตอบให้ลองดู Dashboard ทันที)

### ติดตั้งเอง (ถ้าไม่ใช้สคริปต์)
```bash
python -m venv venv
# Windows:  venv\Scripts\activate
# mac/linux: source venv/bin/activate
pip install -r requirements.txt
python seed_demo.py      # (ไม่บังคับ) ใส่ข้อมูลตัวอย่าง
python app.py
```

---

## ฟีเจอร์

**สร้างแบบสอบถาม (ต้องล็อกอิน)**
- เพิ่ม/ลบ/แก้ไข/**ลากสลับลำดับ**คำถามได้ไม่จำกัด
- 8 ประเภทคำถาม: คำตอบสั้น, ย่อหน้า, ปรนัย, checkbox, dropdown, linear scale, วันที่, เวลา + ตัวคั่น section
- ตั้ง required/optional ต่อคำถาม, พรีวิว, เปิด/ปิดรับคำตอบ, ลิงก์แชร์ + **QR code**

**หน้าตอบ (ไม่ต้องล็อกอิน)**
- แสดงทุกคำถามในหน้าเดียว, validate ก่อนส่ง, รองรับภาษาไทยเต็มรูปแบบ, mobile-friendly
- หน้าขอบคุณหลังส่ง + กันตอบซ้ำด้วย cookie

**Dashboard วิเคราะห์ผล**
- ภาพรวม: จำนวนผู้ตอบ, completion rate, กราฟแนวโน้มตามเวลา
- สรุปรายคำถามตามประเภท: pie/bar + %, histogram + ค่าเฉลี่ย/มัธยฐาน, word frequency, การกระจายวันที่/เวลา
- ดูคำตอบรายบุคคล, filter ตามช่วงวันที่, **อัปเดตเรียลไทม์** ผ่าน WebSocket
- Export **CSV** และ **Excel (.xlsx)**

---

## โครงสร้างโปรเจกต์
```
app.py              — สร้างแอป, ลงทะเบียน blueprint, ตั้งค่า Socket.IO + ความปลอดภัย
config.py           — ค่าตั้งค่า (SECRET_KEY, cookie, ขนาด request, ฯลฯ)
extensions.py       — instance ของ socketio / login / csrf / limiter
models.py           — ตาราง users, forms, questions, responses, answers
authz.py            — ฟังก์ชันเช็คสิทธิ์ความเป็นเจ้าของฟอร์ม
socket_handlers.py  — จัดการ WebSocket (join room เฉพาะเจ้าของฟอร์ม)
blueprints/
  auth.py           — สมัคร / เข้าสู่ระบบ / ออกจากระบบ
  builder.py        — สร้าง/แก้ไขฟอร์ม + API จัดการคำถาม
  respond.py        — หน้าตอบ (public) + endpoint รับคำตอบ
  dashboard.py      — analytics + export CSV/Excel
templates/          — หน้า HTML (Jinja2)
static/css|js/      — main.css, builder.js, respond.js, dashboard.js
seed_demo.py        — สร้างข้อมูลตัวอย่าง
```

---

## การตั้งค่าผ่าน Environment Variables

| ตัวแปร | ค่าเริ่มต้น | ใช้ทำอะไร |
|---|---|---|
| `SECRET_KEY` | สุ่มอัตโนมัติ (เก็บใน `.secret_key`) | เซ็นเซสชัน — **ตั้งเองเสมอบน production** |
| `BASE_URL` | `http://localhost:5000` | ใช้สร้างลิงก์แชร์ + QR code ให้ถูกโดเมน |
| `FORCE_HTTPS` | ไม่ตั้ง | ตั้งเป็น `1` เมื่อรันหลัง HTTPS เพื่อบังคับ cookie ให้ปลอดภัย |

ตัวอย่าง (mac/linux):
```bash
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')"
export BASE_URL="https://survey.mydomain.com"
export FORCE_HTTPS=1
```

---

## วิธีให้คนอื่นเข้ามาใช้ (Deploy)

เลือกได้ 3 ระดับตามความต้องการ:

### ระดับ 1 — แชร์ในวง Wi-Fi/LAN เดียวกัน (ง่ายสุด)
แอปเปิดที่ `0.0.0.0:5000` อยู่แล้ว แค่หา IP เครื่องคุณ:
- Windows: `ipconfig` → ดู IPv4 Address (เช่น `192.168.1.20`)
- mac/linux: `ifconfig` หรือ `ip addr`

แล้วให้คนในวง Wi-Fi เดียวกันเปิด `http://192.168.1.20:5000/s/<form_id>`
(อาจต้องอนุญาต Python ผ่าน Firewall) — เหมาะกับงานอีเวนต์/ในออฟฟิศ

### ระดับ 2 — ลิงก์สาธารณะชั่วคราว (เดโมให้ลูกค้า)
ใช้ tunnel เปิดพอร์ตออกอินเทอร์เน็ตโดยไม่ต้องมีเซิร์ฟเวอร์:
```bash
python app.py                     # เทอร์มินัลที่ 1
# เทอร์มินัลที่ 2 — เลือกอย่างใดอย่างหนึ่ง:
ngrok http 5000                   # https://ngrok.com
cloudflared tunnel --url http://localhost:5000   # ฟรี ไม่ต้องสมัคร
```
คัดลอกลิงก์ `https://xxxx.ngrok.io` ที่ได้ แล้วตั้ง `BASE_URL` เป็นลิงก์นั้นเพื่อให้ QR/ลิงก์แชร์ถูกต้อง

### ระดับ 3 — Production จริง (ใช้งานถาวร)

**3.1 ใช้ production server**

แอปตั้งค่า Socket.IO เป็น **async mode = `threading`** (ทำงานได้ทุกเวอร์ชัน Python รวมถึง 3.14
โดยไม่ต้องพึ่ง eventlet/gevent) เหมาะกับงานสเกลเล็ก–กลาง ทั่วไปให้รันหลัง nginx ได้เลย:
```bash
python app.py            # เสิร์ฟที่ 0.0.0.0:5000 (WebSocket ผ่าน simple-websocket)
```

ถ้าต้องรองรับผู้ใช้พร้อมกันจำนวนมาก แนะนำใช้เซิร์ฟเวอร์ที่ล็อกเป็น **Python 3.11/3.12**
แล้วรันด้วย gunicorn + eventlet worker (เร็วกว่าสำหรับ concurrency สูง):
```bash
pip install gunicorn eventlet
gunicorn -k eventlet -w 1 app:app -b 0.0.0.0:5000
```
> **สำคัญ:** ไม่ว่าโหมดไหน ให้ใช้ **1 worker** (`-w 1`) เพราะเก็บ room ไว้ในหน่วยความจำ
> ถ้าต้องสเกลหลาย worker/หลายเครื่อง ต้องเพิ่ม message queue (Redis) แล้วตั้ง
> `SocketIO(..., message_queue="redis://...")` ใน `extensions.py`

**3.2 ตั้ง env ก่อนรัน:** `SECRET_KEY`, `BASE_URL` (โดเมนจริง), `FORCE_HTTPS=1`

**3.3 วาง nginx เป็น reverse proxy** (สำคัญ: ต้องส่ง header สำหรับ WebSocket)
```nginx
server {
    listen 80;
    server_name survey.mydomain.com;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;      # ← จำเป็นสำหรับ WebSocket
        proxy_set_header Connection "upgrade";        # ←
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
แล้วเปิด HTTPS ด้วย Let's Encrypt (`certbot --nginx`)

**3.4 หรือใช้ PaaS (ไม่ต้องดูแลเซิร์ฟเวอร์เอง)** เช่น Render / Railway
- Start command: `python app.py` (โหมด threading) หรือถ้าล็อก Python 3.11/3.12 ใช้ `gunicorn -k eventlet -w 1 app:app`
- ตั้ง Environment Variables ตามตาราง (`SECRET_KEY`, `BASE_URL`, `FORCE_HTTPS=1`)
- ⚠️ SQLite บน PaaS ที่ filesystem ไม่ถาวรจะหายเมื่อ redeploy — ควรย้ายไป **PostgreSQL**
  (แก้ `SQLALCHEMY_DATABASE_URI` แล้ว `pip install psycopg2-binary`) สำหรับใช้งานจริงระยะยาว

---

## ความปลอดภัยที่ทำไว้แล้ว

รหัสผ่าน hash ด้วย scrypt · CSRF protection ทุกฟอร์ม/API · rate limiting (login/register/submit) ·
authorization เช็คความเป็นเจ้าของทุก route (คนอื่นเข้าฟอร์มเราไม่ได้ = 404) · Socket.IO room เฉพาะเจ้าของ ·
กันตอบซ้ำด้วย cookie · จำกัดขนาด request · sanitize กัน CSV formula injection · security headers

**เช็กลิสต์ก่อนขึ้น production:** ตั้ง `SECRET_KEY` เอง · เปิด `FORCE_HTTPS=1` หลัง TLS ·
พิจารณาย้ายจาก SQLite → PostgreSQL · สำรอง `survey.db` สม่ำเสมอ

---

## ข้อจำกัด / พัฒนาต่อได้

- Word frequency ภาษาไทยยังตัดคำแบบง่าย (เว้นวรรค) — ถ้าต้องการแม่นขึ้นใช้ `pythainlp` ได้
- กันตอบซ้ำใช้ cookie (ลบ cookie แล้วตอบใหม่ได้) — ถ้าต้องเข้มงวดเพิ่ม login ฝั่งคนตอบ หรือจำกัดต่อ IP
- Rate limit เก็บใน memory — ถ้าหลาย worker ให้ย้าย storage ไป Redis
