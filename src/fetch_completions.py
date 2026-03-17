"""
Process NCES IPEDS C2022_A completions data.
Filters to: our 151 schools, bachelor's degrees (AWLEVEL=5), MAJORNUM=1,
and a curated set of ~130 6-digit CIP codes covering the user's 75 disciplines.
Outputs long-form CSV: ipeds_completions_by_cip.csv
"""
import os
import pandas as pd
import zipfile

_ROOT          = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA_DIR       = os.path.join(_ROOT, "data", "raw")       # C2022_A.zip lives here
INTERIM_DIR    = os.path.join(_ROOT, "data", "interim")   # schools_with_unitids.csv
PROCESSED_DIR  = os.path.join(_ROOT, "data", "processed") # output CSV

# ── CIP code label mapping ────────────────────────────────────────────────────
# Keys are floats matching the CIPCODE column (e.g. 11.0701)
# We map CIP code → discipline label
CIP_LABELS = {
    # CIP 11: Computer Science / IT / Security
    "11.0101": "Computer and Information Sciences, General",
    "11.0103": "Information Technology",
    "11.0104": "Informatics",
    "11.0201": "Computer Programming / Information Systems",
    "11.0401": "Information Science/Studies",
    "11.0501": "Information Systems (CIS)",
    "11.0701": "Computer Science",
    "11.0802": "Data Science / Data Analytics",
    "11.0803": "Computer Graphics Technology",
    "11.0804": "Modeling, Virtual Environments and Simulation",
    "11.0901": "Computer Systems Networking / Cloud Computing",
    "11.1001": "Network and System Administration",
    "11.1003": "Cybersecurity / Information Systems Security",
    "11.1004": "Web/Multimedia Management",
    "11.1006": "Computer Support Specialist",
    # CIP 14: Engineering
    "14.0201": "Aerospace Engineering",
    "14.0301": "Agricultural Engineering",
    "14.0501": "Biomedical Engineering",
    "14.0701": "Chemical Engineering",
    "14.0801": "Civil Engineering",
    "14.0901": "Computer Engineering",
    "14.1001": "Electrical Engineering",
    "14.1201": "Engineering Physics",
    "14.1401": "Environmental Engineering",
    "14.1801": "Materials Science and Engineering",
    "14.1901": "Mechanical Engineering",
    "14.2001": "Metallurgical Engineering",
    "14.2301": "Nuclear Engineering",
    "14.2701": "Systems Engineering",
    "14.2901": "Manufacturing Engineering",
    "14.3301": "Construction Engineering",
    "14.3501": "Industrial Engineering",
    "14.3701": "Operations Research (Engineering)",
    "14.3901": "Architectural Engineering",
    "14.4001": "Software Engineering",
    "14.4101": "Mechatronics",
    "14.4201": "Robotics Engineering",
    "14.4301": "Telecommunications Engineering",
    # CIP 15: Engineering Technology
    "15.0303": "Electrical/Electronic Engineering Technology",
    "15.0405": "Robotics Technology",
    "15.0406": "Mechatronics Technology",
    "15.0612": "Industrial Technology",
    "15.0613": "Manufacturing Technology",
    "15.1202": "Computer Technology/Computer Systems Technology",
    "15.0000": "Engineering Technologies, General",
    # CIP 27: Mathematics / Statistics
    "27.0101": "Mathematics, General",
    "27.0301": "Applied Mathematics",
    "27.0303": "Computational Mathematics",
    "27.0304": "Operations Research",
    "27.0501": "Statistics, General",
    "27.0503": "Actuarial Science",
    # CIP 40: Physical Sciences
    "40.0501": "Chemistry",
    "40.0601": "Geology/Earth Science",
    "40.0801": "Physics",
    "40.1001": "Materials Science",
    # CIP 26: Biological Sciences
    "26.0101": "Biology",
    "26.0102": "Biomedical Sciences",
    "26.0210": "Biochemistry",
    "26.0305": "Toxicology",
    "26.1102": "Biostatistics",
    # CIP 52: Business
    "52.0101": "Business/Commerce, General",
    "52.0201": "Business Administration and Management",
    "52.0203": "Logistics / Supply Chain Management",
    "52.0301": "Accounting",
    "52.0408": "Aviation Management",
    "52.0601": "Business Economics",
    "52.0801": "Finance",
    "52.0804": "Personal Financial Planning",
    "52.0901": "Hospitality Administration",
    "52.1001": "Human Resources Management",
    "52.1101": "International Business",
    "52.1201": "Management Information Systems",
    "52.1301": "Management Science / Business Analytics",
    "52.1304": "Actuarial Science (Business)",
    "52.1401": "Marketing",
    "52.1501": "Real Estate",
    "52.1806": "International Trade",
    "52.1902": "Fashion Merchandising",
    # CIP 45: Social Sciences
    "45.0601": "Economics",
    "45.0701": "Geography",
    "45.0901": "International Relations",
    "45.1001": "Political Science / Government",
    "45.1101": "Sociology",
    "45.1201": "Urban Affairs",
    # CIP 42: Psychology
    "42.0101": "Psychology",
    "42.2707": "Forensic Psychology",
    # CIP 43: Criminal Justice / Security
    "43.0103": "Criminal Justice",
    "43.0106": "Forensic Science",
    "43.0116": "Cyber/Computer Forensics",
    "43.0119": "Critical Infrastructure Protection",
    "43.0301": "Homeland Security",
    "43.0302": "Emergency Management",
    "43.0303": "Critical Infrastructure Protection",
    "43.0304": "Counterterrorism",
    # CIP 49: Aviation
    "49.0101": "Aeronautics / Aviation Science",
    "49.0102": "Airline/Commercial Pilot",
    "49.0104": "Aviation/Airway Management",
    # CIP 24: Liberal Arts / Multidisciplinary
    "24.0101": "Liberal Arts / Individualized Studies",
    "24.0102": "General Studies",
    "24.0103": "Humanities",
    # CIP 54: History
    "54.0101": "History",
    # CIP 38: Philosophy
    "38.0101": "Philosophy",
    # CIP 05: Area Studies
    "05.0103": "Asian Studies",
    "05.0107": "Latin American Studies",
    "05.0109": "European Studies",
    "05.0111": "Global Studies / Global Multicultural Studies",
    "05.0125": "Regional Studies",
    # CIP 13: Education
    "13.1210": "Early Childhood Education",
    "13.1202": "Elementary Education",
    # CIP 22: Legal
    "22.0001": "Law, General",
    "22.0301": "Legal Studies",
    # CIP 51: Health / Veterinary
    "51.2401": "Veterinary Medicine / Pre-Vet",
    "30.0000": "Multidisciplinary / Interdisciplinary Studies",
    "30.7001": "Artificial Intelligence (Interdisciplinary)",
    "30.7101": "Data Science (Interdisciplinary)",
}

