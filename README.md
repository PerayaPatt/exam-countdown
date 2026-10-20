# Exam Countdown

A cool web app that counts down the days left before each exam and calculates how many minutes you need to study per day to reach your goal.


Live site: https://PerayaPatt.pythonanywhere.com

## Features

- Add an exam subject with its exam date and a study goal in hours
- Log the minutes you studied each day
- See the days left, your progress, and the minutes you need to study per day
- Delete subjects you no longer need

## How it works

- Days left = exam date − today date
- Minutes per day = (goal − minutes studied) ÷ days left (rounded up)
- If the exam is today, it shows the total minutes remaining
- If the exam has already passed, or the goal is already reached, minutes per day is not shown
- Uses UTC+7. 

## Built with
Python, Flask, SQLite, plain HTML/CSS (no framework), and the Mitr font from Google Fonts

## Run locally

```
pip install flask
python app.py
```

Then open http://127.0.0.1:5000

The first run creates an `exams.db` file and adds 3 sample subjects.

## AI usage

I built this project in collaboration with Claude (Anthropic's AI assistant). 

## Not done yet

- Login system (right now everyone sees the same data)
- Editing a subject info.
- Viewing history
