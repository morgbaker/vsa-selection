"""
fetch_ipeds.py
Fetches IPEDS data from the Urban Institute Education Data API for all matched schools.
Endpoints used (year=2022):
  - ipeds/directory/          → Carnegie classification, public/private, inst size, HBCU
  - ipeds/admissions-enrollment/ → admissions rate, total enrolled
  - ipeds/grad-rates/         → 6-year completion rates (overall + by race)
  - ipeds/institutional-characteristics/ → Pell grant, room/board (bonus fields)

Race codes (grad-rates + fall-enrollment):
  1=White, 2=Black, 3=Hispanic, 4=Asian,
  5=American Indian, 6=Pacific Islander, 7=Two or more, 8=Non-resident, 9=Unknown, 99=Total

Carnegie basic codes (cc_basic_2021):
  15=R1 (Doctoral – Very High Research), 16=R2 (Doctoral – High Research),
  17=Doctoral/Professional, 18=Master's: Larger,  19=Master's: Medium, 20=Master's: Small,
  21=Baccalaureate: Arts & Sciences, 22=Baccalaureate: Diverse, 23=Baccalaureate/Associate's,
  14=Research Colleges and Universities, others coded accordingly.

inst_control codes:  1=Public, 2=Private not-for-profit, 3=Private for-profit
"""

import requests
import pandas as pd
import time

# ── Config ─────────────────────────────────────────────────────────────────────
BASE = "https://educationdata.urban.org/api/v1/college-university"
YEAR = 2022
SLEEP = 0.25   # seconds between requests (be polite to the API)

CARNEGIE_LABELS = {
    -2: "Not applicable",
    -1: "Not reported",
    1:  "Associate's: Public two-year",
    2:  "Associate's: Public four-year",
    3:  "Associate's: Private not-for-profit",
    4:  "Associate's: Private for-profit",
    10: "Special Focus: Two-Year",
    11: "Special Focus: Four-Year",
    12: "Tribal",
    13: "Other",
    14: "Research Universities (high research activity)",
    15: "R1: Doctoral – Very High Research",
    16: "R2: Doctoral – High Research",
    17: "Doctoral/Professional",
    18: "Master's: Larger Programs",
    19: "Master's: Medium Programs",
    20: "Master's: Small Programs",
    21: "Baccalaureate: Arts & Sciences",
    22: "Baccalaureate: Diverse Fields",
    23: "Baccalaureate/Associate's",
}

CONTROL_LABELS = {
    1: "Public",
    2: "Private not-for-profit",
    3: "Private for-profit",
}

RACE_NAMES = {
    1: "white", 2: "black", 3: "hispanic", 4: "asian",
    5: "american_indian", 6: "pacific_islander", 7: "two_or_more",
    8: "nonresident", 9: "unknown",
}

# ── Helper ─────────────────────────────────────────────────────────────────────
def api_get(endpoint, params=None):
    """GET a single-page Urban Institute API result; returns list of result dicts."""
    url = f"{BASE}/ipeds/{endpoint}/{YEAR}/"
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("results", [])
    return []

# ── Fetch functions per endpoint ───────────────────────────────────────────────
def fetch_directory(unitid):
    rows = api_get("directory", {"unitid": unitid})
    if not rows:
        return {}
    r = rows[0]
    cc = r.get("cc_basic_2021", -1)
    ctrl = r.get("inst_control", -1)
    return {
        "inst_name_ipeds"    : r.get("inst_name"),
        "inst_control"       : ctrl,
        "inst_control_label" : CONTROL_LABELS.get(ctrl, "Unknown"),
        "carnegie_basic_2021": cc,
        "carnegie_label"     : CARNEGIE_LABELS.get(cc, f"Code {cc}"),
        "inst_size"          : r.get("inst_size"),
        "hbcu"               : r.get("hbcu"),
        "land_grant"         : r.get("land_grant"),
        "locale"             : r.get("urban_centric_locale"),
    }

