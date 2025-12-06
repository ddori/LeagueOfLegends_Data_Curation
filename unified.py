import pandas as pd
import numpy as np
from typing import Optional


def normalize_role(raw: str) -> str:
    if raw is None:
        return "UNKNOWN"
    r = str(raw).upper().strip()
    if r in {"TOP", "TOPLANE", "TOP_LANE"}:
        return "TOP"
    if r in {"JUNGLE", "JNG", "JG", "JUN", "JUG"}:
        return "JUNGLE"
    if r in {"MID", "MIDDLE", "MID_LANE"}:
        return "MIDDLE"
    if r in {"ADC", "BOT", "BOTTOM", "DUO_CARRY"}:
        return "BOTTOM"
    if r in {"SUP", "SUPPORT", "UTILITY", "DUO_SUPPORT"}:
        return "UTILITY"
    if r in {"TEAM"}:
        return "TEAM"
    if r in {"NONE", "", "UNASSIGNED"}:
        return "UNKNOWN"
    return r


def parse_pro_with_raw(
    df: pd.DataFrame,
    patch_mm_prefix: Optional[str] = None,
) -> pd.DataFrame:
    # 느슨한 패치 필터: "15.2" 이런 prefix 기준
    if patch_mm_prefix is not None and "patch" in df.columns:
        before = len(df)
        mask = df["patch"].astype(str).str.startswith(str(patch_mm_prefix))
        df = df[mask]
        print(f"[PRO] patch startswith {patch_mm_prefix}: {before} -> {len(df)}")

    out = pd.DataFrame(index=df.index)

    out["dataset_type"] = "pro"
    out["tier"] = "PRO"

    out["match_id"] = df["gameid"].astype(str)
    out["patch"] = df["patch"].astype(str)
    out["duration_min"] = df["gamelength"].astype(float) / 60.0

    roles = df["position"].astype(str)
    out["role"] = roles.apply(normalize_role)

    out["champion"] = df["champion"].astype(str)

    # combat
    out["kills"] = df["kills"].astype("Int64")
    out["deaths"] = df["deaths"].astype("Int64")
    out["assists"] = df["assists"].astype("Int64")

    deaths_nonzero = out["deaths"].replace(0, np.nan)
    out["kda"] = ((out["kills"] + out["assists"]) / deaths_nonzero).fillna(
        (out["kills"] + out["assists"]).astype(float)
    )

    # damage / economy
    out["player_damage"] = df["damagetochampions"].astype(float)
    out["dpm"] = df["dpm"].astype(float)
    out["total_gold"] = df["totalgold"].astype(float)
    out["gpm"] = df["earned gpm"].astype(float)
    out["cspm"] = df["cspm"].astype(float)
    out["cs_total"] = out["cspm"] * out["duration_min"]

    # team / share
    out["teamkills"] = df["teamkills"].astype(float)
    out["damage_share"] = df["damageshare"].astype(float)
    out["team_damage"] = out["player_damage"] / out["damage_share"].replace(0, np.nan)

    # vision
    out["vision_score"] = df["visionscore"].astype(float)
    out["wards_placed"] = df.get("wardsplaced", pd.Series([np.nan] * len(df))).astype(float)
    out["wards_killed"] = df.get("wardskilled", pd.Series([np.nan] * len(df))).astype(float)

    # objectives
    out["team_dragons"] = df.get("dragons", pd.Series([np.nan] * len(df))).astype(float)
    out["team_barons"] = df.get("barons", pd.Series([np.nan] * len(df))).astype(float)
    out["team_towers"] = df.get("towers", pd.Series([np.nan] * len(df))).astype(float)

    # lane diff
    for src, dst in [
        ("golddiffat10", "gold_diff_10"),
        ("xpdiffat10", "xp_diff_10"),
        ("csdiffat10", "cs_diff_10"),
    ]:
        if src in df.columns:
            out[dst] = df[src].astype(float)
        else:
            out[dst] = np.nan

    out["win"] = df["result"].astype(int).eq(1)

    return out

