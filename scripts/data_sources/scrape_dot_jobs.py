import concurrent.futures
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
import os
import threading
import itertools
from tqdm import tqdm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. CONFIGURATION
# ==========================================
START_JID = 1
END_JID = 999999 
MAX_WORKERS = 10 
CHUNK_SIZE = 1000

BASE_URL = "https://cityjobs.nyc.gov/job/posting-jid-{jid}"
DOWNLOADS_FOLDER = os.path.join(os.path.expanduser('~'), 'Downloads')
RAW_FILE_PATH = os.path.join(DOWNLOADS_FOLDER, 'nyc_jobs_RAW.csv')
CLEAN_FILE_PATH = os.path.join(DOWNLOADS_FOLDER, 'nyc_jobs_PRISTINE.csv')

# ==========================================
# 2. NETWORK SETUP
# ==========================================
thread_local = threading.local()

def get_session():
    if not hasattr(thread_local, "session"):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        thread_local.session = session
    return thread_local.session

# ==========================================
# 3. EXTRACTION LOGIC (The Scraper)
# ==========================================
def fetch_and_parse(jid):
    url = BASE_URL.format(jid=jid)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    session = get_session()
    
    try:
        response = session.get(url, headers=headers, timeout=15, verify=False)
        
        status = "Active"
        if response.status_code != 200 or "not found" in response.url.lower():
            status = "Expired / Not Found"
        elif "/jobs" in response.url.lower() and "/job/" not in response.url.lower():
            status = "Expired / Redirected"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        if soup.find(string=lambda t: t and "no longer available" in t.lower()) or \
           soup.find(string=lambda t: t and "has now expired" in t.lower()):
            status = "Expired / Tombstone"

        title_elem = soup.find('h1', class_='header') or soup.find('h1')
        title = title_elem.text.strip() if title_elem else None

        if not title and "Expired" in status:
            return None

        # --- Extractor Helpers ---
        def extract_next(keyword):
            elem = soup.find(string=lambda t: t and keyword.lower() in t.lower().strip())
            if elem and elem.parent.find_next_sibling(['p', 'div', 'span']):
                return elem.parent.find_next_sibling(['p', 'div', 'span']).text.strip()
            return np.nan

        def extract_section(keyword):
            header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4', 'strong', 'p'] and keyword.lower() in tag.text.lower())
            if header:
                content = []
                sib = header.find_next_sibling()
                while sib and sib.name not in ['h2', 'h3', 'h4']:
                    content.append(sib.text.strip())
                    sib = sib.find_next_sibling()
                return "\n".join(content).strip()
            return np.nan

        def extract_inline(keyword):
            elem = soup.find(string=lambda t: t and keyword.lower() in t.lower())
            if elem and ":" in elem:
                return elem.split(":", 1)[1].strip()
            return extract_next(keyword)

        # --- Map to exact 31-Column Schema ---
        raw_salary = extract_next("Salary range") if pd.isna(extract_next("Salary range")) is False else extract_next("Salary")
        
        record = {
            "job_id": jid,
            "business_title": title,
            "agency": extract_next("Agency"),
            "posting_date": extract_next("Posted on"),
            "post_until": extract_next("Posted until") if pd.isna(extract_next("Posted until")) is False else extract_next("Post until"),
            "civil_service_title": extract_next("Civil service title"),
            "title_code_no": extract_next("Title code"),
            "title_classification": extract_next("Title classification"),
            "level": extract_next("Job level"),
            "career_level": extract_inline("Experience level"),
            "job_category": extract_inline("Category"),
            "full_time_part_time_indicator": extract_next("Full-time") if soup.find(string=lambda t: t and "Full-time" in t) else "Part-time",
            "raw_salary_string": raw_salary, # To be split in the cleaning phase
            "work_location": extract_next("Work location") if pd.isna(extract_next("Work location")) is False else extract_next("Location"),
            "division_work_unit": extract_next("Department") if pd.isna(extract_next("Department")) is False else extract_next("Division/Work Unit"),
            "number_of_positions": extract_next("Number of positions"),
            "job_description": extract_section("Job Description"),
            "minimum_qual_requirements": extract_section("Minimum Qualifications"),
            "preferred_skills": extract_section("Preferred Skills"),
            "additional_information": extract_section("Additional Information"),
            "to_apply": extract_section("To Apply"),
            "residency_requirement": extract_section("Residency Requirement"),
            "source_version": "HTML_Scrape",
            "scrape_status": status,
            "url": response.url
        }
        return record
        
    except Exception:
        return None

# ==========================================
# 4. CLEANING LOGIC (The Pandas Formatter)
# ==========================================
def clean_dataset(input_csv, output_csv):
    print("\nInitiating Phase 2: Data Integrity Cleaning...")
    df = pd.read_csv(input_csv, dtype=str, low_memory=False)
    
    # 1. Clean Text & Carriage Returns
    text_cols = df.select_dtypes(include=['object']).columns
    for col in text_cols:
        df[col] = df[col].str.replace(r'[\r\n]+', ' ', regex=True).str.strip()
        df[col] = df[col].replace(r'^(nan|None|)$', np.nan, regex=True)

    # 2. Parse Salaries
    if 'raw_salary_string' in df.columns:
        # Regex to extract numeric values from strings like "$60,549.00 – $82,435.00"
        salaries = df['raw_salary_string'].str.replace(',', '').str.extractall(r'(\d+\.?\d*)')
        if not salaries.empty:
            df['salary_range_from'] = salaries.xs(0, level='match')[0].astype(float)
            if 1 in salaries.index.get_level_values('match'):
                df['salary_range_to'] = salaries.xs(1, level='match')[0].astype(float)
            else:
                df['salary_range_to'] = df['salary_range_from'] # If only one salary is listed
    
    # 3. Enforce Dates & Numbers
    for col in ['posting_date', 'post_until']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
    df['job_id'] = pd.to_numeric(df['job_id'], errors='coerce')
    df.dropna(subset=['job_id'], inplace=True)
    df['job_id'] = df['job_id'].astype(int)

    # 4. Standardize Values
    if 'civil_service_title' in df.columns:
        df['civil_service_title'] = df['civil_service_title'].str.upper()
    if 'full_time_part_time_indicator' in df.columns:
        df['full_time_part_time_indicator'] = df['full_time_part_time_indicator'].str.upper().str[:1]

    # Fill NaNs
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Not Specified")

    # Export
    df.to_csv(output_csv, index=False, date_format='%Y-%m-%d %H:%M:%S')
    print(f"Pristine Dataset saved to: {output_csv}")

# ==========================================
# 5. EXECUTION PIPELINE
# ==========================================
def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, size))
        if not chunk: break
        yield chunk

def main():
    print(f"=== PHASE 1: EXTRACTION ===")
    start_jid = START_JID
    
    if os.path.exists(RAW_FILE_PATH):
        try:
            df_existing = pd.read_csv(RAW_FILE_PATH, usecols=['job_id'])
            if not df_existing.empty:
                start_jid = int(df_existing['job_id'].max()) + 1
                print(f"Found existing raw data. Resuming scrape from JID {start_jid}...")
        except Exception:
            pass

    write_header = not os.path.exists(RAW_FILE_PATH)
    
    for chunk in chunked_iterable(range(start_jid, END_JID + 1), CHUNK_SIZE):
        chunk_records = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_and_parse, j): j for j in chunk}
            batch_label = "Batch {}-{}".format(chunk[0], chunk[-1])
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(chunk), desc=batch_label, unit="req"):
                res = future.result()
                if res: chunk_records.append(res)