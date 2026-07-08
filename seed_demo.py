"""Seed the database with a demo account, a sample form (all question types),
and a batch of random responses — so the dashboard has something to show.

Usage:
    python seed_demo.py

Login afterwards with:  username = demo   password = demo1234
Safe to re-run: it skips creation if the demo form already exists.
"""
import json
import random
from datetime import datetime, timedelta

from app import app
from models import db, User, Form, Question, Response, Answer

DEMO_USER = "demo"
DEMO_PASS = "demo1234"


def seed():
    with app.app_context():
        db.create_all()

        user = User.query.filter_by(username=DEMO_USER).first()
        if not user:
            user = User(username=DEMO_USER, email="demo@example.com")
            user.set_password(DEMO_PASS)
            db.session.add(user)
            db.session.commit()
            print(f"created user: {DEMO_USER} / {DEMO_PASS}")

        if Form.query.filter_by(user_id=user.id, title="แบบสำรวจความพึงพอใจร้านกาแฟ Bean & Co.").first():
            print("demo form already exists - skipping (login: demo / demo1234)")
            return

        form = Form(
            user_id=user.id,
            title="แบบสำรวจความพึงพอใจร้านกาแฟ Bean & Co.",
            description="ช่วยบอกความคิดเห็นของคุณ เพื่อให้เราพัฒนาบริการให้ดียิ่งขึ้น 🙏",
            is_active=True,
        )
        db.session.add(form)
        db.session.flush()

        specs = [
            dict(text="เมนูที่คุณสั่งบ่อยที่สุด", type="multiple",
                 options=["อเมริกาโน่", "ลาเต้", "คาปูชิโน่", "มัทฉะ", "ชาไทย"], required=True),
            dict(text="โปรโมชั่นที่คุณสนใจ (เลือกได้หลายข้อ)", type="checkbox",
                 options=["ซื้อ 1 แถม 1", "สะสมแต้ม", "ส่วนลดนักเรียน", "เมนูตามฤดูกาล"]),
            dict(text="ให้คะแนนความพึงพอใจโดยรวม", type="scale",
                 scale_min=1, scale_max=5, scale_label_low="ไม่พอใจ", scale_label_high="พอใจมาก", required=True),
            dict(text="สาขาที่คุณใช้บริการ", type="dropdown",
                 options=["สยาม", "อารีย์", "ทองหล่อ", "เอกมัย"]),
            dict(text="วันที่มาใช้บริการล่าสุด", type="date"),
            dict(text="ข้อเสนอแนะเพิ่มเติม", type="paragraph"),
        ]
        questions = []
        for i, s in enumerate(specs):
            q = Question(
                form_id=form.id, text=s["text"], type=s["type"],
                options_json=json.dumps(s.get("options", []), ensure_ascii=False),
                required=s.get("required", False), order_index=i + 1,
                scale_min=s.get("scale_min", 1), scale_max=s.get("scale_max", 5),
                scale_label_low=s.get("scale_label_low", ""), scale_label_high=s.get("scale_label_high", ""),
            )
            db.session.add(q)
            questions.append((q, s))
        db.session.flush()

        comments = [
            "กาแฟอร่อยมาก บริการดีเยี่ยม", "ที่นั่งน้อยไปหน่อยช่วงเย็น",
            "พนักงานยิ้มแย้มดีค่ะ", "อยากให้มีเมนูไม่หวานเพิ่ม",
            "ราคาโอเคเมื่อเทียบกับคุณภาพ", "wifi เร็วดี นั่งทำงานได้",
            "ขนมอร่อย แต่หมดเร็ว", "", "", "บรรยากาศดีมากกก",
        ]
        now = datetime.utcnow()
        n = 24
        for r in range(n):
            submitted = now - timedelta(days=random.randint(0, 9), hours=random.randint(0, 23))
            resp = Response(form_id=form.id, session_id=f"seed-{r}", submitted_at=submitted)
            db.session.add(resp)
            db.session.flush()
            for q, s in questions:
                val = None
                if q.type == "multiple":
                    val = random.choice(s["options"])
                elif q.type == "checkbox":
                    val = random.sample(s["options"], random.randint(1, len(s["options"])))
                elif q.type == "scale":
                    val = random.choices([3, 4, 5, 4, 5, 2], k=1)[0]
                elif q.type == "dropdown":
                    val = random.choice(s["options"])
                elif q.type == "date":
                    val = (submitted - timedelta(days=random.randint(0, 3))).strftime("%Y-%m-%d")
                elif q.type == "paragraph":
                    c = random.choice(comments)
                    val = c if c else None
                if val is None:
                    continue
                db.session.add(Answer(
                    response_id=resp.id, question_id=q.id,
                    value_json=json.dumps(val, ensure_ascii=False),
                ))
        db.session.commit()
        print(f"created demo form with {len(questions)} questions and {n} responses")
        print(f"\nLogin:  {DEMO_USER} / {DEMO_PASS}")


if __name__ == "__main__":
    seed()
