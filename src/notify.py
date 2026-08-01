from __future__ import annotations
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(subject: str, html_body: str) -> None:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")
    mail_from = os.getenv("MAIL_FROM") or user
    mail_to = os.getenv("MAIL_TO")

    if not all([host, port, user, pwd, mail_from, mail_to]):
        raise RuntimeError("Configurazione email incompleta: controlla .env")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to

    msg.attach(MIMEText(html_body, "html"))

    recipients = [address.strip() for address in mail_to.split(",") if address.strip()]
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(user, pwd)
        server.sendmail(mail_from, recipients, msg.as_string())
