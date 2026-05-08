import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta
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

def is_recent(date_text):
    """어제 또는 오늘 기사인지 확인"""
    if not date_text:
        return True  # 날짜 없으면 일단 포함
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return today in date_text or yesterday in date_text

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

def parse_site(list_url, base_url, source_name):
    soup = fetch_page(list_url)
    if not soup:
        return []

    articles = []
    for a_tag in soup.select("a[href*='articleView'], a[href*='article']"):
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
        if base_url.replace("https://", "").replace("http://", "") not in url:
            continue

        # 날짜 추출
        parent = a_tag.parent
        date_el = None
        for _ in range(5):
            if parent is None:
                break
            date_el = parent.select_one("span.dates, em.dates, span.date, dd.txt-date, span.time")
            if date_el:
                break
            parent = parent.parent
        date = date_el.get_text(strip=True) if date_el else ""

        articles.append({
            "title": title,
            "url": url,
            "date": date,
            "summary": "",
            "source": source_name,
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

    # 최신 10개만
    unique = unique[:MAX_ARTICLES_PER_SITE]
    logger.info(f"[{source_name}] {list_url} -> {len(unique)}건")
    return unique

def crawl_all():
    all_articles = []
    for site_key, site_cfg in SITES.items():
        source_name = site_cfg.get("name", site_key)
        site_articles = []
        for url in site_cfg["list_urls"]:
            articles = parse_site(url, site_cfg["base_url"], source_name)
            site_articles.extend(articles)
            time.sleep(REQUEST_DELAY)

        for art in site_articles:
            if not art["summary"]:
                art["summary"] = extract_article_body(art["url"])
                time.sleep(REQUEST_DELAY)

        all_articles.extend(site_articles)

    # 전체 합쳐서 최신 10개만
    all_articles = all_articles[:MAX_ARTICLES_PER_SITE]
    logger.info(f"총 {len(all_articles)}건 수집 완료")
    return all_articles
