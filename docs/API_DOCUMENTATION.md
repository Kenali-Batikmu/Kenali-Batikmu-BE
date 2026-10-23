# Spesifikasi API Kenali Batikmu (RESTful API Specification v2.0)

Dokumen ini merupakan referensi resmi antarmuka pemrograman aplikasi (API) untuk **Kenali Batikmu Backend**. Seluruh endpoint dirancang mengikuti standar arsitektur RESTful modern, enkripsi HTTPS, format payload JSON, serta penanganan berkas multipart/form-data dengan efisiensi penyimpanan (Smart Storage Retention).

---

## 1. Ikhtisar Arsitektur & Standar

### 1.1 Lingkungan Server (Environments)
* **Development (Lokal)**: `http://localhost:5000/api`
* **Staging**: `https://staging-api.kenalibatikmu.id/api`
* **Production**: `https://api.kenalibatikmu.id/api`

### 1.2 Skema Autentikasi
API menggunakan autentikasi berbasis token **Bearer Token** (HMAC/JWT):
```http
Authorization: Bearer <token_akses_anda>
```
* Token diterbitkan saat registrasi (`POST /api/auth/register`) atau login berhasil (`POST /api/auth/login`).
* Masa berlaku token default: 30 hari (jika remember me aktif) atau 24 jam (sesi standar).
* Endpoint publik (tanpa token): `/api/health`, registrasi, login, lupa kata sandi, verifikasi OTP, reset kata sandi, dan katalog motif publik.

