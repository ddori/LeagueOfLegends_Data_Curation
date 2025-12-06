import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --------------------------------
# 기본 설정
# --------------------------------

st.set_page_config(
    page_title="LoL Unified Dashboard",
    layout="wide",
)

TIER_ORDER = [
    "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
    "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER",
    "CHALLENGER", "PRO",
]

METRIC_LABEL = {
    # Combat / Economy
    "kills": "Kills",
    "deaths": "Deaths",
    "assists": "Assists",
    "kda": "KDA",
    "player_damage": "Player Damage",
    "dpm": "Damage per Minute",
    "total_gold": "Total Gold",
    "gpm": "Gold per Minute",
    "cs_total": "Total CS",
    "cspm": "CS per Minute",
    "teamkills": "Team Kills",
    "kp": "Kill Participation",
    "aggression_index": "Aggression Index",
    "damage_share": "Damage Share",
    "team_damage": "Team Damage",
    "rce": "Resource Conversion Efficiency",

    # Vision
    "vision_score": "Vision Score",
    "vspm": "Vision Score per Minute",
    "wards_placed": "Wards Placed",
    "wards_killed": "Wards Killed",
    "vision_efficiency": "Vision Efficiency",

    # Objectives
    "team_dragons": "Team Dragons",
    "team_barons": "Team Barons",
    "team_towers": "Team Towers",

    # Lane
    "gold_diff_10": "Gold Diff @10",
    "xp_diff_10": "XP Diff @10",
    "cs_diff_10": "CS Diff @10",
    "lane_pressure_index": "Lane Pressure Index (|Δ|)",
}

# 라인차트에 기본으로 볼 Metric들
LINE_METRICS = [
    "dpm",
    "gpm",
    "cspm",
    "vision_efficiency",
    "team_dragons",
    "lane_pressure_index",
]

METRIC_OPTIONS = list(METRIC_LABEL.keys())


# --------------------------------
# 데이터 로드 & 전처리
# --------------------------------

@st.cache_data
def load_unified(path: str = "unified_pro_soloq_with_metrics.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # tier를 ordered categorical로
    df["tier"] = df["tier"].astype(str).str.upper()
    df["tier"] = pd.Categorical(df["tier"], categories=TIER_ORDER, ordered=True)

    # role 정리
    df["role"] = df["role"].fillna("UNKNOWN")

    # patch 문자열화
    df["patch"] = df["patch"].astype(str)

    # lane_pressure_index 절대값 사용
    if "lane_pressure_index" in df.columns:
        df["lane_pressure_index"] = df["lane_pressure_index"].astype(float).abs()

    return df


def ordered_tiers_in_df(df: pd.DataFrame):
    present = df["tier"].dropna().astype(str).unique().tolist()
    return [t for t in TIER_ORDER if t in present]


df_raw = load_unified()
df = prepare_df(df_raw)

if df.empty:
    st.error("unified_pro_soloq_with_metrics.csv 에 데이터가 없습니다.")
    st.stop()


# --------------------------------
# Sidebar: Role 멀티 셀렉트만
# --------------------------------

st.sidebar.title("⚙️ Controls")

roles_available = sorted(df["role"].dropna().unique().tolist())
selected_roles = st.sidebar.multiselect(
    "Role 선택 (복수 선택 가능)",
    roles_available,
    default=roles_available,
)

df_f = df.copy()
if selected_roles:
    df_f = df_f[df_f["role"].isin(selected_roles)]

if df_f.empty:
    st.warning("선택한 Role 조합에 해당하는 데이터가 없습니다.")
    st.stop()


# --------------------------------
# Header & Overview
# --------------------------------

st.title("🎮 LoL Unified Dashboard (Pro + SoloQ)")

caption_parts = []
caption_parts.append(f"Roles: {', '.join(selected_roles) if selected_roles else 'ALL'}")
st.caption(" / ".join(caption_parts))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Rows", len(df_f))
with col2:
    st.metric("SoloQ Rows", int((df_f["dataset_type"] == "soloq").sum()))
with col3:
    st.metric("Pro Rows", int((df_f["dataset_type"] == "pro").sum()))

st.markdown("---")


# --------------------------------
# Helper: 티어별 mean + std
# --------------------------------

def tier_agg_mean_std(df_in: pd.DataFrame, metric: str) -> pd.DataFrame:
    df_temp = df_in.dropna(subset=["tier", metric])
    if df_temp.empty:
        return pd.DataFrame(columns=["tier", "mean", "std", "count"])

    g = (
        df_temp
        .groupby("tier")[metric]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    g["tier"] = pd.Categorical(
        g["tier"].astype(str),
        categories=ordered_tiers_in_df(df_temp),
        ordered=True,
    )
    g = g.sort_values("tier")
    return g


# --------------------------------
# 라인 그래프: Tier vs Metric (mean ± std)
# --------------------------------

st.subheader("📈 Tier Progression (평균 + 표준편차)")

# 존재하는 metric만 사용
metrics_for_line = [m for m in LINE_METRICS if m in df_f.columns]

if not metrics_for_line:
    st.info("라인 차트에 사용할 수 있는 Metric이 없습니다.")
else:
    for i, metric in enumerate(metrics_for_line):
        if i % 2 == 0:
            cols = st.columns(2)

        with cols[i % 2]:
            g = tier_agg_mean_std(df_f, metric)

            if g.empty:
                st.info(f"{METRIC_LABEL.get(metric, metric)}: 사용 가능한 값이 없습니다.")
                continue

            fig = px.line(
                g,
                x="tier",
                y="mean",
                error_y="std",
                markers=True,
                title=f"{METRIC_LABEL.get(metric, metric)} vs Tier",
            )
            fig.update_layout(
                xaxis_title="Tier",
                yaxis_title="Mean ± Std",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.subheader("📦 Tier-wise Boxplot")

available_metrics_for_box = [
    m for m in METRIC_OPTIONS
    if m in df_f.columns
]

if not available_metrics_for_box:
    st.info("Boxplot에 사용할 수 있는 Metric이 없습니다.")
else:
    metric_box = st.selectbox(
        "Boxplot에 사용할 Metric 선택",
        available_metrics_for_box,
        format_func=lambda x: METRIC_LABEL.get(x, x),
    )

    df_box = df_f.dropna(subset=["tier", metric_box]).copy()
    if df_box.empty:
        st.info(f"{METRIC_LABEL.get(metric_box, metric_box)}: 유효한 데이터가 없습니다.")
    else:
        # ✅ 티어 순서 고정: IRON → ... → PRO
        df_box["tier"] = df_box["tier"].astype(str).str.upper()
        df_box["tier"] = pd.Categorical(
            df_box["tier"],
            categories=TIER_ORDER,   # 전체 순서 고정
            ordered=True,
        )
        df_box = df_box.sort_values("tier")

        fig_box = px.box(
            df_box,
            x="tier",
            y=metric_box,
            points="all",
            title=f"{METRIC_LABEL.get(metric_box, metric_box)} — Tier-wise Distribution",
        )
        fig_box.update_layout(
            xaxis_title="Tier",
            yaxis_title=METRIC_LABEL.get(metric_box, metric_box),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_box, use_container_width=True)