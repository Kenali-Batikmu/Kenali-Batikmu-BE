"""Klasifikasi galat koneksi Supabase menjadi pesan yang bisa ditindaklanjuti.

Dipakai /health/db. Hanya mengembalikan alasan + saran (bukan pesan galat mentah, karena
endpoint ini publik); galat lengkapnya tetap dicatat di log server.
"""

from __future__ import annotations

_NETWORK_TYPES = ("connecterror", "connecttimeout", "readtimeout", "timeout", "connectionerror", "gaierror", "sslerror")
_NETWORK_WORDS = (
    "getaddrinfo",
    "name or service not known",
    "nodename nor servname",
    "temporary failure in name resolution",
    "timed out",
    "connection refused",
    "connection reset",
    "network is unreachable",
    "certificate verify failed",
)


def classify_supabase_error(exc: BaseException) -> tuple[str, str]:
    """Kembalikan (kode_alasan, saran) untuk galat saat menjangkau Supabase."""
    kind = type(exc).__name__.lower()
    text = str(exc).lower()

    if "invalid api key" in text or "invalid jwt" in text or "bad_jwt" in text:
        return (
            "kunci_ditolak",
            "Kunci API ditolak. Pastikan SUPABASE_SERVICE_ROLE_KEY berisi Secret key (sb_secret_...) "
            "dan perbarui pustaka: pip install -U -r requirements.txt (supabase-py lama menolak kunci sb_secret_).",
        )
    if "invalid url" in text or "supabase_url" in text or "unsupported protocol" in text or "unknown url type" in text:
        return (
            "url_salah",
            "SUPABASE_URL tidak valid. Bentuk yang benar: https://<kode-project>.supabase.co "
            "(tanpa /rest/v1 dan tanpa spasi).",
        )
    if "pgrst205" in text or "42p01" in text or "could not find the table" in text or "does not exist" in text:
        return (
            "tabel_belum_ada",
            "Tabel belum dibuat di Supabase. Jalankan db/schema.sql lalu db/seed_reference_data.sql "
            "di Supabase Dashboard -> SQL Editor.",
        )
    if "permission denied" in text or "42501" in text:
        return (
            "izin_ditolak",
            "Izin ditolak di database. Pastikan yang dipakai Secret key (bukan Publishable key) "
            "dan db/schema.sql dijalankan utuh.",
        )
    if kind in _NETWORK_TYPES or any(w in text for w in _NETWORK_WORDS):
        return (
            "jaringan",
            "Server tidak bisa terhubung ke SUPABASE_URL. Periksa internet/DNS/VPN dan ejaan URL. "
            "Uji dengan: nslookup <kode-project>.supabase.co lalu bandingkan dengan DNS 1.1.1.1.",
        )
    if "401" in text or "unauthorized" in text:
        return ("kunci_ditolak", "Permintaan ditolak (401). Periksa kembali SUPABASE_SERVICE_ROLE_KEY.")
    return ("tidak_dikenal", "Penyebab tidak dikenali. Lihat log server (cari 'Cek Supabase gagal') untuk galat lengkapnya.")
