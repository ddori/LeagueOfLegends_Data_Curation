import time
from config import PLATFORM, REGIONAL, QUEUE_ID, REQ_SLEEP
from http_client import get_json

def get_account_by_puuid(puuid):
    url = f"https://{REGIONAL}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    return get_json(url)

def get_summoner_min_by_puuid(puuid):
    url = f"https://{PLATFORM}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return get_json(url)

def get_all_match_ids(puuid, queue=QUEUE_ID, page_size=100, max_pages=None):
    ids, start, pages = [], 0, 0
    while True:
        params = {"queue": queue, "start": start, "count": page_size}
        url = f"https://{REGIONAL}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        chunk = get_json(url, params=params) or []
        time.sleep(REQ_SLEEP)
        if not chunk:
            break
        ids.extend(chunk)
        start += page_size
        pages += 1
        if max_pages and pages >= max_pages:
            break
    seen, dedup = set(), []
    for m in ids:
        if m not in seen:
            dedup.append(m)
            seen.add(m)
    return dedup

def get_match(mid):
    url = f"https://{REGIONAL}.api.riotgames.com/lol/match/v5/matches/{mid}"
    return get_json(url)

def get_timeline(mid):
    url = f"https://{REGIONAL}.api.riotgames.com/lol/match/v5/matches/{mid}/timeline"
    return get_json(url)
