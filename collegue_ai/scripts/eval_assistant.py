import requests

API = "http://127.0.0.1:8000"

CASES = [
    {"q": "Propose une situation déclenchante pour l'unité U1 (1AC).",
     "need": ["Contexte", "Problème", "U1"], "ban": ["SAP", "restauration"]},
    {"q": "Rédige une évaluation formative de 20 min pour l'unité U2 (1AC).",
     "need": ["20 min", "Critères"], "ban": []},
    {"q": "Quelles ressources officielles pour la compétence C11 ?",
     "need": ["C11", "Savoirs"], "ban": []},
    {"q": "Quand est la saisie des notes Massar du semestre 1 ?",
     "need": ["2027-01"], "ban": []},
    {"q": "Propose des modalités de différenciation en salle informatique.",
     "need": ["binômes"], "ban": []},
]

def score(model):
    tot = 0
    for c in CASES:
        try:
            r = requests.post(
                f"{API}/api/ai/chat",
                json={"message": c["q"], "level": "1AC", "unit": "U1", "model": model},
                timeout=180,
            ).json()
            t = r.get("reply", "")
        except Exception as e:
            print(f"Erreur API pour {model}: {e}")
            t = ""
        miss = [k for k in c["need"] if k.lower() not in t.lower()]
        pen = 1 if any(b.lower() in t.lower() for b in c["ban"]) else 0
        s = max(0.0, (len(c["need"]) - len(miss)) / len(c["need"]) - pen)
        tot += s
        print(f"[{model}] {s:.0%}  {c['q'][:50]}  manque: {miss or 'rien'}")
        print("    ->", " ".join(t.split())[:180])
    print(f"== SCORE {model} : {tot / len(CASES):.0%}\n")

print("Évaluation itération 2 (1-2 minutes)...\n")
for m in ["collegue-qwen:latest", "collegue-pedago"]:
    score(m)
