from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json
import os
import re
from datetime import datetime

# === CONFIGURATION ===
BASE_URL = "https://bg3.wiki"
ALL_PAGES_URL = f"{BASE_URL}/wiki/Special:AllPages"
OUTPUT_DIR = "bg3_wiki_dump"
URL_LIST_FILE = "wiki_urls.txt"
LOG_FILE = "scrape_log.txt"

# === SETUP ===
os.makedirs(OUTPUT_DIR, exist_ok=True)

options = Options()
options.headless = True
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    full_msg = f"{timestamp} {msg}"
    print(full_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n")

# === DISCOVER ALL INDEX SEGMENTS (A, B, C, ..., Z, Others) ===
def get_all_index_segments():
    driver.get(ALL_PAGES_URL)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    segment_links = []

    nav_div = soup.find("div", class_="mw-allpages-nav")
    if nav_div:
        for a in nav_div.find_all("a"):
            href = a.get("href")
            if href and href.startswith("/wiki/Special:AllPages?from="):
                full_url = BASE_URL + href
                segment_links.append(full_url)

    log(f"🔠 Found {len(segment_links)} index segments (A–Z & more).")
    return segment_links

# === SCRAPE ALL LINKS FROM ONE SEGMENT PAGE ===
def collect_links_from_segment(start_url):
    log(f"🔍 Crawling segment: {start_url}")
    driver.get(start_url)
    time.sleep(2)

    links = set()
    page_count = 0

    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_links = soup.select(".mw-allpages-body a")
        new_links = 0

        for link in page_links:
            href = link.get("href")
            if href and href.startswith("/wiki/") and not href.startswith("/wiki/Special:"):
                full_url = BASE_URL + href
                if full_url not in links:
                    links.add(full_url)
                    new_links += 1

        page_count += 1
        log(f"📄 Segment page {page_count}: {new_links} new links (segment total: {len(links)})")

        # Follow "next" pagination inside segment
        next_link = None
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if href.startswith("/wiki/Special:AllPages?from=") and href != start_url.replace(BASE_URL, ""):
                next_link = BASE_URL + href
                break

        if next_link and next_link != driver.current_url:
            driver.get(next_link)
            time.sleep(1)
        else:
            break

    return links

# === GET ALL WIKI LINKS ACROSS ALL SEGMENTS ===
def get_all_wiki_links():
    all_links = set()
    segments = get_all_index_segments()

    # Also include the default A-page segment (initial landing)
    segments.insert(0, ALL_PAGES_URL)

    for segment_url in segments:
        segment_links = collect_links_from_segment(segment_url)
        all_links.update(segment_links)

    # Save links
    with open(URL_LIST_FILE, "w", encoding="utf-8") as f:
        for url in sorted(all_links):
            f.write(url + "\n")

    log(f"✅ Total unique article links collected: {len(all_links)}")
    return list(all_links)

# === SCRAPE SINGLE PAGE CONTENT ===
def scrape_page(url):
    driver.get(url)
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    title_tag = soup.find("h1", id="firstHeading")
    content_div = soup.find("div", class_="mw-parser-output")

    if not title_tag or not content_div:
        return None

    title = title_tag.text.strip()
    paragraphs = [p.get_text(strip=True) for p in content_div.find_all("p", recursive=False) if p.get_text(strip=True)]
    headers = [h.get_text(strip=True) for h in content_div.find_all(["h2", "h3"])]
    lists = [li.get_text(strip=True) for li in content_div.find_all("li")]

    return {
        "url": url,
        "title": title,
        "paragraphs": paragraphs,
        "headers": headers,
        "lists": lists
    }

# === MAIN SCRAPER LOGIC ===
def main():
    links = get_all_wiki_links()

    for i, link in enumerate(links):
        try:
            log(f"🔎 Scraping ({i + 1}/{len(links)}): {link}")
            page_data = scrape_page(link)
            if not page_data:
                log(f"⚠️ Skipped (no content): {link}")
                continue

            safe_title = re.sub(r'[<>:"/\\|?*]', "_", page_data["title"]).strip().replace(" ", "_")
            file_path = os.path.join(OUTPUT_DIR, f"{safe_title}.json")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            log(f"❌ Error scraping {link}: {e}")
            continue

    driver.quit()
    log("🏁 All pages scraped successfully.")

if __name__ == "__main__":
    main()
