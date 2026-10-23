# Database Kenali Batikmu (SQLite, skema v2)

Sumber kebenaran: [`app/schema.sqlite.sql`](../app/schema.sqlite.sql) (struktur) dan
[`app/seed.sqlite.sql`](../app/seed.sqlite.sql) (data referensi). Kamus data lengkap ada di
[README §2](../README.md#2-struktur-database). Dokumen ini mencatat **apa yang harus cocok** dan bagaimana
kecocokan itu dijaga.

## 1. Tiga hal yang harus selaras

| Pihak | Yang harus cocok dengan database | Dijaga oleh |
|---|---|---|
| **Model ML** (`batik_mobilenetv2.tflite`, 20 output) | `batik_motifs.ml_class_index` 0–19 dan `slug` identik dengan urutan/nama di `app/models/labels.txt` | test `test_motifs_match_ml_labels_exactly`; `scans._infer` menolak bila jumlah output model ≠ jumlah motif (`model_mismatch`) |
| **Aplikasi mobile** | Kolom yang ditampilkan/diedit di UI: `users.phone`, `modules.video_url`, `module_contents.badge`, galeri tanpa gambar, skor terbaik per modul | test `ModuleTests`, `ProfileTests`; pemetaan di `ModuleContentModel.fromApi` (Dart) |
| **Backend** | Constraint (`CHECK`, `UNIQUE`, FK) dan data tanpa sisa placeholder | test `SchemaAndSeedTests` |

## 2. Riwayat versi

| Versi | Perubahan |
|---|---|
| v1 | 11 tabel; seed 20 motif/20 modul tetapi memuat akun & percobaan kuis demo, penanda `[VERIFIKASI]`, path gambar `/static/...` yang tidak ada |
| **v2** | + `users.phone`, + `modules.video_url`, + `module_contents.badge`, `module_gallery_images.image_url` boleh `NULL`, + tabel `password_resets`, + indeks `idx_scans_module` & `idx_resets_user`, `users.email` `COLLATE NOCASE`. Seed dibersihkan (lihat `CATATAN_PERUBAHAN.md` di folder induk) |

Migrasi v1 → v2 untuk database yang sudah ada berjalan otomatis (`db._migrate_to_2`), hanya untuk struktur.
Data tidak ikut berubah; gunakan `python manage.py reset --yes` untuk memuat seed terbaru.

## 3. Konvensi isi `module_contents`

Lihat tabel konvensi `order_no` di README §2.3 (`module_contents`). Ringkas: `sejarah_filosofi` 1–4 = empat bagian
teori; `karakteristik` 1 = ringkasan, 2–4 = kartu bertanda `badge`, 5+ = daftar pakem.

## 4. Aturan yang berlaku di aplikasi (bukan constraint SQL)

- Progres modul = 20% × (history, character, gallery, quiz, practice); `quiz_done`/`practice_done` bersifat permanen.
- Kuis dinilai di server; kunci jawaban hanya dikirim setelah jawaban masuk.
- `fit_score` (kuis praktik) = probabilitas model untuk motif modul; lulus bila ≥ `modules.passing_score`/100.
- Skor terbaik (`quiz_best_score`, `practice_best_score`) dihitung dari `quiz_attempts` dan `scans`, tidak disimpan ganda.
