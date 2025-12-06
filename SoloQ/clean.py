# soloq/clean.py
import os
import re
import json
import pandas as pd
from config import PATCH_MM  

RAW_DIR = "data"
OUT_DIR = "data"
LANE_DIFF_PREFIX = "soloq_lane_diffs"  
TARGET_MS = 600_000 



def normalize_patch(version: str) -> str:
    if not isinstance(version, str):
        return None
    m = re.match(r"(\d+)\.(\d+)", str(version))
    if not m:
        return None
    major, minor = m.groups()
    return f"{int(major)}.{int(minor)}"



def detect_soloq_base_dir() -> str:
    cands = [d for d in os.listdir(".")
             if d.startswith("output_") and d.endswith("_by_tier") and os.path.isdir(d)]
    if not cands:
        raise FileNotFoundError("No 'output_*_by_tier' folder found in current directory.")
    return cands[0]


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_frame_at_10min(timeline: dict) -> dict | None:
    frames = timeline.get("info", {}).get("frames", [])
    if not frames:
        return None
    cands = [fr for fr in frames if fr.get("timestamp", 0) >= TARGET_MS]
    if cands:
        return cands[0]
    return frames[-1]


def lane_key(team_position: str | None) -> str:
    if not team_position:
        return "UNKNOWN"
    t = str(team_position).upper()
    if t in {"TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"}:
        return t
    return "UNKNOWN"


def collect_lane_diffs_for_match(match_path: str, timeline_path: str):
    m = load_json(match_path)
    t = load_json(timeline_path)

    info = m.get("info", {})
    parts = info.get("participants", [])
    frame = pick_frame_at_10min(t)
    if frame is None:
        return []

    pframes = frame.get("participantFrames", {})

    rows = []
    for p in parts:
        pid = p.get("participantId")
        team_id = p.get("teamId")
        pos = lane_key(p.get("teamPosition"))
        key = str(pid)

        pf = pframes.get(key)
        if not pf:
            continue

        gold10 = pf.get("totalGold", 0) or 0
        xp10 = pf.get("xp", 0) or 0
        cs10 = (pf.get("minionsKilled", 0) or 0) + (pf.get("jungleMinionsKilled", 0) or 0)

        rows.append({
            "matchId": m.get("metadata", {}).get("matchId"),
            "participantId": int(pid),
            "teamId": int(team_id),
            "role_key": pos,
            "gold10": float(gold10),
            "xp10": float(xp10),
            "cs10": float(cs10),
        })

    if not rows:
        return []

    df = pd.DataFrame(rows)

    out = []
    for match_id, g_match in df.groupby("matchId"):
        for role, g_role in g_match.groupby("role_key"):
            if role == "UNKNOWN":
                continue

            by_team = {}
            for team_id, g_team in g_role.groupby("teamId"):
                g_team_sorted = g_team.sort_values("gold10", ascending=False)
                by_team[team_id] = g_team_sorted.iloc[0]

            if len(by_team) != 2:
                continue

            teams = list(by_team.keys())
            a = by_team[teams[0]]
            b = by_team[teams[1]]

            # a 기준
            out.append({
                "matchId": match_id,
                "participantId": int(a["participantId"]),
                "gold_diff_10": float(a["gold10"] - b["gold10"]),
                "xp_diff_10": float(a["xp10"] - b["xp10"]),
                "cs_diff_10": float(a["cs10"] - b["cs10"]),
            })
            # b 기준
            out.append({
                "matchId": match_id,
                "participantId": int(b["participantId"]),
                "gold_diff_10": float(b["gold10"] - a["gold10"]),
                "xp_diff_10": float(b["xp10"] - a["xp10"]),
                "cs_diff_10": float(b["cs10"] - a["cs10"]),
            })

    return out


def build_lane_diff_table(base_dir: str, patch_mm: str | None = None) -> pd.DataFrame:
    all_rows = []
    for tier in os.listdir(base_dir):
        tier_dir = os.path.join(base_dir, tier)
        match_dir = os.path.join(tier_dir, "matches")
        tl_dir = os.path.join(tier_dir, "timelines")
        if not (os.path.isdir(match_dir) and os.path.isdir(tl_dir)):
            continue

        for fn in os.listdir(match_dir):
            if not fn.endswith(".json"):
                continue
            match_path = os.path.join(match_dir, fn)
            mid = fn[:-5]
            tl_path = os.path.join(tl_dir, f"{mid}_timeline.json")
            if not os.path.exists(tl_path):
                continue

            try:
                # patch 필터: gameVersion에서 major.minor만 비교
                if patch_mm is not None:
                    m = load_json(match_path)
                    gv = str(m.get("info", {}).get("gameVersion", ""))
                    patch = normalize_patch(gv)
                    if patch != patch_mm:
                        continue

                rows = collect_lane_diffs_for_match(match_path, tl_path)
                all_rows.extend(rows)
            except Exception as e:
                print(f"[WARN] lane diff failed for {mid}: {e}")

    df = pd.DataFrame(all_rows)
    return df


# -------------------------------
# 2. SoloQ clean
# -------------------------------

