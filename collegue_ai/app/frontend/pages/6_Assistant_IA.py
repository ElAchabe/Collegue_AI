import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import theme
from api_client import api_get, api_post, api_put

st.set_page_config(page_title="Collegue AI — Assistant IA", layout="wide")
theme.inject_theme()
theme.render_sidebar()

st.markdown("### 🤖 Assistant IA — collègue numérique")

status = api_get("/api/ai/status")["data"]
settings = api_get("/api/settings")["data"]

# ---------- Status cards ----------
mode_txt = "🟢 IA locale" if status.get("available") else (
    "🟠 IA activée, injoignable" if status.get("enabled") else "⚪ Hors ligne"
)
st.markdown(
    f"""
    <div class="ca-grid">
      <div class="ca-card"><h4>Mode</h4><div class="ca-value" style="font-size:1rem">{mode_txt}</div>
        <div class="ca-sub">Le mode hors ligne répond toujours, même sans modèle.</div></div>
      <div class="ca-card"><h4>Modèle</h4><div class="ca-value" style="font-size:1rem">{status.get('model') or '—'}</div>
        <div class="ca-sub">0.5b sur ce PC • 1.5b/3b conseillés sur le PC 8 Go.</div></div>
      <div class="ca-card"><h4>Contexte injecté</h4><div class="ca-value" style="font-size:1rem">Officiel 2026-2027</div>
        <div class="ca-sub">Curriculum + arrêté 047.26 + pédagogie.</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Settings ----------
with st.expander("⚙️ Gérer le modèle local (Ollama)"):
    enabled = st.toggle("Activer l'assistant IA local", value=bool(settings.get("ai_enabled")))
    base_url = st.text_input("URL Ollama", value=settings.get("ai_base_url", "http://127.0.0.1:11434"))
    models_resp = api_get("/api/ai/models")
    model_list = models_resp["data"].get("models", []) if models_resp["ok"] else []
    current_model = settings.get("ai_model", "collegue-qwen:latest")
    options = sorted(set(model_list + [current_model]))
    model = st.selectbox("Modèle", options, index=options.index(current_model) if current_model in options else 0)
    b1, b2 = st.columns(2)
    if b1.button("💾 Enregistrer", use_container_width=True):
        api_put("/api/settings", {"ai_enabled": enabled, "ai_base_url": base_url, "ai_model": model})
        st.success("Paramètres enregistrés.")
        st.rerun()
    if b2.button("🔌 Tester la connexion", use_container_width=True):
        t = api_get("/api/ai/status")["data"]
        if t.get("available"):
            st.success(f"Ollama joignable — modèle : {t.get('model')}")
        else:
            st.warning("Ollama injoignable. Vérifiez que `ollama serve` tourne.")

# ---------- Context ----------
c1, c2 = st.columns(2)
with c1:
    level = st.selectbox("Niveau (contexte)", ["—", "1AC", "2AC", "3AC"])
with c2:
    unit = st.selectbox("Unité (optionnel)", ["—", "U1", "U2", "U3", "U4", "U5"])

ctx_level = "" if level == "—" else level
ctx_unit = "" if unit == "—" else unit

if ctx_level:
    cur = api_get(f"/api/reference/curriculum/{ctx_level}")
    if cur["ok"]:
        lv = cur["data"].get("curriculum", {})
        chips = " ".join(
            f'<span class="ca-badge info">{c}</span>' for c in lv.get("targeted_competencies", [])
        )
        sub = ""
        if ctx_unit:
            for u in lv.get("units", []):
                if u.get("unit_id") == ctx_unit:
                    sub = f"<div class='ca-sub' style='opacity:1;margin-top:6px'>Unité {ctx_unit} : {u.get('title')} — " + \
                          " ; ".join(s.get("topic", "") for s in u.get("sub_modules", [])) + "</div>"
        st.markdown(f"<div>{chips}</div>{sub}", unsafe_allow_html=True)

# ---------- Quick tasks ----------
st.markdown("#### ⚡ Tâches rapides du collègue")
lvl_txt = f" ({ctx_level})" if ctx_level else ""
unit_txt = f" pour l'unité {ctx_unit}" if ctx_unit else ""
tasks = [
    ("💥 Situation déclenchante", f"Propose une situation déclenchante{unit_txt}{lvl_txt}."),
    ("📝 Évaluation formative 20 min", f"Rédige une évaluation formative de 20 min{unit_txt}{lvl_txt}."),
    ("🎯 Ressources officielles", f"Donne les ressources officielles des compétences{unit_txt}{lvl_txt}."),
    ("🧑‍🏫 Différenciation", "Propose des modalités de différenciation et de gestion des binômes en salle informatique."),
    ("⏰ Prochaines échéances", "Quelles sont les 3 prochaines échéances officielles ?"),
]
cols = st.columns(len(tasks))
for col, (label, prompt_txt) in zip(cols, tasks):
    with col:
        if st.button(label, use_container_width=True):
            st.session_state["pending_question"] = prompt_txt

if st.button("🗑️ Effacer la conversation"):
    st.session_state["chat"] = []
    st.rerun()

# ---------- Chat ----------
if "chat" not in st.session_state:
    st.session_state["chat"] = []

for msg in st.session_state["chat"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Posez votre question…")
question = prompt or st.session_state.pop("pending_question", None)

if question:
    st.session_state["chat"].append({"role": "user", "content": question})
    history = st.session_state["chat"][:-1][-6:]
    r = api_post("/api/ai/chat", {"message": question, "level": ctx_level, "unit": ctx_unit, "history": history},
        timeout=180
    )
    if r["ok"]:
        src = r["data"].get("source")
        badge = {"ollama": "🟢 IA locale (guidée)", "error": "⚠️ Erreur modèle"}.get(src, "⚪ Hors ligne (officiel)")
        st.session_state["chat"].append(
            {"role": "assistant", "content": f"**[{badge}]** {r['data'].get('reply', '')}"}
        )
    else:
        st.session_state["chat"].append({"role": "assistant", "content": "⚠️ Service momentanément indisponible."})
    st.rerun()
