import json
import math
import re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REF = BASE / "data" / "reference"
OUT = BASE / "data" / "ai"
OUT.mkdir(parents=True, exist_ok=True)

STOP = set("le la les un une des de du et ou a à dans pour sur avec sans est sont été être avoir fait faire ce cette ces se sa son ses au aux en ne pas plus moins très très".split())

def tokenize(text):
    return re.findall(r"[a-zàâçéèêëîïôûùüÿñæœ0-9]+", str(text).lower())

def norm(tokens):
    return [t for t in tokens if t not in STOP and len(t) > 2]

chunks = []
def add_chunk(source, title, text):
    t = " ".join(str(text).split())
    if len(t) > 40:
        chunks.append({"source": source, "title": title, "text": t[:900]})

# 1) Competency framework (orientations pédagogiques officielles)
cur = json.loads((REF / "curriculum_clean.json").read_text(encoding="utf-8"))
for d in cur.get("competency_framework", {}).get("domains_of_action", []):
    for c in d.get("competencies", []):
        res = c.get("resources", {})
        add_chunk("curriculum", f"{c.get('code')} — {c.get('statement')}",
                  f"Compétence {c.get('code')} : {c.get('statement')}. "
                  f"Savoirs : {', '.join(res.get('savoir', []))}. "
                  f"Savoir-faire : {', '.join(res.get('savoir_faire', []))}. "
                  f"Savoir-être : {', '.join(res.get('savoir_etre', []))}.")
for lvl, lv in cur.get("didactic_programs_by_level", {}).items():
    for u in lv.get("units", []):
        for sm in u.get("sub_modules", []):
            add_chunk("curriculum", f"{lvl} {u.get('unit_id')} — {sm.get('topic')}",
                      f"Niveau {lvl}, unité {u.get('unit_id')} : {sm.get('topic')} "
                      f"({sm.get('allocated_hours')} h, compétences {', '.join(sm.get('competency_codes', []))}).")

# 2) Pédagogie (moments, évaluations, conseils)
ped = json.loads((REF / "pedagogy_clean.json").read_text(encoding="utf-8"))
def walk(obj, path="pedagogy"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, path)
    elif isinstance(obj, str):
        add_chunk("pedagogy", path.split("/")[-1], f"{path}: {obj}")
walk(ped)

# 3) Calendrier (échéances officielles)
cal = json.loads((REF / "calendar_clean.json").read_text(encoding="utf-8"))
for h in cal.get("official_holidays", []):
    add_chunk("calendrier", h.get("name", ""), f"{h.get('name')} du {h.get('start_date')} au {h.get('end_date')}.")
for sem_key, sem in cal.get("middle_school_assessment_schedule", {}).items():
    for k, v in sem.items():
        add_chunk("calendrier", k, f"{sem_key}: {k} = {v}")

# --- TF-IDF index ---
docs = [norm(tokenize(c["text"])) for c in chunks]
df = Counter()
for d in docs:
    df.update(set(d))
N = len(docs)
idf = {t: math.log((N + 1) / (n + 1)) + 1 for t, n in df.items()}

index = []
for c, d in zip(chunks, docs):
    tf = Counter(d)
    vec = {t: (n / max(1, len(d))) * idf.get(t, 1) for t, n in tf.items()}
    norm2 = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    index.append({"source": c["source"], "title": c["title"], "text": c["text"],
                  "vec": {t: round(v / norm2, 5) for t, v in vec.items()}})

(OUT / "rag_index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
print(f"OK index RAG : {len(index)} chunks -> data/ai/rag_index.json")
