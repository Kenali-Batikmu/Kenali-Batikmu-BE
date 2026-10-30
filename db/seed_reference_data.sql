-- Dibuat oleh scripts/export_reference_seed.py dari assets/database/kenali_batikmu.db
-- Jalankan SETELAH db/schema.sql. Aman dijalankan ulang.

insert into public.batik_motifs (id, name, slug, origin_region, short_description, thumbnail_url, ml_class_index) values
  (1, 'Batik Betawi', 'batik_betawi', 'DKI Jakarta', 'Batik khas Jakarta dengan motif ondel-ondel, Monas, dan flora-fauna lokal yang merekam kehidupan masyarakat Betawi.', null, 0),
  (2, 'Batik Bokor Kencono', 'batik_bokor_kencono', 'Jawa Tengah (Surakarta)', 'Motif bernuansa bokor, wadah berbentuk mangkuk dalam tradisi Jawa, yang melambangkan kemakmuran dan kemuliaan.', null, 1),
  (3, 'Batik Buketan', 'batik_buketan', 'Pekalongan, Jawa Tengah', 'Motif rangkaian bunga seperti karangan (buket) hasil pengaruh selera Eropa pada batik pesisir Pekalongan.', null, 2),
  (4, 'Batik Dayak', 'batik_dayak', 'Kalimantan', 'Batik yang mengangkat ragam hias Dayak seperti burung enggang, pohon hayat, dan sulur bergaya ukiran.', null, 3),
  (5, 'Batik Jlamprang', 'batik_jlamprang', 'Pekalongan, Jawa Tengah', 'Motif geometris simetris bergaya bintang atau bunga yang diduga dipengaruhi kain patola India.', null, 4),
  (6, 'Batik Kawung', 'batik_kawung', 'Yogyakarta dan Surakarta', 'Salah satu motif tertua: lingkaran lonjong tersusun rapi yang melambangkan kesucian dan keadilan.', 'assets/images/batik_kawung.jpg', 5),
  (7, 'Batik Liong', 'batik_liong', 'Pesisir utara Jawa', 'Batik bergambar naga (liong) hasil akulturasi budaya Tionghoa, simbol kekuatan dan keberuntungan.', null, 6),
  (8, 'Batik Mega Mendung', 'batik_mega_mendung', 'Cirebon, Jawa Barat', 'Motif awan bergradasi warna khas Cirebon yang melambangkan kesabaran dan pembawa hujan.', 'assets/images/batik_mega.jpg', 7),
  (9, 'Batik Parang', 'batik_parang', 'Yogyakarta dan Surakarta', 'Motif diagonal berbentuk S bersambung yang melambangkan semangat pantang menyerah.', 'assets/images/batik_parang.jpg', 8),
  (10, 'Batik Sekar Jagad', 'batik_sekarjagad', 'Jawa Tengah dan Yogyakarta', 'Perpaduan beragam ragam hias yang bertebaran, melambangkan keindahan dan keberagaman dunia.', null, 9),
  (11, 'Batik Sidoluhur', 'batik_sidoluhur', 'Surakarta dan Yogyakarta', 'Motif keluarga Sido untuk pernikahan, berisi harapan agar pemakainya menjadi pribadi yang luhur.', null, 10),
  (12, 'Batik Sidomukti', 'batik_sidomukti', 'Surakarta dan Yogyakarta', 'Motif keluarga Sido untuk pernikahan, berisi harapan hidup makmur dan sejahtera.', null, 11),
  (13, 'Batik Sidomulyo', 'batik_sidomulyo', 'Surakarta dan Yogyakarta', 'Motif keluarga Sido untuk pernikahan, berisi harapan hidup mulia dan terhormat.', null, 12),
  (14, 'Batik Singa Barong', 'batik_singa_barong', 'Cirebon, Jawa Barat', 'Motif makhluk mitologis gabungan beberapa unsur budaya, terinspirasi Kereta Singa Barong keraton Cirebon.', null, 13),
  (15, 'Batik Srikaton', 'batik_srikaton', 'Surakarta, Jawa Tengah', 'Motif bermakna keagungan dan kewibawaan, dengan harapan pemakainya tampak berseri dan berwibawa.', null, 14),
  (16, 'Batik Tribusono', 'batik_tribusono', 'Jawa', 'Motif tradisional Jawa dengan nama yang dapat ditafsirkan sebagai tiga busana atau tiga tatanan.', null, 15),
  (17, 'Batik Tujuh Rupa', 'batik_tujuh_rupa', 'Pekalongan, Jawa Tengah', 'Batik pesisir berwarna-warni dengan motif flora, burung, dan kupu-kupu yang sangat meriah.', null, 16),
  (18, 'Batik Truntum', 'batik_tuntrum', 'Surakarta', 'Bintang kasih sayang abadi, lambang cinta tulus yang senantiasa bersemi.', null, 17),
  (19, 'Batik Wahyu Tumurun', 'batik_wahyu_tumurun', 'Surakarta dan Yogyakarta', 'Motif bermakna turunnya wahyu atau anugerah ilahi, populer untuk pernikahan dan upacara penting.', null, 18),
  (20, 'Batik Wirasat', 'batik_wirasat', 'Jawa', 'Motif tradisional Jawa yang namanya bermakna firasat atau pertanda, sarat pesan dan harapan.', null, 19)