def fetch_admissions(unitid):
    """Returns sex=99 (total) row from admissions-enrollment."""
    rows = api_get("admissions-enrollment", {"unitid": unitid})
    total = next((r for r in rows if r.get("sex") == 99), None)
    if not total:
        return {}
    applied   = total.get("number_applied")
    admitted  = total.get("number_admitted")
    enrolled  = total.get("number_enrolled_total")
    adm_rate  = round(admitted / applied, 4) if applied and applied > 0 else None
    return {
        "total_applied"   : applied,
        "total_admitted"  : admitted,
        "total_enrolled"  : enrolled,
        "admissions_rate" : adm_rate,
    }

def fetch_grad_rates(unitid):
    """Returns overall + per-race 6-yr completion rates from subcohort=99."""
    rows = api_get("grad-rates", {"unitid": unitid})
    # Use subcohort=99 rows (all students, not just Pell/loan subgroup)
    sc99 = [r for r in rows if r.get("subcohort") == 99 and r.get("institution_level") == 4]

    # Overall: race=99, sex=99
    overall_rows = [r for r in sc99 if r.get("race") == 99 and r.get("sex") == 99]
    overall_rate = overall_rows[0].get("completion_rate_150pct") if overall_rows else None

    # Per-race (sex=99 rows)
    race_rates = {}
    race_cohorts = {}
    for r in sc99:
        race = r.get("race")
        if race in RACE_NAMES and r.get("sex") == 99:
            name = RACE_NAMES[race]
            race_rates[f"grad_rate_{name}"] = r.get("completion_rate_150pct")
            race_cohorts[f"cohort_n_{name}"] = r.get("cohort_adj_150pct")

    # Diversity: share of each race in total cohort (sex=99 rows, race != 99)
    # Use cohort_adj_150pct as proxy for total enrollment composition
    total_cohort = sum(
        v for k, v in race_cohorts.items() if v is not None
    )
    diversity = {}
    if total_cohort > 0:
        for r in sc99:
            race = r.get("race")
            if race in RACE_NAMES and r.get("sex") == 99:
                name = RACE_NAMES[race]
                n = r.get("cohort_adj_150pct")
                diversity[f"pct_{name}"] = round(n / total_cohort, 4) if n else None

    return {
        "grad_rate_6yr_overall": overall_rate,
        **race_rates,
        **race_cohorts,
        **diversity,
    }


# ── Main fetch loop ────────────────────────────────────────────────────────────
_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)
_INTERIM_DIR  = os.path.join(_ROOT, "data", "interim")
_PROCESSED_DIR = os.path.join(_ROOT, "data", "processed")

def fetch_all(
    schools_csv=os.path.join(_INTERIM_DIR, "schools_with_unitids.csv"),
    out_csv=os.path.join(_PROCESSED_DIR, "ipeds_school_data.csv"),
):
    schools = pd.read_csv(schools_csv)
    # Only fetch schools that have a UNITID
    schools = schools[schools["UNITID"].notna()].copy()
    schools["UNITID"] = schools["UNITID"].astype(int)

    records = []
    n = len(schools)
    for i, row in schools.iterrows():
        uid  = row["UNITID"]
        name = row["school_name"]
        print(f"[{len(records)+1}/{n}] Fetching unitid={uid}  {name}")

        rec = {"unitid": uid, "school_name": name, "ipeds_name": row.get("ipeds_name"), "year": YEAR}
        rec.update(fetch_directory(uid));     time.sleep(SLEEP)
        rec.update(fetch_admissions(uid));    time.sleep(SLEEP)
        rec.update(fetch_grad_rates(uid));    time.sleep(SLEEP)
        records.append(rec)

    df = pd.DataFrame(records)

    # Reorder columns logically
    front_cols = ["unitid", "school_name", "ipeds_name", "year",
                  "inst_control", "inst_control_label",
                  "carnegie_basic_2021", "carnegie_label",
                  "inst_size", "hbcu", "land_grant", "locale",
                  "total_applied", "total_admitted", "total_enrolled", "admissions_rate",
                  "grad_rate_6yr_overall"]
    other_cols = [c for c in df.columns if c not in front_cols]
    df = df[front_cols + other_cols]

    df.to_csv(out_csv, index=False)
    print(f"\nSaved {len(df)} rows to {out_csv}")
    return df


if __name__ == "__main__":
    df = fetch_all()
    print(df[["school_name", "inst_control_label", "carnegie_label",
              "admissions_rate", "grad_rate_6yr_overall"]].to_string())
