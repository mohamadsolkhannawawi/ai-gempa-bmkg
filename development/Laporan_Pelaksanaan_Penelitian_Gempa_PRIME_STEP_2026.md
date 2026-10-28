B. Gempa (Solkhan, Rasyid)

a. Activities
Pelaksanaan kegiatan penelitian diawali dengan penyiapan rancangan arsitektur sistem berbasis _event-driven microservices_. Secara umum, konsep arsitektur ini membagi sistem pemrosesan yang besar menjadi modul atau layanan kecil yang mandiri, di mana setiap unit bekerja dan saling berinteraksi berdasarkan sinyal atau kejadian (_event_) yang masuk. Dalam pendekatan ini, setiap layanan bekerja secara otomatis saat menerima masukan data baru, memprosesnya, lalu meneruskan hasilnya ke layanan berikutnya tanpa bergantung pada alur proses terpusat yang kaku. Rancangan ini membuat sistem lebih mudah dipahami serta beban komputasi dapat dibagi secara seimbang tanpa membuat keseluruhan sistem terhenti apabila salah satu layanan mengalami kendala.

Pada tahap awal, kami menguji konektivitas protokol transmisi data seismik _real-time_ SeedLink (SeedLink v3) pada stasiun pengamatan BMKG serta jaringan regional yang terbuka dan dapat diakses secara publik per akhir Agustus 2026. Pengujian dilakukan terhadap 20 stasiun seismik _broadband_ terbuka yang bersumber dari server EarthScope IRIS (`rtserve.earthscope.org:18000`). Seluruh stasiun tersebut mencakup stasiun pengamatan di wilayah Indonesia, yaitu II.KAPI (Kappang/Kendari) dan PS.JAY (Jayapura), stasiun perbatasan Asia Tenggara yang meliputi Singapura (MS.KAPK, MS.BESC, MS.UBIN, MS.NTU), Filipina (IU.DAV), Thailand (TM.SKLT, TM.SRIT, TM.SURA), serta stasiun jejaring perbatasan regional India (IN.PBA) dan Australia (AU.XMI, AU.DRS, AU.DPH, AU.KDU, AU.MTN, AU.COEN, AU.DERBY, AU.ARMA, dan S1.AUNHS). Langkah ini memastikan ketersediaan aliran data seismik _real-time_ untuk kebutuhan analisis selanjutnya.

Selanjutnya, arsitektur sistem dirancang dengan prinsip modularitas agar setiap modul pemrosesan dapat berdiri dan dioperasikan sebagai layanan tersendiri. Melalui prinsip pemisahan fungsi secara mandiri ini, setiap alur pekerjaan dirancang fleksibel sehingga layanan dapat dijalankan secara terpisah sesuai kebutuhan—misalnya hanya mengaktifkan layanan _P-picking_ saja, atau menjalankan layanan pengolahan tertentu secara terisolasi. Selain itu, modularitas ini memungkinkan sistem untuk mengadopsi atau mengganti model komputasi dan kecerdasan buatan apa saja tanpa harus merombak struktur sistem yang ada, sehingga arsitektur menjadi adaptif, terukur, dan mudah dikembangkan lebih lanjut.

b. Propose Model
Pada tahap deteksi fase gelombang seismik (_picking_), kami mengusulkan model berbasis _Convolutional Neural Network_ 1-Dimensi (**CNN-1D**) serta model hibrida **CNN-LSTM**. Model ini bekerja pada rentang data sinyal berdurasi $8\text{ detik}$ ($160\text{ sampel}$ pada frekuensi _sampling_ $20\text{ Hz}$) untuk mengenali pola gelombang primer ($P$), gelombang sekunder ($S$), serta memisahkannya dari derau (_noise_). Sebagai mekanisme validasi deteksi, sistem memadukan model tersebut dengan algoritma **STA/LTA** (_Short-Term Average / Long-Term Average_) dan metode _Akaike Information Criterion_ (**AIC**) untuk memastikan ketepatan waktu tiba fase gelombang. Selain itu, sistem disiapkan agar dapat terhubung dengan model berarsitektur tingkat lanjut seperti **PhaseNet**.

