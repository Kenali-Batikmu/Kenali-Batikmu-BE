-- ============================================================================
-- Kenali Batikmu - Seed Data (SQLite)
-- Jalankan SETELAH schema.sqlite.sql (db.seed_db melakukannya otomatis).
-- Mengisi: batik_motifs, modules, module_contents, module_gallery_images,
--          quiz_questions.  TIDAK membuat user/percobaan kuis apa pun
--          (akun demo untuk pengembangan: python manage.py seed-demo).
--
-- Catatan:
--  * ml_class_index 0-19 mengikuti urutan alfabet label model (app/models/labels.txt).
--  * slug = nama kelas dataset (batik_xxx). Slug batik_tuntrum dipertahankan karena
--    harus sama dengan label model; nama tampilannya "Truntum".
--  * Modul 6, 8, 9, 18 memakai materi lengkap dari aplikasi mobile (bagian 5);
--    modul lain masih berisi 1 paragraf per pilar.
--  * Gambar: hanya aset yang benar-benar ada di app (assets/images/...). Sisanya NULL
--    dan app menampilkan ikon pengganti.
-- ============================================================================

PRAGMA foreign_keys = ON;

BEGIN;

-- 1. batik_motifs -----------------------------------------------------------
INSERT OR IGNORE INTO batik_motifs (name, slug, origin_region, short_description, thumbnail_url, ml_class_index) VALUES
('Batik Betawi',        'batik_betawi',        'DKI Jakarta',                         'Batik khas Jakarta dengan motif ondel-ondel, Monas, dan flora-fauna lokal yang merekam kehidupan masyarakat Betawi.', NULL, 0),
('Batik Bokor Kencono', 'batik_bokor_kencono', 'Jawa Tengah (Surakarta)', 'Motif bernuansa bokor, wadah berbentuk mangkuk dalam tradisi Jawa, yang melambangkan kemakmuran dan kemuliaan.', NULL, 1),
('Batik Buketan',       'batik_buketan',       'Pekalongan, Jawa Tengah',             'Motif rangkaian bunga seperti karangan (buket) hasil pengaruh selera Eropa pada batik pesisir Pekalongan.', NULL, 2),
('Batik Dayak',         'batik_dayak',         'Kalimantan',                          'Batik yang mengangkat ragam hias Dayak seperti burung enggang, pohon hayat, dan sulur bergaya ukiran.', NULL, 3),
('Batik Jlamprang',     'batik_jlamprang',     'Pekalongan, Jawa Tengah',             'Motif geometris simetris bergaya bintang atau bunga yang diduga dipengaruhi kain patola India.', NULL, 4),
('Batik Kawung',        'batik_kawung',        'Yogyakarta dan Surakarta',            'Salah satu motif tertua: lingkaran lonjong tersusun rapi yang melambangkan kesucian dan keadilan.', NULL, 5),
('Batik Liong',         'batik_liong',         'Pesisir utara Jawa',                  'Batik bergambar naga (liong) hasil akulturasi budaya Tionghoa, simbol kekuatan dan keberuntungan.', NULL, 6),
('Batik Mega Mendung',  'batik_mega_mendung',  'Cirebon, Jawa Barat',                 'Motif awan bergradasi warna khas Cirebon yang melambangkan kesabaran dan pembawa hujan.', NULL, 7),
('Batik Parang',        'batik_parang',        'Yogyakarta dan Surakarta',            'Motif diagonal berbentuk S bersambung yang melambangkan semangat pantang menyerah.', NULL, 8),
('Batik Sekar Jagad',   'batik_sekarjagad',   'Jawa Tengah dan Yogyakarta',          'Perpaduan beragam ragam hias yang bertebaran, melambangkan keindahan dan keberagaman dunia.', NULL, 9),
('Batik Sidoluhur',     'batik_sidoluhur',     'Surakarta dan Yogyakarta',            'Motif keluarga Sido untuk pernikahan, berisi harapan agar pemakainya menjadi pribadi yang luhur.', NULL, 10),
('Batik Sidomukti',     'batik_sidomukti',     'Surakarta dan Yogyakarta',            'Motif keluarga Sido untuk pernikahan, berisi harapan hidup makmur dan sejahtera.', NULL, 11),
('Batik Sidomulyo',     'batik_sidomulyo',     'Surakarta dan Yogyakarta',            'Motif keluarga Sido untuk pernikahan, berisi harapan hidup mulia dan terhormat.', NULL, 12),
('Batik Singa Barong',  'batik_singa_barong',  'Cirebon, Jawa Barat',                 'Motif makhluk mitologis gabungan beberapa unsur budaya, terinspirasi Kereta Singa Barong keraton Cirebon.', NULL, 13),
('Batik Srikaton',      'batik_srikaton',      'Surakarta, Jawa Tengah', 'Motif bermakna keagungan dan kewibawaan, dengan harapan pemakainya tampak berseri dan berwibawa.', NULL, 14),
('Batik Tribusono',     'batik_tribusono',     'Jawa',                   'Motif tradisional Jawa dengan nama yang dapat ditafsirkan sebagai tiga busana atau tiga tatanan.', NULL, 15),
('Batik Tujuh Rupa',    'batik_tujuh_rupa',    'Pekalongan, Jawa Tengah',             'Batik pesisir berwarna-warni dengan motif flora, burung, dan kupu-kupu yang sangat meriah.', NULL, 16),
('Batik Truntum',      'batik_tuntrum',       'Surakarta',                           'Bintang kasih sayang abadi, lambang cinta tulus yang senantiasa bersemi.', NULL, 17),
('Batik Wahyu Tumurun', 'batik_wahyu_tumurun', 'Surakarta dan Yogyakarta',            'Motif bermakna turunnya wahyu atau anugerah ilahi, populer untuk pernikahan dan upacara penting.', NULL, 18),
('Batik Wirasat',       'batik_wirasat',       'Jawa',                   'Motif tradisional Jawa yang namanya bermakna firasat atau pertanda, sarat pesan dan harapan.', NULL, 19);

