"""
Process Scraped Yelp Data into Business Counts by ZIP

Processes all scraped Yelp CSV files from Qualified_Scrapes folder,
extracts business counts (only businesses with reviews), and aggregates
by ZIP code, state, town, and service.

Input:
- datasets/scraped/Qualified_Scrapes/yelp_*.csv (scraped Yelp data)

Output:
- datasets/scraped/business_count_by_zip_with_reviews.csv
"""

import pandas as pd
from pathlib import Path
import re


def extract_record_count_by_zip(folder_path, n=None, save=True):
    """
    Process scraped Yelp CSV files into business counts by ZIP.

    Args:
        folder_path: Path to folder containing yelp_*.csv files
        n: Optional limit on files to process (None = all)
        save: Whether to save output CSV

    Returns:
        pd.DataFrame: Business counts with columns:
            state, town, zip_code, service_name, business_count
    """
    print("\n" + "="*80)
    print("🔄 PROCESSING SCRAPED YELP DATA")
    print("="*80)

    data = []
    file_count = 0

    root_path = Path(folder_path)
    total_files = sum(1 for _ in root_path.rglob("*.csv"))
    print(f"📂 Found {total_files} CSV files total")

    for file_path in root_path.rglob("*.csv"):
        if n is not None and file_count >= n:
            break

        filename = file_path.name
        full_path_display = str(file_path)

        # Parse filename: yelp_service_name_12345.csv
        match = re.search(r'yelp_(.+)_(\d{5})\.csv$', filename)
        if not match:
            print(f"⚠️ Skipping {full_path_display} - doesn't match format")
            continue

        service_name_raw = match.group(1)
        zip_code = match.group(2)
        service_name = service_name_raw.replace('_', ' ').title()

        # Extract state and town from folder path
        parts = file_path.parts
        state = parts[-4]
        town_raw = parts[-3]
        town = town_raw.replace('_', ' ').title()

        try:
            df = pd.read_csv(file_path)

            # Parse review_count column to extract numeric values
            def parse_reviews(review_str):
                if pd.isna(review_str):
                    return 0
                # Handle formats like "(5 reviews)", "(1 review)", or just numbers
                match = re.search(r'\((\d+)\s*(?:reviews?|review)\)', str(review_str))
                return int(match.group(1)) if match else 0

            df['review_count_num'] = df['review_count'].apply(parse_reviews)

            # Count only businesses with reviews (> 0)
            business_count = (df['review_count_num'] > 0).sum()

            data.append({
                'state': state,
                'town': town,
                'zip_code': zip_code,
                'service_name': service_name,
                'business_count': business_count
            })

            file_count += 1
            print(f"✓ Processed {file_count}/{total_files if n is None else n}: {full_path_display}")
            print(f"  → {business_count} businesses with reviews")

        except Exception as e:
            print(f"❌ Error reading {full_path_display}: {e}")
            continue

    result_df = pd.DataFrame(data)

    print("\n" + "="*80)
    print(f"FINAL DATAFRAME ({len(result_df)} files processed)")
    print("="*80)
    print(result_df)
    print(f"\nDataFrame shape: {result_df.shape}")
    print(f"Columns: {list(result_df.columns)}")

    # Save output
    if save and not result_df.empty:
        output_file = 'datasets/scraped/business_count_by_zip_with_reviews.csv'
        result_df.to_csv(output_file, index=False)
        print(f"\n✅ SAVED: {output_file}")

    print("\n✅ SCRAPED DATA PROCESSING COMPLETE!")
    print("="*80)

    return result_df[['state', 'town', 'zip_code', 'service_name', 'business_count']]


if __name__ == "__main__":
    print("\n🚀 BUSINESS COUNT PROCESSOR")
    print("="*80)

    folder_path = "datasets/scraped/Qualified_Scrapes"
    result_all = extract_record_count_by_zip(folder_path, n=None, save=True)

    print("\nSample output:")
    print(result_all.head(10))

    print("\nSummary:")
    print(f"  Total records: {len(result_all)}")
    print(f"  Services: {result_all['service_name'].nunique()}")
    print(f"  States: {result_all['state'].nunique()}")
    print(f"  ZIPs: {result_all['zip_code'].nunique()}")
    print(f"  Total businesses: {result_all['business_count'].sum():,}")