# Kenali Batikmu — Backend (FastAPI + Supabase)

Backend Python untuk aplikasi Flutter **Kenali Batikmu**. Konsepnya *offline-first*: aplikasi tetap berjalan penuh tanpa internet, dan backend hanya dipakai saat online.

| Bagian | Di mana | Keterangan |
|---|---|---|
| Login, daftar, lupa sandi | **Backend (online)** | Sandi diverifikasi di server, aplikasi menerima token |
| Mengambil progres membaca modul | **Backend (online)** | `GET /sync/pull` |
| Mengambil nilai kuis teori & praktikum | **Backend (online)** | `GET /sync/pull` |
| Mengirim antrean kerja offline | **Backend (online)** | `POST /sync/push` saat internet kembali |
| Membaca modul, kuis teori, kuis praktikum | **Aplikasi (offline)** | Dari `kenali_batikmu.db` + `assets/` di aplikasi |
| Pemindai motif batik (TFLite) | **Aplikasi (offline)** | `batik_mobilenetv2.tflite` di aplikasi |
| Fitur lainnya | **Aplikasi (offline)** | Tidak lewat backend |

Backend **sengaja tidak** menyimpan atau menyajikan isi modul, soal kuis, maupun model pemindai. Tabel `modules` di Supabase hanya data referensi (id, judul, KKM) agar progres yang masuk bisa divalidasi.

## Struktur

```
app/
  main.py            aplikasi FastAPI, /health, /health/db
  config.py          konfigurasi dari .env
  security.py        hash sandi (scrypt), JWT, OTP
  domain.py          aturan progres (murni, tanpa database)
  routers/           auth, me (profil), progress (baca), sync (pull/push)
  services/          akses data Supabase
db/
  setup_all.sql          skema + data referensi dalam satu file (paling mudah dijalankan)
  schema.sql             tabel + RLS + bucket storage (jalankan di Supabase)
  seed_reference_data.sql  20 motif + 20 modul, diekspor dari database bawaan aplikasi
scripts/
  export_reference_seed.py  membuat ulang seed dari kenali_batikmu.db
  smoke_test.py             uji ujung-ke-ujung ke server yang berjalan
tests/                      40 tes (logika, keamanan, alur sinkronisasi)
```

## Menjalankan

1. **Supabase** → SQL Editor → New query → tempel seluruh isi **`db/setup_all.sql`** → Run. (File ini = `db/schema.sql` + `db/seed_reference_data.sql`; boleh juga dijalankan terpisah, skema dulu.)
   - Bila project Supabase Anda sudah punya tabel dengan nama yang sama, cek dulu tipe kolomnya di Table Editor (khususnya `id` bertipe angka dan kolom waktu bertipe `timestamptz`). `schema.sql` memakai `create table if not exists`, jadi tabel lama tidak diubah selain penambahan kolom baru.
2. `cp .env.example .env`, isi `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (Project Settings → API), dan `JWT_SECRET`.
3. ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
4. Verifikasi: buka `http://127.0.0.1:8000/docs`, lalu jalankan `python scripts/smoke_test.py`.
   Tanpa SMTP, set `EXPOSE_OTP_IN_RESPONSE=true` selama pengembangan agar OTP muncul di respons.

Docker: `docker build -t kenali-backend . && docker run --env-file .env -p 8000:8000 kenali-backend`.

## Endpoint (`/api/v1`)

| Method & path | Auth | Fungsi |
|---|---|---|
| `POST /auth/register` | – | Daftar, mengembalikan `user` + token |
| `POST /auth/login` | – | Login, mengembalikan `user` + `access_token` + `refresh_token` |
| `POST /auth/refresh` | – | Access token baru dari refresh token |
| `POST /auth/logout` | – | Cabut refresh token |
| `POST /auth/forgot-password` → `/verify-otp` → `/reset-password` | – | Lupa sandi 3 langkah (OTP 4 digit lewat email) |
| `GET /sync/pull?since=` | ✔ | Progres modul + riwayat kuis teori + hasil praktikum dalam satu panggilan |
| `POST /sync/push` | ✔ | Kirim antrean offline (progres, kuis teori, praktikum) |
| `GET /progress`, `GET /quiz/attempts`, `GET /practice` | ✔ | Versi terpisah dari pull |
| `PUT /practice/{module_id}/image` | ✔ | Unggah foto praktikum → `image_url` |
| `GET/PATCH /me`, `POST /me/password`, `PUT/DELETE /me/avatar` | ✔ | Profil (nama, HP, email, sandi, foto) |