### 1.3 Format Permintaan & Respons
* **Content-Type Permintaan JSON**: `application/json; charset=utf-8`
* **Content-Type Unggahan Berkas**: `multipart/form-data`
* **Format Waktu**: ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ` atau `YYYY-MM-DDTHH:MM:SS.mmmmmm+00:00`)

### 1.4 Standar Penanganan Galat (Error Handling - RFC 7807)
Setiap respon galat HTTP 4xx dan 5xx dikembalikan dalam format objek JSON terpadu:
```json
{
  "code": "validation_error",
  "message": "Format alamat email tidak valid",
  "field": "email"
}
```

#### Tabel Kode Status HTTP Umum:
| Kode HTTP | Status Singkat | Deskripsi |
|---|---|---|
| `200 OK` | Berhasil | Permintaan berhasil diproses dan mengembalikan data. |
| `201 Created` | Berhasil Dibuat | Entitas baru berhasil dibuat (registrasi, scan, pengerjaan kuis). |
| `400 Bad Request` | Permintaan Rusak | Sintaks body JSON tidak valid atau rusak. |
| `401 Unauthorized` | Tidak Terautentikasi | Token tidak disertakan, kedaluwarsa, atau kredensial salah. |
| `404 Not Found` | Tidak Ditemukan | ID sumber daya (modul, motif, scan, avatar) tidak ada di database. |
| `409 Conflict` | Konflik Data | Email sudah terdaftar sebelumnya oleh akun lain. |
| `422 Unprocessable` | Kesalahan Validasi | Data masukan tidak memenuhi aturan bisnis aplikasi. |
| `423 Locked` | Akun Terkunci | Akun dikunci sementara akibat 5x percobaan login gagal berturut-turut. |
| `429 Too Many Requests` | Dibatasi (Rate Limit) | Permintaan OTP terlalu sering atau melebihi batas percobaan. |
| `502 Bad Gateway` | Gateway Bermasalah | Server gagal mengirimkan email via SMTP eksternal. |
| `503 Service Unavailable` | Layanan Mati | Konfigurasi SMTP belum tersedia di server produksi. |

---

## 2. Katalog Endpoint Terperinci

---

### Modul 1: Autentikasi & Akun (`/api/auth`)

#### 1.1 Registrasi Pengguna Baru
* **Metode & Rute**: `POST /api/auth/register`
* **Autentikasi**: Publik (Tidak Memerlukan Token)
* **Deskripsi**: Mendaftarkan akun pembelajar baru dan langsung menghasilkan token sesi aktif.
* **Request Body**:
  ```json
  {
    "name": "Budi Santoso",
    "email": "budi@example.com",
    "password": "Rahasia123!"
  }
  ```
  * Aturan validasi:
    * `name` (string, wajib, 1 - 100 karakter).
    * `email` (string, wajib, format RFC 5322, maks 254 karakter, case-insensitive unik).
    * `password` (string, wajib, minimal 6 karakter, maksimal 128 karakter).
* **Respons Sukses (`201 Created`)**:
  ```json
  {
    "user": {
      "id": 1,
      "name": "Budi Santoso",
      "email": "budi@example.com",
      "phone": null,
      "profile_image_path": null,
      "created_at": "2026-10-23T10:00:00Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 2592000
  }
  ```
* **Contoh Respons Galat**:
  * `409 Conflict`: `{"code": "email_taken", "message": "Email sudah terdaftar.", "field": "email"}`
  * `422 Unprocessable`: `{"code": "validation_error", "message": "Kata sandi minimal 6 karakter", "field": "password"}`

---

#### 1.2 Masuk (Login Akun)
* **Metode & Rute**: `POST /api/auth/login`
* **Autentikasi**: Publik
* **Deskripsi**: Masuk ke dalam akun menggunakan email dan kata sandi terdaftar. Dilengkapi proteksi Brute-Force Lockout (kunci akun 15 menit setelah 5x gagal berturut-turut).
* **Request Body**:
  ```json
  {
    "email": "budi@example.com",
    "password": "Rahasia123!",
    "remember_me": true
  }
  ```
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "user": {
      "id": 1,
      "name": "Budi Santoso",
      "email": "budi@example.com",
      "phone": null,
      "profile_image_path": null,
      "created_at": "2026-10-23T10:00:00Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 2592000
  }
  ```
* **Contoh Respons Galat**:
  * `401 Unauthorized`: `{"code": "invalid_credentials", "message": "Email atau kata sandi salah"}`
  * `423 Locked`: `{"code": "account_locked", "message": "Terlalu banyak percobaan gagal. Coba lagi nanti.", "retry_after_seconds": 900}`

---

#### 1.3 Ambil Data Sesi Pengguna Aktif
* **Metode & Rute**: `GET /api/auth/me`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Deskripsi**: Mengambil identitas dasar pengguna yang saat ini sedang login.
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "user": {
      "id": 1,
      "name": "Budi Santoso",
      "email": "budi@example.com",
      "phone": "08123456789",
      "profile_image_path": "avatars/avatar_1_1729678800.jpg",
      "created_at": "2026-10-23T10:00:00Z"
    }
  }
  ```

---

#### 1.4 Lupa Kata Sandi (Permintaan OTP)
* **Metode & Rute**: `POST /api/auth/forgot-password`
* **Autentikasi**: Publik
* **Deskripsi**: Menghasilkan 4-digit kode OTP pemulihan sandi dan mengirimkannya ke email pengguna. Dilengkapi cooldown 60 detik antar permintaan baru.
* **Request Body**:
  ```json
  {
    "email": "budi@example.com"
  }
  ```
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "delivery": "email",
    "recipient_name": "Budi Santoso",
    "expires_in": 600
  }
  ```
  *(Catatan mode demo lokal tanpa SMTP: respon menyertakan field `"delivery": "demo"` dan `"demo_otp": "1234"`).*
* **Respons Galat**:
  * `404 Not Found`: `{"code": "email_not_found", "message": "Email belum terdaftar di Kenali Batikmu", "field": "email"}`
  * `429 Too Many Requests`: `{"code": "otp_throttled", "message": "Tunggu sebentar sebelum meminta kode baru.", "retry_after_seconds": 45}`

---

#### 1.5 Verifikasi Kode OTP
* **Metode & Rute**: `POST /api/auth/verify-otp`
* **Autentikasi**: Publik
* **Deskripsi**: Memverifikasi kesesuaian kode 4-digit OTP. Jika valid, menghasilkan single-use reset token.
* **Request Body**:
  ```json
  {
    "email": "budi@example.com",
    "otp": "5821"
  }
  ```
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "reset_token": "7w9Zk1LmNpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUvW",
    "expires_in": 900
  }
  ```
* **Respons Galat**:
  * `422 Unprocessable`: `{"code": "invalid_otp", "message": "Kode verifikasi salah. Periksa kembali kode Anda.", "attempts_left": 2}`
  * `422 Unprocessable`: `{"code": "otp_expired", "message": "Kode OTP telah kedaluwarsa. Silakan kirim ulang."}`

---

#### 1.6 Setel Ulang Kata Sandi (Reset Password)
* **Metode & Rute**: `POST /api/auth/reset-password`
* **Autentikasi**: Publik
* **Deskripsi**: Menetapkan kata sandi baru menggunakan `reset_token` yang telah diverifikasi pada tahap sebelumnya.
* **Request Body**:
  ```json
  {
    "email": "budi@example.com",
    "reset_token": "7w9Zk1LmNpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUvW",
    "new_password": "SandiBaru2026!"
  }
  ```
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "message": "Kata sandi berhasil diperbarui. Silakan masuk."
  }
  ```

