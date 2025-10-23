import os, json

def safe_write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def file_exists(path):
    return os.path.exists(path) and os.path.getsize(path) > 0