-- 2. modules ----------------------------------------------------------------
WITH v(slug, title, description, order_no) AS (VALUES
 ('batik_betawi',        'Mengenal Batik Betawi',        'Pelajari sejarah, ciri visual, dan ikon Jakarta yang muncul pada Batik Betawi.', 1),
 ('batik_bokor_kencono', 'Mengenal Batik Bokor Kencono', 'Pelajari makna bokor dan kencana serta ciri visual motif Bokor Kencono.', 2),
 ('batik_buketan',       'Mengenal Batik Buketan',       'Pelajari asal-usul motif karangan bunga dari Pekalongan dan pengaruh Eropanya.', 3),
 ('batik_dayak',         'Mengenal Batik Dayak',         'Pelajari ragam hias Dayak dan filosofi hubungan manusia dengan alam.', 4),
 ('batik_jlamprang',     'Mengenal Batik Jlamprang',     'Pelajari motif geometris Jlamprang dan pengaruh kain patola India.', 5),
 ('batik_kawung',        'Mengenal Batik Kawung',        'Pelajari motif Kawung, salah satu motif batik tertua, beserta maknanya.', 6),
 ('batik_liong',         'Mengenal Batik Liong',         'Pelajari motif naga pada batik pesisir hasil akulturasi budaya Tionghoa.', 7),
 ('batik_mega_mendung',  'Mengenal Batik Mega Mendung',  'Pelajari motif awan bergradasi khas Cirebon dan filosofinya.', 8),
 ('batik_parang',        'Mengenal Batik Parang',        'Pelajari motif Parang, filosofi perjuangan, dan kedudukannya di keraton.', 9),
 ('batik_sekarjagad',   'Mengenal Batik Sekar Jagad',   'Pelajari motif Sekar Jagad yang memadukan beragam ragam hias.', 10),
 ('batik_sidoluhur',     'Mengenal Batik Sidoluhur',     'Pelajari makna Sidoluhur dalam keluarga motif Sido untuk pernikahan.', 11),
 ('batik_sidomukti',     'Mengenal Batik Sidomukti',     'Pelajari makna Sidomukti dan harapan kemakmuran di dalamnya.', 12),
 ('batik_sidomulyo',     'Mengenal Batik Sidomulyo',     'Pelajari makna Sidomulyo dan harapan hidup mulia di dalamnya.', 13),
 ('batik_singa_barong',  'Mengenal Batik Singa Barong',  'Pelajari motif Singa Barong dan simbol akulturasi budaya Cirebon.', 14),
 ('batik_srikaton',      'Mengenal Batik Srikaton',      'Pelajari makna Srikaton dan simbol keagungan di dalamnya.', 15),
 ('batik_tribusono',     'Mengenal Batik Tribusono',     'Pelajari asal-usul nama dan ciri umum motif Tribusono.', 16),
 ('batik_tujuh_rupa',    'Mengenal Batik Tujuh Rupa',    'Pelajari batik pesisir Pekalongan yang kaya warna dan motif flora-fauna.', 17),
 ('batik_tuntrum',       'Mengenal Batik Truntum',       'Pola gemintang cinta kasih tulus yang senantiasa bersemi di keheningan malam.', 18),
 ('batik_wahyu_tumurun', 'Mengenal Batik Wahyu Tumurun', 'Pelajari makna wahyu atau anugerah ilahi pada motif Wahyu Tumurun.', 19),
 ('batik_wirasat',       'Mengenal Batik Wirasat',       'Pelajari asal-usul nama dan makna pertanda pada motif Wirasat.', 20)
)
INSERT OR IGNORE INTO modules (motif_id, title, description, cover_image, passing_score, order_no)
SELECT m.id, v.title, v.description, NULL, 70, v.order_no
FROM v
JOIN batik_motifs m ON m.slug = v.slug;

