# ZIP-service opportunity analyzer


"""
Home Services ZIP-Level Opportunity Analyzer (CAGR-Based)

Analyzes ZIP codes × services to find high-opportunity markets based on:
- Census data (homeownership, income, household size)
- Business competition (Yelp scrapes)
- Demand growth (CAGR from pytrends)

Inputs:
- datasets/raw/ACSDP5Y2023.DP04-Data.csv (housing)
- datasets/raw/ACSDP5Y2023.DP03-Data.csv (income)
- datasets/raw/ACSDP5Y2023.DP02-Data.csv (household size)
- datasets/raw/zips_zctas_states.csv (ZIP ↔ ZCTA mapping)
- datasets/scraped/business_count_by_zip_with_reviews.csv (business counts)
- datasets/demand/demand_cagr_by_state.csv (CAGR by state/service)

Output:
- datasets/output/top_zips_by_services_cagr.csv (top opportunities)
"""

import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings("ignore")

print("🔄 HOME SERVICES ANALYZER v2.8 (CAGR-BASED)")
print("=" * 60)

# === DEFAULTS ===
DEFAULT_FILTERS = {
    "homeownership_min": 0.60,
    "income_min": 75000,
    "cagr_min": 20.0,
    "competition_max": 5.0,
    "large_hh_min": 0,
}

DEFAULT_WEIGHTS = {
    "demand": 40,
    "ownership_income": 30,
    "competition": 30,
}

def get_float(prompt, default):
    s = input(prompt).strip()
    if s == "":
        print(f"  → using default: {default}")
        return default
    return float(s)

def get_int(prompt, default):
    s = input(prompt).strip()
    if s == "":
        print(f"  → using default: {default}")
        return int(s)

# === CONFIGURATION ===
print("🔧 CONFIGURATION")
print("-" * 40)

print(f"Default filters (CAGR-based):")
for k, v in DEFAULT_FILTERS.items():
    print(f"  {k}: {v}")
print(f"  Total weight: {sum(DEFAULT_WEIGHTS.values())}")
print()

choice = input("Do you want to customize filters and weights? (y/n): ").strip().lower()
use_defaults = choice != "y"

FILTERS = {}
WEIGHTS = {}

if use_defaults:
    FILTERS = DEFAULT_FILTERS.copy()
    WEIGHTS = DEFAULT_WEIGHTS.copy()
    print("\n✅ Using default configurations.")
else:
    print("\nCONFIGURE FILTERS AND WEIGHTS (CAGR-BASED)")
    print("-" * 40)

    FILTERS["homeownership_min"] = get_float(
        "Homeownership minimum (e.g., 0.60) [Enter for 0.60]: ",
        DEFAULT_FILTERS["homeownership_min"]
    )
    FILTERS["income_min"] = get_float(
        "Income minimum (e.g., 75000) [Enter for 75000]: ",
        DEFAULT_FILTERS["income_min"]
    )
    FILTERS["cagr_min"] = get_float(
        "CAGR minimum (e.g., 20.0) [Enter for 20.0]: ",
        DEFAULT_FILTERS["cagr_min"]
    )
    FILTERS["competition_max"] = get_float(
        "Competition maximum (providers per 10k, e.g., 5.0) [Enter for 5.0]: ",
        DEFAULT_FILTERS["competition_max"]
    )
    FILTERS["large_hh_min"] = get_int(
        "Minimum large households (e.g., 0) [Enter for 0]: ",
        DEFAULT_FILTERS["large_hh_min"]
    )

    print("\nWeights should sum to 100:")
    w_demand = get_float(
        "Weight for demand (e.g., 40) [Enter for 40]: ",
        DEFAULT_WEIGHTS["demand"]
    )
    w_ownership_income = get_float(
        "Weight for ownership+income (e.g., 30) [Enter for 30]: ",
        DEFAULT_WEIGHTS["ownership_income"]
    )
    w_competition = get_float(
        "Weight for competition (e.g., 30) [Enter for 30]: ",
        DEFAULT_WEIGHTS["competition"]
    )

    WEIGHTS["demand"] = w_demand
    WEIGHTS["ownership_income"] = w_ownership_income
    WEIGHTS["competition"] = w_competition

    print("\n✅ Using custom configurations.")

print("\n🔥 ANALYZING...")

# === 1. CENSUS DATA ===
print("\n" + "="*60)
print("📖 STEP 1: LOADING CENSUS DATA")
print("="*60)

