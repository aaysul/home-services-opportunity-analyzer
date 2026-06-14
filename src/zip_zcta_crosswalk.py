"""
ZIP ↔ ZCTA Crosswalk Generator

Creates a mapping between ZIP codes and ZCTA (ZIP Code Tabulation Areas) 
with state and city information by merging:
- zip_to_zcta_crosswalk.xlsx (Census ZIP ↔ ZCTA mapping)
- usps_zip_locale_detail.csv (USPS ZIP ↔ City/State mapping)

Input:
- datasets/raw/zip_to_zcta_crosswalk.xlsx
- datasets/raw/usps_zip_locale_detail.csv

Output:
- datasets/raw/zips_zctas_states.csv (ZIP ↔ ZCTA ↔ City ↔ State mapping)
"""

import pandas as pd
import numpy as np

# US state codes to names mapping
us_states = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "MA": "Massachusetts", "MD": "Maryland",
    "ME": "Maine", "MI": "Michigan", "MN": "Minnesota", "MO": "Missouri", "MS": "Mississippi",
    "MT": "Montana", "NC": "North Carolina", "ND": "North Dakota", "NE": "Nebraska", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NV": "Nevada", "NY": "New York", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VA": "Virginia",
    "VT": "Vermont", "WA": "Washington", "WI": "Wisconsin", "WV": "West Virginia", "WY": "Wyoming"
}


def create_zip_zcta_crosswalk(
    crosswalk_file='datasets/raw/zip_to_zcta_crosswalk.xlsx',
    usps_file='datasets/raw/usps_zip_locale_detail.csv',
    output_file='datasets/raw/zips_zctas_states.csv'
):
    """
    Create ZIP ↔ ZCTA crosswalk with city and state information.

    Args:
        crosswalk_file: Path to Excel crosswalk file
        usps_file: Path to USPS ZIP locale CSV
        output_file: Path to save final crosswalk CSV

    Returns:
        pd.DataFrame: Crosswalk with ZIP, ZCTA, CITY, STATE, STATE NAME
    """
    print("\n" + "="*80)
    print("🔄 CREATING ZIP ↔ ZCTA CROSSWALK")
    print("="*80)

    # Step 1: Load crosswalk from Excel
    print("\n📖 Loading ZIP ↔ ZCTA crosswalk...")
    zip_zcta_state = pd.read_excel(
        crosswalk_file,
        usecols=['ZIP_CODE', 'zcta', 'STATE'],
        dtype={'zcta': str, 'ZIP_CODE': str}
    ).rename(columns={'ZIP_CODE': 'ZIP', 'zcta': 'ZCTA'}).drop_duplicates()[['ZIP', 'ZCTA', 'STATE']]

    # FIX: Pad with zeros in case Excel stripped them
    zip_zcta_state['ZIP'] = zip_zcta_state['ZIP'].str.zfill(5)
    zip_zcta_state['ZCTA'] = zip_zcta_state['ZCTA'].str.zfill(5)

    # Add state names
    zip_zcta_state['STATE NAME'] = zip_zcta_state['STATE'].map(us_states)

    print(f"  ✅ Loaded {len(zip_zcta_state)} ZIP ↔ ZCTA mappings")
    print(f"  📊 States: {zip_zcta_state['STATE NAME'].nunique()}")

    # Step 2: Load USPS ZIP data
    print("\n📖 Loading USPS ZIP locale data...")
    usps_zips = pd.read_csv(
        usps_file,
        usecols=['PHYSICAL ZIP', 'PHYSICAL CITY', 'PHYSICAL STATE'],
        dtype={'PHYSICAL ZIP': str}
    ).rename(columns={
        'PHYSICAL ZIP': 'ZIP',
        'PHYSICAL CITY': 'CITY',
        'PHYSICAL STATE': 'STATE'
    }).drop_duplicates()[['ZIP', 'CITY', 'STATE']]

    # FIX: Pad with zeros to match crosswalk ZIP format
    usps_zips['ZIP'] = usps_zips['ZIP'].str.zfill(5)

    print(f"  ✅ Loaded {len(usps_zips)} ZIP ↔ City mappings")

    # Step 3: Merge datasets
    print("\n🔄 Merging datasets...")
    zips_zctas_states = pd.merge(
        zip_zcta_state[['ZIP', 'ZCTA', 'STATE NAME']],
        usps_zips,
        on='ZIP',
        how='left'
    )[['ZIP', 'ZCTA', 'CITY', 'STATE', 'STATE NAME']]

    # Clean data
    zips_zctas_states.dropna(inplace=True)
    zips_zctas_states.drop_duplicates(inplace=True)
    zips_zctas_states = zips_zctas_states.sort_values(by='ZIP', ignore_index=True)

    print(f"  ✅ Merged: {len(zips_zctas_states)} final ZIP mappings")
    print(f"  📊 Cities: {zips_zctas_states['CITY'].nunique()}")
    print(f"  📊 States: {zips_zctas_states['STATE NAME'].nunique()}")

    # Step 4: Save
    print(f"\n💾 Saving to: {output_file}")
    zips_zctas_states.to_csv(output_file, index=False)

    print(f"  ✅ Saved {len(zips_zctas_states)} rows")

    print("\n" + "="*80)
    print("✅ CROSSWALK COMPLETE!")
    print("="*80)

    # Show sample
    print("\n📋 Sample output:")
    print(zips_zctas_states.head(10))

    return zips_zctas_states


if __name__ == "__main__":
    print("\n🚀 ZIP ZCTA CROSSWALK GENERATOR")
    print("="*80)

    crosswalk = create_zip_zcta_crosswalk()

    print("\nFinal DataFrame Info:")
    print(f"  Shape: {crosswalk.shape}")
    print(f"  Columns: {list(crosswalk.columns)}")
    print(f"  Memory: {crosswalk.memory_usage().sum() / 1024 / 1024:.2f} MB")