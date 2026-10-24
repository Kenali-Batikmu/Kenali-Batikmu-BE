# Panduan Lengkap Deploy Backend Kenali Batikmu dengan Supabase

Dokumen ini berisi panduan teknis langkah demi langkah untuk melakukan deploy **Kenali Batikmu Backend** dengan memanfaatkan ekosistem **Supabase** (Database PostgreSQL Terkelola dan Cloud Storage) yang dipadukan dengan Web Service Python/Flask (Render / Railway / VPS).

---

## 1. Memahami Arsitektur: Flask + Supabase

Supabase adalah platform **Backend-as-a-Service (BaaS)** yang menyediakan:
1. **Hosted PostgreSQL Database** dengan performa tinggi, backup otomatis, dan dashboard SQL.
2. **Supabase Cloud Storage (S3-Compatible)** untuk menampung file media (foto profil dan foto hasil praktik batik).
3. **API Gateway & Autentikasi**.

Supabase tidak menjalankan runtime bahasa pemrograman dinamis seperti server Python Flask atau TensorFlow Lite secara mandiri. Oleh karena itu, arsitektur standar industri yang digunakan adalah:

```
┌────────────────────────────────────────────────────────┐
│                   APLIKASI MOBILE                      │
│             (Flutter Kenali Batikmu)                   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ HTTPS REST API
┌────────────────────────────────────────────────────────┐
│             WEB SERVICE PYTHON / FLASK                 │
│         (Deploy di Render / Railway / VPS)             │
│  - Endpoint Auth, Profil, Kuis, Modul, Scan AI         │
│  - Menjalankan Model TFLite (batik_mobilenetv2.tflite) │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼ PostgreSQL Connection    ▼ S3 / Storage API
┌──────────────────────────┐  ┌──────────────────────────┐
│   SUPABASE POSTGRESQL    │  │     SUPABASE STORAGE     │
│   (Database Cloud v2)    │  │ (Bucket: avatar, praktik)│
└──────────────────────────┘  └──────────────────────────┘
```

---

## 2. Langkah 1: Membuat Proyek di Supabase

1. Kunjungi situs resmi [Supabase](https://supabase.com/) dan lakukan login (bisa menggunakan akun GitHub).
2. Di dashboard Supabase, klik tombol **New Project**.
3. Isi informasi proyek:
   * **Name**: `kenali-batikmu-be`
   * **Database Password**: Buat kata sandi yang kuat dan simpan di catatan aman.
   * **Region**: Pilih **Singapore (ap-southeast-1)** atau region pilihanmu.
   * **Pricing Plan**: Pilih **Free Plan**.
4. Pada bagian **Security**:
   * Centang: **Enable Data API**.
   * Centang: **Automatically expose new tables**.
   * **JANGAN DICENTANG (Kosongkan)**: **Enable automatic RLS** (agar tabel tidak terkunci otomatis oleh permission policy rumit).
5. Klik **Create new project** dan tunggu proses penyediaan server database selesai.

---

## 3. Langkah 2: Mengambil Connection String dan Menaruh di `.env`

Setelah proyek aktif di Supabase:
1. Masuk ke menu **Project Settings** (ikon gerigi di bilah kiri bawah).
2. Klik submenu **Database**, lalu scroll ke bagian **Connection string**.
3. Pilih tab **URI**. Format bawaannya:
   ```text
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

### Lokasi Menaruh String di File `.env` Lokal:
Buka file `.env` di proyek backend (`Kenali-Batikmu-BE/.env`), scroll ke **baris paling bawah**, dan tambahkan baris:

```env
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD_KAMU]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

> **Catatan Teknis Penting (IPv4 vs IPv6):**
> Koneksi langsung port 5432 (`db.[PROJECT-REF].supabase.co`) hanya mendukung IPv6. Di banyak jaringan Wi-Fi Indonesia yang masih IPv4 murni, gunakan format **Connection Pooling (port 6543)** seperti contoh di atas agar koneksi stabil dan anti-timeout.

---

## 4. Langkah 3: Skema Database PostgreSQL di Supabase

Skema PostgreSQL yang sudah disesuaikan dan dieksekusi di database Supabase:

```sql
-- 1. Tabel users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(30),
    password_hash TEXT NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    lockout_until TIMESTAMPTZ,
    profile_image_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Tabel batik_motifs
CREATE TABLE IF NOT EXISTS batik_motifs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    origin_region VARCHAR(100) NOT NULL,
    short_description TEXT NOT NULL,
    thumbnail_url TEXT,
    ml_class_index INTEGER NOT NULL UNIQUE CHECK (ml_class_index >= 0)
);

-- 3. Tabel modules
CREATE TABLE IF NOT EXISTS modules (
    id SERIAL PRIMARY KEY,
    motif_id INTEGER NOT NULL REFERENCES batik_motifs (id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    cover_image TEXT,
    video_url TEXT,
    passing_score INTEGER NOT NULL DEFAULT 70 CHECK (passing_score BETWEEN 0 AND 100),
    order_no INTEGER NOT NULL UNIQUE
);

-- 4. Tabel module_contents
CREATE TABLE IF NOT EXISTS module_contents (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    pillar VARCHAR(30) NOT NULL CHECK (pillar IN ('sejarah_filosofi', 'karakteristik', 'galeri')),
    title VARCHAR(150) NOT NULL,
    body TEXT NOT NULL,
    badge VARCHAR(50),
    order_no INTEGER NOT NULL,
    UNIQUE (module_id, pillar, order_no)
);

-- 5. Tabel module_gallery_images
CREATE TABLE IF NOT EXISTS module_gallery_images (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    image_url TEXT,
    caption TEXT,
    order_no INTEGER NOT NULL,
    UNIQUE (module_id, order_no)
);

-- 6. Tabel quiz_questions
CREATE TABLE IF NOT EXISTS quiz_questions (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option CHAR(1) NOT NULL CHECK (correct_option IN ('A', 'B', 'C', 'D')),
    explanation TEXT
);

-- 7. Tabel user_module_progress
CREATE TABLE IF NOT EXISTS user_module_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed')),
    progress_percent INTEGER NOT NULL DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
    history_done BOOLEAN NOT NULL DEFAULT FALSE,
    character_done BOOLEAN NOT NULL DEFAULT FALSE,
    gallery_done BOOLEAN NOT NULL DEFAULT FALSE,
    quiz_done BOOLEAN NOT NULL DEFAULT FALSE,
    practice_done BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, module_id)
);

-- 8. Tabel quiz_attempts
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules (id) ON DELETE CASCADE,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. Tabel quiz_attempt_answers
CREATE TABLE IF NOT EXISTS quiz_attempt_answers (
    id SERIAL PRIMARY KEY,
    attempt_id INTEGER NOT NULL REFERENCES quiz_attempts (id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES quiz_questions (id) ON DELETE CASCADE,
    selected_option CHAR(1) NOT NULL CHECK (selected_option IN ('A', 'B', 'C', 'D')),
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (attempt_id, question_id)
);

-- 10. Tabel scans
CREATE TABLE IF NOT EXISTS scans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    scan_type VARCHAR(20) NOT NULL CHECK (scan_type IN ('universal', 'kuismu')),
    module_id INTEGER REFERENCES modules (id) ON DELETE SET NULL,
    image_path TEXT,
    top_motif_id INTEGER REFERENCES batik_motifs (id) ON DELETE SET NULL,
    confidence REAL CHECK (confidence BETWEEN 0 AND 1),
    fit_score REAL CHECK (fit_score BETWEEN 0 AND 1),
    passed BOOLEAN,
    inference_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. Tabel scan_probabilities
CREATE TABLE IF NOT EXISTS scan_probabilities (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER NOT NULL REFERENCES scans (id) ON DELETE CASCADE,
    motif_id INTEGER NOT NULL REFERENCES batik_motifs (id) ON DELETE CASCADE,
    probability REAL NOT NULL CHECK (probability BETWEEN 0 AND 1),
    UNIQUE (scan_id, motif_id)
);

-- 12. Tabel password_resets
CREATE TABLE IF NOT EXISTS password_resets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    otp_hash TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    reset_token_hash TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indeks
CREATE INDEX IF NOT EXISTS idx_modules_motif ON modules (motif_id);
CREATE INDEX IF NOT EXISTS idx_contents_module ON module_contents (module_id, pillar, order_no);
CREATE INDEX IF NOT EXISTS idx_questions_module ON quiz_questions (module_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user_module ON quiz_attempts (user_id, module_id, attempted_at);
CREATE INDEX IF NOT EXISTS idx_scans_user ON scans (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_resets_user ON password_resets (user_id, created_at);
```

