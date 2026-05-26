# 💻 Code Generation

Manhattan Mission Control can generate ready-to-run code snippets for any dataset. This guide shows what's available and how to use the generated code.

---

## How to Generate Code

1. Find a dataset using the search
2. Click **`</> Code`** on the dataset card
3. Select your preferred language from the tabs
4. Click **📋 Copy** to copy to clipboard, or **⬇ Download** to save the file

---

## Python

### What you get

A complete Python script that:
- Connects to the Socrata API using `sodapy`
- Fetches the dataset into a pandas DataFrame
- Prints the first few rows and basic statistics

### Example output

```python
# Manhattan Mission Control — Generated Code
# Dataset: NYC Sidewalk Inspection Results
# ID: abc1-2345
# Generated: 2025-05-26

from sodapy import Socrata
import pandas as pd

# Initialize client
# Get a free app token at https://data.cityofnewyork.us/
client = Socrata(
    "data.cityofnewyork.us",
    "YOUR_APP_TOKEN",   # Replace with your token, or None for anonymous access
    timeout=30
)

# Fetch data (adjust limit as needed)
results = client.get("abc1-2345", limit=2000)
df = pd.DataFrame.from_records(results)

# Basic exploration
print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
print("\nColumn types:")
print(df.dtypes)
print("\nFirst 5 rows:")
print(df.head())
print("\nBasic statistics:")
print(df.describe())
```

### Running the code

```bash
pip install sodapy pandas
python nyc_sidewalk_inspections.py
```

---

## R

### What you get

An R script using `httr` and `jsonlite` to fetch and explore the dataset.

### Example output

```r
# Manhattan Mission Control — Generated Code
# Dataset: NYC Sidewalk Inspection Results
# Generated: 2025-05-26

library(httr)
library(jsonlite)
library(dplyr)

# Configuration
DATASET_ID <- "abc1-2345"
APP_TOKEN  <- "YOUR_APP_TOKEN"   # or "" for anonymous
BASE_URL   <- "https://data.cityofnewyork.us/resource"

# Fetch data
url <- paste0(BASE_URL, "/", DATASET_ID, ".json")
response <- GET(
  url,
  add_headers("X-App-Token" = APP_TOKEN),
  query = list("$limit" = 1000)
)

if (http_status(response)$category != "Success") {
  stop("API error: ", content(response, "text"))
}

df <- fromJSON(content(response, "text", encoding = "UTF-8"))

# Explore
cat("Rows:", nrow(df), "Cols:", ncol(df), "\n")
str(df)
head(df)
summary(df)
```

### Running the code

```r
install.packages(c("httr", "jsonlite", "dplyr"))
source("nyc_sidewalk_inspections.R")
```

---

## JavaScript

### What you get

A JavaScript snippet using the Fetch API. Works in the browser console, Node.js, or any JS environment.

### Example output

