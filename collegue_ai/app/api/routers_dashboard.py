import json
import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
REFERENCE_DIR = BASE_DIR / "data" / "reference"
PLANS_DIR = BASE_DIR / "data" / "plans"


def load(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def first_date(text):
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(text))
    return m.group(0) if m else None


@router.get("/api/dashboard/summary")
def dashboard_summary(level_code: str = "1AC", school_year: str = "2026-2027"):
    calendar = load(REFERENCE_DIR / "calendar_clean.json") or {}
    curriculum = load(REFERENCE_DIR / "curriculum_clean.json") or {}
    pedagogy = load(REFERENCE_DIR / "pedagogy_clean.json") or {}

    today = date.today()

    next_holiday = None
    holidays = sorted(
        calendar.get("official_holidays", []),
        key=lambda x: x.get("start_date", "9999-12-31")
    )
    for h in holidays:
        d = first_date(h.get("start_date"))
        if not d:
            continue
        start = date.fromisoformat(d)
        if start >= today:
            next_holiday = {
                "name": h.get("name"),
                "start_date": h.get("start_date"),
                "end_date": h.get("end_date"),
                "days_until": (start - today).days,
                "is_estimated": bool(h.get("is_estimated", False))
            }
            break

    key_dates = []
    schedule = calendar.get("middle_school_assessment_schedule", {})
    for sem_key, sem in schedule.items():
        for label, value in sem.items():
            d = first_date(value)
            if d:
                key_dates.append({"label": label, "date": d})

    milestones = calendar.get("framework_milestones", {})
    for label, value in milestones.items():
        if isinstance(value, str):
            d = first_date(value)
            if d:
                key_dates.append({"label": label, "date": d})

    upcoming = [k for k in key_dates if date.fromisoformat(k["date"]) >= today]
    upcoming.sort(key=lambda x: x["date"])

    main_deadlines = []
    for k in upcoming[:3]:
        main_deadlines.append({
            "label": k["label"],
            "date": k["date"],
            "days_until": (date.fromisoformat(k["date"]) - today).days
        })

    level = curriculum.get("didactic_programs_by_level", {}).get(level_code, {})
    units = level.get("units", [])
    sub_modules = [sm for u in units for sm in u.get("sub_modules", [])]

    annual = load(PLANS_DIR / "annual" / f"AP-{level_code}-{school_year}.json")
    annual_done = bool(annual)

    unit_dir = PLANS_DIR / "unit"
    unit_done = len(list(unit_dir.glob(f"UP-{level_code}-*-{school_year}.json"))) if unit_dir.exists() else 0
    unit_total = len(units)

    seq_dir = PLANS_DIR / "sequence"
    seq_done = len([
        p for p in seq_dir.glob("SEQ-*.json")
        if p.name.startswith(f"SEQ-{level_code}_")
    ]) if seq_dir.exists() else 0
    seq_total = len(sub_modules) * 3

    progress = 0.0
    if annual_done:
        progress += 0.2
    if unit_total:
        progress += 0.4 * min(unit_done / unit_total, 1.0)
    if seq_total:
        progress += 0.4 * min(seq_done / seq_total, 1.0)

    tips_src = pedagogy.get("predecessor_teacher_tips", {})
    tips = tips_src.get("didactic_best_practices", [])[:2]
    tips += tips_src.get("laboratory_management", [])[:2]

    return {
        "today": today.isoformat(),
        "level_code": level_code,
        "school_year": school_year,
        "next_holiday": next_holiday,
        "main_deadlines": main_deadlines,
        "progress": {
            "percent": int(round(progress * 100)),
            "annual_done": annual_done,
            "units_done": unit_done,
            "units_total": unit_total,
            "fiches_done": seq_done,
            "fiches_total": seq_total
        },
        "tips": tips
    }
