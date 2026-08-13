from pathlib import Path
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
from fastapi import  FastAPI, HTTPException , Request 

app = FastAPI(title="API for fetching data from a URL")

BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = Path("cache")

HEADERS = {
    "User-Agent": (
        "PROJECT: shlokktiwarii"
        "(+https://github.com/Shlok Tiwari/shlokktiwarii)"
    )
}

def get_book_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")\

    book_urls = []

    for link in soup.select("article.product_pod h3 a"):
        href = link.get("href")

        if href:
            absolute_url = urljoin(page_url, href)
            book_urls.append(absolute_url)

    return book_urls


def get_next_page(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one("li.next a")

    if not next_link:
        return None

    href = next_link.get("href")

    if not href:
        return None

    return urljoin(page_url, href)


@app.get("/discover")
def discover_books():

    catalogue_pages = 0
    discovered_urls = []

    current_url = BASE_URL

    while catalogue_pages < 3:

        catalogue_pages += 1

        # Page 1 comes from the cache
        if catalogue_pages == 1:
            cache_file = CACHE_DIR / "catalogue-page-1.html"

            if not cache_file.exists():
                return {
                    "error": "Run Stage 1 first. "
                             "catalogue-page-1.html not found."
                }

            html = cache_file.read_text(encoding="utf-8")

        else:
            # Stage 2 will later fetch/cache pages 2 and 3
            # For now, this keeps the structure ready.
            break

        book_urls = get_book_links(html, current_url)

        discovered_urls.extend(book_urls)

        next_url = get_next_page(html, current_url)

        if not next_url:
            break

        current_url = next_url

    unique_urls = list(dict.fromkeys(discovered_urls))

    return {
        "catalogue_pages": catalogue_pages,
        "discovered": len(discovered_urls),
        "unique_urls": len(unique_urls),
        "book_urls": unique_urls,
    }
