"""
🚀 ULTIMATE YELP SCRAPER: PROXY POOL + SELENIUM + RESUME + CAPTCHA + CACHED GECKODRIVER

Scrapes Yelp business data for home services across qualified ZIP codes.
Uses proxy pool rotation, Datadome captcha solving, and resume capability.

Input:
- datasets/raw/zips_zctas_states.csv (ZIP ↔ ZCTA mapping)
- datasets/output/busy_families_housing.csv (qualified ZIPs from analyzer)

Output:
- datasets/scraped/Qualified_Scrapes/yelp_*.csv (scraped business data)
"""

import configparser
import os
import platform
import pandas as pd
import time
import random
import re
import asyncio
import aiohttp
import nest_asyncio
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")
nest_asyncio.apply()

from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
from itertools import cycle


# =============================================================================
# 🔍 CACHED GECKODRIVER DETECTOR
# =============================================================================

def find_cached_geckodriver():
    """Find existing geckodriver.exe in webdriver_manager cache"""
    print("🔍 Searching webdriver_manager cache...")
    wdm_cache = Path.home() / ".wdm" / "drivers" / "geckodriver"
    
    if not wdm_cache.exists():
        print("❌ Cache directory not found")
        return None
    
    for root, dirs, files in os.walk(wdm_cache):
        for file in files:
            if file == "geckodriver.exe":
                full_path = os.path.join(root, file)
                size = os.path.getsize(full_path)
                
                # Mask username in path
                display_path = str(full_path)
                display_path = re.sub(r'C:\\users\\[^\\]+', r'C:\\users\\...', display_path, flags=re.IGNORECASE)
                
                print(f"✅ FOUND: {display_path}")
                print(f"   Size: {size:,} bytes")
                return full_path
    
    print("❌ No cached geckodriver found")
    return None


# =============================================================================
# CONFIG + DIRECTORIES
# =============================================================================

DATA_DIR = Path("datasets/raw")
YELP_DIR = Path("datasets/scraped/Qualified_Scrapes")
MAX_CAPTCHA_TRIES = 3
MAX_TESTS = 30  # Test first N proxies

SERVICES = [
    "Soft washing",
    "Junk removal",
    "Tree service",
    "Pressure washing",
    "Gutter cleaning",
    "Window cleaning",
    "Asphalt/concrete work",
    "Driveway sealing",
]


# =============================================================================
# 🧪 PROXY POOL MANAGER
# =============================================================================

