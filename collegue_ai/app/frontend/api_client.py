import requests

API_BASE = "http://127.0.0.1:8000"


def api_get(path, timeout=15):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=timeout)
        return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_post(path, payload, timeout=30):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_put(path, payload, timeout=30):
    try:
        r = requests.put(f"{API_BASE}{path}", json=payload, timeout=timeout)
        return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}