---

### Modul 2: Profil Pengguna & Foto Avatar (`/api/profile`)

#### 2.1 Ambil Detail Profil & Statistik Belajar
* **Metode & Rute**: `GET /api/profile`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Deskripsi**: Mengambil profil lengkap pengguna beserta rekapitulasi progres modul dan riwayat scan.
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "user": {
      "id": 1,
      "name": "Budi Santoso",
      "email": "budi@example.com",
      "phone": "08123456789",
      "profile_image_path": "avatars/avatar_1_1729678800.jpg",
      "created_at": "2026-10-23T10:00:00Z"
    },
    "stats": {
      "completed_modules": 3,
      "total_modules": 20,
      "overall_progress_percent": 15,
      "scanned_count": 8
    },
    "completed_modules": [
      {
        "id": 4,
        "title": "Batik Parang Kusumo",
        "motif_id": 4,
        "completed_at": "2026-10-23T11:30:00Z"
      }
    ]
  }
  ```

---

#### 2.2 Perbarui Biodata Profil Pengguna
* **Metode & Rute**: `PATCH /api/profile`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Deskripsi**: Memperbarui nama lengkap, email, nomor HP, atau kata sandi baru. Hanya field yang dikirimkan yang akan diubah (partial update).
* **Request Body**:
  ```json
  {
    "name": "Budi Santoso S.Sn",
    "phone": "081298765432"
  }
  ```
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "user": {
      "id": 1,
      "name": "Budi Santoso S.Sn",
      "email": "budi@example.com",
      "phone": "081298765432",
      "profile_image_path": "avatars/avatar_1_1729678800.jpg",
      "created_at": "2026-10-23T10:00:00Z"
    }
  }
  ```

---

#### 2.3 Unggah Foto Profil (Avatar)
* **Metode & Rute**: `POST /api/profile/avatar`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Content-Type**: `multipart/form-data`
* **Deskripsi**: Mengunggah foto profil pengguna.
  * **Kebijakan Smart Retention**: Foto profil lama milik pengguna otomatis dihapus dari disk server sebelum foto baru disimpan, sehingga ukuran disk server tetap optimal (maksimal 1 berkas per pengguna).
* **Form-Data**:
  * `avatar`: Berkas gambar (format JPG, PNG, atau WEBP, maksimal 5 MB).
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "user": {
      "id": 1,
      "name": "Budi Santoso S.Sn",
      "email": "budi@example.com",
      "phone": "081298765432",
      "profile_image_path": "avatars/avatar_1_1729678950.jpg",
      "created_at": "2026-10-23T10:00:00Z"
    }
  }
  ```

---

#### 2.4 Unduh / Tampilkan Foto Profil
* **Metode & Rute**: `GET /api/profile/avatar`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Deskripsi**: Mengembalikan berkas biner foto profil aktif pengguna.
* **Respons Sukses (`200 OK`)**: Biner file `image/jpeg` atau `image/png`.

---

#### 2.5 Hapus Foto Profil
* **Metode & Rute**: `DELETE /api/profile/avatar`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Deskripsi**: Menghapus foto profil dari server dan mengosongkan path avatar pada profil akun.
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "user": {
      "id": 1,
      "name": "Budi Santoso S.Sn",
      "email": "budi@example.com",
      "phone": "081298765432",
      "profile_image_path": null,
      "created_at": "2026-10-23T10:00:00Z"
    }
  }
  ```

---

### Modul 3: Katalog Motif Batik (`/api/motifs`)

