# 🏠 Home Services Opportunity Analyzer

**CAGR-Based ZIP Code & Service Opportunity Finder**

Analyze ZIP codes × home services to find high-opportunity markets using demand growth, census data, and competition analysis.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run entire pipeline
bash scripts/run_all.sh

# OR run steps individually
python src/zip_zcta_crosswalk.py
python src/scraper.py
python src/business_count_processor.py
python src/pytrends_fetcher.py
python src/demand_pytrends.py
python src/cagr_computer.py
python src/zip_service_analyzer.py
```


---

## 📁 Project Structure

```
home-services-opportunity-analyzer/
├── src/
│   ├── scraper.py                  # Yelp scraper
│   ├── business_count_processor.py # Process scraped data
│   ├── zip_zcta_crosswalk.py       # ZIP ↔ ZCTA mapping
│   ├── pytrends_fetcher.py         # Google Trends fetcher
│   ├── demand_pytrends.py          # Process pytrends data
│   ├── cagr_computer.py            # Compute CAGR
│   ├── zip_service_analyzer.py     # Final ZIP scoring
│   ├── census_loader.py            # Load Census data
│   ├── config.py                   # Configuration
│   ├── helpers.py                  # Utilities
│   └── cli.py                      # CLI entry point
├── datasets/
│   ├── raw/                        # Source data (ignored)
│   ├── scraped/                    # Scraped data (ignored)
│   ├── demand/                     # Demand data (ignored)
│   └── output/                     # Final results (tracked)
├── scripts/
│   ├── run_all.sh                  # Run pipeline
│   └── run_pytrends_demand.sh      # Run pytrends steps
├── tests/                          # Unit tests
├── docs/                           # Documentation
├── notebooks/                      # Jupyter notebooks
├── requirements.txt
├── .gitignore
└── README.md
```


---

## 🔄 Pipeline Flow

```
Step 1 → ZIP ↔ ZCTA Crosswalk
  File: src/zip_zcta_crosswalk.py
  Input:  zip_to_zcta_crosswalk.xlsx + usps_zip_locale_detail.csv
  Output: datasets/raw/zips_zctas_states.csv

  ↓

Step 2 → Yelp Scraper (hours - overnight)
  File: src/scraper.py
  Input:  zips_zctas_states.csv + qualified ZIPs
  Output: datasets/scraped/Qualified_Scrapes/yelp_*.csv
  Features: Proxy pool + captcha + resume

  ↓

Step 3 → Process Scraped Data
  File: src/business_count_processor.py
  Input:  datasets/scraped/Qualified_Scrapes/yelp_*.csv
  Output: datasets/scraped/business_count_by_zip_with_reviews.csv

  ↓

Step 4 → Fetch Demand (10-20 min)
  File: src/pytrends_fetcher.py
  Input:  Google Trends API
  Output: datasets/demand/pytrends_raw/services_trends_*.csv
  Features: Retry logic + exponential backoff

  ↓

Step 5 → Process Demand
  File: src/demand_pytrends.py
  Input:  Raw pytrends CSV
  Output: datasets/demand/hs_states_demand_2021-2025.csv

  ↓

Step 6 → Compute CAGR
  File: src/cagr_computer.py
  Input:  Demand matrix
  Output: datasets/demand/demand_cagr_by_state.csv
  Formula: CAGR = (end/start)^(1/4) - 1

  ↓

Step 7 → ZIP-Level Scoring ✨
  File: src/zip_service_analyzer.py
  Input:  Census + Business + CAGR + ZIP mapping
  Output: datasets/output/top_zips_by_services_cagr.csv
  Score: 40% CAGR + 30% Census + 30% Competition
```


---

## 📋 Services Tracked

| Service |
| :-- |
| Soft washing |
| Junk removal |
| Tree service |
| Pressure washing |
| Gutter cleaning |
| Window cleaning |
| Asphalt/concrete work |
| Driveway sealing |


---

## 🏆 Scoring Formula

| Factor | Source | Weight |
| :-- | :-- | :-- |
| **CAGR (Demand)** | Google Trends 2021-2025 | 40% |
| **Homeownership + Income** | US Census ACS 2023 | 30% |
| **Low Competition** | Yelp Scrapes | 30% |


---

## 🛠️ Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**

- pandas
- pytrends
- seleniumwire
- aiohttp
- webdriver-manager
- beautifulsoup4
- nest-asyncio


### Download Census Data

Place these files in `datasets/raw/`:

```
datasets/raw/ACSDP5Y2023.DP02-Data.csv   # Household size
datasets/raw/ACSDP5Y2023.DP03-Data.csv   # Median income
datasets/raw/ACSDP5Y2023.DP04-Data.csv   # Homeownership
datasets/raw/zip_to_zcta_crosswalk.xlsx  # ZIP ↔ ZCTA
datasets/raw/usps_zip_locale_detail.csv  # ZIP → City
```


---

## 🚦 Running

### One Command

```bash
bash scripts/run_all.sh
```


### Step-by-Step

```bash
# Step 1: Create crosswalk
python src/zip_zcta_crosswalk.py

# Step 2: Scrape Yelp (overnight)
python src/scraper.py

# Step 3: Process scraped data
python src/business_count_processor.py

# Step 4: Fetch pytrends
python src/pytrends_fetcher.py

# Step 5: Process demand
python src/demand_pytrends.py

# Step 6: Compute CAGR
python src/cagr_computer.py

# Step 7: Run analyzer
python src/zip_service_analyzer.py
```


### Custom Filters

```bash
python src/zip_service_analyzer.py
```

When prompted, customize:

```
Homeownership minimum: 0.65
Income minimum: 100000
CAGR minimum: 25.0
Competition maximum: 3.0
```


---

## 📤 Output

### Final File

**Path:** `datasets/output/top_zips_by_services_cagr.csv`

### Columns

| Column | Description |
| :-- | :-- |
| ZIP | ZIP code |
| State | State abbreviation |
| Service | Service name |
| Geography | City name |
| Homeownership% | Homeownership rate (0-1) |
| MedianIncome | Median household income |
| HH>4Members | Households with 4+ members |
| CAGR% | Annual growth rate (%) |
| Providers/10k | Businesses per 10k units |
| Score | Composite score (0-100) |


---

## 🔍 Troubleshooting

### Scraper Issues

```
Problem: "No live proxies found"
Fix: Add proxies to USProxyPool.__init__()
     self.us_proxies = ["123.45.67.89:8080"]

Problem: "CAPTCHA not solved"
Fix: Increase MAX_CAPTCHA_TRIES = 5

Problem: "Firefox profile not found"
Fix: Create profile named "default-release"
```


### pytrends Issues

```
Problem: "429 Too Many Requests"
Fix: Increase RETRY_DELAY = 10

Problem: "No data returned"
Fix: Adjust timeframe format
```


### Data Issues

```
Problem: "File not found"
Fix: Download Census data (see Setup)

Problem: "Empty output"
Fix: Lower filters in analyzer
```


---

## 🧪 Testing

```bash
pytest tests/ -v
```


---

## 📄 License

MIT License

---

## 🙏 Credits

- Google Trends (pytrends)
- US Census Bureau (ACS data)
- Yelp (scraped data)
