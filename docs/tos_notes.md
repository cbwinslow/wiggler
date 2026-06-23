# ToS / robots.txt Policy Notes

This document tracks per-domain Terms of Service and robots.txt analysis for Wiggler.

---

## MLB Properties

| Domain | robots.txt | ToS automated scripts | Wiggler status |
|---|---|---|---|
| mlb.com | Publishes sitemaps; blocks `/api/`, `/app/`, `/embed/`, `/tv/`, `/search` | **Explicitly prohibited** | HARD BLOCKED |
| www.mlb.com | Same as mlb.com | **Explicitly prohibited** | HARD BLOCKED |
| m.mlb.com | Mobile; same policy | **Explicitly prohibited** | HARD BLOCKED |
| tickets.mlb.com | Ticketing subdomain | **Explicitly prohibited** | HARD BLOCKED |

**MLB ToS reference:** MLB's Terms of Use state users must not use automated scripts to collect information from or otherwise interact with MLB Digital Properties.

MLB sitemap endpoints (safe for URL discovery only, not automated body scraping):
- `https://www.mlb.com/sitemap/news-48h.xml` (48-hour news)
- `https://www.mlb.com/sitemap/news-weekly.xml` (weekly news)

---

## Local / Regional News Sites

Each site must be evaluated independently. General guidance:
- Parse robots.txt before crawling.
- Read ToS for automation/scraping clauses.
- Default to conservative 2-second crawl delay unless robots.txt specifies otherwise.
- Do not store full article body unless the site's license permits it.

---

## Adding a New Domain

To add a domain to Wiggler's policy registry:
1. Check `https://domain.com/robots.txt` manually.
2. Read the site's Terms of Use for automated access clauses.
3. If restricted: add to `_TOS_RESTRICTED` in `crawltop/core/robots.py`.
4. If allowed: configure crawl delay and allowed paths in settings.
5. Document findings in this file.

---

_Last updated: v0.3_
