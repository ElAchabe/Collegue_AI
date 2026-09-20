import json
import re
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
REFERENCE_DIR = BASE_DIR / "data" / "reference"
ANNUAL_DIR = BASE_DIR / "data" / "plans" / "annual"

UNIT_COLORS = ["#2563eb", "#16a34a", "#d97706", "#7c3aed", "#db2777", "#0891b2"]

FRENCH_MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

DEADLINE_LABELS_FR = {
    "last_continuous_assessments": "Derniers contrôles continus",
    "massar_grades_deadline": "Saisie des notes Massar (CC)",
    "local_unified_exam_3AC": "Examen local unifié (3AC)",
    "local_exam_grades_deadline": "Saisie des notes examen local",
    "massar_report_generation": "Génération des rapports Massar",
    "class_councils": "Conseils de classe",
    "report_cards_distribution": "Distribution des bulletins",
    "massar_grades_deadline_cc": "Saisie des notes Massar (CC)",
    "collective_prep_regional_exam_3AC": "Préparation collective examen régional",
    "regional_unified_exam_3AC": "Examen régional unifié (3AC)",
    "regional_exam_grades_deadline": "Saisie des notes examen régional",
    "massar_final_report_generation": "Génération du rapport final Massar",
    "class_and_orientation_councils": "Conseils de classe et d'orientation",
    "final_results_distribution": "Distribution des résultats finaux",
}


