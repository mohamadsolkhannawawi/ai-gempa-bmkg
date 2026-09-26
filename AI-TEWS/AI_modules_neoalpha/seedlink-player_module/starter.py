import multiprocessing
from multiprocessing import Pool
import os, json, time, glob, threading, csv, pymongo, redis
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

# Get all data in this range
r = redis.Redis(host=redis_host, port=int(redis_port), db=0)

T = UTCDateTime(STARTTIME)
T1 = UTCDateTime(pd.read_csv('sls/'+sorted(os.listdir('sls'))[0]).Starttime[0])
stream_sh = [s.replace('\\','/') for s in glob.glob('archive_local_sh'+f'/*/*/*/*/*.{T.strftime("%Y.%j")}')]
stream_bh = [s.replace('\\','/') for s in glob.glob('archive_local_bh'+f'/*/*/*/*/*.{T.strftime("%Y.%j")}')]

data_local = get_local_data(stream_sh+stream_bh)

FGSK = []
for key in tqdm(data_local):
    st = read(key).merge()
    st = st.trim(T, T+35)
    if st:
        FGSK.append(key)

FGSK = set_db_all(FGSK)

# Function to process each key in parallel
def process_key(key, values):
    try:
        stream = read(key).merge()
        # Delete the previous streams and headers
        r.delete("mseed_stream_" + stream[0].id)
        r.delete("mseed_header_" + stream[0].id)

        # Process each time window (t0, t1)
        for t0, t1 in values:
            trs = stream.copy()
            trs = trs.trim(UTCDateTime(t0)-(T1-T), UTCDateTime(t1)-(T1-T))
            try:
                store(trs, r)  # Assuming store(trs) is defined elsewhere
            except Exception as e:
                pass
    except Exception as e:
        print(f"Error processing key {key}: {e}")

print("Store waveform to redis...")
tasks = [process_key(key, data_local[key]) for key in tqdm(FGSK)]
    
# Store list in Redis (using lpush to push elements in the list)
r = redis.Redis(host=redis_host, port=int(redis_port), db=0)
for item in FGSK:
    r.rpush('stored_seedlink_keys', item)

print("Waveforms Stored!")

