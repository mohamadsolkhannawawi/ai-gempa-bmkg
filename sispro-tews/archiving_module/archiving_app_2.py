import sys
import logging
import os
import io
import json
import redis
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from kafka import KafkaConsumer
from obspy import Stream, Trace, read
from filelock import FileLock
import threading
import obspy
import gc
import multiprocessing
import asyncio
from aiokafka import AIOKafkaConsumer
import signal
import psutil
import time
from configuration.database import get_database_connection
from bson.objectid import ObjectId
import pandas as pd
from tqdm import tqdm
from obspy.core import Stream, Trace
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor

load_dotenv("./.env")

MAX_PROCESS = 100

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

redis_host = os.getenv('redis_host', 'localhost')
redis_port = int(os.getenv('redis_port', 6379))
redis_client = redis.from_url(f'redis://{redis_host}:{redis_port}', decode_responses=True)

def process_data(data):
    try:
        
        current_timestamp = int(time.time())
        today = datetime.utcnow().date()
        channel = data["network"] + "." + data["station"] + "." + data["location"] + "." + data["channel"]

        
        messages = redis_client.lrange("ori_"+channel, 0, 3000)

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
                if len(stream)>0:
                    if int(trace.stats.starttime.timestamp) >= int(stream[-1].stats.endtime.timestamp):
                        stream.append(trace)
                else:
                    stream.append(trace)   
                    
            if stream:
                stream.write(filename, format='MSEED')
                
            msg_data = json.loads(messages)
            if msg_data.get('expiration_timestamp', 0) < current_timestamp:
                redis_client.lrem(f'ori_{channel}', 0, msg_data)                  

            

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
        station_ready_to_get_datas = []
        for seedlink_url in seedlink_urls:
            df_filtered = df_database_station[df_database_station["server_seedlink"] == seedlink_url]
            for _, row in df_filtered.iterrows():
                for channel in row["channel"]:
                    station_ready_to_get_datas.append(
                        {
                            "seedlink_url": seedlink_url,
                            "network": row["network"],
                            "station": row["code"],
                            "channel": channel,
                            "location": row["location"]
                        }
                    )
                    
                    
        from concurrent.futures import ProcessPoolExecutor, as_completed
        arr_results = split_array(station_ready_to_get_datas[200:400], 1)
        with ThreadPoolExecutor(max_workers=200) as executor:
            # Submit all tasks to the executor
            futures = [executor.submit(process_in_parallel, data) for data in arr_results]
            
        print("start " + str(now))
        now = datetime.now()
        print("finish " + str(now))

def split_array(arr, chunk_size):
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]

async def main():
    await get_data_from_redis()

# Run the main function
asyncio.run(main())