#### 3.1 Daftar Seluruh Motif Batik (20 Motif)
* **Metode & Rute**: `GET /api/motifs`
* **Autentikasi**: Publik (Opsional Token)
* **Deskripsi**: Mengembalikan katalog 20 motif batik nusantara terverifikasi lengkap dengan daerah asal dan indeks kelas Machine Learning (MobileNetV2).
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "total": 20,
    "motifs": [
      {
        "id": 4,
        "name": "Parang Kusumo",
        "slug": "parang-kusumo",
        "origin_region": "Surakarta dan Yogyakarta",
        "short_description": "Batik larangan keraton bermakna ksatria dengan keharuman budi pekerti bunga kembang melati.",
        "ml_class_index": 3,
        "sample_image_url": "/static/motifs/parang_kusumo.jpg"
      }
    ]
  }
  ```

---

#### 3.2 Detail Motif Batik Spesifik
* **Metode & Rute**: `GET /api/motifs/<motif_id>`
* **Autentikasi**: Publik
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "motif": {
      "id": 4,
      "name": "Parang Kusumo",
      "slug": "parang-kusumo",
      "origin_region": "Surakarta dan Yogyakarta",
      "short_description": "Batik larangan keraton bermakna ksatria dengan keharuman budi pekerti bunga kembang melati.",
      "ml_class_index": 3,
      "sample_image_url": "/static/motifs/parang_kusumo.jpg"
    }
  }
  ```

---

### Modul 4: Modul Belajar, Pilar Materi, & Kuis (`/api/modules`)

#### 4.1 Daftar Seluruh Modul Pembelajaran
* **Metode & Rute**: `GET /api/modules`
* **Autentikasi**: Publik (Jika menggunakan token, menyertakan status progres belajar pengguna).
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "total": 20,
    "modules": [
      {
        "id": 4,
        "motif_id": 4,
        "motif_name": "Parang Kusumo",
        "title": "Batik Parang Kusumo",
        "order_no": 4,
        "video_url": "https://www.youtube.com/watch?v=parangkusumo",
        "practice_task": "Temukan kain batik motif Parang Kusumo, sejajarkan garis diagonal lereng 45 derajat...",
        "passing_score": 70,
        "progress": {
          "pillar_sejarah_filosofi": true,
          "pillar_karakteristik": true,
          "pillar_galeri": true,
          "quiz_passed": true,
          "practice_done": false,
          "progress_percent": 75
        }
      }
    ]
  }
  ```

---

#### 4.2 Detail Modul Lengkap (3 Pilar Materi Terstruktur)
* **Metode & Rute**: `GET /api/modules/<module_id>`
* **Autentikasi**: Publik (Opsional Token)
* **Deskripsi**: Mengambil seluruh detail materi modul, termasuk video edukasi, instruksi praktikum, serta 3 pilar konten mendalam (`sejarah_filosofi`, `karakteristik`, dan `galeri`).
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "module": {
      "id": 4,
      "motif_id": 4,
      "motif_name": "Parang Kusumo",
      "motif_origin": "Surakarta dan Yogyakarta",
      "title": "Batik Parang Kusumo",
      "order_no": 4,
      "video_url": "https://www.youtube.com/watch?v=parangkusumo",
      "practice_task": "Temukan kain batik motif Parang Kusumo, sejajarkan garis diagonal lereng 45 derajat...",
      "passing_score": 70,
      "pillars": {
        "sejarah_filosofi": "Materi narasi mendalam tentang sejarah Panembahan Senopati di Pantai Parangkusumo...",
        "karakteristik": "Ciri khas geometris miring lereng 45 derajat, ornamen mlinjon ketupat, dan warna soga alam...",
        "galeri": "Dokumentasi ragam aplikasi kain parang kusumo dalam upacara lamaran adat Jawa..."
      },
      "stats": {
        "total_quiz_bank": 25,
        "active_quiz_questions": 10
      }
    }
  }
  ```

---

#### 4.3 Tandai Pilar Materi Selesai Dibaca
* **Metode & Rute**: `POST /api/modules/<module_id>/pillars/<pillar>`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Path Parameters**:
  * `module_id` (integer): ID modul (1 - 20).
  * `pillar` (string): Nama pilar (`sejarah_filosofi`, `karakteristik`, atau `galeri`).