# Convert to float keys matching the CIPCODE column format
CIP_FLOAT_MAP = {}
for code_str, label in CIP_LABELS.items():
    try:
        CIP_FLOAT_MAP[round(float(code_str), 4)] = label
    except ValueError:
        pass

# ── Race columns in C2022_A ───────────────────────────────────────────────────
RACE_COLS = {
    "CTOTALT" : "Total",
    "CWHITT"  : "White",
    "CBKAAT"  : "Black",
    "CHISPT"  : "Hispanic",
    "CASIAT"  : "Asian",
    "CAIANT"  : "American_Indian",
    "CNHPIT"  : "Pacific_Islander",
    "C2MORT"  : "Two_or_More",
    "CUNKNT"  : "Unknown",
    "CNRALT"  : "Nonresident",
}

# ── Load target schools ───────────────────────────────────────────────────────
print("Loading schools_with_unitids.csv...")
sw = pd.read_csv(os.path.join(INTERIM_DIR, "schools_with_unitids.csv"))
sw = sw[sw["UNITID"].notna()].copy()
sw["UNITID"] = sw["UNITID"].astype(int)
target_unitids = set(sw["UNITID"].tolist())
unitid_to_name = sw.set_index("UNITID")["school_name"].to_dict()
print(f"Target UNITIDs: {len(target_unitids)}")

