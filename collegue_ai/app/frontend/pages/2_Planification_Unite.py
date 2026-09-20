import streamlit as st
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import theme
from api_client import api_get, api_post, api_put

st.set_page_config(page_title="Collegue AI — Planification d'unité", layout="wide")
theme.inject_theme()
theme.render_sidebar()

st.markdown("### 🗂️ Planification d'unité — consulter, commenter, imprimer")


def build_unit_html(up, weeks_info, school_name, teacher_name):
    seq_rows = ""
    for s in up.get("proposed_sequences", []):
        wi = weeks_info.get(s.get("sub_module_id"), {})
        seq_rows += (
            "<tr>"
            f"<td>{s.get('sub_module_id')}</td>"
            f"<td>{s.get('sequence_title')}</td>"
            f"<td>{', '.join(s.get('competency_codes', []))}</td>"
            f"<td>{s.get('duration_hours')} h</td>"
            f"<td>S{wi.get('start', '?')}→S{wi.get('end', '?')}</td>"
            "</tr>"
        )
    moments = "".join(
        f"<li><b>{m.get('moment')}</b> : {m.get('target')}</li>"
        for m in up.get("planning_moments", [])
    )
    sugg = "".join(f"<li>{s}</li>" for s in up.get("pedagogical_suggestions", []))
    tips = "".join(f"<li>{s}</li>" for s in up.get("laboratory_tips", []))
    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Plan d'unité — {up.get('unit_title')}</title>
