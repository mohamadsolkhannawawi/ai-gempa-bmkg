import os, redis, pymongo, time, json, gc
import numpy as np
import pandas as pd
from obspy import UTCDateTime, Trace, Stream
from kafka import KafkaConsumer, KafkaProducer
from multiprocessing.pool import ThreadPool
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

# Instantiate some clients
# from redis.cluster import RedisCluster as Redis
# from redis.cluster import ClusterNode
# nodes = [ClusterNode(REDIS_HOST, REDIS_PORT), ]
# redis_client = Redis(startup_nodes=nodes)
# redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
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

import keras
phasenet = keras.models.load_model(r"skydrifter_file/implementation31mei/important_file_1/phasenet.h5", compile=False)
phasenet.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])

to_time = lambda x: str(UTCDateTime(x))

pool = ThreadPool(MAX_WORKERS)


# def task(message):
#     # try:
#         data = json_serializer(message)

#         # Store to redis
#         redis_key = f"ai_arrival_{data['network']}_{data['station']}" 
#         redis_client.hset(redis_key, data['channel'], json.dumps(data))

#         print(redis_key)
#         # Get all messages from the Redis stream
#         channel_series = []
#         for channel in CONFIG_CHANNEL:
#             _json = redis_client.hget(redis_key, channel)
#             if not _json:
#                 return 0
#             channel_series.append(json.loads(_json))

#         stream = Stream()
#         start_time = []
#         end_time = []
#         for data in channel_series:
#             header = {
#                 'network': data['network'],
#                 'station': data['station'],
#                 'location': data['location'], 
#                 'channel': data['channel'],
#                 'starttime': data['starttime'], 
#                 'endtime': data['endtime'], 
#                 'sampling_rate': data['sampling_rate'], 
#                 'delta': data['delta'],
#                 'npts': data['npts'],
#                 'mseed': {"dataquality":'D'},
#             }
#             start_time.append(data['starttime'])
#             end_time.append(data['endtime'])
#             trace = Trace(data=np.array(data['waveform']), header=header)
#             stream.append(trace)
        
#         start_time = UTCDateTime(max(start_time))
#         end_time = UTCDateTime(min(end_time))

#         if end_time - start_time < OVERLAPS_SEC:
#             return 0
        
#         redis_client.delete(redis_key)

#         stream = stream.trim(start_time, end_time)
#         detect = sd.SeisAutoDetect(stream)
#         candidate = detect.execute()
#         candidate = [pick for pick in candidate if str(pick).split('.')[0].isdigit()]
#         picker = sd.SeisAutoPickVoid(stream)
#         pick_P = picker.execute(candidate=candidate,model=model_P)
#         pick_P = np.mean(pick_P)
#         pick_S = picker.execute(candidate=candidate,model=model_S)
#         pick_S = np.mean(pick_S)

#         if not str(pick_P).split('.')[0].isdigit() or not str(pick_S).split('.')[0].isdigit(): return 0

#         if pick_P<0 or pick_S<0: return 0

#         candidate_dt = [to_time(pick) for pick in candidate if str(pick).split('.')[0].isdigit()]
        
#         # Search station details in db
#         db_station = station_col.find_one({
#             'network': data['network'], 
#             'code': data['station'],
#         })

#         # Insert candidates as picks to db and kafka
#         print(f"{candidate_dt=}")
#         pick_ids = send_picks_to_db(candidate_dt, db_station, pick_col)
#         send_picks_to_kafka(candidate_dt, db_station, pick_ids, producer)

#         # Insert arrivals to db and kafka
#         pick_P_dt = to_time(pick_P)
#         pick_S_dt = to_time(pick_S)
        
#         pick_arrival_data = {
#             'P': {
#                 'timestamp': pick_P_dt
#             },
#             'S': {
#                 'timestamp': pick_S_dt
#             },
#         }
#         print(f"{pick_arrival_data=}")

#         p_arrival_id, s_arrival_id = send_arrivals_to_db(pick_arrival_data, db_station, pick_ids[0], arrival_col)
#         pick_arrival_data['P']['_id'] = p_arrival_id
#         pick_arrival_data['S']['_id'] = s_arrival_id
        
#         send_arrivals_to_kafka(pick_arrival_data, db_station, pick_ids[0], producer)

#         # TODO
#         # send arrival topic dengan data yang disesuaikan (yg dibutuhkan locmag pick_arrival_data)
#         # bikin dictionary data yang disesuaikan kyk yang ada sekarang
        
#         # producer.send(ARRIVAL_WAVEFORM_TOPIC, json.dumps(pick_arrival_data).encode())
#         print(f"{UTCDateTime.now()}: Picking done!")
        
#         # rval = {'nowtime':str(UTCDateTime.now()), 'endtime': str(end_time), 'pick': str(pick_P_dt)}
#         # redis_client.xadd('DEBUG_STEP2_'+redis_key, {"data": json.dumps(rval)})

