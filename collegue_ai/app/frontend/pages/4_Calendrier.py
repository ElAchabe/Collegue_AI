import streamlit as st
import sys
import re
from pathlib import Path
from datetime import date, timedelta

sys.path.append(str(Path(__file__).resolve().parents[1]))

import theme
from api_client import api_get

st.set_page_config(page_title="Collegue AI — Calendrier", layout="wide")
theme.inject_theme()
theme.render_sidebar()

st.markdown("### 🗓️ Calendrier officiel — Année scolaire 2026-2027")
st.caption("Arrêté 047.26 du 2026-07-03 — Ministère de l'Éducation Nationale, du Préscolaire et des Sports")

LABELS_FR = {
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


def iso_dates(text):
    return re.findall(r"\d{4}-\d{2}-\d{2}", str(text))


def card(title, value, sub=""):
    return (
        f'<div class="ca-card"><h4>{title}</h4>'
        f'<div class="ca-value" style="font-size:1rem">{value}</div>'
        f'<div class="ca-sub">{sub}</div></div>'
    )


resp = api_get("/api/reference/calendar/2026-2027")
if not resp["ok"]:
    st.error(resp["error"])
    st.stop()
cal = resp["data"]
today = date.today()

m = cal.get("framework_milestones", {})
start = date.fromisoformat(m.get("mandatory_class_start"))
end = date.fromisoformat(m.get("classes_end_middle_school"))
total_weeks = 43

# ---------- Current week + next deadline ----------
if today < start:
    current_week = None
    week_label = "Avant la rentrée des cours"
elif today > end:
    current_week = None
    week_label = "Année scolaire terminée"
else:
    current_week = (today - start).days // 7 + 1
    week_label = f"Semaine actuelle : S{current_week}"

events = []
for h in cal.get("official_holidays", []):
    events.append({
        "label": h.get("name", ""),
        "date": date.fromisoformat(h.get("start_date")),
        "kind": "holiday",
        "estimated": bool(h.get("is_estimated", False)),
    })
for sem_key, sem in cal.get("middle_school_assessment_schedule", {}).items():
    for key, value in sem.items():
        ds = iso_dates(value)
        if ds:
            events.append({
                "label": LABELS_FR.get(key, key),
                "date": date.fromisoformat(ds[0]),
                "kind": "assessment",
                "estimated": False,
            })

upcoming = [e for e in events if e["date"] >= today]
upcoming.sort(key=lambda e: e["date"])

top_cards = card("📍 Position", week_label, f"Aujourd'hui : {today.isoformat()}")
if upcoming:
    nxt = upcoming[0]
    days = (nxt["date"] - today).days
    top_cards += card("⏭️ Prochaine échéance", nxt["label"], f"{nxt['date'].isoformat()} • J-{days}")
top_cards += card("🏛️ Décret", "047.26", "Signé le 2026-07-03")
st.markdown(f'<div class="ca-grid">{top_cards}</div>', unsafe_allow_html=True)

# ---------- Jalons du cadre ----------
st.markdown("#### 🏛️ Jalons officiels du cadre")
rec = m.get("student_reception_staggered", {})
rec_txt = " • ".join(
    f"{k.replace('level_', '').replace('_and_primary_', ' & primaire ')} : {v}"
    for k, v in rec.items()
)
cards = (
    card("Rentrée administrative", m.get("administrative_entry", ""))
    + card("Rentrée des enseignants", m.get("teacher_entry", ""))
    + card("Début obligatoire des cours", m.get("mandatory_class_start", ""))
    + card("Fin des cours (collégial)", m.get("classes_end_middle_school", ""))
)
st.markdown(f'<div class="ca-grid">{cards}</div>', unsafe_allow_html=True)
st.caption(f"Accueil échelonné des élèves : {rec_txt}")

# ---------- Vacances & fêtes ----------
st.markdown("#### 🌴 Vacances & fêtes")
rows = []
for h in cal.get("official_holidays", []):
    est = "⚠️ estimée" if h.get("is_estimated") else ""
    rows.append({
        "Événement": h.get("name", ""),
        "Du": h.get("start_date", ""),
        "Au": h.get("end_date", ""),
        "Jours": h.get("duration_days", ""),
        "Statut": est or "officielle",
    })
st.dataframe(rows, use_container_width=True, hide_index=True)

# ---------- Échéances d'évaluation ----------
st.markdown("#### 📝 Échéances d'évaluation (Massar, examens, conseils)")
for sem_key, sem in cal.get("middle_school_assessment_schedule", {}).items():
    sem_num = "1" if sem_key == "semester_1" else "2"
    st.markdown(f"**Semestre {sem_num}**")
    sem_cards = ""
    for key, value in sem.items():
        ds = iso_dates(value)
        if not ds:
            continue
        d0 = date.fromisoformat(ds[0])
        days = (d0 - today).days
        badge = "ok" if days > 30 else ("warn" if days > 7 else "late")
        w = (d0 - start).days // 7 + 1
        rng = value if len(ds) > 1 or "to" in str(value) or "and" in str(value) else ds[0]
        sem_cards += (
            f'<div class="ca-card"><h4>{LABELS_FR.get(key, key)}</h4>'
            f'<div class="ca-value" style="font-size:.95rem">{rng}</div>'
            f'<span class="ca-badge {badge}">J-{days}</span>'
            f'<span class="ca-badge info">S{w}</span></div>'
        )
    st.markdown(f'<div class="ca-grid">{sem_cards}</div>', unsafe_allow_html=True)

# ---------- Frise annuelle ----------
st.markdown("#### 📅 Frise annuelle S1 → S43")
holiday_weeks = {}
for h in cal.get("official_holidays", []):
    hs = date.fromisoformat(h.get("start_date"))
    w = (hs - start).days // 7 + 1
    holiday_weeks[w] = h.get("name", "")

exam_weeks = {}
for sem_key, sem in cal.get("middle_school_assessment_schedule", {}).items():
    for key, value in sem.items():
        ds = iso_dates(value)
        if ds:
            w = (date.fromisoformat(ds[0]) - start).days // 7 + 1
            exam_weeks.setdefault(w, []).append(LABELS_FR.get(key, key))

gantt = '<div class="gantt">'
for w in range(1, total_weeks + 1):
    ws = start + timedelta(days=(w - 1) * 7)
    we = ws + timedelta(days=6)
    if w in holiday_weeks:
        cls, style = "gcell holiday", ""
        title = f"S{w} — 🌴 {holiday_weeks[w]}"
    elif w in exam_weeks:
        cls, style = "gcell", "background:#dc2626;color:#fff"
        title = f"S{w} — 📝 " + ", ".join(exam_weeks[w])
    else:
        cls, style = "gcell", ""
        title = f"S{w}"
    if current_week == w:
        style += "outline:3px solid #2563eb;outline-offset:1px"
        title += " • semaine actuelle"
    gantt += f'<div class="{cls}" style="{style}" title="{title} ({ws} → {we})">{w}</div>'
gantt += "</div>"
st.markdown(gantt, unsafe_allow_html=True)
st.caption("Hachuré = vacances • Rouge = semaine d'échéances (Massar/examens/conseils) • Contour bleu = semaine actuelle.")

# ---------- Printable document ----------
st.markdown("#### 🖨️ Document officiel imprimable")


def build_calendar_html():
    hol_rows = ""
    for h in cal.get("official_holidays", []):
        est = " (estimée)" if h.get("is_estimated") else ""
        hol_rows += (
            f"<tr><td>{h.get('name', '')}</td><td>{h.get('start_date', '')}</td>"
            f"<td>{h.get('end_date', '')}</td><td>{h.get('duration_days', '')}{est}</td></tr>"
        )
    ev_rows = ""
    for sem_key, sem in cal.get("middle_school_assessment_schedule", {}).items():
        for key, value in sem.items():
            ev_rows += (
                f"<tr><td>S{ '1' if sem_key == 'semester_1' else '2' }</td>"
                f"<td>{LABELS_FR.get(key, key)}</td><td>{value}</td></tr>"
            )
    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Calendrier officiel 2026-2027</title>
<style>body{{font-family:Arial,sans-serif;margin:20px;color:#111;font-size:12px}}
h1{{font-size:18px}}h2{{font-size:14px;margin-top:16px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #999;padding:5px 6px;text-align:left}}
.center{{text-align:center}}@media print{{body{{margin:8mm}}}}</style></head><body>
<div class="center">Royaume du Maroc — Ministère de l'Éducation Nationale, du Préscolaire et des Sports<br/>
<b>CALENDRIER OFFICIEL — ANNÉE SCOLAIRE 2026-2027</b><br/>Arrêté 047.26 du 2026-07-03</div>
<h2>I. Jalons du cadre</h2>
<table><tr><th>Jalon</th><th>Date</th></tr>
<tr><td>Rentrée administrative</td><td>{m.get('administrative_entry', '')}</td></tr>
<tr><td>Rentrée des enseignants</td><td>{m.get('teacher_entry', '')}</td></tr>
<tr><td>Début obligatoire des cours</td><td>{m.get('mandatory_class_start', '')}</td></tr>
<tr><td>Fin des cours (collégial)</td><td>{m.get('classes_end_middle_school', '')}</td></tr></table>
<h2>II. Vacances & fêtes</h2>
<table><tr><th>Événement</th><th>Du</th><th>Au</th><th>Durée</th></tr>{hol_rows}</table>
<h2>III. Échéances d'évaluation</h2>
<table><tr><th>Semestre</th><th>Échéance</th><th>Date(s)</th></tr>{ev_rows}</table>
</body></html>"""


school_name = st.text_input("Établissement", "Collège : ____________________")
st.download_button(
    "⬇️ Télécharger le calendrier officiel (HTML imprimable)",
    data=build_calendar_html(),
    file_name="calendrier_officiel_2026-2027.html",
    mime="text/html",
    use_container_width=True,
)