-- 3. module_contents (3 pilar per modul) -------------------------------------
WITH v(mod, pillar, title, body) AS (VALUES
-- 1 Betawi
(1,'sejarah_filosofi','Sejarah dan Filosofi Batik Betawi','Batik Betawi tergolong muda dibanding batik keraton. Masyarakat Betawi sebelumnya tidak memiliki tradisi batik yang kuat. Sejak awal 2000-an batik Betawi dikembangkan, antara lain di kawasan Terogong, Jakarta Selatan, sebagai identitas visual Jakarta. Motifnya mencerminkan budaya Betawi yang terbuka dan memadukan unsur Melayu, Tionghoa, Arab, dan Eropa.'),
(1,'karakteristik','Ciri Khas Batik Betawi','Motif utamanya meliputi ondel-ondel, Monas, rumah adat Betawi, serta flora dan fauna khas Jakarta. Warnanya cenderung cerah dan berani, misalnya merah, hijau, biru, dan kuning, dengan komposisi yang ramai dan bergaya dekoratif.'),
(1,'galeri','Cara Mengamati Galeri Batik Betawi','Saat mengamati gambar, cari ikon kota Jakarta: figur ondel-ondel bermahkota, tugu Monas, atau pohon dan burung khas. Kehadiran ikon urban inilah yang membedakannya dari batik keraton Jawa yang bernuansa soga dan geometris.'),
-- 2 Bokor Kencono
(2,'sejarah_filosofi','Sejarah dan Filosofi Batik Bokor Kencono','Nama motif ini berasal dari kata bokor, yaitu wadah logam berbentuk mangkuk besar yang dipakai dalam tradisi dan upacara Jawa, dan kencana yang berarti emas. Gabungan keduanya melambangkan harapan akan kemakmuran, kemuliaan, dan rezeki yang melimpah.'),
(2,'karakteristik','Ciri Khas Batik Bokor Kencono','Bentuk bokor atau wadah menjadi unsur khas, biasanya dikelilingi ornamen flora, sulur, dan isian halus yang tersusun berulang. Rincian ornamen dapat berbeda antar perajin batik.'),
(2,'galeri','Cara Mengamati Galeri Batik Bokor Kencono','Perhatikan bentuk menyerupai mangkuk atau wadah di dalam pola, lalu amati ornamen flora dan sulur yang mengelilinginya. Bentuk wadah inilah petunjuk utama untuk membedakannya dari motif bunga biasa.'),
-- 3 Buketan
(3,'sejarah_filosofi','Sejarah dan Filosofi Batik Buketan','Kata buketan berasal dari bahasa Belanda, yaitu buket (karangan bunga). Motif ini berkembang di Pekalongan pada masa kolonial, ketika selera Eropa dan Indo-Eropa memengaruhi batik pesisir. Perajin seperti Eliza van Zuylen dikenal lewat batik bergaya buketan yang digemari kalangan Indo-Belanda.'),
(3,'karakteristik','Ciri Khas Batik Buketan','Ciri utamanya adalah rangkaian bunga seperti karangan, kadang dilengkapi kupu-kupu atau burung. Isen-isen halus dan warna-warna cerah atau pastel khas batik pesisir membuat tampilannya naturalis dan manis.'),
(3,'galeri','Cara Mengamati Galeri Batik Buketan','Cari kelompok bunga yang tersusun membentuk satu rangkaian utuh, bukan bunga yang tersebar acak. Bunga yang realistis dan warna yang lembut atau meriah adalah petunjuk bahwa ini batik gaya pesisir.'),
-- 4 Dayak
(4,'sejarah_filosofi','Sejarah dan Filosofi Batik Dayak','Batik Dayak relatif modern. Ragam hiasnya diambil dari seni tradisi suku Dayak di Kalimantan, seperti ukiran, tato, dan hiasan manik-manik. Filosofinya menekankan keselarasan manusia dengan alam, leluhur, dan dunia spiritual.'),
(4,'karakteristik','Ciri Khas Batik Dayak','Motif yang sering muncul adalah burung enggang, pohon hayat (pohon kehidupan), sulur dan spiral bergaya ukiran, serta perisai. Warnanya cenderung kontras, misalnya hitam, merah, dan cokelat.'),
(4,'galeri','Cara Mengamati Galeri Batik Dayak','Perhatikan bentuk enggang bergaya dekoratif, sulur melengkung seperti ukiran, dan komposisi yang simetris. Pola ini berbeda dari motif Jawa yang lebih banyak geometris atau flora halus.'),
-- 5 Jlamprang
(5,'sejarah_filosofi','Sejarah dan Filosofi Batik Jlamprang','Motif Jlamprang diduga terpengaruh kain patola dari India yang masuk lewat jalur perdagangan. Motif ini dikenal terutama di Pekalongan (kawasan Krapyak) dan menjadi contoh perpaduan budaya India dengan batik pesisir Jawa.'),
(5,'karakteristik','Ciri Khas Batik Jlamprang','Jlamprang bersifat geometris dengan bentuk bintang atau bunga, lingkaran, dan belah ketupat yang tersusun simetris dan berulang. Warnanya umumnya cerah, sesuai gaya batik pesisir.'),
(5,'galeri','Cara Mengamati Galeri Batik Jlamprang','Amati pola yang rapi dan simetris seperti ubin, dengan pusat berbentuk bintang atau bunga. Tidak ada figur hewan besar atau awan, hanya komposisi geometris yang berulang.'),
-- 7 Liong
(7,'sejarah_filosofi','Sejarah dan Filosofi Batik Liong','Liong berarti naga dalam bahasa Tionghoa. Motif ini lahir dari akulturasi budaya Tionghoa dengan batik pesisir utara Jawa. Naga melambangkan kekuatan, kebaikan, dan keberuntungan.'),
(7,'karakteristik','Ciri Khas Batik Liong','Figur naga bertubuh panjang dan bersisik, dengan kepala berjanggut serta cakar, sering dikelilingi awan atau bunga. Warnanya cenderung cerah dan meriah, banyak memakai merah.'),
(7,'galeri','Cara Mengamati Galeri Batik Liong','Cari tubuh naga yang melingkar dengan sisik dan kepala yang jelas. Naga pada batik ini berbeda dari figur Singa Barong yang merupakan makhluk gabungan.'),
-- 10 Sekar Jagad
(10,'sejarah_filosofi','Sejarah dan Filosofi Batik Sekar Jagad','Sekar berarti bunga dan jagad berarti dunia, sehingga Sekar Jagad bermakna keindahan dunia. Ada pula tafsir yang mengaitkannya dengan kata kaart (peta) dalam bahasa Belanda. Motif ini melambangkan keberagaman dan keindahan dunia.'),
(10,'karakteristik','Ciri Khas Batik Sekar Jagad','Beragam ragam hias, seperti bunga, hewan, dan isen-isen, tersebar dalam bidang-bidang tidak beraturan seperti peta. Warnanya bisa klasik maupun cerah.'),
(10,'galeri','Cara Mengamati Galeri Batik Sekar Jagad','Perhatikan banyaknya motif berbeda yang bercampur dalam satu kain, dipisah bidang-bidang tidak beraturan. Keragaman isi inilah yang menjadi ciri utamanya.'),
-- 11 Sidoluhur
(11,'sejarah_filosofi','Sejarah dan Filosofi Batik Sidoluhur','Sido berarti menjadi atau terus-menerus, dan luhur berarti mulia. Sidoluhur mengandung harapan agar pemakainya menjadi pribadi berbudi luhur. Motif keluarga Sido umum dipakai dalam upacara pernikahan adat Jawa.'),
(11,'karakteristik','Ciri Khas Batik Sidoluhur','Motif keluarga Sido umumnya berupa ornamen tersusun dalam bidang-bidang teratur (ceplokan) dengan latar warna soga. Rincian ornamen dapat berbeda antar perajin dan gaya Surakarta atau Yogyakarta.'),
(11,'galeri','Cara Mengamati Galeri Batik Sidoluhur','Amati susunan ornamen dalam bidang teratur dengan latar cokelat soga. Karena keluarga Sido mirip satu sama lain, perhatikan juga keterangan nama motif.'),
-- 12 Sidomukti
(12,'sejarah_filosofi','Sejarah dan Filosofi Batik Sidomukti','Mukti berarti makmur dan sejahtera. Sidomukti mengandung harapan agar pemakainya hidup makmur dan sejahtera. Motif ini lazim dipakai pengantin dalam upacara pernikahan adat Jawa.'),
(12,'karakteristik','Ciri Khas Batik Sidomukti','Motif ini umumnya berisi ornamen yang tersusun teratur dengan latar soga. Seperti keluarga Sido lainnya, rincian ornamen berbeda menurut gaya perajin dan daerah.'),
(12,'galeri','Cara Mengamati Galeri Batik Sidomukti','Amati ornamen yang tersusun teratur dengan latar cokelat soga. Karena mirip dengan Sidoluhur dan Sidomulyo, nama motif dan konteks pemakaiannya membantu membedakannya.'),
-- 13 Sidomulyo
(13,'sejarah_filosofi','Sejarah dan Filosofi Batik Sidomulyo','Mulyo berarti mulia dan sejahtera. Sidomulyo mengandung harapan agar pemakainya menjalani hidup yang mulia, terhormat, dan sejahtera. Motif ini termasuk keluarga Sido yang lazim hadir dalam upacara pernikahan adat Jawa.'),
(13,'karakteristik','Ciri Khas Batik Sidomulyo','Susunan ornamen teratur dengan latar soga merupakan ciri umum keluarga Sido. Rincian ornamen dapat berbeda menurut gaya Surakarta atau Yogyakarta.'),
(13,'galeri','Cara Mengamati Galeri Batik Sidomulyo','Amati tata letak ornamen yang teratur dan warna soga yang hangat. Karena dekat dengan Sidomukti dan Sidoluhur, perhatikan keterangan nama motif.'),
-- 14 Singa Barong
(14,'sejarah_filosofi','Sejarah dan Filosofi Batik Singa Barong','Motif ini terinspirasi Kereta Singa Barong milik keraton Cirebon. Wujud singa barong umumnya memadukan belalai gajah (unsur India), kepala naga (unsur Tionghoa), dan sayap buraq (unsur Islam). Gabungan tersebut menjadi simbol akulturasi budaya serta kekuatan dan keberanian.'),
(14,'karakteristik','Ciri Khas Batik Singa Barong','Figur makhluk mitologis dengan unsur campuran, yakni belalai, sayap, dan kepala bertaring, sering dikelilingi awan atau ornamen khas Cirebon. Warnanya cenderung kaya dan kontras.'),
(14,'galeri','Cara Mengamati Galeri Batik Singa Barong','Cari satu makhluk dengan bagian tubuh campuran, bukan hewan biasa. Belalai dan sayap pada satu tubuh adalah petunjuk yang kuat.'),
-- 15 Srikaton
(15,'sejarah_filosofi','Sejarah dan Filosofi Batik Srikaton','Nama Srikaton dapat dibaca sebagai sri (kemakmuran, keagungan) dan katon (tampak). Motif ini melambangkan harapan agar pemakainya tampak berseri, berwibawa, dan agung.'),
(15,'karakteristik','Ciri Khas Batik Srikaton','Motif tradisional Jawa dengan susunan ornamen yang teratur dan bernuansa klasik. Rincian ornamen dapat berbeda antar perajin.'),
(15,'galeri','Cara Mengamati Galeri Batik Srikaton','Amati tata letak ornamen yang teratur dan warna klasik khas batik Jawa Tengah. Nama motif dan konteks pemakaian membantu pengenalannya.'),
-- 16 Tribusono
(16,'sejarah_filosofi','Sejarah dan Filosofi Batik Tribusono','Nama Tribusono dapat ditafsirkan dari tri (tiga) dan busono atau busana (pakaian). Tafsir ini umumnya dimaknai sebagai harapan akan tatanan atau kelengkapan hidup yang baik.'),
(16,'karakteristik','Ciri Khas Batik Tribusono','Motif tradisional Jawa dengan susunan ornamen yang teratur dan warna klasik. Rincian ornamen dapat berbeda antar perajin.'),
(16,'galeri','Cara Mengamati Galeri Batik Tribusono','Amati susunan ornamen yang teratur dan warna klasik. Gunakan nama motif sebagai petunjuk tambahan karena pola mirip dengan beberapa motif Jawa lain.'),
-- 17 Tujuh Rupa
(17,'sejarah_filosofi','Sejarah dan Filosofi Batik Tujuh Rupa','Tujuh Rupa adalah batik pesisir Pekalongan. Namanya dikaitkan dengan banyaknya warna (tujuh warna) dan juga makna pitu sebagai pitulungan (pertolongan). Gaya warna-warninya dipengaruhi pertemuan budaya Jawa, Tionghoa, dan Eropa.'),
(17,'karakteristik','Ciri Khas Batik Tujuh Rupa','Warnanya sangat beragam dan meriah. Motifnya didominasi bunga, burung, dan kupu-kupu bergaya naturalis dengan isen-isen halus.'),
(17,'galeri','Cara Mengamati Galeri Batik Tujuh Rupa','Perhatikan banyaknya warna dalam satu kain serta flora dan fauna yang meriah. Palet warna yang sangat ramai adalah petunjuk utamanya.'),
-- 19 Wahyu Tumurun
(19,'sejarah_filosofi','Sejarah dan Filosofi Batik Wahyu Tumurun','Wahyu berarti anugerah ilahi dan tumurun berarti turun. Wahyu Tumurun mengandung harapan agar pemakainya mendapat anugerah dan petunjuk dari Tuhan. Motif ini populer dalam pernikahan dan upacara penting.'),
(19,'karakteristik','Ciri Khas Batik Wahyu Tumurun','Unsur yang sering muncul antara lain mahkota, sayap (lar), dan bunga, tersusun dalam bidang yang teratur. Warna klasik soga mendominasi.'),
(19,'galeri','Cara Mengamati Galeri Batik Wahyu Tumurun','Cari bentuk mahkota dan sayap di antara ornamen bunga. Keberadaan mahkota dan sayap adalah petunjuk utama motif ini.'),
-- 20 Wirasat
(20,'sejarah_filosofi','Sejarah dan Filosofi Batik Wirasat','Wirasat berarti firasat atau pertanda. Motif ini dimaknai sebagai pesan, petunjuk, dan harapan dalam menjalani hidup.'),
(20,'karakteristik','Ciri Khas Batik Wirasat','Motif tradisional Jawa dengan susunan ornamen teratur dan warna klasik. Rincian ornamen dapat berbeda antar perajin.'),
(20,'galeri','Cara Mengamati Galeri Batik Wirasat','Amati susunan ornamen yang teratur dan warna klasik. Gunakan nama motif sebagai petunjuk tambahan.')
)
INSERT OR IGNORE INTO module_contents (module_id, pillar, title, body, order_no)
SELECT m.id, v.pillar, v.title, v.body, 1
FROM v
JOIN modules m ON m.order_no = v.mod;

