# SoloQ/parse.py
import os, json, re
import pandas as pd

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_ARROW = True
except Exception:
    HAS_ARROW = False


def sanitize_key(key: str) -> str:
    return re.sub(r"[^0-9a-zA-Z_]+", "_", key).strip("_")


def flatten_dict(d, prefix=""):
    out = {}
    if not isinstance(d, dict):
        return out
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten_dict(v, key))
        elif isinstance(v, list):
            if all(isinstance(x, dict) for x in v):
                for i, x in enumerate(v):
                    out.update(flatten_dict(x, f"{key}[{i}]"))
            else:
                out[key] = ",".join(map(str, v))
        else:
            out[key] = v
    return out


def parse_perks(perks):
    out = {}
    if not perks:
        return out
    stat = perks.get("statPerks", {})
    out["perks_statDefense"] = stat.get("defense")
    out["perks_statFlex"] = stat.get("flex")
    out["perks_statOffense"] = stat.get("offense")
    for s in perks.get("styles", []):
        desc = s.get("description", "")
        style_id = s.get("style")
        out[f"perks_{desc}_styleId"] = style_id
        for i, sel in enumerate(s.get("selections", [])):
            for var in ["perk", "var1", "var2", "var3"]:
                out[f"perks_{desc}_{i}_{var}"] = sel.get(var)
    return out


def parse_team_info(team):
    out = {"team_teamId": team.get("teamId"), "team_win": team.get("win")}
    for obj, val in (team.get("objectives") or {}).items():
        out[f"team_obj_{obj}_first"] = val.get("first")
        out[f"team_obj_{obj}_kills"] = val.get("kills")
    for i, b in enumerate(team.get("bans", [])):
        out[f"team_ban_{i}_championId"] = b.get("championId")
        out[f"team_ban_{i}_pickTurn"] = b.get("pickTurn")
    return out


def kda(k, d, a):
    if not d:
        return (k or 0) + (a or 0)
    return ((k or 0) + (a or 0)) / (d or 1)


def parse_one_json(tier, data):
    info = data.get("info", {})
    meta = data.get("metadata", {})
    match_id = meta.get("matchId")

    teams = {t["teamId"]: parse_team_info(t) for t in info.get("teams", [])}
    rows = []
    duration = info.get("gameDuration", 1)
    dur_min = duration / 60.0

    for p in info.get("participants", []):
        row = {
            "tier": tier,
            "matchId": match_id,
            "gameVersion": info.get("gameVersion"),
            "queueId": info.get("queueId"),
            "mapId": info.get("mapId"),
            "gameMode": info.get("gameMode"),
            "gameDuration": duration,
            "summonerName": p.get("summonerName"),
            "championName": p.get("championName"),
            "teamPosition": p.get("teamPosition"),
            "lane": p.get("lane"),
            "kills": p.get("kills"),
            "deaths": p.get("deaths"),
            "assists": p.get("assists"),
            "win": p.get("win"),
            "goldEarned": p.get("goldEarned"),
            "totalDamageDealtToChampions": p.get("totalDamageDealtToChampions"),
            "totalMinionsKilled": p.get("totalMinionsKilled"),
            "neutralMinionsKilled": p.get("neutralMinionsKilled"),
        }

        dur = dur_min if dur_min > 0 else 1
        row["gpm"] = (p.get("goldEarned", 0) or 0) / dur
        row["dpm"] = (p.get("totalDamageDealtToChampions", 0) or 0) / dur
        cs = (p.get("totalMinionsKilled", 0) or 0) + (p.get("neutralMinionsKilled", 0) or 0)
        row["cspm"] = cs / dur
        row["kda"] = kda(p.get("kills", 0), p.get("deaths", 0), p.get("assists", 0))

        for ck, cv in (p.get("challenges") or {}).items():
            row[f"ch_{sanitize_key(str(ck))}"] = cv
        row.update(parse_perks(p.get("perks")))
        for k, v in teams.get(p.get("teamId"), {}).items():
            row[k] = v

        flat = flatten_dict(p)
        for k, v in flat.items():
            if k not in row:
                row[sanitize_key(k)] = v
        rows.append(row)
    return rows


def build_dataframe(base_dir):
    all_rows = []
    for tier in os.listdir(base_dir):
        matches_dir = os.path.join(base_dir, tier, "matches")
        if not os.path.isdir(matches_dir):
            continue
        for fn in os.listdir(matches_dir):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(matches_dir, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                all_rows.extend(parse_one_json(tier, data))
            except Exception as e:
                print(f"{fp}: {e}")
    df = pd.DataFrame(all_rows)
    df.columns = [sanitize_key(c) for c in df.columns]
    return df


def save_outputs(df, patch_tag):
    os.makedirs("data", exist_ok=True)
    csv_path = f"data/soloq_full_{patch_tag}.csv"
    parquet_path = f"data/soloq_full_{patch_tag}.parquet"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"CSV saved: {csv_path}")

    if HAS_ARROW:
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, parquet_path, compression="snappy")
        print(f"Parquet saved: {parquet_path}")
    else:
        print("pyarrow not installed, skipped Parquet.")


if __name__ == "__main__":
    # 자동 탐지: output_*_by_tier
    base_candidates = [d for d in os.listdir(".") if d.startswith("output_") and d.endswith("_by_tier")]
    if not base_candidates:
        raise FileNotFoundError("No 'output_*_by_tier' folder found in current directory.")
    base_dir = base_candidates[0]
    patch_tag = base_dir.replace("output_", "").replace("_by_tier", "")
    print(f"🔍 Detected base_dir={base_dir} (PATCH={patch_tag})")

    df = build_dataframe(base_dir)
    print(f"DataFrame shape: {df.shape}")
    save_outputs(df, patch_tag)
