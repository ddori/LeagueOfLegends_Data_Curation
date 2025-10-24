# League of Legends — SoloQ & Pro Data Curation

> End-to-end project that **acquires**, **parses**, and **analyzes** League of Legends data for **2025 Spring/Summer (H1)** from both **SoloQ** and **professional** play, producing analysis-ready tables and reproducible visualizations.

---

## 1) Overview

- **Goal**: collect SoloQ and professional match data for 2025 H1, transform everything into **analysis-ready DataFrames**, and expose **clear visual analyses** (e.g., DPM/GPM by tier, SoloQ vs Pro comparisons).
- **Why this repo**: You can run acquisition in the cloud via **GitHub Actions**, or locally. The pipeline follows the **USGS Data Life Cycle** (Acquisition → Processing → Analysis → Preservation/Publishing). https://github.com/ddori/UIUC_DataCuration/actions
- **Included visualization**: see notebooks that reproduce plots like:

<img width="989" height="490" alt="image" src="https://github.com/user-attachments/assets/931fa0a7-05ec-45f1-93db-7e56b5ed2480" />
<img width="989" height="490" alt="image" src="https://github.com/user-attachments/assets/178bf148-2018-4f57-a673-a095fad3d998" />

---

## 2) Data Sources & Scope

- **SoloQ**: retrieved through the **Riot Games API** (returns **JSON** match payloads).
- **Rate Limits**: 20 requests every 1 seconds(s), 100 requests every 2 minutes(s)
- **Professional**: retrieved from **Oracle’s Elixir** (CSV).  
  In CI, these are standardized to the same schema for direct comparison with SoloQ.
- **Time window**: **2025 H1** (Spring & Summer seasons).  
  For SoloQ, matches are restricted to **Patch 15.15–15.20** to align with the same period.

---

## 3) Ethics & Policy

- **Riot API Policy & legal/ethical compliance**:  https://developer.riotgames.com/policies/general
  Only publicly available match data are collected. This project **follows Riot Games Developer Portal policies** (usage, rate limits, and ToS).  
- **API key validity**: **Riot API keys expire roughly every 24 hours**. After expiration, **request a new key** from the Riot Developer Portal and re-run the workflow. https://developer.riotgames.com/
- **Secrets**: Never commit secrets. API keys must be provided through **GitHub Actions inputs** or local environment variables.

---

## 4) Environment & Requirements

- **Python**: `3.11`
- **Install**:
  ```bash
  # from repo root (requirements.txt is at the root)
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  ```
- Typical packages used:
  - `requests` (SoloQ acquisition)
  - `pandas`
  - `pyarrow` (Parquet write/read)
  - `matplotlib` / `plotly` (visualization)
  - `jupyter` (run notebooks)
  
  > Exact versions are pinned in `requirements.txt`.

---

## 5) How the Pipeline Works

### Acquisition (SoloQ)
1. **Riot API** is called for match lists and match details.
2. Results are saved under `SoloQ/output_<patch>_by_tier/<TIER>/matches/*.json`.

### Processing / Parsing
1. `SoloQ/parse.py` scans `output_<patch>_by_tier` automatically.
2. It flattens all available fields including stats, runes, challenges, and team data.
3. It writes both:
   - CSV: `SoloQ/data/soloq_full_<patch>.csv`
   - Parquet: `SoloQ/data/soloq_full_<patch>.parquet`

### Analysis
- In `analysis`, you will find notebooks for:
  - **SoloQ** analysis
  - **Pro** analysis
  - **Comparison** (SoloQ vs Pro tier analysis)

---

## 6) GitHub Actions (CI)

- **SoloQ workflow**: **Actions → Get SoloQ data** https://github.com/ddori/UIUC_DataCuration/actions/workflows/soloq.yml
  <img width="1295" height="594" alt="image" src="https://github.com/user-attachments/assets/fd41db24-33bc-49ea-811d-6ccb63da1f5a" />

  **Inputs**:
  - `riot_api_key` (required, masked in logs)
  - `max_pages_per_player` (optional limit)
  - `patch_mm` (e.g., `15.20`)

  **Artifacts produced**:
  - `soloq-raw-json`: the raw JSON output at `SoloQ/output_<patch>_by_tier`
  - `soloq-parsed`: CSV + Parquet parsed dataset in `SoloQ/data/`

- **Pro workflow (Oracle’s Elixir)**: **Actions → Get Pro data by Year**  https://github.com/ddori/UIUC_DataCuration/actions/workflows/get_pro_by_year.yml
  <img width="1306" height="420" alt="image" src="https://github.com/user-attachments/assets/7344f7c2-3da2-4932-ab55-f9b9573fddca" />

  **Inputs**:
  - `year` (e.g., `2025`)

  **Behavior**:
  - Downloads the Oracle’s Elixir CSV for the given year via CI.  

  **Artifacts produced**:
  - `pro-raw-year`: the downloaded CSV for the specified year  

---


## 7) Professional Data (Oracle’s Elixir)

- Pro data are sourced from **Oracle’s Elixir** as CSV files (season/year).
- In CI or locally, align schema to match SoloQ outputs.

---

## 8) Outputs

- **Raw**: `SoloQ/output_<patch>_by_tier/<TIER>/matches/*.json`
- **Parsed tables**:
  - `SoloQ/data/soloq_full_<patch>.csv`
  - `SoloQ/data/soloq_full_<patch>.parquet`

---

## 9) Local Run Example

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt

export RIOT_API_KEY=YOUR_KEY
cd SoloQ
python parse.py
cd ..

jupyter lab
```

---

## 10) Acknowledgments
- **Riot Policies** https://developer.riotgames.com/policies/general
- **Riot Games Developer Portal** https://developer.riotgames.com/docs/portal
- **Oracle’s Elixir** https://oracleselixir.com/tools/downloads


