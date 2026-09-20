import streamlit as st
import sys
import re
from pathlib import Path
from datetime import date

sys.path.append(str(Path(__file__).resolve().parent))

import theme
from api_client import api_get

st.set_page_config(page_title="Collegue AI", page_icon="🧑‍🏫", layout="wide")
theme.inject_theme()
theme.render_sidebar()

st.markdown("### 🏠 Tableau de bord")


def iso_dates(text):
    return re.findall(r"\d{4}-\d{2}-\d{2}", str(text))


today = date.today()

cal_resp = api_get("/api/reference/calendar/2026-2027")
cal = cal_resp["data"] if cal_resp["ok"] else {}
m = cal.get("framework_milestones", {})

start_txt = m.get("mandatory_class_start", "")
end_txt = m.get("classes_end_middle_school", "")
start = date.fromisoformat(start_txt) if start_txt else None
end = date.fromisoformat(end_txt) if end_txt else None

if start and today < start:
    week_label = "Avant la rentrée"
elif end and today > end:
    week_label = "Année terminée"
elif start:
    week_label = f"Semaine actuelle : S{(today - start).days // 7 + 1}"
else:
    week_label = "—"

events = []
for h in cal.get("official_holidays", []):
    try:
        events.append({
            "label": h.get("name", ""),
            "date": date.fromisoformat(h.get("start_date")),
            "kind": "🌴",
        })
    except Exception:
        pass
for sem_key, sem in cal.get("middle_school_assessment_schedule", {}).items():
    for key, value in sem.items():
        ds = iso_dates(value)
        if ds:
            events.append({
                "label": key,
                "date": date.fromisoformat(ds[0]),
                "kind": "⚠️",
            })

upcoming = sorted([e for e in events if e["date"] >= today], key=lambda e: e["date"])
next_evt = upcoming[0] if upcoming else None

annual = api_get("/api/planning/annual")
n_annual = len(annual["data"].get("plans", [])) if annual["ok"] else 0
unit_r = api_get("/api/planning/unit")
n_unit = len(unit_r["data"].get("plans", [])) if unit_r["ok"] else 0
seq_r = api_get("/api/planning/sequence")
n_seq = len(seq_r["data"].get("plans", [])) if seq_r["ok"] else 0

ai = api_get("/api/ai/status")
ai_data = ai["data"] if ai["ok"] else {}
if ai_data.get("available"):
    ai_txt = "🟢 IA locale en ligne"
elif ai_data.get("enabled"):
    ai_txt = "🟠 IA activée mais injoignable"
else:
    ai_txt = "⚪ IA désactivée (hors ligne)"

next_txt = next_evt["label"] if next_evt else "—"
next_sub = ""
if next_evt:
    next_sub = f"{next_evt['date'].isoformat()} • J-{(next_evt['date'] - today).days}"

cards = f"""
<div class="ca-grid">
  <div class="ca-card"><h4>📍 Position dans l'année</h4>
    <div class="ca-value" style="font-size:1.1rem">{week_label}</div>
    <div class="ca-sub">Aujourd'hui : {today.isoformat()}</div></div>
  <div class="ca-card"><h4>⏭️ Prochaine échéance</h4>
    <div class="ca-value" style="font-size:1rem">{next_txt}</div>
    <div class="ca-sub">{next_sub}</div></div>
  <div class="ca-card"><h4>🗂️ Documents préparés</h4>
    <div class="ca-value">{n_annual + n_unit + n_seq}</div>
    <div class="ca-sub">{n_annual} plan(s) annuel(s) • {n_unit} unité(s) • {n_seq} fiche(s)</div></div>
  <div class="ca-card"><h4>🤖 Assistant IA</h4>
    <div class="ca-value" style="font-size:1rem">{ai_txt}</div>
    <div class="ca-sub">Gérer dans la page Assistant IA</div></div>
</div>
"""
st.markdown(cards, unsafe_allow_html=True)

st.markdown("#### ⚡ Actions rapides")
st.markdown(
    """
    <div class="ca-grid">
      <a class="ca-card ca-action" href="/Planification_Annuelle">
        <span class="ca-action-icon">📆</span>
        <b>Plan annuel</b>
        <span class="ca-sub">Grille S1→S43, commentaires, modèle imprimable</span>
      </a>
      <a class="ca-card ca-action" href="/Planification_Unite">
        <span class="ca-action-icon">🗂️</span>
        <b>Plan d'unité</b>
        <span class="ca-sub">Compétences, séquences, moments</span>
      </a>
      <a class="ca-card ca-action" href="/Preparation_Sequence">
        <span class="ca-action-icon">📝</span>
        <b>Fiches</b>
        <span class="ca-sub">Ressources • Intégration • Évaluation</span>
      </a>
      <a class="ca-card ca-action" href="/Assistant_IA">
        <span class="ca-action-icon">🤖</span>
        <b>Assistant</b>
        <span class="ca-sub">IA locale + mode hors ligne</span>
      </a>
    </div>
    """,
    unsafe_allow_html=True,
)
left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown("#### 📅 Prochaines échéances officielles")
    for e in upcoming[:5]:
        days = (e["date"] - today).days
        badge = "ok" if days > 30 else ("warn" if days > 7 else "late")
        st.markdown(
            f'{e["kind"]} **{e["label"]}** — {e["date"].isoformat()} '
            f'<span class="ca-badge {badge}">J-{days}</span>',
            unsafe_allow_html=True,
        )

with right:
    st.markdown("#### 💡 Conseil du jour")
    ped = api_get("/api/reference/pedagogy")
    tip = "Privilégier la méthode démonstrative : Montrer → Faire faire → Faire dire."
    if ped["ok"]:
        tips = (
            ped["data"]
            .get("predecessor_teacher_tips", {})
            .get("didactic_best_practices", [])
        )
        if tips:
            tip = tips[today.toordinal() % len(tips)]
    st.info(tip)
