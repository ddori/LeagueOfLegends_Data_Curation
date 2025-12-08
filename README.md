# League of Legends — SoloQ & Pro Data Curation

A fully automated pipeline for acquiring, parsing, cleaning, and unifying **League of Legends SoloQ and professional match data** into a single analysis-ready dataset. The final output enables **tier-wise comparison** between ranked SoloQ (IRON → CHALLENGER) and professional matches (PRO), supported by a reproducible GitHub Actions workflow and an interactive Streamlit dashboard.

---

## 1. Overview
<img width="2318" height="1171" alt="image" src="https://github.com/user-attachments/assets/cec03fa1-2120-4ff2-ba72-ef92bb7df1c8" />

**Goal**  
Provide a unified dataset that highlights how player behavior, combat patterns, economy, objective control, and vision metrics change as skill increases from SoloQ to professional play.

**Main Outputs**
- Cleaned SoloQ player-level dataset  
- Cleaned Pro player-level dataset  
- Unified dataset with derived metrics:
  ```
  unified_pro_soloq_with_metrics.csv
  ```
- Interactive dashboard:
  ```
  streamlit run app.py
  ```

**Execution Options**
- Local execution (Python 3.11)
- Reproducible CI execution with:
  ```
  .github/workflows/unified_lol.yml
  ```

---

## 2. Repository Structure

```
LeagueOfLegends_Data_Curation/
│
├─ SoloQ/
│   ├─ acquire.py          # Driver: collect SoloQ matches by tier
│   ├─ collector.py        # API sampling + match/timeline download
│   ├─ league_api.py       # League / tier listing endpoints
│   ├─ riot_api.py         # Match, timeline, account queries
│   ├─ http_client.py      # Rate-limit-aware HTTP client (429/5xx retry)
│   ├─ parse.py            # Raw JSON → flat tables
│   ├─ clean.py            # Patch filtering, metrics, normalization
│   ├─ config.py           # API key, PATCH_MM, region, queue
│   ├─ utils.py
│   └─ output_<patch>_by_tier/
│
├─ pro/
│   ├─ clean.py            # Clean Oracle’s Elixir CSV
│   └─ data/               # Raw + cleaned datasets
│
├─ unified.py              # Build unified_pro_soloq_with_metrics.csv
├─ app.py                  # Streamlit dashboard (SoloQ + Pro comparison)
├─ provenance.py           # Provenance graph & metadata
│
├─ notebooks/
│   ├─ soloq_analysis_visualization.ipynb
│   ├─ pro_2025_analysis.ipynb
│   └─ soloq_pro_comparison.ipynb
│
├─ requirements.txt
└─ .github/workflows/unified_lol.yml
```

---

## 3. Data Sources

### 3.1 SoloQ — Riot Games Developer API

SoloQ data is collected directly from Riot API.

**How to get a Riot API key**
1. Visit official Riot Developer Portal:  
   https://developer.riotgames.com/
2. Create an account (or login)
3. Generate a **Personal API Key** (RGAPI-xxxx-xxxx)
4. Set as environment variable:

```
export RIOT_API_KEY="RGAPI-xxxxxxxx-xxxxxxxx"
```

The pipeline uses:
- **RANKED_SOLO_5x5 (Queue ID: 420)**
- **Platform: KR**
- **Tier sampling → match → timeline**

---

### 3.2 Pro — Oracle’s Elixir (Google Drive)

Professional match data (2025 season) is taken from Oracle’s Elixir CSV.

In CI (GitHub Actions), it is downloaded from a **prepared Google Drive folder**:

> **Allowed Pro data folder:**  
> https://drive.google.com/drive/u/1/folders/1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH

**IMPORTANT:**  
When running the GitHub Actions pipeline, you must:
1. Open the folder above  
2. **Choose the year you want** (e.g., 2024, 2025)  
3. **Right-click → Get link**  
4. Paste that **specific file link** into the workflow input:
   ```
   pro_gdrive_url
   ```

The workflow uses `gdown --fuzzy` to download the file.

---

## 4. Local Usage

### 4.1 Environment Setup

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Minimum dependencies:
```
dotenv
requests
pandas
matplotlib
seaborn
pyarrow
streamlit
prov
pydot
graphviz
```

---

### 4.2 SoloQ Pipeline (Local)

**Step 1 — Acquire raw data**
```
cd SoloQ
python acquire.py
```
Downloads tier-wise samples under:
```
SoloQ/output_<PATCH_MM>_by_tier/
```

