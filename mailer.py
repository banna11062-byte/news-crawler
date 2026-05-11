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


def build_html(articles):
    today = datetime.now().strftime("%Y년 %m월 %d일")

    cards = ""
    for i, art in enumerate(articles):
        image = art.get("image", "")
        image_html = ""
        if image and i == 0:
            image_html = f"""
            <div style="width:100%;height:200px;overflow:hidden;background:#F1EFE8;">
              <img src="{image}" style="width:100%;height:100%;object-fit:cover;" alt="">
            </div>"""

        title = art.get("title", "")
        summary = clean_summary(art.get("summary", ""), title)
        if len(summary) > 150:
            summary = summary[:150] + "..."

        cards += f"""
        <div style="background:#fff;border:0.5px solid #E5E5E0;border-radius:12px;
                    margin-bottom:14px;overflow:hidden;">
          {image_html}
          <div style="padding:16px 18px;">
            <div style="font-size:11px;color:#EA6A1F;font
