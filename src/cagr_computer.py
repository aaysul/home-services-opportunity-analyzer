# CAGR computation (2021-2025)


import pandas as pd
import numpy as np

# Load dataset and parse dates
print("🔄 Loading data...")
df = pd.read_csv("hs_states_demand_2021-2025.csv")
df["date"] = pd.to_datetime(df["date"])  # convert string -> datetime
df["year"] = df["date"].dt.year         # extract year for grouping

# Fixed list of service columns to analyze (must match CSV column names)
services = [
    "Asphalt/concrete work",
    "Driveway sealing",
    "Gutter cleaning",
    "Junk removal",
    "Pressure washing",
    "Soft washing",
    "Tree service",
    "Window cleaning",
]

# Quick dataset summary
print(f"✅ Data loaded: {df.shape[0]:,} rows, {len(services)} services")
print(f"📅 Years: {sorted(df['year'].unique())}")
print(f"🗺️ States: {len(df['geo'].unique())}")

# Step 1: Compute annual average demand per state and year
# Group by state (geo) and year, compute mean for each service column.
annual_avg = (
    df.groupby(["geo", "year"])[services]
    .mean()
    .reset_index()
)
print(f"✅ Annual averages computed: {annual_avg.shape[0]} rows")

# Step 2: Select start (2021) and end (2025) matrices for CAGR calculation
# Set index to 'geo' so returned DataFrames align by state.
start_data = annual_avg[annual_avg["year"] == 2021].set_index("geo")[services]
end_data = annual_avg[annual_avg["year"] == 2025].set_index("geo")[services]

# Defensive check: ensure the two matrices have the same states (indices)
common_states = start_data.index.intersection(end_data.index)
if len(common_states) < len(start_data.index) or len(common_states) < len(end_data.index):
    missing_start = end_data.index.difference(start_data.index)
    missing_end = start_data.index.difference(end_data.index)
    print("⚠️ Warning: mismatched state coverage between 2021 and 2025:")
    if not missing_start.empty:
        print(f"  - States present in 2025 but missing in 2021: {list(missing_start)[:6]}{'...' if len(missing_start)>6 else ''}")
    if not missing_end.empty:
        print(f"  - States present in 2021 but missing in 2025: {list(missing_end)[:6]}{'...' if len(missing_end)>6 else ''}")
    # Restrict calculation to common states to avoid misalignment
    start_data = start_data.loc[common_states]
    end_data = end_data.loc[common_states]

# Step 3: CAGR calculation function
def calc_cagr_matrix(end, start, years=4):
    """
    Compute CAGR matrix over `years` years:
    CAGR = (end / start)^(1/years) - 1

    Args:
        end: (n_states, n_services) DataFrame, end-year values (2025)
        start: (n_states, n_services) DataFrame, start-year values (2021)
        years: number of years between start and end (2021–2025 → 4 years)

    Returns:
        DataFrame of CAGR values (same shape as `end`), in decimal (e.g., 0.03 = 3%).
    """
    # Convert to numpy arrays for elementwise math
    start_vals = start.to_numpy(dtype=float)
    end_vals = end.to_numpy(dtype=float)

    # Replace non-positive values with 1.0 to avoid division by zero or negative growth artifacts.
    # This choice treats zero/negative reported averages as a baseline of 1 unit.
    # If you'd prefer NaN propagation instead, remove these replacements.
    start_vals = np.where(start_vals <= 0, 1.0, start_vals)
    end_vals = np.where(end_vals <= 0, 1.0, end_vals)

    # Compute CAGR (decimal)
    cagr = (end_vals / start_vals) ** (1.0 / years) - 1.0

    # Return a DataFrame with the same index/columns as `end`
    return pd.DataFrame(cagr, index=end.index, columns=end.columns)

# Step 4: Compute CAGR (2021–2025, 4-year interval)
cagr_decimal = calc_cagr_matrix(end_data, start_data, years=4)

# Convert to percentage scale (0–100)
cagr_pct = cagr_decimal * 100.0

print("✅ CAGR (2021–2025) calculated!")
# Show global min/max across the matrix, handling potential NaNs
min_pct = cagr_pct.min().min()
max_pct = cagr_pct.max().max()
print(f"📈 CAGR range (pct): {min_pct:.2f}% to {max_pct:.2f}%")

# Step 5: Example analysis for one service (Junk removal)
print("\n" + "="*80)
print("🏆 TOP 10 STATES BY JUNK REMOVAL CAGR (2021–2025)")
print("="*80)
# Sort descending and show top 10; round for display
print(cagr_pct["Junk removal"].sort_values(ascending=False).head(10).round(2))

# Step 6: Summary statistics for all services (CAGR %)
print("\n📊 CAGR SUMMARY STATS (pct points):")
print(cagr_pct.describe().round(3))

# Step 7: Save CAGR table for downstream ZIP-level analyzer
df_cagr_detailed = cagr_pct.reset_index()
df_cagr_detailed = df_cagr_detailed.round(3)  # round to 3 decimals (pct)
df_cagr_detailed.to_csv("demand_cagr_by_state.csv", index=False)

print("\n" + "="*80)
print("💾 SAVED: demand_cagr_by_state.csv")
print(f"📋 Columns: {list(df_cagr_detailed.columns)}")
print("✅ CAGR table READY FOR ZIP CROSSWALK MERGE!")

print("\nSample (CAGR %):")
print(df_cagr_detailed[["geo", "Junk removal", "Tree service", "Window cleaning"]].head(10))

# Step 8: Identify "hot" states by average CAGR across services
print("\n🔥 HOT STATES (avg CAGR > 3.0%):")
# Compute mean across service columns by row (axis=1)
avg_cagr = cagr_pct.mean(axis=1).round(3)

# Filter and sort states exceeding the threshold
hot_states = avg_cagr[avg_cagr > 3.0].sort_values(ascending=False)
print(hot_states.head(10))