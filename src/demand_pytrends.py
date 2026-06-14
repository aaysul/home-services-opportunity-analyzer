"""
Process Raw pytrends Output into State-Level Demand Matrix

Input:
- services_trends_all_states_2021_2026_with_retries.csv (raw pytrends)

Output:
- hs_states_demand_2021-2025.csv (state demand matrix)
"""

import pandas as pd

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


def process_pytrends_output(
    input_file='datasets/demand/pytrends_raw/services_trends_all_states_2021_2026_with_retries.csv',
    output_file='datasets/demand/hs_states_demand_2021-2025.csv'
):
    print("\n" + "="*80)
    print("🔄 PROCESSING PYTRENDS OUTPUT")
    print("="*80)

    # Step 1: Read CSV with date parsing
    print(f"📖 Reading: {input_file}")
    search_df = pd.read_csv(input_file, parse_dates=['date'])[['date', 'geo', *services]].set_index('date')
    print(f"  ✅ Loaded {len(search_df)} rows, {len(services)} services")

    # Step 2: Create pivot table
    print("🔄 Creating pivot table...")
    hs_demand = search_df.pivot_table(index=['date', 'geo'], values=services).fillna(0).round(1)
    print(f"  ✅ Pivot created: {hs_demand.shape[0]} rows × {hs_demand.shape[1]} columns")

    # Step 3: Reset/set index
    hs_demand = hs_demand.reset_index().set_index('date')

    # Step 4: Clean geo codes
    hs_demand['geo'] = hs_demand['geo'].str.replace('US-', '', regex=False)
    print(f"  ✅ Geo codes cleaned")

    # Step 5: Save (exclude national 'US')
    state_demand = hs_demand.query("geo != 'US'")
    state_demand.to_csv(output_file, index=True)
    print(f"  ✅ Saved {len(state_demand)} rows to {output_file}")

    print("\n✅ COMPLETE!")
    return state_demand


if __name__ == "__main__":
    demand_df = process_pytrends_output()
    print("\nSample:")
    print(demand_df.head(10))