-- 4. quiz_questions (4 soal per modul) --------------------------------------
WITH v(mod, question, a, b, c, d, correct, explanation) AS (VALUES
-- 1 Betawi
(1,'Dari daerah manakah Batik Betawi berasal?','DKI Jakarta','Cirebon','Yogyakarta','Pekalongan','A','Batik Betawi adalah batik khas Jakarta.'),
(1,'Ikon manakah yang lazim muncul pada Batik Betawi?','Meru','Ondel-ondel','Naga','Burung enggang','B','Ondel-ondel dan Monas adalah ikon khas Jakarta.'),
(1,'Budaya Betawi terbuka terhadap pengaruh apa saja?','Hanya Jawa','Hanya India','Melayu, Tionghoa, Arab, dan Eropa','Hanya Belanda','C','Betawi memadukan unsur Melayu, Tionghoa, Arab, dan Eropa.'),
(1,'Dibandingkan batik keraton, warna Batik Betawi cenderung...','Cerah dan berani','Hanya hitam putih','Hanya cokelat soga','Selalu pudar','A','Batik Betawi cenderung memakai warna cerah dan berani.'),
-- 2 Bokor Kencono
(2,'Apa arti kata kencana pada nama Bokor Kencono?','Perak','Emas','Tembaga','Kayu','B','Kencana berarti emas.'),
(2,'Bokor adalah...','Senjata tajam','Alat musik','Wadah berbentuk mangkuk besar','Hewan mitologi','C','Bokor adalah wadah logam berbentuk mangkuk besar.'),
(2,'Motif Bokor Kencono melambangkan harapan akan...','Kemakmuran dan kemuliaan','Peperangan','Kesedihan','Perjalanan jauh','A','Bokor dan kencana melambangkan kemakmuran dan kemuliaan.'),
(2,'Bentuk khas yang dicari pada motif ini adalah...','Naga bersisik','Awan berlapis','Wadah atau bokor','Gunung berapi','C','Bentuk wadah menjadi petunjuk utamanya.'),
-- 3 Buketan
(3,'Kata buket pada Buketan berasal dari bahasa...','Belanda','Arab','Tionghoa','Sunda','A','Buket berasal dari bahasa Belanda yang berarti karangan bunga.'),
(3,'Buketan berkembang terutama di kota...','Surakarta','Pekalongan','Cirebon','Yogyakarta','B','Buketan berkembang di Pekalongan.'),
(3,'Ciri utama motif Buketan adalah...','Garis diagonal tegas','Naga bersisik','Rangkaian bunga seperti karangan','Lingkaran bersilang','C','Buketan menampilkan rangkaian bunga seperti karangan.'),
(3,'Motif Buketan dipengaruhi selera dari...','India','Eropa (Indo-Belanda)','Dayak','Arab','B','Selera Eropa dan Indo-Eropa memengaruhi Buketan.'),
-- 4 Dayak
(4,'Burung apa yang sering menjadi motif penting pada Batik Dayak?','Merpati','Enggang','Kakatua putih','Elang jawa','B','Burung enggang penting dalam budaya Dayak.'),
(4,'Dari pulau mana Batik Dayak berasal?','Sumatra','Sulawesi','Kalimantan','Bali','C','Suku Dayak berada di Kalimantan.'),
(4,'Pohon hayat melambangkan...','Kehidupan dan hubungan manusia dengan alam','Perdagangan','Kekuasaan raja Jawa','Musim hujan','A','Pohon hayat adalah pohon kehidupan.'),
(4,'Ragam hias Batik Dayak diambil dari...','Candi Hindu Jawa','Keramik Tiongkok','Seni Eropa','Ukiran, tato, dan manik-manik Dayak','D','Ragam hias berakar dari seni tradisi Dayak.'),
-- 5 Jlamprang
(5,'Motif Jlamprang diduga dipengaruhi kain...','Songket','Patola India','Ulos','Tenun ikat Sumba','B','Jlamprang diduga terpengaruh kain patola India.'),
(5,'Jlamprang dikenal berkembang di kota...','Pekalongan','Cirebon','Surakarta','Yogyakarta','A','Jlamprang dikenal di Pekalongan.'),
(5,'Ciri visual Jlamprang adalah...','Figur hewan realistis','Garis diagonal tunggal','Awan bergradasi','Geometris simetris bergaya bintang atau bunga','D','Jlamprang bersifat geometris dan simetris.'),
(5,'Jlamprang termasuk kelompok batik...','Keraton','Dayak','Pesisir','Betawi','C','Jlamprang termasuk batik pesisir Pekalongan.'),
-- 6 Kawung
(6,'Bentuk dasar Kawung adalah...','Lingkaran lonjong tersusun rapi','Segitiga bergerigi','Ombak berlapis','Naga melingkar','A','Kawung berupa lingkaran lonjong yang tersusun rapi.'),
(6,'Kawung dikaitkan dengan buah...','Salak','Mangga','Aren (kolang-kaling)','Durian','C','Bentuk Kawung dikaitkan dengan buah kawung atau aren.'),
(6,'Kawung melambangkan...','Kesucian, keadilan, dan pengendalian diri','Peperangan','Perdagangan laut','Musim hujan','A','Kawung melambangkan kesucian dan keadilan.'),
(6,'Pada masa lalu pemakaian Kawung di keraton...','Dilarang sepenuhnya','Diatur dan dikaitkan dengan bangsawan','Hanya untuk anak-anak','Hanya untuk upacara adat Sunda','B','Pemakaiannya diatur dan dikaitkan dengan bangsawan.'),
-- 7 Liong
(7,'Liong berarti...','Singa','Naga','Burung','Awan','B','Liong berarti naga.'),
(7,'Budaya apa yang memengaruhi Batik Liong?','Dayak','Betawi','Tionghoa','Sunda','C','Liong lahir dari akulturasi budaya Tionghoa.'),
(7,'Naga melambangkan...','Kekuatan, kebaikan, dan keberuntungan','Kesedihan','Kemiskinan','Kesunyian','A','Naga adalah simbol kekuatan dan keberuntungan.'),
(7,'Warna yang lazim menonjol pada Batik Liong adalah...','Putih polos','Merah dan warna cerah lain','Abu-abu saja','Hijau tua saja','B','Batik Liong cenderung cerah dan banyak memakai merah.'),
-- 8 Mega Mendung
(8,'Mega mendung berarti...','Awan mendung','Matahari terbit','Ombak laut','Gunung tinggi','A','Mega berarti awan, mendung berarti gelap.'),
(8,'Mega Mendung berasal dari...','Pekalongan','Jakarta','Cirebon','Yogyakarta','C','Mega Mendung adalah batik khas Cirebon.'),
(8,'Ciri warna Mega Mendung adalah...','Warna acak tanpa pola','Gradasi dalam satu warna','Hanya hitam','Hanya emas','B','Awannya bergradasi dari tua ke muda.'),
(8,'Makna awan mendung adalah...','Pembawa hujan dan kesabaran','Tanda perang','Tanda kesedihan abadi','Kekayaan emas','A','Awan mendung melambangkan pembawa hujan dan kesabaran.'),
-- 9 Parang
(9,'Pola dasar Parang berupa...','Lingkaran lonjong','Rangkaian bunga','Garis diagonal berbentuk S bersambung','Naga melingkar','C','Parang berupa garis diagonal bersambung.'),
(9,'Parang melambangkan...','Semangat pantang menyerah','Kemalasan','Kesedihan','Kekayaan emas','A','Garis yang tak putus melambangkan perjuangan.'),
(9,'Nama Parang dikaitkan dengan...','Gunung','Parang (golok) atau pereng (lereng karang)','Awan','Bunga melati','B','Namanya dikaitkan dengan parang atau pereng.'),
(9,'Pada masa lalu beberapa jenis Parang termasuk pola larangan yang...','Wajib dipakai rakyat','Dipakai hanya saat berkabung','Hanya dipakai raja dan keluarganya','Tidak boleh dipakai pengantin','C','Pola larangan hanya boleh dipakai raja dan keluarganya.'),
-- 10 Sekar Jagad
(10,'Sekar berarti...','Dunia','Bunga','Awan','Gunung','B','Sekar berarti bunga.'),
(10,'Jagad berarti...','Dunia','Laut','Naga','Emas','A','Jagad berarti dunia.'),
(10,'Ciri Sekar Jagad adalah...','Satu motif besar','Garis diagonal tunggal','Banyak ragam hias dalam bidang tidak beraturan','Lingkaran lonjong saja','C','Beragam motif bercampur dalam bidang tidak beraturan.'),
(10,'Sekar Jagad melambangkan...','Perang','Keberagaman dan keindahan dunia','Kesedihan','Kemiskinan','B','Motifnya melambangkan keberagaman dan keindahan dunia.'),
-- 11 Sidoluhur
(11,'Luhur berarti...','Mulia','Makmur','Cepat','Kecil','A','Luhur berarti mulia.'),
(11,'Sido berarti...','Hilang','Menjadi atau terus-menerus','Takut','Pergi','B','Sido berarti menjadi atau terus-menerus.'),
(11,'Motif keluarga Sido lazim dipakai pada...','Pemakaman','Pertandingan','Pernikahan adat Jawa','Panen padi','C','Keluarga Sido lazim dipakai dalam pernikahan.'),
(11,'Harapan pada Sidoluhur adalah...','Berbudi luhur','Cepat kaya','Bepergian jauh','Memenangkan perang','A','Sidoluhur berisi harapan berbudi luhur.'),
-- 12 Sidomukti
(12,'Mukti berarti...','Mulia','Makmur dan sejahtera','Cepat','Tinggi','B','Mukti berarti makmur dan sejahtera.'),
(12,'Sidomukti berisi harapan agar pemakainya...','Hidup makmur dan sejahtera','Selalu bepergian','Selalu bersedih','Tidak menikah','A','Sidomukti mengandung harapan hidup makmur.'),
(12,'Sidomukti termasuk keluarga motif...','Parang','Kawung','Sido','Liong','C','Sidomukti termasuk keluarga Sido.'),
(12,'Motif Sidomukti lazim dipakai saat...','Pernikahan adat Jawa','Berkabung','Menanam padi','Berperang','A','Motif ini lazim dipakai pengantin.'),
-- 13 Sidomulyo
(13,'Mulyo berarti...','Mulia dan sejahtera','Kecil','Cepat','Gelap','A','Mulyo berarti mulia dan sejahtera.'),
(13,'Sidomulyo berisi harapan agar pemakainya...','Menjalani hidup mulia dan terhormat','Selalu bepergian','Tidak bekerja','Bersedih','A','Sidomulyo berisi harapan hidup mulia dan terhormat.'),
(13,'Sidomulyo termasuk keluarga motif...','Kawung','Liong','Sido','Dayak','C','Sidomulyo termasuk keluarga Sido.'),
(13,'Apa yang membantu membedakan Sidomulyo dengan Sidomukti?','Hanya jumlah warna','Nama motif dan konteks pemakaian','Ukuran kain','Tidak ada','B','Karena mirip, nama motif membantu membedakannya.'),
-- 14 Singa Barong
(14,'Motif Singa Barong berasal dari...','Cirebon','Pekalongan','Jakarta','Kalimantan','A','Singa Barong terinspirasi keraton Cirebon.'),
(14,'Motif ini terinspirasi...','Kereta Singa Barong','Candi Borobudur','Kapal pinisi','Rumah gadang','A','Terinspirasi Kereta Singa Barong keraton Cirebon.'),
(14,'Wujud Singa Barong umumnya memadukan...','Hanya unsur Jawa','Belalai gajah, kepala naga, dan sayap buraq','Hanya burung','Hanya singa','B','Gabungan unsur India, Tionghoa, dan Islam.'),
(14,'Singa Barong menjadi simbol...','Kemiskinan','Perdagangan beras','Akulturasi budaya serta kekuatan dan keberanian','Kesunyian','C','Gabungan unsur budaya melambangkan akulturasi dan kekuatan.'),
-- 15 Srikaton
(15,'Sri pada Srikaton dapat dibaca sebagai...','Kemakmuran dan keagungan','Perang','Kemiskinan','Perjalanan','A','Sri berarti kemakmuran atau keagungan.'),
(15,'Katon berarti...','Hilang','Tampak','Tinggi','Dalam','B','Katon berarti tampak.'),
(15,'Srikaton melambangkan harapan agar pemakainya...','Tampak berseri dan berwibawa','Selalu bersembunyi','Selalu bepergian','Tidak bekerja','A','Srikaton berisi harapan berseri dan berwibawa.'),
(15,'Motif Srikaton termasuk kelompok batik...','Dayak','Betawi','Tradisional Jawa','Modern Eropa','C','Srikaton termasuk batik tradisional Jawa.'),
-- 16 Tribusono
(16,'Tri pada Tribusono berarti...','Dua','Tiga','Empat','Lima','B','Tri berarti tiga.'),
(16,'Busono dapat diartikan sebagai...','Busana (pakaian)','Gunung','Laut','Awan','A','Busono dapat diartikan busana.'),
(16,'Tribusono termasuk kelompok batik...','Dayak','Tradisional Jawa','Betawi','Eropa','B','Tribusono adalah motif tradisional Jawa.'),
(16,'Untuk membedakan Tribusono dari motif Jawa lain, yang membantu adalah...','Nama motif sebagai petunjuk tambahan','Ukuran kain','Harga kain','Jenis benang','A','Pola mirip, sehingga nama motif membantu.'),
-- 17 Tujuh Rupa
(17,'Batik Tujuh Rupa berasal dari...','Pekalongan','Cirebon','Jakarta','Yogyakarta','A','Tujuh Rupa adalah batik pesisir Pekalongan.'),
(17,'Nama Tujuh Rupa dikaitkan dengan...','Tujuh hewan','Tujuh gunung','Banyaknya warna','Tujuh candi','C','Namanya dikaitkan dengan banyaknya warna.'),
(17,'Motif yang dominan pada Tujuh Rupa adalah...','Garis diagonal','Bunga, burung, dan kupu-kupu','Naga','Awan bergradasi','B','Motifnya didominasi flora dan fauna meriah.'),
(17,'Gaya Tujuh Rupa dipengaruhi pertemuan budaya...','Jawa, Tionghoa, dan Eropa','Hanya Dayak','Hanya Arab','Hanya Betawi','A','Dipengaruhi budaya Jawa, Tionghoa, dan Eropa.'),
-- 19 Wahyu Tumurun
(19,'Wahyu berarti...','Perang','Anugerah ilahi','Gunung','Awan','B','Wahyu berarti anugerah ilahi.'),
(19,'Tumurun berarti...','Naik','Hilang','Turun','Berhenti','C','Tumurun berarti turun.'),
(19,'Unsur yang sering muncul pada motif ini adalah...','Mahkota dan sayap (lar)','Naga','Ondel-ondel','Awan bergradasi','A','Mahkota dan sayap adalah petunjuk utamanya.'),
(19,'Wahyu Tumurun populer untuk...','Pernikahan dan upacara penting','Pemakaman','Panen padi','Berperang','A','Motif ini populer dalam pernikahan dan upacara penting.'),
-- 20 Wirasat
(20,'Wirasat berarti...','Firasat atau pertanda','Gunung','Naga','Bunga','A','Wirasat berarti firasat atau pertanda.'),
(20,'Motif Wirasat dimaknai sebagai...','Pesan, petunjuk, dan harapan','Perang','Perdagangan','Kesedihan','A','Wirasat dimaknai sebagai pesan dan petunjuk.'),
(20,'Wirasat termasuk kelompok batik...','Dayak','Tradisional Jawa','Betawi','Modern Eropa','B','Wirasat adalah motif tradisional Jawa.'),
(20,'Untuk membedakan Wirasat dari motif Jawa lain, yang membantu adalah...','Ukuran kain','Harga kain','Nama motif sebagai petunjuk tambahan','Jenis benang','C','Pola mirip, sehingga nama motif membantu.')
)
INSERT OR IGNORE INTO quiz_questions (module_id, question, option_a, option_b, option_c, option_d, correct_option, explanation)
SELECT m.id, v.question, v.a, v.b, v.c, v.d, v.correct, v.explanation
FROM v
JOIN modules m ON m.order_no = v.mod
WHERE NOT EXISTS (SELECT 1 FROM quiz_questions q WHERE q.module_id = m.id);

