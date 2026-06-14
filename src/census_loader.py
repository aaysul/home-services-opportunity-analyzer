# ACS Census data loader

# Import required libraries
import pandas as pd
import numpy as np

# Columns to read from ACS DP04 (Housing characteristics)
# DP04_0001E = Total households (used as denominator for rates)
# DP04_0007E = Owner-occupied households (homeownership)
# DP04_0032E..DP04_0037E = housing age buckets (1970-1999 and older)
dp04_cols = ['GEO_ID', 'NAME', 'DP04_0001E', 'DP04_0007E',
             # Housing age buckets (exclude recent/newer buckets)
             'DP04_0032E', 'DP04_0033E', 'DP04_0034E',
             'DP04_0035E', 'DP04_0036E', 'DP04_0037E'
            ]

# Columns to read from ACS DP03 (Income)
# DP03_0062E = Median household income estimate
dp03_cols = ['GEO_ID', 'DP03_0062E']

# Columns to read from ACS DP02 (Household size distribution)
# DP02_0001E = Total households (should match DP04_0001E if same universe)
# DP02_0008E..DP02_0011E = counts for 4-,5-,6-,7+ person households
dp02_cols = [
    'GEO_ID',
    'DP02_0001E',
    'DP02_0008E',
    'DP02_0009E',
    'DP02_0010E',
    'DP02_0011E'
]

# Load datasets using only selected columns to reduce memory usage
dp04 = pd.read_csv('Datasets/ACSDP5Y2023.DP04-Data.csv', usecols=dp04_cols, low_memory=False)
dp03 = pd.read_csv('Datasets/ACSDP5Y2023.DP03-Data.csv', usecols=dp03_cols, low_memory=False)
dp02 = pd.read_csv('Datasets/ACSDP5Y2023.DP02-Data.csv', usecols=dp02_cols, low_memory=False)

# Merge datasets on GEO_ID to create a single dataframe with needed variables
# Use an inner merge by default; adjust if you need left/right joins
df = dp04.merge(dp03, on='GEO_ID').merge(dp02, on='GEO_ID')

# Convert selected columns to numeric, coercing non-numeric to NaN.
# This prevents type errors during arithmetic and ensures NaNs propagate for missing data.
numeric_cols = [
    'DP04_0001E', 'DP04_0007E', 'DP03_0062E',
    'DP02_0001E', 'DP02_0008E', 'DP02_0009E', 'DP02_0010E', 'DP02_0011E',
    'DP04_0032E', 'DP04_0033E', 'DP04_0034E', 'DP04_0035E', 'DP04_0036E', 'DP04_0037E'
]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Calculate counts and percentages used for filtering and output

# large_households: sum of 4-,5-,6-,7+ person households
df['large_households'] = (df['DP02_0008E'] + df['DP02_0009E'] +
                          df['DP02_0010E'] + df['DP02_0011E'])

# pct_large_households: proportion of households that are 4+ person
# Use DP02_0001E (total households from DP02). If zero or NaN, result becomes NaN.
df['pct_large_households'] = df['large_households'] / df['DP02_0001E']

# homeownership_rate: owner-occupied households divided by total households (DP04)
# If DP04_0001E is zero/NaN, result will be NaN (safe division).
df['homeownership_rate'] = df['DP04_0007E'] / df['DP04_0001E']

# pct_old_housing: proportion of housing units built 1999 or earlier (approx. 25+ years)
# older_housing_cols are the buckets representing older construction years
older_housing_cols = ['DP04_0032E', 'DP04_0034E', 'DP04_0035E', 'DP04_0036E', 'DP04_0037E']
df['pct_old_housing'] = df[older_housing_cols].sum(axis=1) / df['DP04_0001E']

# Optional: If you prefer to treat NaN rates as 0 for filtering, uncomment next two lines
# df[['pct_large_households','homeownership_rate','pct_old_housing']] = df[['pct_large_households','homeownership_rate','pct_old_housing']].fillna(0)

# Apply filtering criteria:
# - Homeownership rate > 60%
# - Median household income > $75,000
# - >25% households are large (4+ persons)
# - >50% housing stock is older than ~25 years
filtered = df[
    (df['homeownership_rate'] > 0.6) &
    (df['DP03_0062E'] > 75000) &
    (df['pct_large_households'] > 0.25) &
    (df['pct_old_housing'] > 0.5)
].copy()

# Prepare final output columns, round rates to 3 decimal places for readability
result = filtered[['GEO_ID', 'NAME', 'homeownership_rate', 'DP03_0062E', 'pct_large_households', 'pct_old_housing']].round(3)
result.columns = ['GEO_ID', 'Geography', 'Homeownership%', 'MedianIncome', 'LargeHH%', 'OldHouse%']

# Print summary and save to CSV
print(f"Found {len(result)} matching geographies:")
print(result.head(10))
result.to_csv('Datasets/busy_families_housing.csv', index=False)