Nama field di respons sama dengan kolom tabel Supabase yang selama ini dibaca aplikasi (`module_id`, `quiz_score`, `practice_score`, `progress_percent`, `history_done`, …), jadi parsing di Dart hampir tidak berubah.

## Alur sinkronisasi di aplikasi

**Setelah login (online):** simpan token, panggil `GET /sync/pull`, tulis hasilnya ke SQLite lokal, simpan `server_time`. Tarikan berikutnya cukup `?since=<server_time>` (UTC).

**Saat bekerja offline:** semuanya tetap ditulis ke SQLite lokal seperti sekarang, dengan `is_synced = 0`.

**Saat internet kembali:** kumpulkan baris `is_synced = 0` lalu `POST /sync/push`. Setiap item dibalas dengan `status`:

| status | Artinya | Di aplikasi |
|---|---|---|
| `accepted` | Tersimpan | tandai `is_synced = 1` |
| `duplicate` | Sudah ada / server punya yang lebih baru | tandai `is_synced = 1` |
| `rejected` | Item cacat (mis. skor di luar 0–100, `module_id` tidak dikenal); alasannya ada di `detail` | tandai `is_synced = 1`, jangan kirim ulang |
| `error` | Gangguan sementara | biarkan `is_synced = 0`, kirim lagi nanti |

Item divalidasi satu per satu: item cacat hanya menolak dirinya sendiri, bukan seluruh batch. Permintaan tetap berstatus HTTP 200.

Respons juga memuat `progress_snapshot` (progres hasil gabungan di server) untuk menimpa data lokal.

Aturan di server, sama dengan aplikasi: progres = 5 komponen × 20% (sejarah, karakteristik, galeri, kuis teori, praktikum); kuis dan praktikum baru dihitung bila skor ≥ KKM modul. Penggabungan bersifat monoton (boolean di-OR, skor diambil tertinggi), sehingga aman dikirim ulang dan aman dari banyak perangkat. Hasil praktikum disimpan satu per modul (yang terbaru menang). Lulus/tidaknya dihitung ulang di server memakai KKM dari tabel `modules`.

Untuk kuis teori, kirim `client_ref` unik per percobaan (mis. `"<id-perangkat>-<id lokal>"`) agar pengiriman ulang tidak menggandakan riwayat.

## Pemetaan dari `supabase_service.dart`

Penerapannya sudah dikerjakan di paket `kenali-batikmu-flutter-integration.zip`; tabel ini dipertahankan sebagai referensi.

| Sekarang | Ganti dengan |
|---|---|
| `registerUser` | `POST /auth/register` |
| `getUserByEmail` + `PasswordHasher.verify` saat login | `POST /auth/login` (server yang memverifikasi) |
| `updateUserProfile`, `uploadAvatar`, `deleteAvatar` | `PATCH /me`, `PUT /me/avatar`, `DELETE /me/avatar` |
| `uploadPracticeImage` | `PUT /practice/{id}/image` |
| `saveQuizAttempt`, `savePracticeScan`, `syncUserModuleProgress` (`processOfflineQueue`) | satu `POST /sync/push` |
| `fetchUserModuleProgress`, `fetchQuizAttempts`, `fetchPracticeScans` | `GET /sync/pull` |
| `fetchMotifs`, `fetchModules` | tidak dipakai lagi: master data hanya dari database bawaan aplikasi |
| `fetchQuizQuestions` | tidak dipakai; soal dibaca dari SQLite lokal |

Perubahan perilaku yang perlu diikuti aplikasi:
- Server tidak pernah mengirim `password_hash`. Untuk membuka aplikasi saat offline, andalkan sesi tersimpan, bukan verifikasi sandi lokal.
- Login dan lupa sandi memakai pesan generik (`Email atau kata sandi salah`; lupa sandi selalu menjawab sama) agar tidak membocorkan email terdaftar. Teks "Akun belum terdaftar" tidak lagi bisa ditampilkan.
- OTP dibuat dan dikirim server lewat email. Kode hanya tampil di aplikasi bila server dijalankan dengan `EXPOSE_OTP_IN_RESPONSE=true` (khusus pengembangan).
- Scan universal tidak dikirim ke backend (tetap lokal). Hanya hasil praktikum (`scan_type = 'kuismu'`) yang disinkronkan.
- Akun lama yang hash-nya SHA-256 tetap bisa login; hash otomatis di-upgrade ke scrypt saat login berhasil.

## Keamanan & batasan yang perlu Anda ketahui

