import time
import logging
import requests
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from config import SITES, GOOGLE_NEWS_QUERIES, KEYWORDS, HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT, ENGDAILY_COUNT, GOOGLE_NEWS_COUNT
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


def fetch_xml(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, "lxml-xml")
    except Exception as e:
        logger.warning(f"XML 로딩 실패 [{url}]: {e}")
        return None


def has_keyword(text):
    return any(kw in text for kw in KEYWORDS)


def upgrade_image_url(url):
    if not url:
        return ""
    url = url.replace("/thumb/", "/photo/")
    url = url.replace("_v150.", ".")
    url = url.replace("_v300.", ".")
    url = url.replace("_v400.", ".")
    url = url.replace("_v640.", ".")
    if url.startswith("http://"):
        url = "https://" + url[7:]
    return url


def resolve_google_news_url(url):
    """구글 뉴스 URL을 실제 기사 URL로 변환"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        return resp.url
    except Exception as e:
        logger.warning(f"URL 변환 실패: {e}")
        return url


def extract_article_data(url):
    soup = fetch_page(url)
    if not soup:
        return "", "", ""

    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    if not title:
        h_tag = soup.select_one("h1, h2.article-head-title, h3.heading")
        if h_tag:
            title = h_tag.get_text(strip=True)

    body = ""
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        body = og_desc["content"].strip()

    if not body:
        for selector in ["div#article-view-content-div", "div.article-body",
                         "div#articleBodyContents", "div.news_txt",
                         "article", "div.view_con"]:
            el = soup.select_one(selector)
            if el:
                body = el.get_text(separator=" ", strip=True)[:1000]
                break

    image = ""
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image = og_image["content"]
    else:
        for selector in ["div#article-view-content-div img", "div.article-body img",
                         "article img", "div.view_con img"]:
            img_el = soup.select_one(selector)
            if img_el and img_el.get("src"):
                image = img_el["src"]
                if not image.startswith("http"):
                    image = urljoin(url, image)
                break

    image = upgrade_image_url(image)
    return title, body, image


def parse_engdaily(list_url, base_url, source_name):
    soup = fetch_page(list_url)
    if not soup:
        return []

    articles = []
    seen_urls = set()
    for a_tag in soup.select("a[href*='articleView']"):
        href = a_tag.get("href", "")
        if not href.startswith("http"):
            url = urljoin(base_url, href)
        else:
            url = href

        if url in seen_urls:
            continue
        seen_urls.add(url)

        if is_duplicate(url):
            continue
        if base_url.replace("https://", "").replace("http://", "") not in url:
            continue

        articles.append({
            "title": "",
            "url": url,
            "date": "",
            "summary": "",
            "image": "",
            "source": source_name,
            "topic": "",
            "relevance": "",
        })

    logger.info(f"[{source_name}] {list_url} -> {len(articles)}건 후보")
    return articles


def parse_google_news(query):
    rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    soup = fetch_xml(rss_url)
    if not soup:
        return []

    articles = []
    items = soup.find_all("item")[:GOOGLE_NEWS_COUNT * 3]

    for item in items:
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        source_el = item.find("source")

        if not title_el or not link_el:
            continue

        title = title_el.get_text(strip=True)
        url = link_el.get_text(strip=True)

        if " - " in title:
            parts = title.rsplit(" - ", 1)
            title = parts[0].strip()

        source_name = source_el.get_text(strip=True) if source_el else "구글뉴스"

        summary = ""
        if desc_el:
            desc_html = desc_el.get_text(strip=True)
            desc_soup = BeautifulSoup(desc_html, "html.parser")
            summary = desc_soup.get_text(separator=" ", strip=True)[:500]

        if is_duplicate(url):
            continue

        articles.append({
            "title": title,
            "url": url,
            "date": "",
            "summary": summary,
            "image": "",
            "source": source_name,
            "topic": query,
            "relevance": "",
        })

    logger.info(f"[구글뉴스: {query}] -> {len(articles)}건")
    return articles


def crawl_all():
    all_articles = []

    engdaily_collected = []
    for site_key, site_cfg in SITES.items():
        source_name = site_cfg.get("name", site_key)
        candidates = []
        for url in site_cfg["list_urls"]:
            articles = parse_engdaily(url, site_cfg["base_url"], source_name)
            candidates.extend(articles)
            time.sleep(REQUEST_DELAY)

        seen = set()
        unique = []
        for a in candidates:
            if a["url"] not in seen:
                seen.add(a["url"])
                unique.append(a)

        for art in unique:
            if len(engdaily_collected) >= ENGDAILY_COUNT:
                break
            title, body, image = extract_article_data(art["url"])
            if not title:
                continue
            if not has_keyword(title):
                continue
            art["title"] = title
            art["summary"] = body
            art["image"] = image
            engdaily_collected.append(art)
            time.sleep(REQUEST_DELAY)

    all_articles.extend(engdaily_collected)
    logger.info(f"엔지니어링데일리: {len(engdaily_collected)}건 수집")

    engdaily_missing = ENGDAILY_COUNT - len(engdaily_collected)
    target_google_count = GOOGLE_NEWS_COUNT + max(0, engdaily_missing)

    query_results = {}
    for query in GOOGLE_NEWS_QUERIES:
        articles = parse_google_news(query)
        query_results[query] = articles
        time.sleep(REQUEST_DELAY)

    google_collected = []
    used_urls = set()
    round_idx = 0
    while len(google_collected) < target_google_count:
        added = False
        for query in GOOGLE_NEWS_QUERIES:
            if len(google_collected) >= target_google_count:
                break
            articles = query_results.get(query, [])
            if round_idx < len(articles):
                art = articles[round_idx]
                if art["url"] not in used_urls:
                    used_urls.add(art["url"])
                    try:
                        real_url = resolve_google_news_url(art["url"])
                        art["url"] = real_url
                        _, _, image = extract_article_data(real_url)
                        art["image"] = image
                        time.sleep(REQUEST_DELAY)
                    except Exception as e:
                        logger.warning(f"이미지 추출 실패: {e}")
                    google_collected.append(art)
                    added = True
        if not added:
            break
        round_idx += 1

    all_articles.extend(google_collected)
    logger.info(f"구글뉴스: {len(google_collected)}건 수집")

    logger.info(f"총 {len(all_articles)}건 수집 완료")
    return all_articles