class USProxyPool:
    def __init__(self):
        self.all_proxies = []
        self.us_proxies = []
        self.live_proxies = []
        self.proxy_cycle = None
    
    async def scrape_and_test_proxies(self):
        """Complete proxy pipeline: scrape → filter US → test live"""
        print("🔄 [PROXY POOL] Scraping fresh US proxies...")
        
        # Step 1: Scrape
        url = 'https://free-proxy-list.net/'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url, headers=headers) as resp:
                html = await resp.text()
        
        soup = BeautifulSoup(html, 'lxml')
        table = soup.select_one('table.table tbody')
        
        for row in table.select('tr'):
            cols = row.select('td')
            if len(cols) >= 8:
                ip, port, country_code, country_name = [c.get_text(strip=True) for c in cols[:4]]
                if country_code == 'US' or 'United States' in country_name:
                    self.us_proxies.append(f"{ip}:{port}")
        
        print(f"📈 Found {len(self.us_proxies)} US proxies")
        
        # Step 2: Test live proxies
        print("🧪 Testing live connectivity...")
        connector = aiohttp.TCPConnector(limit=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            semaphore = asyncio.Semaphore(25)
            
            async def test_proxy(proxy):
                async with semaphore:
                    try:
                        async with session.get('http://httpbin.org/ip', 
                                             proxy=f'http://{proxy}',
                                             timeout=aiohttp.ClientTimeout(total=4)) as r:
                            return proxy if r.status == 200 else None
                    except:
                        return None
            
            tasks = [test_proxy(p) for p in self.us_proxies[:MAX_TESTS]]
            results = await asyncio.gather(*tasks)
            self.live_proxies = [p for p in results if p]
        
        print(f"✅ {len(self.live_proxies)} LIVE US PROXIES READY!")
        self.proxy_cycle = cycle(self.live_proxies)
        return self.live_proxies
    
    def get_next_proxy(self):
        return next(self.proxy_cycle)


# =============================================================================
# FIXED SELENIUM + PROXY CLASS WITH CACHED DRIVER SUPPORT
# =============================================================================

class ProxyYelpScraper:
    def __init__(self, proxy_pool: USProxyPool, profile_name="default-release", cached_driver_path=None):
        self.proxy_pool = proxy_pool
        self.profile_name = profile_name
        self.cached_driver_path = cached_driver_path
        self.driver = None
    
    def create_driver_with_proxy(self, proxy=None):
        """Create new driver with rotating proxy + cached driver support"""
        if self.driver:
            try:
                self.driver.quit()
            except: 
                pass
        
        if not proxy and self.proxy_pool.live_proxies:
            proxy = self.proxy_pool.get_next_proxy()
        elif not proxy:
            print("❌ No live proxies available!")
            return None
        
        print(f"🌐 Using proxy: {proxy}")
        
        profiles = self.get_firefox_profiles()
        if self.profile_name not in profiles:
            print(f"❌ Profile '{self.profile_name}' not found!")
            return None
        
        profile_path = profiles[self.profile_name]
        
        # Firefox options with proxy
        firefox_options = Options()
        firefox_options.profile = profile_path
        firefox_options.set_preference("network.proxy.type", 1)
        firefox_options.set_preference("network.proxy.http", proxy.split(':')[0])
        firefox_options.set_preference("network.proxy.http_port", int(proxy.split(':')[1]))
        firefox_options.set_preference("network.proxy.ssl", proxy.split(':')[0])
        firefox_options.set_preference("network.proxy.ssl_port", int(proxy.split(':')[1]))
        
        # Use cached driver if available, otherwise download
        if self.cached_driver_path and os.path.exists(self.cached_driver_path):
            print(f"🔄 Using cached geckodriver: {self.cached_driver_path}")
            service = Service(executable_path=self.cached_driver_path)
        else:
            print("📥 Downloading fresh geckodriver...")
            service = Service(GeckoDriverManager().install())
        
        seleniumwire_options = {'disable_encoding': True}
        
        self.driver = webdriver.Firefox(
            service=service,
            options=firefox_options,
            seleniumwire_options=seleniumwire_options
        )
        self.driver.set_window_size(1366, 768)
        return self.driver
    
    def get_firefox_profiles(self):
        """Detect Firefox profiles"""
        system = platform.system()
        if system != "Windows":
            return {"default": ""}
        
        appdata = os.getenv('APPDATA')
        mozilla_path = os.path.join(appdata, "Mozilla", "Firefox")
        profiles_ini = os.path.join(mozilla_path, "profiles.ini")
        
        if not os.path.exists(profiles_ini):
            return {}
        
        config = configparser.ConfigParser()
        config.read(profiles_ini)
        
        profiles = {}
        for section in config.sections():
            if section.startswith('Profile'):
                try:
                    name = config.get(section, 'Name', fallback=section)
                    rel_path = config.get(section, 'Path')
                    full_path = os.path.normpath(os.path.join(mozilla_path, rel_path))
                    if os.path.exists(full_path):
                        profiles[name] = full_path
                except:
                    continue
        return profiles
    
    def handle_captcha(self):
        """Datadome CAPTCHA solver"""
        try:
            time.sleep(3)
            wait = WebDriverWait(self.driver, 5)
            iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='captcha-delivery.com']")))
            print("🔍 CAPTCHA DETECTED")
            self.driver.switch_to.frame(iframe)
            
            slider = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".slider")))
            container = slider.find_element(By.XPATH, "./parent::*")
            
            width = container.size['width']
            distance = int(width * 0.98) + 5
            
            actions = ActionChains(self.driver)
            actions.move_to_element_with_offset(slider, 10, 8).click_and_hold().perform()
            
            for i in range(15):
                offset = int(distance/15) + random.randint(0, 2)
                actions.move_by_offset(offset, random.randint(-1, 1)).perform()
                time.sleep(random.uniform(0.02, 0.03))
            
            actions.release().perform()
            self.driver.switch_to.default_content()
            print("✅ CAPTCHA SOLVED")
            return True
        except TimeoutException:
            return False
    
    def scrape_single_zip(self, service: str, state: str, zip_code: str):
        """Main scraping logic with proxy rotation"""
        driver = self.create_driver_with_proxy()
        if not driver:
            return pd.DataFrame()
        
        business_data = []
        url = f"https://www.yelp.com/search?find_desc={service.replace(' ', '+')}&find_loc={state}+{zip_code}"
        print(f"🔗 Scraping: {url}")
        
        try:
            driver.get(url)
            time.sleep(4)
            
            # Handle CAPTCHA
            for attempt in range(MAX_CAPTCHA_TRIES):
                if self.handle_captcha():
                    time.sleep(3)
                else:
                    break
            
            page_num = 0
            while True:
                page_num += 1
                print(f"📄 Page {page_num}")
                
                xpath = '//div[@class="mainAttributes__09f24__PBx6v arrange-unit__09f24__JfPbg arrange-unit-fill__09f24__y4c05 y-css-mhg9c5"]'
                
                try:
                    containers = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, xpath))
                    )
                except TimeoutException:
                    print("🏁 No more results")
                    break
                
                for container in containers:
                    try:
                        name = container.find_element(By.XPATH, './div[1]/h3').text.strip()
                        rating = container.find_element(By.XPATH, './div[2]/div[2]/span[1]').text.strip()
                        reviews = container.find_element(By.XPATH, './div[2]/div[2]/span[2]').text.strip()
                        
                        business_data.append({
                            'name': name, 'rating': rating, 'review_count': reviews
                        })
                    except:
                        continue
                
                # Next page check
                try:
                    next_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, 
                            '//button[@class="pagination-button__09f24__QdhX3 y-css-1xmdaty" and not(contains(@class, "is-disabled"))]')))
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(3)
                except TimeoutException:
                    print("🏁 End of pages")
                    break
            
            df = pd.DataFrame(business_data).drop_duplicates()
            print(f"✅ {len(df)} businesses scraped")
            return df
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return pd.DataFrame()
        finally:
            try:
                self.driver.quit()
            except: 
                pass


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def sanitize_filename(s: str) -> str:
    """Sanitize string for use as filename"""
    return re.sub(r'[^a-zA-Z0-9_\\s-]', '_', str(s)).replace(' ', '_').strip()