* **Deskripsi**: Menyimpan penanda baca pilar materi pengguna dan memperbarui persentase progres modul.
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "module_id": 4,
    "pillar": "sejarah_filosofi",
    "progress": {
      "pillar_sejarah_filosofi": true,
      "pillar_karakteristik": false,
      "pillar_galeri": false,
      "quiz_passed": false,
      "practice_done": false,
      "progress_percent": 20
    }
  }
  ```

---

#### 4.4 Ambil Soal Kuis Modul (Randomizer Bank Soal)
* **Metode & Rute**: `GET /api/modules/<module_id>/quiz`
* **Autentikasi**: Publik (Opsional Token)
* **Query Parameters**:
  * `limit` (integer, default: 10, batas: 1 - 25): Jumlah soal yang diminta.
  * `random` (integer: 1 atau 0, default: 1): Jika `1`, 10 butir soal dipilih secara acak dari 25 bank soal modul.
* **Deskripsi**: Mengambil soal pilihan ganda A, B, C, D untuk modul terkait tanpa membocorkan kunci jawaban kepada klien.
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "module_id": 4,
    "total_questions": 10,
    "questions": [
      {
        "id": 76,
        "question_number": 1,
        "question_text": "Apakah makna filosofis utama dari kata 'Kusumo' dalam motif Batik Parang Kusumo?",
        "options": {
          "A": "Bunga kembang yang menebarkan keharuman budi pekerti luhur",
          "B": "Pedang ksatria tajam tak terkalahkan",
          "C": "Ombak samudra yang ganas",
          "D": "Mahkota emas raja keraton"
        }
      }
    ]
  }
  ```

---

#### 4.5 Pengiriman & Sinkronisasi Hasil Kuis (Dual-Mode Scoring)
* **Metode & Rute**: `POST /api/modules/<module_id>/quiz/attempts`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Deskripsi**: Mendukung 2 mode evaluasi fleksibel sesuai prinsip Offline-First:
  1. **Mode A (Online Scoring)**: Klien mengirimkan jawaban mentah, server menghitung skor dan mengembalikan koreksi pembahasan.
  2. **Mode B (Offline Evaluated Sync)**: Ponsel telah menilai kuis secara lokal di SQLite saat offline, lalu mengirimkan hasil final (`score`, `passed`, `attempted_at`) saat kembali mendapatkan sinyal internet.
* **Aturan Kelulusan**:
  * Standar KKM: Skor >= 70 (minimal 7 benar dari 10 soal).
  * Jika lulus, otomatis mencentang status `quiz_passed = 1` pada progres modul.

##### Contoh Payload Mode A (Online Scoring):
```json
{
  "answers": [
    {"question_id": 76, "selected_option": "A"},
    {"question_id": 77, "selected_option": "C"},
    {"question_id": 78, "selected_option": "B"},
    {"question_id": 79, "selected_option": "A"},
    {"question_id": 80, "selected_option": "D"},
    {"question_id": 81, "selected_option": "B"},
    {"question_id": 82, "selected_option": "A"},
    {"question_id": 83, "selected_option": "C"},
    {"question_id": 84, "selected_option": "A"},
    {"question_id": 85, "selected_option": "D"}
  ]
}
```

##### Contoh Payload Mode B (Offline Sync):
```json
{
  "total_questions": 10,
  "score": 80.0,
  "passed": true,
  "attempted_at": "2026-10-23T08:15:00Z"
}
```

* **Respons Sukses (`201 Created`)**:
  ```json
  {
    "attempt": {
      "id": 12,
      "module_id": 4,
      "score": 80.0,
      "passed": true,
      "attempted_at": "2026-10-23T08:15:00Z"
    },
    "evaluation": {
      "correct_count": 8,
      "total_questions": 10,
      "passing_score": 70
    },
    "progress": {
      "pillar_sejarah_filosofi": true,
      "pillar_karakteristik": true,
      "pillar_galeri": true,
      "quiz_passed": true,
      "practice_done": false,
      "progress_percent": 80
    }
  }
  ```

---

