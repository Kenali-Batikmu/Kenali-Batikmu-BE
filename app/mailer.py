from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from .config import Settings

log = logging.getLogger("kenali.mailer")


def send_otp_email(settings: Settings, to_email: str, to_name: str, otp: str) -> None:
    """Kirim OTP lewat SMTP. Dipanggil sebagai background task; kegagalan hanya dicatat di log."""
    if not settings.smtp_configured:
        log.warning("SMTP belum dikonfigurasi, email OTP untuk akun tidak dikirim.")
        return
    try:
        sender = settings.smtp_from or settings.smtp_user
        name = " ".join((to_name or "").split()) or "Pengguna"
        msg = EmailMessage()
        msg["Subject"] = f"Kode verifikasi {settings.app_name}"
        msg["From"] = sender
        msg["To"] = to_email
        msg.set_content(
            f"Halo {name},\n\n"
            f"Kode verifikasi untuk mengatur ulang kata sandi {settings.app_name} Anda adalah:\n\n"
            f"    {otp}\n\n"
            f"Kode berlaku {settings.otp_ttl_minutes} menit. Jika Anda tidak memintanya, abaikan email ini.\n"
        )
        context = ssl.create_default_context()
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15, context=context) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.starttls(context=context)
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
    except Exception:  # noqa: BLE001 - jangan sampai background task melempar error
        log.exception("Gagal mengirim email OTP")
