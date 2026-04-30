import pandas as pd
import re

# ===== Address normalization function =====
def normalize_address(addr):
    if pd.isna(addr) or addr == '':
        return ''
    s = str(addr).strip().upper()
    # Remove apt/unit suffixes
    s = re.sub(r'\s+(APT|UNIT|#|STE|SUITE).*$', '', s)
    # Standard street type abbreviations
    replacements = {
        r'\bSTREET\b': 'ST', r'\bAVENUE\b': 'AVE', r'\bBOULEVARD\b': 'BLVD',
        r'\bPLACE\b': 'PL', r'\bROAD\b': 'RD', r'\bDRIVE\b': 'DR',
        r'\bPARKWAY\b': 'PKWY', r'\bTERRACE\b': 'TER', r'\bCOURT\b': 'CT',
        r'\bLANE\b': 'LN', r'\bSQUARE\b': 'SQ',
        r'\bWEST\b': 'W', r'\bEAST\b': 'E', r'\bNORTH\b': 'N', r'\bSOUTH\b': 'S',
    }
    for pattern, repl in replacements.items():
        s = re.sub(pattern, repl, s)
    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# ===== Load Zillow rent data =====
zori = pd.read_csv('data/Zip_zori_uc_sfrcondomfr_sm_month.csv')
zori['RegionName'] = zori['RegionName'].astype(str)
manhattan_rent = zori[zori['RegionName'].str.startswith(('100', '101', '102'))]
latest_month = manhattan_rent.columns[-1]
rent = manhattan_rent[['RegionName', latest_month]].rename(
    columns={'RegionName': 'zip_code', latest_month: 'median_rent'}
)
rent = rent.dropna()
rent['median_rent'] = rent['median_rent'].round(0).astype(int)

# ===== Load 311 complaints =====
complaints = pd.read_csv('data/erm2-nwe9.csv')
complaints['incident_zip'] = complaints['incident_zip'].astype(str).str[:5]
complaints['created_date'] = pd.to_datetime(complaints['created_date'], errors='coerce')
complaints['incident_address_norm'] = complaints['incident_address'].apply(normalize_address)
complaints = complaints[complaints['incident_address_norm'] != '']

# ZIP-level
zip_counts = complaints.groupby('incident_zip').size().reset_index(name='complaint_count')
zip_counts = zip_counts.rename(columns={'incident_zip': 'zip_code'})
top_type_per_zip = (
    complaints.groupby(['incident_zip', 'complaint_type']).size()
    .reset_index(name='count').sort_values(['incident_zip', 'count'], ascending=[True, False])
    .groupby('incident_zip').first().reset_index()
    .rename(columns={'incident_zip': 'zip_code', 'complaint_type': 'top_complaint'})
)[['zip_code', 'top_complaint']]
merged = rent.merge(zip_counts, on='zip_code', how='inner')
merged = merged.merge(top_type_per_zip, on='zip_code', how='left')
merged['complaint_percentile'] = (merged['complaint_count'].rank(pct=True) * 100).round(0).astype(int)
merged.to_csv('data/manhattan_final.csv', index=False)
print(f"ZIP-level data saved: {len(merged)} ZIPs")

# Building-level complaints with open/closed split
complaints['is_open'] = complaints['status'].astype(str).str.upper() == 'OPEN'
building = complaints.groupby(['incident_address_norm', 'incident_zip']).agg(
    complaint_count=('unique_key', 'count'),
    open_complaints=('is_open', 'sum'),
    top_complaint=('complaint_type', lambda x: x.mode().iloc[0] if not x.mode().empty else 'Unknown'),
    last_complaint_date=('created_date', 'max')
).reset_index()
building = building.rename(columns={'incident_address_norm': 'address', 'incident_zip': 'zip_code'})
building['last_complaint_date'] = building['last_complaint_date'].dt.strftime('%Y-%m-%d')
building['open_complaint_ratio'] = (building['open_complaints'] / building['complaint_count']).round(2)
# Filter removed