dp04 = pd.read_csv(
    "datasets/raw/ACSDP5Y2023.DP04-Data.csv",
    usecols=["GEO_ID", "NAME", "DP04_0001E", "DP04_0007E"],
    skiprows=[1]
)
dp03 = pd.read_csv(
    "datasets/raw/ACSDP5Y2023.DP03-Data.csv",
    usecols=["GEO_ID", "DP03_0062E"],
    skiprows=[1]
)
dp02 = pd.read_csv(
    "datasets/raw/ACSDP5Y2023.DP02-Data.csv",
    usecols=["GEO_ID", "DP02_0001E", "DP02_0008E", "DP02_0009E", "DP02_0010E", "DP02_0011E"],
    skiprows=[1]
)

census_df = dp04.merge(dp03, on="GEO_ID").merge(dp02, on="GEO_ID")

numeric_cols = [
    "DP04_0001E", "DP04_0007E", "DP03_0062E",
    "DP02_0001E", "DP02_0008E", "DP02_0009E", "DP02_0010E", "DP02_0011E"
]
census_df[numeric_cols] = census_df[numeric_cols].apply(pd.to_numeric, errors="coerce")

census_df["homeownership_rate"] = census_df["DP04_0007E"] / census_df["DP04_0001E"]
census_df["large_households"] = census_df[["DP02_0008E", "DP02_0009E", "DP02_0010E", "DP02_0011E"]].sum(axis=1)
census_df["total_housing_units"] = census_df["DP02_0001E"]
census_df["ZCTA"] = census_df["GEO_ID"].str[-5:].astype(str).str.zfill(5)

print(f"  ✅ Census loaded: {len(census_df)} geographies")

# === 2. ZIP ↔ ZCTA MAPPING ===
print("\n" + "="*60)
print("📖 STEP 2: LOADING ZIP MAPPING")
print("="*60)

zips_df = pd.read_csv("datasets/raw/zips_zctas_states.csv")
zips_df["ZCTA"] = zips_df["ZCTA"].astype(str).str.zfill(5)

print(f"  ✅ ZIP mapping loaded: {len(zips_df)} ZIPs")

# === 3. BUSINESS DATA ===
print("\n" + "="*60)
print("📖 STEP 3: LOADING BUSINESS DATA")
print("="*60)

business_df = pd.read_csv("datasets/scraped/business_count_by_zip_with_reviews.csv")
business_df = business_df.rename(columns={"zip_code": "ZIP", "state": "STATE"})

business_agg = business_df.groupby(["ZIP", "STATE"])["business_count"].sum().reset_index()
business_agg.rename(columns={"business_count": "total_businesses"}, inplace=True)

print(f"  ✅ Business data loaded: {len(business_agg)} ZIPs")

# === 4. CAGR DEMAND DATA ===
print("\n" + "="*60)
print("📖 STEP 4: LOADING CAGR DEMAND")
print("="*60)

demand_cagr_df = pd.read_csv("datasets/demand/demand_cagr_by_state.csv")

print(f"  ✅ CAGR demand loaded: {len(demand_cagr_df)} states")

# === 5. MERGE ALL DATA ===
print("\n" + "="*60)
print("🔄 STEP 5: MERGING ALL DATA")
print("="*60)

# Census + ZIP mapping
df1 = census_df.merge(zips_df[["ZIP", "ZCTA", "STATE"]], on="ZCTA")
print(f"  ✅ Census + ZIP: {len(df1)} rows")

# + Business
df2 = df1.merge(business_agg, on=["ZIP", "STATE"])
print(f"  ✅ + Business: {len(df2)} rows")

# Competition ratio
df2["competition_ratio"] = df2["total_businesses"] / (df2["total_housing_units"] / 10000)

# === 6. MELT CAGR & MERGE BY SERVICE ===
print("\n" + "="*60)
print("🔄 STEP 6: MELTING CAGR & MERGING SERVICES")
print("="*60)

services_cols = [
    "Asphalt/concrete work",
    "Driveway sealing",
    "Gutter cleaning",
    "Junk removal",
    "Pressure washing",
    "Soft washing",
    "Tree service",
    "Window cleaning",
]

# Melt CAGR table
demand_cagr_melted = demand_cagr_df.melt(
    id_vars=["geo"],
    value_vars=services_cols,
    var_name="service_name",
    value_name="cagr_pct"
)