on conflict (id) do update set
  name = excluded.name,
  slug = excluded.slug,
  origin_region = excluded.origin_region,
  short_description = excluded.short_description,
  thumbnail_url = excluded.thumbnail_url,
  ml_class_index = excluded.ml_class_index;

insert into public.modules (id, motif_id, title, description, cover_image, video_url, passing_score, order_no) values
  (1, 1, 'Mengenal Batik Betawi', 'Pelajari sejarah, ciri visual, dan ikon Jakarta yang muncul pada Batik Betawi.', null, null, 70, 1),
  (2, 2, 'Mengenal Batik Bokor Kencono', 'Pelajari makna bokor dan kencana serta ciri visual motif Bokor Kencono.', null, null, 70, 2),
  (3, 3, 'Mengenal Batik Buketan', 'Pelajari asal-usul motif karangan bunga dari Pekalongan dan pengaruh Eropanya.', null, null, 70, 3),
  (4, 4, 'Mengenal Batik Dayak', 'Pelajari ragam hias Dayak dan filosofi hubungan manusia dengan alam.', null, null, 70, 4),
  (5, 5, 'Mengenal Batik Jlamprang', 'Pelajari motif geometris Jlamprang dan pengaruh kain patola India.', null, null, 70, 5),
  (6, 6, 'Mengenal Batik Kawung', 'Pelajari motif Kawung, salah satu motif batik tertua, beserta maknanya.', 'assets/images/batik_kawung.jpg', null, 70, 6),
  (7, 7, 'Mengenal Batik Liong', 'Pelajari motif naga pada batik pesisir hasil akulturasi budaya Tionghoa.', null, null, 70, 7),
  (8, 8, 'Mengenal Batik Mega Mendung', 'Pelajari motif awan bergradasi khas Cirebon dan filosofinya.', 'assets/images/batik_mega.jpg', 'https://www.youtube.com/watch?v=wylWYSHkzoQ', 70, 8),
  (9, 9, 'Mengenal Batik Parang', 'Pelajari motif Parang, filosofi perjuangan, dan kedudukannya di keraton.', 'assets/images/batik_parang_kusumo.jpg', 'https://www.youtube.com/watch?v=iulhQDSIVMQ', 70, 9),
  (10, 10, 'Mengenal Batik Sekar Jagad', 'Pelajari motif Sekar Jagad yang memadukan beragam ragam hias.', null, null, 70, 10),
  (11, 11, 'Mengenal Batik Sidoluhur', 'Pelajari makna Sidoluhur dalam keluarga motif Sido untuk pernikahan.', null, null, 70, 11),
  (12, 12, 'Mengenal Batik Sidomukti', 'Pelajari makna Sidomukti dan harapan kemakmuran di dalamnya.', null, null, 70, 12),
  (13, 13, 'Mengenal Batik Sidomulyo', 'Pelajari makna Sidomulyo dan harapan hidup mulia di dalamnya.', null, null, 70, 13),
  (14, 14, 'Mengenal Batik Singa Barong', 'Pelajari motif Singa Barong dan simbol akulturasi budaya Cirebon.', null, null, 70, 14),
  (15, 15, 'Mengenal Batik Srikaton', 'Pelajari makna Srikaton dan simbol keagungan di dalamnya.', null, null, 70, 15),
  (16, 16, 'Mengenal Batik Tribusono', 'Pelajari asal-usul nama dan ciri umum motif Tribusono.', null, null, 70, 16),
  (17, 17, 'Mengenal Batik Tujuh Rupa', 'Pelajari batik pesisir Pekalongan yang kaya warna dan motif flora-fauna.', null, null, 70, 17),
  (18, 18, 'Mengenal Batik Truntum', 'Pola gemintang cinta kasih tulus yang senantiasa bersemi di keheningan malam.', null, null, 70, 18),
  (19, 19, 'Mengenal Batik Wahyu Tumurun', 'Pelajari makna wahyu atau anugerah ilahi pada motif Wahyu Tumurun.', null, null, 70, 19),
  (20, 20, 'Mengenal Batik Wirasat', 'Pelajari asal-usul nama dan makna pertanda pada motif Wirasat.', null, null, 70, 20)
on conflict (id) do update set
  motif_id = excluded.motif_id,
  title = excluded.title,
  description = excluded.description,
  cover_image = excluded.cover_image,
  video_url = excluded.video_url,
  passing_score = excluded.passing_score,
  order_no = excluded.order_no;

