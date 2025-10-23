import time, requests
from config import HEAD

def get_json(url, params=None, retry=3):
    for t in range(retry):
        r = requests.get(url, headers=HEAD, params=params, timeout=20)
        if r.status_code == 429:
            ra = int(r.headers.get("Retry-After", "2"))
            time.sleep(ra + 1)
            continue
        try:
            data = r.json()
        except Exception:
            data = None
        if r.ok and not (isinstance(data, dict) and "status" in data):
            return data
        msg = data.get("status", {}).get("message") if isinstance(data, dict) else r.text
        code = data.get("status", {}).get("status_code") if isinstance(data, dict) else r.status_code
        if t < retry - 1 and code in (500,502,503,504,403,404):
            time.sleep(1.5 * (t + 1))
            continue
        raise RuntimeError(f"HTTP {code} @ {url} :: {msg}")
