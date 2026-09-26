from rocketry import Rocketry
from rocketry.conds import every, after_success
import json
import redis
import os, time, warnings
import pandas as pd
from multiprocessing.pool import ThreadPool
from dotenv import load_dotenv
import numpy as np
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy import Stream, UTCDateTime
import os
from datetime import date, datetime
from obspy import read
from multiprocessing import Process, set_start_method
from dotenv import load_dotenv
import io
from confluent_kafka import Producer
from bson.objectid import ObjectId
from utils.util import get_gmt_7_time
from utils.util import check_and_make_existing_path
from configuration.database import get_database_connection

# SSH tunnel settings
import threading
from time import sleep
from configuration.redis import publish_redis_message
import asyncio
from multiprocessing import Process, current_process, Manager
from repositories.station_repository import station_find_by_code_and_network_repository
import sys

from seedlink_player_utils import get_started_time, get_trace, get_stream
Delta_T = get_started_time()

import faulthandler
faulthandler.enable()

sys.setrecursionlimit(100000)  # Adjust the recursion limit
load_dotenv("./.env")

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
seedlink_url = os.getenv('seedlink_url')
regional = os.getenv('regional_player')
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

import threading

lock = threading.Lock()

# Create an event to signal when to stop the thread

# Function to serialize data to JSON format
def json_serializer(data):
    return json.dumps(data).encode('utf-8')

def run_client( 
                seedlink_url,
                network,
                station,
                channel):
    client = None
    while True:
        try:
            if seedlink_url=='localhost':
                stid = get_stream()[(network, station, channel+'.D')]
                get_trace(stid, db, producer, Delta_T, NOWTIME=True)
                break
            else:
                pass
        except Exception as e:
            print(f"Client run terminated with exception: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if client != None:
                client.close()
                del client
            print("Client run method exited.")
            import traceback
            traceback.print_exc()
        
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

producer = Producer({
    'bootstrap.servers': kafka_host+":"+kafka_port,})

if os.path.isfile("./data/station.csv") == True:
    os.remove("./data/station.csv")

if os.path.isfile("./data/station_database.csv") == True:
    os.remove("./data/station_database.csv")

client_threads =[]
clients = []
stop_event = threading.Event()

# Creating some tasks
@app.task(every("20 seconds"))
async def profile_process():
    
    # global client_thread
    global clients
    global client_threads
    # global station_total_to_close
    try:
        if regional != "":
            db_users = db["user"]
            user_data = db_users.find_one({
                "username": regional  # Assuming "regional" is a variable you defined elsewhere
            })
            station_ids = user_data["stations"]
            db_station = db["station"]

            station_datas = []
            for station_id in station_ids:
                station_data = db_station.find_one({
                    '_id': ObjectId(station_id)
                })
                station_datas.append(station_data)
        else:
            station_datas = db["station"]

        if not os.path.isfile("./data/station.csv"):    
            print("first pulling station")    

            df_database_station = pd.DataFrame.from_dict(station_datas)
            df_database_station.to_csv("./data/station.csv", index=False)
            print(df_database_station)

            seedlink_urls = df_database_station['server_seedlink'].unique().tolist()
            
            for seedlink_url in seedlink_urls:
                df_database_station_filtered1 = df_database_station[df_database_station["server_seedlink"]==seedlink_url]
                for _, row in df_database_station_filtered1.iterrows():    
                    channels = row["channel"]
                    for channel in channels:
                        client_thread = threading.Thread(
                            target=run_client, 
                            args=(
                                seedlink_url,
                                row["network"], 
                                row["code"], 
                                channel
                            ))
                        client_thread.start()
                        client_thread.join(0)
                        client_threads.append(client_thread)
                print("client for", seedlink_url, "started")
        else:
            df_existing = pd.read_csv("./data/station.csv")

            df_database_station = pd.DataFrame.from_dict(station_datas)
            df_database_station.to_csv("./data/station_database.csv", index=False)
            df_database_station = pd.read_csv("./data/station_database.csv")

            print(df_existing)
            print(df_database_station)

            are_equal = False
            if df_existing.shape == df_database_station.shape:
                for col in df_existing.columns:
                    df_existing[col] = pd.to_numeric(df_existing[col], errors='coerce')
                for col in df_database_station.columns:
                    df_database_station[col] = pd.to_numeric(df_database_station[col], errors='coerce')

                
                are_equal = np.isclose(df_existing.sort_index(axis=1).fillna(0).values, 
                       df_database_station.sort_index(axis=1).fillna(0).values).all()
            else:
                # Handle the case where DataFrames have different shapes
                are_equal = False
            
            print(are_equal)
            
    except Exception as e:
        print("General Error:",e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # If this script is run, only Rocketry is run
    app.run()