def clean_soloq_df(df: pd.DataFrame, patch_mm: str | None = None) -> pd.DataFrame:
    df = df.copy()

    # 1) 리메이크 / 잘못된 매치 제거
    if "gameDuration" in df.columns:
        before = len(df)
        df = df[df["gameDuration"] >= 300]
        print(f"[INFO] gameDuration >= 300s: {before} -> {len(df)}")

    # 2) 모드 / 맵 / 큐 필터
    if "gameMode" in df.columns:
        before = len(df)
        df = df[df["gameMode"] == "CLASSIC"]
        print(f"[INFO] gameMode == CLASSIC: {before} -> {len(df)}")

    if "mapId" in df.columns:
        before = len(df)
        df = df[df["mapId"] == 11]
        print(f"[INFO] mapId == 11: {before} -> {len(df)}")

    if "queueId" in df.columns:
        before = len(df)
        df = df[df["queueId"] == 420]
        print(f"[INFO] queueId == 420: {before} -> {len(df)}")

    # 3) patch 정규화 + 필터
    if "gameVersion" in df.columns:
        df["patch"] = df["gameVersion"].astype(str).apply(normalize_patch)

    if patch_mm is not None and "patch" in df.columns:
        before = len(df)
        df = df[df["patch"] == patch_mm]
        print(f"[INFO] patch == {patch_mm}: {before} -> {len(df)}")

    # 4) PII 제거
    pii_candidates = [
        "puuid",
        "summonerName",
        "summonerID",
        "summonerId",
        "riotIdGameName",
        "riotIdTagline",
        "accountId",
    ]
    drop_pii = [c for c in df.columns
                if c in pii_candidates or c.lower() in ["puuid", "summonername", "riotid"]]
    if drop_pii:
        print(f"[INFO] dropping PII columns: {drop_pii}")
        df = df.drop(columns=drop_pii, errors="ignore")

    # 5) visionScore dtype 정리
    if "visionScore" in df.columns:
        df["visionScore"] = pd.to_numeric(df["visionScore"], errors="coerce")

    # 6) 역할 표준화 → role
    if "teamPosition" in df.columns:
        df["role"] = (
            df["teamPosition"]
            .fillna("")
            .astype(str)
            .str.upper()
            .replace({
                "TOP": "TOP",
                "JUNGLE": "JUNGLE",
                "MIDDLE": "MID",
                "MID": "MID",
                "BOTTOM": "BOT",
                "ADC": "BOT",
                "UTILITY": "SUPPORT",
                "SUPPORT": "SUPPORT",
            })
        )

    # 7) lane diff가 들어왔으면 lane_pressure_index 계산
    if {"gold_diff_10", "xp_diff_10", "cs_diff_10"}.issubset(df.columns):
        df["lane_pressure_index"] = (
            df["gold_diff_10"].fillna(0)
            + df["xp_diff_10"].fillna(0)
            + df["cs_diff_10"].fillna(0)
        ) / 3.0

    # 8) unified 스키마/metric 계산에 필요한 컬럼만 남기기
    columns_keep = [
        # 식별/메타
        "tier",
        "role",
        "patch",
        "matchId",
        "participantId",   # lane diff merge용
        "team_teamId",
        "gameDuration",

        # 기본 전투/경제
        "kills",
        "deaths",
        "assists",
        "kda",
        "goldEarned",
        "gpm",
        "totalDamageDealtToChampions",
        "dpm",
        "totalMinionsKilled",
        "neutralMinionsKilled",
        "cspm",

        # 시야
        "visionScore",
        "wardsPlaced",
        "wardsKilled",

        # 팀 오브젝트
        "team_obj_dragon_kills",
        "team_obj_baron_kills",
        "team_obj_tower_kills",

        # 라인전 관련
        "gold_diff_10",
        "xp_diff_10",
        "cs_diff_10",
        "lane_pressure_index",
    ]

    existing = [c for c in columns_keep if c in df.columns]
    missing = [c for c in columns_keep if c not in df.columns]
    if missing:
        print(f"[INFO] missing columns (ignored): {missing}")

    df = df[existing]
    print(f"[INFO] columns after drop: {len(existing)}")

    return df


# -------------------------------
# 3. main: lane diff + clean
# -------------------------------

def main(patch_mm: str | None = None):
    if patch_mm is None:
        patch_mm = PATCH_MM

    patch_tag = patch_mm
    in_path = os.path.join(RAW_DIR, f"soloq_full_{patch_tag}.csv")
    out_path = os.path.join(OUT_DIR, f"soloq_clean_{patch_tag}.csv")
    lane_path = os.path.join(OUT_DIR, f"{LANE_DIFF_PREFIX}_{patch_tag}.csv")

    if not os.path.exists(in_path):
        raise FileNotFoundError(in_path)

    # 1) lane diff 테이블 생성 (없으면)
    if not os.path.exists(lane_path):
        base_dir = detect_soloq_base_dir()
        print(f"[INFO] building lane diff table from: {base_dir}")
        lane_df = build_lane_diff_table(base_dir, patch_mm=patch_mm)
        print("[INFO] lane diff shape:", lane_df.shape)
        lane_df.to_csv(lane_path, index=False)
        print(f"[INFO] saved lane diffs → {lane_path}")
    else:
        print(f"[INFO] loading lane diffs from: {lane_path}")
        lane_df = pd.read_csv(lane_path)

    # 2) raw soloq CSV 로드
    print(f"[INFO] loading raw soloq: {in_path}")
    df_raw = pd.read_csv(in_path)
    print("[INFO] raw shape:", df_raw.shape)

    # 3) lane diff merge (matchId + participantId 기준)
    if {"matchId", "participantId"}.issubset(df_raw.columns):
        df_raw = df_raw.merge(
            lane_df,
            how="left",
            on=["matchId", "participantId"],
        )
        print("[INFO] after merging lane diffs:", df_raw.shape)
    else:
        print("[WARN] matchId/participantId not found in raw soloq; lane diffs not merged")

    # 4) clean
    df_clean = clean_soloq_df(df_raw, patch_mm=patch_mm)
    print("[INFO] cleaned shape:", df_clean.shape)

    df_clean.to_csv(out_path, index=False)
    print(f"[INFO] saved cleaned soloq → {out_path}")


if __name__ == "__main__":
    main()
