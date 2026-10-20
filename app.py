import math
import os
import sqlite3
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Flask, redirect, render_template_string, request

app = Flask(__name__)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exams.db")


def today():
    # server ของ PythonAnywhere ใช้เวลา UTC ต้องใช้เวลาไทย ไม่งั้นช่วงตี 0-7 วันจะเพี้ยน
    return datetime.now(ZoneInfo("Asia/Bangkok")).date()


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            goal INTEGER NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)
    # ใส่ข้อมูลตัวอย่างครั้งแรกที่ยังไม่มีอะไร (วันที่นับจากวันนี้ หน้าเว็บจะมีของให้ดูเสมอ)
    if con.execute("SELECT COUNT(*) FROM exams").fetchone()[0] == 0:
        t = today()
        con.executemany(
            "INSERT INTO exams (name, exam_date, goal, done) VALUES (?, ?, ?, ?)",
            [
                ("ฟิสิกส์ กลางภาค", str(t + timedelta(days=14)), 900, 540),
                ("เคมี กลางภาค", str(t + timedelta(days=17)), 720, 180),
                ("ชีววิทยา กลางภาค", str(t + timedelta(days=21)), 600, 210),
            ],
        )
    con.commit()
    con.close()


init_db()


@app.route("/")
def index():
    con = db()
    rows = con.execute("SELECT * FROM exams ORDER BY exam_date").fetchall()
    con.close()

    exams = []
    for r in rows:
        days_left = (date.fromisoformat(r["exam_date"]) - today()).days
        remain = max(r["goal"] - r["done"], 0)
        if days_left > 0:
            per_day = math.ceil(remain / days_left)
        elif days_left == 0:
            per_day = remain  # สอบวันนี้ ห้ามหารด้วย 0
        else:
            per_day = 0  # สอบไปแล้ว
        percent = min(round(r["done"] * 100 / r["goal"]), 100)
        exams.append(dict(r, days_left=days_left, remain=remain, per_day=per_day, percent=percent))

    return render_template_string(PAGE, exams=exams, today=today(), err=request.args.get("err"))


@app.route("/add", methods=["POST"])
def add():
    name = request.form.get("name", "").strip()
    try:
        exam_date = date.fromisoformat(request.form.get("exam_date", ""))
        hours = int(request.form.get("hours", ""))
    except ValueError:
        return redirect("/?err=วันที่หรือจำนวนชั่วโมงไม่ถูกต้อง")
    if not name or len(name) > 100:
        return redirect("/?err=ใส่ชื่อวิชา (ไม่เกิน 100 ตัวอักษร)")
    if exam_date < today():
        return redirect("/?err=วันสอบผ่านไปแล้ว")
    if hours < 1 or hours > 500:
        return redirect("/?err=เป้าหมายต้องอยู่ระหว่าง 1-500 ชั่วโมง")

    con = db()
    con.execute(
        "INSERT INTO exams (name, exam_date, goal) VALUES (?, ?, ?)",
        (name, str(exam_date), hours * 60),
    )
    con.commit()
    con.close()
    return redirect("/")


@app.route("/log/<int:exam_id>", methods=["POST"])
def log(exam_id):
    try:
        minutes = int(request.form.get("minutes", ""))
    except ValueError:
        return redirect("/?err=ใส่นาทีเป็นตัวเลข")
    if minutes < 1 or minutes > 720:
        return redirect("/?err=นาทีต้องอยู่ระหว่าง 1-720")

    con = db()
    con.execute("UPDATE exams SET done = done + ? WHERE id = ?", (minutes, exam_id))
    con.commit()
    con.close()
    return redirect("/")


@app.route("/delete/<int:exam_id>", methods=["POST"])
def delete(exam_id):
    con = db()
    con.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    con.commit()
    con.close()
    return redirect("/")


PAGE = """
<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>อีกกี่วันสอบ</title>
<link href="https://fonts.googleapis.com/css2?family=Mitr:wght@300;500&display=swap" rel="stylesheet">
<style>
  body { font-family: 'Mitr', sans-serif; font-weight: 300; background: #fff8e7; color: #3d405b; margin: 0; }
  .page { max-width: 560px; margin: 0 auto; padding: 20px; }
  h1 { font-weight: 500; color: #e07a5f; margin-bottom: 0; }
  .exam { background: white; border-left: 8px solid #81b29a; border-radius: 6px; padding: 12px 16px; margin: 12px 0; }
  .exam.soon { border-color: #f2cc8f; }
  .exam.urgent { border-color: #e07a5f; }
  .exam.past { border-color: #ccc; color: #999; }
  .days { float: right; font-size: 32px; font-weight: 500; text-align: right; }
  .days small { font-size: 14px; }
  .bar { background: #eee; height: 10px; border-radius: 5px; margin: 8px 0; }
  .bar div { background: #81b29a; height: 10px; border-radius: 5px; }
  form { display: inline; }
  input, button { font-family: inherit; font-size: 14px; padding: 4px 8px; }
  button { background: #3d405b; color: white; border: none; border-radius: 4px; cursor: pointer; }
  button.del { background: none; color: #999; text-decoration: underline; }
  .err { background: #fde2e2; color: #b33; padding: 8px 12px; border-radius: 6px; }
  .add p { margin: 8px 0; }
</style>
</head>
<body>
<div class="page">
  <h1>อีกกี่วันสอบ</h1>
  <p>วันนี้ {{ today }}</p>

  {% if err %}<p class="err">{{ err }}</p>{% endif %}

  {% for e in exams %}
  <div class="exam {% if e.days_left < 0 %}past{% elif e.days_left <= 3 %}urgent{% elif e.days_left <= 14 %}soon{% endif %}">
    <div class="days">
      {% if e.days_left > 0 %}{{ e.days_left }} <small>วัน</small>
      {% elif e.days_left == 0 %}<small>สอบวันนี้</small>
      {% else %}<small>สอบแล้ว</small>{% endif %}
    </div>
    <b>{{ e.name }}</b><br>
    <small>สอบ {{ e.exam_date }}</small>
    <div class="bar"><div style="width: {{ e.percent }}%"></div></div>
    <small>
      อ่านแล้ว {{ e.done }} / {{ e.goal }} นาที ({{ e.percent }}%)
      {% if e.remain == 0 %} · ครบแล้ว
      {% elif e.days_left >= 0 %} · ต้องอ่านวันละ <b>{{ e.per_day }}</b> นาที{% endif %}
    </small>
    <div style="margin-top: 8px">
      {% if e.days_left >= 0 %}
      <form method="post" action="/log/{{ e.id }}">
        <input name="minutes" type="number" min="1" max="720" required placeholder="นาที" style="width: 70px">
        <button>บันทึก</button>
      </form>
      {% endif %}
      <form method="post" action="/delete/{{ e.id }}" onsubmit="return confirm('ลบวิชานี้?')">
        <button class="del">ลบ</button>
      </form>
    </div>
  </div>
  {% else %}
  <p>ยังไม่มีวิชาสอบ ลองเพิ่มข้างล่างดู</p>
  {% endfor %}

  <h3>เพิ่มวิชาสอบ</h3>
  <div class="exam add">
    <form method="post" action="/add">
      <p>ชื่อวิชา <input name="name" required maxlength="100"></p>
      <p>วันสอบ <input name="exam_date" type="date" required></p>
      <p>อยากอ่านให้ได้ <input name="hours" type="number" min="1" max="500" required style="width: 70px"> ชั่วโมง</p>
      <button>เพิ่ม</button>
    </form>
  </div>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)
