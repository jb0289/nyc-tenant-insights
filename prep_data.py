import pandas as pd

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

# ===== ZIP-level aggregation =====
zip_counts = complaints.groupby('incident_zip').size().reset_index(name='complaint_count')
zip_counts = zip_counts.rename(columns={'incident_zip': 'zip_code'})

top_type_per_zip = (
    complaints.groupby(['incident_zip', 'complaint_type'])
    .size()
    .reset_index(name='count')
    .sort_values(['incident_zip', 'count'], ascending=[True, False])
    .groupby('incident_zip')
    .first()
    .reset_index()
    .rename(columns={'incident_zip': 'zip_code', 'complaint_type': 'top_complaint'})
)[['zip_code', 'top_complaint']]

merged = rent.merge(zip_counts, on='zip_code', how='inner')
merged = merged.merge(top_type_per_zip, on='zip_code', how='left')
merged['complaint_percentile'] = (merged['complaint_count'].rank(pct=True) * 100).round(0).astype(int)
merged.to_csv('data/manhattan_final.csv', index=False)
print(f"ZIP-level data saved: {len(merged)} ZIPs")

# ===== Building-level aggregation =====
complaints['incident_address'] = complaints['incident_address'].astype(str).str.strip().str.upper()
complaints = complaints[complaints['incident_address'] != 'NAN']
complaints = complaints[complaints['incident_address'] != '']

building = complaints.groupby(['incident_address', 'incident_zip']).agg(
    complaint_count=('unique_key', 'count'),
    top_complaint=('complaint_type', lambda x: x.mode().iloc[0] if not x.mode().empty else 'Unknown')
).reset_index()
building = building.rename(columns={'incident_address': 'address', 'incident_zip': 'zip_code'})
building = building[building['complaint_count'] >= 3]  # Skip addresses with barely any data
building = building.sort_values('complaint_count', ascending=False)
building.to_csv('data/building_complaints.csv', index=False)
print(f"Building-level data saved: {len(building)} addresses")

# Demo addresses for the Streamlit app. We take the top 20 most-complained buildings spread across ZIPs, plus some low-complaint ones for contrast. We save these to a separate CSV that the app can load without needing to process the entire dataset, which speeds up loading and avoids potential issues with large datasets in Streamlit.
# Top 20 most-complained buildings spread across ZIPs, plus some low-complaint ones for contrast
top_buildings = building.head(30)
low_buildings = building[building['complaint_count'].between(3, 8)].sample(min(10, len(building)), random_state=42)
demo = pd.concat([top_buildings.head(20), low_buildings.head(10)])
demo['display'] = demo['address'] + ', ' + demo['zip_code']
demo[['display', 'address', 'zip_code']].to_csv('data/demo_addresses.csv', index=False)
print(f"Demo addresses saved: {len(demo)} addresses")

print("\nPrep complete. Ready to build the app.")