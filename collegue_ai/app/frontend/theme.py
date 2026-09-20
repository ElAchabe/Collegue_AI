import streamlit as st
from datetime import date

from api_client import api_get

CUSTOM_CSS = """
<style>
.ca-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:12px 0}
.ca-card{background:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.25);border-radius:16px;padding:16px}
.ca-card h4{margin:0 0 8px;font-size:.95rem;opacity:.8}
.ca-value{font-size:1.35rem;font-weight:700}
.ca-sub{opacity:.7;font-size:.85rem;margin-top:4px}
.ca-bar{background:rgba(128,128,128,0.2);border-radius:999px;height:12px;overflow:hidden;margin-top:8px}
.ca-bar>div{background:#2563eb;height:12px;border-radius:999px}
.ca-badge{display:inline-block;padding:4px 10px;border-radius:999px;font-size:.8rem;font-weight:600;margin:2px}
.ok{background:#dcfce7;color:#14532d}
.warn{background:#fef3c7;color:#92400e}
.late{background:#fee2e2;color:#7f1d1d}
.info{background:#dbeafe;color:#1e3a8a}
.ca-table{width:100%;border-collapse:collapse;margin:12px 0;font-size:.9rem}
.ca-table th,.ca-table td{border:1px solid rgba(128,128,128,0.3);padding:8px 10px;text-align:left;vertical-align:top}
.ca-table th{background:rgba(128,128,128,0.12)}
.ca-table tr.holiday td{background:rgba(217,119,6,0.12)}
.ca-table tr.monthrow td{background:rgba(37,99,235,0.12);font-weight:700}
.ca-table tr.marker td{background:rgba(220,38,38,0.10)}
.chip{display:inline-block;padding:2px 10px;border-radius:999px;color:#fff;font-size:.78rem;font-weight:600}
.gantt{display:flex;gap:2px;flex-wrap:wrap;margin:12px 0}
.gcell{width:22px;height:34px;border-radius:6px;background:rgba(128,128,128,0.15);display:flex;align-items:center;justify-content:center;font-size:.68rem}
.gcell.holiday{background:repeating-linear-gradient(45deg,rgba(217,119,6,.5) 0 4px,transparent 4px 8px)}
@media (max-width:640px){.ca-value{font-size:1.1rem}.gcell{width:16px;height:26px}}
div[data-testid="stPopover"]{width:100%}
div[data-testid="stPopover"] button{width:100%;text-align:left;white-space:normal;height:auto;padding:12px 14px;border-radius:14px}
/* === Badges des rappels officiels === */
.tip-badge{
  display:block;
  width:fit-content;
  margin:0 auto 4px auto;
  padding:4px 16px;
  border-radius:999px;
  font-size:.72rem;
  font-weight:800;
  text-transform:uppercase;
  letter-spacing:.1em;
  text-align:center;
}
.tip-badge.ok{background:rgba(34,197,94,.16);color:#4ade80;border:1px solid rgba(34,197,94,.55);}
.tip-badge.info{background:rgba(59,130,246,.16);color:#93c5fd;border:1px solid rgba(59,130,246,.55);}
.tip-badge.warn{background:rgba(245,158,11,.16);color:#fcd34d;border:1px solid rgba(245,158,11,.55);}
.tip-badge.late{background:rgba(239,68,68,.16);color:#fca5a5;border:1px solid rgba(239,68,68,.55);}

/* === UNE SEULE CARTE : le badge + le titre dans le même rectangle === */
div[data-testid="stColumn"]:has(.tip-badge){
  border:1px solid rgba(128,128,128,.35);
  border-radius:14px;
  padding:12px 10px 6px 10px;
  background:rgba(128,128,128,.06);
}
div[data-testid="stColumn"]:has(.tip-badge):hover{
  border-color:rgba(37,99,235,.65);
}
/* Le bouton popup devient transparent : il fusionne avec la carte */
div[data-testid="stColumn"]:has(.tip-badge) div[data-testid="stPopover"] > button{
  border:none;
  background:transparent;
  box-shadow:none;
  justify-content:center;
  text-align:center;
}
div[data-testid="stColumn"]:has(.tip-badge) div[data-testid="stPopover"] > button:hover{
  background:rgba(37,99,235,.12);
  border-radius:10px;
}

/* === Grille annuelle : bandeau + lignes === */
.wk-row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0}
.wk-month{min-width:92px;font-weight:800;opacity:.75;font-size:.75rem;text-transform:uppercase;letter-spacing:.06em}
.wk{display:inline-flex;align-items:center;justify-content:center;min-width:44px;height:34px;padding:0 8px;border-radius:9px;font-size:.82rem;font-weight:800;text-decoration:none;color:#fff}
.wk.t-regular{background:#52525b}
.wk.t-holiday{background:repeating-linear-gradient(45deg,#b45309 0 5px,#78350f 5px 10px)}
.wk.t-exam{background:#dc2626}
.wk.t-critical{background:#f59e0b;color:#111}
.wk-dates{opacity:.65;font-size:.78rem}
.wk-month-header{margin:14px 0 6px 0;font-weight:800;font-size:.85rem;text-transform:uppercase;letter-spacing:.08em;opacity:.85;border-bottom:1px solid rgba(128,128,128,.3);padding-bottom:4px}
.wk-comp{opacity:.7;font-size:.78rem}
@media (max-width:640px){.wk{min-width:34px;height:28px;font-size:.72rem}}

/* === Actions rapides : grandes cartes cliquables avec grandes icônes === */
.ca-action{display:flex;flex-direction:column;gap:6px;text-decoration:none;color:inherit;
  transition:transform .12s ease, border-color .12s ease}
.ca-action:hover{transform:translateY(-2px);border-color:rgba(37,99,235,.65)}
.ca-action-icon{font-size:2.2rem;line-height:1}

</style>
"""


def inject_theme():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("## 🧑‍ Collegue AI")
        st.caption("Assistant de planification hors ligne — v0.6")

        status = api_get("/api/ai/status")
        if status["ok"] and status["data"].get("available"):
            st.success("Assistant IA : en ligne")
        elif status["ok"] and status["data"].get("enabled"):
            st.warning("Assistant IA : activé mais indisponible")
        else:
            st.info("Assistant IA : désactivé (mode hors ligne)")

        st.caption(f"Nous sommes le {date.today().isoformat()}")
        st.divider()
