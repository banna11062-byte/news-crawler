import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")
RECIPIENT_EMAILS = [e.strip() for e in os.getenv("RECIPIENT_EMAILS", "").split(",") if e.strip()]
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

SITES = {
    "engineering_daily": {
        "base_url": "https://www.engdaily.com",
        "list_urls": [
            "https://www.engdaily.com/news/articleList.html?sc_section_code=S1N1&view_type=sm",
            "https://www.engdaily.com/news/articleList.html?sc_section_code=S1N2&view_type=sm",
            "https://www.engdaily.com/news/articleList.html?sc_section_code=S1N3&view_type=sm",
            "https://www.engdaily.com/news/articleList.html?sc_section_code=S1N5&view_type=sm",
        ],
        "name": "엔지니어링데일리",
    },
}

GOOGLE_NEWS_QUERIES = [
    "데이터센터 법령",
    "데이터센터 신기술",
    "AI 데이터센터",
]

ENGDAILY_COUNT = int(os.getenv("ENGDAILY_COUNT", "3"))
GOOGLE_NEWS_COUNT = int(os.getenv("GOOGLE_NEWS_COUNT", "5"))

TOPICS = [
    "건축설계", "엔지니어링", "건설사업관리",
    "CM", "PMC", "설계공모", "건축사", "구조설계",
    "기계설비설계", "전기설계", "인허가", "공정관리",
    "사업관리", "감리", "타당성조사", "기본설계", "실시설계",
    "데이터센터", "AI 데이터센터", "데이터센터 법령",
]

KEYWORDS = [
    "설계", "엔지니어링", "건설사업관리", "CM", "PMC",
    "건축", "건설", "시공", "감리", "공정", "구조",
    "기계설비", "전기", "소방", "인허가", "착공", "준공",
    "발주", "입찰", "공모", "수주", "설계비",
    "기본계획", "기본설계", "실시설계", "타당성",
    "데이터센터", "IDC", "AIDC",
]

SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "08:00")
DB_PATH = os.getenv("DB_PATH", "news_crawler.db")
MAX_ARTICLES_PER_SITE = int(os.getenv("MAX_ARTICLES_PER_SITE", "5"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.5"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}
