from rocketry import Rocketry
from rocketry.conds import every, after_success
import json
import shutil
import os
import pandas as pd
from multiprocessing.pool import ThreadPool
from dotenv import load_dotenv

import os
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
import json
import numpy as np

from bson.objectid import ObjectId

from configuration.database import get_database_connection
# SSH tunnel settings
import threading
from time import sleep
from engines.waveform_missing import get_waveform_data
from engines.waveform_missing_end_day import get_waveform_data_end_day

import sys
sys.setrecursionlimit(100000) 

load_dotenv("./.env")

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
seedlink_url = os.getenv('seedlink_url')
regional = os.getenv('regional')
SSH_HOST = os.getenv('ssh_host')
SSH_PORT = int(os.getenv('ssh_port'))
SSH_USERNAME = os.getenv('ssh_username')
SSH_PASSWORD = os.getenv('ssh_password')
MONGO_HOST = os.getenv('database_host')
MONGO_DB = os.getenv('database_name')
LOCAL_BIND_PORT = int(os.getenv('database_port'))
REMOTE_BIND_PORT = int(os.getenv('database_port'))

# Creating the Rocketry app
app = Rocketry(config={"task_execution": "async"})

pool = ThreadPool(10)

# Function to serialize data to JSON format
def json_serializer(data):
    return json.dumps(data).encode('utf-8')
# Initialize a producer

db = get_database_connection(
    SSH_HOST,
    SSH_PORT,
    SSH_USERNAME,
    SSH_PASSWORD,
    MONGO_HOST,
    MONGO_DB,
    LOCAL_BIND_PORT,
    REMOTE_BIND_PORT,

)

def fetch_data(server_fdsn, network, code, channel):
    print(server_fdsn, network, code, channel)
    get_waveform_data(db, server_fdsn, network, code, channel)

# Define a function for processing each row
def process_row(row):
    for channel in row["channel"]:
        fetch_data(row["server_fdsn"], row["network"], row["code"], channel)


# Creating some tasks
@app.task(every("5 seconds"))
async def profile_process():
    global client  # Declare client as global within this function
    try:
        if regional != "":
            db_users = db["user"]
            user_data = db_users.find_one({
                "username": regional  # Assuming "regional" is a variable you defined elsewhere
            })

            # Get FDSN server from config
            server_fdsn = []
            fdsn_id = user_data["modules"].get("fdsn")
            
            if fdsn_id != None:
                db_modules = db["module"]
                fdsn_config = db_modules.find_one(fdsn_id).get("config")
                if fdsn_config != None:
                    server_fdsn = fdsn_config.get("servers", [])

            # Get station data
            station_ids = user_data["stations"]
            db_station = db["station"]

            networks = []
            stations = []
            channels = []
            station_datas = []
            for station_id in station_ids:
                station_data = db_station.find_one({
                    '_id': ObjectId(station_id)
                })
                station_data["server_fdsn"] = server_fdsn
                station_datas.append(station_data)
        else:
            station_datas = db["station"]
        print(station_datas)

        df_database_station = pd.DataFrame.from_dict(station_datas)

        # Convert the list column to a string to make it hashable
        df_database_station['channel'] = df_database_station['channel'].apply(lambda x: str(x))
        df_database_station['server_fdsn'] = df_database_station['server_fdsn'].apply(lambda x: str(x))

        # Now you can drop duplicates
        df_database_station = df_database_station.drop_duplicates()
        # If you need the 'channel' column back as lists, convert it back
        df_database_station['channel'] = df_database_station['channel'].apply(lambda x: eval(x))
        df_database_station['server_fdsn'] = df_database_station['server_fdsn'].apply(lambda x: eval(x))
        
        print(df_database_station)

        # for index, row in df_database_station.iterrows():
        #     for channel in row["channel"]:

        #         print(row["server_fdsn"], row["network"], row["code"], channel)
        #         get_waveform_data(row["server_fdsn"], row["network"], row["code"], channel)

        threads = []
        for index, row in df_database_station.iterrows():
            thread = threading.Thread(target=process_row, args=(row,))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()


        # for fdsn_url in fdsn_urls:
        #         df_database_station_filtered1 = df_database_station[df_database_station["server_fdsn"]==fdsn_url]
        #         networks = df_database_station_filtered1["network"].to_list()
        #         for network in networks:
        #             df_database_station_filtered2 = df_database_station[
        #                 (df_database_station["server_fdsn"]==fdsn_url)&
        #                 (df_database_station["network"]==network)
        #             ]
        #             stations =df_database_station_filtered2["code"].to_list()
        #             print(stations)
        #             for station in stations:
        #                 df_database_station_filtered3= df_database_station[
        #                     (df_database_station["server_fdsn"]==fdsn_url)&
        #                     (df_database_station["network"]==network)&
        #                     (df_database_station["code"]==station)
        #                 ]
        #                 channels = df_database_station_filtered3["channel"].to_list()
        #                 if channels != None:
        #                     if len(channels) > 0:
        #                         channels = channels[0]
        #                     for channel in channels:
        #                         try:
        #                             print(fdsn_url, network, station, channel)
        #                             get_waveform_data(fdsn_url,network, station, channel)
        #                         except Exception as e:
        #                             continue
    except Exception as e:
        print(str(e))



