"""
src/model_acceptance.py
-----------------------
Helper functions for the VICEROY acceptance modeling workflow.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.genmod.generalized_estimating_equations import GEE
from statsmodels.genmod import families
from statsmodels.genmod.cov_struct import Exchangeable, Independence



# Paths
BASE       = Path(__file__).resolve().parent.parent
VSA_PATH   = BASE / "data" / "processed" / "vsa_data_cleaned.csv"
IPEDS_PATH = BASE / "data" / "processed" / "ipeds_school_data.csv"

# Variable lists
OUTCOME      = "accepted"          # LMS Onboarded == 1 OR Institution Selection == 1
OUTCOME_ROTC = "rotc_cohort_outcome" 

STUDENT_COVARS = ["GPA", "female", "pell", "veteran", "student_year", "grad_student"]
IPEDS_COVARS   = ["hbcu", "hsi_proxy", "r1_r2", "admissions_rate",
                  "grad_rate_6yr_overall"]

MILITARY_COVARS    = ["mil_affil", "dod_scholar", "dod_interest_high"]
ROTC_BRANCH_COVARS = ["rotc_air_force", "rotc_army"]  # reference: non-ROTC

# Extended IPEDS covariates including public/land-grant flags for interactions
IPEDS_EXTENDED = ["hbcu", "hsi_proxy", "r1_r2", "public", "land_grant_flag",
                  "admissions_rate", "grad_rate_6yr_overall"]


# Data loading
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and return (vsa, ipeds) as raw DataFrames."""
    vsa   = pd.read_csv(VSA_PATH)
    ipeds = pd.read_csv(IPEDS_PATH)
    return vsa, ipeds


# Feature engineering — student level
def _combined_race_eth(row: pd.Series) -> str:
    """OMB convention: Hispanic takes precedence, then Race field."""
    eth  = str(row.get("Ethnicity", "")).strip()
    race = str(row.get("Race", "")).strip()
    if eth == "Hispanic or Latino":
        return "Hispanic"
    if race == "White":
        return "White_NH"
    if race == "Black or African American":
        return "Black_NH"
    if race == "Asian":
        return "Asian_NH"
    return "Other_NH"  


def engineer_student_features(vsa: pd.DataFrame) -> pd.DataFrame:
    """
    Add engineered student-level columns to the VSA dataframe.
    """
    df = vsa.copy()

    # Outcomes — handle both bool (True/False) and float (1.0/NaN) from CSV 
    df["inst_selected"] = df["Institution_Selection"].fillna(False).astype(bool).astype(int)
    df["lms_onboarded"] = df["LMS_Onboarded"].fillna(False).astype(bool).astype(int)
    df["accepted"]      = ((df["inst_selected"] == 1) |
                            (df["lms_onboarded"] == 1)).astype(int)

    # Race/ethnicity (OMB combined)
    df["race_eth"] = df.apply(_combined_race_eth, axis=1)

    # GPA
    df["GPA"] = pd.to_numeric(df["GPA"], errors="coerce")

    # Binary / ordinal predictors
    df["female"] = (df["Sex"] == "Female").astype(int)
    df["pell"] = df["PellGrantTF"].map({"Yes": 1, "No": 0})
    df["veteran"] = df["VeteranTF"].map({"Yes": 1, "No": 0})
    df["us_citizen"] = df["CountryOfCitizenship"].isin(
                            ["US Citizen", "US Dual Citizen"]).astype(int)
    df["student_year"] = df["StudentClass"].map(
                            {"1st Year": 1, "2nd Year": 2, "3rd Year": 3,
                             "4th Year": 4, "5th Year": 5, "6th Year": 6})
    df["grad_student"] = df["DegreeType"].isin(
                            ["Master's Degree",
                             "Doctoral Degree (Ph.D., Ed.D., etc.)"]).astype(int)

    return df