Setelah fase gelombang terdeteksi, tahap asosiasi fase gelombang dilakukan dengan mengelompokkan data dari berbagai stasiun melalui pendekatan spasio-temporal berbasis **DBSCAN** (_Density-Based Spatial Clustering of Applications with Noise_). Metode ini menyatukan fase-fase deteksi berdasarkan keselarasan waktu tiba dan kedekatan lokasi stasiun pengamatan, sehingga peristiwa gempabumi yang nyata dapat dipisahkan secara akurat dari deteksi semu (_spurious picks_). Proses asosiasi ini memastikan hanya sinyal gelombang yang berasal dari satu sumber gempa yang sama yang diteruskan ke tahap kalkulasi parameter.

Selanjutnya, pada tahap penentuan lokasi sumber gempa (hiposenter) dan magnitudo (**LocMag**), kami menggunakan model regresi berbasis jaringan saraf tiruan (_deep neural regression_). Model ini memanfaatkan data gelombang tiga komponen ($Z$, $N$, dan $E$) untuk memperkirakan posisi episenter relatif, kedalaman hiposenter ($Z$), serta estimasi magnitudo momen ($M_w$). Dengan skema ini, parameter utama gempabumi dapat dihitung secara cepat dan otomatis sesaat setelah fase gelombang terasosiasi dengan baik.

c. Data Preprocessing
Tahapan pra-pemrosesan data diawali dengan menerima dan mengurai (_parsing_) paket data seismik format miniSEED dari server SeedLink v3 menjadi deret waktu sinyal digital. Seluruh sinyal gelombang yang masuk kemudian diseragamkan frekuensi _sampling_-nya menjadi $20\text{ Hz}$ agar memiliki resolusi data yang konsisten. Selanjutnya, sinyal dibersihkan dengan menstabilkan garis dasar sinyal serta menyaring frekuensi menggunakan _bandpass filter_ pada rentang $1{,}0\text{ Hz}$ hingga $10{,}0\text{ Hz}$ untuk menghilangkan derau atau getaran lain di luar frekuensi gempa bumi.

Setelah sinyal bersih, sistem menyelaraskan data waktu dari tiga arah komponen ortogonal ($Z$, $N$, dan $E$) berdasarkan stempel waktu standar UTC. Aliran data kontinu ini kemudian dipotong menjadi beberapa rentang durasi sesuai kebutuhan analisis, yaitu rentang $8\text{ detik}$ untuk deteksi fase cepat serta $60$ hingga $300\text{ detik}$ untuk analisis magnitudo. Seluruh data disimpan sementara dalam _buffer_ yang dilengkapi penghapusan otomatis data lama agar penggunaan memori tetap efisien. Terakhir, skala amplitudo sinyal diseragamkan agar data siap diolah oleh model kecerdasan buatan.

Diagram alir tahapan pra-pemrosesan data gelombang seismik disajikan dalam sintaks PlantUML garis lurus ortogonal berikut:

```text
@startuml
skinparam linetype ortho
skinparam nodesep 45
skinparam ranksep 45
skinparam roundcorner 0
skinparam shadowing false
skinparam packageStyle rectangle
skinparam defaultFontName Arial
skinparam defaultFontSize 11
skinparam ArrowFontSize 10
skinparam ArrowColor #2C3E50
skinparam ArrowThickness 1.5

rectangle "1. Ingesti Data Mentah" as STEP1 {
  [Paket MiniSEED 512 Byte\n(Streaming SeedLink v3)] as IN_SEED
}

rectangle "2. Dekompresi & Resampling Sinyal" as STEP2 {
  [Dekompresi & Parsing Metadata\n(Struktur Trace & Stream ObsPy)] as DECODE_MSEED
  [Resampling & Decimation\n(Standardisasi Frekuensi ke 20 Hz)] as RESAMPLE_20HZ
}

rectangle "3. Signal Conditioning & Filtering" as STEP3 {
  [Detrending & Demeaning\n(Koreksi Linear Baseline Drift)] as DETREND
  [Cosine Tapering 5%\n(Peredam Spectral Leakage)] as TAPER
  [Bandpass Filter Butterworth Orde-4\n(Frekuensi 1.0 Hz - 10.0 Hz)] as BANDPASS
}

rectangle "4. Sinkronisasi 3-Komponen (Z, N, E)" as STEP4 {
  [Sinkronisasi Waktu Presisi UTC\n(Penyelarasan Kanal Z, N, E)] as SYNC_3C
}

rectangle "5. Sliding Window & Redis Buffer" as STEP5 {
  [Segmentasi Sliding Window\n(8s / 160 Sampel @ 20 Hz)] as SLIDING_WIN
  [Buffer Redis Streams\n(ai_pick_... | TTL Expire 600s)] as REDIS_BUF
}

rectangle "6. Normalisasi Amplitudo Dinamis" as STEP6 {
  [Penskalaan Amplitudo Lokal\n((x - x0) / 1000)] as NORM_SCALE
}

rectangle "7. Output Tensor Masukan AI" as STEP7 {
  [Tensor 3-Komponen Siap Inferensi\n(Dimensi: 160 x 3 / N x 3)] as OUT_TENSOR
}

IN_SEED --> DECODE_MSEED : Byte Stream
DECODE_MSEED --> RESAMPLE_20HZ : Resampling 20 Hz
RESAMPLE_20HZ --> DETREND : Koreksi Baseline
DETREND --> TAPER : Redam Spectral Leakage
TAPER --> BANDPASS : Redam Noise Frekuensi
BANDPASS --> SYNC_3C : Sinyal Bersih 3 Kanal
SYNC_3C --> SLIDING_WIN : Pembagian Window Waktu
SLIDING_WIN --> REDIS_BUF : Simpan ke Buffer Real-Time
REDIS_BUF --> NORM_SCALE : Fetch Sliding Window
NORM_SCALE --> OUT_TENSOR : Input Tensor ke Model AI
@enduml
```

