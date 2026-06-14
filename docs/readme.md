**CAGR-Based ZIP Code & Service Opportunity Finder**

Analyze ZIP codes × home services to find high-opportunity markets using:
- 📈 **Demand Growth** (pytrends CAGR 2021-2025)
- 🏡 **Census Data** (homeownership, income, household size)
- 🏪 **Competition** (Web scrapes)

---

## 📊 What It Does

Finds the best ZIP codes to launch home services based on:

| Factor | Source | Weight |
|---|---|---|
| **CAGR (Demand Growth)** | Google Trends (2021-2025) | 40% |
| **Homeownership + Income** | US Census ACS 2023 | 30% |
| **Competition (Low)** | Scrapes | 30% |

**Output:** Top ZIP codes ranked by service with composite scores.

---

## 🚀 Quick Start

```bash
# 1. Clone repo
cd E:/Projects/home-services-opportunity-analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run entire pipeline (one command)
bash scripts/run_all.sh

# OR run steps individually:
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

- **src/** - Python source files
  - `scraper.py` - Yelp scraper (proxy pool + captcha)
  - `business_count_processor.py` - Process scraped data
  - `zip_zcta_crosswalk.py` - Create ZIP ↔ ZCTA mapping
  - `pytrends_fetcher.py` - Fetch demand from Google Trends
  - `demand_pytrends.py` - Process raw pytrends → demand matrix
  - `cagr_computer.py` - Compute CAGR (2021-2025)
  - `zip_service_analyzer.py` - ZIP-level scoring (final output)
  - `census_loader.py` - Load ACS Census data
  - `config.py` - Configuration
  - `helpers.py` - Utility functions
  - `cli.py` - Command-line entry point

- **datasets/** - Data files (not tracked by Git)
  - `raw/` - Source data (Census, ZIP mappings)
  - `scraped/` - Scraped Yelp data
  - `demand/` - pytrends demand data
  - `output/` - Final results (tracked)

- **scripts/** - Shell scripts
  - `run_all.sh` - Run entire pipeline
  - `run_pytrends_demand.sh` - Run pytrends + demand steps

- **tests/** - Unit tests
- **docs/** - Documentation
- **notebooks/** - Jupyter notebooks
- `requirements.txt` - Python dependencies
- `.gitignore` - Git ignore file
- `README.md` - This file

---
'''
## 🔄 Pipeline Flow

STEP 1: ZIP ↔ ZCTA CROSSWALK
src/zip_zcta_crosswalk.py
Input: zip_to_zcta_crosswalk.xlsx + usps_zip_locale_detail.csv
Output: datasets/raw/zips_zctas_states.csv


↓ STEP 2:  SCRAPER (hours - may run overnight)
src/scraper.py
Input: zips_zctas_states.csv + qualified ZIPs
Output: datasets/scraped/Qualified_Scrapes/_*.csv
Features: Proxy pool + captcha solving + resume capability


↓ STEP 3: PROCESS SCRAPED DATA
src/business_count_processor.py
Input: datasets/scraped/Qualified_Scrapes/_*.csv
Output: datasets/scraped/business_count_by_zip_with_reviews.csv


↓ STEP 4: FETCH DEMAND (10-20 minutes)
src/pytrends_fetcher.py
Input: Google Trends API
Output: datasets/demand/pytrends_raw/services_trends_*.csv
Features: Exponential backoff + retry logic


↓ STEP 5: PROCESS DEMAND
src/demand_pytrends.py
Input: Raw pytrends CSV
Output: datasets/demand/hs_states_demand_2021-2025.csv


↓ STEP 6: COMPUTE CAGR
src/cagr_computer.py
Input: Demand matrix
Output: datasets/demand/demand_cagr_by_state.csv
Formula: CAGR = (end/start)^(1/4) - 1 (2021-2025)


↓ STEP 7: ZIP-LEVEL SCORING (FINAL OUTPUT)
src/zip_service_analyzer.py
Input: Census + Business + CAGR + ZIP mapping
Output: datasets/output/top_zips_by_services_cagr.csv
Score: 40% CAGR + 30% Ownership/Income + 30% Competition

'''
---

## 📋 Services Tracked

| Service | Keyword |
|---|---|
| Soft washing | `"Soft washing"` |
| Junk removal | `"Junk removal"` |
| Tree service | `"Tree service"` |
| Pressure washing | `"Pressure washing"` |
| Gutter cleaning | `"Gutter cleaning"` |
| Window cleaning | `"Window cleaning"` |
| Asphalt/concrete work | `"Asphalt/concrete work"` |
| Driveway sealing | `"Driveway sealing"` |

---

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key packages:**
- `pandas` → Data processing
- `pytrends` → Google Trends API
- `seleniumwire` →  scraping
- `aiohttp` → Async proxy testing
- `webdriver-manager` → Firefox driver
- `beautifulsoup4` → Proxy page scraping

### 2. Download Census Data

Download ACS 2023 5-year estimates from US Census Bureau:

```bash
# URLs (save to datasets/raw/):
# DP02: https://census.gov/.../ACSDP5Y2023.DP02-Data.csv
# DP03: https://census.gov/.../ACSDP5Y2023.DP03-Data.csv
# DP04: https://census.gov/.../ACSDP5Y2023.DP04-Data.csv
```

**Or use our data download script:**
```bash
python scripts/download_census.py
```

### 3. (Optional) Get Qualified ZIPs

If you have a `busy_families_housing.csv` from previous analysis:

```bash
# Place in datasets/raw/
cp your_file.csv datasets/raw/busy_families_housing.csv
```

The scraper will only scrape these ZIPs. Otherwise, it scrapes all ZIPs.

---

## 🚦 Running the Pipeline

### Option A: One Command (Recommended)

```bash
bash scripts/run_all.sh
```

### Option B: Step-by-Step

```bash
# Step 1: Create crosswalk
python src/zip_zcta_crosswalk.py

