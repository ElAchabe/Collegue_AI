import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

import requests
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
REFERENCE_DIR = BASE_DIR / "data" / "reference"
SETTINGS_PATH = REFERENCE_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "ai_enabled": False,
    "ai_base_url": "http://127.0.0.1:11434",
    "ai_model": "collegue-qwen:latest",
}

SYSTEM_PROMPT = (
    "Tu es Collegue AI, le collègue numérique d'un enseignant d'informatique "
    "du secondaire collégial marocain (APC, pédagogie de l'intégration). "
    "RÈGLES STRICTES : 1) français simple ; 2) 120 mots maximum ; 3) puces courtes ; "
    "4) contexte réel : salle informatique, séances de 1 h, élèves de 12-15 ans ; "
    "5) ne répète jamais une phrase ; 6) suis le MODELE.\n"
    "MODELE (bonne réponse, situation déclenchante) :\n"
    "• Contexte : le professeur montre un ordinateur éteint et demande « que voit-on ? ».\n"
    "• Déclencheur : les élèves citent écran, clavier, souris, unité centrale.\n"
    "• Problème : « comment ces éléments travaillent-ils ensemble ? ».\n"
    "• Lien : annonce de la compétence C0.\n"
    "Réponds maintenant dans ce style."
)

SITUATION_FICHES = {
    "C0_C31": {
        "contexte": "le professeur montre l'ordinateur de la salle et demande « de quoi est composée cette machine ? »",
        "declencheur": "les élèves citent écran, clavier, souris, unité centrale",
        "probleme": "« comment ces éléments travaillent-ils ensemble pour afficher ce que vous voyez ? »",
        "lien": "annonce de la compétence C0 (technologies de base du système informatique)",
    },
    "C11_C12": {
        "contexte": "le professeur projette une affiche finie (titre + image + texte) sans montrer les étapes",
        "declencheur": "les élèves décrivent ce qu'ils voient et devinent les outils utilisés",
        "probleme": "« comment produire la même affiche vous-mêmes en 30 minutes ? »",
        "lien": "annonce de la compétence C11 (produire un document multimédia)",
    },
    "C13": {
        "contexte": "le professeur demande de reproduire à l'écran un dessin géométrique simple, sans donner la méthode",
        "declencheur": "les élèves essaient, se trompent, et expriment le besoin de commandes précises",
        "probleme": "« quelles commandes donnent exactement ce résultat ? »",
        "lien": "annonce de la compétence C13 (initiation à la programmation)",
    },
    "C21_C22_C23": {
        "contexte": "une question d'une autre discipline (ex. « où naît le fleuve Nil ? ») est posée sans manuel",
        "declencheur": "les élèves proposent des sources, dont Internet",
        "probleme": "« comment trouver une information fiable, et comment la vérifier ? »",
        "lien": "annonce des compétences C21/C22 (recherche d'information)",
    },
    "C32_C33": {
        "contexte": "le professeur lit un message étrange reçu par un ancien élève (canular)",
        "declencheur": "les élèves discutent : vrai ou faux ? faut-il transférer ?",
        "probleme": "« quelles règles respecter pour communiquer sans risque ? »",
        "lien": "annonce de la compétence C32/C33 (messagerie et nétiquette)",
    },
}

DIFFERENCIATION = [
    "Binômes homogènes pour les TP dirigés ; semi-hétérogènes pour les projets.",
    "Rotation stricte clavier/souris : 25 min par élève.",
    "Fiche d'aide pas-à-pas pour les élèves en difficulté ; défi supplémentaire pour les rapides.",
    "Un élève « tuteur » par rangée pour les pannes simples.",
]

HELP_TEXT = (
    "Je réponds sur : situation déclenchante, plan de séance, évaluation formative, différenciation, "
    "compétences (ex. « C11 »), échéances, vacances, Massar, programme, laboratoire. "
    "Précisez votre besoin, ex. « Propose une situation déclenchante pour l'unité U2 (1AC) »."
)


