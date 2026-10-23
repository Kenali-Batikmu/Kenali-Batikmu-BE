"""Pengiriman email OTP lewat SMTP (pustaka standar, tanpa dependensi tambahan)."""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app

log = logging.getLogger(__name__)


class MailError(Exception):
    pass


def smtp_configured() -> bool:
    cfg = current_app.config
    return bool(cfg["SMTP_HOST"] and cfg["SMTP_FROM"])


def send_otp_email(to_email: str, to_name: str, otp: str) -> None:
    cfg = current_app.config
    minutes = cfg["OTP_TTL_MINUTES"]
    msg = EmailMessage()
    msg["Subject"] = "Kode verifikasi Kenali Batikmu"
    msg["From"] = cfg["SMTP_FROM"]
    msg["To"] = to_email
    msg.set_content(
        f"Halo {to_name},\n\n"
        f"Kode verifikasi untuk mengatur ulang kata sandi Kenali Batikmu Anda adalah:\n\n"
        f"    {otp}\n\n"
        f"Kode berlaku {minutes} menit. Jika Anda tidak meminta ini, abaikan email ini.\n"
    )
    try:
        if cfg["SMTP_SECURITY"] == "ssl":
            server = smtplib.SMTP_SSL(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15)
        with server:
            if cfg["SMTP_SECURITY"] == "starttls":
                server.starttls(context=ssl.create_default_context())
            if cfg["SMTP_USER"]:
                server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        log.error("Gagal mengirim email OTP: %s", exc)
        raise MailError(str(exc)) from exc
