# CAGR computation (2021-2025)

"""
Compute CAGR (2021-2025) from State-Level Demand Matrix

Input:
- hs_states_demand_2021-2025.csv (state demand matrix)

Output:
- demand_cagr_by_state.csv (CAGR percentages by state/service)
"""

import pandas as pd
import numpy as np

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


def calc_cagr_matrix(end, start, years=4):
    """
    Compute CAGR: (end / start)^(1/years) - 1
    
    Args:
        end: 2025 DataFrame (n_states × n_services)
        start: 2021 DataFrame (n_states × n_services)
        years: 4 (2021 to 2025)
    
    Returns:
        DataFrame of CAGR values (decimal)
    """
    start_vals = start.to_numpy(dtype=float)
    end_vals = end.to_numpy(dtype=float)
    
    # Replace non-positive with 1.0
    start_vals = np.where(start_vals <= 0, 1.0, start_vals)
    end_vals = np.where(end_vals <= 0, 1.0, end_vals)
    
    cagr = (end_vals / start_vals) ** (1.0 / years) - 1.0
    
    return pd.DataFrame(cagr, index=end.index, columns=end.columns)


def compute_cagr(
    demand_file='datasets/demand/hs_states_demand_2021-2025.csv',
    output_file='datasets/demand/demand_cagr_by_state.csv'
):
    print("\n" + "="*80)
    print("🔄 COMPUTING CAGR (2021-2025)")
    print("="*80)

    # Load demand
    demand_df = pd.read_csv(demand_file, parse_dates=['date'])
    demand_df["year"] = demand_df["date"].dt.year
    print(f"  ✅ Loaded {len(demand_df)} rows")

    # Annual averages
    annual_avg = demand_df.groupby(["geo", "year"])[services].mean().reset_index()
    print(f"  ✅ Annual averages: {annual_avg.shape[0]} rows")

    # Get 2021 and 2025
    start_data = annual_avg[annual_avg["year"] == 2021].set_index("geo")[services]
    end_data = annual_avg[annual_avg["year"] == 2025].set_index("geo")[services]

    # Match states
    common_states = start_data.index.intersection(end_data.index)
    start_data = start_data.loc[common_states]
    end_data = end_data.loc[common_states]
    print(f"  ✅ Using {len(common_states)} states")

    # Compute CAGR
    cagr_decimal = calc_cagr_matrix(end_data, start_data, years=4)
    cagr_pct = cagr_decimal * 100.0

    print(f"  📈 CAGR range: {cagr_pct.min().min():.2f}% to {cagr_pct.max().max():.2f}%")

    # Top 10 Junk removal
    print("\n🏆 TOP 10 STATES BY JUNK REMOVAL CAGR:")
    print(cagr_pct["Junk removal"].sort_values(ascending=False).head(10).round(2))

    # Summary
    print("\n📊 CAGR SUMMARY:")
    print(cagr_pct.describe().round(3))

    # Save
    df_cagr = cagr_pct.reset_index().round(3)
    df_cagr.to_csv(output_file, index=False)
    print(f"\n💾 SAVED: {output_file}")

    # Hot states
    print("\n🔥 HOT STATES (avg CAGR > 3.0%):")
    avg_cagr = cagr_pct.mean(axis=1).round(3)
    print(avg_cagr[avg_cagr > 3.0].sort_values(ascending=False).head(10))

    print("\n✅ COMPLETE!")
    return df_cagr


if __name__ == "__main__":
    cagr_df = compute_cagr()
    print("\nSample:")
    print(cagr_df[["geo", "Junk removal", "Tree service"]].head(10))