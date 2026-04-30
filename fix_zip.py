import pandas as pd
df = pd.read_csv('data/buildings_with_pluto.csv', dtype={'zip_code': str})
print(f"Before: '{df.loc[df['address']=='149 W 80 ST', 'zip_code'].iloc[0]}'")
df['zip_code'] = df['zip_code'].str.replace('.0', '', regex=False).str.strip()
df.to_csv('data/buildings_with_pluto.csv', index=False)
df2 = pd.read_csv('data/buildings_with_pluto.csv', dtype={'zip_code': str})
print(f"After:  '{df2.loc[df2['address']=='149 W 80 ST', 'zip_code'].iloc[0]}'")
