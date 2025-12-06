# analysis/clean_pro.py
import os
import pandas as pd

DATA_DIR = "./data"
RAW_PATH = os.path.join(DATA_DIR, "2025_LoL_esports_match_data_from_OraclesElixir.csv")
CLEAN_PATH = os.path.join(DATA_DIR, "pro_2025_cleaned.csv")


def clean_pro_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    print("[PRO CLEAN] raw shape:", df.shape)

    # ------------------------------------------------------
    # 1) 기본 필터
    # ------------------------------------------------------

    # datacomplete만 사용
    if "datacompleteness" in df.columns:
        df = df[df["datacompleteness"].astype(str).str.lower() == "complete"]

    # TEAM row 제거
    if "position" in df.columns:
        df = df[df["position"].astype(str).str.upper() != "TEAM"]

    # 5분 미만 경기는 삭제
    df["gamelength"] = pd.to_numeric(df["gamelength"], errors="coerce")
    df = df[df["gamelength"] >= 300]

    # ------------------------------------------------------
    # 2) 핵심 컬럼 결측치 제거 (필수)
    # ------------------------------------------------------
    required_cols = [
        "champion", "kills", "deaths", "assists",
        "teamkills", "damagetochampions", "dpm",
        "totalgold", "visionscore"
    ]
    ex_req = [c for c in required_cols if c in df.columns]
    df = df.dropna(subset=ex_req, how="any")

    # ------------------------------------------------------
    # 3) 전체 행 대비 NaN 비율이 너무 높은 컬럼 삭제
    #    → 80% 이상 NaN이면 삭제
    # ------------------------------------------------------
    na_ratio = df.isna().mean()
    drop_cols = na_ratio[na_ratio > 0.80].index.tolist()

    print(f"[PRO CLEAN] dropping {len(drop_cols)} columns due to >80% NaN")
    df = df.drop(columns=drop_cols, errors="ignore")

    # ------------------------------------------------------
    # 4) value가 거의 없는(단일 값만 존재하는) 컬럼 삭제
    #    예: 전부 0, 전부 동일 숫자 → 정보 없음
    # ------------------------------------------------------
    low_variance_cols = [
        c for c in df.columns
        if df[c].nunique(dropna=True) <= 1
    ]
    print(f"[PRO CLEAN] dropping {len(low_variance_cols)} constant columns")
    df = df.drop(columns=low_variance_cols, errors="ignore")

    # ------------------------------------------------------
    # 5) position이 비어있으면 제거
    # ------------------------------------------------------
    df = df[df["position"].astype(str).str.strip() != ""]

    print("[PRO CLEAN] final shape:", df.shape)
    return df


def main():
    df_raw = pd.read_csv(RAW_PATH)
    df_clean = clean_pro_df(df_raw)
    df_clean.to_csv(CLEAN_PATH, index=False, encoding="utf-8-sig")
    print(f"[PRO CLEAN] saved → {CLEAN_PATH}")


if __name__ == "__main__":
    main()
