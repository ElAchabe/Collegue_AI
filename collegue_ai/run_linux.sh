#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.api.main:app --host 127.0.0.1 --port 8000 &

streamlit run app/frontend/Home.py --browser.gatherUsageStats false
