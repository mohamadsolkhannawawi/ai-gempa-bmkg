import os, redis, pymongo, time, json, gc, copy
import numpy as np
import pandas as pd
from obspy import UTCDateTime, Trace, Stream
from kafka import KafkaConsumer, KafkaProducer
from multiprocessing.pool import ThreadPool
from flask import Flask, request, jsonify
from obspy.signal.trigger import aic_simple, classic_sta_lta, trigger_onset

from utils.messaging import send_picks_to_db, \
                            send_picks_to_kafka, \
                            get_db_station, \
                            ts_transform

from utils.preprocessing import get_channel_stream
   
import skydrifter as sd
from skydrifter.SeisAutoDetect.Algorithm.SherelKNN import SherelKNN

from config import *
import keras
import logging

app = Flask(__name__)

gc_counter = 0

POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"], max_block_ms=120000)
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
pick_col = db['pick']
station_col = db['station']
arrival_col = db['arrival']

# Load models
detection_algo = SherelKNN()            

to_time = lambda x: str(UTCDateTime(x))

pool = ThreadPool(MAX_WORKERS)

def task(data):
    try:
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

        detector = sd.SeisAutoDetect(stream=stream, algo=detection_algo)
        trigger = detector.execute()

        if trigger == False: return 0

        # TODO
        ### Additional AIC-Picker
        aic = aic_simple(stream[-1].data)
        pick_aic = np.max(aic[np.isfinite(aic)]) - np.min(aic[np.isfinite(aic)])
        if pick_aic<200: return 0
        else: candidate = [(start_time+(np.argmin(aic)/stream[-1].stats.sampling_rate)).timestamp,] 
        ###

        # TODO
        ### DUMMY
        # candidate = [start_time.timestamp,] 
        ###

        candidate = [pick for pick in candidate if str(pick).split('.')[0].isdigit()]
        picks = [to_time(pick) for pick in candidate if str(pick).split('.')[0].isdigit()]

        db_station = get_db_station(data['network'], data['station'], db)
        pick_ids = send_picks_to_db(picks, db_station, pick_col)
        send_picks_to_kafka(picks, db_station, pick_ids, producer)
        
        gc.collect()
        return 1
    except Exception as e:
        gc.collect()
        raise e
    
@app.route('/predict', methods=['POST'])
def process_waveform():
    if request.method == 'POST':
        try:
            message = request.get_json()
            # pool.imap_unordered(task, [message])

            # Create a response
            print("Message consumed successfully!")
            response = {
                "success": True,
                "code": task(message),
                "message": "Message consumed successfully!",
            }
        except Exception as e:
            # Create a response
            response = {
                "success": False,
                "code": 500,
                "message": str(e),
            }
        finally:
            # Return a JSON response
            return jsonify(response)


if __name__ == "__main__":
    print("Processing picking")
    app.run(debug=False)
