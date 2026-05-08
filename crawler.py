import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from config import SITES, KEYWORDS, HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT, MAX_ARTICLES_PER_SITE
from database import is_duplicate

logger = logging.getLogger(__name__)

def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.warning(f"페이지 로딩 실패 [{url}]: {e}")
        return None

def has_keyword(text):
    return any(kw in text for kw in KEYWORDS)

def extract_article_body(url):
    soup = fetch_page(url)
    if not soup:
        return ""
    for selector in ["div#article-view-content-div", "div.article-body",
                     "div#articleBodyContents", "div.news_txt",
                     "article", "div.view_con"]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(separator=" ", strip=True)[:300]
    return ""

def parse_engdaily(list_url, base_url):
    soup = fetch_page(list_url)
    if not soup:
        return []

    articles = []
    # 기사 링크 전체 탐색
    for a_tag in soup.select("a[href*='articleView']"):
        title = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")
        if not href.startswith("http"):
            url = urljoin(base_url, href)
        else:
            url = href

        if not title or not url:
            continue
        if len(title) < 10:
            continue
        if is_duplicate(url):
            continue
        if not has_keyword(title):
            continue

        articles.append({
            "title": title,
            "url": url,
            "date": "",
            "summary": "",
            "source": "엔지니어링데일리",
            "topic": "",
            "relevance": "",
        })

    # 중복 URL 제거
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    logger.info(f"[엔지니어링데일리] {list_url} → {len(unique)}건")
    return unique

def parse_dnews(list_url, base_url):
    soup = fetch_page(list_url)
    if not soup:
        return []

    articles = []
    for a_tag in soup.select("a[href*='article']"):
        title = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")
        if not href.startswith("http"):
            url = urljoin(base_url, href)
        else:
            url = href

        if not title or not url:
            continue
        if len(title) < 10:
            continue
        if is_duplicate(url):
            continue
        if not has_keyword(title):
            continue
        if "dnews.co.kr" not in url:
            continue

        articles.append({
            "title": title,
            "url": url,
            "date": "",
            "summary": "",
            "source": "대한경제",
            "topic": "",
            "relevance": "",
        })

    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    logger.info(f"[대한경제] {list_url} → {len(unique)}건")
    return unique

SITE_PARSERS = {
    "엔지니어링데일리": parse_engdaily,
    "대한경제": parse_dnews,
}

def crawl_all():
    all_articles = []
    for site_name, site_cfg in SITES.items():
        parser = SITE_PARSERS.get(site_name)
        if not parser:
            continue

        site_articles = []
        for url in site_cfg["list_urls"]:
            articles = parser(url, site_cfg["base_url"])
            site_articles.extend(articles)
            time.sleep(REQUEST_DELAY)

        for art in site_articles[:MAX_ARTICLES_PER_SITE]:
            if not art["summary"]:
                art["summary"] = extract_article_body(art["url"])
                time.sleep(REQUEST_DELAY)

        all_articles.extend(site_articles[:MAX_ARTICLES_PER_SITE])

    logger.info(f"총 {len(all_articles)}건 수집 완료")
    return all_articles