def clean_history_text(text):
    text = str(text)
    if text.startswith("**["):
        idx = text.find("]**")
        if idx != -1:
            text = text[idx + 3:]
    for marker in ("QUESTION :", "QUESTION:", "BROUILLON OFFICIEL", "Consigne :"):
        text = text.split(marker)[0]
    return text.strip()


def plan_seance_curated(ui, level_code, unit_id):
    if not ui:
        return (
            "Pour générer un plan de séance, sélectionnez un niveau et une unité "
            "(ex. 1AC + U1), ou précisez : « plan de séance pour l'unité U2 (2AC) »."
        )
    comps = ", ".join(ui.get("competency_codes", [])) or "compétence visée"
    topics = " ; ".join(ui.get("sub_modules", [])) or ui.get("title", "")
    fam = family_of(ui["competency_codes"][0]) if ui.get("competency_codes") else "C11_C12"
    f = SITUATION_FICHES.get(fam or "C11_C12", SITUATION_FICHES["C11_C12"])
    return (
        f"Plan de séance (1 h) — {level_code}, unité {unit_id} : {ui['title']} ({comps}).\n"
        f"• En-tête : sujets : {topics}. Matériel : salle informatique, vidéoprojecteur. Prérequis : séance précédente.\n"
        f"• Moment 1 — Déclenchement (5 min) : {f['contexte']}. Déclencheur : {f['declencheur']}. Problème : {f['probleme']}\n"
        "• Moment 2 — Apprentissages (35 min) : cycle démonstratif : Montrer (10 min) ; "
        "Faire faire en binômes avec rotation clavier/souris (20 min) ; Faire dire / verbalisation (5 min).\n"
        "• Moment 3 — Synthèse & régulation (10 min) : trace écrite courte institutionnalisée ; "
        "annonce de l'évaluation formative (20 min max) ; remédiation ciblée.\n"
        "• Différenciation : fiche pas-à-pas pour les élèves lents ; défi pour les rapides ; élève tuteur par rangée.\n"
        "• Évaluation : formative en fin d'unité (au moins 2 par semestre, 20 min max) ; critères minimaux vs perfectionnement."
    )
RAG_INDEX_PATH = BASE_DIR / "data" / "ai" / "rag_index.json"
_rag_cache = None

def rag_retrieve(q, top_k=3):
    global _rag_cache
    if _rag_cache is None:
        if not RAG_INDEX_PATH.exists():
            return []
        _rag_cache = json.loads(RAG_INDEX_PATH.read_text(encoding="utf-8"))
    toks = [t for t in re.findall(r"[a-zàâçéèêëîïôûùüÿñæœ0-9]+", q.lower()) if len(t) > 2]
    qv = Counter(toks)
    best = []
    for doc in _rag_cache:
        s = sum(qv[t] * w for t, w in doc["vec"].items() if t in qv)
        if s > 0:
            best.append((s, doc))
    best.sort(key=lambda x: -x[0])
    return [d["text"] for _, d in best[:top_k]]



def sanitize_reply(text):
    for marker in ("<|im_end|>", "<|im_start|>", "\nuser:", "\nQ :", "QUESTION", "[🟢", "[⚪", "**["):
        text = text.split(marker)[0]
    return text.strip()
    

def family_of(code):
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


