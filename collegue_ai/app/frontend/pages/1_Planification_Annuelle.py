import streamlit as st
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import theme
from api_client import api_get, api_post, api_put

st.set_page_config(page_title="Collegue AI — Planification annuelle", layout="wide")
theme.inject_theme()
theme.render_sidebar()

# ==========================================
# Fonctions utilitaires et Dialogs (doivent être définies avant le rendu UI)
# ==========================================

def find_item_for_week(plan_data, week_num):
    """Retrouve la séquence programmée sur une semaine donnée."""
    for it in plan_data.get("items", []):
        ws = it.get("actual_week_start")
        we = it.get("actual_week_end")
        if ws and we and ws <= week_num <= we:
            return it
    return None

@st.dialog("💬 Semaine : contenu programmé & remarque")
def week_dialog(wk):
    p = st.session_state.get("annual_plan", {})
    key = str(wk["week"])

    st.markdown(f"### Semaine S{wk['week']} · {wk['start']} → {wk['end']}")

    # --- Contenu pédagogique programmé cette semaine ---
    item = find_item_for_week(p, wk["week"])
    if item:
        st.markdown(
            f"**Unité :** {item.get('unit_id')} — {item.get('unit_title', '')}\n\n"
            f"**Séquence :** {item.get('topic')}\n\n"
            f"**Compétence(s) :** {', '.join(item.get('competency_codes', []))}\n\n"
            f"**Masse horaire :** {item.get('official_hours')} h officielle / "
            f"{item.get('planned_hours')} h planifiée"
        )
    else:
        st.caption("Aucune séquence programmée cette semaine.")

    # --- Événements officiels de la semaine ---
    events = []
    if wk.get("full_holiday"):
        events.append("🌴 " + wk["full_holiday"])
    events += ["🌴 " + x for x in wk.get("partial_holidays", [])]
    if wk.get("deadlines"):
        events.append("⚠️ " + ", ".join(wk["deadlines"]))
    if wk.get("marker"):
        events.append("📝 " + wk["marker"])
    if events:
        st.info(" · ".join(events))

    st.divider()

    # --- Remarque / tâche pédagogique ---
    current = p.get("weekly_notes", {}).get(key, "")
    txt = st.text_area(
        "Remarque / tâche pédagogique à enregistrer",
        value=current,
        height=140,
    )

    b1, b2 = st.columns(2)
    if b1.button("💾 Enregistrer", type="primary", use_container_width=True):
        p.setdefault("weekly_notes", {})[key] = txt
        r = api_put(f"/api/planning/annual/{p['annual_plan_id']}", p)
        if r["ok"]:
            st.session_state["annual_plan"] = p
            st.success("Remarque enregistrée.")
            st.rerun()
        else:
            st.error(r["error"])
            
    if b2.button("🗑️ Effacer", use_container_width=True):
        p.setdefault("weekly_notes", {}).pop(key, None)
        api_put(f"/api/planning/annual/{p['annual_plan_id']}", p)
        st.rerun()

# ==========================================


st.title("📆 Planification annuelle")

BADGES = {"ok": "conforme", "info": "repère", "warn": "vigilance", "late": "à corriger"}

# ---------- Context topbar ----------
plans_response = api_get("/api/planning/annual")
saved_ids = [p["annual_plan_id"] for p in plans_response["data"].get("plans", [])] if plans_response["ok"] else []

t1, t2, t3 = st.columns([1, 1, 2])
level = t1.selectbox("Niveau", ["1AC", "2AC", "3AC"], key="tb_level")
school_year = t2.text_input("Année scolaire", "2026-2027", key="tb_year")
saved_choice = t3.selectbox("Plan enregistré (consulter / modifier)", ["— nouveau plan —"] + saved_ids, key="tb_saved")

a1, a2 = st.columns([2, 1])
generate = a1.button("➕ Générer un nouveau plan", type="primary", use_container_width=True)
load_btn = a2.button("📂 Charger le plan sélectionné", use_container_width=True, disabled=(saved_choice == "— nouveau plan —"))

if generate:
    r = api_post("/api/planning/annual/generate", {"level_code": level, "school_year": school_year})
    if r["ok"]:
        st.session_state["annual_plan"] = r["data"]
        st.success("Planification annuelle générée.")
    else:
        st.error(r["error"])