-- 5. Materi lengkap dari aplikasi mobile (modul 6, 8, 9, 18) ------------------
-- Sebelumnya hanya ada hardcode di AppProvider (Dart). Konvensi module_contents:
--   sejarah_filosofi : order 1 = Hakikat & Simbol, 2 = Asal Daerah & Sejarah,
--                      3 = Makna Filosofis, 4 = Penggunaan Tradisional & Pakem
--   karakteristik    : order 1 = ringkasan, 2 = struktur utama, 3 = ornamen, 4 = warna
--                      (badge = label kecil di kartu), 5+ = daftar pakem
-- Modul 9 (Parang) memakai materi Parang Kusumo; modul 18 (Truntum) menggantikan
-- teks lama "Tuntrum/tentrem" yang berupa tebakan nama.
WITH v(mod, pillar, order_no, title, body, badge) AS (VALUES
(9,'sejarah_filosofi',1,'Hakikat & Simbol','Motif Parang Kusumo memancarkan ritme visual diagonal yang merepresentasikan deburan ombak Samudra Hindia yang tiada henti menghantam tebing karang terjal. Garis meliuk tanpa putus mencerminkan laku prihatin, kesinambungan budi pekerti luhur, dan ketabahan batin manusia Jawa dalam mengarungi pasang surut gelombang kehidupan tanpa pernah kehilangan kehormatan martabatnya.',NULL),
(9,'sejarah_filosofi',2,'Asal Daerah & Sejarah','Diciptakan pada era Panembahan Senopati (pendiri Kesultanan Mataram Islam) saat melakukan semedi meditasi di pesisir tebing Parangtritis. Gerak dinamis air laut yang tak kenal menyerah mengilhami terciptanya garis diagonal sakral ini.',NULL),
(9,'sejarah_filosofi',3,'Makna Filosofis Simbolik','Berasal dari kata Parang (batu karang/lereng terjal) dan Kusumo (bunga bangsawan). Motif ini memuat amanah luhur bahwa keturunan ningrat sejati wajib mengharumkan nama bangsa laksana bunga mekar dengan ketegaran jiwa sekeras batu karang.',NULL),
(9,'sejarah_filosofi',4,'Penggunaan Tradisional & Pakem','Tergolong sebagai batik larangan sakral (awisan dalem). Dahulu kala hanya boleh dikenakan keluarga sentana dalem keraton pada upacara tukar cincin pernikahan adat dan pisowanan agung menghadap Sri Sultan atau Sunan.',NULL),
(9,'karakteristik',1,'Anatomi Visual','Kenali struktur anatomi visual dan ornamen pakem yang membedakan Parang Kusumo dari ragam parang lainnya dalam tradisi keraton Mataram.',NULL),
(9,'karakteristik',2,'Jejak Lilin Malam Alami','Tetesan canting membentuk kontur lereng ombak tanpa henti','Struktur Utama • 45° Lereng'),
(9,'karakteristik',3,'Ornamen Mlinjon & Lidah Api','Tekstur belah ketupat mini pengisi ruang kosong motif.','Isen-Isen Halus'),
(9,'karakteristik',4,'Warna Khas Sogan','Paduan soga tua, oker kuning, dan krem mori murni.','Pewarna Alami'),
(9,'karakteristik',5,'Sudut Kemiringan 45°','Garis lereng sejajar membentang miring 45 derajat tanpa terputus, melambangkan kontinuitas tekad ksatria Jawa.',NULL),
(9,'karakteristik',6,'Ornamen Mlinjon & Lidah Api','Lekukan menyerupai lidah api berulang yang diselingi belah ketupat mikro, memberi keseimbangan ritme dinamis.',NULL),
(9,'karakteristik',7,'Tiga Warna Sakral Sogan','Didominasi warna cokelat soga tua (soga jambal), kuning oker keemasan (kayu tegeran), dan dasar putih gading mori prima.',NULL),
(9,'karakteristik',8,'Dimensi Khusus Ningrat','Ukuran lidah parang berkisar 3-4 cm, dikhususkan bagi bangsawan dan keturunan keraton Mataram.',NULL),
(8,'sejarah_filosofi',1,'Hakikat & Simbol','Motif Megamendung melambangkan awan pembawa hujan sebagai simbol kesuburan dan pemberi kehidupan. Tarikan garis awannya yang tegas mencerminkan maskulinitas, namun tetap luwes membawa kesejukan.',NULL),
(8,'sejarah_filosofi',2,'Asal Daerah & Sejarah','Diciptakan di wilayah pesisir utara Jawa, tepatnya Cirebon. Terinspirasi dari kedatangan bangsa Tiongkok ke wilayah keraton Cirebon pada masa lampau.',NULL),
(8,'sejarah_filosofi',3,'Makna Filosofis Simbolik','Mega berarti awan, dan Mendung berarti cuaca sejuk/menahan amarah. Filosofinya adalah manusia harus bisa meredam amarah (teduh) dalam situasi apa pun.',NULL),
(8,'sejarah_filosofi',4,'Penggunaan Tradisional & Pakem','Dahulu digunakan oleh kalangan keraton Cirebon, kini menjadi motif kebanggaan masyarakat umum baik untuk pakaian formal maupun kasual.',NULL),
(8,'karakteristik',1,'Anatomi Visual','Berbeda dengan parang, Megamendung berfokus pada gradasi warna dan garis lengkung awan yang menyerupai gumpalan memanjang.',NULL),
(8,'karakteristik',2,'Garis Awan Tegas','Lengkungan awan ditarik dengan garis yang tegas dan tidak putus.','Struktur Utama'),
(8,'karakteristik',3,'Bentuk Lonjong/Segitiga','Ujung awan cenderung meruncing membedakannya dengan awan Tiongkok yang bulat.','Ciri Khas Bentuk'),
(8,'karakteristik',4,'Gradasi 7 Warna','Pakem aslinya memiliki 7 gradasi warna dari biru tua hingga biru muda.','Pewarna Pesisir'),
(8,'karakteristik',5,'Gradasi Warna (Ganggeng)','Harus memiliki gradasi warna yang halus, umumnya lebih dari 3 tingkat warna untuk menciptakan efek 3D awan.',NULL),
(8,'karakteristik',6,'Bentuk Runcing','Berbeda dengan motif awan Tiongkok yang membulat, Megamendung memiliki ujung yang agak lancip/runcing.',NULL),
(8,'karakteristik',7,'Arah Horizontal','Bentuk awan membentang secara horizontal, melambangkan kehidupan yang sejajar.',NULL),
(6,'sejarah_filosofi',1,'Hakikat & Simbol','Motif Kawung tersusun dari empat elips geometris simetris yang menyerupai belahan buah kolang-kaling atau kuncup teratai yang merekah. Motif ini mencerminkan pengendalian diri yang teguh, kemurnian hati nurani, dan keadilan pemimpin dalam menaungi rakyatnya.',NULL),
(6,'sejarah_filosofi',2,'Asal Daerah & Sejarah','Diciptakan dan berkembang pesat di lingkungan Keraton Kesultanan Ngayogyakarta Hadiningrat sejak era Mataram Islam pada abad ke-13.',NULL),
(6,'sejarah_filosofi',3,'Makna Filosofis Simbolik','Filosofi empat elips merujuk pada konsep Kiblat Papat Limo Pancer: empat penjuru mata angin dengan satu pusat batin yang menuntun manusia senantiasa eling lan waspada terhadap godaan duniawi.',NULL),
(6,'sejarah_filosofi',4,'Penggunaan Tradisional & Pakem','Termasuk salah satu batik larangan (awisan dalem) yang dahulu hanya boleh dikenakan oleh para pembesar dan abdi dalem keraton sebagai lambang integritas moral.',NULL),
(6,'karakteristik',1,'Anatomi Visual','Pola geometris simetris empat lingkaran lonjong dengan isen titik cecek di poros tengah.',NULL),
(6,'karakteristik',2,'Simetri 4 Elips (Kiblat Papat)','Empat bidang lonjong yang berpotongan secara presisi membentuk lingkaran bunga.','Struktur Utama'),
(6,'karakteristik',3,'Poros Tengah (Pancer)','Titik pusat perpotongan kelopak yang dihiasi isen cecek mikro halus.','Titik Poros'),
(6,'karakteristik',4,'Sogan Klasik & Putih Mori','Warna cokelat alami kulit kayu soga berpadu kontras dengan putih mori lembut.','Pewarna Alami'),
(6,'karakteristik',5,'Proporsi Elips Presisi','Ukuran keempat bidang kelopak harus proporsional dan membentuk sudut 90 derajat yang teratur.',NULL),
(6,'karakteristik',6,'Isen Poros Pancer','Pusat silang harus memiliki titik temu atau cecek penyeimbang ritme ornamen.',NULL),
(6,'karakteristik',7,'Garis Kontur Mulus','Tarikan canting melingkar tanpa patahan tajam untuk menjaga keharmonisan bentuk.',NULL),
(18,'sejarah_filosofi',1,'Hakikat & Simbol','Motif Truntum menampilkan tebaran kuntum bunga melati mikro menyerupai gemintang di langit malam. Diciptakan oleh Kanjeng Ratu Kencana (Permaisuri Pakubuwono III) saat merenung menatap bintang di keheningan malam sembari mencanting untuk menumbuhkan kembali cinta kasih sang Raja.',NULL),
(18,'sejarah_filosofi',2,'Asal Daerah & Sejarah','Diciptakan di lingkungan Keraton Kasunanan Surakarta Hadiningrat pada pertengahan abad ke-18.',NULL),
(18,'sejarah_filosofi',3,'Makna Filosofis Simbolik','Truntum berasal dari kata taruntum yang berarti bersemi atau tumbuh kembali. Mengandung filosofi cinta kasih yang tulus, tanpa pamrih, dan senantiasa mekar abadi sepanjang masa.',NULL),
(18,'sejarah_filosofi',4,'Penggunaan Tradisional & Pakem','Wajib dikenakan oleh orang tua pengantin pada upacara pernikahan adat Jawa, menyimbolkan doa restu agar cinta kedua mempelai selalu bersemi dan mampu menjadi panutan hidup.',NULL),
(18,'karakteristik',1,'Anatomi Visual','Pola repetisi kuntum bunga melati mikro yang tertata rapi di atas latar hitam pekat.',NULL),
(18,'karakteristik',2,'Kuntum Bintang Melati','Motif bunga kecil berbentuk bintang berkelopak mekar teratur di seluruh kain.','Struktur Utama'),
(18,'karakteristik',3,'Cecek Isen Melati','Titik-titik mikro lilin malam yang mengisi bagian dalam kelopak bintang.','Isen Canting Halus'),
(18,'karakteristik',4,'Latar Hitam & Emas Cokelat','Latar hitam pekat menyerupai langit malam berpadu cokelat soga keemasan.','Warna Tradisi'),
(18,'karakteristik',5,'Kerapatan Kuntum Seragam','Jarak antar kuntum bunga terjaga secara konsisten di seluruh bidang kain mori.',NULL),
(18,'karakteristik',6,'Latar Gelap Pekat','Warna dasar harus hitam atau cokelat pekat tanpa corak latar tambahan.',NULL),
(18,'karakteristik',7,'Canting Cecek Halus','Bintik cecek mikro pada mahkota melambangkan ketulusan dan kehalusan budi pekerti.',NULL)
)
INSERT INTO module_contents (module_id, pillar, order_no, title, body, badge)
SELECT m.id, v.pillar, v.order_no, v.title, v.body, v.badge
FROM v JOIN modules m ON m.order_no = v.mod;

