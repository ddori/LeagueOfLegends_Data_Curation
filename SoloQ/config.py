# config.py
import os

API_KEY = os.getenv("RIOT_API_KEY", "").strip()
if not API_KEY:
    raise ValueError("RIOT_API_KEY not set. Provide it via workflow input.")

PLATFORM = "kr"
REGIONAL = "asia"
HEAD = {"X-Riot-Token": API_KEY}
QUEUE_ID = 420
REQ_SLEEP = 0.7
PATCH_MM = "15.24" 
OUT_DIR = f"./output_{PATCH_MM}_by_tier"

LOWER_TIERS = ["IRON","BRONZE","SILVER","GOLD","PLATINUM","EMERALD","DIAMOND"]
DIVS = ["I","II","III","IV"]