# Step 2: Scrape  (run overnight - takes hours)
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

### Option C: Custom Filters

```bash
python src/zip_service_analyzer.py
```

When prompted:

Do you want to customize filters and weights? (y/n): y

Homeownership minimum (e.g., 0.60) [Enter for 0.60]: 0.65
Income minimum (e.g., 75000) [Enter for 75000]: 100000
CAGR minimum (e.g., 20.0) [Enter for 20.0]: 25.0
Competition maximum (providers per 10k, e.g., 5.0) [Enter for 5.0]: 3.0

Weight for demand (e.g., 40) [Enter for 40]: 50
Weight for ownership+income (e.g., 30) [Enter for 30]: 25
Weight for competition (e.g., 30) [Enter for 30]: 25

text

---

## 📤 Output

### Final Result

**File:** `datasets/output/top_zips_by_services_cagr.csv`

**Columns:**
| Column | Description |
|---|---|
| `ZIP` | ZIP code |
| `State` | State abbreviation |
| `Service` | Service name |
| `Geography` | City name |
| `Homeownership%` | Homeownership rate (0-1) |
| `MedianIncome` | Median household income |
| `HH>4Members` | households with 4+ members |
| `CAGR%` | Annual growth rate (%) |
| `Providers/10k` | Competition (businesses per 10k housing units) |
| `Score` | Composite score (0-100) |

**Example:**

ZIP State Service Geography Homeownership% MedianIncome HH>4Members CAGR% Providers/10k Score
75001 TX Junk removal Abilene 0.72 95000 1200 35.2 2.1 87.4
90210 CA Tree service Beverly Hills 0.85 125000 800 28.7 1.5 82.1

text

---

## 🔍 Troubleshooting

### Scraper Issues

**Problem:** "No live proxies found"
```bash
# Solution: Check proxy list URL
# Manual fix: Add your own proxies to USProxyPool.__init__()
self.us_proxies = ["123.45.67.89:8080", "98.76.54.32:3128"]
```

**Problem:** "CAPTCHA not solved"
```bash
# Solution: Increase MAX_CAPTCHA_TRIES
MAX_CAPTCHA_TRIES = 5
```

**Problem:** "Firefox profile not found"
```bash
# Solution: Create Firefox profile named "default-release"
# Or change profile_name in ProxyScraper()
```

### pytrends Issues

**Problem:** "429 Too Many Requests"
```python
# Solution: Increase RETRY_DELAY in pytrends_fetcher.py
RETRY_DELAY = 10  # seconds
```

**Problem:** "No data returned"
```python
# Solution: Adjust timeframe format
timeframe='2021-01-01 2026-01-01'  # Your current format
```

### Data Issues

**Problem:** "File not found: datasets/raw/ACSDP5Y2023.DP02-Data.csv"
```bash
# Solution: Download census data (see Setup Instructions)
```

**Problem:** "Empty output"
```bash
# Solution: Lower filters
python src/zip_service_analyzer.py
# Set: homeownership_min=0.50, income_min=50000, cagr_min=10.0
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run single test
pytest tests/test_zip_service_analyzer.py -v
```

---

## 📚 Data Dictionary

See `docs/data_dictionary.md` for complete data documentation.

### Key Files

| File | Source | Description |
|---|---|---|
| `ACSDP5Y2023.DP02-Data.csv` | US Census | Household size, housing units |
| `ACSDP5Y2023.DP03-Data.csv` | US Census | Median income |
| `ACSDP5Y2023.DP04-Data.csv` | US Census | Homeownership rate |
| `zips_zctas_states.csv` | Generated | ZIP ↔ ZCTA ↔ City mapping |
| `services_trends_*.csv` | Google Trends | State-level demand (2021-2026) |
| `demand_cagr_by_state.csv` | Generated | CAGR by state/service |
| `business_count_by_zip_*.csv` | Generated | Business counts by ZIP |
| `top_zips_by_services_cagr.csv` | Generated | **Final output** |

---

## 📄 License

MIT License

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Submit a pull request

---

## 🙏 Credits

Built with:
- Google Trends (pytrends)
- US Census Bureau (ACS data)
-  (scraped data)

---

## 📞 Contact

Questions? Open an issue on GitHub.

---

**Made with ❤️ for home services market analysis**