if load_btn and saved_choice != "— nouveau plan —":
    r = api_get(f"/api/planning/annual/{saved_choice}")
    if r["ok"]:
        st.session_state["annual_plan"] = r["data"]
        st.success(f"Plan {saved_choice} chargé.")
    else:
        st.error(r["error"])

plan = st.session_state.get("annual_plan")
if not plan:
    st.info("Générez un nouveau plan ou chargez un plan enregistré pour afficher la planification.")
    st.stop()

pid = plan["annual_plan_id"]
grid_resp = api_get(f"/api/planning/annual/{pid}/grid")
if not grid_resp["ok"]:
    st.error(grid_resp["error"])
    st.stop()
grid = grid_resp["data"]

st.page_link("pages/7_Modele_Annuel.py", label="📄 Ouvrir le modèle officiel imprimable (téléchargement / impression)", use_container_width=True)

# ---------- VISIBLE official reminders (tips) ----------

# ---------- Rappels officiels : verdict global + 3 familles regroupées ----------

st.markdown("### 💡 Rappels officiels — cliquez sur une carte pour le détail")

BADGE_LABELS = {"ok": "Conforme", "info": "Repère", "warn": "Vigilance", "late": "À corriger"}

tips = []
official = int(grid.get("total_official_hours", 0))
planned = int(grid.get("total_planned_hours", 0))

if planned == official:
    tips.append({
        "kind": "ok", "icon": "✏️", "label": "Masse horaire : conforme",
        "title": "Masse horaire officielle",
        "details": f"Planifié : {planned} h — Officiel : {official} h.",
        "how": "Conservez ce total si vous modifiez une séquence : toute heure ajoutée doit être retirée ailleurs.",
        "source": "curriculum_clean.json — total_hours par niveau.",
    })
else:
    tips.append({
        "kind": "late", "icon": "✏️", "label": "Masse horaire : à corriger",
        "title": "Masse horaire officielle",
        "details": f"Planifié : {planned} h — Officiel : {official} h.",
        "how": "Ajustez les heures des séquences concernées via « Consulter, commenter, modifier une séquence ».",
        "source": "curriculum_clean.json — total_hours par niveau.",
    })

tips.append({
    "kind": "info", "icon": "🗓️",
    "label": f"{grid.get('teaching_weeks_count', 34)} semaines d'enseignement",
    "title": "Semaines d'enseignement et d'évaluation",
    "details": f"{grid.get('teaching_weeks_count', 34)} semaines utiles réparties de S1 à S{len(grid.get('weeks', []))}.",
    "how": "Les semaines de vacances restent libres ; les évaluations (écrits 20 min, sommatives 55 min) se placent sur des semaines d'enseignement.",
    "source": "academic_calendar.json — pacing_structure_weeks.",
})

tips.append({
    "kind": "ok", "icon": "🌴", "label": "Vacances : aucune séquence placée",
    "title": "Règle des vacances",
    "details": "Aucune séquence ne chevauche une semaine de vacances.",
    "how": "Si vous déplacez une séquence, vérifiez que la nouvelle semaine est libre (voir page Calendrier).",
    "source": "academic_calendar.json — official_holidays.",
})

tips.append({
    "kind": "info", "icon": "⚠️", "label": "Déplacer une séquence",
    "title": "Avant de déplacer une séquence",
    "details": "Les échéances officielles (Massar, examens unifiés, conseils) sont fixes.",
    "how": "Ouvrez « Échéances officielles » ci-dessous et choisissez une semaine libre avant l'échéance concernée.",
    "source": "academic_calendar.json — middle_school_assessment_schedule.",
})

est = grid.get("estimated_holidays", [])
if est:
    tips.append({
        "kind": "warn", "icon": "🕌", "label": f"{len(est)} date(s) estimée(s)",
        "title": "Dates religieuses estimées",
        "details": "À confirmer officiellement : " + ", ".join(est) + ".",
        "how": "Ces dates peuvent être décalées d'un ou deux jours selon l'observation lunaire. Revérifiez avant de figer le semestre 2.",
        "source": "academic_calendar.json — is_estimated : true.",
    })

