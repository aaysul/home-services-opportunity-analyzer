# pytrends demand acquisition


import pandas as pd
from pytrends.request import TrendReq
import time
import random
from requests.exceptions import RequestException
pd.set_option('future.no_silent_downcasting', True)

# List of all US states (FIPS codes)
us_states = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
]

services = [
    "Junk removal", "Tree service", "Pressure washing", 
    "Gutter cleaning", "Window cleaning", "Asphalt/concrete work", 
    "Driveway sealing", "Soft washing"
]

def fetch_trends_data(pytrends, service, geo, max_retries=5):
    """Fetch trends data with exponential backoff retries"""
    for attempt in range(max_retries):
        try:
            print(f"    Attempt {attempt + 1}/{max_retries} for {service} in {geo}")
            pytrends.build_payload([service], cat=0, timeframe='2021-01-01 2026-01-01', geo=geo)
            
            # Try interest_over_time first
            data = pytrends.interest_over_time()
            if data.empty:
                data = pytrends.interest_by_region(resolution='DMA', inc_low_vol=True, inc_geo_code=False)
            
            if not data.empty:
                return data
            
        except Exception as e:
            print(f"    Attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s, 8s
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"    Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                print(f"    Max retries exceeded for {service} in {geo}")
    
    return pd.DataFrame()

# Connect to Google Trends
print("Initializing Google Trends connection...")
pytrends = TrendReq(hl='en-US', tz=360)

all_data = []

# Process national data first
for service in services:
    print(f"\n=== Processing National: {service} ===")
    data = fetch_trends_data(pytrends, service, 'US')
    if not data.empty:
        data['service'] = service
        data['geo'] = 'US'
        all_data.append(data.reset_index())
    time.sleep(1)

# Process states
for service in services:
    print(f"\n{'='*60}")
    print(f"=== Processing Service: {service} ===")
    print(f"{'='*60}")
    
    state_count = 0
    for state in us_states:
        state_count += 1
        print(f"State {state_count}/50: {state}")
        
        data = fetch_trends_data(pytrends, service, f'US-{state}')
        if not data.empty:
            data['service'] = service
            data['geo'] = f'US-{state}'
            all_data.append(data.reset_index())
        
        # Always sleep between requests (more aggressive rate limiting)
        time.sleep(1 + random.uniform(0, 0.5))
    
    # Longer break between services
    print(f"Completed {service}. Sleeping 5s...")
    time.sleep(5)

# Save combined data
if all_data:
    print("\nCombining all data...")
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Remove duplicate columns if they exist
    combined_df = combined_df.loc[:, ~combined_df.columns.duplicated()]
    
    filename = 'services_trends_all_states_2021_2026_with_retries.csv'
    combined_df.to_csv(filename, index=False)
    
    print(f"\n✅ Data saved to '{filename}'")
    print(f"📊 Total records: {len(combined_df):,}")
    print(f"📈 Services covered: {combined_df['service'].nunique()}")
    print(f"🌎 Geos covered: {combined_df['geo'].nunique()}")
    print("\nFirst few rows:")
    print(combined_df.head())
else:
    print("❌ No data retrieved")

print("\n🎉 Script completed!")