<style>body{{font-family:Arial,sans-serif;margin:20px;color:#111;font-size:12px}}
h1{{font-size:18px}}h2{{font-size:14px;margin-top:16px}}
table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #999;padding:5px 6px;text-align:left;vertical-align:top}}
.center{{text-align:center}}
.sign{{margin-top:26px;display:flex;justify-content:space-between}}
@media print{{body{{margin:8mm}}}}</style></head><body>
<div class="center">Royaume du Maroc<br/>
Ministère de l'Éducation Nationale, du Préscolaire et des Sports<br/>
<b>{school_name}</b><br/>
<b>PLAN D'UNITÉ — INFORMATIQUE — {up.get('level_code')}</b><br/>
Année scolaire : {up.get('school_year')} | Enseignant(e) : {teacher_name or '____________'}</div>
<h1>Unité {up.get('unit_id')} — {up.get('unit_title')}</h1>
<p>Volume horaire officiel : {up.get('total_official_hours')} h •
Évaluations : formatives ≥ 2/semestre (20 min max) + sommative (55 min).</p>
<h2>I. Séquences</h2>
<table><tr><th>Sous-module</th><th>Séquence</th><th>Comp.</th><th>Masse h.</th><th>Semaines</th></tr>
{seq_rows}</table>
<h2>II. Moments d'apprentissage</h2><ul>{moments}</ul>
<h2>III. Suggestions pédagogiques officielles</h2><ul>{sugg}</ul>
<h2>IV. Gestion du laboratoire</h2><ul>{tips}</ul>
<h2>V. Notes de l'enseignant</h2><p>{up.get('teacher_notes', '') or '________________'}</p>
<div class="sign"><span>Signature de l'enseignant(e) :</span><span>Visa de l'administration :</span></div>
</body></html>"""


# ---------- Context topbar ----------
plans_resp = api_get("/api/planning/annual")
saved = plans_resp["data"].get("plans", []) if plans_resp["ok"] else []
if not saved:
    st.info("Générez d'abord un plan annuel dans la page « Planification annuelle ».")
    st.stop()

t1, t2, t3 = st.columns([2, 2, 1])
with t1:
    pid = st.selectbox("Plan annuel", [p["annual_plan_id"] for p in saved], key="up_pid")
level_code = pid.split("-")[1]

grid_resp = api_get(f"/api/planning/annual/{pid}/grid")
grid = grid_resp["data"] if grid_resp["ok"] else {}
items = grid.get("items", [])
unit_ids = []
for it in items:
    if it.get("unit_id") not in unit_ids:
        unit_ids.append(it.get("unit_id"))

if not unit_ids:
    st.warning("Aucune unité trouvée dans ce plan annuel.")
    st.stop()

with t2:
    uid = st.selectbox("Unité", unit_ids, format_func=lambda u: f"Unité {u}", key="up_uid")
with t3:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    gen = st.button("🔄 Générer / actualiser", type="primary", use_container_width=True)

key_tag = f"{pid}_{uid}"
if gen or st.session_state.get("unit_tag") != key_tag:
    r = api_post("/api/planning/unit/generate", {"annual_plan_id": pid, "unit_id": uid})
    if r["ok"]:
        st.session_state["unit_plan"] = r["data"]
        st.session_state["unit_tag"] = key_tag
    else:
        st.error(r["error"])
        st.stop()

up = st.session_state["unit_plan"]

# ---------- Unit position in the year ----------
unit_items = [it for it in items if it.get("unit_id") == uid]
unit_color = unit_items[0].get("color", "#2563eb") if unit_items else "#2563eb"
u_start = min([it.get("actual_week_start", 1) for it in unit_items]) if unit_items else 1
u_end = max([it.get("actual_week_end", 1) for it in unit_items]) if unit_items else 1
weeks_info = {
    it.get("sub_module_id"): {
        "start": it.get("actual_week_start"),
        "end": it.get("actual_week_end"),
    }
    for it in unit_items
}
holidays_in_unit = [
    wk.get("full_holiday")
    for wk in grid.get("weeks", [])
    if wk.get("full_holiday") and u_start <= wk.get("week", 0) <= u_end
]
sem = unit_items[0].get("semester", 1) if unit_items else 1

# ---------- Identity cards ----------
hol_txt = ("🌴 " + ", ".join(holidays_in_unit)) if holidays_in_unit else "Aucune semaine de vacances dans cette plage"
st.markdown(
    f"""
    <div class="ca-grid">
      <div class="ca-card"><h4>📦 Unité</h4>
        <div class="ca-value" style="font-size:1.02rem">{up.get('unit_title')}</div>
        <span class="chip" style="background:{unit_color}">Unité {uid}</span>
        <span class="ca-badge info">Semestre {sem}</span></div>
      <div class="ca-card"><h4>⏱️ Volume horaire</h4>
        <div class="ca-value">{up.get('total_official_hours')} h</div>
        <div class="ca-sub">{len(up.get('proposed_sequences', []))} séquences</div></div>
      <div class="ca-card"><h4>📅 Position dans l'année</h4>
        <div class="ca-value">S{u_start} → S{u_end}</div>
        <div class="ca-sub">{hol_txt}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Mini-Gantt ----------
gantt = '<div class="gantt">'
for wk in grid.get("weeks", []):
    seq = wk.get("sequence") or {}
    if seq.get("unit_id") == uid:
        cls, style = "gcell", f"background:{unit_color};color:#fff"
    elif wk.get("full_holiday"):
        cls, style = "gcell holiday", ""
    else:
        cls, style = "gcell", "opacity:.35"
    gantt += f'<div class="{cls}" style="{style}" title="S{wk["week"]}">{wk["week"]}</div>'
gantt += "</div>"
st.markdown(gantt, unsafe_allow_html=True)
st.caption("Semaines de l'unité en couleur • vacances hachurées • reste de l'année estompé.")

left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown("#### 🎯 Compétences visées")
    comp_resp = api_get(f"/api/reference/curriculum/{level_code}")
    comp_map = {}
    if comp_resp["ok"]:
        for domain in comp_resp["data"].get("competency_framework", {}).get("domains_of_action", []):
            for c in domain.get("competencies", []):
                comp_map[c.get("code")] = c
    for cd in up.get("competency_details", []):
        code = cd.get("code")
        full = comp_map.get(code, {})
        with st.expander(f"**{code}** — {cd.get('statement')}"):
            res = full.get("resources", {})
            k1, k2, k3 = st.columns(3)
            k1.markdown("**Savoirs**\n" + "\n".join(f"- {x}" for x in res.get("savoir", [])))
            k2.markdown("**Savoir-faire**\n" + "\n".join(f"- {x}" for x in res.get("savoir_faire", [])))
            k3.markdown("**Savoir-être**\n" + "\n".join(f"- {x}" for x in res.get("savoir_etre", [])))

    st.markdown("#### 🧩 Séquences de l'unité")
    for s in up.get("proposed_sequences", []):
        wi = weeks_info.get(s.get("sub_module_id"), {})
        st.markdown(
            f"""
            <div class="ca-card" style="margin-bottom:10px">
              <span class="chip" style="background:{unit_color}">{uid}</span>
              <b>{s.get('sequence_title')}</b><br/>
              <span class="ca-badge ok">S{wi.get('start')}→S{wi.get('end')}</span>
              <span class="ca-badge info">{', '.join(s.get('competency_codes', []))}</span>
              <span class="ca-badge warn">{s.get('duration_hours')} h</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/3_Preparation_Sequence.py",
            label=f"➡️ Préparer les 3 fiches : {s.get('sequence_title')[:42]}…",
        )

    st.markdown("#### 🔄 Les trois moments d'apprentissage")
    m1, m2, m3 = st.columns(3)
    for col, m in zip([m1, m2, m3], up.get("planning_moments", [])):
        with col:
            st.markdown(
                f"<div class='ca-card'><b>{m.get('moment')}</b>"
                f"<div class='ca-sub' style='opacity:1'>{m.get('target')}</div></div>",
                unsafe_allow_html=True,
            )

with right:
    st.markdown("#### 💡 Conseils officiels")
    with st.popover("📖 Suggestions pédagogiques officielles"):
        for s in up.get("pedagogical_suggestions", []):
            st.write(f"- {s}")
    with st.popover("🧪 Gestion du laboratoire (conseils)"):
        for s in up.get("laboratory_tips", []):
            st.write(f"- {s}")

    st.markdown("#### ✏️ Notes de l'enseignant")
    notes = st.text_area("Notes", value=up.get("teacher_notes", ""), height=140, key=f"un_notes_{uid}")
    if st.button("💾 Enregistrer les notes", use_container_width=True):
        up["teacher_notes"] = notes
        r = api_put(f"/api/planning/unit/{up['unit_plan_id']}", up)
        if r["ok"]:
            st.success("Notes enregistrées.")
        else:
            st.error(r["error"])

    st.markdown("#### 🖨️ Modèle officiel de l'unité")
    school_name = st.text_input("Établissement", "Collège : ____________________")
    teacher_name = st.text_input("Enseignant(e)", "")
    st.download_button(
        "⬇️ Télécharger le document unité (HTML imprimable)",
        data=build_unit_html(up, weeks_info, school_name, teacher_name),
        file_name=f"{up['unit_plan_id']}_document.html",
        mime="text/html",
        use_container_width=True,
    )
    st.download_button(
        "⬇️ JSON",
        data=json.dumps(up, ensure_ascii=False, indent=2),
        file_name=f"{up['unit_plan_id']}.json",
        mime="application/json",
        use_container_width=True,
    )