---

## 5. Langkah 4: Migrasi Data Seed Otomatis

Script otomatis [`migrate_to_supabase.py`](file:///c:/laragon/www/Project%20Kuliah/Kenali%20Batikmu/Kenali-Batikmu-BE/migrate_to_supabase.py) tersedia di root repositori backend untuk memindahkan data dari SQLite lokal ke Supabase PostgreSQL.

Jalankan perintah ini di terminal backend:
```bash
python migrate_to_supabase.py
```

Status data yang berhasil dimigrasikan:
* **batik_motifs**: 20 motif batik nusantara.
* **modules**: 20 modul pembelajaran lengkap.
* **module_contents**: 253 konten narasi 3 pilar sejarah, filosofi, dan karakteristik.
* **module_gallery_images**: 77 gambar dokumentasi galeri.
* **quiz_questions**: 500 butir bank soal pilihan ganda (25 per modul).
* **users**: 2 akun pengguna awal (Sekar Ayu Kinanti dan akun demo).

---

## 6. Langkah 5: Konfigurasi Supabase Storage untuk Gambar

1. Buka menu **Storage** (ikon bucket di bilah menu kiri dashboard Supabase).
2. Klik tombol **New bucket**.
3. Buat bucket pertama:
   * **Name**: `avatars`
   * Centang: **Public bucket** (agar foto profil bisa dibaca langsung).
   * Klik **Save**.
4. Buat bucket kedua:
   * **Name**: `practices`
   * Centang: **Public bucket**.
   * Klik **Save**.

---

## 7. Langkah 6: Deploy Web Service ke Render.com

Web service Flask yang menjalankan logika bisnis dan model Machine Learning TFLite (`batik_mobilenetv2.tflite`) di-host secara gratis di [Render.com](https://render.com/).

### 7.1 Commit dan Push ke GitHub
Di terminal proyek backend (`Kenali-Batikmu-BE`):
```bash
git add Procfile requirements.txt docs/ migrate_to_supabase.py
git commit -m "chore: setup Supabase deployment and migration"
git push origin julian
```

### 7.2 Buat Web Service Baru di Render
1. Login ke [Render.com](https://render.com/) menggunakan akun GitHub kamu.
2. Klik tombol **New +** di pojok kanan atas, lalu pilih **Web Service**.
3. Hubungkan repositori GitHub `Kenali-Batikmu-BE`.
4. Masukkan konfigurasi layanan:
   * **Name**: `kenali-batikmu-api`
   * **Region**: `Singapore` (paling dekat dengan Indonesia).
   * **Branch**: `julian` (atau branch tempat kodemu berada).
   * **Runtime**: `Python 3`.
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   * **Instance Type**: `Free`.

### 7.3 Masukkan Environment Variables di Render
Di halaman konfigurasi yang sama, scroll ke bagian **Environment Variables** dan tambahkan:

| Key | Value | Keterangan |
|---|---|---|
| `FLASK_ENV` | `production` | Mode produksi |
| `SECRET_KEY` | *(Salin nilai SECRET_KEY dari file .env kamu)* | Kunci enkripsi token |
| `DATABASE_URL` | *(Salin nilai DATABASE_URL dari file .env kamu)* | String PostgreSQL Supabase |

5. Klik tombol **Create Web Service**.
6. Render akan otomatis mengunduh dependencies, memuat model TFLite `batik_mobilenetv2.tflite`, dan mengaktifkan web service kamu.

Setelah proses build selesai (~2-3 menit), Render akan memberikan URL publik aktif, misalnya:
`https://kenali-batikmu-api.onrender.com`

---

## 8. Langkah 7: Pengujian & Integrasi ke Mobile

1. **Uji Health Check di Browser**:
   Buka URL: `https://kenali-batikmu-api.onrender.com/api/health`
   Respon yang diharapkan:
   ```json
   {
     "status": "healthy",
     "version": "2.0.0",
     "database": "connected",
     "ml_model": "ready",
     "ml_classes_count": 20
   }
   ```

2. **Hubungkan Aplikasi Mobile**:
   Di proyek `Kenali-Batikmu-Mobile`, arahkan `baseUrl` ke URL Render tersebut:
   ```dart
   class ApiConfig {
     static const String baseUrl = 'https://kenali-batikmu-api.onrender.com/api';
   }
   ```
