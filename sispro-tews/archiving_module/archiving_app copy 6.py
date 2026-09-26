import sys
import logging
import os
import io
import json
import aioredis
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from kafka import KafkaConsumer
from obspy import Stream, Trace, read
from filelock import FileLock
import threading
import gc
import multiprocessing
import asyncio
from aiokafka import AIOKafkaConsumer
import signal
import psutil
import time
from configuration.database import get_database_connection
load_dotenv("./.env")
from bson.objectid import ObjectId
import pandas as pd
from tqdm import tqdm
import obspy
from obspy.core import Stream, Trace
MAX_PROCESS = 100

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
redis_client = aioredis.from_url(f'redis://{redis_host}:{redis_port}', decode_responses=True)

async def get_data_from_redis():
    current_timestamp = int(time.time())
    station_datas = db["station"]
    today = datetime.utcnow().date()
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
                    
        print(station_ready_to_get_datas)
        for data in tqdm(station_ready_to_get_datas):
            try:
                channel = data["network"]+"."+data["station"]  +"."+data["location"]  +"."+data["channel"]              
                messages = await asyncio.wait_for(redis_client.lrange(f'{channel}_history', 0, 3000), timeout=1.0)

                data_list = json.loads('[' + ','.join(messages) + ']')  # Join messages and parse as a list

                # Create DataFrame directly from the list of dictionaries
                df = pd.DataFrame(data_list)

                if not df.empty:

                    df['expiration_timestamp'] = pd.to_numeric(df['expiration_timestamp'], errors='coerce')
                    valid_df = df[df['expiration_timestamp'] > current_timestamp]

                    # Convert DataFrame back to list of dictionaries
                    # valid_datas = valid_df.to_dict(orient='records')


                    current_year = today.year
                    julian_day = today.timetuple().tm_yday

                    fmtstr = '/'+ str(current_year)+"/"+data["network"]+"/"+data["station"]+"/"+data["channel"]+ ".D"
                    directory = f"../archive{fmtstr}"

                    # Create the directory if it does not exist
                    os.makedirs(directory, exist_ok=True)
                    filename1 = f"{directory}/{data['network']}.{data['station']}.{data['location']}.{data['channel']}.D.{current_year}.{julian_day}.mseed"

                    # Check if the file exists
                    if os.path.exists(filename1):
                        # Load existing MiniSEED file into a Stream
                        stream = obspy.read(filename1)

                        # Extract metadata of existing traces
                        existing_traces_metadata = set(
                            (trace.stats.station, trace.stats.network, trace.stats.location, trace.stats.channel, trace.stats.starttime)
                            for trace in stream
                        )
                    else:
                        # Create a new Stream if the file does not exist
                        stream = Stream()
                        existing_traces_metadata = set()

                    for index, row in valid_df.iterrows():
                        # Convert the waveform to a NumPy array
                        waveform_data = np.array(row['waveform'])

                        # Create a Trace object
                        trace = Trace(data=waveform_data)
                        trace.stats.station = row["station"]
                        trace.stats.network = row["network"]
                        trace.stats.location = row["location"]
                        trace.stats.channel = row["channel"]
                        trace.stats.starttime = obspy.UTCDateTime(row["starttime"])
                        trace.stats.sampling_rate = row["sampling_rate"]

                        # Check if the trace already exists in the existing stream
                        # print("dsad")                       
                        trace_metadata = (trace.stats.station, trace.stats.network, trace.stats.location, trace.stats.channel, trace.stats.starttime)
                        # print("dsad")   
                        # if trace_metadata not in existing_traces_metadata:
                        #     # Append the Trace to the Stream
                        #     print("test ", row["station"])

                        stream.append(trace)
 
                        # existing_traces_metadata.add(trace_metadata)  # Update the existing metadata set
   
                    # Save the updated Stream back to the MiniSEED file
                    stream.write(filename1, format='MSEED')

                    # print(valid_datas)
            except Exception as e:
                print(str(e))
        print("finish")



async def main():
    while True:
        await get_data_from_redis()
        await asyncio.sleep(60)  # Use asyncio.sleep instead of time.sleep

# Run the async main function
asyncio.run(main())