- **RLS:** `schema.sql` mengunci semua tabel pengguna dari kunci `anon`. Sebelumnya aplikasi membaca/menulis tabel `users` (termasuk hash sandi) langsung dengan anon key; setelah migrasi hal itu tidak lagi diizinkan. Hapus juga policy lama yang mengizinkan anon menulis ke bucket `avatars`/`practices` bila ada.
- **Kunci `service_role`** hanya boleh ada di server. Jangan masukkan ke Flutter.
- **Skor datang dari perangkat.** Karena kuis dikerjakan offline, server tidak bisa membuktikan skor itu asli; ia hanya memvalidasi rentang, modul, dan KKM. Ini konsekuensi desain offline, bukan bug. Bila nilai harus tepercaya (mis. untuk penilaian resmi), kuis harus dinilai di server.
- **Pembatasan percobaan** hanya per akun (5 gagal → kunci 15 menit; OTP maksimal 5 salah). Tidak ada pembatasan per IP. Pasang rate limit di reverse proxy (Nginx/Cloudflare). Pembatasan per akun juga membuat akun bisa sengaja dikunci orang lain; itu kompromi yang umum.
- **Refresh token tidak dirotasi** (agar tidak memutus sesi bila respons hilang di jaringan buruk), tetapi diperpanjang tiap dipakai, bisa dicabut lewat logout, dan semua dicabut saat sandi diganti/direset.
- Bucket foto bersifat publik (sama seperti aplikasi sekarang). Ubah menjadi privat bila foto praktikum dianggap sensitif.
- `/docs` aktif secara default; tutup lewat reverse proxy di produksi bila tidak diperlukan.

## Bila `/health/db` atau smoke test gagal (503)

Respons 503 kini menyebut `reason` dan `detail`. Penyebab yang paling sering:

| `reason` | Artinya | Perbaikan |
|---|---|---|
| `kunci_ditolak` | Kunci salah, atau pustaka `supabase-py` lama menolak kunci `sb_secret_` | Pakai **Secret key** (bukan Publishable key), lalu `pip install -U -r requirements.txt` dan **restart** server |
| `tabel_belum_ada` | Skema belum dibuat | Jalankan `db/schema.sql` lalu `db/seed_reference_data.sql` di Supabase SQL Editor |
| `seed_kosong` | Tabel ada tapi tidak ada modul | Jalankan `db/seed_reference_data.sql` |
| `url_salah` | `SUPABASE_URL` keliru | Bentuk: `https://<kode-project>.supabase.co`, tanpa `/rest/v1` |
| `jaringan` | Server tidak bisa menjangkau Supabase (DNS/ISP/VPN/firewall) | `nslookup <kode>.supabase.co` lalu bandingkan dengan `nslookup <kode>.supabase.co 1.1.1.1`; coba DNS 1.1.1.1 atau VPN |

Pengujian di luar aplikasi (PowerShell memakai `curl.exe`, bukan `curl`):

```
curl.exe -i "https://<kode>.supabase.co/rest/v1/modules?select=id&limit=1" -H "apikey: <SECRET KEY>"
```

`200` + `[{"id":1}]` berarti Supabase, kunci, dan tabel beres. `401`/`Invalid API key`: kunci. `PGRST205`: tabel belum dibuat.
Timeout atau gagal resolve: jaringan. Server hanya membaca `.env` saat start, jadi **restart** `uvicorn` setelah mengubahnya
(`--reload` memantau berkas `.py`, bukan `.env`).

## Status pengujian

`python -m unittest discover -s tests` → 49 tes lulus: aturan progres dan penggabungan, hash sandi (termasuk format scrypt dan SHA-256 lama dari aplikasi), JWT (kedaluwarsa, tanda tangan salah, `alg=none`), OTP, validasi gambar, dan alur sinkronisasi (dedup, hasil praktikum lebih lama, item gagal, penolakan per item, kirim ulang) dan klasifikasi galat koneksi Supabase terhadap database tiruan di memori. Tanpa pydantic terpasang, tes memakai stub yang hanya meniru sebagian aturan skema; jalankan tes di lingkungan dengan `pip install -r requirements.txt` agar aturan validasi aslinya ikut teruji.

**Belum teruji:** lapisan HTTP FastAPI, panggilan `supabase-py` ke Supabase sungguhan, dan `db/schema.sql` di PostgreSQL. Kode ini ditulis tanpa akses jaringan. `scripts/smoke_test.py` disediakan untuk memeriksa semuanya sekaligus di mesin Anda; jalankan itu lebih dulu dan kabari bila ada yang gagal.
