import time
import requests
import psycopg2
from psycopg2.extras import execute_values
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ---------------------------------------------
# 1. BASIC UTILITIES
# ---------------------------------------------

def clean(text):
    """Remove extra spaces and line breaks."""
    if not text:
        return None
    return " ".join(text.split())


def extract_labeled_field(soup, label_text):
    """
    Extracts fields like:
    Agency: Department of Sanitation
    """
    label = soup.find("label", string=lambda t: t and label_text.lower() in t.lower())
    if not label:
        return None
    return clean(label.find_parent().get_text().replace(label_text, ""))


def extract_dynamic_field(soup, field_name):
    """
    Extracts fields inside the JobInformationWidget.
    Example:
    Title code -> 13643
    """
    name = soup.find(
        "p",
        class_="attrax-job-information-widget__dynamic-field-name",
        string=lambda t: t and field_name.lower() in t.lower()
    )
    if not name:
        return None

    value = name.find_next_sibling("p")
    return clean(value.get_text()) if value else None


def extract_section_by_heading(soup, heading_text):
    """
    Extracts sections like:
    Minimum Qualifications
    Preferred Skills
    Additional Information
    """
    header = soup.find(string=lambda t: t and heading_text.lower() in t.lower())
    if not header:
        return None

    container = header.parent
    texts = []

    for sib in container.find_next_siblings():
        # Stop when next section header appears
        if sib.name == "div" and "jobad-" in " ".join(sib.get("class", [])):
            break
        texts.append(sib.get_text(" ", strip=True))

    return "\n".join([t for t in texts if t.strip()])


# ---------------------------------------------
# 2. SCRAPING LOGIC
# ---------------------------------------------

BASE = "https://cityjobs.nyc.gov"
SEARCH_URL = f"{BASE}/jobs"


def get_job_links(page_soup):
    """Find all job detail links on a search results page."""
    links = set()
    for a in page_soup.select("a[href*='-jid-']"):
        href = a.get("href")
        if href:
            links.add(urljoin(BASE, href))
    return links


def crawl_all_job_links():
    """Go through all pages of the job listings and collect job URLs."""
    all_links = set()
    page = 1

    while True:
        print(f"Checking page {page}...")
        resp = requests.get(SEARCH_URL, params={"page": page}, timeout=10)

        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        links = get_job_links(soup)

        if not links:
            break

        print(f"Found {len(links)} jobs on page {page}")
        all_links.update(links)

        page += 1
        time.sleep(1)  # polite delay

    return sorted(all_links)


def scrape_job(url):
    """Scrape all metadata from a single job posting."""
    print(f"Scraping job: {url}")
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    job = {"url": url}

    # Title
    title_el = soup.select_one("h1.header__text")
    job["title"] = clean(title_el.get_text()) if title_el else None

    # Labeled fields
    job["agency"] = extract_labeled_field(soup, "Agency")
    job["job_type"] = extract_labeled_field(soup, "Job type")
    job["category"] = extract_labeled_field(soup, "Category")
    job["experience_level"] = extract_labeled_field(soup, "Experience level")

    # Dynamic fields
    job["job_id"] = extract_dynamic_field(soup, "Job ID")
    job["title_code"] = extract_dynamic_field(soup, "Title code")
    job["civil_service_title"] = extract_dynamic_field(soup, "Civil service title")
    job["business_title"] = extract_dynamic_field(soup, "Business title")
    job["work_location"] = extract_dynamic_field(soup, "Work location")
    job["department"] = extract_dynamic_field(soup, "Department")
    job["job_level"] = extract_dynamic_field(soup, "Job level")
    job["number_of_positions"] = extract_dynamic_field(soup, "Number of positions")

    # Salary
    salary = soup.select_one(".salary-widget span span")
    job["salary_range"] = clean(salary.get_text()) if salary else None

    # Posting date
    posted = soup.select_one(".date-widget .date-label")
    if posted:
        job["posting_date"] = clean(
            posted.parent.get_text().replace("Posted on:", "")
        )

    # Description
    desc = soup.select_one("[aria-label='Job description']")
    job["description"] = desc.get_text("\n", strip=True) if desc else None

    # Sections
    job["minimum_qualifications"] = extract_section_by_heading(soup, "Minimum Qualifications")
    job["preferred_skills"] = extract_section_by_heading(soup, "Preferred Skills")
    job["additional_information"] = extract_section_by_heading(soup, "Additional Information")
    job["residency_requirement"] = extract_section_by_heading(soup, "Residency Requirement")

    return job


def scrape_all_jobs():
    """Full pipeline: get all job links, then scrape each job."""
    links = crawl_all_job_links()
    print(f"Total jobs found: {len(links)}")

    jobs = []
    for i, url in enumerate(links, 1):
        print(f"[{i}/{len(links)}]")
        try:
            jobs.append(scrape_job(url))
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        time.sleep(0.5)

    return jobs


# ---------------------------------------------
# 3. POSTGRESQL STORAGE
# ---------------------------------------------

def save_jobs_to_postgres(jobs, conn_string):
    """Save all scraped jobs into PostgreSQL using bulk upsert."""
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()

    fields = [
        "url", "title", "job_id", "agency", "job_type", "category",
        "experience_level", "title_code", "civil_service_title",
        "business_title", "work_location", "department", "job_level",
        "number_of_positions", "salary_range", "posting_date",
        "description", "minimum_qualifications", "preferred_skills",
        "additional_information", "residency_requirement"
    ]

    rows = [[job.get(f) for f in fields] for job in jobs]

    sql = f"""
        INSERT INTO cityjobs ({",".join(fields)})
        VALUES %s
        ON CONFLICT (url) DO UPDATE SET
        {",".join([f"{f}=EXCLUDED.{f}" for f in fields if f != "url"])};
    """

    execute_values(cur, sql, rows)
    conn.commit()
    cur.close()
    conn.close()

    print("Jobs saved to PostgreSQL.")


# ---------------------------------------------
# 4. MAIN ENTRY POINT
# ---------------------------------------------

if __name__ == "__main__":
    jobs = scrape_all_jobs()

    save_jobs_to_postgres(
        jobs,
        conn_string="dbname=cityjobs user=postgres password=YOURPASS host=localhost"
    )
