import os
import smtplib
import time
from typing import List, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(key, default)


def _parse_recipients(val: Optional[str]) -> List[str]:
    if not val:
        return []
    return [x.strip() for x in val.split(",") if x.strip()]


def send_html(subject: str, html: str, to_addrs: Optional[List[str]] = None) -> bool:
    host = _get_env("SMTP_HOST")
    port = int(_get_env("SMTP_PORT", "587"))
    user = _get_env("SMTP_USER")
    password = _get_env("SMTP_PASSWORD")
    mail_from = _get_env("MAIL_FROM") or user
    timeout = int(_get_env("SMTP_TIMEOUT", "20"))
    retries = int(_get_env("SMTP_RETRIES", "2"))

    if not host or not mail_from or not to_addrs:
        print("SMTP config incomplete (SMTP_HOST, MAIL_FROM, MAIL_TO)")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = ", ".join(to_addrs)
    part = MIMEText(html, "html")
    msg.attach(part)

    attempt = 0
    while attempt <= retries:
        try:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.starttls()
                if user and password:
                    smtp.login(user, password)
                smtp.sendmail(mail_from, to_addrs, msg.as_string())
            return True
        except Exception as e:
            attempt += 1
            if attempt > retries:
                print(f"SMTP send failed: {e}")
                return False
            time.sleep(2 ** attempt)


def send_preview_file(path: str) -> bool:
    if not os.path.exists(path):
        print(f"preview file not found: {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    to_env = _get_env("MAIL_TO")
    recipients = _parse_recipients(to_env)
    subject = _get_env("MAIL_SUBJECT", "Daily Podcast Digest")
    return send_html(subject, html, recipients)


if __name__ == "__main__":
    preview = os.path.join(os.path.dirname(__file__), "..", "preview.html")
    preview = os.path.abspath(preview)
    dry = os.environ.get("DRY_RUN", "0") == "1"
    if dry:
        print("DRY_RUN=1 set; skipping send")
    else:
        ok = send_preview_file(preview)
        print("sent" if ok else "failed")
