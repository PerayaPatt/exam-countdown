import math
import os
import sqlite3
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Flask, redirect, render_template_string, request

app = Flask(__name__)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exams.db")


def today():
    # server must use UTC+7
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
    # start with example info.
    if con.execute("SELECT COUNT(*) FROM exams").fetchone()[0] == 0:
        t = today()
        con.executemany(
            "INSERT INTO exams (name, exam_date, goal, done) VALUES (?, ?, ?, ?)",
            [
                ("Physics", str(t + timedelta(days=14)), 900, 540),
                ("Chemistry", str(t + timedelta(days=17)), 720, 180),
                ("Biology", str(t + timedelta(days=21)), 600, 210),
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
            per_day = remain  # exam today
        else:
            per_day = 0  # exam finished
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
        return redirect("/?err=The date or number of hours is incorrect.")
    if not name or len(name) > 100:
        return redirect("/?err=Subject Name (maximum 100 characters)")
    if exam_date < today():
        return redirect("/?err=The exam day has passed.")
    if hours < 1 or hours > 500:
        return redirect("/?err=The number of hours must be between 1 and 500.")

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
        return redirect("/?err=Enter the minutes as a number.")
    if minutes < 1 or minutes > 720:
        return redirect("/?err=The number of minutes must be between 1 and 720.")

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
<title>Exam Countdown</title>
<link href="https://fonts.googleapis.com/css2?family=Mitr:wght@300;500&display=swap" rel="stylesheet">
<style>
  /* Dark theme (default) */
  :root {
    color-scheme: dark;
    --bg: #0f1220;
    --card: #1a1f35;
    --line: #2f3558;
    --text: #e6e9f5;
    --muted: #8b93b5;
    --past: #2f3558;
    --ok: #2dd4bf;
    --warn: #fbbf24;
    --urgent: #fb7185;
    --btn: #7c5cff;
    --title: linear-gradient(90deg, #7c5cff, #2dd4bf);
    --bar: linear-gradient(90deg, #7c5cff, #2dd4bf);
    --input-border: #2f3558;
    --err-bg: rgba(251,113,133,.15);
    --err-text: #fb7185;
    --shadow: 0 4px 16px rgba(0,0,0,.3);
    --glow: 0 0 14px rgba(251,113,133,.25);
  }

  /* Light theme: only when the user picks it with the button */
  :root[data-theme="light"] {
    color-scheme: light;
    --bg: #f4f6ff;
    --card: #ffffff;
    --line: #e4e8f7;
    --text: #1f2340;
    --muted: #7a82a6;
    --past: #d5d9ec;
    --ok: #2dd4bf;
    --warn: #fbbf24;
    --urgent: #fb7185;
    --btn: #5b3df5;
    --title: linear-gradient(90deg, #5b3df5, #06b6d4);
    --bar: linear-gradient(90deg, #5b3df5, #06b6d4);
    --input-border: #d5d9ec;
    --err-bg: #ffe4e9;
    --err-text: #be123c;
    --shadow: 0 4px 16px rgba(91,61,245,.10);
    --glow: 0 0 14px rgba(244,63,94,.20);
  }

  body { font-family: 'Mitr', sans-serif; font-weight: 300; background: var(--bg); color: var(--text); margin: 0; }
  .page { max-width: 560px; margin: 0 auto; padding: 20px; position: relative; }
  h1 { font-weight: 500; margin-bottom: 0; background: var(--title); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .exam { background: var(--card); border-left: 8px solid var(--ok); border-radius: 8px; padding: 12px 16px; margin: 12px 0; box-shadow: var(--shadow); }
  .exam.soon { border-color: var(--warn); }
  .exam.urgent { border-color: var(--urgent); box-shadow: var(--glow); }
  .exam.past { border-color: var(--past); color: var(--muted); }
  .days { float: right; font-size: 32px; font-weight: 500; text-align: right; }
  .days small { font-size: 14px; }
  .bar { background: var(--line); height: 10px; border-radius: 5px; margin: 8px 0; }
  .bar div { background: var(--bar); height: 10px; border-radius: 5px; }
  form { display: inline; }
  input, button { font-family: inherit; font-size: 14px; padding: 4px 8px; }
  input { background: var(--card); color: var(--text); border: 1px solid var(--input-border); border-radius: 6px; }
  input::placeholder { color: var(--muted); }
  button { background: var(--btn); color: white; border: none; border-radius: 6px; cursor: pointer; }
  button.del { background: none; color: var(--muted); text-decoration: underline; }
  button.theme { position: absolute; top: 20px; right: 20px; background: var(--card); color: var(--text); border: 1px solid var(--input-border); }
  .err { background: var(--err-bg); color: var(--err-text); padding: 8px 12px; border-radius: 6px; }
  .add p { margin: 8px 0; }
</style>
<script>
  try { var t = sessionStorage.getItem('theme2'); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
</script>
</head>
<body>
<div class="page">
<button type="button" class="theme" id="themeBtn" aria-label="Switch theme">Light / Dark</button>
  <h1>Exam Countdown</h1>
  <p>Today {{ today }}</p>

  {% if err %}<p class="err">{{ err }}</p>{% endif %}

  {% for e in exams %}
  <div class="exam {% if e.days_left < 0 %}past{% elif e.days_left <= 3 %}urgent{% elif e.days_left <= 14 %}soon{% endif %}">
    <div class="days">
      {% if e.days_left > 1 %}{{ e.days_left }} <small>Days</small>
      {% elif e.days_left == 1 %}{{ e.days_left }} <small>Day</small>
      {% elif e.days_left == 0 %}<small>Exam Today</small>
      {% else %}<small>Exam Taken</small>{% endif %}
    </div>
    <b>{{ e.name }}</b><br>
    <small>Exam {{ e.exam_date }}</small>
    <div class="bar"><div style="width: {{ e.percent }}%"></div></div>
    <small>
      Read for {{ e.done }} / {{ e.goal }} minutes ({{ e.percent }}%)
      {% if e.remain == 0 %} · Complete
      {% elif e.days_left >= 0 %} · Goal: <b>{{ e.per_day }}</b> minutes/day{% endif %}
    </small>
    <div style="margin-top: 8px">
      {% if e.days_left >= 0 %}
      <form method="post" action="/log/{{ e.id }}">
        <input name="minutes" type="number" min="1" max="720" required placeholder="Minutes" style="width: 70px">
        <button>Save</button>
      </form>
      {% endif %}
      <form method="post" action="/delete/{{ e.id }}" onsubmit="return confirm('Remove this subject?')">
        <button class="del">Remove</button>
      </form>
    </div>
  </div>
  {% else %}
  <p>There are no exam subjects yet; try adding new subject.</p>
  {% endfor %}

  <h3>Add a new subject</h3>
  <div class="exam add">
    <form method="post" action="/add">
      <p>Subject Name <input name="name" required maxlength="100"></p>
      <p>Exam Date <input name="exam_date" type="date" required></p>
      <p>Reading Goal <input name="hours" type="number" min="1" max="500" required style="width: 70px"> hours</p>
      <button>Add</button>
    </form>
  </div>
</div>
<script>
  document.getElementById('themeBtn').onclick = function () {
    var root = document.documentElement;
    var isDark = root.dataset.theme !== 'light';
    var next = isDark ? 'light' : 'dark';
    root.dataset.theme = next;
    try { sessionStorage.setItem('theme2', next); } catch (e) {}
  };
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)
