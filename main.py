from pathlib import Path
import httpx
from fastapi import  FastAPI, HTTPException , Request 

app = FastAPI(title="API for fetching data from a URL")

URL = "https://books.toscrape.com/"
CACHE_FILE = Path("cache/catalogue-page-1.html")

HEADERS = {
    "User-Agent": (
        "PROJECT: shlokktiwarii"
        "(+https://github.com/Shlok Tiwari/shlokktiwarii)"
    )
}

@app.get("/")
def home():
    return {"message": "Books Scraper API is running"}

@app.get("/scrape")
async def scrape_first_page():
    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=10.0
        ) as client:

            response = await client.get(URL)

        # Checking status before doing anything with the HTML
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch catalogue page"
            )
        # Creating cache directory
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Saving the response
        CACHE_FILE.write_text(
            response.text,
            encoding="utf-8"
        )
        return {
            "status": "success",
            "status_code": response.status_code,
            "cached_file": str(CACHE_FILE)
        }
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request timed out"
        )

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Request failed: {error}"
        )
        
        