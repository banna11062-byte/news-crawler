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

def extract_article_data(url):
    soup = fetch_page(url)
    if not soup:
        return "", ""

    body = ""
    for selector in ["div#article-view-content-div", "div.article-body",
                     "div#articleBodyContents", "div.news_txt",
                     "article", "div.view_con"]:
        el = soup.select_one(selector)
        if el:
            body = el.get_text(separator=" ", strip=True)[:500]
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

    return body, image

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

        articles.append({
            "title": title,
            "url": url,
            "date": "",
            "summary": "",
            "image": "",
            "source": source_name,
            "topic": "",
            "relevance": "",
        })

    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    unique = unique[:MAX_ARTICLES_PER_SITE]
    logger.info(f"[{source_name}] {list_url} -> {len(unique)}건")
    return unique

def crawl_all():
    all_articles = []
    for site_key, site_cfg in SITES.items():
        source_name = site_cfg.get("name", site_key)
        if source_name != "엔지니어링데일리":
            continue
        site_articles = []
        for url in site_cfg["list_urls"]:
            articles = parse_site(url, site_cfg["base_url"], source_name)
            site_articles.extend(articles)
            time.sleep(REQUEST_DELAY)

        for art in site_articles:
            if not art["summary"]:
                body, image = extract_article_data(art["url"])
                art["summary"] = body
                art["image"] = image
                time.sleep(REQUEST_DELAY)

        all_articles.extend(site_articles)

    all_articles = all_articles[:MAX_ARTICLES_PER_SITE]
    logger.info(f"총 {len(all_articles)}건 수집 완료")
    return all_articles
