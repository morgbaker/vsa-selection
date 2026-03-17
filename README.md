# Predictors of VICEROY Scholar Selection

**Author:** Morgan Baker

---

## Overview

This repository documents a working research project investigating which factors
influence selection into the Griffiss Institute's cyber workforce development
pipeline, VICEROY. 

The project begins with data cleaning and exploratory analysis, then quantifies
how much of selection outcome is explained by institutional context versus
individual characteristics, and fits a population-averaged logistic model to
estimate individual-level effects within that structure.

The raw applicant data is proprietary and not included. See [`data/README.md`](data/README.md) for the full schema.

---

## Repository Structure

```
notebooks/
    01_EDA.ipynb                          
    02_data_cleaning.ipynb            
    03_selection_analysis.ipynb 

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

### [`03_selection_analysis.ipynb`](notebooks/03_institutional_vs_individual.ipynb)
Structural diagnosis and multivariate modeling of VICEROY selection.
- Eligibility definition: GPA ≥ 3.2, US citizen, partner institution 
- ICC decomposition
- Cluster size distribution 
- Bivariate GEE odds ratio screening across all student-level predictors
- Joint GEE model 

---

## `src/model_acceptance.py`

Central modeling module. Key components:

- **`engineer_student_features`** / **`engineer_military_features`** — derives binary and ordinal predictors from raw VSA columns (GPA coercion, citizenship flag,ROTC branch indicators, DoD scholar flag)
- **`compute_icc`** — one-way ANOVA ICC decomposition; primary justification for GEE over naive logistic regression
- **`run_gee_logistic`** — population-averaged logistic GEE clustered by institution; exchangeable or independence working correlation; GPA mean-centered before fitting
- **`gee_or_table`** — tidy odds ratio / CI / p-value output from a fitted GEE result

---

## Technical Stack

- Python 3.10+, pandas, numpy, scipy, statsmodels, matplotlib, seaborn
- GEE models (exchangeable and independence working correlations, QIC-based
  comparison) via `statsmodels.genmod.generalized_estimating_equations`
- IPEDS data fetched via NCES API (`src/fetch_ipeds.py`)

See [`requirements.txt`](requirements.txt) for full dependencies.

---

## AI Assistance

This project was developed using Claude (Anthropic) as a collaborative tool.
AI assisted with code generation and iterative debugging throughout the analysis pipeline. All analytical decisions including model selection, eligibility definitions, and interpretation of findings were directed by the author.