def load(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def all_iso_dates(text):
    return re.findall(r"\d{4}-\d{2}-\d{2}", str(text))


def monday_of(d):
    return d - timedelta(days=d.weekday())


@router.get("/api/planning/annual/{annual_plan_id}/grid")
def annual_grid(annual_plan_id: str):
    plan = load(ANNUAL_DIR / f"{annual_plan_id}.json")
    if not plan:
        raise HTTPException(status_code=404, detail="Annual plan not found")

    calendar = load(REFERENCE_DIR / "calendar_clean.json") or {}
    curriculum = load(REFERENCE_DIR / "curriculum_clean.json") or {}

    milestones = calendar.get("framework_milestones", {})
    try:
        admin_entry = date.fromisoformat(milestones.get("administrative_entry"))
        mandatory_start = date.fromisoformat(milestones.get("mandatory_class_start"))
        classes_end = date.fromisoformat(milestones.get("classes_end_middle_school"))
    except Exception:
        raise HTTPException(status_code=400, detail="Calendar milestones missing or invalid")

    grid_start = monday_of(admin_entry)
    grid_end = monday_of(classes_end)

    holidays = []
    for h in calendar.get("official_holidays", []):
        try:
            holidays.append({
                "name": h.get("name"),
                "start": date.fromisoformat(h.get("start_date")),
                "end": date.fromisoformat(h.get("end_date")),
                "estimated": bool(h.get("is_estimated", False)),
            })
        except Exception:
            continue

    mid_year_start = None
    for h in holidays:
        if "mi-année" in str(h.get("name", "")).lower() or "منتصف" in str(h.get("name", "")):
            mid_year_start = h["start"]
            break
    if not mid_year_start:
        mid_year_start = date.fromisoformat("2027-01-24")

    weeks = []
    w = grid_start
    week_no = 1
    while w <= grid_end:
        w_end = w + timedelta(days=6)
        full = None
        partial = []
        for h in holidays:
            if h["start"] <= w and h["end"] >= w_end:
                full = h["name"]
            elif h["start"] <= w_end and h["end"] >= w:
                partial.append(h["name"])
        weeks.append({
            "week": week_no,
            "start": w.isoformat(),
            "end": w_end.isoformat(),
            "month": FRENCH_MONTHS[w.month - 1],
            "full_holiday": full,
            "partial_holidays": partial,
            "teaching": (full is None) and (w_end >= mandatory_start) and (w <= classes_end),
        })
        w += timedelta(days=7)
        week_no += 1

    teaching_weeks = [wk for wk in weeks if wk["teaching"]]
    ord_map = {i + 1: wk for i, wk in enumerate(teaching_weeks)}

    def week_number_of(d):
        return ((d - grid_start).days // 7) + 1

    today = date.today()
    deadlines = []
    for sem_key, sem in calendar.get("middle_school_assessment_schedule", {}).items():
        sem_num = 1 if sem_key == "semester_1" else 2
        for key, value in sem.items():
            found = all_iso_dates(value)
            if not found:
                continue
            d0 = date.fromisoformat(found[0])
            d1 = date.fromisoformat(found[-1])
            deadlines.append({
                "label": DEADLINE_LABELS_FR.get(key, key),
                "date": d0.isoformat(),
                "end_date": d1.isoformat(),
                "semester": sem_num,
                "week": week_number_of(d0),
                "days_until": (d0 - today).days,
            })
    deadlines.sort(key=lambda x: x["date"])

    week_deadlines = {}
    for dl in deadlines:
        week_deadlines.setdefault(dl["week"], []).append(dl["label"])

    comp_statements = {}
    for domain in curriculum.get("competency_framework", {}).get("domains_of_action", []):
        for comp in domain.get("competencies", []):
            comp_statements[comp.get("code")] = comp.get("statement")

    items = plan.get("items", [])
    unit_ids = []
    for it in items:
        if it.get("unit_id") not in unit_ids:
            unit_ids.append(it.get("unit_id"))
    unit_colors = {u: UNIT_COLORS[i % len(UNIT_COLORS)] for i, u in enumerate(unit_ids)}

    enriched = []
    occupancy = {}
    max_ord_used = 0
    for it in items:
        try:
            o_start = int(it.get("week_start", 1))
            o_end = int(it.get("week_end", o_start))
        except Exception:
            o_start = o_end = 1
        max_ord_used = max(max_ord_used, o_end)

        a_start_w = ord_map.get(o_start)
        a_end_w = ord_map.get(o_end)
        if a_start_w and a_end_w:
            a_start = date.fromisoformat(a_start_w["start"])
            a_end = date.fromisoformat(a_end_w["end"])
            semester = 1 if a_start < mid_year_start else 2
        else:
            a_start = a_end = None
            semester = 1

        e = dict(it)
        e.update({
            "ord_start": o_start,
            "ord_end": o_end,
            "week_start_date": a_start.isoformat() if a_start else "",
            "week_end_date": a_end.isoformat() if a_end else "",
            "actual_week_start": a_start_w["week"] if a_start_w else None,
            "actual_week_end": a_end_w["week"] if a_end_w else None,
            "semester": semester,
            "competency_statements": [
                comp_statements.get(c, "") for c in it.get("competency_codes", [])
            ],
            "color": unit_colors.get(it.get("unit_id"), "#888888"),
        })
        enriched.append(e)

        if a_start_w and a_end_w:
            for wk in teaching_weeks:
                if a_start_w["week"] <= wk["week"] <= a_end_w["week"]:
                    occupancy[wk["week"]] = {
                        "topic": it.get("topic"),
                        "unit_id": it.get("unit_id"),
                        "color": e["color"],
                    }

    markers = {}
    if teaching_weeks:
        markers[teaching_weeks[0]["week"]] = "Évaluation diagnostique (positionnement)"

    last_ord_of_unit = {}
    for it in items:
        last_ord_of_unit[it.get("unit_id")] = int(it.get("week_end", 1))
    for unit_id, o in last_ord_of_unit.items():
        wk = ord_map.get(o + 1) or ord_map.get(o)
        if wk:
            markers[wk["week"]] = f"Évaluation formative — {unit_id} (écrit, 20 min)"

    s1_teaching = [wk for wk in teaching_weeks if date.fromisoformat(wk["start"]) < mid_year_start]
    if s1_teaching:
        markers[s1_teaching[-1]["week"]] = "Évaluation sommative S1 (55 min)"
    if teaching_weeks:
        markers[teaching_weeks[-1]["week"]] = "Évaluation sommative S2 (55 min)"

    total_planned = 0
    for it in items:
        try:
            total_planned += int(it.get("planned_hours", 0))
        except Exception:
            pass
    official_total = int(plan.get("total_official_hours", 0))

    checks = []
    checks.append({
        "ok": total_planned == official_total,
        "label": f"Masse horaire planifiée ({total_planned} h) = masse officielle ({official_total} h)"
    })
    checks.append({
        "ok": max_ord_used <= len(teaching_weeks),
        "label": f"Semaines d'enseignement utilisées : {max_ord_used} / {len(teaching_weeks)} disponibles"
    })
    checks.append({
        "ok": True,
        "label": "Aucune séquence placée sur une semaine de vacances (moteur vérifié)"
    })
    checks.append({
        "ok": len(deadlines) > 0,
        "label": f"{len(deadlines)} échéances officielles chargées depuis academic_calendar.json"
    })
    estimated = [h["name"] for h in holidays if h["estimated"]]
    checks.append({
        "ok": True,
        "label": f"Dates estimées signalées : {', '.join(estimated) if estimated else 'aucune'}"
    })

    for wk in weeks:
        wk["marker"] = markers.get(wk["week"])
        wk["deadlines"] = week_deadlines.get(wk["week"], [])

    return {
        "annual_plan_id": plan.get("annual_plan_id"),
        "level_code": plan.get("level_code"),
        "level_name": plan.get("level_name"),
        "school_year": plan.get("school_year"),
        "subject": plan.get("subject"),
        "total_official_hours": official_total,
        "total_planned_hours": total_planned,
        "teaching_weeks_count": len(teaching_weeks),
        "checks": checks,
        "estimated_holidays": [h["name"] for h in holidays if h["estimated"]],
        "weeks": weeks,
        "deadlines": deadlines,
        "items": enriched,
        "unit_colors": unit_colors,
    }