per_row = 3
for i in range(0, len(tips), per_row):
    cols = st.columns(per_row)
    for col, tip in zip(cols, tips[i:i + per_row]):
        with col:
            st.markdown(
                f'<div class="tip-badge {tip["kind"]}">{BADGE_LABELS[tip["kind"]]}</div>',
                unsafe_allow_html=True,
            )
            with st.popover(f'{tip["icon"]}  {tip["label"]}'):
                st.markdown(f'### {tip["icon"]} {tip["title"]}')
                st.write(tip["details"])
                st.info(tip["how"])
                st.caption("Source : " + tip["source"])

# ---------- Échéances officielles : même titre que Rappels + semestres exclusifs + popups ----------
st.markdown("### ⏰ Échéances officielles (arrêté 047.26) — choisissez un semestre, cliquez pour le détail")

DEADLINE_DETAILS = {
    "Derniers contrôles continus": {
        "what": "Dernière série de contrôles continus du semestre (contrôle continu).",
        "do": "Terminez les passations et la correction, puis programmez la remédiation avant la saisie des notes.",
    },
    "Saisie des notes Massar (CC)": {
        "what": "Date limite de saisie des notes du contrôle continu dans Massar.",
        "do": "Vérifiez vos moyennes et saisissez-les dans Massar avant cette date.",
    },
    "Examen local unifié (3AC)": {
        "what": "Examen local unifié pour les 3AC.",
        "do": "Préparez les élèves, organisez la surveillance et la correction selon les normes officielles.",
    },
    "Saisie des notes examen local": {
        "what": "Date limite de saisie des notes de l'examen local unifié.",
        "do": "Saisissez les notes de l'examen local dans Massar avant cette date.",
    },
    "Génération des rapports Massar": {
        "what": "Début de génération des rapports Massar du semestre.",
        "do": "Contrôlez la complétude de vos saisies avant la génération des rapports.",
    },
    "Conseils de classe": {
        "what": "Tenue des conseils de classe du semestre.",
        "do": "Préparez les dossiers des élèves et les bilans à présenter au conseil.",
    },
    "Distribution des bulletins": {
        "what": "Distribution des bulletins aux familles.",
        "do": "Préparez la communication avec les parents (points forts, pistes de remédiation).",
    },
    "Préparation collective examen régional": {
        "what": "Journées de préparation collective à l'examen régional unifié (3AC).",
        "do": "Organisez des séances de révision et d'entraînement sur situations complexes.",
    },
    "Examen régional unifié (3AC)": {
        "what": "Examen régional unifié pour les 3AC.",
        "do": "Assurez la logistique et la surveillance ; accompagnez les élèves jusqu'à la veille.",
    },
    "Saisie des notes examen régional": {
        "what": "Date limite de saisie des notes de l'examen régional.",
        "do": "Saisissez les notes dans Massar avant cette date.",
    },
    "Génération du rapport final Massar": {
        "what": "Génération du rapport final Massar de l'année.",
        "do": "Vérifiez toutes les saisies de l'année avant la génération.",
    },
    "Conseils de classe et d'orientation": {
        "what": "Conseils de classe et d'orientation de fin d'année.",
        "do": "Préparez les bilans et les propositions d'orientation.",
    },
    "Distribution des résultats finaux": {
        "what": "Distribution des résultats finaux aux élèves et familles.",
        "do": "Organisez la remise des résultats et l'accompagnement des élèves.",
    },
}


@st.dialog("📌 Détail de l'échéance")
def show_deadline(dl):
    info = DEADLINE_DETAILS.get(
        dl["label"],
        {"what": "Échéance officielle de l'arrêté 047.26.", "do": "Consultez la note ministérielle correspondante."},
    )
    rng = dl["date"] if dl["end_date"] == dl["date"] else f"{dl['date']} → {dl['end_date']}"
    badge = "ok" if dl["days_until"] > 30 else ("warn" if dl["days_until"] > 7 else "late")
    st.markdown(f"### {dl['label']}")
    st.write(f"**Date(s) :** {rng}")
    st.write(f"**Semaine de la grille :** S{dl['week']}")
    st.markdown(f'<span class="ca-badge {badge}">J-{dl["days_until"]}</span>', unsafe_allow_html=True)
    st.write(info["what"])
    st.info("**À faire :** " + info["do"])
    st.caption("Source : academic_calendar.json — arrêté 047.26.")