#### 4.6 Riwayat Percobaan Kuis Pengguna
* **Metode & Rute**: `GET /api/modules/<module_id>/quiz/attempts`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "best_score": 80.0,
    "attempts": [
      {
        "id": 12,
        "score": 80.0,
        "passed": true,
        "attempted_at": "2026-10-23T08:15:00Z"
      },
      {
        "id": 8,
        "score": 60.0,
        "passed": false,
        "attempted_at": "2026-10-22T14:10:00Z"
      }
    ]
  }
  ```

---

### Modul 5: Pemindaian AI & Evaluasi Praktikum (`/api/scans`)

*(Catatan: Sesuai arsitektur Offline-First, aplikasi mobile menjalankan inferensi di HP. Endpoint di bawah ini bertindak sebagai API server fallback dan sinkronisasi awan).*

#### 5.1 Universal Scan Batik (Stateless Fallback)
* **Metode & Rute**: `POST /api/scans/universal`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Content-Type**: `multipart/form-data`
* **Deskripsi**: Menerima gambar kain batik dan mengklasifikasikan motif menggunakan model Machine Learning MobileNetV2 (20 kelas). Mengembalikan Top 5 prediksi motif dengan persentase kecocokan.
* **Form-Data**:
  * `image`: Berkas foto kain (JPG/PNG/WEBP, maks 10 MB).
* **Respons Sukses (`201 Created`)**:
  ```json
  {
    "scan": {
      "id": 45,
      "scan_type": "universal",
      "confidence": 0.942,
      "inference_time_ms": 112,
      "created_at": "2026-10-23T10:30:00Z"
    },
    "top_match": {
      "motif_id": 4,
      "name": "Parang Kusumo",
      "origin_region": "Surakarta dan Yogyakarta",
      "probability": 0.942,
      "percent": 94,
      "short_description": "Batik larangan keraton bermakna ksatria...",
      "suggested_module": {
        "id": 4,
        "title": "Batik Parang Kusumo"
      }
    },
    "top5": [
      {"rank": 1, "motif_id": 4, "name": "Parang Kusumo", "probability": 0.942, "percent": 94},
      {"rank": 2, "motif_id": 2, "name": "Parang Rusak", "probability": 0.035, "percent": 4},
      {"rank": 3, "motif_id": 1, "name": "Cecek Hasan", "probability": 0.011, "percent": 1},
      {"rank": 4, "motif_id": 3, "name": "Truntum", "probability": 0.007, "percent": 1},
      {"rank": 5, "motif_id": 5, "name": "Kawung", "probability": 0.005, "percent": 1}
    ]
  }
  ```

---

#### 5.2 Unggah Evaluasi Kuis Praktikum Modul
* **Metode & Rute**: `POST /api/modules/<module_id>/practice`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Content-Type**: `multipart/form-data`
* **Deskripsi**: Mengunggah foto hasil karya kain batik pada kuis praktikum modul tertentu.
  * **Kebijakan Smart Retention**: Foto praktikum lama milik pengguna pada modul terkait otomatis dihapus dari server saat mencoba ulang (retake), sehingga server hanya menyimpan maksimal 1 foto karya per modul.
* **Form-Data**:
  * `image`: Berkas foto karya kain batik praktikum.
* **Respons Sukses (`201 Created`)**:
  ```json
  {
    "scan": {
      "id": 46,
      "scan_type": "kuismu",
      "module_id": 4,
      "passed": true,
      "fit_score": 0.885,
      "rating": "Sangat Baik",
      "inference_time_ms": 108,
      "created_at": "2026-10-23T10:45:00Z"
    },
    "progress": {
      "pillar_sejarah_filosofi": true,
      "pillar_karakteristik": true,
      "pillar_galeri": true,
      "quiz_passed": true,
      "practice_done": true,
      "progress_percent": 100
    }
  }
  ```

---

#### 5.3 Riwayat Pemindaian Pengguna
* **Metode & Rute**: `GET /api/scans`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Query Parameters**:
  * `type` (string, opsional): Filter jenis scan (`universal` atau `kuismu`).
  * `limit` (integer, default: 50, batas: 1 - 100).
  * `offset` (integer, default: 0).
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "total": 1,
    "limit": 50,
    "offset": 0,
    "scans": [
      {
        "id": 46,
        "scan_type": "kuismu",
        "motif_name": "Parang Kusumo",
        "module_id": 4,
        "module_title": "Batik Parang Kusumo",
        "score": 0.885,
        "passed": true,
        "created_at": "2026-10-23T10:45:00Z"
      }
    ]
  }
  ```

