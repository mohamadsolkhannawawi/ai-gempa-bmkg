import os, redis, pymongo, time, json, gc
import numpy as np
from obspy import UTCDateTime, Trace, Stream
from kafka import KafkaConsumer, KafkaProducer
from multiprocessing.pool import ThreadPool
from flask import Flask, request, jsonify

from utils.messaging import json_serializer, \
                            send_picks_to_db, \
                            send_picks_to_kafka, \
                            send_arrivals_to_db, \
                            send_arrivals_to_kafka

import skydrifter as sd
from PhaseNet1D_3001 import *

                                
from config import *

app = Flask(__name__)

gc_counter = 0

# Instantiate some clients
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"], max_block_ms=120000)
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
pick_col = db['pick']
station_col = db['station']
arrival_col = db['arrival']

# Load models
model_P_path = r"skydrifter_file/implementation31mei/important_file_1/model_P.pth"
model_P = PhaseNet1D_3001(in_channel=3,out_channel=1)
model_P.load_state_dict(torch.load(model_P_path))
model_S_path = r"skydrifter_file/implementation31mei/important_file_1/model_S.pth"
model_S = PhaseNet1D_3001(in_channel=3,out_channel=1)
model_S.load_state_dict(torch.load(model_S_path))

to_time = lambda x: str(UTCDateTime(x))

pool = ThreadPool(MAX_WORKERS)

def task(message):
    try:
        data = json_serializer(message)

        # Store to redis
        redis_key = f"ai_arrival_{data['network']}_{data['station']}" 
        redis_client.hset(redis_key, data['channel'], json.dumps(data))

        print(redis_key)
        # Get all messages from the Redis stream
        channel_series = []
        for channel in CONFIG_CHANNEL:
            _json = redis_client.hget(redis_key, channel)
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
        
        redis_client.delete(redis_key)

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
        
        # Search station details in db
        db_station = station_col.find_one({
            'network': data['network'], 
            'code': data['station']
        })

        # Insert candidates as picks to db and kafka
        print(f"{candidate_dt=}")
        pick_ids = send_picks_to_db(candidate_dt, db_station, pick_col)
        send_picks_to_kafka(candidate_dt, db_station, pick_ids, producer)

        # Insert arrivals to db and kafka
        pick_P_dt = to_time(pick_P)
        pick_S_dt = to_time(pick_S)
        
        pick_arrival_data = {
            'P': {
                'timestamp': pick_P_dt
            },
            'S': {
                'timestamp': pick_S_dt
            },
        }
        print(f"{pick_arrival_data=}")

        p_arrival_id, s_arrival_id = send_arrivals_to_db(pick_arrival_data, db_station, pick_ids[0], arrival_col)
        pick_arrival_data['P']['_id'] = p_arrival_id
        pick_arrival_data['S']['_id'] = s_arrival_id
        
        send_arrivals_to_kafka(pick_arrival_data, db_station, pick_ids[0], producer)

        # TODO
        # send arrival topic dengan data yang disesuaikan (yg dibutuhkan locmag pick_arrival_data)
        # bikin dictionary data yang disesuaikan kyk yang ada sekarang
        
        # producer.send(ARRIVAL_WAVEFORM_TOPIC, json.dumps(pick_arrival_data).encode())
        print(f"{UTCDateTime.now()}: Picking done!")
        
        rval = {'nowtime':str(UTCDateTime.now()), 'endtime': str(end_time), 'pick': str(pick_P_dt)}
        redis_client.xadd('DEBUG_STEP2_'+redis_key, {"data": json.dumps(rval)})

        gc.collect()
        return 0
    except Exception as e:
        print("Error: ", e)
        import traceback
        traceback.print_exc()
        gc.collect()
        return e

# Route for testing
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
