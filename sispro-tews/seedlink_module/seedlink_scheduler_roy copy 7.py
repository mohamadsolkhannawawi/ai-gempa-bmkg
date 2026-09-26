import os
import warnings
import pandas as pd
import json
import gc
import sys
import logging
import asyncio
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from kafka import KafkaProducer
from bson.objectid import ObjectId
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy.io.mseed.headers import InternalMSEEDWarning
from rocketry import Rocketry
from configuration.database import get_database_connection
from configuration.redis import publish_redis_message
from repositories.station_repository import station_find_by_code_and_network_repository

# Set recursion limit
sys.setrecursionlimit(100000)

# Load environment variables
load_dotenv("./.env")

# Kafka and database connection settings
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

# Create database connection
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

# Configure Kafka producer
producer = KafkaProducer(bootstrap_servers=f"{kafka_host}:{kafka_port}")

# Remove old CSV files if they exist
for file in ["./data/station.csv", "./data/station_database.csv"]:
    if os.path.isfile(file):
        os.remove(file)

MAX_CLIENT_PROCESS = 400

# Exception handler for logging
class ExceptionHandler(logging.Handler):
    def __init__(self, level=logging.ERROR):
        super().__init__()
        self.level = level

    def emit(self, record):
        if record.levelno >= self.level:
            raise RuntimeError(record.getMessage())

# Configure logging to capture messages at the ERROR level and above
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger('obspy.clients.seedlink')
logger.addHandler(ExceptionHandler())

# Custom SeedLink client
class MySeedLinkClient(EasySeedLinkClient):
    def __init__(self, server_url, autoconnect=True):
        self.threadpool = ThreadPoolExecutor(max_workers=10)
        super().__init__(server_url, autoconnect)

    def on_data(self, trace):
        try:
            print(f'Received trace for station {trace.stats.station}')
            print(trace)
            print()
            self.threadpool.submit(self.save_stream_to_mseed, trace)
        except Exception as e:
            print(e)
            self.on_seedlink_error()

    def on_terminate(self):
        try:
            print("Stopping")
            super().on_terminate()
        except Exception as e:
            print(e)
            self.on_seedlink_error()

    def on_seedlink_error(self):
        print("Stopping by error")
        super().on_terminate()

    def save_stream_to_mseed(self, trace):
        try:
            today = datetime.utcnow().date()
            path_save_day = f"../archive_data/{today}/{trace.stats.network}/{trace.stats.station}/{trace.stats.channel}/day_mseed"
            
            os.makedirs(path_save_day, exist_ok=True)

            waveform = trace.data
            station_data = station_find_by_code_and_network_repository(db, trace.stats.station, trace.stats.network)
            
            json_string = {
                "date":str(today),
                "starttime":str(trace.stats.starttime),
                "endtime":str(trace.stats.endtime),
                "sampling_rate": trace.stats.sampling_rate,
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
                "waveform": waveform.tolist()
            }

            producer.send('waveform_seedlink', json.dumps(json_string).encode())
            producer.flush()
    
            trace = trace.interpolate(sampling_rate=5)
            waveform_interpolated = trace.data
            json_string["waveform"] = waveform_interpolated.tolist()
            
            channel = trace.stats.network+"."+trace.stats.station+"." + trace.stats.location + "."+ trace.stats.channel
            publish_redis_message(channel, json.dumps(json_string))
        except Exception as e:
            print(str(e))

async def batch_run_client(arr_datas):
    warnings.filterwarnings("error", category=InternalMSEEDWarning)
    while True:
        client = None
        try:
            client = MySeedLinkClient(server_url=arr_datas[0]['seedlink_url']) 
            for data in arr_datas:
                network = data['network']
                station = data['station']
                for channel in data['channel']:
                    client.select_stream(network, station, channel)

            client.run()
        except InternalMSEEDWarning as w:
            print(f"Warning caught as exception {str(w)}")
        except Exception as e:
            print(f"Client run terminated with exception {str(e)}")
        finally:
            if client:
                client.close()
                del client
            gc.collect()
            print("Client run method exited.")
            continue

def split_array(arr, chunk_size):
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]

async def main():
    try:
        if regional:
            user_data = db["user"].find_one({"username": regional})
            station_ids = user_data["stations"]
            station_datas = [db["station"].find_one({'_id': ObjectId(station_id)}) for station_id in station_ids]
        else:
            station_datas = list(db["station"].find())

        if not os.path.isfile("./data/station.csv"):
            df_database_station = pd.DataFrame.from_dict(station_datas)
            df_database_station.to_csv("./data/station.csv", index=False)

        seedlink_urls = df_database_station['server_seedlink'].unique().tolist()
        tasks = []
        for seedlink_url in seedlink_urls:
            station_will_runs = []
            df_filtered = df_database_station[df_database_station["server_seedlink"] == seedlink_url]
            for _, row in df_filtered.iterrows():
                station_will_run = {
                    "seedlink_url": seedlink_url,
                    "network": row["network"], 
                    "station": row["code"], 
                    "channel": row["channel"]
                }
                station_will_runs.append(station_will_run)

            arr_results = split_array(station_will_runs, MAX_CLIENT_PROCESS)
            for result_chunk in arr_results:
                tasks.append(asyncio.create_task(batch_run_client(result_chunk)))

        await asyncio.gather(*tasks)

    except Exception as e:
        print(f"Terminated {str(e)}")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
