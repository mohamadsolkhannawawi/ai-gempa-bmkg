#!/bin/bash

# Buat direktori sls jika belum ada
mkdir -p sls

# Masuk ke direktori sls
cd sls

# Unzip file seedlink_time_sample.zip
unzip ../seedlink_time_sample.zip

# Kembali ke direktori sebelumnya
cd ..

# Download file dari Google Drive menggunakan gdown
gdown https://drive.google.com/uc?id=1mu-74g_OTlGl9j730iBHRTDPz5HlMTtE
gdown https://drive.google.com/uc?id=1kyjo_YxpodCfF9udnWvGdxhh0XUZQGuD

# Unzip file yang didownload
unzip archive_local_bh.zip
unzip archive_local_sh.zip
