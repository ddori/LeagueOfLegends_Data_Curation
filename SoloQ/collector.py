import os, time, json
from config import OUT_DIR, PATCH_MM, REQ_SLEEP
from utils import safe_write, file_exists
from league_api import sample_one_candidate_entry
from riot_api import get_account_by_puuid, get_summoner_min_by_puuid, get_all_match_ids, get_match, get_timeline

os.makedirs(OUT_DIR, exist_ok=True)

def collect_one_tier(tier, max_pages_per_player=None):
    print(f"\n▶ Collecting {tier}")
    tier_dir = os.path.join(OUT_DIR, tier)
    os.makedirs(os.path.join(tier_dir, "matches"), exist_ok=True)
    os.makedirs(os.path.join(tier_dir, "timelines"), exist_ok=True)

    candidates = sample_one_candidate_entry(tier)
    if not candidates:
        print(f"[WARN] no entries for {tier}")
        return

    chosen = None
    for e in candidates:
        puuid = e["puuid"]
        try:
            acc = get_account_by_puuid(puuid)
            if isinstance(acc, dict) and "gameName" in acc:
                chosen = (e, acc)
                break
        except Exception as err:
            print(f"  candidate skipped ({puuid[:16]}…): {err}")
            continue
        finally:
            time.sleep(REQ_SLEEP)

    if not chosen:
        print(f"[ERROR] {tier}: no usable candidate")
        return

    entry, account = chosen
    puuid = entry["puuid"]
    print(f"  ✓ chosen: {account.get('gameName')}#{account.get('tagLine')}  ({puuid[:18]}…)")

    safe_write(os.path.join(tier_dir, "league_entry_snapshot.json"), entry)
    safe_write(os.path.join(tier_dir, "account_info.json"), account)

    try:
        summ_min = get_summoner_min_by_puuid(puuid)
        safe_write(os.path.join(tier_dir, "summoner_min.json"), summ_min)
        print("  ✓ summoner_min saved")
    except Exception as e:
        print(f"  [WARN] summoner_min failed: {e}")

    mids = get_all_match_ids(puuid, max_pages=max_pages_per_player)
    print(f"  ✓ total matches: {len(mids)}")

    kept = []
    for mid in mids:
        mpath = os.path.join(tier_dir, "matches", f"{mid}.json")
        if file_exists(mpath):
            try:
                with open(mpath, "r", encoding="utf-8") as f:
                    m = json.load(f)
                gv = str(m.get("info", {}).get("gameVersion", ""))
                if gv.startswith(PATCH_MM):
                    kept.append(mid)
            except Exception:
                pass
            continue
        try:
            m = get_match(mid)
            gv = str(m.get("info", {}).get("gameVersion", ""))
            time.sleep(REQ_SLEEP)
            if gv.startswith(PATCH_MM):
                safe_write(mpath, m)
                kept.append(mid)
                print(f"    + match saved {mid} ({gv})")
        except Exception as e:
            print(f"    [WARN] match {mid} failed: {e}")

    print(f"  ✓ kept {len(kept)} matches for patch {PATCH_MM}")

    for mid in kept:
        tlpath = os.path.join(tier_dir, "timelines", f"{mid}_timeline.json")
        if file_exists(tlpath):
            continue
        try:
            tl = get_timeline(mid)
            safe_write(tlpath, tl)
            print(f"    + timeline saved {mid}")
            time.sleep(REQ_SLEEP)
        except Exception as e:
            print(f"    [WARN] timeline {mid} failed: {e}")

    print(f"✅ Done {tier} → {tier_dir}")

def collect_all_tiers(max_pages_per_player=None):
    tiers = ["IRON","BRONZE","SILVER","GOLD","PLATINUM","EMERALD","DIAMOND","MASTER","GRANDMASTER","CHALLENGER"]
    for t in tiers:
        try:
            collect_one_tier(t, max_pages_per_player=max_pages_per_player)
        except Exception as e:
            print(f"[ERROR] {t} failed: {e}")
