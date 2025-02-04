import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Function to check if a URL belongs to the same domain
def is_same_domain(base_url, url):
    return urlparse(url).netloc == urlparse(base_url).netloc

# Function to format the page content
def format_content(soup):
    formatted_text = []
    
    # Add headings
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = heading.name
        formatted_text.append(f"\n{'#' * int(level[1:])} {heading.get_text().strip()}\n")
    
    # Add paragraphs
    for paragraph in soup.find_all('p'):
        formatted_text.append(f"{paragraph.get_text().strip()}\n")
    
    # Add lists
    for ul in soup.find_all('ul'):
        for li in ul.find_all('li'):
            formatted_text.append(f"- {li.get_text().strip()}\n")
        formatted_text.append("\n")  # Separate lists with a blank line
    
    # Add blockquotes
    for blockquote in soup.find_all('blockquote'):
        formatted_text.append(f"> {blockquote.get_text().strip()}\n")
    
    # Join all parts into a single string
    return "\n".join(formatted_text).strip()

# Function to scrape a single page
def scrape_page(url, base_url, session, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            print(f"Scraping: {url}")
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Format the page content
                formatted_content = format_content(soup)
                
                # Save the page content
                filename = f"scraped_pages/{url.replace('https://', '').replace('http://', '').replace('/', '_')}.txt"
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"URL: {url}\n")
                    f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(formatted_content)
                
                # Extract all links on the page
                links = set()
                for a_tag in soup.find_all("a", href=True):
                    link = urljoin(base_url, a_tag["href"])
                    if is_same_domain(base_url, link):
                        links.add(link)
                
                return links
            else:
                logging.warning(f"Failed to retrieve {url} (Status Code: {response.status_code})")
                retries += 1
        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")
            retries += 1
            time.sleep(2 ** retries)  # Exponential backoff
    return set()

# Main function to start scraping
def scrape_website(start_url, max_depth=3, max_workers=10):
    visited = set()
    session = requests.Session()  # Reuse TCP connection
    futures = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Initial scrape
        futures.append(executor.submit(scrape_page, start_url, start_url, session))
        
        current_depth = 1
        while current_depth <= max_depth:
            next_level_links = set()
            for future in as_completed(futures):
                links = future.result()
                for link in links:
                    if link not in visited:
                        next_level_links.add(link)
                        visited.add(link)
            
            # Submit new tasks for the next depth level
            futures = [executor.submit(scrape_page, link, start_url, session) for link in next_level_links]
            current_depth += 1

# Example usage
if __name__ == "__main__":
    start_url = input("Enter: ")  # Replace with the target website
    scrape_website(start_url)