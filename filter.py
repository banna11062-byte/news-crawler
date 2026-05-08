import json
import time
import logging
import requests

logger = logging.getLogger(__name__)

GEMINI_API_KEY = "AIzaSyBVvmsGCUNK1jbUuWmiudB323VmW6FtbR8"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

SYSTEM_PROMPT = """당신은 건축/엔지니어링/건설 분야 뉴스 큐레이터입니다.
주어진 기사 목록을 분석하여 다음 토픽과 관련된 기사만 선별해 주세요.

[관심 토픽]
- 건축설계 (설계공모, 건축사사무소, 인허가, 기본·실시설계 등)
- 엔지니어링 (구조, 기계설비, 전기, 소방, 토목 설계 등)
- 건설사업관리 (CM, PMC, 공정관리, 원가관리, 품질관리, 안전관리 등)

[제외 기준]
- 단순 시공·공사 낙찰 결과
- 부동산 분양·매매 정보
- 건설사 실적·주가 정보

응답은 반드시 아래 JSON 형식으로만 답하세요. 다른 말은 하지 마세요.
{
  "filtered": [
    {
      "index": 0,
      "topic": "해당 토픽",
      "relevance": "관련성 설명 한 줄"
    }
  ]
}"""


def _call_gemini(prompt, retry=0):
    """429 뜨면 자동으로 기다렸다가 재시도"""
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

        # 429 = 한도 초과 → 기다렸다가 재시도
        if response.status_code == 429:
            wait = 60 * (retry + 1)  # 1분, 2분, 3분...
            logger.warning(f"API 한도 초과. {wait}초 대기 후 재시도 ({retry+1}번째)")
            time.sleep(wait)
            return _call_gemini(prompt, retry + 1)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        if retry < 3:
            logger.warning(f"타임아웃. 30초 대기 후 재시도")
            time.sleep(30)
            return _call_gemini(prompt, retry + 1)
        return None
    except Exception as e:
        logger.error(f"API 오류: {e}")
        return None


def filter_articles(articles):
    if not articles:
        return []
    result = []
    BATCH_SIZE = 30
    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i:i+BATCH_SIZE]
        filtered = _filter_batch(batch)
        result.extend(filtered)
        # 배치 사이 30초 대기 (한도 초과 방지)
        if i + BATCH_SIZE < len(articles):
            logger.info("다음 배치 전 30초 대기...")
            time.sleep(30)

    logger.info(f"필터링: {len(articles)}건 → {len(result)}건")
    return result


def _filter_batch(batch):
    text = ""
    for i, art in enumerate(batch):
        text += (
            f"[{i}] 출처: {art['source']}\n"
            f"    제목: {art['title']}\n"
            f"    요약: {art.get('summary','')[:150]}\n\n"
        )

    prompt = SYSTEM_PROMPT + f"\n\n아래 기사를 분석해주세요.\n\n{text}"

    raw = _call_gemini(prompt)
    if not raw:
        return []

    try:
        raw_text = raw["candidates"][0]["content"]["parts"][0]["text"].strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        data = json.loads(raw_text)
        filtered = []
        for item in data.get("filtered", []):
            idx = item["index"]
            if 0 <= idx < len(batch):
                art = dict(batch[idx])
                art["topic"] = item.get("topic", "")
                art["relevance"] = item.get("relevance", "")
                filtered.append(art)
        return filtered

    except Exception as e:
        logger.error(f"파싱 오류: {e}")
        return []