sem_choice = st.radio(
    "Semestre",
    ["Semestre 1", "Semestre 2"],
    horizontal=True,
    label_visibility="collapsed",
    key="sem_choice",
)
sem_num = 1 if sem_choice == "Semestre 1" else 2

sem_deadlines = [d for d in grid["deadlines"] if d["semester"] == sem_num]

dcols = st.columns(2)
for i, dl in enumerate(sem_deadlines):
    with dcols[i % 2]:
        if st.button(
            f"📅 {dl['label']}  •  S{dl['week']}  •  J-{dl['days_until']}",
            key=f"dl_{sem_num}_{i}",
            use_container_width=True,
        ):
            show_deadline(dl)

st.caption("Cliquez sur une échéance pour voir le détail : dates, semaine de la grille, et actions à faire.")




# ---------- Grille annuelle détaillée (même style que Rappels / Échéances) ----------
st.markdown("### 📅 Grille annuelle détaillée (S1 → S43)")


def week_type(wk):
    if wk.get("full_holiday") or wk.get("partial_holidays"):
        return "holiday"
    if wk.get("marker"):
        return "exam"
    if wk.get("deadlines"):
        return "critical"
    return "regular"


weeks = grid["weeks"]

# Légende des couleurs
st.markdown(
    '<span class="ca-badge" style="background:#52525b33;color:#d4d4d8;border:1px solid #52525b">📘 Semaine normale</span>'
    '<span class="ca-badge" style="background:#b4530933;color:#fcd34d;border:1px solid #b45309">🌴 Vacances / fête</span>'
    '<span class="ca-badge" style="background:#dc262633;color:#fca5a5;border:1px solid #dc2626">📝 Semaine d\'évaluation</span>'
    '<span class="ca-badge" style="background:#f59e0b33;color:#fde68a;border:1px solid #f59e0b">⚠️ Échéance critique</span>',
    unsafe_allow_html=True,
)

# Bandeau de navigation : une ligne par mois, semaines cliquables
strip = ""
cur_month = None
for wk in weeks:
    if wk["month"] != cur_month:
        if cur_month is not None:
            strip += "</div>"
        cur_month = wk["month"]
        strip += f'<div class="wk-row"><span class="wk-month">{cur_month}</span>'
    t = week_type(wk)
    extra = ""
    if wk.get("marker"):
        extra += "📝"
    if wk.get("deadlines"):
        extra += "⚠️"
    if wk.get("full_holiday") or wk.get("partial_holidays"):
        extra += "🌴"
    strip += (
        f'<a class="wk t-{t}" href="#wk-{wk["week"]}" '
        f'title="Aller à S{wk["week"]} ({wk["start"]} → {wk["end"]})">'
        f'{wk["week"]}{extra}</a>'
    )
strip += "</div>"
st.markdown(strip, unsafe_allow_html=True)
st.caption("Cliquez sur une semaine du bandeau pour aller directement à sa ligne dans la grille.")

# Grille détaillée : une ligne par semaine, cliquable (💬)
cur_month = None
for wk in weeks:
    if wk["month"] != cur_month:
        cur_month = wk["month"]
        st.markdown(f'<div class="wk-month-header">{cur_month}</div>', unsafe_allow_html=True)

    t = week_type(wk)
    seq = wk.get("sequence") or {}
    unit_chip = (
        f'<span class="chip" style="background:{seq.get("color", "#888")}">{seq.get("unit_id")}</span> '
        if seq else ""
    )
    topic = seq.get("topic", "")
    comp = ", ".join(seq.get("competency_codes", [])) if seq.get("competency_codes") else ""
    hours = seq.get("hours", "")

    events = []
    if wk.get("full_holiday"):
        events.append("🌴 " + wk["full_holiday"])
    events += ["🌴 " + p for p in wk.get("partial_holidays", [])]
    if wk.get("deadlines"):
        events.append("⚠️ " + ", ".join(wk["deadlines"]))
    if wk.get("marker"):
        events.append("📝 " + wk["marker"])
    note = (plan.get("weekly_notes") or {}).get(str(wk["week"]), "")
    if note:
        events.append("💬 " + note)

    c1, c2, c3, c4 = st.columns([0.9, 2.6, 1.7, 0.45])
    c1.markdown(
        f'<span id="wk-{wk["week"]}"></span>'
        f'<span class="wk t-{t}" style="cursor:default">{wk["week"]}</span> '
        f'<span class="wk-dates">{wk["start"][5:]} → {wk["end"][5:]}</span>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        f'{unit_chip}<b>{topic}</b>'
        + (f' <span class="wk-comp">· {comp}</span>' if comp else "")
        + (f' <span class="wk-comp">· {hours} h</span>' if hours else ""),
        unsafe_allow_html=True,
    )
    c3.markdown("<br>".join(events) if events else "—", unsafe_allow_html=True)
    if c4.button("💬", key=f"wkbtn_{wk['week']}"):
        week_dialog(wk)