**Step 2 — Parse JSON → tables**
```
python parse.py
```
Produces:
```
SoloQ/data/soloq_full_<PATCH_MM>.csv
SoloQ/data/soloq_full_<PATCH_MM>.parquet
```

**Step 3 — Clean SoloQ**
```
python clean.py
```
Output:
```
SoloQ/data/soloq_clean_<PATCH_MM>.csv
```

Move back:
```
cd ..
```

---

### 4.3 Pro Pipeline (Local)

Download the CSV from Oracle’s Elixir and place it into:

```
pro/data/
```

Example:
```
pro/data/2025_LoL_esports_match_data_from_OraclesElixir.csv
```

Run clean:
```
cd pro
python clean.py
cd ..
```

Output:
```
pro/data/pro_2025_cleaned.csv
```

---

### 4.4 Build Unified Dataset

From project root:

```
python unified.py
```

Generates:
```
unified_pro_soloq_with_metrics.csv
```

This contains:
- aligned schemas (tier, role, patch consistency)
- derived metrics (DPM, GPM, CSPM, etc.)
- team objective metrics
- vision efficiency metrics
- lane pressure metrics (normalized, abs)

---

### 4.5 Dashboard

Run:
```
streamlit run app.py
```

The dashboard allows:
- role filtering
- tier-wise progression visualization
- boxplot distribution by tier
- clear SoloQ vs Pro comparison

**Purpose:**  
See how behavior **systematically changes** from IRON to PRO.

---

## 5. GitHub Actions Pipeline

File:
```
.github/workflows/unified_lol.yml
```

### 5.1 Trigger
Manual:
```
Actions → LoL Unified Pipeline → Run workflow
```

### 5.2 Inputs
Required:
- `riot_api_key` — RGAPI-xxxx key
- `patch_mm` — e.g. 15.24
- `pro_gdrive_url` — Link copied from the Google Drive folder above

### 5.3 Job Sequence
1. **soloq-acquire**
2. **soloq-parse**
3. **soloq-clean**
4. **pro-download-clean**
5. **unify**
6. **app-check**

Artifacts are automatically passed between jobs.

Each step is independent and follows the same local logic.

## 6. Analysis

All data exploration and comparison notebooks are stored in the `analysis/` folder.

The notebooks included are:

- `soloq_analysis_visualization.ipynb`  
  Visualization and exploration of cleaned SoloQ data. Includes distribution checks, metric validation, and patch filtering verification.

- `pro_2025_analysis.ipynb`  
  Analysis of professional match data provided by Oracle's Elixir, including feature validation and metric alignment.

- `soloq_pro_comparison.ipynb`  
  The primary analysis notebook comparing SoloQ and professional match data across all tiers. Generates tier progression plots, distribution comparisons, and unified schema validation needed for the dashboard.
  
These notebooks complement the automated pipeline and provide deeper insight into how derived metrics behave across sampling groups.

---

## 7. Provenance & Reproducibility
<img width="3221" height="817" alt="provenance" src="https://github.com/user-attachments/assets/9e76391b-1526-4a65-bcfb-0d7963148c91" />

This project includes full **data provenance tracking** to ensure the entire dataset creation process is **transparent**, **verifiable**, and **reproducible**.

### 7.1 Provenance Graph
- `provenance.py` can generate a provenance graph following the structure of the **USGS Science Data Lifecycle**
- The pipeline captures:
  - **Acquisition** → Riot API sampling
  - **Processing** → Parsing, cleaning, normalization
  - **Analysis Preparation** → Derived metrics & schema alignment
  - **Preservation** → Artifacts passed through GitHub Actions
  - **Dissemination** → Final unified dataset + interactive dashboard

The provenance record includes:
- input data source URLs (Google Drive for Pro data, Riot API endpoints)
- transformation scripts (versioned in git)
- intermediate outputs (GitHub Actions artifacts)
- environment dependencies (`requirements.txt`)
- metadata consistency (tier/role/patch normalization)

This enables **traceability**:
Every value in the unified dataset can be traced back to:
- a raw JSON file from Riot API, or
- a row from Oracle’s Elixir CSV

---

## 7. Acknowledgments

- **Riot Games Developer Portal**  
  https://developer.riotgames.com/

- **Riot Policies**  
  https://developer.riotgames.com/policies/general

- **Oracle’s Elixir**  
  https://oracleselixir.com/tools/downloads

This project is for **research & educational purposes**.  
All data use must follow Riot Games API policies.