---

#### 5.4 Detail Pemindaian Spesifik
* **Metode & Rute**: `GET /api/scans/<scan_id>`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "scan": {
      "id": 46,
      "scan_type": "kuismu",
      "module_id": 4,
      "top_motif_id": 4,
      "confidence": 0.885,
      "fit_score": 0.885,
      "passed": true,
      "rating": "Sangat Baik",
      "inference_time_ms": 108,
      "has_image": true,
      "created_at": "2026-10-23T10:45:00Z"
    },
    "ranking": [
      {
        "rank": 1,
        "motif_id": 4,
        "name": "Parang Kusumo",
        "origin_region": "Surakarta dan Yogyakarta",
        "probability": 0.885,
        "percent": 89
      }
    ]
  }
  ```

---

#### 5.5 Unduh Berkas Foto Hasil Scan
* **Metode & Rute**: `GET /api/scans/<scan_id>/image`
* **Autentikasi**: Memerlukan Token (`Bearer`)
* **Deskripsi**: Mengunduh berkas gambar pindaian milik pengguna.
* **Respons Sukses (`200 OK`)**: Biner file `image/jpeg` atau `image/png`.

---

### Modul 6: Status Sistem (`/api/health`)

#### 6.1 Pemeriksaan Kesehatan Server (Health Check)
* **Metode & Rute**: `GET /api/health`
* **Autentikasi**: Publik
* **Deskripsi**: Memantau ketersediaan server, koneksi database SQLite, dan kesiapan model Machine Learning TFLite.
* **Respons Sukses (`200 OK`)**:
  ```json
  {
    "status": "healthy",
    "version": "2.0.0",
    "database": "connected",
    "ml_model": "ready",
    "ml_classes_count": 20,
    "timestamp": "2026-10-23T10:50:00Z"
  }
  ```

---

## 3. Matriks Kode Error Terstandarisasi

| HTTP Code | Error Code (`code`) | Keterangan & Solusi |
|---|---|---|
| `400` | `invalid_json` | Format JSON request body tidak terbaca atau sintaks rusak. |
| `401` | `invalid_credentials` | Pasangan email dan kata sandi salah. |
| `401` | `token_missing` | Header `Authorization: Bearer <token>` tidak disertakan. |
| `401` | `token_expired` | Masa berlaku token telah habis, arahkan pengguna ke login. |
| `404` | `not_found` | Sumber daya ID (modul/motif/scan) tidak ditemukan di database. |
| `404` | `email_not_found` | Email yang dimasukkan pada form lupa sandi belum terdaftar. |
| `404` | `avatar_not_found` | Pengguna belum pernah mengunggah foto profil. |
| `409` | `email_taken` | Email telah digunakan oleh akun lain saat registrasi. |
| `422` | `validation_error` | Field masukan tidak lolos validasi (panjang karakter, format email). |
| `422` | `invalid_question` | `question_id` yang dijawab bukan milik modul yang diuji. |
| `422` | `invalid_option` | Opsi jawaban bukan A, B, C, atau D. |
| `422` | `duplicate_answer` | Soal yang sama dikirimkan lebih dari satu kali dalam 1 attempt. |
| `422` | `invalid_otp` | 4 digit kode OTP salah. |
| `422` | `otp_expired` | Kode OTP melewati batas masa berlaku (10 menit). |
| `423` | `account_locked` | 5x salah sandi berturut-turut. Akun dikunci 15 menit. |
| `429` | `otp_throttled` | Permintaan OTP dibatasi jeda 60 detik sebelum dapat meminta lagi. |
| `429` | `otp_locked` | Kode OTP salah 3x berturut-turut, pengguna harus meminta kode baru. |
| `502` | `email_failed` | Pengiriman email OTP gagal menghubungi relay SMTP eksternal. |
| `503` | `email_not_configured`| Server berjalan tanpa kredensial SMTP aktif. |

---

*Dokumen ini diperbarui secara berkala dan disinkronkan dengan basis data skema v2 serta test suite Kenali Batikmu.*
