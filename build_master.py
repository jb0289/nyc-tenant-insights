"""
Master data pipeline using PLUTO as the base of every Manhattan residential building.
Complaints + violations get LEFT JOINed onto PLUTO.
Buildings with no record get Grade A+.
"""
import pandas as pd
import re
import datetime
from pathlib import Path

# ===== Address normalization =====
def normalize_address(addr):
    if pd.isna(addr) or addr == '':
        return ''
    s = str(addr).strip().upper()
    s = re.sub(r'\s+(APT|UNIT|#|STE|SUITE).*$', '', s)
    s = re.sub(r'\bWEST\b', 'W', s)
    s = re.sub(r'\bEAST\b', 'E', s)
    s = re.sub(r'\bNORTH\b', 'N', s)
    s = re.sub(r'\bSOUTH\b', 'S', s)
    s = re.sub(r'\bSTREET\b', 'ST', s)
    s = re.sub(r'\bAVENUE\b', 'AVE', s)
    s = re.sub(r'\bBOULEVARD\b', 'BLVD', s)
    s = re.sub(r'\bPLACE\b', 'PL', s)
    s = re.sub(r'\bROAD\b', 'RD', s)
    s = re.sub(r'\bDRIVE\b', 'DR', s)
    s = re.sub(r'\bPARKWAY\b', 'PKWY', s)
    s = re.sub(r'(\d+)(ST|ND|RD|TH)\b', r'\1', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


# ===== Step 1: Load PLUTO as master =====
print("Loading PLUTO master...")
pluto = pd.read_csv('data/pluto/pluto_manhattan.csv', dtype={'zipcode': str}, low_memory=False)
pluto['address_norm'] = pluto['address'].apply(normalize_address)
pluto['zip_str'] = pluto['zipcode'].str[:5]

# Filter to residential buildings only
# Residential building classes: A, B, C, D, R (apartments, walk-ups, elevator, condos, condos)
pluto['bldg_letter'] = pluto['bldgclass'].astype(str).str[0]
residential = pluto[pluto['bldg_letter'].isin(['A', 'B', 'C', 'D', 'R'])].copy()
residential = residential[residential['unitsres'] > 0]
print(f"  Residential buildings in PLUTO: {len(residential):,}")

# Some addresses are duplicated in PLUTO (multiple tax lots same address) — keep highest unit count
master = residential.sort_values('unitsres', ascending=False).drop_duplicates(['address_norm', 'zip_str'])
print(f"  Unique residential addresses: {len(master):,}")

# Keep only fields we need
master = master[['address_norm', 'zip_str', 'unitsres', 'unitstotal', 'yearbuilt', 'numfloors', 'bldgarea', 'bldgclass', 'ownername', 'latitude', 'longitude', 'exempttot']].rename(columns={'address_norm': 'address', 'zip_str': 'zip_code'})


# ===== Step 2: Load and aggregate 311 complaints =====
print("\nLoading 311 complaints...")
complaints = pd.read_csv('data/erm2-nwe9.csv', low_memory=False)
complaints['incident_address'] = complaints['incident_address'].astype(str).apply(normalize_address)
complaints['incident_zip'] = complaints['incident_zip'].astype(str).str[:5]
complaints['created_date'] = pd.to_datetime(complaints['created_date'], errors='coerce')
complaints['is_open'] = complaints['status'].astype(str).str.upper() != 'CLOSED'

complaint_agg = complaints.groupby(['incident_address', 'incident_zip']).agg(
    complaint_count=('unique_key', 'count'),
    open_complaints=('is_open', 'sum'),
    top_complaint=('complaint_type', lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'N/A'),
    last_complaint_date=('created_date', 'max')
).reset_index()
complaint_agg = complaint_agg.rename(columns={'incident_address': 'address', 'incident_zip': 'zip_code'})
complaint_agg['last_complaint_date'] = complaint_agg['last_complaint_date'].dt.strftime('%Y-%m-%d')
print(f"  Buildings with complaints: {len(complaint_agg):,}")


# ===== Step 3: Load and aggregate violations =====
print("\nLoading HPD violations...")
violations = pd.read_csv('data/wvxf-dwi5.csv', low_memory=False)
violations['housenumber'] = violations['housenumber'].astype(str).str.strip()
violations['streetname'] = violations['streetname'].astype(str).str.strip().str.upper()
violations['raw_address'] = (violations['housenumber'] + ' ' + violations['streetname']).str.strip()
violations['address'] = violations['raw_address'].apply(normalize_address)
violations['zip_code'] = violations['zip'].astype(str).str[:5]
violations['inspectiondate'] = pd.to_datetime(violations['inspectiondate'], errors='coerce')
violations['class'] = violations['class'].astype(str).str.upper().str[0]
violations['severity_weight'] = violations['class'].map({'A': 1, 'B': 2, 'C': 5}).fillna(1)
violations['is_open'] = violations['violationstatus'].astype(str).str.upper() == 'OPEN'

violation_agg = violations.groupby(['address', 'zip_code']).agg(
    violation_count=('violationid', 'count'),
    weighted_violations=('severity_weight', 'sum'),
    class_a=('class', lambda x: (x == 'A').sum()),
    class_b=('class', lambda x: (x == 'B').sum()),
    class_c=('class', lambda x: (x == 'C').sum()),
    open_violations=('is_open', 'sum'),
    last_violation_date=('inspectiondate', 'max')
).reset_index()
violation_agg['last_violation_date'] = violation_agg['last_violation_date'].dt.strftime('%Y-%m-%d')
print(f"  Buildings with violations: {len(violation_agg):,}")


# ===== Step 4: LEFT JOIN onto PLUTO master =====
print("\nMerging onto PLUTO master...")
master = master.merge(complaint_agg, on=['address', 'zip_code'], how='left')
master = master.merge(violation_agg, on=['address', 'zip_code'], how='left')

# Fill missing values
fill_zero = ['complaint_count', 'open_complaints', 'violation_count', 'weighted_violations',
             'class_a', 'class_b', 'class_c', 'open_violations']
for col in fill_zero:
    master[col] = master[col].fillna(0).astype(int)
master['top_complaint'] = master['top_complaint'].fillna('No complaints')
master['last_complaint_date'] = master['last_complaint_date'].fillna('N/A')
master['last_violation_date'] = master['last_violation_date'].fillna('N/A')
master['open_complaint_ratio'] = master.apply(
    lambda r: r['open_complaints'] / r['complaint_count'] if r['complaint_count'] > 0 else 0,
    axis=1
).round(2)


# ===== Step 5: Composite quality score =====
today = datetime.date.today()
def recency_boost(date_str):
    if date_str == 'N/A' or pd.isna(date_str):
        return 1.0
    try:
        d = pd.to_datetime(date_str).date()
        days_ago = (today - d).days
        if days_ago <= 30: return 1.5
        elif days_ago <= 90: return 1.3
        elif days_ago <= 365: return 1.1
        else: return 1.0
    except:
        return 1.0

master['recency_multiplier'] = master['last_complaint_date'].apply(recency_boost)
master['open_ratio_penalty'] = master.apply(
    lambda r: r['open_complaint_ratio'] * 50 if r['complaint_count'] >= 5 else 0,
    axis=1
)
master['quality_score_raw'] = (
    (master['complaint_count'] * master['recency_multiplier'])
    + master['weighted_violations']
    + master['open_ratio_penalty']
    + (master['open_violations'] * 2)
)


# ===== Step 6: A+ to F grading =====
def grade_tier(row):
    c = int(row.get('complaint_count', 0))
    v = int(row.get('violation_count', 0))
    o = int(row.get('open_complaints', 0)) + int(row.get('open_violations', 0))
    cc = int(row.get('class_c', 0))
    if c >= 300 or cc >= 11: return 'F'
    if c >= 150 or cc >= 7: return 'D-'
    if c >= 75 or v >= 40 or cc >= 4: return 'D'
    if c >= 40 or v >= 25 or cc >= 3: return 'D+'
    if c >= 25 or v >= 15 or cc >= 2: return 'C-'
    if c >= 15 or v >= 10 or cc >= 1: return 'C'
    if c >= 8 or v >= 5: return 'C+'
    if c >= 5 or v >= 3 or o >= 2: return 'B-'
    if c >= 3 or v >= 2 or o >= 1: return 'B'
    if c >= 1 or v >= 1: return 'B+'
    if c == 0 and v <= 1 and o == 0: return 'A'
    return 'A+'

master['grade'] = master.apply(grade_tier, axis=1)
master['quality_score'] = (master['quality_score_raw'].rank(pct=True) * 100).round(0).astype(int)

master = master.sort_values('quality_score_raw', ascending=False)
master.to_csv('data/buildings_with_pluto.csv', index=False)

print(f"\n=== MASTER DATASET ===")
print(f"Total buildings: {len(master):,}")
order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']
print(master['grade'].value_counts().reindex(order, fill_value=0))

print("\nSample buildings:")
for addr in ['43 GROVE ST', '225 CENTRAL PARK N', '225 CENTRAL PARK W', '149 W 80 ST', '136 W 28 ST']:
    m = master[master['address'] == addr]
    if len(m) > 0:
        r = m.iloc[0]
        print(f"  {addr}: {r['complaint_count']} c / {r['violation_count']} v / Class C={r['class_c']} → {r['grade']}")
    else:
        print(f"  {addr}: NOT FOUND IN PLUTO")