WITH v(mod, order_no, caption) AS (VALUES
(9,1,'Proses Mencanting'),
(9,2,'Kain Sogan Klasik'),
(9,3,'Jejak Lilin Lereng'),
(9,4,'Detail Isen Canting'),
(8,1,'Proses Pembuatan Pola'),
(8,2,'Gradasi Warna Biru'),
(8,3,'Hasil Akhir Khas Cirebon'),
(6,1,'Sketsa Geometris Kawung'),
(6,2,'Pencantingan Mori Putih'),
(6,3,'Kain Kawung Mataram Sogan'),
(18,1,'Pola Kuntum Bintang'),
(18,2,'Pencelupan Warna Gelap'),
(18,3,'Kain Truntum Pengantin')
)
INSERT INTO module_gallery_images (module_id, image_url, caption, order_no)
SELECT m.id, NULL, v.caption, v.order_no
FROM v JOIN modules m ON m.order_no = v.mod;

UPDATE modules SET video_url = 'https://www.youtube.com/watch?v=iulhQDSIVMQ' WHERE order_no = 9;
UPDATE modules SET video_url = 'https://www.youtube.com/watch?v=wylWYSHkzoQ' WHERE order_no = 8;
UPDATE modules SET cover_image = 'assets/images/batik_kawung.jpg'        WHERE order_no = 6;
UPDATE modules SET cover_image = 'assets/images/batik_mega.jpg'          WHERE order_no = 8;
UPDATE modules SET cover_image = 'assets/images/batik_parang_kusumo.jpg' WHERE order_no = 9;
UPDATE batik_motifs SET thumbnail_url = 'assets/images/batik_kawung.jpg' WHERE slug = 'batik_kawung';
UPDATE batik_motifs SET thumbnail_url = 'assets/images/batik_mega.jpg'   WHERE slug = 'batik_mega_mendung';
UPDATE batik_motifs SET thumbnail_url = 'assets/images/batik_parang.jpg' WHERE slug = 'batik_parang';

