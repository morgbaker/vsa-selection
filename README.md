# Predictors of Scholar Selection

**Author:** Morgan Baker

---

## Overview

This repository documents a working research project investigating which factors influence selection into the a cyber workforce development program that connects students to internships in the defense space. 

The project begins with data cleaning and exploratory analysis, then quantifies
how much of selection outcome is explained by institutional context versus
individual characteristics, and fits a linear probability model with institution
fixed effects to estimate individual-level effects within that structure.

The raw applicant data is proprietary and not included. See [`data/README.md`](data/README.md) for the full schema.

---

## Repository Structure

```
notebooks/
    01_EDA.ipynb                          
    02_data_cleaning.ipynb            
    03_selection_model.ipynb 

src/
    model_acceptance.py     
    fetch_ipeds.py       
    fetch_completions.py     

data/
    README.md               
```

---

## Notebooks

### [`01_EDA.ipynb`](notebooks/01_EDA.ipynb)
Exploratory analysis of the 2025–26 applicant pool.
- Missing data assessment and cleaning pipeline
- Distributions: GPA, demographics, academic background, military/DoD affiliation

### [`02_data_cleaning.ipynb`](notebooks/02_data_cleaning.ipynb)
Reproducible cleaning pipeline from raw Excel export to analysis-ready CSV.
- Sparse row removal and StudentID deduplication (keep most recent submission)
- GPA type coercion and out-of-range handling
- Institution name normalization: free-text corrections, typo flagging, casing standardization
- Discipline/major consolidation
- Output: `data/processed/vsa_data_cleaned.csv`

### [`03_selection_model.ipynb`](notebooks/03_selection_model.ipynb)
Structural diagnosis and primary inferential analysis of VICEROY selection.
- Eligibility definition: GPA ≥ 3.2, US citizen, partner institution
- ICC decomposition: quantifies between- vs. within-institution variance
- Cluster size and acceptance rate distributions across competitive institutions
- Part 1 — LPM testing whether non-competitive school attendance (0%/100% acceptance rate) is predicted by individual characteristics; validates sample restriction as a capacity decision
- Part 2 — LPM with institution fixed effects and clustered SEs on competitive sample; logistic regression reported as robustness check
- mil_affil deep-dive: acceptance by ROTC branch, within-institution scatter, GPA overlap
- Sensitivity: threshold robustness check (10%/90% exclusion boundary)

---

## `src/model_acceptance.py`

Central modeling module. Key components:

- **`engineer_student_features`** / **`engineer_military_features`** — derives binary and ordinal predictors from raw VSA columns (GPA coercion, citizenship flag, ROTC branch indicators, DoD scholar flag)
- **`compute_icc`** — one-way ANOVA ICC decomposition; quantifies the share of outcome variance attributable to institution membership
- **`merge_ipeds`** — left-joins VSA applicant records to IPEDS institutional characteristics on institution name

---

## Technical Stack

- Python 3.10+, pandas, numpy, scipy, statsmodels, matplotlib, seaborn
- LPM and logistic regression with institution fixed effects and clustered standard errors via `statsmodels.formula.api`
- IPEDS data fetched via Urban Institute Education Data API (`src/fetch_ipeds.py`)

See [`requirements.txt`](requirements.txt) for full dependencies.

---

## AI Assistance

This project was developed using Claude (Anthropic) as a collaborative tool.
AI assisted with code generation and iterative debugging throughout the analysis pipeline. All analytical decisions including model selection, eligibility definitions, and interpretation of findings were directed by the author.