# Feature engineering — military / DoD pipeline
def engineer_military_features(vsa: pd.DataFrame) -> pd.DataFrame:
    """
    Add military/DoD pipeline columns to a VSA dataframe that has already
    been processed by engineer_student_features().
    """
    df = vsa.copy()

    cadet = df.get("CadetCorpTF", pd.Series(dtype=str)).eq("Yes")
    rotc  = (df.get("ROTCBranch", pd.Series(dtype=str)).notna() &
             df.get("ROTCBranch", pd.Series(dtype=str)).ne("") &
             df.get("ROTCBranch", pd.Series(dtype=str)).ne("nan"))
    df["mil_affil"] = (cadet | rotc).astype(int)

    df["rotc_air_force"] = (df.get("ROTCBranch", pd.Series(dtype=str)) == "Air Force").astype(int)
    df["rotc_army"]      = (df.get("ROTCBranch", pd.Series(dtype=str)) == "Army").astype(int)

    sfs   = df.get("SFSTF",   pd.Series(dtype=str)).eq("Yes")
    smart = df.get("SMARTTF", pd.Series(dtype=str)).eq("Yes")
    csa   = df.get("CSATF",   pd.Series(dtype=str)).eq("Yes")
    df["dod_scholar"] = (sfs | smart | csa).astype(int)

    df["dod_interest_high"] = (df.get("DoD_Job_Interest", pd.Series(dtype=str)) == "Yes").astype(int)

    rotc_cohort = df.get("ROTC_Cohort_Selected", pd.Series(dtype=object)).fillna(False).astype(bool)
    df["rotc_cohort_outcome"] = rotc_cohort.astype(int)

    return df


# Feature engineering — institution level (IPEDS)
def engineer_ipeds_features(ipeds: pd.DataFrame) -> pd.DataFrame:
    """
    Add engineered institution-level columns to the IPEDS dataframe.

    hsi_proxy    : int   1 if pct_hispanic >= 0.25 (federal HSI definition proxy)
    msi          : int   1 if HBCU or HSI
    selectivity  : str   Tier label derived from admissions_rate
    r1_r2        : int   1 if Carnegie R1 or R2
    """
    df = ipeds.copy()

    df["hsi_proxy"] = (df["pct_hispanic"].fillna(0) >= 0.25).astype(int)
    df["msi"]       = ((df["hbcu"] == 1) | (df["hsi_proxy"] == 1)).astype(int)
    df["r1_r2"]     = df["carnegie_label"].isin([
        "R1: Doctoral – Very High Research",
        "R2: Doctoral – High Research",
        "Research Universities (high research activity)",
    ]).astype(int)

    def _selectivity(rate):
        if pd.isna(rate) or rate >= 0.90:
            return "Open_Access"
        elif rate >= 0.65:
            return "Less_Selective"
        elif rate >= 0.40:
            return "Selective"
        else:
            return "Highly_Selective"

    df["selectivity"] = df["admissions_rate"].apply(_selectivity)
    return df


def engineer_ipeds_extended(ipeds: pd.DataFrame) -> pd.DataFrame:
    """
    Extend an IPEDS dataframe (already processed by engineer_ipeds_features)
    with additional flags needed for cross-level interaction models.
    """
    df = ipeds.copy()

    df["public"]          = (df["inst_control"] == 1).astype(int)
    df["land_grant_flag"] = df["land_grant"].fillna(0).astype(int)
    df["urban_locale"]    = df["locale"].isin([11, 12, 13]).astype(int)
    df["inst_size_large"] = (df["inst_size"] == 5).astype(int)

    return df


