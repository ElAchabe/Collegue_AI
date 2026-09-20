@echo off
cd /d %~dp0

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate.bat

pip install -r requirements.txt

start "Collegue AI API" cmd /k uvicorn app.api.main:app --host 0.0.0.0 --port 8000

timeout /t 3

streamlit run app/frontend/Home.py --browser.gatherUsageStats false
