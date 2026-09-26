import os, redis, pymongo, time, json, gc
import numpy as np
import tensorflow as tf
from obspy import UTCDateTime, Trace
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer
from multiprocessing.pool import ThreadPool
from flask import Flask, request, jsonify

from utils.messaging import json_serializer, \
                            send_picks_to_kafka, \
                            send_picks_to_db, \
                            send_arrival_waveform_to_kafka

from utils.preprocessing import trace_processing,\
                                single_channel_processing, \
                                multi_channel_processing \
                                
from config import *

app = Flask(__name__)

gc_counter = 0

# Instantiate some clients
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
pick_col = db['pick']
station_col = db['station']

model : tf.keras.models.Model = tf.keras.models.load_model("./models/cnnset_8s_20hz_0.h5", compile=False)

pool = ThreadPool(MAX_WORKERS)

def task(message):
    try:
        data = json_serializer(message)

        # Get station metadata
        station_metadata = {key: data[key] for key in ['network', 'station']}
        station_as_key = ".".join(station_metadata.values())
        
        # Filter out missing station
        db_station = station_col.find_one({
            'network': station_metadata['network'],
            'code': station_metadata['station'],
        })

        if db_station == None:
            print("Station not found:", station_metadata)
            return
    
        # Produce to pick_waveform for phase pick if waveform station in pick cache
        if redis_client.sismember('picked_station', station_as_key):
            arrival_waveform_data = {
                'station_id': str(db_station['_id']),
                'network': station_metadata['network'],
                'station': station_metadata['station'],
                'channel': data['channel'],
                'starttime': data['starttime'],
                'endtime': data['endtime'],
                'delta': data['delta'],
                'waveform': data['waveform']
            }
            producer.send(ARRIVAL_WAVEFORM_TOPIC, json.dumps(arrival_waveform_data).encode())
        
        trace = trace_processing(data, SAMPLE_RATE)
        # station_channels = [trace.stats.channel[:-1]+ch for ch in ['E','N','Z']]
        # station_channels = STATION_CHANNELS[trace.stats.station]
        full_waveform, picks = single_channel_processing(trace, WINDOW_SIZE, CENTER, NCHECK, redis_client)
        # picks = multi_channel_processing(trace, station_channels, WINDOW_SIZE, CENTER, NCHECK, redis_client)

        print(trace.id, trace.stats.endtime, picks)
        if picks:
            print(full_waveform)

            pick_ids = send_picks_to_db(db_station, pick_col, picks)
            send_picks_to_kafka(db_station, picks, pick_ids, producer)

            # Insert station data to redis to store waveforms in the future
            redis_client.sadd('picked_station', station_as_key)

            # TODO: Add flow to arrival_waveform
            send_arrival_waveform_to_kafka(db_station, full_waveform, float(trace.stats.delta), picks, pick_ids, producer)

        print(f"{UTCDateTime.now()}: Picking done!")

   
        gc.collect()
        return 0
    except Exception as e:
        print("Error: ", e)
        import traceback
        traceback.print_exc()
        gc.collect()
        return e

@app.route('/hello', methods=['GET'])
def hello():
    # Create a response
    response = {
        "success": True,
        "code": 200,
        "message": "HELLO!",
    }
    print("Hello")
    return jsonify(response)

@app.route('/predict', methods=['POST'])
def process_waveform():
    if request.method == 'POST':
        try:
            message = request.get_json()
            pool.imap_unordered(task, [message])
            
            if gc_counter > MAX_WORKERS:
                gc.collect()
                gc_counter = 0
                # pprint.pprint(gc.garbage)
            gc_counter += 1

            # Create a response
            print("Message consumed successfully!")
            response = {
                "success": True,
                "code": 200,
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
    app.run(debug=True)