# Merge
def merge_ipeds(vsa: pd.DataFrame, ipeds: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join VSA with IPEDS on Institution / school_name.

    7 VSA institutions do not match any school_name in ipeds_school_data.csv:
    These applicants are excluded from IPEDS-merged models via dropna.
    """
    ipeds_cols = ["school_name", "inst_control", "hbcu", "hsi_proxy", "msi",
                  "selectivity", "r1_r2", "admissions_rate",
                  "grad_rate_6yr_overall", "land_grant", "locale", "inst_size"]
    merged = vsa.merge(
        ipeds[ipeds_cols],
        left_on="Institution",
        right_on="school_name",
        how="left",
    )
    unmatched = merged.loc[merged["hbcu"].isna(), "Institution"].unique()
    if len(unmatched):
        print(f"⚠️  {len(unmatched)} institutions unmatched to IPEDS "
              f"({merged['hbcu'].isna().sum()} applicants excluded from merged models):")
        for s in sorted(unmatched):
            print(f"   • {s}")
    return merged


# Utility — ICC decomposition
def compute_icc(y: pd.Series, groups: pd.Series) -> dict:
    """
    Compute the naive (one-way ANOVA) ICC for a binary outcome.

    Quantifies the proportion of total outcome variance attributable to
    between-institution differences — the primary justification for GEE.

    Returns
    dict with keys: between_var, within_var, icc, n_groups, n_obs, group_means
    """
    df = pd.DataFrame({"y": y.values, "g": groups.values}).dropna()
    grand_mean  = df["y"].mean()
    group_stats = df.groupby("g")["y"].agg(["mean", "count"])

    ss_between = ((group_stats["mean"] - grand_mean) ** 2 * group_stats["count"]).sum()
    df_between = len(group_stats) - 1

    group_mean_map = group_stats["mean"].to_dict()
    ss_within  = ((df["y"] - df["g"].map(group_mean_map)) ** 2).sum()
    df_within  = len(df) - len(group_stats)

    ms_between = ss_between / df_between if df_between > 0 else np.nan
    ms_within  = ss_within  / df_within  if df_within  > 0 else np.nan

    k      = len(group_stats)
    n_avg  = (len(df) - (group_stats["count"] ** 2).sum() / len(df)) / (k - 1)
    n_avg  = max(n_avg, 1e-9)

    between_var = max((ms_between - ms_within) / n_avg, 0.0)
    within_var  = ms_within if not np.isnan(ms_within) else 0.0
    denom       = between_var + within_var

    return {
        "between_var": between_var,
        "within_var":  within_var,
        "icc":         between_var / denom if denom > 0 else np.nan,
        "n_groups":    k,
        "n_obs":       len(df),
        "group_means": group_stats["mean"].sort_values(),
    }


# Utility — interaction term builder
def add_interactions(X: pd.DataFrame,
                     pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """
    Append multiplicative interaction columns to a design matrix.
    """
    X_out = X.copy()
    for col_a, col_b in pairs:
        X_out[f"{col_a}_x_{col_b}"] = X_out[col_a] * X_out[col_b]
    return X_out


# Model — GEE logistic (primary model)
def run_gee_logistic(
    df: pd.DataFrame,
    outcome: str,
    covars: list[str],
    group_col: str = "Institution",
    cov_struct: str = "exchangeable",
    center_gpa: bool = True,
) -> object:
    """
    Fit a population-averaged logistic GEE model clustered by group_col.

    Parameters
    df         : merged VSA + IPEDS dataframe with engineered features;
                 eligibility filter (GPA >= 3.2, us_citizen == 1) applied upstream
    outcome    : binary outcome column name (OUTCOME or OUTCOME_ROTC)
    covars     : list of numeric covariate column names
    group_col  : clustering variable (default: 'Institution')
    cov_struct : 'exchangeable' (default) or 'independence' (sensitivity check)
    center_gpa : demean GPA before fitting; recommended for interaction models

    Returns
    GEEResultsWrapper — key attributes: .params, .pvalues, .conf_int(), .bse, .qic()
    """

    cols_needed = [outcome, group_col] + covars
    sub = df[cols_needed].dropna().copy()

    if center_gpa and "GPA" in sub.columns:
        sub["GPA"] = sub["GPA"] - sub["GPA"].mean()

    sub    = sub.sort_values(group_col).reset_index(drop=True)
    y      = sub[outcome].astype(float)
    X      = sm.add_constant(sub[covars].astype(float))
    groups = sub[group_col]

    cov_obj = Exchangeable() if cov_struct == "exchangeable" else Independence()

    return GEE(y, X, groups=groups,
               family=families.Binomial(),
               cov_struct=cov_obj).fit()


# Results formatting — GEE odds ratio table
def gee_or_table(result) -> pd.DataFrame:
    """
    Return a tidy DataFrame of odds ratios, 95% CIs, and p-values from a
    GEEResultsWrapper.
    """
    ci = result.conf_int()
    return pd.DataFrame({
        "OR":       np.exp(result.params),
        "CI_lower": np.exp(ci.iloc[:, 0]),
        "CI_upper": np.exp(ci.iloc[:, 1]),
        "p_value":  result.pvalues,
    }).round(4)
