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

SYSTEM_PROMPT = """당신은 건축/엔지니어링/건설 분야 뉴스 큐레이터입니다.
주어진 기사 목록을 분석하여 다음 토픽과 관련된 기사만 선별해 주세요.

[관심 토픽]
- 건축설계 (설계공모, 건축사사무소, 인허가 등)
- 엔지니어링 (구조, 기계설비, 전기, 토목 설계 등)
- 건설사업관리 (CM, PMC, 공정관리, 안전관리 등)

응답은 반드시 JSON 형식으로만 답하세요. 다른 말은 하지 마세요.
{
  "filtered": [
    {
      "index": 0,
      "topic": "해당 토픽",
      "relevance": "관련성 설명 한 줄"
    }
  ]
}"""


def filter_articles(articles):
    if not articles:
        return []

    result = []
    for i, art in enumerate(articles):
        logger.info(f"필터링 중... ({i+1}/{len(articles)})")
        filtered = _filter_one(art, i)
        if filtered:
            result.append(filtered)
        if i < len(articles) - 1:
            time.sleep(5)

    logger.info(f"필터링: {len(articles)}건 → {len(result)}건")
    return result


def _filter_one(article, idx):
    text = (
        f"[0] 출처: {article['source']}\n"
        f"    제목: {article['title']}\n"
        f"    요약: {article.get('summary','')[:150]}\n"
    )
    prompt = SYSTEM_PROMPT + f"\n\n아래 기사를 분석해주세요.\n\n{text}"

    try:
        response = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1}
            },
            timeout=30
        )

        if response.status_code == 429:
            logger.warning(f"한도 초과. 60초 대기 후 재시도")
            time.sleep(60)
            return _filter_one(article, idx)

        response.raise_for_status()
        raw = response.json()
        raw_text = raw["candidates"][0]["content"]["parts"][0]["text"].strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        data = json.loads(raw_text)
        for item in data.get("filtered", []):
            art = dict(article)
            art["topic"] = item.get("topic", "")
            art["relevance"] = item.get("relevance", "")
            return art
        return None

    except Exception as e:
        logger.error(f"필터링 오류: {e}")
        return None