# ---------- Séquences : consulter, commenter, modifier ----------
st.markdown("### 📝 Séquences — consulter, commenter, modifier")

SEQ_SUGGESTIONS = {
    "C0_C31": [
        "Étaler la découverte de l'outil sur plusieurs séances.",
        "Utiliser des schémas illustratifs (constituants, touches du clavier).",
        "Appuyer les notions par des démonstrations pratiques (Montrer → Faire faire → Faire dire).",
        "Éduquer à la préservation du matériel et aux consignes de sécurité.",
    ],
    "C11_C12": [
        "Centrer l'approche sur l'utilisation du logiciel, non sur le logiciel lui-même.",
        "Imposer des textes courts et concrets pour maximiser la manipulation.",
        "Problématiser les activités ; éviter les ateliers purement directifs.",
        "Envisager de petits projets personnels ou d'équipe.",
    ],
    "C13": [
        "Simple initiation : accent sur l'analyse, l'organisation et la rigueur.",
        "Introduire les commandes judicieusement et au besoin.",
        "Inciter les apprenants à déceler leurs erreurs et à les corriger.",
    ],
    "C21_C22_C23": [
        "Appuyer les activités sur des besoins réels de recherche.",
        "Insister sur la méthodologie de recherche d'information.",
        "Apprendre à critiquer les informations trouvées.",
    ],
    "C32_C33": [
        "Inciter chaque apprenant à créer sa propre adresse email.",
        "Pratiquer le travail de groupe et la communication à distance.",
        "Respecter une éthique et des valeurs citoyennes dans l'usage d'Internet.",
    ],
}


def seq_family(code):
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


@st.dialog("🔎 Fiche officielle de la séquence")
def seq_official_dialog(item, comp_map):
    st.markdown(f"### {item.get('unit_id')} — {item.get('topic')}")
    for code in item.get("competency_codes", []):
        comp = comp_map.get(code)
        if not comp:
            continue
        st.markdown(f"**{code} — {comp.get('statement')}**")
        res = comp.get("resources", {})
        c1, c2, c3 = st.columns(3)
        c1.markdown("**Savoirs**\n" + "\n".join(f"- {x}" for x in res.get("savoir", [])) or "—")
        c2.markdown("**Savoir-faire**\n" + "\n".join(f"- {x}" for x in res.get("savoir_faire", [])) or "—")
        c3.markdown("**Savoir-être**\n" + "\n".join(f"- {x}" for x in res.get("savoir_etre", [])) or "—")
        fam = seq_family(code)
        if fam:
            st.info("**Suggestions officielles :**\n" + "\n".join("• " + s for s in SEQ_SUGGESTIONS[fam]))


if not st.session_state.get("annual_plan"):
    st.info("Générez ou chargez d'abord un plan annuel pour consulter ses séquences.")
