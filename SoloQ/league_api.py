import time, random
from config import PLATFORM, DIVS, LOWER_TIERS, REQ_SLEEP
from http_client import get_json

def get_entries_lower_tier(tier, pages=3):
    pool = []
    for div in DIVS:
        for page in range(1, pages + 1):
            url = f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/{tier}/{div}"
            data = get_json(url, params={"page": page})
            time.sleep(REQ_SLEEP)
            pool.extend([e for e in data if "puuid" in e])
    return pool

def get_entries_top_tier(tier):
    path = {
        "MASTER": "masterleagues/by-queue",
        "GRANDMASTER": "grandmasterleagues/by-queue",
        "CHALLENGER": "challengerleagues/by-queue",
    }[tier]
    url = f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/{path}/RANKED_SOLO_5x5"
    data = get_json(url)
    time.sleep(REQ_SLEEP)
    return [e for e in data.get("entries", []) if "puuid" in e]

def sample_one_candidate_entry(tier, candidate_cap=50):
    entries = get_entries_lower_tier(tier) if tier in LOWER_TIERS else get_entries_top_tier(tier)
    random.shuffle(entries)
    return entries[:candidate_cap]
