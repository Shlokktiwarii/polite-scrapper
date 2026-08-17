import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import hashlib
import re

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, ValidationError



app = FastAPI(title="Books to Scrape API")


BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = Path("cache")
DETAIL_CACHE_DIR = CACHE_DIR / "books"
OUTPUT_DIR = Path("output")
BOOKS_FILE = OUTPUT_DIR / "books.json"
ERRORS_FILE = OUTPUT_DIR / "errors.json"
FAILED_PAGES_FILE = OUTPUT_DIR / "failed_pages.json"

USER_AGENT = (
    "Books to Scrape API"
    "(+https://github.com/Shlok_Tiwari/shlokktiwarii)"
)

HEADERS = {
    "User-Agent": USER_AGENT
}

TIMEOUT = 12.0
REQUEST_DELAY = 0.5

class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl

    price_text: str
    price_gbp: float

    availability_text: str
    rating_text: str | None

    description: str | None

    source_page: HttpUrl
    fetched_at: str


# Utility functions

def cache_filename(url: str) -> str:
    """
    Creates a safe and unique filename from a URL.
    """
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"{url_hash}.html"


async def fetch_page(client: httpx.AsyncClient, url: str) -> str:
    """
    Fetch a page politely.
    """

    await asyncio.sleep(REQUEST_DELAY)

    response = await client.get(url)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch {url}"
        )

    return response.text


def get_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")

#Discover catalogue pages


def get_book_links(
    html: str,
    page_url: str
) -> list[str]:

    soup = get_soup(html)

    urls = []

    for link in soup.select("article.product_pod h3 a"):

        href = link.get("href")

        if href:
            absolute_url = urljoin(page_url, href)
            urls.append(absolute_url)

    return urls


def get_next_page(
    html: str,
    page_url: str
) -> str | None:

    soup = get_soup(html)

    next_link = soup.select_one("li.next a")

    if not next_link:
        return None

    href = next_link.get("href")

    if not href:
        return None

    return urljoin(page_url, href)


async def discover_catalogue_pages():

    catalogue_pages = []
    all_book_urls = []

    current_url = BASE_URL

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=TIMEOUT
    ) as client:

        for page_number in range(1, 4):

            cache_file = CACHE_DIR / f"catalogue-page-{page_number}.html"

            # Page 1 should already exist from Stage 1.
            if cache_file.exists():

                html = cache_file.read_text(
                    encoding="utf-8"
                )

            else:

                html = await fetch_page(
                    client,
                    current_url
                )

                CACHE_DIR.mkdir(
                    parents=True,
                    exist_ok=True
                )

                cache_file.write_text(
                    html,
                    encoding="utf-8"
                )

            catalogue_pages.append(current_url)

            book_urls = get_book_links(
                html,
                current_url
            )

            all_book_urls.extend(book_urls)

            next_url = get_next_page(
                html,
                current_url
            )

            if not next_url:
                break

            current_url = next_url

    # Remove duplicates while preserving order
    unique_urls = list(
        dict.fromkeys(all_book_urls)
    )

    return catalogue_pages, unique_urls


#Extacting book details


def extract_book(
    html: str,
    product_url: str,
    source_page: str
) -> dict:

    soup = get_soup(html)

    # Title
    title_element = soup.select_one(
        "div.product_main h1"
    )

    title = (
        title_element.get_text(strip=True)
        if title_element
        else None
    )

    # Price
    price_element = soup.select_one(
        "div.product_main .price_color"
    )

    price_text = (
        price_element.get_text(strip=True)
        if price_element
        else None
    )

    # Availability
    availability_element = soup.select_one(
        "div.product_main .availability"
    )

    availability_text = (
        availability_element.get_text(
            " ",
            strip=True
        )
        if availability_element
        else None
    )

    # Rating
    rating_element = soup.select_one(
        "div.product_main .star-rating"
    )

    rating_text = None

    if rating_element:

        classes = rating_element.get("class", [])

        rating_names = {
            "One",
            "Two",
            "Three",
            "Four",
            "Five"
        }

        for value in classes:

            if value in rating_names:
                rating_text = value
                break

    # Description
    description_element = soup.select_one(
        "#product_description + p"
    )

    if description_element:
        description = description_element.get_text(
            " ",
            strip=True
        )
    else:
        description = None

    # Fetch timestamp
    fetched_at = datetime.now(
        timezone.utc
    ).isoformat()

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }

