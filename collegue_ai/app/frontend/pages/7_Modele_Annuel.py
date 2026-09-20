import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import theme
from api_client import api_get

st.set_page_config(page_title="Collegue AI — Modèle annuel", layout="wide")
theme.inject_theme()
theme.render_sidebar()

st.title("📄 Modèle officiel — Planification annuelle")

plans_response = api_get("/api/planning/annual")
saved_ids = [p["annual_plan_id"] for p in plans_response["data"].get("plans", [])] if plans_response["ok"] else []

if not saved_ids:
    st.warning("Aucun plan annuel enregistré. Générez d'abord un plan dans « Planification annuelle ».")
    st.stop()

c1, c2 = st.columns([2, 1])
pid = c1.selectbox("Plan à imprimer", saved_ids)
school_name = c2.text_input("Établissement", "Collège : ____________________")
teacher_name = st.text_input("Enseignant(e)", "")

grid_resp = api_get(f"/api/planning/annual/{pid}/grid")
if not grid_resp["ok"]:
    st.error(grid_resp["error"])
    st.stop()
grid = grid_resp["data"]


def build_official_html(grid, school_name, teacher_name):
    head = f"""
    <div style="text-align:center;font-size:12px;line-height:1.5">
      Royaume du Maroc<br/>
      Ministère de l'Éducation Nationale, du Préscolaire et des Sports<br/>
      <strong>{school_name}</strong><br/>
      <strong>PLANIFICATION ANNUELLE — {grid['subject']} — {grid['level_name']}</strong><br/>
      Année scolaire : {grid['school_year']} | Enseignant(e) : {teacher_name or '____________'}<br/>
      Masse horaire officielle : {grid['total_official_hours']} h |
      Volume planifié : {grid['total_planned_hours']} h
    </div>
    """

    body = '<table><tr><th>Mois</th><th>Semaines</th><th>Vacances / échéances</th>'
    body += '<th>Séquences & séances</th><th>Masse h.</th><th>Compétences</th><th>Évaluations</th></tr>'

    current_month = None
    for wk in grid["weeks"]:
        if wk["month"] != current_month:
            current_month = wk["month"]
            body += f'<tr class="m"><td colspan="7">{current_month}</td></tr>'

        notes = []
        if wk.get("full_holiday"):
            notes.append("🌴 " + wk["full_holiday"])
        elif wk.get("partial_holidays"):
            notes.append("🌴 " + ", ".join(wk["partial_holidays"]))
        if wk.get("deadlines"):
            notes.append("⚠ " + ", ".join(wk["deadlines"]))
        if wk.get("marker"):
            notes.append("📝 " + wk["marker"])

        seq = wk.get("sequence")
        if wk.get("full_holiday") and not seq:
            body += (
                f'<tr class="h"><td></td><td>S{wk["week"]}</td>'
                f'<td>{"<br/>".join(notes)}</td><td colspan="4">— vacances —</td></tr>'
            )
        elif seq:
            body += (
                f'<tr><td></td><td>S{wk["week"]}</td><td>{"<br/>".join(notes)}</td>'
                f'<td><span class="sq" style="background:{seq["color"]}">{seq["unit_id"]}</span> '
                f'{seq["topic"]}</td><td></td><td></td><td></td></tr>'
            )
        elif notes:
            body += (
                f'<tr class="e"><td></td><td>S{wk["week"]}</td>'
                f'<td>{"<br/>".join(notes)}</td><td colspan="4"></td></tr>'
            )

    seq_rows = '<table><tr><th>Unité</th><th>Séquence</th><th>Séances</th><th>Masse h.</th>'
    seq_rows += '<th>Compétences</th><th>Évaluation programmée</th></tr>'
    for it in grid["items"]:
        seq_rows += (
            f'<tr><td>{it["unit_id"]}</td><td>{it["topic"]}</td>'
            f'<td>{it["official_hours"]} séances (1 h)</td><td>{it["official_hours"]} h</td>'
            f'<td>{", ".join(it["competency_codes"])}</td>'
            f'<td>Évaluation formative (écrit, 20 min) en fin d\'unité</td></tr>'
        )
    seq_rows += "</table>"

    dl_rows = '<table><tr><th>Semestre</th><th>Échéance</th><th>Date(s)</th><th>Semaine</th></tr>'
    for dl in grid["deadlines"]:
        rng = dl["date"] if dl["end_date"] == dl["date"] else f'{dl["date"]} → {dl["end_date"]}'
        dl_rows += f'<tr><td>S{dl["semester"]}</td><td>{dl["label"]}</td><td>{rng}</td><td>S{dl["week"]}</td></tr>'
    dl_rows += "</table>"

    return (
        '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
        f'<title>Planification annuelle {grid["school_year"]}</title>'
        '<style>body{font-family:Arial,sans-serif;margin:18px;color:#111;font-size:12px}'
        'table{border-collapse:collapse;width:100%;font-size:10px;margin-top:8px}'
        'td,th{border:1px solid #777;padding:4px 5px;text-align:left;vertical-align:top}'
        'tr.m td{background:#e5e7eb;font-weight:bold}'
        'tr.h td{background:#fef3c7}tr.e td{background:#fee2e2}'
        '.sq{color:#fff;padding:1px 7px;border-radius:999px;font-size:9px}'
        'h2{font-size:14px;margin-top:16px}'
        '.sign{margin-top:26px;display:flex;justify-content:space-between;font-size:12px}'
        '@media print{body{margin:8mm}}</style></head><body>'
        + head +
        '<h2>I. Progression hebdomadaire</h2>' + body +
        '<h2>II. Récapitulatif des séquences</h2>' + seq_rows +
        '<h2>III. Échéances officielles (arrêté 047.26)</h2>' + dl_rows +
        '<div class="sign"><span>Signature de l\'enseignant(e) :</span>'
        '<span>Visa de l\'administration :</span></div>'
        '</body></html>'
    )


st.subheader("Aperçu du document")
st.write(
    f"**{grid['level_name']}** — {grid['total_official_hours']} h officielles / "
    f"{grid['total_planned_hours']} h planifiées — {grid['teaching_weeks_count']} semaines d'enseignement."
)
st.info("Le document complet (progression + récapitulatif + échéances + signatures) se télécharge ci-dessous.")

st.download_button(
    "️ Télécharger le modèle officiel (HTML imprimable)",
    data=build_official_html(grid, school_name, teacher_name),
    file_name=f"{pid}_modele_officiel.html",
    mime="text/html",
    type="primary",
    use_container_width=True
)
st.caption("Pour obtenir un PDF : ouvrez le fichier téléchargé dans le navigateur, puis Imprimer → Enregistrer en PDF.")
