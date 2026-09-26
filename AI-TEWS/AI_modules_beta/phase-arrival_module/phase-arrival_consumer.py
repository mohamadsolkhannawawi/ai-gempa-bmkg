import os, redis, pymongo, time, json, gc, threading
import numpy as np
import pandas as pd
from obspy import UTCDateTime, Trace, Stream
from kafka import KafkaConsumer, KafkaProducer
from multiprocessing.pool import ThreadPool
from bson.objectid import ObjectId

from utils.messaging import json_serializer, \
                            send_arrivals_to_db, \
                            send_arrivals_to_kafka, \
                            ts_transform

from utils.preprocessing import get_channel_stream
   
import skydrifter as sd
from PhaseNet1D_3001 import *
from skydrifter.SeisAutoPick.RealTimePicker.Algorithm.TorchPicker import TorchPicker
                                
from config import *

gc_counter = 0

POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
pick_consumer = KafkaConsumer(PICK_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"], max_block_ms=120000)
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
pick_col = db['pick']
station_col = db['station']
arrival_col = db['arrival']

# Load models
picker_algo = TorchPicker()
model_P_path = r"skydrifter/__SkydrifterFile/_2_implementation2agustus/important_file_4/model_P.pth"
model_P = PhaseNet1D_3001(in_channel=3,out_channel=1)
model_P.load_state_dict(torch.load(model_P_path))
model_S_path = r"skydrifter/__SkydrifterFile/_2_implementation2agustus/important_file_4/model_S.pth"
model_S = PhaseNet1D_3001(in_channel=3,out_channel=1)
model_S.load_state_dict(torch.load(model_S_path))

picker_algo.config['model_P'] = model_P
picker_algo.config['model_S'] = model_S

to_time = lambda x: str(UTCDateTime(x))

pool = ThreadPool(MAX_WORKERS)

def task(message):
    data = json_serializer(message)
    print(data)
    try:
        db_station = db['station'].find_one({'_id':data['station_id']})
        data['network'] = db_station['network']
        data['station'] = db_station['code']
        data['location'] = db_station['location']
        # Filter channels (BH and SH)
        data['channel'] = [ch for ch in sorted(db_station['channel']) if ch[:-1] in ['BH','SH']][0]
        data['endtime'] = str(UTCDateTime(data['timestamp']) - PADDING_FIRST_WINDOW + WINDOW_SIZE_SEC)
        key = f"aicache_{data['network']}.{data['station']}.{data['location']}.{data['channel']}_data"
        stream = get_channel_stream(key.replace(data['channel'], data['channel'][:-1]+'E'), data['endtime'], WINDOW_SIZE_SEC, redis_client)
        stream += get_channel_stream(key.replace(data['channel'], data['channel'][:-1]+'N'), data['endtime'], WINDOW_SIZE_SEC, redis_client)
        stream += get_channel_stream(key.replace(data['channel'], data['channel'][:-1]+'Z'), data['endtime'], WINDOW_SIZE_SEC, redis_client)
        start_time = max([tr.stats.starttime for tr in stream])
        end_time = min([tr.stats.endtime for tr in stream])
        stream = stream.trim(start_time, end_time)
        if end_time - start_time < WINDOW_SIZE_SEC//2: 
            return [0, end_time - start_time, WINDOW_SIZE_SEC//2]
        for i in range(3):
            temp_value = np.ones(WINDOW_SIZE)*np.mean(stream[i].data)
            temp_value[:len(stream[i].data)] = stream[i].data[:WINDOW_SIZE]
            stream[i].data = temp_value
        
        print("POOLED!!!")

        pick_id = ObjectId(data['pick'])
        
        picker = sd.SeisAutoPickRunner(stream=stream, algo=picker_algo)
        picker.execute()

        if picker.algo.P_pick['P'] == None or picker.algo.P_pick['S'] == None:
            return 0

        pick_P = picker.algo.P_pick['P']
        pick_S = picker.algo.P_pick['S']
        
        if not str(pick_P).split('.')[0].isdigit() or not str(pick_S).split('.')[0].isdigit(): return 0
        if pick_P<0 or pick_S<0: return 0

        print('PICKED!!!')
        
        pick_P_dt = to_time(pick_P)
        pick_S_dt = to_time(pick_S)
        pick_arrival_data = {
            'P': {'timestamp': pick_P_dt},
            'S': {'timestamp': pick_S_dt},
        }
        p_arrival_id, s_arrival_id = send_arrivals_to_db(pick_arrival_data, db_station, pick_id, arrival_col)
        pick_arrival_data['P']['_id'] = p_arrival_id
        pick_arrival_data['S']['_id'] = s_arrival_id
        send_arrivals_to_kafka(pick_arrival_data, db_station, pick_id, producer)

        print('SUCCESS!!!')
        gc.collect()
        return 1
    except Exception as e:
        gc.collect()
        return e

if __name__ == "__main__":
    print("Processing PhaseArrivalPicking")

    for message in pick_consumer:
        task(message)
        continue
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKERS:
            print("System Overhead: Forced Stop!!!...............")
            break