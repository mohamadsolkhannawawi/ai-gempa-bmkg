import os, redis, pymongo, time, json, gc, threading
import numpy as np
import pandas as pd
from obspy import UTCDateTime, Trace, Stream
from kafka import KafkaConsumer, KafkaProducer
from multiprocessing.pool import ThreadPool
from bson.objectid import ObjectId
from flask import Flask, request, jsonify
from obspy.signal.trigger import aic_simple

from utils.messaging import json_serializer, \
                            send_picks_to_db, \
                            send_picks_to_kafka, \
                            send_arrivals_to_db, \
                            send_arrivals_to_kafka, \
                            get_db_station

from utils.preprocessing import trace_processing,\
                                single_channel_processing,\
                                get_channel_stream,\
                                pick_detection,\
                                arrival_picker
   
import skydrifter as sd
from PhaseNet1D_3001 import *

                                
from config import *

app = Flask(__name__)

gc_counter = 0

POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
pick_consumer = KafkaConsumer(PICK_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"], max_block_ms=120000)
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]

# Load models
model_P_path = r"skydrifter_file/implementation31mei/important_file_1/model_P.pth"
model_P = PhaseNet1D_3001(in_channel=3,out_channel=1)
model_P.load_state_dict(torch.load(model_P_path))
model_S_path = r"skydrifter_file/implementation31mei/important_file_1/model_S.pth"
model_S = PhaseNet1D_3001(in_channel=3,out_channel=1)
model_S.load_state_dict(torch.load(model_S_path))

import keras
phasenet = keras.models.load_model(r"skydrifter_file/implementation31mei/important_file_1/phasenet.h5", compile=False)
phasenet.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])

to_time = lambda x: str(UTCDateTime(x))

pool = ThreadPool(MAX_WORKER)

def task(data):
    try:
        db_station = db['station'].find_one({'_id':data['station_id']})
        data['network'] = db_station['network']
        data['station'] = db_station['code']
        data['location'] = db_station['location']
        data['channel'] = [ch for ch in sorted(db_station['channel']) if ch[:-1] in ['BH','SH']][0]
        data['endtime'] = str(UTCDateTime(data['timestamp']) - 5 + WINDOW_SIZE_SEC)
        key = f"aicache_{data['network']}.{data['station']}.{data['location']}.{data['channel']}_data"
        stream = get_channel_stream(key.replace(data['channel'], data['channel'][:-1]+'E'), data['endtime'], WINDOW_SIZE_SEC, redis_client)
        stream += get_channel_stream(key.replace(data['channel'], data['channel'][:-1]+'N'), data['endtime'], WINDOW_SIZE_SEC, redis_client)
        stream += get_channel_stream(key.replace(data['channel'], data['channel'][:-1]+'Z'), data['endtime'], WINDOW_SIZE_SEC, redis_client)
        start_time = max([tr.stats.starttime for tr in stream])
        end_time = min([tr.stats.endtime for tr in stream])
        if end_time - start_time < WINDOW_SIZE_SEC: return 0
        stream = stream.trim(start_time, end_time)

        pick_id = ObjectId(data['pick'])
        
        threshold = 0.2
        window_size = 3000
        step_size = 1000
        from numpy.lib.stride_tricks import sliding_window_view
        windows = sliding_window_view(np.nan_to_num(stream[-1].data[:-1])/1000, window_shape=window_size)[::step_size]
        thresholded_predictions = np.zeros([stream[-1].data[:-1].shape[0],2])
        for i, window in enumerate(windows):
            window = window.reshape(1, window_size, 1, 1) 
            prediction = phasenet.predict(window)[0,:,0,1:]
            thresholded = (prediction > threshold).astype(int)*prediction
            if thresholded[:,0].max()>0:
                temp = thresholded_predictions[i*step_size + np.argmax(thresholded[:,0]), 0]
                thresholded_predictions[i*step_size + np.argmax(thresholded[:,0]), 0] = max([thresholded[:,0].max(), temp])
                if thresholded[:,1].max()>0:
                    temp = thresholded_predictions[i*step_size + np.argmax(thresholded[:,1]), 1]
                    thresholded_predictions[i*step_size + np.argmax(thresholded[:,1]), 1] = max([thresholded[:,1].max(), temp])

        pick_P, pick_S = np.argmax(thresholded_predictions, axis=0)
        if pick_S>pick_P:
            pick_P, pick_S = start_time+(pick_P/stream[-1].stats.sampling_rate), start_time+(pick_S/stream[-1].stats.sampling_rate)
        else: 
            pick_P, pick_S = start_time+(pick_P/stream[-1].stats.sampling_rate), start_time+(pick_P/stream[-1].stats.sampling_rate)+5
        pick_P, pick_S = pick_P.timestamp, pick_S.timestamp

        if not str(pick_P).split('.')[0].isdigit() or not str(pick_S).split('.')[0].isdigit(): return 0
        if pick_P<0 or pick_S<0: return 0
        
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

        gc.collect()
        return 1
    except Exception as e:
        gc.collect()
        return e

if __name__ == "__main__":
    print("Processing PhasePicking")

    for message in pick_consumer:
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKER:
            print("System Overhead: Forced Stop!!!...............")
            break