def parse_soloq_with_raw(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)

    # dataset / tier
    out["dataset_type"] = "soloq"
    out["tier"] = df["tier"].astype(str) if "tier" in df.columns else "UNKNOWN"

    # match id
    if "matchId" in df.columns:
        out["match_id"] = df["matchId"].astype(str)
    elif "match_id" in df.columns:
        out["match_id"] = df["match_id"].astype(str)
    else:
        out["match_id"] = ""

    if "gameVersion" in df.columns:
        gv_split = df["gameVersion"].astype(str).str.split(".")
        out["patch"] = gv_split.str[0] + "." + gv_split.str[1]
    elif "patch" in df.columns:
        out["patch"] = df["patch"].astype(str)
    else:
        out["patch"] = np.nan

    # duration
    if "gameDuration" in df.columns:
        out["duration_min"] = df["gameDuration"].astype(float) / 60.0
    elif "duration_min" in df.columns:
        out["duration_min"] = df["duration_min"].astype(float)
    else:
        out["duration_min"] = 0.0

    # role: raw는 teamPosition, clean은 role
    if "teamPosition" in df.columns:
        roles_src = df["teamPosition"].astype(str)
        out["role"] = roles_src.apply(normalize_role)
    elif "role" in df.columns:
        roles_src = df["role"].astype(str)
        out["role"] = roles_src.apply(normalize_role)
    else:
        out["role"] = "UNKNOWN"

    if "championName" in df.columns:
        out["champion"] = df["championName"].astype(str)
    elif "champion" in df.columns:
        out["champion"] = df["champion"].astype(str)
    else:
        out["champion"] = "UNKNOWN"

    # combat
    for col in ["kills", "deaths", "assists"]:
        if col in df.columns:
            out[col] = df[col].astype("Int64")
        else:
            out[col] = pd.Series([pd.NA] * len(df), dtype="Int64")

    deaths_nonzero = out["deaths"].replace(0, np.nan)
    out["kda"] = ((out["kills"] + out["assists"]) / deaths_nonzero).fillna(
        (out["kills"] + out["assists"]).astype(float)
    )

    # damage / economy
    if "totalDamageDealtToChampions" in df.columns:
        out["player_damage"] = df["totalDamageDealtToChampions"].astype(float)
    else:
        out["player_damage"] = 0.0

    if "dpm" in df.columns:
        out["dpm"] = df["dpm"].astype(float)
    elif "ch_damagePerMinute" in df.columns:
        out["dpm"] = df["ch_damagePerMinute"].astype(float)
    else:
        out["dpm"] = out["player_damage"] / out["duration_min"].replace(0, np.nan)

    if "goldEarned" in df.columns:
        out["total_gold"] = df["goldEarned"].astype(float)
    else:
        out["total_gold"] = 0.0

    if "gpm" in df.columns:
        out["gpm"] = df["gpm"].astype(float)
    else:
        out["gpm"] = out["total_gold"] / out["duration_min"].replace(0, np.nan)

    if "totalMinionsKilled" in df.columns:
        cs1 = df["totalMinionsKilled"].fillna(0)
    else:
        cs1 = 0
    if "neutralMinionsKilled" in df.columns:
        cs2 = df["neutralMinionsKilled"].fillna(0)
    else:
        cs2 = 0
    cs_total = cs1 + cs2
    out["cs_total"] = cs_total.astype(float)

    if "cspm" in df.columns:
        out["cspm"] = df["cspm"].astype(float)
    else:
        out["cspm"] = out["cs_total"] / out["duration_min"].replace(0, np.nan)

    # teamkills
    if "team_obj_champion_kills" in df.columns:
        out["teamkills"] = df["team_obj_champion_kills"].astype(float)
    else:
        out["teamkills"] = np.nan

    # damage share / team damage
    team_dmg_pct_col = None
    if "ch_teamDamagePercentage" in df.columns:
        team_dmg_pct_col = "ch_teamDamagePercentage"
    elif "challenges_teamDamagePercentage" in df.columns:
        team_dmg_pct_col = "challenges_teamDamagePercentage"

    if team_dmg_pct_col is not None:
        ratio = df[team_dmg_pct_col].replace(0, np.nan).astype(float)
        out["damage_share"] = ratio
        out["team_damage"] = out["player_damage"] / ratio
    else:
        out["damage_share"] = np.nan
        out["team_damage"] = np.nan

    # vision
    if "visionScore" in df.columns:
        out["vision_score"] = df["visionScore"].astype(float)
    else:
        out["vision_score"] = np.nan

    out["wards_placed"] = df.get("wardsPlaced", pd.Series([np.nan] * len(df))).astype(float)
    out["wards_killed"] = df.get("wardsKilled", pd.Series([np.nan] * len(df))).astype(float)

    # objectives
    if "team_obj_dragon_kills" in df.columns:
        out["team_dragons"] = df["team_obj_dragon_kills"].astype(float)
    else:
        out["team_dragons"] = df.get("dragonKills", pd.Series([np.nan] * len(df))).astype(float)

    if "team_obj_baron_kills" in df.columns:
        out["team_barons"] = df["team_obj_baron_kills"].astype(float)
    else:
        out["team_barons"] = df.get("baronKills", pd.Series([np.nan] * len(df))).astype(float)

    if "team_obj_tower_kills" in df.columns:
        out["team_towers"] = df["team_obj_tower_kills"].astype(float)
    else:
        out["team_towers"] = df.get("turretKills", pd.Series([np.nan] * len(df))).astype(float)

    if "ch_laningPhaseGoldExpAdvantage" in df.columns:
        out["gold_diff_10"] = df["ch_laningPhaseGoldExpAdvantage"].astype(float)
    elif "gold_diff_10" in df.columns:
        out["gold_diff_10"] = df["gold_diff_10"].astype(float)
    else:
        out["gold_diff_10"] = np.nan

    if "ch_maxCsAdvantageOnLaneOpponent" in df.columns:
        out["cs_diff_10"] = df["ch_maxCsAdvantageOnLaneOpponent"].astype(float)
    elif "cs_diff_10" in df.columns:
        out["cs_diff_10"] = df["cs_diff_10"].astype(float)
    else:
        out["cs_diff_10"] = np.nan

    if "ch_xpDiffAt10" in df.columns:
        out["xp_diff_10"] = df["ch_xpDiffAt10"].astype(float)
    elif "xp_diff_10" in df.columns:
        out["xp_diff_10"] = df["xp_diff_10"].astype(float)
    else:
        out["xp_diff_10"] = np.nan

    # win
    if "win" in df.columns:
        out["win"] = df["win"].astype(bool)
    else:
        out["win"] = False

    return out

