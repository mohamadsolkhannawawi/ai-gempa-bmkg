from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool
import asyncio
import os, json, time, glob, threading, csv, pymongo, redis, sys
import numpy as np
import pandas as pd
from tqdm import tqdm
from obspy import UTCDateTime, Trace, read
from kafka import KafkaProducer
from obspy.clients.filesystem.sds import Client
from bson.objectid import ObjectId
from utils import *
from vars import STARTTIME

print("Starting...")

r = redis.Redis(host=redis_host, port=int(redis_port), db=0)
producer = KafkaProducer(bootstrap_servers=[f"{kafka_host}:{kafka_port}"])
r_fe = redis.Redis(host=redis_host_fe, port=redis_port_fe, db=0)
FGSK = r.lrange('stored_seedlink_keys', 0, -1)
FGSK = [item.decode('utf-8') for item in FGSK]
start_idx = sys.argv[1]
end_idx = sys.argv[2]

Delta_T = get_started_time(STARTTIME)
print(Delta_T)

async def batch_process(keys):
    executor = ThreadPoolExecutor(max_workers=len(keys))
    for key in keys:
        executor.submit(process_key, key, Delta_T, producer, r, r_fe)

# Function to handle a single key, to be executed in parallel
def process_key(key, Delta_T, producer, r, r_fe):
    stid = '.'.join(key.split('/')[-1].split('.')[:-3])
    get_trace(stid, Delta_T, producer, r, r_fe, frac=0.5, NOWTIME=True)

def split_array(arr, chunk_size):
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]

splitted_fgsk = split_array(FGSK[int(start_idx):int(end_idx)], 400)

processes = []
# Create processes
print(start_idx, end_idx)
tasks = []
async def main():
    for key in splitted_fgsk:
        tasks.append(asyncio.create_task(batch_process(key)))

    await asyncio.gather(*tasks)
    
asyncio.run(main())
    
    # process = threading.Thread(target=process_key, args=(key, Delta_T))
    # processes.append(process)
    # process.start()  # Start the process immediately without waiting

# # Wait for all processes to finish
# for process in processes:
#     process.join(0)  # This ensures all processes are completed before proceeding

