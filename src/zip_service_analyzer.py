# ZIP-service opportunity analyzer


import pandas as pd
import numpy as np
import warnings

# Suppress warnings to keep output clean
warnings.filterwarnings("ignore")

print("🔄 HOME SERVICES ANALYZER v2.8 (CAGR‑BASED)")
print("=" * 60)

# === DEFAULTS FOR FILTERS AND WEIGHTS ===
# Filter thresholds for ZIP–service opportunity scoring
DEFAULT_FILTERS = {
    "homeownership_min": 0.60,      # minimum homeownership rate
    "income_min": 75000,            # minimum median household income
    "cagr_min": 20.0,               # minimum CAGR (%) for demand growth
    "competition_max": 5.0,         # max providers per 10k housing units
    "large_hh_min": 0,              # minimum large households (4+ persons)
}

# Scoring weights (must sum to 100)
DEFAULT_WEIGHTS = {
    "demand": 40,                  # demand growth (CAGR)
    "ownership_income": 30,        # homeownership + income combo
    "competition": 30,             # competition (inverted)
}

def get_float(prompt, default):
    """
    Read a float from user input.
    If input is empty, return default and show a message.
    """
    s = input(prompt).strip()
    if s == "":
        print(f"  → using default: {default}")
        return default
    return float(s)

def get_int(prompt, default):
    """
    Read an int from user input.
    If input is empty, return default and show a message.
    """
    s = input(prompt).strip()
    if s == "":
        print(f"  → using default: {default}")
        return int(s)

# === INITIAL PROMPT: Change configs or use defaults? ===
print("🔧 CONFIGURATION")
print("-" * 40)

# Show default filter values
print(f"Default filters (CAGR‑based):")
for k, v in DEFAULT_FILTERS.items():
    print(f"  {k}: {v}")

# Show total weight (should be 100)
print(f"  Total weight: {sum(DEFAULT_WEIGHTS.values())}")
print()

# Ask user if they want to customize
choice = input("Do you want to customize filters and weights? (y/n): ").strip().lower()
use_defaults = choice != "y"

FILTERS = {}
WEIGHTS = {}

if use_defaults:
    # Use predefined defaults
    FILTERS = DEFAULT_FILTERS.copy()
    WEIGHTS = DEFAULT_WEIGHTS.copy()
    print("\n✅ Using default configurations.")
else:
    # Let the user input each filter and weight
    print("\nCONFIGURE FILTERS AND WEIGHTS (CAGR‑BASED)")
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

# === 1. LOAD AND PROCESS CENSUS DATA (ACS DP04, DP03, DP02) ===
# DP04: housing characteristics (total households, owner-occupied)
dp04 = pd.read_csv(
    "Datasets/ACSDP5Y2023.DP04-Data.csv",
    usecols=["GEO_ID", "NAME", "DP04_0001E", "DP04_0007E"],
    skiprows=[1]
)

# DP03: income (median household income)
dp03 = pd.read_csv(
    "Datasets/ACSDP5Y2023.DP03-Data.csv",
    usecols=["GEO_ID", "DP03_0062E"],
    skiprows=[1]
)

# DP02: household size distribution (4–7+ person households)
dp02 = pd.read_csv(
    "Datasets/ACSDP5Y2023.DP02-Data.csv",
    usecols=[
        "GEO_ID", "DP02_0001E", "DP02_0008E", "DP02_0009E",
        "DP02_0010E", "DP02_0011E"
    ],
    skiprows=[1]
)

# Merge on GEO_ID to combine housing, income, and household size
census_df = dp04.merge(dp03, on="GEO_ID").merge(dp02, on="GEO_ID")

# Convert selected columns to numeric, coercing errors to NaN
numeric_cols = [
    "DP04_0001E", "DP04_0007E", "DP03_0062E",
    "DP02_0001E", "DP02_0008E", "DP02_0009E", "DP02_0010E", "DP02_0011E"
]
census_df[numeric_cols] = census_df[numeric_cols].apply(
    pd.to_numeric, errors="coerce"
)

# Compute homeownership rate: owner-occupied / total households
census_df["homeownership_rate"] = (
    census_df["DP04_0007E"] / census_df["DP04_0001E"]
)

# Count large households (4+ persons): sum of 4–7+ person household counts
census_df["large_households"] = (
    census_df[["DP02_0008E", "DP02_0009E", "DP02_0010E", "DP02_0011E"]].sum(axis=1)
)

# Use DP02 total households as proxy for total housing units
census_df["total_housing_units"] = census_df["DP02_0001E"]

# Extract ZIP (ZCTA) from GEO_ID (last 5 characters) and pad to 5 digits
census_df["ZCTA"] = (
    census_df["GEO_ID"].str[-5:].astype(str).str.zfill(5)
)

# === 2. LOAD BUSINESS AND DEMAND (CAGR) DATA ===
# ZIP ↔ ZCTA ↔ STATE mapping
zips_df = pd.read_csv("Datasets/zips_zctas_states.csv")
# Business counts by ZIP (from Yelp scrape processor)
business_df = pd.read_csv("Datasets/business_count_by_zip_with_reviews.csv")

# State-level CAGR demand table (computed earlier)
demand_cagr_df = pd.read_csv("demand_cagr_by_state.csv")

# Normalize ZCTA column to 5-digit strings
zips_df["ZCTA"] = zips_df["ZCTA"].astype(str).str.zfill(5)

# Normalize business_df column names for joining
business_df = business_df.rename(columns={"zip_code": "ZIP", "state": "STATE"})

# === Merge census with ZIP mapping (via ZCTA) ===
df1 = census_df.merge(
    zips_df[["ZIP", "ZCTA", "STATE"]],
    on="ZCTA"
)

