import sys
import logging
import os
import math
import json
import redis
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from obspy import Stream, Trace, read
from filelock import FileLock
import threading
import obspy
import gc
import multiprocessing
import asyncio
import signal
import time
from configuration.docker_conf import get_replica_id
from configuration.database import get_database_connection
from bson.objectid import ObjectId
import pandas as pd
from obspy.core import Stream, Trace
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor

load_dotenv("./.env")

MAX_PROCESS = 10
REPLICA_ID = get_replica_id()
REPLICA_COUNT = int(os.getenv('archive_replica_count'))

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

redis_connected = False
redis_host = os.getenv('redis_host', 'localhost')
redis_port = int(os.getenv('redis_port', 6379))
print(f"Redis: {redis_host}:{redis_port}")
print(f"MongoDB: {MONGO_HOST}:{LOCAL_BIND_PORT}")

RETRY_AFTER = 100
for retry in range(1, RETRY_AFTER+1):
    try:
        redis_client = redis.from_url(f'redis://{redis_host}:{redis_port}', decode_responses=True)
    except Exception as e:
        time.sleep(5)
        if retry % 5 == 0:
            print(f"Redis connection failed. Retrying... ({e})")
        
        if retry == RETRY_AFTER:
            raise e            
    else:
        print(f"Redis connected successfully after {retry} retry")
        break        
    
def process_data(data):
    try:
        
        current_timestamp = int(time.time())
        today = datetime.utcnow().date()
        channel = data["network"] + "." + data["station"] + "." + data["location"] + "." + data["channel"]

        list_len = redis_client.llen(f'ori_{channel}')
        messages = redis_client.lrange(f'ori_{channel}', 0, list_len)

        data_list = json.loads('[' + ','.join(messages) + ']')
        valid_df = pd.DataFrame(data_list)
        
        if not valid_df.empty:
            current_year = today.year
            julian_day = today.timetuple().tm_yday

            fmtstr = f"/{current_year}/{data['network']}/{data['station']}/{data['channel']}.D"
            directory = f"/archive{fmtstr}"
            os.makedirs(directory, exist_ok=True)

            filename = f"{directory}/{data['network']}.{data['station']}.{data['location']}.{data['channel']}.D.{current_year}.{julian_day}.mseed"
            
            stream = Stream()

            if os.path.exists(filename):
                stream = obspy.read(filename)
            else:
                stream = Stream()

            waveform_data = valid_df['waveform'].values
            stations = valid_df['station'].values
            networks = valid_df['network'].values
            locations = valid_df['location'].values
            channels = valid_df['channel'].values
            starttimes = valid_df['starttime'].values
            sampling_rates = valid_df['sampling_rate'].values

            for i in range(len(valid_df)):
                trace = Trace(data=np.array(waveform_data[i]))
                trace.stats.station = stations[i]
                trace.stats.network = networks[i]
                trace.stats.location = locations[i]
                trace.stats.channel = channels[i]
                trace.stats.starttime = obspy.UTCDateTime(starttimes[i])
                trace.stats.sampling_rate = sampling_rates[i]
                trace.data = trace.data.astype(np.int32)
                if len(stream)>0:
                    if int(trace.stats.starttime.timestamp) >= int(stream[-1].stats.endtime.timestamp):
                        stream.append(trace)
                else:
                    stream.append(trace)                    

            if stream:
                stream.write(filename, format='MSEED')
                
            redis_client.ltrim(f'ori_{channel}', list_len-1, -1)


    except Exception as e:
        print("error "+str(e))
        
def process_in_parallel(data):
    for result_chunk in data:
        asyncio.create_task(process_data(result_chunk))

    return data  # Returning data to capture progress

async def get_data_from_redis():
    station_datas = db["station"]
    now = datetime.now()
    if regional:
        user_data = db["user"].find_one({"username": regional})
        station_ids = user_data["stations"]
        station_datas = [db["station"].find_one({'_id': ObjectId(station_id)}) for station_id in station_ids]

        df_database_station = pd.DataFrame(station_datas)
        print(df_database_station)

        seedlink_urls = df_database_station['server_seedlink'].unique().tolist()
        channel_ready_to_get_datas = []
        for seedlink_url in seedlink_urls:
            df_filtered = df_database_station[df_database_station["server_seedlink"] == seedlink_url]
            for _, row in df_filtered.iterrows():
                for channel in row["channel"]:
                    channel_ready_to_get_datas.append(
                        {
                            "seedlink_url": seedlink_url,
                            "network": row["network"],
                            "station": row["code"],
                            "channel": channel,
                            "location": row["location"]
                        }
                    )
                    
        print(f"Processing total of {len(channel_ready_to_get_datas)} channels")
        
        # Check redis connection and get all keys
        RETRY_AFTER = 100
        for retry in range(1, RETRY_AFTER+1):
            try:
                all_keys = redis_client.keys("ori_*")
            except Exception as e:
                time.sleep(5)
                if retry % 5 == 0:
                    print(f"Redis connection failed. Retrying... ({e})")
                
                if retry == RETRY_AFTER:
                    raise e            
            else:
                print(f"Redis connected successfully after {retry} retry")
                break        
            
        # all_keys = redis_client.keys("ori_*")
        # if len(all_keys) > len(channel_ready_to_get_datas):
        
        # Preprocess key into list of dictionary containing seedlink_url, network, station, channel, location
        channel_ready_to_get_datas = []
        for key in all_keys:
            channel = key.replace("ori_","")
            channel_ready_to_get_datas.append(
                {
                    "network": channel.split(".")[0],
                    "station": channel.split(".")[1],
                    "location": channel.split(".")[2],
                    "channel": channel.split(".")[3],
                }
            )
        print("Final:")
        print(f"{len(all_keys)=} vs {len(channel_ready_to_get_datas)=}")
                            
        # If service is replicated, run only part of all channels according to replica id
        if REPLICA_ID != None:
            print("Detected as replica number", REPLICA_ID)
            channel_per_replica = math.ceil(len(channel_ready_to_get_datas) / REPLICA_COUNT)
            start = (int(REPLICA_ID)-1) * channel_per_replica
            end = int(REPLICA_ID) * channel_per_replica
            channel_ready_to_get_datas = channel_ready_to_get_datas[start:end]
            print(f"Channel per replica: {channel_per_replica}")
            print(f"Processing total of {end-start} from index {start} to {end}")
        else:
            print("No replica, processing all channels")
            
        print("start " + str(now))
        arr_results = split_array(channel_ready_to_get_datas, 1)
        with ThreadPoolExecutor(max_workers=channel_per_replica) as executor:
            # Submit all tasks to the executor
            futures = [executor.submit(process_in_parallel, data) for data in arr_results]

        now = datetime.now()
        print("finish " + str(now))

def split_array(arr, chunk_size):
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]

async def main():
    await get_data_from_redis()

# Run the main function
asyncio.run(main())