d. Arsitektur
Arsitektur sistem dirancang berbasis _event-driven_ menggunakan Apache Kafka sebagai pusat pertukaran data (_message broker_). Seluruh modul pemrosesan dan antarmuka pengguna berkomunikasi secara asinkron melalui mekanisme _publish-subscribe_, di mana setiap modul dapat memproduksi (_produce_) atau mengonsumsi (_subscribe_) data topik tertentu sesuai tugasnya. Selain itu, seluruh modul terhubung dengan konfigurasi global (_Universal Subscribe: Config_) untuk memastikan parameter operasional tersinkronisasi secara menyeluruh.

![Diagram Arsitektur Sistem AI-GEMPA Berbasis Event-Driven dan Apache Kafka](path/ke/gambar-arsitektur.png)
*Gambar: Diagram Arsitektur Sistem AI-GEMPA Berbasis Event-Driven dan Apache Kafka.*

Struktur arsitektur sistem terdiri dari beberapa komponen utama:

1. **Record Stream Module**
   Modul ini berfungsi sebagai pintu masuk penerimaan data gelombang seismik (_waveform_) secara kontinu dari sumber eksternal (protokol SeedLink dan FDSN). Di dalamnya, komponen _Record Stream Handler_ menerima aliran gelombang lalu mengirimkannya ke Kafka sebagai `Produce: Waveform`, sekaligus melayani permintaan pengarsipan (`ArchiveRequest`).

2. **Archiving Module**
   Modul pengarsipan yang mengonsumsi data `ArchiveWaveform` dan `ArchiveRequest` dari Kafka. Modul ini bertugas menyimpan rekaman gelombang historis serta mengirimkan kembali data arsip tersebut sebagai `Produce: ArchiveWaveform` ketika dibutuhkan oleh proses analisis lanjutan.

3. **Preprocessing Module**
   Modul pra-pemrosesan yang mengonsumsi aliran data mentah (`Subscribe: Waveform`) dari Kafka. Tugas dan algoritma yang dijalankan pada modul ini meliputi:
   - Pemeriksaan kanal data pasif atau rusak (_Dead Channel checking_).
   - Penyelarasan frekuensi _sampling_ menjadi $20\text{ Hz}$ (_Sampling rate synchronization_).
   - Penyaringan frekuensi menggunakan _bandpass filter_ pada rentang $0{,}1 - 10\text{ Hz}$ (opsional).
   Output hasil pemrosesan dikirimkan kembali ke Kafka sebagai `Produce: PreprocessedWaveform`.

4. **AI Event Detection Module**
   Modul ini bertugas mendeteksi indikasi awal gempa bumi dan didukung oleh _Load Balancer_ untuk menjaga kelancaran pembagian beban kerja. Modul ini mengonsumsi data `Subscribe: PreprocessedWaveform` untuk mengenali fase gelombang awal dengan rincian tugas:
   - Pengelompokan awal fase P ke dalam suatu kejadian (*P picks clustering to event*).
   - Eliminasi deteksi kosong atau palsu (*Eliminate void picks*).
   - Validasi keberadaan fase (*Passing existence picks*).
   Hasil deteksi awal berupa fase P dikirimkan ke Kafka sebagai `Produce: P-Picks`.

