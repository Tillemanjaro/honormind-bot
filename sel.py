from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import json
import os

# Configure headless browser
options = Options()
options.headless = True
driver = webdriver.Chrome(options=options)

BASE_URL = "https://bg3.wiki"
ALL_PAGES_URL = f"{BASE_URL}/wiki/Special:AllPages"
OUTPUT_DIR = "bg3_wiki_dump"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_all_wiki_links():
    print("🔍 Collecting all page links...")
    driver.get(ALL_PAGES_URL)
    time.sleep(2)
    all_links = set()

    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_links = soup.select(".mw-allpages-body a")
        for link in page_links:
            href = link.get("href")
            if href and href.startswith("/wiki/") and not href.startswith("/wiki/Special:"):
                all_links.add(BASE_URL + href)

        # Check for next page
        next_link = soup.select_one("a.mw-allpages-nav[href*='from=']")
        if next_link:
            next_url = BASE_URL + next_link["href"]
            driver.get(next_url)
            time.sleep(1)
        else:
            break

    print(f"✅ Found {len(all_links)} pages.")
    return list(all_links)

def scrape_page(url):
    driver.get(url)
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    title = soup.find("h1", id="firstHeading").text.strip()
    content_div = soup.find("div", class_="mw-parser-output")

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

def main():
    all_links = get_all_wiki_links()

    for i, link in enumerate(all_links):
        try:
            print(f"📄 Scraping ({i+1}/{len(all_links)}): {link}")
            page_data = scrape_page(link)
            file_name = os.path.join(OUTPUT_DIR, f"{page_data['title'].replace('/', '_')}.json")
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Error scraping {link}: {e}")
            continue

    print("🏁 Scraping complete!")
    driver.quit()

if __name__ == "__main__":
    main()
