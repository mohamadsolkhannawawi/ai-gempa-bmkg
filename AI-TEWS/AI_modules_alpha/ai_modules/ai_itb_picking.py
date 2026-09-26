import os, redis, pymongo, threading, time, json, pytz
import numpy as np
import tensorflow as tf
from obspy import UTCDateTime, Trace, Stream
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer

from datetime import datetime, timezone

from utils.messaging import json_serializer
from utils.preprocessing import trace_processing

import skydrifter as sd
from skydrifter.PeculiarSupport.obspy_support import convert_timestamp
from PhaseNet1D_3001 import *

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

REDIS_HOST = os.getenv("redis_host")
REDIS_PORT = os.getenv("redis_port")

MONGO_HOST = os.getenv("database_host")
MONGO_PORT = os.getenv("database_port")

DB_NAME = os.getenv("database_name")

# Kafka topics
PICK_TOPIC = os.getenv("pick_topic")
ARRIVAL_WAVEFORM_TOPIC = os.getenv("arrival_waveform_topic")
SAMPLE_RATE = 20
WINDOW_SIZE_SEC = 300
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE
OVERLAPS_SEC = 180
OVERLAPS = OVERLAPS_SEC * SAMPLE_RATE
MAX_WORKER = 1000

# Instantiate some clients
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
pick_consumer = KafkaConsumer(PICK_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]

# Load models
model_P_path = r"skydrifter_file/implementation31mei/important_file_1/model_P.pth"
model_P = PhaseNet1D_3001(in_channel=3,out_channel=1)
model_P.load_state_dict(torch.load(model_P_path))
model_S_path = r"skydrifter_file/implementation31mei/important_file_1/model_S.pth"
model_S = PhaseNet1D_3001(in_channel=3,out_channel=1)
model_S.load_state_dict(torch.load(model_S_path))

to_time = lambda x: UTCDateTime(x).strftime(format='%Y-%m-%d %H:%M:%S.%f')

def ai_itb_picking_process(data, window_size, overlaps, r, channels = ['BHE','BHN','BHZ']):
    # Store to redis
    redis_key = f"ai_arrival_{data['network']}_{data['station']}" 
    r.hset(redis_key, data['channel'], json.dumps(data))

    print(redis_key)
    # Get all messages from the Redis stream
    channel_series = []
    for channel in channels:
         _json = r.hget(redis_key, channel)
         if not _json:
             return 0
         channel_series.append(json.loads(_json))

    stream = Stream()
    start_time = []
    end_time = []
    for data in channel_series:
        header = {
            'network': data['network'],
            'station': data['station'],
            'location': data['location'], 
            'channel': data['channel'],
            'starttime': data['starttime'], 
            'endtime': data['endtime'], 
            'sampling_rate': data['sampling_rate'], 
            'delta': data['delta'],
            'npts': data['npts'],
            'mseed': {"dataquality":'D'},
        }
        start_time.append(data['starttime'])
        end_time.append(data['endtime'])
        trace = Trace(data=np.array(data['waveform']), header=header)
        stream.append(trace)
    
    start_time = UTCDateTime(max(start_time))
    end_time = UTCDateTime(min(end_time))
    
    if end_time - start_time < OVERLAPS_SEC:
        return 0
    
    r.delete(redis_key)

    stream = stream.trim(start_time, end_time)
    detect = sd.SeisAutoDetect(stream)
    candidate = detect.execute()
    candidate = [pick for pick in candidate if str(pick).split('.')[0].isdigit()]
    picker = sd.SeisAutoPickVoid(stream)
    pick_P = picker.execute(candidate=candidate,model=model_P)
    pick_P = np.mean(pick_P)
    pick_S = picker.execute(candidate=candidate,model=model_S)
    pick_S = np.mean(pick_S)

    if not str(pick_P).split('.')[0].isdigit() or not str(pick_S).split('.')[0].isdigit(): return 0

    if pick_P<0 or pick_S<0: return 0

    candidate_dt = [to_time(pick) for pick in candidate if str(pick).split('.')[0].isdigit()]
    # TODO
    # send pick topic dengan data candidate_dt

    pick_P_dt = to_time(pick_P)
    pick_S_dt = to_time(pick_S)
    
    db_station = db["station"]

    station_data = db_station.find_one({'code': data['station']})
    
    pick_arrival_data = {
        'station': data['station'],
        'pick_p': pick_P_dt,
        'pick_s': pick_S_dt,
        'longitude': station_data['longitude'],
        'latitude': station_data['latitude'],
    }
    print(pick_arrival_data)

    # TODO
    # send arrival topic dengan data yang disesuaikan (yg dibutuhkan locmag pick_arrival_data)
    # bikin dictionary data yang disesuaikan kyk yang ada sekarang
    
    # producer.send(ARRIVAL_WAVEFORM_TOPIC, json.dumps(pick_arrival_data).encode())

def task(message):
    data = json_serializer(message)
    ai_itb_picking_process(data, WINDOW_SIZE, OVERLAPS, redis_client)


if __name__ == "__main__":
    print("Processing Pick")

    for message in pick_consumer:
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKER:
            print("System Overhead: Forced Stop!!!...............")
            break