# ── Load C2022_A ──────────────────────────────────────────────────────────────
print("Loading C2022_A.zip...")
with zipfile.ZipFile(os.path.join(DATA_DIR, "C2022_A.zip")) as z:
    csv_name = [n for n in z.namelist() if n.lower().endswith('.csv') and 'c2022_a' in n.lower()][0]
    with z.open(csv_name) as f:
        raw = pd.read_csv(f, encoding='latin-1', low_memory=False)

raw.columns = [c.strip().lstrip('\ufeff') for c in raw.columns]
print(f"Raw rows: {len(raw):,}")

# ── Apply filters ─────────────────────────────────────────────────────────────
# Filter to target schools
df = raw[raw["UNITID"].isin(target_unitids)].copy()
print(f"After school filter: {len(df):,} rows")

# Filter to bachelor's (AWLEVEL=5) and first major (MAJORNUM=1)
df = df[(df["AWLEVEL"] == 5) & (df["MAJORNUM"] == 1)].copy()
print(f"After bachelor's/majornum filter: {len(df):,} rows")

# Round CIPCODE to 4 decimal places for matching
df["CIPCODE_R"] = df["CIPCODE"].round(4)
target_cips = set(CIP_FLOAT_MAP.keys())
df = df[df["CIPCODE_R"].isin(target_cips)].copy()
print(f"After CIP filter: {len(df):,} rows across {df['CIPCODE_R'].nunique()} unique CIPs")

if len(df) == 0:
    print("\nERROR: No rows matched! Checking what CIP codes exist for our schools...")
    check = raw[(raw["UNITID"].isin(target_unitids)) & (raw["AWLEVEL"] == 5) & (raw["MAJORNUM"] == 1)]
    sample_cips = sorted(check["CIPCODE"].unique()[:30])
    print(f"Sample CIPCODEs in data: {sample_cips}")
    raise SystemExit("No matching rows")

# ── Melt race columns to long form ───────────────────────────────────────────
keep_cols = ["UNITID", "CIPCODE_R"] + list(RACE_COLS.keys())
df = df[keep_cols].copy()

# Replace suppression codes (non-numeric) with 0 or NaN
for col in RACE_COLS:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

df_long = df.melt(
    id_vars=["UNITID", "CIPCODE_R"],
    value_vars=list(RACE_COLS.keys()),
    var_name="race_col",
    value_name="n_awards",
)
df_long["race"] = df_long["race_col"].map(RACE_COLS)
df_long.drop(columns="race_col", inplace=True)

# ── Add labels ────────────────────────────────────────────────────────────────
df_long["school_name"] = df_long["UNITID"].map(unitid_to_name)
df_long["cip_label"]   = df_long["CIPCODE_R"].map(CIP_FLOAT_MAP)
df_long["cipcode_str"] = df_long["CIPCODE_R"].apply(lambda x: f"{x:07.4f}")
df_long["year"] = 2022
df_long["award_level"] = "Bachelor's"

# ── Final column order ────────────────────────────────────────────────────────
df_out = df_long[[
    "UNITID", "school_name", "year", "award_level",
    "cipcode_str", "cip_label",
    "race", "n_awards"
]].rename(columns={"UNITID": "unitid", "cipcode_str": "cipcode"})

df_out = df_out.sort_values(["school_name", "cipcode", "race"]).reset_index(drop=True)

out_path = os.path.join(PROCESSED_DIR, "ipeds_completions_by_cip.csv")
df_out.to_csv(out_path, index=False)
print(f"\nSaved {len(df_out):,} rows → {out_path}")
print(f"Unique schools: {df_out['unitid'].nunique()}")
print(f"Unique CIP codes: {df_out['cipcode'].nunique()}")
print(f"\n── Top 20 CIP code groups by total bachelor's awarded ──")
summary = (
    df_out[df_out["race"] == "Total"]
    .groupby(["cipcode", "cip_label"])["n_awards"]
    .sum()
    .sort_values(ascending=False)
    .head(20)
)
print(summary.to_string())
