import json
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DS = BASE / "data" / "ai" / "qa_dataset.jsonl"
rows = [json.loads(l) for l in DS.read_text(encoding="utf-8").splitlines() if l.strip()]

WANTED = ["situation", "evaluation", "ressources", "echeances", "differenciation", "calendrier"]
examples, seen = [], set()
for r in rows:
    if r["intent"] in WANTED and r["intent"] not in seen:
        seen.add(r["intent"])
        ans = r["answer"]
        if len(ans) > 450:
            ans = ans[:450].rsplit("\n", 1)[0]
        examples.append((r["question"], ans))
    if len(examples) >= 6:
        break

RULES = (
    "Tu es Collegue AI, collègue numérique d'un enseignant d'informatique au collège marocain "
    "(APC, pédagogie de l'intégration). Réponds en français, 120 mots max, puces courtes, "
    "sans répéter, sans inventer de dates ni de contenus. "
    "Si un CONTEXTE OFFICIEL est fourni, réponds UNIQUEMENT à partir de lui."
)

sys_msg = RULES + "\nEXEMPLES :\n" + "\n".join(f"Q : {q}\nR : {a}" for q, a in examples)

TEMPLATE = (
    "<|im_start|>system\n" + sys_msg + "<|im_end|>\n"
    "{% for message in messages %}"
    "<|im_start|>{{ message.role }}\n{{ message.content }}<|im_end|>\n"
    "{% endfor %}"
    "<|im_start|>assistant\n"
)

mf = BASE / "data" / "ai" / "Modelfile.pedago"
mf.write_text(
    "FROM collegue-qwen:latest\n"
    'TEMPLATE """' + TEMPLATE + '"""\n'
    'PARAMETER stop "<|im_end|>"\n'
    "PARAMETER temperature 0.2\n"
    "PARAMETER num_ctx 4096\n"
    "PARAMETER num_predict 300\n",
    encoding="utf-8",
)

subprocess.run(["ollama", "create", "collegue-pedago", "-f", str(mf)], check=True)
print("OK modele collegue-pedago (ChatML + stop token) cree.")
