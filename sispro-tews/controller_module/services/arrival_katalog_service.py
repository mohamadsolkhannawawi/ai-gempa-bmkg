
from repositories.arrival_katalog_repository import get_arrival_katalog_repo
from utils.util import get_response
import dateutil.parser
from passlib.context import CryptContext
from datetime import datetime, timedelta

from jose import jwt, JWTError
from bson import ObjectId, json_util
from datetime import datetime, timedelta
import json

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import dateutil.parser
import io
import os
import base64
import random
import string
import uuid
# run the following on terminal to generate a secret key
# openssl rand -hex 32
SECRET_KEY = "3e8a3f31aab886f8793176988f8298c9265f84b8388c9fef93635b08951f379b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_arrival_katalog_service(db, origin_id, current_user):
    try:

        arrival_katalog_datas = get_arrival_katalog_repo(db, origin_id)
       
        if len(arrival_katalog_datas)>0:
            arrival_katalog_data = arrival_katalog_datas[0]

            tahun = datetime.now().year  # Ambil tahun saat ini
            random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            public_id = f"bmg{tahun}{random_chars}"

            write_to_txt = f"""Event:
Public ID               {public_id}
Preferred Origin ID     {origin_id}
Preferred Magnitude ID  {str(arrival_katalog_data["magnitudes"][0]["_id"])} 
Description
    region name: {arrival_katalog_data["sub_region"]}, {arrival_katalog_data["region"]}, {arrival_katalog_data["country"]}
Creation Time           {str(arrival_katalog_data["origin_time"]).split(".")[0]}

Origin:
    Public ID              {origin_id}
    Date                   {str(arrival_katalog_data["origin_time"]).split(" ")[0]}
    Time                   {str(arrival_katalog_data["origin_time"]).split(" ")[1]} +/-    0.8 s
    Latitude               {str(arrival_katalog_data["latitude"])} deg  +/-      5 km
    Longitude              {str(arrival_katalog_data["longitude"])} deg  +/-      2 km
    Depth                  {str(arrival_katalog_data["depth"])} km   +/-    6 km
    Agency                 BMKG
    Creation time          {str(arrival_katalog_data["origin_time"]).split(".")[0]} 

{len(arrival_katalog_data["magnitudes"])} Network magnitudes: 
"""
            

            random_id = str(uuid.uuid4())

            # Nama folder tujuan
            temp_folder = "temp"

            # Jika folder temp belum ada, buat foldernya
            if not os.path.exists(temp_folder):
                os.makedirs(temp_folder)

            with open(f"./temp/output_{random_id}.txt", "w") as f:
                # Tulis informasi event dan origin
                f.write(write_to_txt)
                # Tulis header phase arrivals sesuai dengan format yang diinginkan
                row_format = "{type:<4}\t{value:<3}"
                # Loop untuk tiap data arrival
                for magnitude_data in arrival_katalog_data["magnitudes"]:
                    f.write("    "+row_format.format(
                        type=magnitude_data["type"],
                        value=magnitude_data["value"],
                    ) + "\n")
                f.write("\n")
                f.write(f"{len(arrival_katalog_data['arrivals'])} Phase arrivals:   \n")
                
                f.write("    sta\tnet\tphase\ttime   \n")
                row_format = "    {sta:<4}\t{net:<3}\t{phase:<5}\t{time:<20}"
                # Loop untuk tiap data arrival
                for arrival_data in arrival_katalog_data["arrivals"]:
                    f.write(row_format.format(
                        sta=arrival_data["station"]["code"],
                        net=arrival_data["station"]["network"],
                        phase=arrival_data["phase_type"],
                        time=str(arrival_data["timestamp"]),
                    ) + "\n")
                f.write("\n")
                
                if arrival_katalog_data["station_magnitudes_per_type"][0]["station_magnitudes"] != {}:
                    f.write(f"{len(arrival_katalog_data['station_magnitudes_per_type'])} Station magnitudes:   \n\n")

                    f.write("    sta\tnet\ttype\tvalue\ttime   \n")
                    row_format = "    {sta:<4}\t{net:<3}\t{type:<5}\t{value:<5}\t{time:<20}"
                    for station_magnitude_data in arrival_katalog_data["station_magnitudes_per_type"]:
                        if len(station_magnitude_data["station_magnitudes"]) < 1:
                            continue
                        f.write(row_format.format(
                            sta=station_magnitude_data["station_magnitudes"]["station"]["code"],
                            net=station_magnitude_data["station_magnitudes"]["station"]["network"],
                            type=station_magnitude_data["type"],
                            value=station_magnitude_data["station_magnitudes"]["value"],
                            time=str(station_magnitude_data["station_magnitudes"]["created_at"]),
                        ) + "\n")

            with open(f"./temp/output_{random_id}.txt", "rb") as file:
                file_data = file.read()
            encoded_data = base64.b64encode(file_data)

            # Jika ingin menampilkan hasil sebagai string (bukan bytes)
            encoded_string = encoded_data.decode("utf-8")
            arrival_katalog_data_base64 = {
                "file": encoded_string,
            }

            if os.path.exists(f"./temp/output_{random_id}.txt"):
                os.remove(f"./temp/output_{random_id}.txt")

            return get_response(True, "get arrival katalog plot successfully", arrival_katalog_data_base64)
        else:
            return get_response(False, "get arrival katalog plot false", None)

    except Exception as e:
        from traceback import print_exc
        print_exc()
        return get_response(False, "get arrival katalog failed", str(e))
        

