import logging
import argparse
import schedule
import time as _time
from datetime import datetime
from config import SCHEDULE_TIME
from database import init_db, save_article, mark_sent, get_unsent_articles
from crawler import crawl_all
from filter import filter_articles
from mailer import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("crawler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

def run(dry_run=False):
    logger.info(f"크롤러 시작 [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")

    raw = crawl_all()
    if not raw:
        logger.warning("수집된 기사 없음")
        return

    filtered = filter_articles(raw)
    if not filtered:
        logger.info("관련 기사 없음")
        return

    new = []
    for art in filtered:
        if save_article(art):
            new.append(art)
            logger.info(f"  저장: [{art['source']}] {art['title'][:50]}")

    to_send = get_unsent_articles()

    if dry_run:
        print(f"\n=== 테스트 결과: {len(to_send)}건 ===")
        for a in to_send:
            print(f"  [{a['topic']}] {a['title']}")
        return

    if send_email(to_send):
        mark_sent([a["url"] for a in to_send])
        logger.info(f"발송 완료: {len(to_send)}건")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--time", default=SCHEDULE_TIME)
    args = parser.parse_args()

    init_db()

    if args.schedule:
        logger.info(f"스케줄 모드: 매일 {args.time} 실행")
        schedule.every().day.at(args.time).do(run, dry_run=args.dry_run)
        run(dry_run=args.dry_run)
        while True:
            schedule.run_pending()
            _time.sleep(60)
    else:
        run(dry_run=args.dry_run)

if __name__ == "__main__":
    main()