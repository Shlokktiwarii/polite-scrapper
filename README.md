# Books to Scrape — Scraper

### Target

**Website:** Books to Scrape  
**URL:** https://books.toscrape.com/

Books to Scrape is a sandbox website specifically created for practicing web scraping. The website states that it is a safe environment for people to learn and practice scraping.

### Why this site?

I selected Books to Scrape because it is explicitly designed for scraping practice. This makes it an appropriate and permitted target for this internship assignment.

### Scope

The scraper will collect data from **only the first 3 catalogue pages**.

The scraper will not crawl the entire website or follow unrelated links.

### Robots.txt

I checked:

https://books.toscrape.com/robots.txt

**Result:** No robots.txt file was found.

Therefore, there is no robots.txt file providing additional crawling instructions for this site.

> A missing robots.txt file is not treated as permission by itself. The site's explicit statement that it is a sandbox for practicing scraping is the basis for selecting this target.

### Data to Collect

For each book, the scraper will collect:

- Book title
- Price
- Availability
- Rating
- Book URL

Only publicly available catalogue information will be collected.

### Why is this data appropriate?

This data is directly displayed on the catalogue pages and is necessary for demonstrating basic web scraping, parsing, and data extraction without collecting personal or sensitive information.

## Scraping Rules

This scraper follows these rules:

1. Only the first 3 catalogue pages are scraped.
2. A request timeout is used.
3. The HTTP status code is checked before parsing the response.
4. The downloaded pages are cached locally.
5. The cached copies are used during development instead of repeatedly requesting the website.
6. The scraper identifies itself using a descriptive User-Agent.
7. This code will not be reused on another site without checking that site's rules and terms first.

## Project Structure

```text
scraper/
├── README.md
├── .gitignore
├── src/
│   └── main.py
└── cache/
    └── catalogue-page-1.html