5. **AI Phase Association Module**
   Modul ini bertugas mengelompokkan hasil pembacaan fase gelombang dari berbagai stasiun pengamatan dengan dukungan _Load Balancer_. Modul ini mengonsumsi data `Subscribe: Phase P AI-Picks` untuk menyatukan sinyal-sinyal yang saling bersesuaian menjadi kelompok kejadian gempa bumi yang utuh. Hasil pengelompokan ini dikirimkan ke Kafka sebagai `Produce: Cluster`.

6. **AI Phase Picking Module**
   Modul ini bertugas menentukan waktu tiba fase gelombang P dan S secara akurat dengan dukungan _Load Balancer_. Modul ini mengonsumsi data `Subscribe: PreprocessedWaveform`, `Cluster`, dan rekaman arsip `Archived Waveform`. Dengan menerapkan model AI **PhaseNetID**, modul ini menghasilkan penentuan fase gelombang P dan S yang dikirimkan ke Kafka sebagai `Produce: Phase P & S AI-Picks`.

7. **AI Hypocenter and Magnitude Module**
   Modul kalkulasi parameter gempa yang dilengkapi _Load Balancer_. Modul ini menerima masukan berupa waktu tiba fase ($T_p$, $T_s$), koordinat stasiun, fase P dan S terkonfirmasi, serta data gelombang. Menggunakan model AI yang telah dilatih, modul ini menentukan posisi hiposenter (koordinat dan kedalaman) serta estimasi magnitudo gempa, yang kemudian dikirimkan ke Kafka sebagai `Produce: Events`.

8. **Database Module**
   Modul basis data yang mengelola penyimpanan rekaman parameter sistem secara terpusat. Modul ini mengonsumsi berbagai topik hasil analisis (`P-Picks`, `Cluster`, `AI-Picks`, `Events`, serta permintaan `DBRequest`), lalu menyediakan respons data (`DBResponse`) kembali melalui Kafka untuk kebutuhan visualisasi.

9. **Graphical User Interface (GUI)**
   Lapisan antarmuka pengguna grafis yang mengonsumsi data terstruktur dari Kafka untuk menampilkan informasi secara visual dan interaktif dalam beberapa tampilan utama:
   - **Trace View:** Menampilkan rekaman gelombang multi-stasiun dan waktu tiba fase gelombang secara langsung (_real-time_).
   - **Origin Locator View:** Menampilkan visualisasi kalkulasi hiposenter, pembaruan penentuan fase, kurva waktu tempuh (_travel time / Wadati_), serta tabel stasiun pendeteksi.
     
     ![Desain Antarmuka Origin Locator View](path/ke/gui-origin-locator-view.png)
     *Gambar: Desain Antarmuka Origin Locator View untuk Analisis Hiposenter dan Penentuan Fase.*

   - **Map View:** Menampilkan peta interaktif yang memproyeksikan titik stasiun, lokasi episenter gempa, mekanisme fokus (_focal mechanism_), struktur tektonik/sesar, sebaran gunung api, dan batas lempeng.
     
     ![Desain Antarmuka Map View](path/ke/gui-map-view.png)
     *Gambar: Desain Antarmuka Map View untuk Pemantauan Spasial dan Struktur Tektonik.*

   - **Event View:** Menampilkan daftar peristiwa gempa bumi beserta ringkasan parameter (*Event Summary*) seperti magnitudo, kedalaman, dan koordinat.
     
     ![Desain Antarmuka Event View](path/ke/gui-event-view.png)
     *Gambar: Desain Antarmuka Event View untuk Ringkasan Kejadian Gempa Bumi.*

   - **Config View:** Menyediakan antarmuka pengelolaan konfigurasi modul, pengaturan stasiun pengamatan, batas wilayah, serta parameter sistem.

Diagram alur komponen dan pertukaran data berbasis Kafka tersebut disajikan pada diagram berikut:

```text
@startuml
skinparam linetype ortho
skinparam nodesep 40
skinparam ranksep 45
skinparam roundcorner 0
skinparam shadowing false
skinparam packageStyle rectangle
skinparam defaultFontName Arial
skinparam defaultFontSize 11
skinparam ArrowFontSize 10
skinparam ArrowColor #2C3E50
skinparam ArrowThickness 1.5

rectangle "Pusat Pesan Terdistribusi" as BUS {
  queue "Apache Kafka\n(Event Broker)" as KAFKA
}

rectangle "Modul Aliran Data & Pra-Pemrosesan" as INGEST_GRP {
  [Record Stream Module\n(SeedLink & FDSN Handler)] as MOD_STREAM
  [Archiving Module\n(Penyimpanan Gelombang)] as MOD_ARCHIVE
  [Preprocessing Module\n(Dead Channel, Resampling 20Hz, Filter)] as MOD_PREP
}

rectangle "Modul Pemrosesan AI" as AI_GRP {
  [AI Event Detection Module\n(P-Picks Awal)] as MOD_EVENT_DET
  [AI Phase Association Module\n(Pengelompokan Kluster)] as MOD_ASSOC
  [AI Phase Picking Module\n(PhaseNetID: P & S Picks)] as MOD_PHASE_PICK
  [AI Hypocenter & Magnitude Module\n(Estimasi Hiposenter & Magnitudo)] as MOD_LOCMAG
}

rectangle "Penyimpanan & Basis Data" as DB_GRP {
  [Database Module\n(Penyimpanan Data & Parameter)] as MOD_DB
}

rectangle "Antarmuka Pengguna (GUI)" as GUI_GRP {
  [Trace View\n(Visualisasi Gelombang & Picks)] as V_TRACE
  [Origin Locator View\n(Analisis Relokasi Hiposenter)] as V_LOC
  [Map View\n(Peta Seismik, Sesar, & Gunung Api)] as V_MAP
  [Event View\n(Daftar Katalog Gempa)] as V_EVENT
  [Config View\n(Manajemen Konfigurasi Sistem)] as V_CONF
}

MOD_STREAM --> KAFKA : Produce Waveform
KAFKA --> MOD_ARCHIVE : Subscribe ArchiveWaveform / Request
MOD_ARCHIVE --> KAFKA : Produce ArchiveWaveform
KAFKA --> MOD_PREP : Subscribe Waveform
MOD_PREP --> KAFKA : Produce PreprocessedWaveform

KAFKA --> MOD_EVENT_DET : Subscribe PreprocessedWaveform
MOD_EVENT_DET --> KAFKA : Produce P-Picks
KAFKA --> MOD_ASSOC : Subscribe Phase P AI-Picks
MOD_ASSOC --> KAFKA : Produce Cluster
KAFKA --> MOD_PHASE_PICK : Subscribe PreprocessedWaveform, Cluster, Archive
MOD_PHASE_PICK --> KAFKA : Produce Phase P & S AI-Picks
KAFKA --> MOD_LOCMAG : Subscribe AI-Picks, Waveform, Archive
MOD_LOCMAG --> KAFKA : Produce Events

KAFKA --> MOD_DB : Subscribe Picks, Cluster, Events, DBRequest
MOD_DB --> KAFKA : Produce DBResponse

KAFKA --> V_TRACE : Stream Waveform & Picks
KAFKA --> V_LOC : Stream Data Analisis Hiposenter
KAFKA --> V_MAP : Stream Data Spasial, Sesar, & Peringatan
KAFKA --> V_EVENT : Stream Daftar Kejadian Gempa
KAFKA --> V_CONF : Stream & Update Konfigurasi
@enduml
```

e. Result
Pelaksanaan penelitian ini menghasilkan rancangan arsitektur sistem berbasis _event-driven microservices_ yang mampu menerima dan memproses aliran data seismik _real-time_ secara kontinu dari 20 stasiun pengamatan terbuka di wilayah Indonesia dan jaringan regional sekitarnya. Pengujian konektivitas menunjukkan bahwa pengiriman data seismik berjalan dengan lancar tanpa membebani kinerja komputasi secara keseluruhan. Sistem ini juga dirancang modular sehingga setiap fungsi—seperti pendeteksi fase gelombang (_P-picking_) maupun modul lainnya—dapat dioperasikan secara terpisah atau digabungkan sesuai kebutuhan, serta memudahkan penambahan berbagai model kecerdasan buatan di masa mendatang.