#         gc.collect()
#         return 1
#     # except Exception as e:
#     #     print("Error: ", e)
#     #     import traceback
#     #     traceback.print_exc()
#     #     gc.collect()
#     #     return e


def task3(data):
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
            # Fill in missing data
            temp_value = np.ones(len(stream[i].data))*np.mean(stream[i].data)
            temp_value[:len(stream[i].data)] = stream[i].data[:]
            stream[i].data[:] = stream[i].data[:] 

        # if end_time - start_time < WINDOW_SIZE_SEC: return 0

        # picks = pick_detection(key, stream)

        # detect = sd.SeisAutoDetect(stream)
        # candidate = detect.execute()
        # if len(candidate)==0: return 0

        # AIC
        aic = aic_simple(stream[-1].data)
        pick_aic = np.max(aic[np.isfinite(aic)]) - np.min(aic[np.isfinite(aic)])
        if pick_aic<1500: return 0
        else: candidate = [(start_time+(np.argmin(aic)/stream[-1].stats.sampling_rate)).timestamp,] ## DUMMY

        candidate = [pick for pick in candidate if str(pick).split('.')[0].isdigit()]
        picks = [to_time(pick) for pick in candidate if str(pick).split('.')[0].isdigit()]

        db_station = get_db_station(data['network'], data['station'], db)
        pick_ids = send_picks_to_db(picks, db_station, pick_col)
        send_picks_to_kafka(picks, db_station, pick_ids, producer)
        
        # picker = sd.SeisAutoPickVoid(stream)
        # pick_P = picker.execute(candidate=candidate,model=model_P)
        # pick_P = np.mean(pick_P)
        # pick_S = picker.execute(candidate=candidate,model=model_S)
        # pick_S = np.mean(pick_S)

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
            return 0
            # pick_P, pick_S = start_time+(pick_P/stream[-1].stats.sampling_rate), start_time+(pick_P/stream[-1].stats.sampling_rate)+5
        pick_P, pick_S = pick_P.timestamp, pick_S.timestamp

        if not str(pick_P).split('.')[0].isdigit() or not str(pick_S).split('.')[0].isdigit(): return 0
        if pick_P<0 or pick_S<0: return 0
        
        for pick, pick_id in zip(picks, pick_ids):
            # pick_arrival_data = arrival_picker(key, stream, pick)
            break
        
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
    

# # def task2(data):
# #         # Get station metadata
# #         station_metadata = {key: data[key] for key in ['network', 'station']}
# #         station_as_key = ".".join(station_metadata.values())
        
# #         # Filter out missing station
# #         db_station = station_col.find_one({
# #             'network': station_metadata['network'],
# #             'code': station_metadata['station'],
# #             'server_seedlink': 'localhost',
# #         })

# #         if db_station == None:
# #             print("Station not found:", station_metadata)
# #             return 0
    
# #         trace = trace_processing(data, SAMPLE_RATE)
# #         full_waveform, picks = single_channel_processing(trace, WINDOW_SIZE, CENTER, NCHECK, redis_client)

# #         print(trace.id, trace.stats.endtime, picks)
# #         if picks:

# #             picks = [p['timestamp'] for p in picks][0:1]
# #             pick_ids = send_picks_to_db(picks, db_station, pick_col)
# #             send_picks_to_kafka(picks, db_station, pick_ids, producer)
# #             pick_arrival_data = {
# #                 'P': {
# #                     'timestamp': str(picks[0])
# #                 },
# #                 'S': {
# #                     'timestamp': str(UTCDateTime(picks[0])+15)
# #                 },
# #             }
                
# #             p_arrival_id, s_arrival_id = send_arrivals_to_db(pick_arrival_data, db_station, pick_ids[0], arrival_col)
# #             pick_arrival_data['P']['_id'] = p_arrival_id
# #             pick_arrival_data['S']['_id'] = s_arrival_id

# #             send_arrivals_to_kafka(pick_arrival_data, db_station, pick_ids[0], producer)
# #             print(db_station, pick_arrival_data)
            
# #         print(f"{UTCDateTime.now()}: Picking done!")

   
# #         gc.collect()
# #         return 1
    
# # Route for testing
# @app.route('/hello', methods=['GET'])
# def hello():
#     # Create a response
#     response = {
#         "success": True,
#         "code": 200,
#         "message": "HELLO!",
#     }
#     print("Hello")
#     return jsonify(response)

@app.route('/predict', methods=['POST'])
def process_waveform():
    if request.method == 'POST':
        try:
            message = request.get_json()
            # pool.imap_unordered(task3, [message])

            # if gc_counter > MAX_WORKERS:
            #     gc.collect()
            #     gc_counter = 0
            #     pprint.pprint(gc.garbage)
            # gc_counter += 1

            # Create a response
            print("Message consumed successfully!")
            response = {
                "success": True,
                # "code": 200,
                "code": task3(message),
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
