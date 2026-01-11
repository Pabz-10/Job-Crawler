import csv
import json
import os
import re
from datetime import datetime, timedelta
from jobspy import scrape_jobs
import pandas as pd

def parse_date(date_input) -> str:
    """
    Parses a date string or datetime object and returns a standardized 'YYYY-MM-DD' string.
    Returns a fallback date for unparsable formats.
    """
    today = datetime.now()
    
    # Handle None, NaN, or empty inputs
    if pd.isna(date_input) or date_input is None:
        return today.strftime('%Y-%m-%d')  # Use today instead of 1970
    
    # If it's already a datetime object, just format it
    if isinstance(date_input, (datetime, pd.Timestamp)):
        return date_input.strftime('%Y-%m-%d')
    
    # If it's not a string at this point, try converting
    if not isinstance(date_input, str):
        try:
            return pd.to_datetime(date_input).strftime('%Y-%m-%d')
        except:
            return today.strftime('%Y-%m-%d')
    
    date_str = date_input.strip()
    if not date_str:
        return today.strftime('%Y-%m-%d')
    
    date_str_lower = date_str.lower()

    # Handle relative dates
    if 'hour' in date_str_lower or 'just posted' in date_str_lower or 'today' in date_str_lower:
        return today.strftime('%Y-%m-%d')
    if 'yesterday' in date_str_lower:
        return (today - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Handle 'X days/weeks ago'
    try:
        if 'day' in date_str_lower:
            days = int(re.search(r'(\d+)', date_str_lower).group(1))
            return (today - timedelta(days=days)).strftime('%Y-%m-%d')
        if 'week' in date_str_lower:
            weeks = int(re.search(r'(\d+)', date_str_lower).group(1))
            return (today - timedelta(days=weeks * 7)).strftime('%Y-%m-%d')
    except (ValueError, AttributeError):
        pass

    # Final attempt: general purpose date parser
    try:
        return pd.to_datetime(date_str).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return today.strftime('%Y-%m-%d')


def filter_by_experience(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters out jobs that explicitly require 3 or more years of experience
    in the description.
    """
    if 'description' not in df.columns:
        return df

    def check_experience(description: str) -> bool:
        if not isinstance(description, str):
            return False

        # 1. Clean the description to remove HTML tags before searching
        clean_description = re.sub(r'<[^>]+>', ' ', description)
        
        # 2. Regex to find numbers followed by "year" or "yr", accounting for "+"
        # e.g., "10+ years", "5 years", "3-5 yrs"
        matches = re.findall(r'\b(\d+)\s*[-–]?\s*(\d*)\s*\+?\s*y(?:ea)?rs?', clean_description, re.IGNORECASE)
        
        for match in matches:
            # Check the first number in a potential range (e.g., the "3" in "3-5 years")
            try:
                # The first number in the match tuple is the primary one
                year_str = match[0] if isinstance(match, tuple) else match
                years_required = int(year_str)
                if years_required >= 3:
                    return True  # High experience requirement found
            except (ValueError, IndexError):
                continue
        return False

    mask = df['description'].apply(check_experience)
    
    initial_count = len(df)
    df_filtered = df[~mask]
    filtered_count = initial_count - len(df_filtered)

    if filtered_count > 0:
        print(f"Filtered out {filtered_count} jobs based on experience requirements (>= 3 years).")
        
    return df_filtered


# Define search queries and locations
QUERIES = [
    "new grad software engineer",
    "new grad software developer",
    "junior software developer",
    "entry level software engineer",
    "software developer",
    "recent graduate software engineer",
    "junior backend developer",
    "junior frontend developer",
    "junior full stack developer"
]
LOCATIONS = ["Vancouver, BC", "Toronto, ON"]
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src')
OUTPUT_FILE = os.path.join(DATA_DIR, 'jobs.json')

def run_scraper():
    """
    Scrapes jobs from multiple sites for specified queries and locations,
    then saves the results to a JSON file.
    """
    all_jobs_list = []
    
    print(f"Starting scrape at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Scrape jobs using python-jobspy
    for query in QUERIES:
        for location in LOCATIONS:
            print(f"Scraping for '{query}' in '{location}'...")
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin", "glassdoor", "google", "zip_recruiter"],
                    search_term=query,
                    location=location,
                    results_wanted=25,
                    hours_old=24,
                    country_indeed='Canada',
                )
                
                if jobs is not None and not jobs.empty:
                    print(f"Found {len(jobs)} jobs.")
                    
                    # Debug: Check what's in the date_posted column
                    if 'date_posted' in jobs.columns:
                        print(f"Sample dates before processing: {jobs['date_posted'].head().tolist()}")
                        print(f"Date types: {jobs['date_posted'].dtype}")
                    else:
                        print(f"Available columns: {jobs.columns.tolist()}")
                    
                    all_jobs_list.append(jobs)
                else:
                    print("No jobs found for this query.")
            except Exception as e:
                print(f"An error occurred while scraping '{query}' in '{location}': {e}")

    if not all_jobs_list:
        print("Scraping complete. No jobs found in total.")
        return

    # Combine all found jobs into a single DataFrame
    final_df = pd.concat(all_jobs_list, ignore_index=True)

    # --- Post-Scraping Filtering ---
    # Remove jobs that are clearly not entry-level based on title
    negative_keywords = ['senior', 'sr', 'lead', 'principal', 'staff', 'manager', 'architect', 'experienced', 'structural']
    # The regex `(?i)` makes it case-insensitive. `\b` ensures we match whole words.
    pattern = r'(?i)\b(' + '|'.join(negative_keywords) + r')\b'

    # Keep rows where the title does NOT contain any of the negative keywords
    initial_count = len(final_df)
    final_df = final_df[~final_df['title'].str.contains(pattern, regex=True, na=False)]
    filtered_count = initial_count - len(final_df)
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} jobs with senior-level keywords in the title.")
    
    # 2. Filter by experience in description
    final_df = filter_by_experience(final_df)

    # --- Data Cleaning and Processing ---
    # Fill missing values
    final_df.fillna({'description': 'No description available.'}, inplace=True)

    # Standardize column names and select the most relevant ones
    final_df.rename(columns={'job_url': 'link', 'date_posted': 'date'}, inplace=True)
    
    # Ensure all required columns exist, add them if they don't
    required_cols = ['title', 'company', 'location', 'date', 'link', 'site', 'description']
    for col in required_cols:
        if col not in final_df.columns:
            final_df[col] = 'N/A'

    # Keep only the relevant columns
    final_df = final_df[required_cols]

    # Remove duplicate jobs based on the job link
    final_df.drop_duplicates(subset=['link'], keep='first', inplace=True)

    # Sort jobs by date (newest first)
    final_df['date_numeric'] = pd.to_datetime(final_df['date'], errors='coerce')
    final_df.sort_values(by='date_numeric', ascending=False, inplace=True)
    final_df.drop(columns=['date_numeric'], inplace=True)
    
    # --- Save to JSON ---
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Standardize and sort by date using the new robust function
    final_df['date'] = final_df['date'].apply(parse_date)
    final_df.sort_values(by='date', ascending=False, inplace=True)
    
    jobs_list_of_dicts = final_df.to_dict(orient='records')
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(jobs_list_of_dicts, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully saved {len(jobs_list_of_dicts)} unique jobs to {os.path.abspath(OUTPUT_FILE)}")
if __name__ == "__main__":
    run_scraper()