# ===== Load HPD violations with class =====
violations = pd.read_csv('data/wvxf-dwi5.csv')
violations['housenumber'] = violations['housenumber'].astype(str).str.strip()
violations['streetname'] = violations['streetname'].astype(str).str.strip().str.upper()
violations['raw_address'] = (violations['housenumber'] + ' ' + violations['streetname']).str.strip()
violations['address_norm'] = violations['raw_address'].apply(normalize_address)
violations['zip'] = violations['zip'].astype(str).str[:5]
violations['inspectiondate'] = pd.to_datetime(violations['inspectiondate'], errors='coerce')
violations['class'] = violations['class'].astype(str).str.upper().str[0]  # First letter A/B/C

# Severity-weighted violation count
violations['severity_weight'] = violations['class'].map({'A': 1, 'B': 2, 'C': 5}).fillna(1)

v_counts = violations.groupby(['address_norm', 'zip']).agg(
    violation_count=('violationid', 'count'),
    weighted_violations=('severity_weight', 'sum'),
    class_a=('class', lambda x: (x == 'A').sum()),
    class_b=('class', lambda x: (x == 'B').sum()),
    class_c=('class', lambda x: (x == 'C').sum()),
    last_violation_date=('inspectiondate', 'max')
).reset_index()
v_counts = v_counts.rename(columns={'address_norm': 'address', 'zip': 'zip_code'})
v_counts['last_violation_date'] = v_counts['last_violation_date'].dt.strftime('%Y-%m-%d')

open_v = violations[violations['violationstatus'].astype(str).str.upper() == 'OPEN']
open_counts = open_v.groupby(['address_norm', 'zip']).size().reset_index(name='open_violations')
open_counts = open_counts.rename(columns={'address_norm': 'address', 'zip': 'zip_code'})

# Merge
building = building.merge(v_counts, on=['address', 'zip_code'], how='outer')
building = building.merge(open_counts, on=['address', 'zip_code'], how='left')
for col in ['violation_count', 'weighted_violations', 'class_a', 'class_b', 'class_c', 'open_violations']:
    building[col] = building[col].fillna(0).astype(int)
building['last_violation_date'] = building['last_violation_date'].fillna('N/A')

# Fill complaint-side columns for violation-only buildings (NaN -> 0)
for col in ['complaint_count', 'open_complaints']:
    if col in building.columns:
        building[col] = building[col].fillna(0).astype(int)
if 'open_complaint_ratio' in building.columns:
    building['open_complaint_ratio'] = building['open_complaint_ratio'].fillna(0)
if 'last_complaint_date' in building.columns:
    building['last_complaint_date'] = building['last_complaint_date'].fillna('N/A')
if 'top_complaint' in building.columns:
    building['top_complaint'] = building['top_complaint'].fillna('No complaints')

# ===== Composite quality score =====
building['quality_score_raw'] = (
    building['complaint_count']
    + building['weighted_violations']
    + (building['open_complaint_ratio'] * 50)
)
building['quality_score'] = (building['quality_score_raw'].rank(pct=True) * 100).round(0).astype(int)

# Fixed-threshold A+ to F grading based on absolute counts
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

building['grade'] = building.apply(grade_tier, axis=1)

# Keep building_percentile for backwards compat
building['building_percentile'] = building['quality_score']

building = building.sort_values('quality_score_raw', ascending=False)
building.to_csv('data/building_complaints.csv', index=False)
print(f"Building-level data saved: {len(building)} addresses")
print(f"Buildings with violations match: {(building['violation_count'] > 0).sum()}")
print(f"Match rate: {(building['violation_count'] > 0).sum() / len(building) * 100:.1f}%")
print()
print("Grade distribution:")
print(building['grade'].value_counts().sort_index())

# Demo addresses
top_buildings = building.head(20)
mid_buildings = building[building['quality_score'].between(40, 60)].head(5)
low_buildings = building[building['quality_score'] <= 30].head(5)
demo = pd.concat([top_buildings, mid_buildings, low_buildings])
demo['display'] = demo['address'] + ', ' + demo['zip_code']
demo[['display', 'address', 'zip_code']].to_csv('data/demo_addresses.csv', index=False)
print(f"\nDemo addresses saved: {len(demo)} addresses")
print("Prep complete.")
