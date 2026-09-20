import json
import random
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REF = BASE / "data" / "reference"
OUT = BASE / "data" / "ai"
OUT.mkdir(parents=True, exist_ok=True)

cur = json.loads((REF / "curriculum_clean.json").read_text(encoding="utf-8"))
cal = json.loads((REF / "calendar_clean.json").read_text(encoding="utf-8"))
ped = json.loads((REF / "pedagogy_clean.json").read_text(encoding="utf-8"))

COMPS = {}
for d in cur.get("competency_framework", {}).get("domains_of_action", []):
    for c in d.get("competencies", []):
        COMPS[c.get("code")] = c

def fam(code):
    if code in ("C0", "C31"): return "C0_C31"
    if code in ("C11", "C12"): return "C11_C12"
    if code == "C13": return "C13"
    if code in ("C21", "C22", "C23"): return "C21_C22_C23"
    if code in ("C32", "C33"): return "C32_C33"
    return "C11_C12"

SIT = {
 "C0_C31": ("le professeur montre l'ordinateur de la salle et demande « de quoi est composée cette machine ? »",
            "les élèves citent écran, clavier, souris, unité centrale",
            "« comment ces éléments travaillent-ils ensemble pour afficher ce que vous voyez ? »"),
 "C11_C12": ("le professeur projette une affiche finie (titre + image + texte) sans montrer les étapes",
             "les élèves décrivent ce qu'ils voient et devinent les outils utilisés",
             "« comment produire la même affiche vous-mêmes en 30 minutes ? »"),
 "C13": ("le professeur demande de reproduire un dessin géométrique simple à l'écran, sans donner la méthode",
         "les élèves essaient, se trompent, et expriment le besoin de commandes précises",
         "« quelles commandes donnent exactement ce résultat ? »"),
 "C21_C22_C23": ("une question d'une autre discipline (ex. « où naît le fleuve Nil ? ») est posée sans manuel",
                "les élèves proposent des sources, dont Internet",
                "« comment trouver une information fiable, et comment la vérifier ? »"),
 "C32_C33": ("le professeur lit un message étrange reçu par un ancien élève (canular)",
             "les élèves discutent : vrai ou faux ? faut-il transférer ?",
             "« quelles règles respecter pour communiquer sans risque ? »"),
}

rows = []
def add(q, a, intent):
    rows.append({"intent": intent, "question": q, "answer": a})

for lvl, lv in cur.get("didactic_programs_by_level", {}).items():
    for u in lv.get("units", []):
        uid = u.get("unit_id"); title = u.get("title", ""); sms = u.get("sub_modules", [])
        codes = []
        for sm in sms:
            for c in sm.get("competency_codes", []) or ([sm.get("competency")] if sm.get("competency") else []):
                if c and c not in codes: codes.append(c)
        first = codes[0] if codes else "C11"
        ctx, dec, prob = SIT[fam(first)]
        topics = " ; ".join(sm.get("topic", "") for sm in sms)
        sit = (f"Situation déclenchante (unité {uid} — {title}) :\n"
               f"• Contexte : {ctx}.\n• Déclencheur : {dec}.\n• Problème : {prob}\n"
               f"• Lien : annonce de la compétence {first} ; sujets : {topics}.\nDurée : 5 min, début de séance 1.")
        add(f"Propose une situation déclenchante pour l'unité {uid} ({lvl}).", sit, "situation")
        add(f"Comment introduire l'unité {uid} en {lvl} ?", sit, "situation")
        eva = (f"Évaluation formative (20 min) — unité {uid} ({lvl}, {', '.join(codes)}) :\n"
               "• Ex. 1 (7 min) : restitution guidée d'un savoir-faire vu en TP.\n"
               "• Ex. 2 (10 min) : mini-tâche sur fichier court, consignes affichées.\n"
               "• Auto-correction (3 min) : grille projetée, l'élève coche ses réussites.\n"
               "Critères minimaux : résultat conforme, démarche partiellement autonome.\n"
               "Perfectionnement : autonomie complète, soin, rapidité.")
        add(f"Rédige une évaluation formative de 20 min pour l'unité {uid} ({lvl}).", eva, "evaluation")
        add(f"Comment évaluer l'unité {uid} en {lvl} ?", eva, "evaluation")
        integ = (f"Activité d'intégration — unité {uid} ({lvl}) :\n"
                 f"• Situation-problème : produire un livrable combinant : {topics}.\n"
                 "• Consignes : 3 étapes opérationnelles affichées, travail en binôme.\n"
                 "• Livrable attendu : fichier numérique + 2 phrases de méthode.\n"
                 "• Critères : mobilisation coordonnée des acquis, soin, autonomie.")
        add(f"Propose une activité d'intégration pour l'unité {uid} ({lvl}).", integ, "integration")

for code, c in COMPS.items():
    res = c.get("resources", {})
    a = (f"{code} : {c.get('statement')}\n"
         f"Savoirs : {', '.join(res.get('savoir', []))}.\n"
         f"Savoir-faire : {', '.join(res.get('savoir_faire', []))}.\n"
         f"Savoir-être : {', '.join(res.get('savoir_etre', []))}.")
    add(f"Quelles ressources officielles pour la compétence {code} ?", a, "ressources")
    add(f"Décris la compétence {code}.", a, "ressources")

hols = cal.get("official_holidays", [])
if hols:
    h = hols[0]
    add("Quelle est la prochaine vacance ?",
        f"Prochaine vacance : {h.get('name')} du {h.get('start_date')} au {h.get('end_date')}.", "calendrier")
s1 = cal.get("middle_school_assessment_schedule", {}).get("semester_1", {})
add("Quand est la saisie des notes Massar du semestre 1 ?",
    f"Saisie des notes Massar (CC) avant le {s1.get('massar_grades_deadline')}.", "echeances")
add("Quand est l'examen local unifié des 3AC ?",
    f"Examen local unifié (3AC) : {s1.get('local_unified_exam_3AC')}.", "echeances")

lab = ped.get("predecessor_teacher_tips", {}).get("laboratory_management", [])
if lab:
    add("Conseils de gestion du laboratoire ?",
        "Gestion du laboratoire :\n" + "\n".join("• " + t for t in lab), "lab")
diff = ("Différenciation & binômes :\n"
        "• Binômes homogènes pour les TP dirigés ; semi-hétérogènes pour les projets.\n"
        "• Rotation stricte clavier/souris : 25 min par élève.\n"
        "• Fiche d'aide pas-à-pas pour les élèves en difficulté ; défi supplémentaire pour les rapides.\n"
        "• Un élève « tuteur » par rangée pour les pannes simples.")
add("Propose des modalités de différenciation en salle informatique.", diff, "differenciation")

# paraphrase augmentation
extra = list(rows)
for r in rows:
    if r["intent"] == "situation":
        extra.append({**r, "question": r["question"].replace("Propose", "Donne")})
random.seed(7); random.shuffle(extra)

(OUT / "qa_dataset.jsonl").write_text(
    "\n".join(json.dumps(x, ensure_ascii=False) for x in extra), encoding="utf-8")
print(f"OK {len(extra)} paires Q/R -> data/ai/qa_dataset.jsonl")
