from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import date, timedelta
from .routers_dashboard import router as dashboard_router
from .routers_ai import router as ai_router
from .routers_grid import router as grid_router
from .routers_ai import router as ai_router

import json

BASE_DIR = Path(__file__).resolve().parents[2]
REFERENCE_DIR = BASE_DIR / "data" / "reference"
PLANS_DIR = BASE_DIR / "data" / "plans"
ANNUAL_DIR = PLANS_DIR / "annual"
UNIT_DIR = PLANS_DIR / "unit"
SEQUENCE_DIR = PLANS_DIR / "sequence"
PWA_DIR = Path(__file__).resolve().parents[1] / "pwa"

for directory in [ANNUAL_DIR, UNIT_DIR, SEQUENCE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Collegue AI API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount PWA static files
app.mount("/pwa", StaticFiles(directory=PWA_DIR, html=True), name="pwa")

app.include_router(dashboard_router)
app.include_router(ai_router)
app.include_router(grid_router)
app.include_router(ai_router)

SUGGESTIONS_BY_FAMILY = {
    "C0_C31": [
        "Étaler la découverte de l'outil informatique sur plusieurs séances.",
        "Utiliser des schémas illustratifs (constituants d'un ordinateur, touches du clavier).",
        "Ouvrir au besoin une unité centrale pour l'observation.",
        "Appuyer le développement des notions par des démonstrations pratiques.",
        "Éduquer les apprenants à une éthique d'utilisation et à la préservation du matériel."
    ],
    "C11_C12": [
        "Centrer l'approche sur l'utilisation du logiciel, non sur le logiciel lui-même.",
        "Utiliser des documents courts, objectifs et motivants pour les travaux pratiques.",
        "Problématiser les activités et éviter les ateliers purement directifs.",
        "Envisager de petits projets personnels ou d'équipe.",
        "Veiller à ce que chaque apprenant bénéficie d'un temps de manipulation."
    ],
    "C13": [
        "Simple initiation : mettre l'accent sur l'analyse, l'organisation et la rigueur.",
        "Introduire les commandes d'une manière judicieuse et au besoin.",
        "Inciter les apprenants à raisonner, à déceler leurs erreurs et à les corriger.",
        "Problématiser l'introduction d'un nouvel outil (créer le besoin avant la commande)."
    ],
    "C21_C22_C23": [
        "Appuyer les activités sur des besoins réels de recherche d'information.",
        "Insister sur la méthodologie de recherche d'information.",
        "Apprendre aux apprenants à critiquer les informations trouvées.",
        "Relier les recherches aux disciplines scolaires et aux intérêts des apprenants."
    ],
    "C32_C33": [
        "Inciter chaque apprenant à créer sa propre adresse électronique.",
        "Pratiquer le travail de groupe et la communication à distance.",
        "Respecter une éthique et des valeurs sociales et citoyennes dans l'usage d'Internet."
    ]
}


def family_for_code(code):
    if code in ("C0", "C31"):
        return "C0_C31"
    if code in ("C11", "C12"):
        return "C11_C12"
    if code == "C13":
        return "C13"
    if code in ("C21", "C22", "C23"):
        return "C21_C22_C23"
    if code in ("C32", "C33"):
        return "C32_C33"
    return None


def load_json(path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_curriculum_data():
    return load_json(REFERENCE_DIR / "curriculum_clean.json")


def get_pedagogy_data():
    return load_json(REFERENCE_DIR / "pedagogy_clean.json")


def get_calendar_data():
    calendar_path = REFERENCE_DIR / "calendar_clean.json"
    return load_json(calendar_path) if calendar_path.exists() else {}


def find_competency(curriculum, code):
    framework = curriculum.get("competency_framework", {})
    for domain in framework.get("domains_of_action", []):
        for comp in domain.get("competencies", []):
            if comp.get("code") == code:
                return {
                    "code": code,
                    "domain": domain.get("name"),
                    "statement": comp.get("statement"),
                    "resources": comp.get("resources", {})
                }
    return None


def merge_resources(codes, curriculum):
    merged = {"savoir": [], "savoir_faire": [], "savoir_etre": []}
    for code in codes:
        comp = find_competency(curriculum, code)
        if not comp:
            continue
        for key in merged:
            for item in comp.get("resources", {}).get(key, []):
                if item not in merged[key]:
                    merged[key].append(item)
    return merged


def suggestions_for_codes(codes):
    suggestions = []
    for code in codes:
        family = family_for_code(code)
        if family:
            for s in SUGGESTIONS_BY_FAMILY[family]:
                if s not in suggestions:
                    suggestions.append(s)
    return suggestions


def week_to_date(calendar, week_number):
    milestones = calendar.get("framework_milestones", {})
    start_text = milestones.get("mandatory_class_start")
    if not start_text:
        return None
    try:
        start = date.fromisoformat(start_text)
    except Exception:
        return None
    return start + timedelta(days=(int(week_number) - 1) * 7)


def find_holiday_conflicts(calendar, start_d, end_d):
    conflicts = []
    for holiday in calendar.get("official_holidays", []):
        try:
            h_start = date.fromisoformat(holiday.get("start_date"))
            h_end = date.fromisoformat(holiday.get("end_date"))
        except Exception:
            continue
        if start_d <= h_end and end_d >= h_start:
            conflicts.append(holiday.get("name"))
    return conflicts


def decorate_item(calendar, item):
    ws = item.get("week_start")
    we = item.get("week_end")
    if not ws or not we:
        return item
    start_d = week_to_date(calendar, ws)
    end_d = week_to_date(calendar, we)
    if start_d and end_d:
        end_d = end_d + timedelta(days=6)
        item["week_start_date"] = start_d.isoformat()
        item["week_end_date"] = end_d.isoformat()
        item["holiday_conflicts"] = find_holiday_conflicts(calendar, start_d, end_d)
    return item


def wrap_html(title, body):
    return (
        "<!DOCTYPE html>\n<html lang='fr'><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>"
        "body{font-family:Arial,sans-serif;margin:24px;color:#111}"
        "table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #999;padding:6px;font-size:13px;text-align:left}"
        "h1{font-size:20px}h2{font-size:16px;margin-top:18px}"
        "@media print{body{margin:8mm}}"
        "</style></head><body>" + body + "</body></html>"
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "project": "Collegue AI",
        "message": "Offline-first planning API"
    }


@app.get("/")
def root_redirect():
    """Redirect root to PWA"""
    return RedirectResponse("/pwa/")


@app.get("/api/reference/curriculum/{level_code}")
def get_curriculum(level_code: str):
    data = get_curriculum_data()
    level_code = level_code.upper()
    level = data.get("didactic_programs_by_level", {}).get(level_code)
    if not level:
        raise HTTPException(status_code=404, detail=f"Level not found: {level_code}")
    return {
        "level_code": level_code,
        "metadata": data.get("curriculum_metadata", {}),
        "competency_framework": data.get("competency_framework", {}),
        "curriculum": level
    }


@app.get("/api/reference/calendar/{school_year}")
def get_calendar(school_year: str):
    return get_calendar_data()


@app.get("/api/reference/pedagogy")
def get_pedagogy():
    return get_pedagogy_data()


class AnnualPlanRequest(BaseModel):
    level_code: str
    school_year: str = "2026-2027"


@app.post("/api/planning/annual/generate")
def generate_annual_plan(request: AnnualPlanRequest):
    curriculum = get_curriculum_data()
    calendar = get_calendar_data()

    level_code = request.level_code.upper()
    level = curriculum.get("didactic_programs_by_level", {}).get(level_code)

    if not level:
        raise HTTPException(status_code=404, detail=f"Level not found: {level_code}")

    pacing = calendar.get("pacing_structure_weeks", {})
    semester_1_weeks = int(pacing.get("semester_1_weeks", 17))
    total_weeks = int(pacing.get("total_teaching_and_assessment_weeks", 34))

    items = []
    warnings = []
    week_cursor = 1
    total_planned_hours = 0

    for unit in level.get("units", []):
        for sub_module in unit.get("sub_modules", []):
            hours = int(sub_module.get("allocated_hours", 0))
            week_start = week_cursor
            week_end = week_cursor + hours - 1
            semester = 1 if week_start <= semester_1_weeks else 2

            item = {
                "item_id": f"AP-{level_code}-{request.school_year}-{sub_module.get('topic_id')}",
                "unit_id": unit.get("unit_id"),
                "unit_title": unit.get("title"),
                "sub_module_id": sub_module.get("topic_id"),
                "topic": sub_module.get("topic"),
                "competency_codes": sub_module.get("competency_codes", []),
                "official_hours": hours,
                "planned_hours": hours,
                "semester": semester,
                "week_start": week_start,
                "week_end": week_end,
                "notes": "",
                "status": "planned"
            }

            decorate_item(calendar, item)

            if item.get("holiday_conflicts"):
                warnings.append(
                    f"{sub_module.get('topic_id')}: chevauche {', '.join(item['holiday_conflicts'])}."
                )

            if week_end > total_weeks:
                warnings.append(
                    f"{sub_module.get('topic_id')}: semaine {week_end} au-delà des {total_weeks} semaines officielles."
                )

            items.append(item)
            total_planned_hours += hours
            week_cursor = week_end + 1

    official_total = int(level.get("total_hours", 0))

    if total_planned_hours != official_total:
        warnings.append(
            f"Volume planifié ({total_planned_hours}) différent du volume officiel ({official_total})."
        )

    plan = {
        "annual_plan_id": f"AP-{level_code}-{request.school_year}",
        "school_year": request.school_year,
        "level_code": level_code,
        "level_name": level.get("level_name"),
        "subject": curriculum.get("curriculum_metadata", {}).get("subject", "Informatique"),
        "total_official_hours": official_total,
        "total_planned_hours": total_planned_hours,
        "assessment_schedule": calendar.get("middle_school_assessment_schedule", {}),
        "status": "draft",
        "items": items,
        "warnings": warnings
    }

    save_json(ANNUAL_DIR / f"{plan['annual_plan_id']}.json", plan)
    return plan


@app.get("/api/planning/annual")
def list_annual_plans():
    plans = []
    for file_path in sorted(ANNUAL_DIR.glob("*.json")):
        try:
            plan = json.loads(file_path.read_text(encoding="utf-8"))
            plans.append({
                "annual_plan_id": plan.get("annual_plan_id"),
                "level_code": plan.get("level_code"),
                "school_year": plan.get("school_year"),
                "status": plan.get("status"),
                "total_planned_hours": plan.get("total_planned_hours")
            })
        except Exception:
            continue
    return {"plans": plans}


@app.get("/api/planning/annual/{annual_plan_id}")
def get_annual_plan(annual_plan_id: str):
    return load_json(ANNUAL_DIR / f"{annual_plan_id}.json")


@app.put("/api/planning/annual/{annual_plan_id}")
def update_annual_plan(annual_plan_id: str, payload: dict):
    calendar = get_calendar_data()
    total_weeks = int(
        calendar.get("pacing_structure_weeks", {}).get("total_teaching_and_assessment_weeks", 34)
    )

    items = payload.get("items", [])
    warnings = []
    total = 0

    for item in items:
        try:
            total += int(item.get("planned_hours", 0))
        except Exception:
            pass

        decorate_item(calendar, item)

        if item.get("holiday_conflicts"):
            warnings.append(
                f"{item.get('sub_module_id')}: chevauche {', '.join(item['holiday_conflicts'])}."
            )

        we = item.get("week_end") or 0
        if int(we) > total_weeks:
            warnings.append(
                f"{item.get('sub_module_id')}: semaine {we} au-delà des {total_weeks} semaines officielles."
            )

    official = int(payload.get("total_official_hours", 0))
    payload["total_planned_hours"] = total

    if official and total != official:
        warnings.append(
            f"Volume planifié ({total}) différent du volume officiel ({official})."
        )

    payload["warnings"] = warnings

    save_json(ANNUAL_DIR / f"{annual_plan_id}.json", payload)
    return payload


@app.get("/api/export/annual/{annual_plan_id}")
def export_annual(annual_plan_id: str):
    plan = load_json(ANNUAL_DIR / f"{annual_plan_id}.json")

    rows = ""
    for item in plan.get("items", []):
        conflicts = ", ".join(item.get("holiday_conflicts", [])) or "-"
        rows += (
            "<tr>"
            f"<td>{item.get('unit_id')}</td>"
            f"<td>{item.get('topic')}</td>"
            f"<td>{', '.join(item.get('competency_codes', []))}</td>"
            f"<td>{item.get('planned_hours')}</td>"
            f"<td>S{item.get('semester')}</td>"
            f"<td>{item.get('week_start_date', '')} → {item.get('week_end_date', '')}</td>"
            f"<td>{conflicts}</td>"
            "</tr>"
        )

    body = (
        f"<h1>Planification annuelle — {plan.get('level_name')}</h1>"
        f"<p><strong>Année scolaire :</strong> {plan.get('school_year')} | "
        f"<strong>Matière :</strong> {plan.get('subject')} | "
        f"<strong>Volume officiel :</strong> {plan.get('total_official_hours')} h | "
        f"<strong>Volume planifié :</strong> {plan.get('total_planned_hours')} h</p>"
        "<table><tr><th>Unité</th><th>Sous-module</th><th>Comp.</th><th>Heures</th>"
        "<th>Sem.</th><th>Période</th><th>Chevauchements</th></tr>"
        + rows +
        "</table>"
    )

    return {"html": wrap_html(plan.get("annual_plan_id", "plan"), body)}


class UnitPlanRequest(BaseModel):
    annual_plan_id: str
    unit_id: str


@app.post("/api/planning/unit/generate")
def generate_unit_plan(request: UnitPlanRequest):
    annual_plan = load_json(ANNUAL_DIR / f"{request.annual_plan_id}.json")
    level_code = annual_plan.get("level_code")
    school_year = annual_plan.get("school_year")

    curriculum = get_curriculum_data()
    level = curriculum.get("didactic_programs_by_level", {}).get(level_code)

    if not level:
        raise HTTPException(status_code=404, detail=f"Level not found: {level_code}")

    unit = None
    for u in level.get("units", []):
        if u.get("unit_id") == request.unit_id:
            unit = u
            break

    if not unit:
        raise HTTPException(status_code=404, detail=f"Unit not found: {request.unit_id}")

    items = [i for i in annual_plan.get("items", []) if i.get("unit_id") == request.unit_id]

    competency_codes = []
    for sm in unit.get("sub_modules", []):
        for code in sm.get("competency_codes", []):
            if code not in competency_codes:
                competency_codes.append(code)

    competency_details = []
    for code in competency_codes:
        comp = find_competency(curriculum, code)
        if comp:
            competency_details.append({
                "code": comp["code"],
                "domain": comp["domain"],
                "statement": comp["statement"]
            })

    pedagogy = get_pedagogy_data()
    framework = pedagogy.get("pedagogical_planning_framework", {})
    moments = framework.get("three_moments_of_learning", [])
    tips = pedagogy.get("predecessor_teacher_tips", {})

    proposed_sequences = []
    for sm in unit.get("sub_modules", []):
        proposed_sequences.append({
            "sub_module_id": sm.get("topic_id"),
            "sequence_title": sm.get("topic"),
            "competency_codes": sm.get("competency_codes", []),
            "duration_hours": sm.get("allocated_hours", 0)
        })

    unit_plan = {
        "unit_plan_id": f"UP-{level_code}-{unit.get('unit_id')}-{school_year}",
        "annual_plan_id": request.annual_plan_id,
        "level_code": level_code,
        "school_year": school_year,
        "unit_id": unit.get("unit_id"),
        "unit_title": unit.get("title"),
        "targeted_competencies": competency_codes,
        "competency_details": competency_details,
        "total_official_hours": sum(
            sm.get("allocated_hours", 0) for sm in unit.get("sub_modules", [])
        ),
        "annual_items": items,
        "proposed_sequences": proposed_sequences,
        "planning_moments": moments,
        "pedagogical_suggestions": suggestions_for_codes(competency_codes),
        "laboratory_tips": tips.get("laboratory_management", []),
        "didactic_best_practices": tips.get("didactic_best_practices", []),
        "teacher_notes": "",
        "status": "draft"
    }

    save_json(UNIT_DIR / f"{unit_plan['unit_plan_id']}.json", unit_plan)
    return unit_plan


@app.get("/api/planning/unit")
def list_unit_plans():
    plans = []
    for file_path in sorted(UNIT_DIR.glob("*.json")):
        try:
            plan = json.loads(file_path.read_text(encoding="utf-8"))
            plans.append({
                "unit_plan_id": plan.get("unit_plan_id"),
                "level_code": plan.get("level_code"),
                "unit_id": plan.get("unit_id"),
                "unit_title": plan.get("unit_title"),
                "status": plan.get("status")
            })
        except Exception:
            continue
    return {"plans": plans}


@app.get("/api/planning/unit/{unit_plan_id}")
def get_unit_plan(unit_plan_id: str):
    return load_json(UNIT_DIR / f"{unit_plan_id}.json")


@app.put("/api/planning/unit/{unit_plan_id}")
def update_unit_plan(unit_plan_id: str, payload: dict):
    save_json(UNIT_DIR / f"{unit_plan_id}.json", payload)
    return {"status": "saved", "unit_plan_id": unit_plan_id}


class SequencePlanRequest(BaseModel):
    unit_plan_id: str
    sub_module_id: str
    fiche_type: str = "fiche_ressources"


@app.post("/api/planning/sequence/generate")
def generate_sequence_plan(request: SequencePlanRequest):
    if request.fiche_type not in ("fiche_ressources", "fiche_integration", "fiche_evaluation"):
        raise HTTPException(
            status_code=400,
            detail="fiche_type must be fiche_ressources, fiche_integration or fiche_evaluation"
        )

    unit_plan = load_json(UNIT_DIR / f"{request.unit_plan_id}.json")
    level_code = unit_plan.get("level_code")

    curriculum = get_curriculum_data()
    level = curriculum.get("didactic_programs_by_level", {}).get(level_code, {})

    sub_module = None
    for u in level.get("units", []):
        for sm in u.get("sub_modules", []):
            if sm.get("topic_id") == request.sub_module_id:
                sub_module = sm
                break

    if not sub_module:
        raise HTTPException(status_code=404, detail=f"Sub-module not found: {request.sub_module_id}")

    codes = sub_module.get("competency_codes", [])
    resources = merge_resources(codes, curriculum)
    suggestions = suggestions_for_codes(codes)

    pedagogy = get_pedagogy_data()
    framework = pedagogy.get("pedagogical_planning_framework", {})
    templates = framework.get("three_mandatory_preparation_files", {})
    evaluation_norms = pedagogy.get("evaluation_rules_and_norms", {})
    tips = pedagogy.get("predecessor_teacher_tips", {})

    suffix = {
        "fiche_ressources": "RES",
        "fiche_integration": "INT",
        "fiche_evaluation": "EVA"
    }[request.fiche_type]

    fiche = {
        "sequence_plan_id": f"SEQ-{request.sub_module_id}-{suffix}",
        "unit_plan_id": request.unit_plan_id,
        "level_code": level_code,
        "unit_id": unit_plan.get("unit_id"),
        "sub_module_id": sub_module.get("topic_id"),
        "sequence_title": sub_module.get("topic"),
        "fiche_type": request.fiche_type,
        "competency_codes": codes,
        "duration_hours": sub_module.get("allocated_hours", 0),
        "template_structure": templates.get(request.fiche_type, {}).get("template_structure", []),
        "status": "draft"
    }

    if request.fiche_type == "fiche_ressources":
        fiche.update({
            "resources": resources,
            "prerequisites": [],
            "material_and_logistics": [
                "Salle informatique",
                "Ordinateurs en nombre suffisant (travail en binômes)",
                "Vidéoprojecteur si disponible",
                "Cahier de cours pour la trace écrite"
            ],
            "deroulement": {
                "situation_declenchante": "",
                "activite_pratique": "",
                "synthese_trace_ecrite": ""
            },
            "differentiation": [
                "Binômes homogènes ou semi-hétérogènes",
                "Rotation stricte du temps machine (règle des 25 min par élève)"
            ],
            "methodological_suggestions": suggestions,
            "didactic_best_practices": tips.get("didactic_best_practices", [])
        })

    if request.fiche_type == "fiche_integration":
        fiche.update({
            "situation_probleme": "",
            "consignes_operationnelles": [],
            "ressources_a_mobiliser": resources.get("savoir_faire", []),
            "group_organization": "Travail en binômes",
            "livrable_attendu": "",
            "methodological_suggestions": suggestions
        })

    if request.fiche_type == "fiche_evaluation":
        fiche.update({
            "competency_to_evaluate": codes,
            "evaluation_type": "formative",
            "duration_minutes": 20,
            "evaluation_situation": "",
            "criteria": {
                "criteres_minimaux": [],
                "criteres_de_perfectionnement": []
            },
            "observable_indicators": [],
            "evaluation_norms": {
                "formative": evaluation_norms.get("formative_evaluation", {}),
                "summative": evaluation_norms.get("summative_evaluation", {}),
                "criteria_design_rules": evaluation_norms.get("criteria_design_rules", [])
            }
        })

    save_json(SEQUENCE_DIR / f"{fiche['sequence_plan_id']}.json", fiche)
    return fiche


@app.get("/api/planning/sequence")
def list_sequence_plans():
    plans = []
    for file_path in sorted(SEQUENCE_DIR.glob("*.json")):
        try:
            plan = json.loads(file_path.read_text(encoding="utf-8"))
            plans.append({
                "sequence_plan_id": plan.get("sequence_plan_id"),
                "fiche_type": plan.get("fiche_type"),
                "sequence_title": plan.get("sequence_title"),
                "status": plan.get("status")
            })
        except Exception:
            continue
    return {"plans": plans}


@app.get("/api/planning/sequence/{sequence_plan_id}")
def get_sequence_plan(sequence_plan_id: str):
    return load_json(SEQUENCE_DIR / f"{sequence_plan_id}.json")


@app.put("/api/planning/sequence/{sequence_plan_id}")
def update_sequence_plan(sequence_plan_id: str, payload: dict):
    save_json(SEQUENCE_DIR / f"{sequence_plan_id}.json", payload)
    return {"status": "saved", "sequence_plan_id": sequence_plan_id}


@app.get("/api/export/sequence/{sequence_plan_id}")
def export_sequence(sequence_plan_id: str):
    fiche = load_json(SEQUENCE_DIR / f"{sequence_plan_id}.json")
    ft = fiche.get("fiche_type")

    body = (
        f"<h1>{fiche.get('sequence_title')}</h1>"
        f"<p><strong>Type :</strong> {ft} | "
        f"<strong>Compétences :</strong> {', '.join(fiche.get('competency_codes', []))} | "
        f"<strong>Durée :</strong> {fiche.get('duration_hours')} h</p>"
    )

    if ft == "fiche_ressources":
        res = fiche.get("resources", {})
        body += "<h2>Ressources</h2>"
        body += "<h3>Savoirs</h3><ul>" + "".join(
            f"<li>{x}</li>" for x in res.get("savoir", [])) + "</ul>"
        body += "<h3>Savoir-faire</h3><ul>" + "".join(
            f"<li>{x}</li>" for x in res.get("savoir_faire", [])) + "</ul>"
        body += "<h3>Savoir-être</h3><ul>" + "".join(
            f"<li>{x}</li>" for x in res.get("savoir_etre", [])) + "</ul>"
        body += "<h3>Prérequis</h3><ul>" + "".join(
            f"<li>{x}</li>" for x in fiche.get("prerequisites", [])) + "</ul>"
        der = fiche.get("deroulement", {})
        body += (
            "<h2>Déroulement</h2>"
            f"<p><strong>Situation déclenchante :</strong> {der.get('situation_declenchante', '')}</p>"
            f"<p><strong>Activité pratique :</strong> {der.get('activite_pratique', '')}</p>"
            f"<p><strong>Synthèse / trace écrite :</strong> {der.get('synthese_trace_ecrite', '')}</p>"
        )

    elif ft == "fiche_integration":
        body += (
            "<h2>Situation-problème</h2>"
            f"<p>{fiche.get('situation_probleme', '')}</p>"
            "<h3>Consignes opérationnelles</h3><ul>" + "".join(
                f"<li>{x}</li>" for x in fiche.get("consignes_operationnelles", [])) + "</ul>"
            "<h3>Ressources à mobiliser</h3><ul>" + "".join(
                f"<li>{x}</li>" for x in fiche.get("ressources_a_mobiliser", [])) + "</ul>"
            f"<p><strong>Organisation :</strong> {fiche.get('group_organization', '')} | "
            f"<strong>Livrable attendu :</strong> {fiche.get('livrable_attendu', '')}</p>"
        )

    else:
        crit = fiche.get("criteria", {})
        body += (
            "<h2>Situation d'évaluation</h2>"
            f"<p>{fiche.get('evaluation_situation', '')}</p>"
            f"<p><strong>Type :</strong> {fiche.get('evaluation_type', '')} | "
            f"<strong>Durée :</strong> {fiche.get('duration_minutes', '')} min</p>"
            "<h3>Critères minimaux</h3><ul>" + "".join(
                f"<li>{x}</li>" for x in crit.get("criteres_minimaux", [])) + "</ul>"
            "<h3>Critères de perfectionnement</h3><ul>" + "".join(
                f"<li>{x}</li>" for x in crit.get("criteres_de_perfectionnement", [])) + "</ul>"
            "<h3>Indicateurs observables</h3><ul>" + "".join(
                f"<li>{x}</li>" for x in fiche.get("observable_indicators", [])) + "</ul>"
        )

    return {"html": wrap_html(sequence_plan_id, body)}


@app.get("/api/plans/recent")
def get_recent_plans():
    """Return the 5 most recent saved plans (annual/unit/sequence) from data/plans/"""
    recent = []
    
    # Collect annual plans
    for file_path in ANNUAL_DIR.glob("*.json"):
        try:
            plan = json.loads(file_path.read_text(encoding="utf-8"))
            recent.append({
                "type": "annual",
                "level": plan.get("level_code"),
                "unit": None,
                "title": plan.get("level_name"),
                "saved_at": file_path.stat().st_mtime
            })
        except Exception:
            continue
    
    # Collect unit plans
    for file_path in UNIT_DIR.glob("*.json"):
        try:
            plan = json.loads(file_path.read_text(encoding="utf-8"))
            recent.append({
                "type": "unit",
                "level": plan.get("level_code"),
                "unit": plan.get("unit_id"),
                "title": plan.get("unit_title"),
                "saved_at": file_path.stat().st_mtime
            })
        except Exception:
            continue
    
    # Collect sequence plans
    for file_path in SEQUENCE_DIR.glob("*.json"):
        try:
            plan = json.loads(file_path.read_text(encoding="utf-8"))
            recent.append({
                "type": "sequence",
                "level": plan.get("level_code"),
                "unit": plan.get("sub_module_id"),
                "title": plan.get("sequence_title"),
                "saved_at": file_path.stat().st_mtime
            })
        except Exception:
            continue
    
    # Sort by saved_at descending and take top 5
    recent.sort(key=lambda x: x["saved_at"], reverse=True)
    recent = recent[:5]
    
    # Convert timestamps to ISO format
    for plan in recent:
        plan["saved_at"] = date.fromtimestamp(plan["saved_at"]).isoformat()
    
    return recent
