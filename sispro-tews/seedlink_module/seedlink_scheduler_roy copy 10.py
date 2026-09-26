

import os, warnings
import pandas as pd
from multiprocessing.pool import ThreadPool
from dotenv import load_dotenv
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
import os
from datetime import  datetime

from dotenv import load_dotenv
import json
from kafka import KafkaProducer
from bson.objectid import ObjectId
from configuration.database import get_database_connection
# SSH tunnel settings
import threading
from configuration.redis import publish_redis_message, publish_redis_message_general
import asyncio
from repositories.station_repository import station_find_by_code_and_network_repository
import sys
import gc
from obspy.io.mseed.headers import InternalMSEEDWarning
from concurrent.futures import ThreadPoolExecutor
from multiprocessing.pool import ThreadPool


sys.setrecursionlimit(100000)  # Adjust the recursion limit
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


import threading

import logging

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

producer = KafkaProducer(bootstrap_servers=kafka_host+":"+kafka_port)

client_threads =[]
clients = []
stop_event = threading.Event()

MAX_CLIENT_PROCESS = 400
total_core = 10
pool = ThreadPool(MAX_CLIENT_PROCESS)



if os.path.isfile("./data/station.csv") == True:
    os.remove("./data/station.csv")

if os.path.isfile("./data/station_database.csv") == True:
    os.remove("./data/station_database.csv")

class ExceptionHandler(logging.Handler):
    def _init_(self, level=logging.ERROR):
        super()._init_()
        self.level = level

    def emit(self, record):
        if record.levelno >= self.level:
            raise RuntimeError(record.getMessage())

# Configure logging to capture messages at the ERROR level and above
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger('obspy.clients.seedlink')

# Add the custom exception handler to the specific logger
logger.addHandler(ExceptionHandler())


LOCAL_STATION_LIST = []

def split_array(arr, chunk_size):
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]

class MySeedLinkClient(EasySeedLinkClient):
    def __init__(self, server_url, autoconnect=True):
        self.threadpool = ThreadPoolExecutor(max_workers=10)
        super().__init__(server_url, autoconnect)
        
    def player_run(self):
        pass

    def on_data(self, trace):
        try:
            print(f'Received trace for station {trace.stats.station}:')
            print(trace)
            self.threadpool.submit(self.save_stream_to_mseed, trace)

        except Exception as e:
            print(e)
            self.on_seedlink_error()

    def on_terminate(self):
        try:
            print("Stopping")
            
            return super().on_terminate()
        except Exception as e:
            print(e)
            self.on_seedlink_error()
    
    def on_seedlink_error(self):

        print("Stopping by error")
      
        
        return super().on_terminate()

    
    def acked(self, err, msg):
        if err is not None:
            print(f"Failed to deliver message: {err.str()}")
        else:
            print(f"Message produced: {msg.value()}")
        
    
    def save_stream_to_mseed(self, trace):
        try:
            today = datetime.utcnow().date()
            
            
            path_save_day = "../archive_data/"+str(today)+"/"+trace.stats.network+"/"+trace.stats.station+"/"+trace.stats.channel+"/day_mseed"
            
            if not os.path.exists(path_save_day):
                os.makedirs(path_save_day)


            waveform2 = trace.data
            import time
            station_data = station_find_by_code_and_network_repository(db,trace.stats.station, trace.stats.network,)
            
            
            
            # trace.interpolate(sampling_rate=5) 
            json_string = {
                "date":str(today),
                "starttime":str(trace.stats.starttime),
                "endtime":str(trace.stats.endtime),
                "sampling_rate": trace.stats.sampling_rate,
                # "record_length": trace.stats.number_of_records,
                "delta": trace.stats.delta,
                "location": trace.stats.location,
                "location_database":station_data["location"],
                "longitude":station_data["longitude"],
                "latitude":station_data["latitude"],
                "npts": trace.stats.npts,
                "station":trace.stats.station,
                "network":trace.stats.network,
                "channel":trace.stats.channel,
                "expiration_timestamp":int(time.time()) + 1800,
                "waveform":waveform2.tolist()
            }

            # Send a message
            producer.send('waveform_seedlink', json.dumps(json_string).encode())
            # Ensure all messages are sent and then close the producer
            producer.flush()

            # channel = trace.stats.network+"."+trace.stats.station+"." + trace.stats.location + "."+ trace.stats.channel
            publish_redis_message_general("waveform_seedlink", json.dumps(json_string))
            
            trace = trace.interpolate(sampling_rate=5) 
            waveform3 = trace.data
            json_string = {
                "date":str(today),
                "starttime":str(trace.stats.starttime),
                "endtime":str(trace.stats.endtime),
                "sampling_rate": trace.stats.sampling_rate,
                # "record_length": trace.stats.number_of_records,
                "delta": trace.stats.delta,
                "location": trace.stats.location,
                "location_database":station_data["location"],
                "longitude":station_data["longitude"],
                "latitude":station_data["latitude"],
                "npts": trace.stats.npts,
                "station":trace.stats.station,
                "network":trace.stats.network,
                "channel":trace.stats.channel,
                "expiration_timestamp":int(time.time()) + 1800,
                "waveform":waveform3.tolist()
            }
           
            channel = trace.stats.network+"."+trace.stats.station+"." + trace.stats.location + "."+ trace.stats.channel
            publish_redis_message(channel, json.dumps(json_string))
            
           
        except Exception as e:
            print(str(e))

async def batch_run_client(arr_datas):
    client = None
    warnings.filterwarnings("error", category=InternalMSEEDWarning)
    is_add = False
    while True:
        try:
            client = MySeedLinkClient(server_url=arr_datas[0]['seedlink_url']) 
            for data in arr_datas:
                network = data['network']
                station = data['station']
                for channel in data['channel']:
                    client.select_stream(network, station, channel)
            station = ""
            if is_add == False:
                clients.append(client)       

            client.run()  # Assuming `run` has an async equivalent
        except InternalMSEEDWarning as w:
            print("Warning caught as exception "+station+"  "+str(w))
        except Exception as e:
            print("Client run terminated with exception "+station+"  "+str(e))
        finally:
            if client:
                client.close()
                del client
            
            gc.collect()
            print("Client run method exited.")
            continue
        
async def main():
    
    # global client_thread
    global clients
    global client_threads
    # global station_total_to_close
    try:
        station_datas = db["station"]
        if regional:
            user_data = db["user"].find_one({"username": regional})
            station_ids = user_data["stations"]
            station_datas = [db["station"].find_one({'_id': ObjectId(station_id)}) for station_id in station_ids]

        if not os.path.isfile("./data/station.csv"):
            print("First pulling station")
            df_database_station = pd.DataFrame(station_datas)
            df_database_station.to_csv("./data/station.csv", index=False)
            print(df_database_station)

            seedlink_urls = df_database_station['server_seedlink'].unique().tolist()
            tasks = []
            for seedlink_url in seedlink_urls:
                df_filtered = df_database_station[df_database_station["server_seedlink"] == seedlink_url]
                station_will_runs = [{
                    "seedlink_url": seedlink_url,
                    "network": row["network"],
                    "station": row["code"],
                    "channel": row["channel"]
                } for _, row in df_filtered.iterrows()]

                arr_results = split_array(station_will_runs, MAX_CLIENT_PROCESS)
                for result_chunk in arr_results:
                    tasks.append(asyncio.create_task(batch_run_client(result_chunk)))

            await asyncio.gather(*tasks)
                # print(f"Server {seedlink_url} used {len(arr_results)} client!")
    except Exception as e:
         print("Terminated "+str(e))