else:
    plan = st.session_state["annual_plan"]
    items = grid.get("items", []) or plan.get("items", [])

    curriculum_resp = api_get(f"/api/reference/curriculum/{plan.get('level_code')}")
    comp_map = {}
    if curriculum_resp["ok"]:
        for domain in curriculum_resp["data"].get("competency_framework", {}).get("domains_of_action", []):
            for comp in domain.get("competencies", []):
                comp_map[comp.get("code")] = comp

    units = []
    for it in items:
        if it.get("unit_id") not in units:
            units.append(it.get("unit_id"))

    c_unit, c_seq = st.columns([1, 3])
    with c_unit:
        unit_choice = st.selectbox("Unité", units, format_func=lambda u: f"Unité {u}")
    unit_items = [it for it in items if it.get("unit_id") == unit_choice]
    options = [f"S{it.get('week_start')}→S{it.get('week_end')} · {it.get('topic')}" for it in unit_items]
    with c_seq:
        seq_label = st.selectbox("Séquence", options)
    item = unit_items[options.index(seq_label)]

    in_range = []
    for wk in grid.get("weeks", []):
        wnum = wk.get("week")
        if item.get("actual_week_start") and item.get("actual_week_end") and (
            item["actual_week_start"] <= wnum <= item["actual_week_end"]
        ):
            if wk.get("full_holiday") or wk.get("partial_holidays"):
                in_range.append("🌴 " + (wk.get("full_holiday") or ", ".join(wk.get("partial_holidays", []))))
            if wk.get("deadlines"):
                in_range.append("⚠️ " + ", ".join(wk["deadlines"]))
            if wk.get("marker"):
                in_range.append("📝 " + wk["marker"])

    st.markdown(
        f'<span class="chip" style="background:{item.get("color", "#2563eb")}">Unité {item.get("unit_id")}</span> '
        f'<span class="ca-badge info">Semestre {item.get("semester")}</span> '
        f'<span class="ca-badge ok">S{item.get("week_start")}→S{item.get("week_end")}</span> '
        f'<span class="ca-badge warn">{item.get("official_hours")} h officielles</span>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown("#### 📖 Consulter")
        for code in item.get("competency_codes", []):
            comp = comp_map.get(code)
            if comp:
                with st.expander(f"**{code}** — {comp.get('statement')}"):
                    res = comp.get("resources", {})
                    k1, k2, k3 = st.columns(3)
                    k1.markdown("**Savoirs**\n" + "\n".join(f"- {x}" for x in res.get("savoir", [])))
                    k2.markdown("**Savoir-faire**\n" + "\n".join(f"- {x}" for x in res.get("savoir_faire", [])))
                    k3.markdown("**Savoir-être**\n" + "\n".join(f"- {x}" for x in res.get("savoir_etre", [])))
        fams = {seq_family(c) for c in item.get("competency_codes", []) if seq_family(c)}
        if fams:
            sugg = []
            for f in sorted(fams):
                sugg += SEQ_SUGGESTIONS[f]
            st.info("**Suggestions officielles :**\n" + "\n".join("• " + s for s in sugg))
        if in_range:
            st.warning("Dans cette période : " + " · ".join(in_range))
        if st.button("🔎 Fiche officielle complète", use_container_width=True):
            seq_official_dialog(item, comp_map)

    with right:
        st.markdown("#### ✏️ Commenter & modifier")
        iid = item.get("item_id")
        saved_item = next((p for p in plan.get("items", []) if p.get("item_id") == iid), {})
        new_hours = st.number_input(
            "Heures planifiées", 1, 40,
            value=int(item.get("planned_hours", item.get("official_hours", 1))),
            key=f"sq_h_{iid}",
        )
        c_a, c_b = st.columns(2)
        new_ws = c_a.number_input("Sem. début", 1, 43, value=int(item.get("week_start", 1)), key=f"sq_ws_{iid}")
        new_we = c_b.number_input("Sem. fin", 1, 43, value=int(item.get("week_end", 1)), key=f"sq_we_{iid}")
        new_sem = st.selectbox("Semestre", [1, 2], index=0 if item.get("semester") == 1 else 1, key=f"sq_sem_{iid}")
        new_notes = st.text_area(
            "Commentaire de l'enseignant",
            value=saved_item.get("notes", ""),
            height=120,
            key=f"sq_n_{iid}",
        )
        if st.button("💾 Enregistrer", type="primary", use_container_width=True):
            for pi in plan["items"]:
                if pi["item_id"] == iid:
                    pi["planned_hours"] = int(new_hours)
                    pi["week_start"] = int(new_ws)
                    pi["week_end"] = int(new_we)
                    pi["semester"] = int(new_sem)
                    pi["notes"] = new_notes
            r = api_put(f"/api/planning/annual/{plan['annual_plan_id']}", plan)
            if r["ok"]:
                st.session_state["annual_plan"] = plan
                st.success("Séquence enregistrée.")
                st.rerun()
            else:
                st.error(r["error"])
        st.page_link(
            "pages/3_Preparation_Sequence.py",
            label="➡️ Préparer les 3 fiches (Ressources / Intégration / Évaluation)",
            use_container_width=True,
        )


if saved_ids:
    st.dataframe(plans_response["data"].get("plans", []))
