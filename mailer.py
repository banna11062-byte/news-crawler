import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import EMAIL_ADDRESS, EMAIL_APP_PASSWORD, SMTP_HOST, SMTP_PORT, RECIPIENT_EMAILS

logger = logging.getLogger(__name__)


def clean_summary(summary, title):
    if not summary:
        return ""
    if "기자" in summary[:50] and "=" in summary[:50]:
        eq_pos = summary.find("=")
        if 0 < eq_pos < 50:
            summary = summary[eq_pos+1:].strip()
    if title and summary.startswith(title):
        summary = summary[len(title):].strip()
    return summary


def build_card(art, is_first):
    image = art.get("image", "")
    image_html = ""
    if image and is_first:
        image_html = '<div style="width:100%;height:200px;overflow:hidden;background:#F1EFE8;"><img src="' + image + '" style="width:100%;height:100%;object-fit:cover;" alt=""></div>'

    title = art.get("title", "")
    summary = clean_summary(art.get("summary", ""), title)
    if len(summary) > 150:
        summary = summary[:150] + "..."

    source = art.get("source", "엔지니어링데일리")
    url = art["url"]

    return (
        '<div style="background:#fff;border:0.5px solid #E5E5E0;border-radius:12px;margin-bottom:14px;overflow:hidden;">'
        + image_html
        + '<div style="padding:16px 18px;">'
        + '<div style="font-size:11px;color:#EA6A1F;font-weight:500;margin-bottom:6px;">' + source + '</div>'
        + '<div style="font-size:16px;font-weight:500;color:#2C2C2A;line-height:1.4;margin-bottom:8px;">' + title + '</div>'
        + '<div style="font-size:13px;color:#5F5E5A;line-height:1.7;margin-bottom:12px;">' + summary + '</div>'
        + '<a href="' + url + '" style="display:inline-block;background:#FAEEDA;color:#854F0B;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:500;text-decoration:none;" target="_blank">기사 전문 보기 →</a>'
        + '</div></div>'
    )


def build_html(articles):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    cards = "".join(build_card(art, i == 0) for i, art in enumerate(articles))

    header = (
        '<div style="background:#EA6A1F;padding:32px 28px;text-align:center;color:#fff;">'
        + '<div style="font-size:11px;letter-spacing:4px;opacity:0.85;margin-bottom:8px;">DAILY NEWSLETTER</div>'
        + '<div style="font-size:32px;font-weight:500;letter-spacing:-0.5px;margin-bottom:6px;">선진레터</div>'
        + '<div style="font-size:13px;opacity:0.9;">' + today + ' · ' + str(len(articles)) + '건</div>'
        + '</div>'
    )

    footer = (
        '<div style="background:#fff;padding:16px;text-align:center;color:#888780;font-size:11px;border-top:0.5px solid #E5E5E0;">'
        + '선진레터 · 출처: 엔지니어링데일리<br>매일 오전 8시 자동 발송'
        + '</div>'
    )

    return (
        '<!DOCTYPE html><html lang="ko"><body style="margin:0;padding:0;background:#f5f5f5;font-family:Apple SD Gothic Neo,Noto Sans KR,sans-serif;">'
        + '<div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;border:0.5px solid #E5E5E0;">'
        + header
        + '<div style="padding:24px 20px 8px;background:#fff;">' + cards + '</div>'
        + footer
        + '</div></body></html>'
    )


def send_email(articles):
    if not articles:
        return False
    today = datetime.now().strftime("%Y.%m.%d")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "[선진레터] " + today + " — " + str(len(articles)) + "건"
    msg["From"] = "선진레터 <" + EMAIL_ADDRESS + ">"
    msg["To"] = ", ".join(RECIPIENT_EMAILS)
    msg.attach(MIMEText(build_html(articles), "html", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAILS, msg.as_string())
        logger.info("메일 발송 완료")
        return True
    except Exception as e:
        logger.error("메일 발송 오류: " + str(e))
        return False
