# Data

The data files in this directory are **not included in the repository** — they contain
student applicant records from the VICEROY Scholar Application system and are proprietary
to the Griffiss Institute.

---

## Source Files

| File | Description |
|---|---|
| `raw/VSA_Dataset_20260202.xlsx` | Raw export from the VICEROY Scholar Application (VSA) system. One row per application submission, 2025–26 cycle. |
| `raw/hd2024.csv` | NCES IPEDS Header Data (2024), used for institution metadata. |
| `raw/C2022_A.zip` | NCES completions data by CIP code and race/ethnicity, used in `src/fetch_completions.py`. |
| `processed/vsa_data_cleaned.csv` | Cleaned applicant records output by `notebooks/VSA_Data_Cleaning.ipynb`. |
| `processed/ipeds_school_data.csv` | Institutional characteristics for 151 partner universities, fetched via `src/fetch_ipeds.py`. |
| `processed/ipeds_completions_by_cip.csv` | STEM completions by institution and CIP code from `src/fetch_completions.py`. |
| `interim/institution_names.csv` | Name crosswalk used to match VSA institution strings to IPEDS school names. |

---

## VSA Schema (key columns)

| Column | Type | Notes |
|---|---|---|
| `StudentID` | str | Anonymized applicant identifier |
| `Institution` | str | Partner university name |
| `GPA` | float | Self-reported; "No GPA yet" → NaN; 0 → NaN |
| `DegreeType` | str | Bachelor's (88%), Master's (7%), other |
| `Discipline` | str | 96% CS or Cybersecurity |
| `Sex` | str | Male / Female / Prefer not to say |
| `Race` | str | IPEDS race categories |
| `Ethnicity` | str | Hispanic or Latino / Not Hispanic |
| `CountryOfCitizenship` | str | US Citizen / Dual Citizen / Not a US Citizen |
| `PellGrantTF` | str | Yes / No — Pell Grant recipient |
| `VeteranTF` | str | Yes / No |
| `CadetCorpTF` | str | Yes / No — ROTC/corps of cadets participation |
| `ROTCBranch` | str | Air Force / Army / Navy / NaN |
| `DoD Job Interest` | str | Yes / Maybe / No |
| `SFSTF`, `SMARTTF`, `CSATF` | str | DoD scholarship flags (SFS, SMART, CSA) |
| `inst_selected` | int | **Primary outcome** — 1 if institution selected this applicant (56% overall) |
| `ROTC Cohort Selected` | float | Post-selection outcome — 1.0 if selected for ROTC cohort (Model F only) |

---

## IPEDS Schema (key columns)

| Column | Notes |
|---|---|
| `school_name` | Matches `Institution` in VSA data after name normalization |
| `inst_control` | 1 = public, 2 = private nonprofit, 3 = private for-profit |
| `hbcu` | 1 if Historically Black College or University |
| `hsi_proxy` | 1 if ≥25% Hispanic enrollment (derived; not official federal designation) |
| `r1_r2` | 1 if Carnegie R1 or R2 research university |
| `admissions_rate` | Undergraduate admissions rate (IPEDS 2022) |
| `grad_rate_6yr_overall` | 6-year graduation rate (IPEDS 2022) |
| `land_grant` | 1 if land-grant institution |
| `locale` | IPEDS locale code (11–13 = city, 21–23 = suburb, 31–33 = town, 41–43 = rural) |
