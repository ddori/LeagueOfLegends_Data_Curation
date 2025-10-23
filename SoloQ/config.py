import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = (os.getenv("RIOT_API_KEY") or "").strip()
PLATFORM = "kr"
REGIONAL = "asia"
HEAD = {"X-Riot-Token": API_KEY}
QUEUE_ID = 420
REQ_SLEEP = 0.7
PATCH_MM = "15.20"
OUT_DIR = "output_1520_by_tier"

LOWER_TIERS = ["IRON","BRONZE","SILVER","GOLD","PLATINUM","EMERALD","DIAMOND"]
DIVS = ["I","II","III","IV"]