# Creating some tasks
@app.task(every("10800 seconds"))
async def delete_60_days_before():
    try:
        today = date.today()
        for folder in os.listdir("../archive_data"):
            date_format = "%Y-%m-%d"

            # Convert the string to a datetime object
            datetime_obj = datetime.strptime(folder, date_format)
            difference = today - datetime_obj.date()
            days_difference = difference.days
            if days_difference > 60:
                shutil.rmtree("../archive_data/"+str(folder))
    except Exception as e:
        print("delete ", str(e))

# @app.task(every("30 seconds"))
# async def fill_data_from_start_day():
#     global client  # Declare client as global within this function
#     try:
#         if regional != "":
#             db_users = db["user"]
#             user_data = db_users.find_one({
#                 "username": regional  # Assuming "regional" is a variable you defined elsewhere
#             })
#             station_ids = user_data["stations"]
#             db_station = db["station"]

#             networks = []
#             stations = []
#             channels = []
#             station_datas = []
#             for station_id in station_ids:
#                 station_data = db_station.find_one({
#                     '_id': ObjectId(station_id)
#                 })
#                 station_datas.append(station_data)
#         else:
#             station_datas = db["station"]
#         print(station_datas)
#         df_database_station = pd.DataFrame.from_dict(station_datas)

#         # Convert the list column to a string to make it hashable
#         df_database_station['channel'] = df_database_station['channel'].apply(lambda x: str(x))

#         # Now you can drop duplicates
#         df_database_station = df_database_station.drop_duplicates()
        
#         # If you need the 'channel' column back as lists, convert it back
#         df_database_station['channel'] = df_database_station['channel'].apply(lambda x: eval(x))
        
#         print(df_database_station)

#         for index, row in df_database_station.iterrows():
#             for channel in row["channel"]:
#                 print(row["server_fdsn"], row["network"], row["code"], channel)
#                 get_waveform_data_end_day(row["server_fdsn"], row["network"], row["code"], channel)

#     except Exception as e:
#         print(str(e))


# @app.task(every("30 seconds"))
# async def fill_data_to_end_day():
#     try:
#         today = date.today()
#         for folder in os.listdir("../archive_data"):
#             date_format = "%Y-%m-%d"

#             # Convert the string to a datetime object
#             datetime_obj = datetime.strptime(folder, date_format)
#             difference = today - datetime_obj.date()
#             days_difference = difference.days
#             if days_difference > 60:
#                 shutil.rmtree("../archive_data/"+str(folder))
#     except Exception as e:
#         print("delete ", str(e))

if __name__ == "__main__":
    # If this script is run, only Rocketry is run
    
    app.run()