```javascript
// Manhattan Mission Control — Generated Code
// Dataset: NYC Sidewalk Inspection Results
// Generated: 2025-05-26

const DATASET_ID = 'abc1-2345';
const APP_TOKEN  = 'YOUR_APP_TOKEN';  // or '' for anonymous
const LIMIT      = 1000;

async function fetchDataset() {
  const url = new URL(
    `https://data.cityofnewyork.us/resource/${DATASET_ID}.json`
  );
  url.searchParams.set('$limit', LIMIT);

  const response = await fetch(url, {
    headers: APP_TOKEN ? { 'X-App-Token': APP_TOKEN } : {}
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  console.log(`Fetched ${data.length} rows`);
  console.table(data.slice(0, 5));
  return data;
}

fetchDataset().catch(console.error);
```

### Running in Node.js

```bash
node nyc_sidewalk_inspections.js
```

### Running in the browser

Paste directly into the browser developer console (F12 → Console).

---

## SOQL Query

### What you get

A pre-built SOQL query URL you can open directly in your browser or use with curl/fetch.

### Example output

```
# Direct API URL (open in browser):
https://data.cityofnewyork.us/resource/abc1-2345.json?$limit=1000

# With SOQL filter:
https://data.cityofnewyork.us/resource/abc1-2345.json?$query=SELECT borough, COUNT(*) GROUP BY borough ORDER BY COUNT(*) DESC&$limit=100

# With curl:
curl "https://data.cityofnewyork.us/resource/abc1-2345.json?$limit=100" \
  -H "X-App-Token: YOUR_APP_TOKEN"

# Export as CSV:
https://data.cityofnewyork.us/resource/abc1-2345.csv?$limit=1000
```

---

## GitHub Actions

### What you get

A complete GitHub Actions workflow that automatically fetches the dataset on a schedule and saves it as a CSV artifact.

### Example output

```yaml
# .github/workflows/fetch-nyc-data.yml
# Manhattan Mission Control — Generated Workflow
# Dataset: NYC Sidewalk Inspection Results

name: Fetch NYC Data

on:
  schedule:
    - cron: '0 6 * * 1'   # Every Monday at 6am UTC
  workflow_dispatch:        # Manual trigger

jobs:
  fetch:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install sodapy pandas

      - name: Fetch dataset
        env:
          SOCRATA_APP_TOKEN: ${{ secrets.SOCRATA_APP_TOKEN }}
        run: |
          python - <<'EOF'
          from sodapy import Socrata
          import pandas as pd

          client = Socrata("data.cityofnewyork.us",
                           "$SOCRATA_APP_TOKEN")
          results = client.get("abc1-2345", limit=50000)
          df = pd.DataFrame.from_records(results)
          df.to_csv("data/nyc_sidewalk_inspections.csv", index=False)
          print(f"Saved {len(df)} rows")
          EOF

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: nyc-data-${{ github.run_number }}
          path: data/*.csv
          retention-days: 30

      - name: Commit updated data
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add data/*.csv
          git diff --staged --quiet || git commit -m "chore: update dataset $(date +%Y-%m-%d)"
          git push
```

### Setup

1. Go to your GitHub repo → **Settings → Secrets → New repository secret**
2. Add `SOCRATA_APP_TOKEN` with your Socrata token
3. Create the workflow file in `.github/workflows/`
4. Push to trigger immediately, or wait for the scheduled run

---

## Jupyter Notebook

### What you get

A downloadable `.ipynb` file with:
- **Cell 1:** Dataset metadata and description
- **Cell 2:** Import statements and configuration
- **Cell 3:** Data loading with progress indicator
- **Cell 4:** Basic EDA (shape, dtypes, head, describe)
- **Cell 5:** Missing values analysis
- **Cell 6:** Visualization template (bar chart of top values)
- **Cell 7:** Export to CSV

### Running the notebook

```bash
pip install jupyter sodapy pandas matplotlib seaborn
jupyter notebook nyc_sidewalk_inspections.ipynb
```

Or use **JupyterLab:**
```bash
pip install jupyterlab
jupyter lab nyc_sidewalk_inspections.ipynb
```

Or upload to **Google Colab** — just drag the `.ipynb` file to [colab.research.google.com](https://colab.research.google.com).

---

## README Generator

### What you get

A `README.md` template for a project built around this dataset, including:
- Dataset description and source citation
- Installation instructions
- Usage examples (Python)
- Data dictionary (auto-generated from column names)
- License section

### Example output

```markdown
# NYC Sidewalk Inspection Analysis

Data source: [NYC Sidewalk Inspection Results](https://data.cityofnewyork.us/dataset/abc1-2345)
provided by NYC Open Data under the [NYC Open Data Terms of Use](https://opendata.cityofnewyork.us/overview/#termsofuse).

## Dataset

| Field | Value |
|-------|-------|
| **ID** | abc1-2345 |
| **Rows** | ~250,000 |
| **Updated** | 2025-05-01 |
| **Category** | Transportation |

## Setup

\`\`\`bash
pip install sodapy pandas
python analysis.py
\`\`\`

## Usage

...
```

---

## Tips for Using Generated Code

### Getting a Socrata App Token

Generated code includes `YOUR_APP_TOKEN` as a placeholder. Replace it with a real token to avoid rate limiting:

1. Register at [data.cityofnewyork.us](https://data.cityofnewyork.us/) (free)
2. Go to **Developer Settings → Create New App Token**
3. Copy the token and paste it into your code

Or use an environment variable:
```bash
export SOCRATA_APP_TOKEN=your_token_here
```

```python
import os
token = os.environ.get("SOCRATA_APP_TOKEN")
```

### Adjusting Row Limits

The default limit is 1,000 rows. To fetch more:
```python
results = client.get("abc1-2345", limit=50000)
```

For very large datasets (> 100k rows), use pagination:
```python
offset = 0
batch_size = 50000
all_results = []

while True:
    batch = client.get("abc1-2345", limit=batch_size, offset=offset)
    if not batch:
        break
    all_results.extend(batch)
    offset += batch_size

df = pd.DataFrame.from_records(all_results)
```

---

*[[Home]] · [[Feature-Reference]] · [[SOQL-Guide]] · [[API-Keys-Setup]]*
