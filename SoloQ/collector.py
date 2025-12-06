import os, time, json
from config import OUT_DIR, PATCH_MM, REQ_SLEEP
from utils import safe_write, file_exists
from league_api import sample_one_candidate_entry
from riot_api import get_account_by_puuid, get_summoner_min_by_puuid, get_all_match_ids, get_match, get_timeline

os.makedirs(OUT_DIR, exist_ok=True)

import os, time, json
from config import OUT_DIR, PATCH_MM, REQ_SLEEP
from utils import safe_write, file_exists
from league_api import sample_one_candidate_entry
from riot_api import get_account_by_puuid, get_summoner_min_by_puuid, get_all_match_ids, get_match, get_timeline

os.makedirs(OUT_DIR, exist_ok=True)


def call_with_retries(fn, *args, retries=5, base_sleep=REQ_SLEEP, label="", **kwargs):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            name = label or fn.__name__
            print(f"  [WARN] {name} failed (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(base_sleep * attempt)
    raise last_err


def collect_one_tier(
    tier,
    max_pages_per_player=None,
    min_matches_for_patch=1,
    max_candidates=10,
):
    print(f"\n▶ Collecting {tier}")
    tier_dir = os.path.join(OUT_DIR, tier)
    os.makedirs(os.path.join(tier_dir, "matches"), exist_ok=True)
    os.makedirs(os.path.join(tier_dir, "timelines"), exist_ok=True)

    candidates = sample_one_candidate_entry(tier)
    if not candidates:
        print(f"[WARN] no entries for {tier}")
        return

    candidates = candidates[:max_candidates]

    chosen_entry = None
    chosen_account = None
    chosen_kept = None

    for idx, e in enumerate(candidates, start=1):
        puuid = e["puuid"]
        print(f"\n  → Candidate {idx}/{len(candidates)}: {puuid[:18]}…")

        try:
            acc = call_with_retries(
                get_account_by_puuid,
                puuid,
                retries=5,
                base_sleep=REQ_SLEEP,
                label="get_account_by_puuid",
            )
        except Exception as err:
            print(f"    [SKIP] account lookup failed: {err}")
            continue

        if not (isinstance(acc, dict) and "gameName" in acc):
            print("    [SKIP] invalid account object (no gameName)")
            continue

        game_name = acc.get("gameName")
        tag_line = acc.get("tagLine")
        print(f"    ✓ account: {game_name}#{tag_line}  ({puuid[:18]}…)")

        try:
            summ_min = call_with_retries(
                get_summoner_min_by_puuid,
                puuid,
                retries=5,
                base_sleep=REQ_SLEEP,
                label="get_summoner_min_by_puuid",
            )
            safe_write(os.path.join(tier_dir, f"summoner_min_{puuid[:12]}.json"), summ_min)
            print("    ✓ summoner_min saved")
        except Exception as e:
            print(f"    [WARN] summoner_min failed after retries: {e}")

        try:
            mids = call_with_retries(
                get_all_match_ids,
                puuid,
                max_pages=max_pages_per_player,
                retries=5,
                base_sleep=REQ_SLEEP,
                label="get_all_match_ids",
            )
        except Exception as e:
            print(f"    [SKIP] get_all_match_ids failed: {e}")
            continue

        print(f"    ✓ total matches: {len(mids)}")

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
                m = call_with_retries(
                    get_match,
                    mid,
                    retries=5,
                    base_sleep=REQ_SLEEP,
                    label=f"get_match({mid})",
                )
                gv = str(m.get("info", {}).get("gameVersion", ""))
                time.sleep(REQ_SLEEP)
                if gv.startswith(PATCH_MM):
                    safe_write(mpath, m)
                    kept.append(mid)
                    print(f"      + match saved {mid} ({gv})")
            except Exception as e:
                print(f"      [WARN] match {mid} failed after retries: {e}")

        print(f"    → kept {len(kept)} matches for patch {PATCH_MM}")

        if len(kept) >= min_matches_for_patch:
            chosen_entry = e
            chosen_account = acc
            chosen_kept = kept
            print(f"    ✓ candidate ACCEPTED for tier {tier}")
            break
        else:
            print(f"    [INFO] candidate has insufficient matches for patch {PATCH_MM}, trying next…")

    if not chosen_entry:
        print(f"[ERROR] {tier}: no candidate had >= {min_matches_for_patch} matches in patch {PATCH_MM}")
        return

    safe_write(os.path.join(tier_dir, "league_entry_snapshot.json"), chosen_entry)
    safe_write(os.path.join(tier_dir, "account_info.json"), chosen_account)

    for mid in chosen_kept:
        tlpath = os.path.join(tier_dir, "timelines", f"{mid}_timeline.json")
        if file_exists(tlpath):
            continue
        try:
            tl = call_with_retries(
                get_timeline,
                mid,
                retries=5,
                base_sleep=REQ_SLEEP,
                label=f"get_timeline({mid})",
            )
            safe_write(tlpath, tl)
            print(f"    + timeline saved {mid}")
            time.sleep(REQ_SLEEP)
        except Exception as e:
            print(f"    [WARN] timeline {mid} failed after retries: {e}")

    print(f"✅ Done {tier} → {tier_dir}")

def collect_all_tiers(max_pages_per_player=None):
    # tiers = ["IRON","BRONZE","SILVER","GOLD","PLATINUM","EMERALD",
    #          "DIAMOND","MASTER","GRANDMASTER","CHALLENGER"]
    tiers = ["BRONZE","SILVER","GOLD","PLATINUM","EMERALD",
             "DIAMOND","MASTER","GRANDMASTER"]
    
    for t in tiers:
        try:
            collect_one_tier(t, max_pages_per_player=max_pages_per_player)
        except Exception as e:
            print(f"[ERROR] {t} failed: {e}")