def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    duration = df["duration_min"].replace(0, np.nan)

    df["kp"] = (df["kills"] + df["assists"]) / df["teamkills"].replace(0, np.nan)
    df["aggression_index"] = (df["kills"] + df["assists"]) / (df["deaths"] + 1)

    df["dpm"] = df["dpm"].astype(float)
    df["gpm"] = df["gpm"].astype(float)
    df["cspm"] = df["cspm"].astype(float)
    df["rce"] = df["dpm"] / df["gpm"].replace(0, np.nan)

    df["vspm"] = df["vision_score"] / duration
    df["vision_efficiency"] = (df["wards_placed"] + df["wards_killed"]) / duration

    df["lane_pressure_index"] = (
        df["gold_diff_10"].abs().fillna(0)
        + df["xp_diff_10"].abs().fillna(0)
        + df["cs_diff_10"].abs().fillna(0)
    ) / 3.0

    return df


def build_unified_dataset(
    pro_path: str,
    soloq_path: str,
    output_path: Optional[str] = None,
    pro_patch_prefix: Optional[str] = None,
    patch_mm: Optional[str] = None, 
) -> pd.DataFrame:
    pro_raw = pd.read_csv(pro_path)
    soloq_raw = pd.read_csv(soloq_path)

    # pro는 prefix로 느슨하게 필터
    pro_parsed = parse_pro_with_raw(pro_raw, patch_mm_prefix=pro_patch_prefix)
    # soloq는 이미 clean 단계에서 patch 필터 했다고 가정하고 그대로 사용
    soloq_parsed = parse_soloq_with_raw(soloq_raw)

    unified = pd.concat([pro_parsed, soloq_parsed], ignore_index=True)
    unified = add_derived_metrics(unified)

    columns_order = [
        "dataset_type",
        "tier",
        "match_id",
        "patch",
        "duration_min",
        "role",
        "champion",
        "win",
        # combat
        "kills",
        "deaths",
        "assists",
        "kda",
        "player_damage",
        "dpm",
        "total_gold",
        "gpm",
        "cs_total",
        "cspm",
        "teamkills",
        "kp",
        "aggression_index",
        "damage_share",
        "team_damage",
        "rce",
        # vision
        "vision_score",
        "vspm",
        "wards_placed",
        "wards_killed",
        "vision_efficiency",
        # objectives
        "team_dragons",
        "team_barons",
        "team_towers",
        # lane
        "gold_diff_10",
        "xp_diff_10",
        "cs_diff_10",
        "lane_pressure_index",
    ]

    for col in columns_order:
        if col not in unified.columns:
            unified[col] = np.nan

    unified = unified[columns_order]

    if output_path is not None:
        unified.to_csv(output_path, index=False)
        print(f"[UNIFIED] saved → {output_path} (shape={unified.shape})")

    return unified


if __name__ == "__main__":
    unified_df = build_unified_dataset(
        pro_path="./pro/data/pro_2025_cleaned.csv",
        soloq_path="./SoloQ/data/soloq_clean_15.24.csv",
        output_path="unified_pro_soloq_with_metrics.csv",
        pro_patch_prefix="15.2",  
        patch_mm="15.24",          
    )
