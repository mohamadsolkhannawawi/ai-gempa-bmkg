# Laporan Analisis Infrastruktur Seismologi Operasional: Ketersediaan Layanan SeedLink Publik untuk Stasiun Seismik Wilayah Indonesia

> **Catatan konversi:** Dokumen PDF sumber tidak memuat gambar/ilustrasi, sehingga tidak ada caption gambar yang perlu dicantumkan. Angka superskrip (<sup>n</sup>) merujuk pada nomor di bagian **Karya yang Dikutip** di akhir dokumen. Blok **📝 Catatan Pemahaman** adalah tambahan penjelasan istilah/pokok bahasan, bukan bagian dari materi asli.

---

## Daftar Isi

1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Konteks Geopolitik Data dan Evolusi Infrastruktur InaTEWS](#2-konteks-geopolitik-data-dan-evolusi-infrastruktur-inatews)
   - 2.1 [Pergeseran Kebijakan Redistribusi Data BMKG (Agustus–September 2026)](#21-pergeseran-kebijakan-redistribusi-data-bmkg-agustusseptember-2026)
   - 2.2 [Arsitektur Telemetri InaTEWS dan Restriksi Jaringan Privat](#22-arsitektur-telemetri-inatews-dan-restriksi-jaringan-privat)
3. [Tinjauan Spesifikasi Protokol dan Mekanisme Penelusuran](#3-tinjauan-spesifikasi-protokol-dan-mekanisme-penelusuran)
4. [Hasil Pemetaan Infrastruktur SeedLink Publik](#4-hasil-pemetaan-infrastruktur-seedlink-publik)
5. [Rincian Stasiun Indonesia pada Server Terverifikasi (Status A)](#5-rincian-stasiun-indonesia-pada-server-terverifikasi-status-a)
6. [Diagnosis Kegagalan Akses pada Jaringan Regional dan Tulang Punggung Lainnya](#6-diagnosis-kegagalan-akses-pada-jaringan-regional-dan-tulang-punggung-lainnya)
7. [Penelusuran Alternatif Non-SeedLink untuk Pemrosesan Waktu-Nyata](#7-penelusuran-alternatif-non-seedlink-untuk-pemrosesan-waktu-nyata)
8. [Rekomendasi Bertingkat Penetrasi Sistem Pemantauan](#8-rekomendasi-bertingkat-penetrasi-sistem-pemantauan)
9. [Otomatisasi Penelusuran Klien: Arsitektur Skrip Evaluasi Berbasis Python](#9-otomatisasi-penelusuran-klien-arsitektur-skrip-evaluasi-berbasis-python)
10. [Elemen Ambiguitas dan Daftar Verifikasi Manual Lanjutan](#10-elemen-ambiguitas-dan-daftar-verifikasi-manual-lanjutan)
11. [Karya yang Dikutip](#karya-yang-dikutip)

---

## 1. Ringkasan Eksekutif

Penelusuran mendalam terhadap infrastruktur jaringan seismik global menyimpulkan bahwa saat ini hampir tidak ada server SeedLink publik tanpa kredensial yang menyiarkan data gelombang waktu-nyata (*real-time waveform*) dari stasiun permanen milik institusi nasional Indonesia (jaringan IA) maupun jaringan kerja sama internasional (jaringan GE). Ketiadaan ini bukan merupakan anomali teknis, melainkan akibat langsung dari perubahan kebijakan pembagian data (*data policy*) oleh Badan Meteorologi, Klimatologi, dan Geofisika (BMKG) yang mencabut izin redistribusi publik untuk data tersebut sejak 28 Agustus 2026<sup>1</sup>. Di luar jaringan yang direstriksi tersebut, satu-satunya stasiun permanen kelas observatorium di Indonesia yang masih memancarkan data secara publik adalah stasiun KAPI (Kappang, Sulawesi Selatan) dari jaringan II, yang didistribusikan melalui infrastruktur EarthScope<sup>2,3</sup>. Namun demikian, penelusuran ini menemukan titik terang baru (berstatus terverifikasi) pada jaringan seismologi warga (*citizen science*) GeoShake (kode jaringan GW), yang menyediakan akses SeedLink anonim secara publik melalui titik akhir `seedlink.geoshake.org:18000` untuk wilayah Indonesia<sup>4</sup>.

Untuk memenuhi kebutuhan operasional skala masif di luar sisa stasiun EarthScope dan inisiatif GeoShake, akses terhadap data waktu-nyata stasiun Indonesia kini mutlak mensyaratkan perjanjian bilateral resmi dan pengajuan otorisasi langsung kepada administrator sistem InaTEWS BMKG<sup>1</sup>.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **SeedLink** | Protokol (berbasis TCP) untuk menyiarkan data seismogram secara *real-time* dari server ke klien. Port standarnya **18000**. |
> | **Real-time waveform** | Bentuk gelombang getaran tanah yang dikirim langsung/terus-menerus (bukan arsip masa lalu). |
> | **Jaringan IA** | Kode jaringan seismik nasional Indonesia (milik BMKG). |
> | **Jaringan GE** | Kode jaringan GEOFON (GFZ Jerman) yang bekerja sama dengan BMKG di Indonesia. |
> | **Jaringan II** | Jaringan IRIS/IDA, bagian dari GSN (Global Seismograph Network). |
> | **BMKG** | Badan Meteorologi, Klimatologi, dan Geofisika – otoritas resmi cuaca, iklim, dan gempa di Indonesia. |
> | **EarthScope** | Organisasi AS pengganti IRIS DMC yang mengelola arsip dan layanan data seismik global. |
> | **Citizen science (GeoShake)** | Jaringan sensor seismik milik warga sipil/relawan; kode jaringan **GW**. |
> | **Titik akhir (endpoint)** | Alamat `host:port` tempat suatu layanan dapat diakses. |
> | **Data policy** | Aturan resmi tentang siapa boleh mengakses/menyebarkan data. **Inti bagian ini:** data BMKG tertutup karena kebijakan, bukan karena masalah teknis. |

---

## 2. Konteks Geopolitik Data dan Evolusi Infrastruktur InaTEWS

Untuk memahami mengapa penelusuran terhadap ratusan titik akhir (*endpoint*) server FDSN (*Federation of Digital Broad-Band Seismograph Networks*) di seluruh dunia menghasilkan ketiadaan data dari wilayah Indonesia, diperlukan analisis mendalam terhadap lanskap operasional, arsitektur teknis sistem peringatan dini, serta pergeseran kebijakan tingkat lembaga yang mengatur aliran data tersebut.

> ### 📝 Catatan Pemahaman
> - **FDSN** = federasi internasional jaringan seismograf pita lebar; menetapkan standar format, kode jaringan, dan layanan data (mis. FDSNWS).
> - **Endpoint** = alamat server yang dapat dihubungi untuk meminta data.

### 2.1 Pergeseran Kebijakan Redistribusi Data BMKG (Agustus–September 2026)

Sebuah peristiwa fundamental yang mengubah topologi distribusi data seismik global terjadi pada kuartal ketiga tahun 2026. Berdasarkan catatan operasional dari forum resmi manajemen data Pusat Penelitian Geosains Jerman (GFZ) yang mengelola GEOFON, aliran data dari 20 stasiun kerja sama GEOFON-BMKG di Indonesia (berada di bawah kode jaringan GE) terputus secara tiba-tiba dari layanan publik waktu-nyata (protokol SeedLink) maupun layanan arsip (FDSNWS-Dataselect) terhitung sejak 28 Agustus 2026 pada pukul 04:55 UTC<sup>1</sup>.

Diskusi dan negosiasi intensif tingkat tinggi antara GFZ dan BMKG berlangsung selama beberapa minggu setelah pemutusan tersebut. Pada 24 September 2026, pihak GEOFON merilis pernyataan resmi yang mengonfirmasi bahwa GFZ telah kembali memperoleh akses waktu-nyata terhadap aliran data stasiun kerja sama tersebut, namun dengan satu klausul restriktif yang sangat ketat: akses tersebut secara eksklusif hanya diizinkan untuk penggunaan internal di dalam perimeter jaringan GFZ<sup>1</sup>. GFZ secara eksplisit dilarang melakukan redistribusi gelombang (*waveform redistribution*) kepada pihak ketiga, publik, atau komunitas seismik global lainnya<sup>1</sup>.

Implikasi dari restriksi ini merambat secara berjenjang (*cascading effect*) ke seluruh arsitektur data global. Sebagai salah satu simpul utama (*master node*) dalam jaringan EIDA (*European Integrated Data Archive*), GFZ sebelumnya bertindak sebagai agregator yang mendistribusikan data ke simpul-simpul cermin (*mirror nodes*) lainnya di Eropa seperti ORFEUS, INGV, RESIF, BGR, dan ETHZ<sup>8</sup>. Dengan dicabutnya izin redistribusi publik, konfigurasi filter pada fail `seedlink.cfg` di server induk GFZ dimodifikasi untuk secara proaktif memblokir propagasi stasiun-stasiun BMKG dan jaringan GE di Indonesia ke porta publik 18000. Akibatnya, ketiadaan data ini bersifat sistemik di seluruh ekosistem EIDA<sup>1</sup>.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **GFZ / GEOFON** | GFZ = pusat riset geosains Jerman (Potsdam); GEOFON = program jaringan seismik global yang dikelolanya. |
> | **FDSNWS-Dataselect** | Layanan web (HTTP) untuk mengunduh data gelombang arsip berdasarkan parameter waktu & stasiun. |
> | **UTC** | Waktu universal terkoordinasi (WIB = UTC+7), jadi 04:55 UTC = 11:55 WIB. |
> | **Redistribusi** | Menyebarkan ulang data ke pihak lain. GFZ boleh *memakai* data, tapi *tidak boleh membagikannya*. |
> | **EIDA** | Arsip data seismologi terdistribusi Eropa; terdiri dari banyak node (ORFEUS, INGV, RESIF, BGR, ETHZ, dll). |
> | **Master node & mirror node** | Master node = sumber utama; mirror node = salinan yang mengambil data dari master. Jika master berhenti membagikan, seluruh mirror ikut kosong (*cascading effect*). |
> | **`seedlink.cfg`** | Berkas konfigurasi server SeedLink (SeisComP) yang menentukan stasiun mana yang disiarkan. |
> | **Porta 18000** | Port TCP standar SeedLink. |
> | **Sistemik** | Terjadi di seluruh sistem, bukan hanya satu server. |

### 2.2 Arsitektur Telemetri InaTEWS dan Restriksi Jaringan Privat

Sistem Peringatan Dini Tsunami Indonesia (InaTEWS), yang pertama kali diresmikan pada 11 November 2008 pasca-tsunami Aceh, sangat bergantung pada tulang punggung perangkat lunak SeisComP<sup>10</sup>. Perangkat lunak ini awalnya dikembangkan secara kolaboratif melalui proyek GITEWS (*German-Indonesian Tsunami Early Warning System*) dan telah berevolusi menjadi standar emas operasional seismik global<sup>10</sup>.

Pada topologi internalnya, ratusan stasiun seismometer pita lebar (*broadband*) yang tersebar di seluruh kepulauan Indonesia merekam pergerakan tanah dan memaketkannya ke dalam format Mini-SEED standar sebesar 512 bita per rekaman<sup>3</sup>. Paket-paket data ini kemudian dikirimkan kembali ke Pusat Data BMKG di Jakarta menggunakan kombinasi telemetri satelit VSAT dan jaringan terestrial khusus<sup>10</sup>. Di dalam perimeter fasilitas BMKG, server akuisisi lokal memproses data tersebut menggunakan modul-modul SeisComP dan protokol SeedLink waktu-nyata secara mulus.

Meskipun sistem internal beroperasi secara instan dan tanpa jeda, arsitektur keamanan *firewall* BMKG dikonfigurasi untuk tidak mengekspos layanan SeedLink komersial atau publik tanpa otentikasi. Kueri dari luar jaringan menuju porta TCP standar 18000 di titik-titik ujung BMKG (misalnya pada alamat `geof.bmkg.go.id`) akan selalu mengalami *timeout* atau pemblokiran *routing* jaringan<sup>6</sup>. Secara operasional, akses eksternal hanya dikabulkan melalui mekanisme otorisasi yang sangat diawasi, seperti penyertaan alamat IP pemohon ke dalam daftar putih (*whitelist*) tingkat jaringan, atau penggunaan skema otentikasi kriptografik seperti GPG token dan Json Web Token (JWT) yang diimplementasikan pada FDSNWS<sup>12</sup>. Hal ini mengonfirmasi bahwa pencarian porta SeedLink terbuka pada rentang IP publik institusi negara tersebut adalah langkah yang sia-sia tanpa adanya perjanjian bilateral tertulis.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **InaTEWS** | *Indonesian Tsunami Early Warning System* – sistem peringatan dini tsunami nasional, dioperasikan BMKG. |
> | **GITEWS** | Proyek kerja sama Jerman–Indonesia yang menjadi cikal bakal InaTEWS. |
> | **SeisComP** | Perangkat lunak open-source untuk akuisisi, pemrosesan, dan distribusi data seismik (SeedLink adalah bagian darinya). |
> | **Seismometer broadband** | Sensor getaran tanah yang merekam rentang frekuensi lebar. |
> | **Mini-SEED** | Format standar data deret waktu seismik; satu rekaman (*record*) di sini berukuran 512 byte. |
> | **VSAT** | *Very Small Aperture Terminal* – telemetri via satelit, penting untuk stasiun di pulau terpencil. |
> | **Telemetri** | Pengiriman data pengukuran dari lokasi jauh ke pusat data. |
> | **Firewall** | Sistem keamanan jaringan yang menyaring lalu lintas masuk/keluar. |
> | **Timeout** | Koneksi gagal karena tidak ada balasan dalam batas waktu. |
> | **Whitelist** | Daftar alamat IP yang diizinkan mengakses. |
> | **GPG token & JWT** | Mekanisme otentikasi kriptografik; JWT (JSON Web Token) adalah token digital penanda identitas/izin. |
> | **Perjanjian bilateral** | Kesepakatan resmi antara dua pihak (mis. institusi pemohon dan BMKG). |

---

## 3. Tinjauan Spesifikasi Protokol dan Mekanisme Penelusuran

Dalam mencari residu data atau jalur distribusi alternatif, analisis bergantung pada cara protokol SeedLink itu sendiri dirancang. Protokol SeedLink beroperasi pada lapisan aplikasi di atas protokol TCP/IP, menyediakan koneksi persisten yang tangguh terhadap fluktuasi jaringan melalui mekanisme transfer data berbasis urutan (*sequence number*)<sup>3</sup>. Spesifikasi protokol SeedLink v3 dan draf v4 mendefinisikan fase *handshake* yang diinisiasi oleh klien menggunakan perintah berbasis ASCII (seperti `HELLO`, `INFO STATIONS`, `SELECT`, dan `DATA`)<sup>9,14</sup>.

Metodologi penelusuran yang diimplementasikan dalam laporan ini memanfaatkan kapabilitas *command-line* alat klien SeedLink standar seperti `slinktool`, modul Earthworm `slink2ew`, serta kode sumber pengembangan perpustakaan `libslink`<sup>15,16,17,44</sup>. Investigasi difokuskan pada:

1. Inspeksi metadata registry FDSN dan entri perutean (*routing*) EIDA untuk mencari titik akhir publik yang memiliki riwayat pertukaran data dengan kawasan Asia Tenggara.
2. Analisis forum pengembang SeisComP, catatan rilis (*changelog*) repositori perangkat lunak<sup>13</sup>, dan basis data akademis terkait InaTEWS<sup>10</sup>.
3. Pengujian pasif terhadap konfigurasi alamat `sources.chain.address` yang kerap terekspos secara tidak sengaja dalam repositori kode publik (seperti GitHub) oleh operator stasiun sekunder<sup>9</sup>.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **Lapisan aplikasi di atas TCP/IP** | SeedLink adalah protokol tingkat aplikasi yang memakai koneksi TCP yang andal. |
> | **Koneksi persisten** | Koneksi tetap terbuka untuk streaming terus-menerus. |
> | **Sequence number** | Nomor urut paket; memungkinkan klien melanjutkan dari paket terakhir bila koneksi putus. |
> | **Handshake** | Tahap "berjabat tangan" awal antara klien–server sebelum data mengalir. |
> | **Perintah SeedLink** | `HELLO` (identifikasi server), `INFO STATIONS` (daftar stasiun), `SELECT` (memilih kanal), `DATA` (mulai kirim data). |
> | **slinktool** | Alat baris perintah klien SeedLink (dari IRIS/EarthScope). |
> | **slink2ew** | Modul penghubung SeedLink ke sistem Earthworm. |
> | **libslink** | Pustaka (library) C untuk membuat klien SeedLink. |
> | **Residu data** | Sisa jalur/aliran data yang mungkin masih terbuka. |
> | **sources.chain.address** | Parameter konfigurasi SeisComP yang menunjuk alamat server sumber data. |

---

## 4. Hasil Pemetaan Infrastruktur SeedLink Publik

Setelah memindai seluruh kandidat agregator utama yang melayani protokol SeedLink di tingkat global, analisis merangkum status ketersediaan titik akhir (*endpoint*) yang memiliki relevansi geografis dengan Indonesia.

### Tabel 1. Hasil Evaluasi Kandidat Server SeedLink Global untuk Wilayah Indonesia

| Alamat Host dan Port | Operator Sistem / Jaringan | Jaringan dan Stasiun Wilayah Indonesia yang Diklaim | Status | Bukti Sumber Referensi + Tanggal | Catatan Eksekusi Akses |
|---|---|---|---|---|---|
| `seedlink.geoshake.org:18000` | GeoShake Global Seismic Network | Jaringan GW (Mengagregasi sensor seismik *citizen science* global, termasuk node di Indonesia). | **A** (Terverifikasi) | Rilis API GeoShake (September 2026)<sup>4</sup> | **PUBLIK ANONIM.** Tidak membutuhkan kredensial, kunci API, atau otentikasi TCP. Berfungsi sebagai alternatif terbuka yang jauh lebih unggul daripada jaringan komersial Raspberry Shake (AM). |
| `rtserve.earthscope.org:18000` (atau port 18500 via TLS) | EarthScope (Dahulu IRIS DMC) | Jaringan II (Hanya menyiarkan satu stasiun aktif di Indonesia: II.KAPI / Kappang, Sulawesi Selatan). | **A** (Terverifikasi) | Pengumuman Migrasi EarthScope (Mei 2026)<sup>2</sup> | **PUBLIK.** Server publik beroperasi pada protokol v3 di port 18000 dan v4 terenkripsi TLS di port 18500. Menggunakan standar FDSN Source Identifiers<sup>2</sup>. |
| `geofon.gfz.de:18000` | GEOFON (GFZ Potsdam) | Jaringan GE (Dahulu 20+ stasiun seperti BKB, BKNI, BNDI; saat ini seluruhnya OFFLINE untuk publik). | **C** (Tidak Aktif/Dicabut) | Forum Manajemen Data GEOFON (September 2026)<sup>1</sup> | Redistribusi publik dimatikan secara sepihak oleh GFZ demi menaati mandat pembatasan dari kebijakan data BMKG<sup>1</sup>. Akses publik ditutup permanen. |
| `auspass.edu.au:18000` | AusPass (ANU, Australia) | Jaringan AU dan sekitarnya (Kawasan Australasia). | **B** (Kemungkinan) | FDSN Data Center Registry (September 2026)<sup>20</sup> | Menyediakan FDSNWS-Dataselect yang terverifikasi publik<sup>20</sup>. Keberadaan port SeedLink 18000 yang diparalelkan belum terverifikasi secara definitif memuat stasiun Indonesia bagian timur, namun patut dicoba oleh pengguna. |
| `eida.bgr.de:18000` | BGR (Jerman) | Jaringan EIDA (Mem-mirror sebagian jaringan terbuka global). | **B** (Kemungkinan) | Dokumentasi Teknis BGR/SeisComP<sup>8</sup> | Terbuka untuk koneksi publik. Kueri `slinktool -L` perlu dieksekusi secara manual dari sisi klien untuk memverifikasi ada tidaknya stasiun regional yang beririsan dengan bujur Indonesia (seperti jaringan MY atau SG) yang belum terhapus. |
| `seedlink.resif.fr:18000` | RESIF (Prancis) | Simpul EIDA / Jaringan GEOSCOPE (G). | **B** (Kemungkinan) | Pemetaan Topologi SeisComP | Jaringan GEOSCOPE (misalnya stasiun G.BKNI jika sensor tersebut terpisah dari telemetri GE) mungkin disiarkan. Tidak ada kepastian hingga perintah `INFO STATIONS` dikirim. |
| (Alamat IP Privat/VPN) | CTBTO / IMS | Jaringan hidroakustik dan seismik IMS (misal: stasiun Lembang atau PS21/PS22)<sup>21</sup>. | **C** (Tidak Terbuka untuk Publik) | Laporan CTBTO (2023–2024)<sup>21</sup> | **Sangat restriktif dan tersandir.** Data hanya disalurkan melalui *Virtual Data Exploitation Centre* (vDEC) atau *National Data Centres* (NDCs) yang memegang otorisasi resmi tingkat negara<sup>24</sup>. |
| `rtserve.ou.edu:18000` | Univ. of Oklahoma / USGS | Jaringan tulang punggung ANSS, jaringan OK. | **C** (Tidak Terbukti / Tidak Relevan) | Laporan Jaringan OGS (2019)<sup>27</sup> | Terverifikasi publik<sup>27</sup>, namun arsitektur data dikhususkan untuk melayani peringatan dini lokal Amerika Utara dan stasiun-stasiun NEIC, bukan seismisitas Asia Tenggara. |

> **(Catatan Deskriptif Status:** **A** = Kehadiran stasiun dan port terverifikasi oleh sumber primer; **B** = Eksistensi host port terverifikasi, namun keberadaan stasiun Indonesia di dalamnya membutuhkan kueri teknis langsung; **C** = Ketiadaan data Indonesia atau ketiadaan akses publik terverifikasi secara kuat**).**

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **Sistem grading A/B/C** | **A** = pasti bisa dipakai; **B** = server ada, perlu dicek manual apakah ada stasiun Indonesia; **C** = tidak bisa/tidak relevan. Ini kunci membaca tabel. |
> | **Agregator** | Server yang mengumpulkan dan menyiarkan data dari banyak sumber. |
> | **Raspberry Shake (AM)** | Seismometer murah populer untuk warga; kode jaringan AM. Datanya tidak terbuka bebas via SeedLink publik. |
> | **TLS (port 18500)** | *Transport Layer Security* – enkripsi koneksi; SeedLink v4 di EarthScope memakainya. |
> | **SeedLink v3 vs v4** | v3 = versi lama (tanpa enkripsi, port 18000); v4 = versi baru, buffer lebih dalam & dukungan TLS. |
> | **FDSN Source Identifiers** | Format penamaan sumber data standar FDSN (mis. `FDSN:II_KAPI_00_B_H_Z`). |
> | **Kode stasiun (BKB, BKNI, BNDI)** | Stasiun-stasiun GE di Indonesia (Balikpapan, Bakara/Kota Ni, Banda Neira, dst.). |
> | **AusPass** | Portal data seismologi Australia (ANU). |
> | **IMS / CTBTO** | *International Monitoring System* milik Organisasi Traktat Pelarangan Uji Coba Nuklir; memantau uji coba nuklir. |
> | **vDEC / NDC** | Pusat data resmi untuk akses data IMS (vDEC) dan pusat data nasional negara anggota (NDC). |
> | **VPN** | *Virtual Private Network* – jaringan privat terenkripsi. |
> | **ANSS / NEIC / OGS** | ANSS = jaringan seismik nasional AS; NEIC = pusat informasi gempa USGS; OGS = Oklahoma Geological Survey. |
> | **`slinktool -L`** | Opsi untuk menampilkan daftar stasiun/stream di server. |

---

## 5. Rincian Stasiun Indonesia pada Server Terverifikasi (Status A)

Dengan tereliminasi seluruh simpul utama EIDA dan server BMKG dari daftar layanan publik tanpa kredensial, komunitas penelitian hanya menyisakan dua entitas agregator yang secara nyata mendistribusikan data berkoordinat geografis Indonesia.

### 5.1 Infrastruktur EarthScope (`rtserve.earthscope.org`)

Transisi infrastruktur dari IRIS Data Management Center menuju infrastruktur komputasi awan yang dikelola oleh konsorsium EarthScope secara resmi dilaporkan telah selesai pada bulan Mei 2026<sup>2</sup>. Selain mengubah rekam jejak DNS (*Domain Name System*) dari `rtserve.iris.washington.edu` ke entitas domain baru, pembaruan ini juga membawa transisi arsitektur ke protokol SeedLink versi 4. Protokol terbaru ini menyediakan *buffer* penyimpanan yang jauh lebih dalam untuk memulihkan koneksi klien setelah terjadinya disrupsi jaringan, serta memperkenalkan dukungan enkripsi TLS pada port 18500<sup>2</sup>. Protokol versi 3 yang tidak terenkripsi tetap dipertahankan pada port tradisional 18000 demi kompatibilitas mundur (*backward compatibility*) dengan klien-klien warisan<sup>2</sup>.

Dalam seluruh repositori katalog stasiun yang disiarkan oleh EarthScope, penelusuran ini hanya menemukan satu (1) stasiun permanen kelas observatorium yang tersisa di wilayah Indonesia:

- **Stasiun:** II.KAPI (Kappang, Provinsi Sulawesi Selatan).
- **Saluran Telemetri (*Channels*):** Meliputi serangkaian instrumen tri-aksial (BHZ, BHN, BHE untuk *broadband*, LHZ, LHN, LHE untuk periode panjang, hingga VHZ untuk frekuensi sangat panjang).
- **Status Dependensi:** Stasiun KAPI merupakan bagian integral dari jaringan IDA (*International Deployment of Accelerometers*) yang berkolaborasi langsung di bawah jaringan GSN (*Global Seismograph Network*) berkode II. Fakta bahwa stasiun ini berafiliasi di luar struktur organisasi birokratis langsung BMKG menjadikannya satu-satunya titik pemantauan permanen yang lolos dari pembatasan kebijakan redistribusi Agustus 2026.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **DNS** | Sistem yang menerjemahkan nama domain (mis. `rtserve.earthscope.org`) menjadi alamat IP. |
> | **Backward compatibility** | Sistem baru tetap bisa dipakai oleh klien/versi lama. |
> | **Kode kanal (BHZ, BHN, BHE, LHZ, VHZ)** | Huruf 1 = laju sampling (**B** broadband, **L** long period, **V** very long period); huruf 2 = jenis instrumen (**H** = high-gain seismometer); huruf 3 = arah komponen (**Z** vertikal, **N** utara–selatan, **E** timur–barat). |
> | **Tri-aksial** | Sensor tiga komponen (vertikal + dua horizontal). |
> | **IDA / GSN** | IDA = jaringan sensor global dari Scripps (UCSD); GSN = Global Seismograph Network. Kode jaringan keduanya: **II**. |
> | **KAPI** | Kode stasiun Kappang, Sulawesi Selatan. |

### 5.2 Jaringan Seismologi Warga GeoShake (`seedlink.geoshake.org`)

Dalam ketiadaan jaringan observatorium profesional, kekosongan data mulai diisi oleh jaringan *citizen science*. Meskipun perangkat Raspberry Shake (kode jaringan AM) yang populer secara luas tidak menyediakan antarmuka SeedLink publik tanpa restriksi komersial atau institusional, sebuah inisiatif jaringan global baru bernama GeoShake telah muncul.

Terdaftar secara resmi di dalam direktori data center FDSN pada tanggal 6 September 2026 dengan penanda kode institusi GEOSHAKE (dan kode jaringan seismik GW), sistem ini mengagregasi ribuan perangkat sensor seismik mikrokontroler milik warga sipil di seluruh dunia<sup>4,5</sup>.

- **Aksesibilitas Teknis:** GeoShake menayangkan aliran data secara terbuka, publik, dan anonim tanpa memerlukan kredensial, nama pengguna, kata sandi, maupun token JWT. Klien perangkat lunak seperti ObsPy, jAmaSeis, atau SWARM dapat segera dikonfigurasikan dengan alamat host `seedlink.geoshake.org` dan port TCP 18000<sup>4</sup>.
- **Ketersediaan Stasiun:** Inventarisasi stasiun bersifat dinamis dan bergantung pada ketersediaan daya dan internet dari relawan pemilik perangkat di wilayah Indonesia.
- **Struktur Nomenklatur Saluran (*Stream Naming*):** Karena berorientasi pada kejadian dan amplitudo aktivitas alih-alih data kontinu mentah yang boros pita jaringan (*bandwidth*), SeedLink GeoShake mendistribusikan data menggunakan format khusus. Saluran berakhiran `_LNZ` menyediakan amplop aktivitas getaran (*activity envelopes*) secara konstan, sementara saluran berakhiran `_ENZ` menyiarkan *burst* data gelombang murni saat algoritme deteksi kejadian terpicu secara lokal oleh getaran gempa bumi<sup>4</sup>.

Infrastruktur GeoShake saat ini merepresentasikan jalur paling reliabel bagi peneliti yang tidak terafiliasi dengan lembaga pemerintah untuk mengakses gelombang gempa Indonesia secara *near real-time* (mendekati waktu-nyata) tanpa menempuh proses negosiasi birokrasi.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **Mikrokontroler** | Papan komputer kecil (mis. ESP32/Arduino) yang membaca sensor getaran murah. |
> | **ObsPy** | Pustaka Python untuk pengolahan data seismologi. |
> | **jAmaSeis & SWARM** | Aplikasi penampil seismogram (jAmaSeis dari IRIS; SWARM dari USGS). |
> | **Activity envelope (`_LNZ`)** | "Amplop" amplitudo getaran yang dikirim konstan – ringkas, hemat bandwidth, tidak berisi gelombang penuh. |
> | **Burst data (`_ENZ`)** | Potongan gelombang mentah yang hanya dikirim saat sensor mendeteksi kejadian (event-triggered). |
> | **Near real-time** | Hampir seketika, ada jeda kecil. |
> | **Implikasi praktis** | Data GeoShake **bukan** data kontinu kualitas observatorium; cocok untuk deteksi/pemantauan, kurang untuk riset yang butuh fidelitas tinggi. |

---

## 6. Diagnosis Kegagalan Akses pada Jaringan Regional dan Tulang Punggung Lainnya

Penting untuk mendokumentasikan alasan spesifik mengapa ratusan server operasional lain yang menaungi wilayah atau berdekatan dengan geografi Indonesia tidak dapat dimanfaatkan. Diagnosis yang komprehensif akan mencegah peneliti mengulang pengujian koneksi yang dipastikan berujung pada penolakan akses jaringan (*connection refused*) atau ketiadaan muatan (*no data payload*).

### 6.1 Simpul Terdesentralisasi EIDA (ORFEUS, INGV, LMU, ODC, NOA)

Jaringan EIDA (*European Integrated Data Archive*) dirancang sebagai sistem basis data dan aliran waktu-nyata terdistribusi yang menyinkronkan data antar lembaga geofisika di benua Eropa. Namun, tata kelola data diatur oleh prinsip node utama (*master node*). GFZ Potsdam berfungsi sebagai simpul utama yang bertanggung jawab atas pengelolaan dan pendistribusian jaringan GE (GEOFON) serta bertindak sebagai gerbang agregator eksternal bagi sebagian data jaringan IA milik BMKG<sup>1</sup>.

Ketika instruksi kebijakan pelarangan redistribusi (*redistribution restriction*) diaktifkan pada server induk GFZ pada akhir Agustus dan September 2026, aliran *packet switching* Mini-SEED ke seluruh topologi perutean EIDA secara otomatis terhenti<sup>1</sup>. Akibatnya, server seperti `eida.orfeus-eu.org:18000` dan titik akhir milik INGV (Italia) atau ODC (Belanda) hanya menampilkan katalog stasiun yang kosong apabila kueri ditujukan untuk koordinat Nusantara. Modifikasi berkas `seedlink.ini` di ujung GFZ menjamin bahwa tidak ada kebocoran stasiun Indonesia ke simpul hilir Eropa manapun.

> ### 📝 Catatan Pemahaman
> - **ORFEUS, INGV, LMU, ODC, NOA** = node/lembaga anggota EIDA (Belanda, Italia, Jerman-München, Belanda, Yunani).
> - **Packet switching** = data dikirim dalam paket-paket kecil; di sini paket Mini-SEED berhenti mengalir ke node hilir.
> - **Simpul hilir (downstream)** = node yang menerima data dari node di atasnya (GFZ).
> - **Connection refused vs no data payload** = (1) server menolak koneksi sama sekali; (2) koneksi berhasil tetapi katalog/data kosong.

### 6.2 Organisasi Perjanjian Pelarangan Uji Coba Nuklir Komprehensif (CTBTO)

Jaringan Sistem Pemantauan Internasional (IMS) milik CTBTO memiliki sejumlah instalasi strategis di Indonesia, termasuk stasiun seismik Lembang (LEM) dan stasiun hidroakustik maupun seismik tersertifikasi seperti PS21 dan PS22<sup>21,22</sup>. Meskipun infrastruktur transmisi mereka juga memanfaatkan perangkat lunak SeisComP dan protokol pertukaran waktu-nyata untuk memproses sinyal dengan filter *band-pass* resolusi tinggi<sup>23</sup>, kerahasiaan militer dan geopolitik melarang keras akses publik.

Distribusi data IMS diatur oleh traktat internasional dan hanya disalurkan menggunakan teknologi jaringan privat virtual (VPN) terenkripsi menuju *Virtual Data Exploitation Centre* (vDEC) atau Pusat Data Nasional (NDC) yang ditunjuk oleh negara anggota<sup>24,25,26</sup>. Memindai ketersediaan stasiun ini melalui port publik secara fundamental mustahil karena pemblokiran lalu lintas di level penyedia layanan internet (ISP).

> ### 📝 Catatan Pemahaman
> - **CTBTO** = organisasi pemantau uji coba nuklir; **IMS** = jaringan sensor (seismik, hidroakustik, infrasound, radionuklida).
> - **Hidroakustik** = sensor gelombang suara di dalam laut.
> - **Band-pass filter** = filter yang hanya meloloskan rentang frekuensi tertentu.
> - **ISP** = *Internet Service Provider*.

### 6.3 Negara Tetangga dan Agregator Regional (TMD, PHIVOLCS, MetMalaysia)

Organisasi meteorologi dan seismologi di kawasan Asia Tenggara sesungguhnya merupakan pengguna mahir dari ekosistem perangkat lunak *open-source* geofisika. *Thai Meteorological Department* (TMD), misalnya, mengoperasikan topologi SeisComP3 lengkap dengan perangkat pengumpulan data (*datalogger*), *digitizer*, dan server SeedLink terpusat melalui lapisan transmisi TCP/IP<sup>30</sup>. Institusi seperti PHIVOLCS di Filipina juga mengimplementasikan mekanisme *ring buffer* (kemungkinan memanfaatkan modul `ringserver`) yang secara berkala diarsipkan<sup>31,32</sup>.

Kendala utamanya terletak pada desain topologi keamanan intranet (*intranet security design*). Institusi-institusi regional ini merancang server SeedLink mereka tidak untuk mengabdi sebagai penyiar (*broadcaster*) global seperti EarthScope, melainkan sebagai *message broker* (pialang pesan) internal untuk membunyikan alarm di pusat komando lokal mereka masing-masing. Oleh karena itu, alamat IP dari hostname FQDN mereka, apabila dipindai menggunakan pemindai porta (*port scanner*), akan mengabaikan paket permintaan (SYN packets) pada port 18000 karena ketiadaan rute translasi alamat jaringan (NAT) dari antarmuka luar menuju *demilitarized zone* (DMZ) server SeisComP. Pengambilan data dari negara-negara ini biasanya dikoordinasikan melalui forum tertutup bilateral seperti saluran komunikasi *Association of Southeast Asian Nations* (ASEAN) *Earthquake Information Center* (AEIC) yang di-host oleh BMKG, yang kembali lagi membutuhkan kredensial VPN tertutup<sup>33,34,35</sup>.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **TMD / PHIVOLCS / MetMalaysia** | Lembaga meteorologi/seismologi Thailand, Filipina (vulkanologi & seismologi), dan Malaysia. |
> | **Datalogger & digitizer** | Alat yang mengubah sinyal analog sensor menjadi data digital dan merekamnya. |
> | **Ring buffer / ringserver** | Penyimpanan melingkar (data lama tertimpa data baru); `ringserver` adalah server data seismik ringan. |
> | **Message broker** | Perantara yang meneruskan pesan/data antar sistem internal. |
> | **FQDN** | *Fully Qualified Domain Name* – nama host lengkap. |
> | **SYN packet** | Paket pertama pembuka koneksi TCP; bila diabaikan, koneksi gagal (timeout). |
> | **NAT & DMZ** | NAT = penerjemah alamat jaringan; DMZ = zona jaringan semi-terbuka antara internet dan jaringan internal. |
> | **AEIC** | Pusat informasi gempa ASEAN, di-host BMKG. |

---

## 7. Penelusuran Alternatif Non-SeedLink untuk Pemrosesan Waktu-Nyata

Ketiadaan porta 18000 SeedLink yang terbuka secara publik tidak serta-merta melumpuhkan kapabilitas riset seismologi observasional. Terdapat sejumlah protokol lapisan transpor lain dan antarmuka pemrograman aplikasi (API) arsitektur REST yang mampu mendeliverasi informasi gelombang dan parameter gempa dalam kerangka waktu nyaris seketika (*near real-time*).

### 7.1 Ekstraksi Terukur menggunakan FDSNWS-Dataselect

Berbeda dengan SeedLink yang menyodorkan (*push*) aliran bit berkelanjutan (*streaming*) ke klien, layanan web FDSNWS-Dataselect mengharuskan klien untuk menarik (*pull*) data dalam bentuk kueri HTTP-GET yang berbasis pada parameter temporal dan penamaan (*network, station, location, channel*)<sup>3</sup>.

- **Keunggulan Arsitektural:** Protokol berbasis HTTP/HTTPS (port 80 atau 443) jauh lebih mudah melintasi rute proksi dan proksi terbalik (*reverse proxies*) tingkat korporasi dibandingkan protokol koneksi berstatus ganda yang disesuaikan (*custom stateful*) seperti SeedLink.
- **Risiko Mekanisme Polling:** Memaksa simulasi waktu-nyata dengan membuat skrip yang mengeksekusi kueri dataselect setiap satu detik sekali sangat tidak dianjurkan. Pendekatan ini akan membanjiri sumber RecordStream atau basis data SDSArchive milik institusi pelayan (misalnya `auspass.edu.au` atau BMKG, jika kredensial dimiliki), yang berisiko memicu modul keamanan pembatasan laju (*rate-limiting*) dan memunculkan respons HTTP 503 *Service Unavailable*<sup>12</sup>. FDSNWS-Dataselect secara intrinsik didesain untuk pengunduhan jendela waktu seismogram masa lalu (*archived timeseries window*), bukan penyiaran secara kontinu.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **Push vs Pull** | *Push* (SeedLink): server mengirim terus-menerus. *Pull* (FDSNWS): klien meminta data setiap kali butuh. |
> | **Parameter NSLC** | Network, Station, Location, Channel – empat "alamat" untuk menentukan satu aliran data seismik. |
> | **Polling** | Mengulang permintaan secara berkala untuk meniru real-time; tidak efisien dan dapat membebani server. |
> | **Rate-limiting & HTTP 503** | Pembatasan jumlah permintaan; 503 = layanan sedang tidak tersedia/kewalahan. |
> | **SDSArchive** | *SeisComP Data Structure* – struktur arsip berkas Mini-SEED. |
> | **Reverse proxy** | Server perantara yang meneruskan permintaan ke server di belakangnya. |

### 7.2 Ekosistem Common Acquisition Protocol Server (CAPS)

Dalam lingkungan SeisComP modern, modul pengumpul data yang lebih baru bernama CAPS (dikembangkan oleh Gempa GmbH) telah diintegrasikan, bermula dari rilis tambalan SeisComP 2018.327 patch 4<sup>13</sup>. Plugin `caps_plugin` ini dirancang khusus untuk mengatasi keterbatasan bawaan SeedLink, seperti ketidakmampuannya menangani paket data yang urutan waktunya tidak sinkron atau kedaluwarsa akibat latensi internet (*out-of-order timestamps*). CAPS sangat efisien menangani data yang dihasilkan oleh perangkat-perangkat sensor IoT (*Internet of Things*)<sup>13</sup>. Kendati demikian, layaknya protokol SeedLink, porta CAPS di jaringan BMKG juga tetap dilindungi secara ketat oleh pembatasan *firewall* dan memerlukan otentikasi IP eksplisit dari pihak kementerian terkait.

> ### 📝 Catatan Pemahaman
> - **CAPS** = *Common Acquisition Protocol Server*, alternatif/pelengkap SeedLink dalam SeisComP.
> - **Gempa GmbH** = perusahaan Jerman pengembang dan pemelihara SeisComP.
> - **Out-of-order timestamps** = data tiba tidak berurutan karena latensi jaringan; SeedLink kesulitan menanganinya, CAPS lebih baik.
> - **IoT** = perangkat sensor murah yang terhubung internet (mis. sensor warga).

### 7.3 Konsumsi API JSON dan XML Waktu-Nyata Milik BMKG

Apabila obyektif operasional dari sistem yang Anda rancang bukan untuk memanen gelombang murni (rekaman percepatan kecepatan dalam format SAC/Mini-SEED) melainkan hanya memerlukan penyelesaian parameter sumber episenter secara kilat, BMKG menyelenggarakan titik akhir (*endpoint*) API publik tanpa sandi yang sangat efisien.

- Infrastruktur pelaporan otomatis InaTEWS mengekspor file `autogempa.xml` dan `gempaterkini.json` melalui URL seperti `https://data.bmkg.go.id/DataMKG/TEWS/autogempa.xml` segera sesudah perangkat lunak penyelesaian hiposenter (*hypocenter solver*) berkonvergensi menghasilkan koordinat kejadian<sup>36,37</sup>.
- Data struktural ini telah divalidasi oleh pakar seismik piket dalam hitungan menit pasca-gelombang P primer menghantam stasiun-stasiun terdekat. Ekosistem perangkat lunak sumber terbuka (seperti repositori modul Node.js atau kerangka UI React) jamak memanfaatkan protokol HTTP biasa atau soket web (*WebSocket*) ke agregator lapis kedua (*second-layer aggregators*) untuk menampilkan parameter spasial pada panel monitor (*dashboard*) seketika<sup>18,38</sup>. Ini merupakan substitusi fungsional yang sempurna untuk aplikasi penampil peringatan yang tidak memerlukan fungsi analisis frekuensi gelombang (seperti *Fast Fourier Transform* atau perhitungan magnitudo momentum independen).

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **Waveform vs parameter gempa** | Waveform = rekaman getaran mentah; parameter = hasil olahan (lokasi, magnitudo, kedalaman, waktu). API BMKG hanya memberi yang kedua. |
> | **SAC / Mini-SEED** | Format berkas data gelombang seismik. |
> | **Episenter / hiposenter** | Hiposenter = titik asal gempa di dalam bumi; episenter = proyeksinya di permukaan. |
> | **Hypocenter solver** | Algoritme penentu lokasi gempa dari waktu tiba gelombang di banyak stasiun. |
> | **Gelombang P** | Gelombang primer; gelombang gempa tercepat, tiba lebih dulu. |
> | **Seismolog piket** | Analis yang berjaga untuk memverifikasi hasil otomatis. |
> | **JSON / XML** | Format data terstruktur yang mudah dibaca program. |
> | **WebSocket** | Koneksi dua arah berkelanjutan di atas HTTP untuk pembaruan langsung. |
> | **FFT / magnitudo momentum** | Analisis frekuensi gelombang dan skala ukuran gempa (Mw) – tidak bisa dihitung hanya dari parameter jadi. |

---

## 8. Rekomendasi Bertingkat Penetrasi Sistem Pemantauan

Berdasarkan keseluruhan diagnosis infrastruktur FDSN dan restriksi peraturan pembagian data yang menaungi Kepulauan Nusantara pada kuartal akhir tahun 2026, berikut adalah rekomendasi langkah strategis (*actionable intelligence*) bertingkat untuk membangun stasiun penerimaan akuisisi data seismik di luar yurisdiksi jaringan lokal.

### Rekomendasi Lapis Pertama: Penyiapan Seketika (*Immediate Plug & Play*)

Peneliti direkomendasikan untuk tidak membuang waktu berusaha meretas masuk (*bypass*) konfigurasi jaringan EIDA atau mencari porta bayangan milik GEOFON, melainkan langsung menggunakan titik akses legal terbuka berikut.

1. **Integrasi GeoShake (Jaringan GW):** Konfigurasikan perangkat lunak klien (seperti rutinitas `slinktool`, modul pembaca Antelope, atau rutin skrip ObsPy) menuju ke `seedlink.geoshake.org:18000`<sup>4</sup>. Jalankan pendaftaran stasiun dengan menggunakan teknik penyaringan koordinat geospasial untuk mengekstrak perangkat-perangkat aktif milik sukarelawan *citizen science* yang berada di dalam poligon wilayah Indonesia.
2. **Koneksi Stasiun Referensi EarthScope:** Sambungkan klien menggunakan protokol TCP murni ke `rtserve.earthscope.org:18000` (atau manfaatkan enkripsi keamanan lapisan transpor, TLS, di porta 18500 untuk kepatuhan standar korporat). Gunakan pola pemilih (*wildcard selector*) `II_KAPI` untuk merekam pita lebar resolusi tinggi dari satu-satunya stasiun permanen internasional di Sulawesi Selatan<sup>2</sup>.

### Rekomendasi Lapis Kedua: Evaluasi Pemindaian Ekstensif Berkala

Disarankan agar skrip *cron job* atau monitor pengawas jaringan (seperti Zabbix) yang Anda kelola dijadwalkan secara berkala menguji ketersediaan porta SeedLink 18000 pada alamat host yang "mungkin aktif", khususnya pada:

- `auspass.edu.au:18000` untuk memindai ketersediaan stasiun kolaborasi riset Geoscience Australia (jaringan AU atau S) yang secara geografis kerap memperluas perimeter operasinya hingga batas zona subduksi pertemuan lempeng Eurasia di selatan Indonesia dan Timor Leste<sup>20</sup>.
- `seedlink.resif.fr:18000` (Simpul Prancis dari EIDA), untuk berjaga-jaga apabila jaringan GEOSCOPE (kode jaringan G) tetap disiarkan dari jalur routing alternatif di luar administrasi GFZ.

### Rekomendasi Lapis Ketiga: Pengajuan Hak Akses Otoritas Kenegaraan

Mengingat kekayaan sebaran densitas sensor sesungguhnya mutlak berada di bawah panji InaTEWS, setiap riset struktural, mikrozonasi, maupun inversi tomografi litosfer yang memerlukan fidelitas tinggi diwajibkan melewati jalur birokrasi legalitas (*formal clearance*):

1. **Inisiasi Kontak Lembaga:** Susun surat permohonan akademis resmi atau nota kesepahaman (MoU) bilateral institusi.
2. **Kanal Korespondensi:** Kirimkan surel elektronik menuju meja administrasi Pusat Gempabumi dan Tsunami BMKG dengan alamat `info_inatews@bmkg.go.id`<sup>6</sup> atau `info.geof@bmkg.go.id`<sup>40</sup>.
3. **Prosedur Otorisasi Akses Teknis:** Permintaan data yang disetujui (umumnya diberikan di bawah klasifikasi Layanan Bebas Tarif untuk universitas dan penelitian dasar<sup>6,41</sup>) akan diimplementasikan secara teknis melalui pendaftaran alamat IP publik statis milik server institusi Anda ke dalam *whitelist* dinding api perangkat perutean keras BMKG, atau BMKG mungkin mengeluarkan kredensial token kriptografis JWT untuk digunakan pada titik akses EIDA *authentication scheme* FDSNWS<sup>12</sup>.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **Plug & Play** | Langsung dipakai tanpa proses perizinan. |
> | **Antelope** | Sistem akuisisi/pemrosesan data seismik komersial (BRTT). |
> | **Wildcard selector (`II_KAPI`)** | Pola pemilih pada perintah `SELECT`/opsi `-S` untuk memilih stasiun/kanal tertentu. |
> | **Bounding box / poligon wilayah** | Batas koordinat untuk menyaring stasiun yang berada di Indonesia. |
> | **Cron job & Zabbix** | Cron = penjadwal tugas otomatis di Linux; Zabbix = perangkat lunak pemantau jaringan. |
> | **Zona subduksi** | Tempat satu lempeng menunjam di bawah lempeng lain (sumber utama gempa besar di selatan Indonesia). |
> | **GEOSCOPE (G)** | Jaringan seismik global Prancis. |
> | **Mikrozonasi & inversi tomografi** | Pemetaan respons tanah lokal terhadap gempa; pencitraan struktur bawah permukaan dari data gelombang. |
> | **MoU** | *Memorandum of Understanding* – nota kesepahaman. |
> | **Layanan Bebas Tarif** | Layanan data tanpa biaya (kategori PNBP-0) untuk universitas/penelitian dasar. |
> | **Alur 3 lapis** | Lapis 1: pakai yang sudah terbuka → Lapis 2: pantau berkala yang mungkin aktif → Lapis 3: ajukan izin resmi ke BMKG. |

---

## 9. Otomatisasi Penelusuran Klien: Arsitektur Skrip Evaluasi Berbasis Python

Dalam paradigma komputasi seismologi modern, menguji ketersediaan (*availability*) dan daftar saluran (*stream inventory*) pada puluhan server yang berbeda secara manual melalui antarmuka *telnet* baris-per-baris sangatlah tidak efisien<sup>9</sup>. Untuk mengefisienkan proses audit jaringan, spesifikasi komunikasi XML yang digariskan dalam protokol komunikasi perintah peladen SeedLink (`INFO STATIONS` atau `INFO STREAMS`) dapat diotomatisasikan<sup>15,17</sup>.

Berkat infrastruktur modul `obspy.clients.seedlink` pada pustaka Python, skrip audit proaktif dapat dibangun. Di bawah ini merupakan kerangka kode operasional (*operational code framework*) Python yang dirancang untuk secara simultan menghubungi larik host kandidat, meminta katalog deskriptor XML stasiun dari perangkat lunak pengelola server target, mengekstrak variabel koordinat geolokasi (lintang dan bujur), lalu menyaring (*filter*) hasil tangkapan tersebut secara logis terhadap poligon imajiner kotak pembatas (*Bounding Box*) wilayah Kepulauan Indonesia (Garis lintang -11.5° sampai 6.5°, dan garis bujur 94.5° sampai 141.5°).

**Python**

```python
#!/usr/bin/env python3
"""
SeedLink Public Network Auditor untuk Stasiun Geografis Indonesia
Dependensi Eksternal: pip install obspy
Desain Arsitektur: Menjalankan rutinitas pengujian TCP statis dengan toleransi kegagalan
(fault-tolerance) tinggi
serta ekstraksi parameter XML spesifikasi protokol SeedLink v3/v4 untuk penyaringan geospasial
proaktif.
"""
from obspy.clients.seedlink.basic_client import Client
import xml.etree.ElementTree as ET
import socket
import logging
import sys

# Konfigurasi tingkat verbositas pencatatan log (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Definisi Tabel Kandidat Endpoint FDSN/SeedLink
# Mengombinasikan entitas GeoShake terverifikasi, infrastruktur EarthScope yang bermigrasi,
# dan simpul-simpul eksperimental EIDA yang berpeluang menyimpan residu routing.
SEEDLINK_CANDIDATES = [
    ("seedlink.geoshake.org", 18000),   # Agregator Citizen Science GeoShake (Jaringan GW)
    ("rtserve.earthscope.org", 18000),  # EarthScope Foundation (Infrastruktur Eks-IRIS)
    ("auspass.edu.au", 18000),          # Universitas Nasional Australia (Node AusPass)
    ("seedlink.resif.fr", 18000),       # Simpul EIDA Regional Prancis (Potensi Jaringan GEOSCOPE)
    ("eida.bgr.de", 18000)              # Simpul BGR Jerman (Pemeriksaan Residu Stasiun Asia)
]

# Konstanta Parameter Bounding Box Geografis Indonesia
LAT_MIN, LAT_MAX = -11.5, 6.5
LON_MIN, LON_MAX = 94.5, 141.5
TIMEOUT_SECS = 15.0


def verify_seedlink_inventory(host, port):
    """
    Fungsi inti untuk membentuk koneksi soket, mentransmisikan kueri INFO,
    serta memparsing pohon hierarki XML ke dalam model spasial yang dapat dievaluasi.
    """
    logging.info(f"Menginisialisasi uji sirkuit jaringan TCP ke target {host}:{port} ...")

    # 1. Probing lapisan TCP murni (Mendeteksi anomali pemblokiran firewall secara dini)
    try:
        sock = socket.create_connection((host, port), timeout=TIMEOUT_SECS)
        sock.close()
    except socket.timeout:
        logging.error(f"[{host}:{port}] Gagal: Jaringan mengalami batas waktu tunggu habis (TCP Timeout).")
        return
    except socket.error as e:
        logging.error(f"[{host}:{port}] Gagal: Koneksi ditolak oleh peladen target ({str(e)}).")
        return

    # 2. Handshaking protokol lapisan aplikasi menggunakan spesifikasi klien SeedLink ObsPy
    indonesian_stations = []
    try:
        # Pembangkitan objek Client dengan toleransi putus koneksi yang ketat
        client = Client(host, port, timeout=TIMEOUT_SECS)

        # Eksekusi perintah spesifik 'INFO STATIONS' yang menghasilkan untaian bita format XML
        xml_payload = client.get_info('STATIONS')

        if not xml_payload:
            logging.warning(f"[{host}:{port}] Anomali: Peladen merespons koneksi namun gagal menyajikan metadata XML.")
            return

        # 3. Serialisasi dan Penelusuran Model Pohon DOM XML
        # Standar umum spesifikasi pengembalian SeisComP menyertakan tag <seedlink><station>
        root_element = ET.fromstring(xml_payload)

        for station_node in root_element.findall('.//station'):
            network_code = station_node.get('network', 'UN')
            station_code = station_node.get('name', 'UNKNOWN_STA')
            lat_str = station_node.get('latitude')
            lon_str = station_node.get('longitude')

            # Melewati putaran (bypass) apabila administrator sumber tidak mendefinisikan metadata geolokasi
            if lat_str is None or lon_str is None:
                continue

            try:
                lat = float(lat_str)
                lon = float(lon_str)

                # Evaluasi algoritme penyaringan Bounding Box spasial
                if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                    indonesian_stations.append(
                        f"  -> {network_code}.{station_code} (Lat: {lat:.4f}, Lon: {lon:.4f})"
                    )
            except ValueError:
                # Blok eksekusi menoleransi kesalahan parsing pada tipe data tak-numerik
                continue

    except Exception as e:
        logging.error(f"[{host}:{port}] Eksekusi kueri terganggu oleh galat protokol SeedLink: {str(e)}")
        return

    # 4. Pelaporan Konsolidasi Temuan Auditing
    if indonesian_stations:
        logging.info(f"[{host}:{port}] SUKSES. Mengidentifikasi {len(indonesian_stations)} titik stasiun di radius spasial Indonesia:")
        for record in indonesian_stations:
            print(record)
    else:
        logging.info(f"[{host}:{port}] Peladen SeedLink Dikonfirmasi Aktif, akan tetapi inventaris kosong pada koordinat kueri.")


if __name__ == "__main__":
    print("=" * 80)
    print(" Sistem Ekstraksi Parameter SeedLink Global - Analisis Geografis Otomatis ")
    print("=" * 80)

    for target_host, target_port in SEEDLINK_CANDIDATES:
        verify_seedlink_inventory(target_host, target_port)
        print("-" * 80)

    sys.exit(0)
```

Skrip investigasi terotomatisasi ini menerapkan kerangka *fault-handling* (penanganan kegagalan) yang mumpuni dengan membedakan penolakan rute TCP level-bawah dari masalah *parsing* protokol lapisan XML, selaras dengan spesifikasi perancangan rutin `libslink`<sup>15</sup>. *Timeout* parameter 15 detik diaplikasikan guna menyesuaikan dengan rekomendasi perutean agar tidak menumpuk *zombie processes* pada sistem pengoperasian pusat data<sup>3</sup>.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **Telnet** | Alat koneksi teks manual ke suatu port; SeedLink bisa diuji dengan mengetik perintah ASCII. |
> | **`INFO STATIONS` / `INFO STREAMS`** | Perintah SeedLink yang meminta daftar stasiun / aliran data dalam format XML. |
> | **Alur skrip (4 tahap)** | (1) Uji koneksi TCP → (2) Handshake & `INFO STATIONS` via ObsPy → (3) Parse XML & filter koordinat bounding box → (4) Cetak laporan stasiun Indonesia. |
> | **Bounding box Indonesia** | Lintang −11.5° s.d. 6.5°, bujur 94.5° s.d. 141.5°. Catatan: kotak ini juga mencakup sebagian wilayah negara tetangga. |
> | **XML parsing (ElementTree)** | Membaca struktur XML dan mengambil atribut `network`, `name`, `latitude`, `longitude`. |
> | **Fault tolerance** | Skrip tidak berhenti total bila satu server gagal; error ditangkap (`try/except`) lalu lanjut ke server berikutnya. |
> | **`socket.timeout` vs `socket.error`** | Timeout = tidak ada balasan (kemungkinan firewall DROP); error = koneksi ditolak secara aktif. |
> | **Zombie process** | Proses yang menggantung dan tidak dibersihkan sistem operasi. |

---

## 10. Elemen Ambiguitas dan Daftar Verifikasi Manual Lanjutan

Sebagai penutup rumusan konseptual analisis intelijen operasional jaringan ini, seorang peneliti infrastruktur geofisika wajib mengenali batasan-batasan teknis komputasi ekstraksi data otomatis. Algoritme identifikasi di atas bersifat kokoh, namun beberapa celah topologis dan asersi administratif jaringan tidak dapat diukur secara eksak tanpa audit manual lebih mendalam dari pihak operator jaringan. Aspek-aspek probabilitas marjinal berikut membutuhkan penyelidikan lanjutan melalui terminal baris perintah di pihak Anda:

1. **Topologi Perutean Bayangan Jaringan Regional (MY, SG, PS) pada Simpul GFZ/EarthScope**
   Di kala aliran BMKG diputus dari redistribusi publik secara legal pasca-September 2026, hal tersebut belum tentu berimbas seketika pada jaringan kenegaraan sekunder di ASEAN yang tidak terikat perjanjian BMKG. Stasiun meteorologi milik Jabatan Meteorologi Malaysia di wilayah Sabah dan Sarawak (jaringan MY), atau stasiun monitoring Institut Vulkanologi Filipina (PHIVOLCS, jaringan PS) yang secara geografis berada sedikit di utara pulau Kalimantan dan Sulawesi (tumpang tindih dengan koordinat poligon kotak pembatas utara Indonesia), dapat saja masih menumpang aliran siar terbuka (*public broadcast*) agregator internasional. Menjalankan kueri manual terisolasi pada `slinktool -L geofon.gfz.de:18000 | grep ' MY '` mungkin secara tak terduga menghasilkan rekaman anomali *broadband* stasiun asing di wilayah perbatasan Indonesia<sup>9</sup>.

2. **Deteksi Parameter Protokol Peladen AusPass (`auspass.edu.au`)**
   Tinjauan literatur FDSN memvalidasi peresmian rute HTTP `fdsnws-dataselect` pada jaringan komputasi Geoscience Australia<sup>20</sup>, namun kelalaian pemutakhiran registri FDSN bisa berarti eksistensi porta 18000 lama milik server SeedLink tidak terpublikasikan secara tekstual namun faktual masih membisu beroperasi di ruang (*socket space*) alamat IP yang sama<sup>9</sup>. Investigasi soket telnet dengan melakukan *ping* jaringan mentah dan kueri koneksi `HELLO` manual akan secara absolut memastikan hal ini<sup>9</sup>.

3. **Operasional Ekspedisi Seismologi Temporer (Jaringan Z, X, Y)**
   Seismologi lapangan sangat lekat dengan penempatan larik sensor sementara yang didanai melalui skema hibah riset internasional. Organisasi pengarah (*principal investigator*) instrumen biasanya enggan mengintegrasikan sistem pelaporan mereka ke server nasional dan memilih mengarahkan (*beam*) aliran instrumen mereka secara instan menggunakan telemetri seluler *dial-up* langsung menuju basis universitas penyelenggara di Prancis, Jerman, atau Amerika Serikat<sup>43</sup>. Agregator node penelitian universitas, semisal EIDA RESIF di Prancis (`seedlink.resif.fr:18000`), merupakan inkubator tempat munculnya kode jaringan tahunan (contoh: Z3, YF, XT) yang kebetulan melakukan perekaman inversi tomografi selama tiga tahun di Kepulauan Sunda Kecil. Mengevaluasi kueri `INFO STREAMS` dengan perhatian khusus pada konvensi kode non-standar menjadi taktik eksploitasi data yang valid<sup>17</sup>.

4. **Regulasi Frekuensi Komunikasi Pada Koneksi Klien Jangka Panjang**
   Keandalan infrastruktur klien pada server komunitas terbuka seperti `seedlink.geoshake.org` berbanding lurus dengan kejelian konfigurasi parameter waktu-tunggu detak (*keepalive/heartbeat packets*). Untuk menghindari pemutusan koneksi otomatis karena proksi TCP menginterpretasikan aliran diam (*idle timeout*) sebagai anomali, spesifikasi perancangan modul penyambung Earthworm (`slink2ew`) menggarisbawahi bahwa interval transmisi detak wajib berada pada frekuensi di bawah ambang 4 menit (240 detik)<sup>16</sup>. Penyesuaian variabel statis KeepAlive ini di dalam parameter eksekusi perangkat lunak lokal (misalnya pada skrip ObsPy *timeout* parameter atau `slinktool -k 60`<sup>17</sup>) menuntut validasi dan pengaturan iteratif demi mendapatkan jaminan siklus koneksi yang permanen dan nirkekurangan paket data (*zero packet drops*).

Paradigma baru operasional seismologi pasca-kebijakan data geofisika tahun 2026 yang lebih mengisolasi kedaulatan data nasional ini secara alamiah akan menuntun evolusi komunitas dari sekadar bertumpu pada birokrasi server sentral institusi (seperti BMKG) menjadi pemanfaatan gabungan kelenturan hibrida sistem desentralisasi berbasis *crowdsourced data* (GeoShake), dengan agregasi data API analitis HTTP yang secara gesit memberikan wawasan hiposenter (*hypocenter insight*) tanpa membebani protokol jaringan lapisan pita lebar (*broadband layer*) TCP warisan lama.

> ### 📝 Catatan Pemahaman
> | Istilah / Pokok | Penjelasan |
> |---|---|
> | **Kode jaringan MY, SG, PS** | MY = Malaysia, SG = Singapura, PS = PHIVOLCS (Filipina) menurut teks laporan. |
> | **`grep ' MY '`** | Perintah Linux untuk menyaring baris yang memuat kode jaringan MY dari daftar stasiun. |
> | **Jaringan temporer (Z, X, Y)** | Kode jaringan sementara untuk ekspedisi riset; kode tahunan seperti Z3, YF, XT bisa dipakai ulang. Datanya sering dikirim langsung ke universitas penyelenggara. |
> | **Principal investigator (PI)** | Peneliti utama pemilik/penanggung jawab proyek dan data. |
> | **Kepulauan Sunda Kecil** | Rangkaian pulau dari Bali hingga Timor (Nusa Tenggara). |
> | **Keepalive / heartbeat** | Sinyal berkala agar koneksi diam tidak diputus; interval harus < 240 detik. |
> | **`slinktool -k 60`** | Mengatur interval keepalive 60 detik. |
> | **Ambiguitas** | Beberapa temuan (AusPass, RESIF, jaringan MY/PS, jaringan temporer) berstatus "mungkin" dan hanya bisa dipastikan lewat uji manual `HELLO`/`INFO STREAMS`. |
> | **Crowdsourced data** | Data dikumpulkan dari banyak kontributor sukarela (GeoShake). |
> | **Kedaulatan data** | Prinsip bahwa negara mengendalikan penyebaran data yang dihasilkan di wilayahnya. |

---

## Karya yang Dikutip

1. No data for GEOFON stations in Indonesia - News, <https://geofon.gfz.de/forum/t/no-data-for-geofon-stations-in-indonesia/43807>
2. SeedLink service is moving as part of our cloud transition, <https://www.earthscope.org/news/seedlink-service-is-moving-as-part-of-our-cloud-transition/>
3. NGF: SeedLink, <https://ngf.earthscope.org/ds/nodes/dmc/services/seedlink/>
4. Developers — GeoShake Open Data, <https://api.geoshake.org/>
5. Data Center: GEOSHAKE - FDSN, <https://www.fdsn.org/datacenters/detail/GEOSHAKE/>
6. Gempabumi Dirasakan - Stasiun Geofisika Tangerang - BMKG, <https://stageof-tangerang.bmkg.go.id/?page_id=29>
7. BPBD TANGGAMUS, <https://bpbd-tanggamus.blogspot.com/>
8. BGR - Homepage, <https://eida.bgr.de/>
9. seedlink — SeisComP Release documentation, <https://www.seiscomp.de/doc/apps/seedlink.html>
10. 10 Years Indonesian Tsunami Early Warning System - GFZpublic, <https://gfzpublic.gfz.de/pubman/item/item_2431901_18/component/file_2469889/10_years_InaTEWS_2431901.pdf>
11. SMART Subsea Cables for Observing the Earth and Ocean, <https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2021.775544/full>
12. fdsnws — SeisComP Release documentation, <https://www.seiscomp.de/doc/apps/fdsnws.html>
13. CHANGELOG.md · d1fc934dda8280a7b0254340d26c89c7f5c10a2d, <https://git.smp.uprm.edu/Fran89/seiscomp3/-/blob/d1fc934dda8280a7b0254340d26c89c7f5c10a2d/CHANGELOG.md>
14. Protocol — SeedLink - FDSN Documentation, <https://docs.fdsn.org/projects/seedlink/en/latest/protocol.html>
15. DMC: Software: Metadata: Categories: SeedLink Utilities, <https://ngf.earthscope.org/ds/nodes/dmc/software/meta/categories/seedlink-utilities/>
16. NGF: Data Services: Nodes: DMC: Manuals: slink2ew, <https://ngf.earthscope.org/ds/nodes/dmc/manuals/slink2ew/>
17. NGF: Data Services: Nodes: DMC: Manuals: slinktool, <https://ngf.earthscope.org/ds/nodes/dmc/manuals/slinktool/>
18. GitHub - bagusindrayana/ews-concept: EWS (Early Warning System, <https://github.com/bagusindrayana/ews-concept>
19. seedlink-rs/CLAUDE.md at main - GitHub, <https://github.com/luhtfiimanal/seedlink-rs/blob/main/CLAUDE.md>
20. Data Center: AusPass - FDSN, <https://www.fdsn.org/datacenters/detail/AusPass/>
21. 2024 NDC Workshop Agenda Beijing | PDF | Seismology - Scribd, <https://www.scribd.com/document/832559678/Agenda-2024-NDC-Workshop-2>
22. CELEBRATING - CTBTO, <https://www.ctbto.org/sites/default/files/2023-02/ctbto_ar_2021_en.pdf>
23. CTBT: Science and Technology Conference 2023 - SnT2023, <https://conferences.ctbto.org/event/23/timetable/?view=standard>
24. Report of Contributions, <https://conferences-test.ctbto.org/event/15/contributions/contributions.pdf>
25. G7: Goma Volcano Seismic Network - FDSN, <https://www.fdsn.org/networks/detail/G7/>
26. CTBT: Science and Technology Conference 2025 - SnT2025 (8-12, <https://conferences.ctbto.org/event/30/timetable/?print=1&view=standard_numbered>
27. The Oklahoma Geological Survey Statewide Seismic Network, <https://www.ou.edu/content/dam/ogs/documents/information/Walteretal2019_network.pdf>
28. Inatews seismic Network and Data centre Operations Support (2014, <https://www.gfz.de/en/section/seismology/projects/completed-projects/indos-2014-2024>
29. CTBT: Science and Technology Conference 2023 - SnT2023, <https://conferences.ctbto.org/event/23/timetable/?view=standard_numbered_inline_minutes>
30. meteorological department - แผ่นดินไหว - กรมอุตุนิยมวิทยา, <https://earthquake.tmd.go.th/documents/file/seismo-doc-1694575816.pdf>
31. Monitoring of seismic activity in Philippine and Indonesia regions, <https://www2.jpgu.org/meeting/2012/html5/PDF/H-DS06/HDS06-P01_e.pdf>
32. PREPARATORY SURVEY REPORT ON THE PROJECT FOR, <https://openjicareport.jica.go.jp/pdf/12154340_01.pdf>
33. InaTEWS BMKG — Informasi Gempabumi dan Tsunami, <https://inatews.bmkg.go.id/>
34. Gempabumi - StaklimJateng - Stasiun Klimatologi Jawa Tengah, <https://staklim-jateng.bmkg.go.id/gempabumi.php>
35. badan meteorologi, klimatologi, dan geofisika - JDIH BMKG, <https://jdih.bmkg.go.id/storage/common/dokumen/SOP011.pdf>
36. Smart Seismic Intelligence Machine Learning for Spatial Clustering, <https://ejournal.unibabwi.ac.id/index.php/Zetroem/article/download/7615/4705>
37. pemanfaatan application programming interface bmkg sebagai, <https://journal.eng.unila.ac.id/index.php/jitet/article/download/9735/4192>
38. bmkg-api · GitHub Topics, <https://github.com/topics/bmkg-api?l=javascript&o=desc&s=stars>
39. Banjir dan Tanah Longsor di Kabupaten Tanggamus, Akses Jalan, <https://bpbd-tanggamus.blogspot.com/2025/09/banjir-dan-tanah-longsor-di-kabupaten.html>
40. Directory of Geoscience Organizations of the World 2019, <https://www.gsj.jp/information/gsj-link/dir/GSJ_DOC_DGOW_2019.pdf>
41. panduan teknis kesiapsiagaan dan penanggulangan kedaruratan, <https://www.bapeten.go.id/upload/53/2831657f3d-finalpanduan-teknis-kesiapsiagaan-dan-penanggulangan-kedaruratan-transportasi-zrasign.pdf>
42. STRUKTUR KECEPATAN SEISMIK DI BAWAH GUNUNG MERAPI, <https://jrisetgeotam.brin.go.id/index.php/jrisgeotam/article/download/1047/pdf>
43. SeisComP 2.1 User Manual | PDF - Scribd, <https://www.scribd.com/document/45744347/seiscomp-2-1>
44. NGF: Data Services: Nodes: DMC: Software Downloads: libslink, <https://ngf.earthscope.org/ds/nodes/dmc/software/downloads/libslink/>