-- Soal tambahan modul 9 (kuis Parang Kusumo dari layar kuis app) dan soal baru modul 18.
WITH v(mod, question, a, b, c, d, correct, explanation) AS (VALUES
(9,'Motif Batik Parang Kusumo secara filosofis melambangkan ... yang tidak pernah padam dalam menghadapi ujian hidup.','semangat perjuangan dan keteguhan hati','ketenangan danau keraton yang syahdu','keagungan senjata keris pusaka Mataram','kesuburan tanah dan hasil bumi Nusantara','A','Kata ''Kusumo'' bermakna bunga ksatria. Bentuk lereng miring menyerupai deburan ombak karang laut selatan menggambarkan gelombang tekad pantang menyerah, keteguhan hati, serta budi pekerti luhur ksatria Jawa.'),
(9,'Ciri khas kemiringan garis lereng pada motif Parang Kusumo adalah sebesar ... derajat.','30','45','60','90','B','Kemiringan lereng 45 derajat melambangkan keteguhan arah dan konsistensi jalan hidup seorang ksatria.'),
(9,'Motif Parang Kusumo diciptakan oleh raja Keraton Mataram pada masa pemerintahan ....','Sultan Agung Hanyakrakusuma','Panembahan Senopati','Sri Sultan Hamengkubuwono I','Pakubuwana IV','B','Motif Parang Kusumo digubah oleh Panembahan Senopati saat bertapa di Pantai Parangtritis dan terinspirasi oleh deburan ombak karang.'),
(9,'Ornamen belah ketupat yang mengisi sela-sela lereng motif Parang dikenal dengan nama ....','Cecek','Kaut','Mlinjon','Isen','C','Mlinjon melambangkan senjata perisai atau benteng perlindungan moral dalam menghadapi godaan hidup.'),
(18,'Siapakah yang menciptakan motif Truntum?','Panembahan Senopati','Kanjeng Ratu Kencana, permaisuri Pakubuwono III','Sultan Agung','Pangeran Diponegoro','B','Truntum diciptakan Kanjeng Ratu Kencana saat merenung menatap bintang sambil mencanting untuk menumbuhkan kembali cinta kasih sang Raja.'),
(18,'Kata Truntum berasal dari kata taruntum yang berarti...','Bersemi atau tumbuh kembali','Awan pembawa hujan','Lereng karang','Empat penjuru','A','Truntum bermakna bersemi atau tumbuh kembali, lambang cinta kasih yang tulus tanpa pamrih.'),
(18,'Pada upacara pernikahan adat Jawa, motif Truntum wajib dikenakan oleh...','Pengantin laki-laki','Orang tua pengantin','Para tamu undangan','Juru rias','B','Orang tua pengantin mengenakan Truntum sebagai doa agar cinta kedua mempelai selalu bersemi dan mampu menjadi panutan hidup.'),
(18,'Bagaimana latar warna pakem Truntum?','Putih bersih tanpa warna lain','Hitam atau cokelat pekat tanpa corak latar tambahan','Biru muda bergradasi','Merah menyala','B','Latar gelap pekat menyerupai langit malam, tempat kuntum bintang melati tersebar rapi.')
)
INSERT INTO quiz_questions (module_id, question, option_a, option_b, option_c, option_d, correct_option, explanation)
SELECT m.id, v.question, v.a, v.b, v.c, v.d, v.correct, v.explanation
FROM v JOIN modules m ON m.order_no = v.mod;

COMMIT;