# Aggregate business counts by ZIP and STATE
business_agg = (
    business_df.groupby(["ZIP", "STATE"])["business_count"]
    .sum()
    .reset_index()
)
business_agg.rename(columns={"business_count": "total_businesses"}, inplace=True)

# Merge aggregated businesses into census+ZIP data
df2 = df1.merge(business_agg, on=["ZIP", "STATE"])

# Compute competition ratio: businesses per 10,000 housing units
df2["competition_ratio"] = (
    df2["total_businesses"] / (df2["total_housing_units"] / 10000)
)

# === 3. MELT CAGR DEMAND TABLE AND JOIN TO BUSINESSES BY SERVICE ===
# Define service columns (CAGR percentages by state)
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

# Melt state-level CAGR table from wide to long format:
# One row per (state, service) with CAGR%
demand_cagr_melted = demand_cagr_df.melt(
    id_vars=["geo"],
    value_vars=services_cols,
    var_name="service_name",
    value_name="cagr_pct"
)

# Normalize service names for case-insensitive matching
business_df["service_name"] = business_df["service_name"].fillna("").astype(str)
business_df["service_name_lower"] = (
    business_df["service_name"].str.lower().str.strip()
)
demand_cagr_melted["service_name_lower"] = (
    demand_cagr_melted["service_name"].str.lower().str.strip()
)

# Match business records to CAGR demand by (STATE, service_name)
# Use lowercase for robust matching
business_cagr = business_df.merge(
    demand_cagr_melted[["geo", "service_name_lower", "cagr_pct"]],
    left_on=["STATE", "service_name_lower"],
    right_on=["geo", "service_name_lower"],
    how="left"
)

# Fill missing CAGR values with overall mean across all services/states
cagr_mean = demand_cagr_df[services_cols].stack().mean()
business_cagr["cagr_pct"] = business_cagr["cagr_pct"].fillna(cagr_mean)

# Merge service-level CAGR back into ZIP-level census+business data
df_services = df2.merge(
    business_cagr[["ZIP", "STATE", "service_name", "cagr_pct"]],
    on=["ZIP", "STATE"]
)

# === 4. FILTER OPPORTUNITIES AND COMPUTE SCORES (CAGR-BASED) ===
filtered_services = df_services[
    (df_services["homeownership_rate"] > FILTERS["homeownership_min"]) &
    (df_services["DP03_0062E"] > FILTERS["income_min"]) &
    (df_services["large_households"] > FILTERS["large_hh_min"]) &
    (df_services["cagr_pct"] > FILTERS["cagr_min"]) &
    (df_services["competition_ratio"] < FILTERS["competition_max"])
].copy()

print(f"\n🎯 {len(filtered_services)} OPPORTUNITIES FOUND!")

if len(filtered_services) > 0:
    # === Normalize metrics to 0–100 scale for scoring ===
    # Homeownership: base 0.50, range 0.50 → 100
    filtered_services["homeownership_norm"] = np.clip(
        (filtered_services["homeownership_rate"] - 0.50) / 0.50 * 100, 0, 100
    )

    # Income: base $50k, range $150k → 100
    filtered_services["income_norm"] = np.clip(
        (filtered_services["DP03_0062E"] - 50000) / 150000 * 100, 0, 100
    )

    # CAGR: 0–50% → 0–100
    filtered_services["cagr_norm"] = np.clip(
        filtered_services["cagr_pct"] / 50 * 100, 0, 100
    )

    # Competition: invert (lower competition = higher score)
    # Scale: competition_ratio * 10 → subtract from 100, clip to [0,100]
    filtered_services["competition_norm"] = np.clip(
        100 - (filtered_services["competition_ratio"] * 10), 0, 100
    )

    # Combine homeownership and income equally into one composite
    ownership_income = (
        0.5 * filtered_services["homeownership_norm"] +
        0.5 * filtered_services["income_norm"]
    )

    # Final score: weighted sum of normalized components
    filtered_services["score"] = (
        filtered_services["cagr_norm"] * WEIGHTS["demand"] / 100 +
        ownership_income * WEIGHTS["ownership_income"] / 100 +
        filtered_services["competition_norm"] * WEIGHTS["competition"] / 100
    )

    # Sort by score descending
    filtered_services = filtered_services.sort_values("score", ascending=False)

    # Select and round final output columns
    result = filtered_services[
        [
            "ZIP", "STATE", "service_name", "NAME", "homeownership_rate",
            "DP03_0062E", "large_households", "cagr_pct",
            "competition_ratio", "score"
        ]
    ].round(2)

    # Rename columns for readability
    result.columns = [
        "ZIP", "State", "Service", "Geography", "Homeownership%",
        "MedianIncome", "HH>4Members", "CAGR%", "Providers/10k", "Score"
    ]

    # Print top 20 opportunities
    print("\n🏆 TOP 20:")
    print("-" * 100)
    print(result.head(20).to_string(index=False))

    # Highlight #1 opportunity
    top = result.iloc[0]
    print(f"\n🎯 #1: ZIP {top['ZIP']} ({top['State']}) | Score: {top['Score']:.0f}")
    print(
        f"   Income: ${top['MedianIncome']:,.0f} | "
        f"CAGR: +{top['CAGR%']:.0f}% | "
        f"Comp: {top['Providers/10k']:.1f}"
    )

# === SAVE RESULTS ===
filename = "Datasets/top_zips_by_services_cagr.csv"
result.to_csv(filename, index=False)
print(f"\n💾 SAVED: {filename}")
print("✅ DONE! (CAGR‑BASED ZIP‑SERVICE SCORES)")