# Normalize service names
business_df["service_name"] = business_df["service_name"].fillna("").astype(str)
business_df["service_name_lower"] = business_df["service_name"].str.lower().str.strip()
demand_cagr_melted["service_name_lower"] = demand_cagr_melted["service_name"].str.lower().str.strip()

# Merge business with CAGR
business_cagr = business_df.merge(
    demand_cagr_melted[["geo", "service_name_lower", "cagr_pct"]],
    left_on=["STATE", "service_name_lower"],
    right_on=["geo", "service_name_lower"],
    how="left"
)

# Fill missing CAGR with mean
cagr_mean = demand_cagr_df[services_cols].stack().mean()
business_cagr["cagr_pct"] = business_cagr["cagr_pct"].fillna(cagr_mean)

print(f"  ✅ CAGR mean: {cagr_mean:.2f}%")

# Merge service-level CAGR into ZIP data
df_services = df2.merge(
    business_cagr[["ZIP", "STATE", "service_name", "cagr_pct"]],
    on=["ZIP", "STATE"]
)

print(f"  ✅ Final merged: {len(df_services)} ZIP × service rows")

# === 7. FILTER & SCORE ===
print("\n" + "="*60)
print("🎯 STEP 7: FILTERING & SCORING")
print("="*60)

filtered_services = df_services[
    (df_services["homeownership_rate"] > FILTERS["homeownership_min"]) &
    (df_services["DP03_0062E"] > FILTERS["income_min"]) &
    (df_services["large_households"] > FILTERS["large_hh_min"]) &
    (df_services["cagr_pct"] > FILTERS["cagr_min"]) &
    (df_services["competition_ratio"] < FILTERS["competition_max"])
].copy()

print(f"\n🎯 {len(filtered_services)} OPPORTUNITIES FOUND!")

if len(filtered_services) > 0:
    # Normalize to 0-100
    filtered_services["homeownership_norm"] = np.clip(
        (filtered_services["homeownership_rate"] - 0.50) / 0.50 * 100, 0, 100
    )
    filtered_services["income_norm"] = np.clip(
        (filtered_services["DP03_0062E"] - 50000) / 150000 * 100, 0, 100
    )
    filtered_services["cagr_norm"] = np.clip(
        filtered_services["cagr_pct"] / 50 * 100, 0, 100
    )
    filtered_services["competition_norm"] = np.clip(
        100 - (filtered_services["competition_ratio"] * 10), 0, 100
    )

    # Composite score
    ownership_income = 0.5 * filtered_services["homeownership_norm"] + 0.5 * filtered_services["income_norm"]
    filtered_services["score"] = (
        filtered_services["cagr_norm"] * WEIGHTS["demand"] / 100 +
        ownership_income * WEIGHTS["ownership_income"] / 100 +
        filtered_services["competition_norm"] * WEIGHTS["competition"] / 100
    )

    # Sort
    filtered_services = filtered_services.sort_values("score", ascending=False)

    # Final output
    result = filtered_services[[
        "ZIP", "STATE", "service_name", "NAME", "homeownership_rate", "DP03_0062E",
        "large_households", "cagr_pct", "competition_ratio", "score"
    ]].round(2)

    result.columns = [
        "ZIP", "State", "Service", "Geography", "Homeownership%",
        "MedianIncome", "HH>4Members", "CAGR%", "Providers/10k", "Score"
    ]

    print("\n🏆 TOP 20:")
    print("-" * 100)
    print(result.head(20).to_string(index=False))

    top = result.iloc[0]
    print(f"\n🎯 #1: ZIP {top['ZIP']} ({top['State']}) | Score: {top['Score']:.0f}")
    print(f"   Income: ${top['MedianIncome']:,.0f} | CAGR: +{top['CAGR%']:.0f}% | Comp: {top['Providers/10k']:.1f}")

# === 8. SAVE ===
print("\n" + "="*60)
print("💾 STEP 8: SAVING OUTPUT")
print("="*60)

filename = "datasets/output/top_zips_by_services_cagr.csv"
result.to_csv(filename, index=False)
print(f"\n✅ SAVED: {filename}")
print(f"📋 Rows: {len(result)}")
print(f"📋 Columns: {list(result.columns)}")

print("\n✅ DONE! (CAGR-BASED ZIP-SERVICE SCORES)")
print("="*60)