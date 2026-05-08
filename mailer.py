import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import EMAIL_ADDRESS, EMAIL_APP_PASSWORD, SMTP_HOST, SMTP_PORT, RECIPIENT_EMAILS

logger = logging.getLogger(__name__)

TOPIC_COLORS = {
    "건축설계": "#2563EB",
    "엔지니어링": "#059669",
    "건설사업관리": "#D97706",
}

def build_html(articles):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    groups = {}
    for art in articles:
        t = art.get("topic", "기타")
        groups.setdefault(t, []).append(art)

    sections = ""
    for topic, arts in groups.items():
        color = TOPIC_COLORS.get(topic, "#475569")
        cards = ""
        for art in arts:
            summary = art.get("summary", "")[:120]
            cards += f"""
            <div style="background:#fff;border-left:4px solid {color};border-radius:8px;
                        padding:16px;margin-bottom:12px;border:1px solid #e2e8f0;">
              <div style="font-size:11px;color:#94a3b8;margin-bottom:6px;">
                {art.get('source','')} · {art.get('date','')}
              </div>
              <a href="{art['url']}" style="color:#1e293b;font-size:15px;font-weight:600;
                 text-decoration:none;" target="_blank">{art['title']}</a>
              <p style="margin:8px 0 0;color:#64748b;font-size:13px;">{summary}...</p>
              <p style="margin:6px 0 0;color:#94a3b8;font-size:12px;font-style:italic;">
                💡 {art.get('relevance','')}</p>
            </div>"""

        sections += f"""
        <div style="margin-bottom:32px;">
          <h2 style="color:{color};font-size:18px;border-bottom:2px solid {color};
                     padding-bottom:8px;">{topic} ({len(arts)}건)</h2>
          {cards}
        </div>"""

    return f"""<!DOCTYPE html><html lang="ko"><body
      style="margin:0;padding:0;background:#f1f5f9;font-family:'Apple SD Gothic Neo',sans-serif;">
      <div style="max-width:680px;margin:0 auto;padding:24px 16px;">
        <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);border-radius:16px;
                    padding:32px;margin-bottom:24px;text-align:center;color:#fff;">
          <h1 style="margin:0 0 6px;font-size:26px;">🏗️ 건설·엔지니어링 뉴스</h1>
          <p style="margin:0;opacity:0.8;">{today} · 총 {len(articles)}건</p>
        </div>
        {sections}
        <div style="text-align:center;color:#94a3b8;font-size:12px;padding:20px;">
          자동 발송 · 출처: 엔지니어링데일리, 대한경제
        </div>
      </div>
    </body></html>"""

def send_email(articles):
    if not articles:
        return False
    today = datetime.now().strftime("%Y.%m.%d")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[건설·엔지니어링 브리핑] {today} — {len(articles)}건"
    msg["From"] = f"건설뉴스봇 <{EMAIL_ADDRESS}>"
    msg["To"] = ", ".join(RECIPIENT_EMAILS)
    msg.attach(MIMEText(build_html(articles), "html", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAILS, msg.as_string())
        logger.info(f"메일 발송 완료 → {RECIPIENT_EMAILS}")
        return True
    except Exception as e:
        logger.error(f"메일 발송 오류: {e}")
        return False