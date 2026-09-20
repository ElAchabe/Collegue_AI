import streamlit as st
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import theme
from api_client import api_get, api_post, api_put

st.set_page_config(page_title="Collegue AI — Préparation de séquence", layout="wide")
theme.inject_theme()
theme.render_sidebar()

st.markdown("### 📝 Préparation de séquence — les 3 fiches officielles")


def build_sequence_dossier(up_full, seq, fiches, school_name, teacher_name):
    fr = fiches.get("fiche_ressources", {})
    fi = fiches.get("fiche_integration", {})
    fe = fiches.get("fiche_evaluation", {})
    res = fr.get("resources", {})
    crit = fe.get("criteria", {})
    der = fr.get("deroulement", {})
    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Dossier de séquence — {seq.get('sequence_title')}</title>
<style>body{{font-family:Arial,sans-serif;margin:20px;color:#111;font-size:12px}}
h1{{font-size:18px}}h2{{font-size:14px;margin-top:18px;border-bottom:2px solid #333;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #999;padding:5px 6px;vertical-align:top;text-align:left}}
ul{{margin:6px 0}}.center{{text-align:center}}
.sign{{margin-top:24px;display:flex;justify-content:space-between}}
@media print{{body{{margin:8mm}}}}</style></head><body>
<div class="center">Royaume du Maroc — Ministère de l'Éducation Nationale, du Préscolaire et des Sports<br/>
<b>{school_name}</b><br/>
<b>DOSSIER PÉDAGOGIQUE DE SÉQUENCE — INFORMATIQUE — {up_full.get('level_code')}</b><br/>
Année scolaire : {up_full.get('school_year')} | Enseignant(e) : {teacher_name or '____________'}</div>
<h1>Unité {up_full.get('unit_id')} — {seq.get('sequence_title')} ({seq.get('duration_hours')} h)</h1>
<h2>1. Fiche Ressources</h2>
<table>
<tr><th>Compétence(s)</th><td>{', '.join(seq.get('competency_codes', []))}</td></tr>
<tr><th>Savoirs</th><td><ul>{''.join(f'<li>{x}</li>' for x in res.get('savoir', []))}</ul></td></tr>
<tr><th>Savoir-faire</th><td><ul>{''.join(f'<li>{x}</li>' for x in res.get('savoir_faire', []))}</ul></td></tr>
<tr><th>Savoir-être</th><td><ul>{''.join(f'<li>{x}</li>' for x in res.get('savoir_etre', []))}</ul></td></tr>
<tr><th>Prérequis</th><td>{'<br/>'.join(fr.get('prerequisites', [])) or '—'}</td></tr>
<tr><th>Matériel & logistique</th><td>{'<br/>'.join(fr.get('material_and_logistics', [])) or '—'}</td></tr>
<tr><th>Déroulement</th><td>Situation déclenchante : {der.get('situation_declenchante', '') or '—'}<br/>
Activité pratique : {der.get('activite_pratique', '') or '—'}<br/>
Synthèse / trace écrite : {der.get('synthese_trace_ecrite', '') or '—'}</td></tr>
<tr><th>Différenciation</th><td>{'<br/>'.join(fr.get('differentiation', [])) or '—'}</td></tr>
</table>
<h2>2. Fiche Intégration</h2>
<table>
<tr><th>Situation-problème</th><td>{fi.get('situation_probleme', '') or '—'}</td></tr>
<tr><th>Consignes opérationnelles</th><td>{'<br/>'.join(fi.get('consignes_operationnelles', [])) or '—'}</td></tr>
<tr><th>Ressources à mobiliser</th><td>{'<br/>'.join(fi.get('ressources_a_mobiliser', [])) or '—'}</td></tr>
<tr><th>Organisation & livrable</th><td>{fi.get('group_organization', '')} — Livrable : {fi.get('livrable_attendu', '') or '—'}</td></tr>
</table>
<h2>3. Fiche Évaluation</h2>
<table>
<tr><th>Type & durée</th><td>{fe.get('evaluation_type', 'formative')} — {fe.get('duration_minutes', 20)} min</td></tr>
<tr><th>Situation d'évaluation</th><td>{fe.get('evaluation_situation', '') or '—'}</td></tr>
<tr><th>Critères minimaux</th><td>{'<br/>'.join(crit.get('criteres_minimaux', [])) or '—'}</td></tr>
<tr><th>Critères de perfectionnement</th><td>{'<br/>'.join(crit.get('criteres_de_perfectionnement', [])) or '—'}</td></tr>
<tr><th>Indicateurs observables</th><td>{'<br/>'.join(fe.get('observable_indicators', [])) or '—'}</td></tr>
</table>
<div class="sign"><span>Signature de l'enseignant(e) :</span><span>Visa de l'administration :</span></div>
</body></html>"""


# ---------- Context topbar ----------
unit_resp = api_get("/api/planning/unit")
unit_plans = unit_resp["data"].get("plans", []) if unit_resp["ok"] else []
if not unit_plans:
    st.info("Générez d'abord un plan d'unité dans la page « Planification d'unité ».")
    st.stop()

t1, t2 = st.columns([1, 2])
with t1:
    upid = st.selectbox("Plan d'unité", [u["unit_plan_id"] for u in unit_plans], key="sq_upid")

up_full_resp = api_get(f"/api/planning/unit/{upid}")
up_full = up_full_resp["data"] if up_full_resp["ok"] else {}
seqs = up_full.get("proposed_sequences", [])

if not seqs:
    st.warning("Ce plan d'unité ne contient aucune séquence.")
    st.stop()

seq_options = [f"{s.get('sub_module_id')} — {s.get('sequence_title')}" for s in seqs]
with t2:
    seq_label = st.selectbox("Séquence", seq_options, key="sq_sel")
seq = seqs[seq_options.index(seq_label)]
sub_id = seq.get("sub_module_id")

# ---------- Ensure the 3 official fiches exist ----------
SUFFIX = {"fiche_ressources": "RES", "fiche_integration": "INT", "fiche_evaluation": "EVA"}
fiches = {}
for ftype, suf in SUFFIX.items():
    fid = f"SEQ-{sub_id}-{suf}"
    r = api_get(f"/api/planning/sequence/{fid}")
    if r["ok"]:
        fiches[ftype] = r["data"]
    else:
        g = api_post(
            "/api/planning/sequence/generate",
            {"unit_plan_id": upid, "sub_module_id": sub_id, "fiche_type": ftype},
        )
        fiches[ftype] = g["data"] if g["ok"] else {}

# ---------- Identity cards ----------
st.markdown(
    f"""
    <div class="ca-grid">
      <div class="ca-card"><h4>🧩 Séquence</h4>
        <div class="ca-value" style="font-size:1rem">{seq.get('sequence_title')}</div>
        <span class="chip" style="background:#2563eb">Unité {up_full.get('unit_id')}</span>
        <span class="ca-badge info">{', '.join(seq.get('competency_codes', []))}</span></div>
      <div class="ca-card"><h4>⏱️ Durée officielle</h4>
        <div class="ca-value">{seq.get('duration_hours')} h</div>
        <div class="ca-sub">Séances de 1 h (TP inclus)</div></div>
      <div class="ca-card"><h4>📄 Fiches préparées</h4>
        <div class="ca-value">3</div>
        <div class="ca-sub">Ressources • Intégration • Évaluation</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- The 3 official fiches ----------
tab_res, tab_int, tab_eva = st.tabs(["📘 Fiche Ressources", "🧩 Fiche Intégration", "📝 Fiche Évaluation"])

with tab_res:
    fr = fiches.get("fiche_ressources", {})
    with st.expander("📐 Structure officielle du document Ressources"):
        for line in fr.get("template_structure", []):
            st.write(f"- {line}")
    res = fr.get("resources", {})
    c1, c2, c3 = st.columns(3)
    c1.markdown("**Savoirs**\n" + "\n".join(f"- {x}" for x in res.get("savoir", [])))
    c2.markdown("**Savoir-faire**\n" + "\n".join(f"- {x}" for x in res.get("savoir_faire", [])))
    c3.markdown("**Savoir-être**\n" + "\n".join(f"- {x}" for x in res.get("savoir_etre", [])))

    pre = st.text_area("Prérequis diagnostiqués (un par ligne)", "\n".join(fr.get("prerequisites", [])), key="fr_pre")
    mat = st.text_area("Matériel & logistique (un par ligne)", "\n".join(fr.get("material_and_logistics", [])), key="fr_mat")
    sd = st.text_area("Situation déclenchante", fr.get("deroulement", {}).get("situation_declenchante", ""), key="fr_sd")
    ap = st.text_area("Activité pratique", fr.get("deroulement", {}).get("activite_pratique", ""), key="fr_ap")
    sy = st.text_area("Synthèse / trace écrite", fr.get("deroulement", {}).get("synthese_trace_ecrite", ""), key="fr_sy")
    dif = st.text_area("Différenciation & gestion des binômes (un par ligne)", "\n".join(fr.get("differentiation", [])), key="fr_dif")

    if st.button("💾 Enregistrer la fiche Ressources", use_container_width=True):
        fr["prerequisites"] = [l for l in pre.splitlines() if l.strip()]
        fr["material_and_logistics"] = [l for l in mat.splitlines() if l.strip()]
        fr.setdefault("deroulement", {})
        fr["deroulement"]["situation_declenchante"] = sd
        fr["deroulement"]["activite_pratique"] = ap
        fr["deroulement"]["synthese_trace_ecrite"] = sy
        fr["differentiation"] = [l for l in dif.splitlines() if l.strip()]
        r = api_put(f"/api/planning/sequence/{fr.get('sequence_plan_id')}", fr)
        if r["ok"]:
            st.success("Fiche Ressources enregistrée.")
        else:
            st.error(r["error"])

with tab_int:
    fi = fiches.get("fiche_integration", {})
    with st.expander("📐 Structure officielle du document Intégration"):
        for line in fi.get("template_structure", []):
            st.write(f"- {line}")
    sit_p = st.text_area("Situation-problème contextualisée (réelle ou réaliste)", fi.get("situation_probleme", ""), key="fi_sit")
    cons = st.text_area("Consignes opérationnelles de travail (une par ligne)", "\n".join(fi.get("consignes_operationnelles", [])), key="fi_cons")
    st.markdown("**Ressources à mobiliser (savoir-faire officiels) :**")
    st.write("\n".join(f"- {x}" for x in fi.get("ressources_a_mobiliser", [])) or "—")
    org = st.text_input("Organisation des groupes / binômes", fi.get("group_organization", ""), key="fi_org")
    liv = st.text_input("Livrable attendu", fi.get("livrable_attendu", ""), key="fi_liv")

    if st.button("💾 Enregistrer la fiche Intégration", use_container_width=True):
        fi["situation_probleme"] = sit_p
        fi["consignes_operationnelles"] = [l for l in cons.splitlines() if l.strip()]
        fi["group_organization"] = org
        fi["livrable_attendu"] = liv
        r = api_put(f"/api/planning/sequence/{fi.get('sequence_plan_id')}", fi)
        if r["ok"]:
            st.success("Fiche Intégration enregistrée.")
        else:
            st.error(r["error"])

with tab_eva:
    fe = fiches.get("fiche_evaluation", {})
    st.markdown(
        """
        <div class="ca-grid">
          <div class="ca-card"><h4>🔁 Formative</h4>
            <div class="ca-sub" style="opacity:1">≥ 2 / semestre • ≤ 20 min • droit à l'erreur (l'erreur = point de départ de la remédiation)</div></div>
          <div class="ca-card"><h4>🏁 Sommative</h4>
            <div class="ca-sub" style="opacity:1">1 / semestre • ≈ 55 min • situation de résolution de problèmes complexe</div></div>
          <div class="ca-card"><h4>📏 Critères</h4>
            <div class="ca-sub" style="opacity:1">peu nombreux • minimaux vs perfectionnement • indépendants • observables</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("📐 Structure officielle du document Évaluation"):
        for line in fe.get("template_structure", []):
            st.write(f"- {line}")

    etype = st.selectbox(
        "Type d'évaluation",
        ["formative", "summative"],
        index=0 if fe.get("evaluation_type") == "formative" else 1,
        key="fe_type",
    )
    dur = 20 if etype == "formative" else 55
    st.caption(f"Durée recommandée (norme officielle) : {dur} min.")

    esit = st.text_area("Énoncé de la situation d'évaluation (inédite pour l'apprenant)", fe.get("evaluation_situation", ""), key="fe_sit")
    cmin = st.text_area("Critères minimaux (un par ligne)", "\n".join(fe.get("criteria", {}).get("criteres_minimaux", [])), key="fe_cmin")
    cperf = st.text_area("Critères de perfectionnement (un par ligne)", "\n".join(fe.get("criteria", {}).get("criteres_de_perfectionnement", [])), key="fe_cperf")
    ind = st.text_area("Indicateurs observables de réussite (un par ligne)", "\n".join(fe.get("observable_indicators", [])), key="fe_ind")

    if st.button("💾 Enregistrer la fiche Évaluation", use_container_width=True):
        fe["evaluation_type"] = etype
        fe["duration_minutes"] = dur
        fe["evaluation_situation"] = esit
        fe.setdefault("criteria", {})
        fe["criteria"]["criteres_minimaux"] = [l for l in cmin.splitlines() if l.strip()]
        fe["criteria"]["criteres_de_perfectionnement"] = [l for l in cperf.splitlines() if l.strip()]
        fe["observable_indicators"] = [l for l in ind.splitlines() if l.strip()]
        r = api_put(f"/api/planning/sequence/{fe.get('sequence_plan_id')}", fe)
        if r["ok"]:
            st.success("Fiche Évaluation enregistrée.")
        else:
            st.error(r["error"])

# ---------- Printable dossier ----------
st.divider()
st.markdown("#### 🖨️ Dossier pédagogique de la séquence (3 fiches)")
d1, d2 = st.columns([2, 1])
with d1:
    school_name = st.text_input("Établissement", "Collège : ____________________")
    teacher_name = st.text_input("Enseignant(e)", "")
with d2:
    st.download_button(
        "⬇️ Télécharger le dossier (HTML imprimable)",
        data=build_sequence_dossier(up_full, seq, fiches, school_name, teacher_name),
        file_name=f"DOSSIER_{sub_id}.html",
        mime="text/html",
        use_container_width=True,
    )