def load(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_settings():
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(s):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/api/settings")
def api_settings():
    return get_settings()


@router.put("/api/settings")
def api_save_settings(payload: dict):
    s = get_settings()
    s.update(payload)
    save_settings(s)
    return s


@router.get("/api/ai/status")
def ai_status():
    s = get_settings()
    available = False
    if s.get("ai_enabled"):
        try:
            r = requests.get(f"{s.get('ai_base_url')}/api/tags", timeout=2)
            available = r.status_code == 200
        except Exception:
            available = False
    return {
        "enabled": bool(s.get("ai_enabled", False)),
        "available": available,
        "model": s.get("ai_model"),
        "base_url": s.get("ai_base_url", ""),
    }


@router.get("/api/ai/models")
def ai_models():
    s = get_settings()
    try:
        r = requests.get(f"{s.get('ai_base_url')}/api/tags", timeout=3)
        models = [m.get("name") for m in r.json().get("models", [])]
    except Exception:
        models = []
    return {"models": models, "selected": s.get("ai_model", "")}


def unit_info(curriculum, level_code, unit_id):
    lv = curriculum.get("didactic_programs_by_level", {}).get(level_code, {})
    for u in lv.get("units", []):
        if u.get("unit_id") == unit_id:
            codes = []
            for sm in u.get("sub_modules", []):
                for c in sm.get("competency_codes", []):
                    if c not in codes:
                        codes.append(c)
            return {
                "title": u.get("title"),
                "competency_codes": codes,
                "sub_modules": [s.get("topic") for s in u.get("sub_modules", [])],
            }
    return None


def build_official_context(level_code, unit_id):
    parts = []
    curriculum = load(REFERENCE_DIR / "curriculum_clean.json") or {}
    pedagogy = load(REFERENCE_DIR / "pedagogy_clean.json") or {}
    lv = curriculum.get("didactic_programs_by_level", {}).get(level_code, {})
    if lv:
        parts.append(
            f"Niveau : {lv.get('level_name')} ; volume total : {lv.get('total_hours')} h ; "
            f"compétences visées : {', '.join(lv.get('targeted_competencies', []))}."
        )
        ui = unit_info(curriculum, level_code, unit_id) if unit_id else None
        if ui:
            parts.append(
                f"Unité {unit_id} : {ui['title']} ; sous-modules : {' ; '.join(ui['sub_modules'])} ; "
                f"compétences : {', '.join(ui['competency_codes'])}."
            )
    norms = pedagogy.get("evaluation_rules_and_norms", {})
    f = norms.get("formative_evaluation", {})
    s = norms.get("summative_evaluation", {})
    if f:
        parts.append(f"Évaluation formative : {f.get('frequency')} ; {f.get('duration')}.")
    if s:
        parts.append(f"Évaluation sommative : {s.get('frequency')} ; {s.get('duration')}.")
    return "\n".join(parts)


def eval_formative_curated(ui):
    comps = ", ".join(ui.get("competency_codes", [])) if ui else "compétence visée"
    title = ui.get("title", "l'unité sélectionnée") if ui else "l'unité sélectionnée"
    return (
        f"Évaluation formative (20 min) — {title} ({comps}) :\n"
        "• Ex. 1 (7 min) : restitution guidée d'un savoir-faire vu en TP.\n"
        "• Ex. 2 (10 min) : mini-tâche sur fichier court, consignes affichées.\n"
        "• Auto-correction (3 min) : grille projetée, l'élève coche ses réussites.\n"
        "Critères minimaux : résultat conforme, démarche partiellement autonome.\n"
        "Perfectionnement : autonomie complète, soin, rapidité.\n"
        "Norme : ≥ 2 formatives/semestre, 20 min max ; l'erreur = départ de la remédiation."
    )


def next_events(cal, today, n=6):
    events = []

    for h in cal.get("official_holidays", []):
        try:
            events.append((h.get("name", ""), date.fromisoformat(h.get("start_date")), "🌴"))
        except Exception:
            pass

    for w_id, w in cal.get("assessment_windows", {}).items():
        try:
            label = {
                "diagnostic": "Évaluation diagnostique",
                "S1_CC": "Contrôle continu — Semestre 1",
                "S2_CC": "Contrôle continu — Semestre 2",
            }.get(w_id, w_id)
            events.append((label, date.fromisoformat(w.get("start")), "⚠️"))
        except Exception:
            pass

    for sem_key, sem in cal.get("middle_school_assessment_schedule", {}).items():
        for key, value in sem.items():
            ds = re.findall(r"\d{4}-\d{2}-\d{2}", str(value))
            if ds:
                events.append((key, date.fromisoformat(ds[0]), "📌"))

    for ev in cal.get("extracurricular_and_competitions", []):
        try:
            events.append((ev.get("name", ""), date.fromisoformat(ev.get("window", {}).get("start")), "🏆"))
        except Exception:
            pass

    events = [e for e in events if e[1] >= today]
    events.sort(key=lambda e: e[1])
    return [f"{e[2]} {e[0]} — {e[1].isoformat()} (J-{(e[1] - today).days})" for e in events[:n]]


def curated_answer(q, level_code, unit_id):
    q_low = q.lower()
    today = date.today()
    cal = load(REFERENCE_DIR / "calendar_clean.json") or {}
    curriculum = load(REFERENCE_DIR / "curriculum_clean.json") or {}
    pedagogy = load(REFERENCE_DIR / "pedagogy_clean.json") or {}
    ui = unit_info(curriculum, level_code, unit_id) if (level_code and unit_id) else None

    code = None
    m = re.search(r"c\s?(\d{1,2})", q_low)
    if m:
        code = "C" + m.group(1)

    if "déclenchante" in q_low or "declenchante" in q_low or "introduction" in q_low:
        fam = None
        if code:
            fam = family_of(code)
        elif ui and ui["competency_codes"]:
            fam = family_of(ui["competency_codes"][0])
        f = SITUATION_FICHES.get(fam or "C11_C12", SITUATION_FICHES["C11_C12"])
        target = f" (unité {unit_id} — {ui['title']})" if ui else ""
        return (
            f"Situation déclenchante{target} :\n"
            f"• Contexte : {f['contexte']}.\n"
            f"• Déclencheur : {f['declencheur']}.\n"
            f"• Problème : {f['probleme']}\n"
            f"• Lien : {f['lien']}.\n"
            "Durée : 5 min, en début de séance 1."
        )

    if ("formative" in q_low or "rédige" in q_low or "redige" in q_low or "prépare" in q_low or "prepare" in q_low) and (
        "évaluation" in q_low or "evaluation" in q_low or "contrôle" in q_low or "controle" in q_low
    ):
        return eval_formative_curated(ui)

    if any(w in q_low for w in ["planification", "plan de séance", "plan de seance", "planning", "planing", "déroulement", "deroulement", "fiche pédagogique", "fiche pedagogique", "préparer la séance", "preparer la seance"]):
        return plan_seance_curated(ui, level_code, unit_id)

    

    if "différenciation" in q_low or "differenciation" in q_low or "binôme" in q_low or "binome" in q_low:
        return "Différenciation & gestion des binômes :\n" + "\n".join("• " + d for d in DIFFERENCIATION)

    if code:
        comp = None
        for domain in curriculum.get("competency_framework", {}).get("domains_of_action", []):
            for c in domain.get("competencies", []):
                if c.get("code") == code:
                    comp = (domain, c)
        if comp:
            domain, c = comp
            res = c.get("resources", {})
            return (
                f"{code} ({domain.get('name')}) : {c.get('statement')}\n"
                f"Savoirs : {', '.join(res.get('savoir', []))}.\n"
                f"Savoir-faire : {', '.join(res.get('savoir_faire', []))}.\n"
                f"Savoir-être : {', '.join(res.get('savoir_etre', []))}."
            )
        return f"Compétence {code} introuvable dans le référentiel officiel."

    if "échéance" in q_low or "echeance" in q_low or "prochaine" in q_low or "prochain" in q_low or "vacance" in q_low:
        return "Prochaines échéances officielles :\n" + "\n".join("• " + e for e in next_events(cal, today))

    if any(w in q_low for w in ["massar", "saisie", "bulletin", "conseil"]):
        s1 = cal.get("middle_school_assessment_schedule", {}).get("semester_1", {})
        s2 = cal.get("middle_school_assessment_schedule", {}).get("semester_2", {})
        return (
            f"Semestre 1 : saisie Massar avant le {s1.get('massar_grades_deadline')} ; conseils les {s1.get('class_councils')} ; bulletins le {s1.get('report_cards_distribution')}.\n"
            f"Semestre 2 : saisie CC avant le {s2.get('massar_grades_deadline_cc')} ; conseils et orientation du {s2.get('class_and_orientation_councils')} ; résultats le {s2.get('final_results_distribution')}."
        )

    if "semaine" in q_low:
        start_txt = cal.get("framework_milestones", {}).get("mandatory_class_start", "")
        if start_txt:
            start = date.fromisoformat(start_txt)
            if today >= start:
                return f"Nous sommes dans la semaine S{(today - start).days // 7 + 1} de l'année scolaire 2026-2027."
        return "Les cours démarrent obligatoirement le 2026-09-07."

    if any(w in q_low for w in ["unité", "unite", "programme", "séquence", "sequence", "volume", "heure"]):
        lv = curriculum.get("didactic_programs_by_level", {}).get(level_code, {})
        if lv:
            lines = [
                f"{u.get('unit_id')} — {u.get('title')} : "
                + ", ".join(f"{sm.get('topic')} ({sm.get('allocated_hours')} h)" for sm in u.get("sub_modules", []))
                for u in lv.get("units", [])
            ]
            return f"Programme {lv.get('level_name')} ({lv.get('total_hours')} h) :\n" + "\n".join("• " + l for l in lines)
        return "Précisez un niveau (1AC, 2AC, 3AC) pour afficher le programme."

    if any(w in q_low for w in ["laboratoire", "sécurité", "securite"]):
        tips = pedagogy.get("predecessor_teacher_tips", {}).get("laboratory_management", [])
        return "Gestion du laboratoire :\n" + "\n".join("• " + t for t in tips)

    if any(w in q_low for w in ["conseil", "suggestion", "méthode", "methode", "approche"]):
        tips = pedagogy.get("predecessor_teacher_tips", {}).get("didactic_best_practices", [])
        return "Bonnes pratiques officielles :\n" + "\n".join("• " + t for t in tips)

    return HELP_TEXT


def guardrail_ok(text):
    if not text:
        return False
    if len(text) > 1600:
        return False
    words = text.split()
    if len(words) > 260:
        return False
    if len(words) > 8:
        grams = Counter(tuple(words[i:i + 4]) for i in range(len(words) - 4))
        if max(grams.values()) > 3:
            return False
    return True


class ChatRequest(BaseModel):
    message: str
    level: str = ""
    unit: str = ""
    history: list = []
    model: str = ""


@router.post("/api/ai/chat")
def ai_chat(req: ChatRequest):
    s = get_settings()
    curated = curated_answer(req.message, req.level, req.unit)

    # Unrecognized intent -> serve offline directly, never call the LLM
    if curated == HELP_TEXT:
        return {"source": "offline", "reply": curated}

    if s.get("ai_enabled"):
        context = build_official_context(req.level, req.unit)
        rag = rag_retrieve(req.message)
        if rag:
            context += "\nEXTRAITS OFFICIELS PERTINENTS :\n" + "\n".join("- " + r for r in rag)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nCONTEXTE OFFICIEL :\n" + context},
        ]
        for h in req.history[-4:]:
            content = clean_history_text(h.get("content", ""))[:800]
            if content:
                messages.append({"role": h.get("role", "user"), "content": content})

        messages.append({
            "role": "user",
            "content": (
                "BROUILLON OFFICIEL À RESPECTER :\n" + curated + "\n\nQUESTION : " + req.message +
                "\n\nConsigne : reformule TRÈS légèrement le brouillon (change 2-3 mots maximum), "
                "garde TOUS les mots-clés, durées, dates et la structure. "
                "Si la question sort du brouillon, réponds en 3 puces max depuis le CONTEXTE OFFICIEL."
            ),
        })

        try:
            r = requests.post(
                f"{s.get('ai_base_url')}/api/chat",
                json={
                    "model": req.model or s.get("ai_model"),
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 300,
                        "repeat_penalty": 1.25,
                        "top_p": 0.9,
                    },
                },
                timeout=120,
            )
            if r.status_code == 200:
                reply = sanitize_reply(r.json().get("message", {}).get("content", ""))
                if guardrail_ok(reply):
                    return {"source": "ollama", "reply": reply}
        except Exception:
            pass

    return {"source": "offline", "reply": curated}