def normalize_price(
    price_text: str
) -> float:

    # £51.77 -> 51.77
    match = re.search(
        r"(\d+(?:\.\d+)?)",
        price_text
    )

    if not match:
        raise ValueError(
            f"Could not parse price: {price_text}"
        )

    return float(match.group(1))


def normalize_record(
    raw_record: dict
) -> dict:

    normalized = raw_record.copy()

    normalized["price_gbp"] = normalize_price(
        raw_record["price_text"]
    )

    return normalized

def save_json(
    path: Path,
    data
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )


def validate_and_store(
    raw_records: list[dict]
):

    valid_records = []
    errors = []

    seen_urls = set()

    for raw_record in raw_records:

        try:

            normalized = normalize_record(
                raw_record
            )

            validated = BookRecord.model_validate(
                normalized
            )

            url = str(
                validated.product_url
            )

            # Canonical URL is the identity
            if url in seen_urls:
                continue

            seen_urls.add(url)

            valid_records.append(
                validated.model_dump(
                    mode="json"
                )
            )

        except (
            ValueError,
            ValidationError
        ) as error:

            errors.append(
                {
                    "record": raw_record,
                    "reason": str(error)
                }
            )

    save_json(
        BOOKS_FILE,
        valid_records
    )

    save_json(
        ERRORS_FILE,
        errors
    )

    return valid_records, errors

# FastAPI endpoints


@app.get("/")
def home():

    return {
        "message": "Books to Scrape API is running"
    }


@app.get("/discover")
async def discover():

    catalogue_pages, unique_urls = (
        await discover_catalogue_pages()
    )

    return {
        "catalogue_pages": len(catalogue_pages),
        "discovered": len(unique_urls),
        "unique_urls": len(unique_urls),
        "book_urls": unique_urls
    }


@app.get("/extract")
async def extract_books():

    catalogue_pages, unique_urls = (
        await discover_catalogue_pages()
    )

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    DETAIL_CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    records = []
    failed_pages=[]

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=TIMEOUT
    ) as client:

        for index, product_url in enumerate(
            unique_urls,
            start=1
        ):

            # Determine catalogue source page
            source_page_index = (
                (index - 1) // 20
            )

            if source_page_index >= len(
                catalogue_pages
            ):
                source_page_index = 0

            source_page = catalogue_pages[
                source_page_index
            ]

        
            # Read cached detail page


            try:
               cache_file = (
                   DETAIL_CACHE_DIR
                   / cache_filename(product_url)
               )

               if cache_file.exists():
                   html = cache_file.read_text(
                       encoding="utf-8"
                   )
               else:
                   html = await fetch_page(
                       client,
                       product_url
                   )

                   cache_file.write_text(
                       html,
                       encoding="utf-8"
                   )

               # Extracting raw record
               record = extract_book(
                   html,
                   product_url,
                   source_page
               )

               records.append(record)

            except Exception as error:
               failed_pages.append({
                   "url": product_url,
                   "reason": str(error)
               })
               continue
    valid_records, errors = validate_and_store(records)
    save_json(
        ERRORS_FILE,
        errors
    )
    save_json(
        FAILED_PAGES_FILE,
        failed_pages
    )

    return {
        "detail_pages": len(records),
        "valid_records": len(valid_records),
        "invalid_records": len(errors),
        "books_file": str(BOOKS_FILE),
        "errors_file": str(ERRORS_FILE),
        "failed_pages_file": str(OUTPUT_DIR / "failed_pages.json"),
        "failed_pages": failed_pages    
    }