def get_state_city(row):
    """Extract state and city from row"""
    return str(row['ZIP']).strip(), str(row['STATE']).strip(), str(row['CITY']).strip()


def process_zips(service: str, qualified_zips: pd.DataFrame, proxy_scraper: ProxyYelpScraper):
    """Process ZIPs with proxy rotation + resume capability"""
    temp_file = YELP_DIR / "remaining_zips.csv"
    
    if temp_file.exists():
        remaining_df = pd.read_csv(temp_file, dtype={"zip_code": str})
        remaining_zips = remaining_df["zip_code"].tolist()
        qualified_zips = qualified_zips[qualified_zips["ZIP"].isin(remaining_zips)]
        print(f"📍 RESUMING: {len(qualified_zips)} ZIPs left")
    else:
        remaining_zips = qualified_zips["ZIP"].tolist()
    
    successful_count = 0
    
    for idx, row in qualified_zips.iterrows():
        zip_code, state, city = get_state_city(row)
        print(f"\n📍 {zip_code} ({state}/{city})")
        
        df = proxy_scraper.scrape_single_zip(service, state, zip_code)
        
        if not df.empty:
            clean_service = service.lower().replace(" ", "_")
            folder = YELP_DIR / sanitize_filename(state) / sanitize_filename(city) / clean_service
            folder.mkdir(parents=True, exist_ok=True)
            
            filename = f"yelp_{clean_service}_{zip_code}.csv"
            filepath = folder / filename
            df.to_csv(filepath, index=False)
            print(f"💾 SAVED {len(df)} → {filepath}")
            successful_count += 1
        
        # Update resume file
        remaining_zips = [z for z in remaining_zips if z != zip_code]
        pd.DataFrame({"zip_code": remaining_zips}).to_csv(temp_file, index=False)
        print(f"📊 {successful_count}/{len(qualified_zips)} | {len(remaining_zips)} remaining")
        time.sleep(10)  # Be nice
    
    if not remaining_zips and temp_file.exists():
        temp_file.unlink()
        print("🎉 ALL COMPLETE!")
    
    return successful_count


async def main():
    """🚀 COMPLETE EXECUTION WITH CACHED DRIVER CHECK"""
    print("\n" + "="*80)
    print("🚀 YELP SCRAPER INITIALIZING")
    print("="*80)
    
    YELP_DIR.mkdir(exist_ok=True)
    
    # Step 0: Check for cached geckodriver FIRST
    print("\n🔍 INITIALIZING...")
    cached_driver = find_cached_geckodriver()
    
    # Step 1: Build proxy pool
    proxy_pool = USProxyPool()
    live_proxies = await proxy_pool.scrape_and_test_proxies()
    
    if not live_proxies:
        print("❌ No live proxies found! Exiting.")
        return
    
    # Step 2: Load ZIP data
    print("\n📊 Loading ZIP data...")
    zips_df = pd.read_csv(DATA_DIR / "zips_zctas_states.csv", dtype={"ZIP": str, "ZCTA": str})
    
    # Check if busy_families_housing.csv exists
    housing_file = DATA_DIR / "busy_families_housing.csv"
    if housing_file.exists():
        households_df = pd.read_csv(housing_file, usecols=["Geography", "Homeownership%", "MedianIncome", "LargeHH%"])
        households_df["ZCTA"] = households_df["Geography"].str[-5:]
        qualified_zips = zips_df.merge(households_df, on="ZCTA")
        print(f"✅ {len(qualified_zips)} qualified ZIPs loaded (from busy_families_housing.csv)")
    else:
        print("⚠️ busy_families_housing.csv not found, using all ZIPs")
        qualified_zips = zips_df
    
    # Step 3: Scrape with proxy rotation + cached driver
    scraper = ProxyYelpScraper(proxy_pool, profile_name="default-release", cached_driver_path=cached_driver)
    
    for service in SERVICES:
        print(f"\n{'='*80}")
        print(f"🚀 SERVICE: {service}")
        print(f"📁 Output: {YELP_DIR}")
        print(f"{'='*80}")
        
        n_done = process_zips(service, qualified_zips, scraper)
        print(f"✅ {service}: {n_done}/{len(qualified_zips)} ZIPs")
    
    print("\n" + "="*80)
    print("🏆 ALL SERVICES COMPLETE!")
    print("="*80)
    print(f"\nNext: Run src/business_count_processor.py to process scraped data")


if __name__ == "__main__":
    asyncio.run(main())