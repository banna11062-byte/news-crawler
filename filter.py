import os
import json
import time
import logging
import requests

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

SYSTEM_PROMPT = """당신은 건축/엔지니어링/건설/데이터센터 분야 뉴스 큐레이터입니다.
주어진 기사를 분석하여 관련 토픽 분류 + 짧은 요약을 작성해주세요.

[관심 토픽]
- 건축설계, 엔지니어링, 건설사업관리(CM/PMC)
- 설계공모, 인허가, 공정관리, 감리
- 데이터센터, AI 데이터센터, 데이터센터 법령/신기술

[요약 규칙]
- 2~3문장으로 핵심만 요약
- 기자 이름, "(엔지니어링데일리)" 같은 머리말 제외
- 자연스러운 한국어로 다시 써주기
- 원문 그대로 베끼지 말고 핵심을 재구성

응답은 반드시 JSON 형식으로만. 다른 말 절대 금지.
{
  "topic": "해당 토픽",
  "summary": "2~3문장으로 요약된 핵심 내용"
}"""


def _call_gemini(prompt, retry=0):
    try:
        response = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            },
            timeout=30
        )

        if response.status_code == 429:
            wait = 60 * (retry + 1)
            logger.warning(f"한도 초과. {wait}초 대기 후 재시도")
            if retry < 3:
                time.sleep(wait)
                return _call_gemini(prompt, retry + 1)
            return None

        if response.status_code in (500, 502, 503, 504):
            logger.warning(f"서버 오류 {response.status_code}. 30초 대기 후 재시도")
            if retry < 2:
                time.sleep(30)
                return _call_gemini(prompt, retry + 1)
            return None

        response.raise_for_status()
        return response.json()

    except Exception as e:
        logger.error(f"API 오류: {e}")
        return None


def filter_articles(articles):
    if not articles:
        return []

    result = []
    for i, art in enumerate(articles):
        logger.info(f"필터링 중... ({i+1}/{len(articles)})")
        filtered = _filter_one(art)
        if filtered:
            result.append(filtered)
        if i < len(articles) - 1:
            time.sleep(5)

    logger.info(f"필터링: {len(articles)}건 → {len(result)}건")
    return result


def _filter_one(article):
    text = (
        f"제목: {article['title']}\n"
        f"출처: {article['source']}\n"
        f"본문: {article.get('summary','')[:800]}"
    )
    prompt = SYSTEM_PROMPT + f"\n\n아래 기사를 분석해주세요.\n\n{text}"

    raw = _call_gemini(prompt)
    if not raw:
        art = dict(article)
        art["topic"] = article.get("topic", "기타")
        return art

    try:
        raw_text = raw["candidates"][0]["content"]["parts"][0]["text"].strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        data = json.loads(raw_text)
        art = dict(article)
        art["topic"] = data.get("topic", article.get("topic", "기타"))
        art["summary"] = data.get("summary", article.get("summary", ""))
        return art

    except Exception as e:
        logger.error(f"파싱 오류: {e}")
        art = dict(article)
        art["topic"] = article.get("topic", "기타")
        return art
