import os, redis, pymongo, time, json, gc, copy
import numpy as np
import pandas as pd
from obspy import UTCDateTime, Trace, Stream
from kafka import KafkaConsumer, KafkaProducer
from multiprocessing.pool import ThreadPool
from flask import Flask, request, jsonify
from obspy.signal.trigger import aic_simple, classic_sta_lta, trigger_onset

from utils.messaging import json_serializer, \
                            send_picks_to_db, \
                            send_picks_to_kafka, \
                            send_arrivals_to_db, \
                            send_arrivals_to_kafka, \
                            get_db_station
                            
from utils.preprocessing import get_channel_stream
from config import *
   
import skydrifter as sd
from PhaseNet1D_3001 import *

# # Load models
# model_P_path = r"skydrifter_file/implementation31mei/important_file_1/model_P.pth"
# model_P = PhaseNet1D_3001(in_channel=3,out_channel=1)
# model_P.load_state_dict(torch.load(model_P_path))
# model_S_path = r"skydrifter_file/implementation31mei/important_file_1/model_S.pth"
# model_S = PhaseNet1D_3001(in_channel=3,out_channel=1)
# model_S.load_state_dict(torch.load(model_S_path))


# import keras
# phasenet = keras.models.load_model(r"skydrifter_file/implementation31mei/important_file_1/phasenet.h5", compile=False)
# phasenet.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])


import seisbench
import seisbench.models as sbm
from numpy.lib.stride_tricks import sliding_window_view
phasenet = sbm.PhaseNet(model_file="skydrifter_file/implementation31mei/important_file_1/sbm_phasenet.h5")


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

to_time = lambda x: str(UTCDateTime(x))

pool = ThreadPool(MAX_WORKERS)

def task(data):
    try:
        key = f"aicache_{data['network']}.{data['station']}.{data['location']}.{data['channel']}_data"
        stream = get_channel_stream(key.replace(data['channel'], data['channel'][:-1]+'E'), data['endtime'], WINDOW_SIZE_SEC, redis_client)
        stream += get_channel_stream(key.replace(data['channel'], data['channel'][:-1]+'N'), data['endtime'], WINDOW_SIZE_SEC, redis_client)
        stream += get_channel_stream(key.replace(data['channel'], data['channel'][:-1]+'Z'), data['endtime'], WINDOW_SIZE_SEC, redis_client)
        
        # Apply bandpass filter
        # stream = stream.filter("bandpass", freqmin=0.1, freqmax=5.0)
        
        start_time = max([tr.stats.starttime for tr in stream])
        end_time = min([tr.stats.endtime for tr in stream])
        stream = stream.trim(start_time, end_time)
        if end_time - start_time < WINDOW_SIZE_SEC//2: 
            return [0, end_time - start_time, WINDOW_SIZE_SEC//2]
        for i in range(3):
            # Fill in missing data
            temp_value = np.ones(WINDOW_SIZE)*np.mean(stream[i].data)
            temp_value[:len(stream[i].data)] = stream[i].data[:WINDOW_SIZE]
            stream[i].data = temp_value[:]

        # AIC
        aic = aic_simple(stream[-1].data)
        pick_aic = np.max(aic[np.isfinite(aic)]) - np.min(aic[np.isfinite(aic)])
        if pick_aic<2000: 
            return 0
        else:
            print(data['network'], data['station'], pick_aic) 
            candidate = [(start_time+(np.argmin(aic)/stream[-1].stats.sampling_rate)).timestamp,] ## DUMMY

        candidate = [pick for pick in candidate if str(pick).split('.')[0].isdigit()]
        picks = [to_time(pick) for pick in candidate if str(pick).split('.')[0].isdigit()]

        db_station = get_db_station(data['network'], data['station'], db)
        pick_ids = send_picks_to_db(picks, db_station, pick_col)
        send_picks_to_kafka(picks, db_station, pick_ids, producer)
        
        ### PICK BONDAN START
        # picker = sd.SeisAutoPickVoid(stream)
        # pick_P = picker.execute(candidate=candidate,model=model_P)
        # pick_P = np.mean(pick_P)
        # pick_S = picker.execute(candidate=candidate,model=model_S)
        # pick_S = np.mean(pick_S)
        ### PICK BONDAN END

        # ### PICK ALFA START
        # threshold = 0.2
        # window_size = 3000
        # step_size = 1000
        # from numpy.lib.stride_tricks import sliding_window_view
        # windows = sliding_window_view(np.nan_to_num(stream[-1].data[:])/1000, window_shape=window_size)[::step_size]
        # thresholded_predictions = np.zeros([stream[-1].data[:].shape[0],2])
        # for i, window in enumerate(windows):
        #     window = window.reshape(1, window_size, 1, 1) 
        #     prediction = phasenet.predict(window)[0,:,0,1:]
        #     thresholded = (prediction > threshold).astype(int)*prediction
        #     if thresholded[:,0].max()>0:
        #         temp = thresholded_predictions[i*step_size + np.argmax(thresholded[:,0]), 0]
        #         thresholded_predictions[i*step_size + np.argmax(thresholded[:,0]), 0] = max([thresholded[:,0].max(), temp])
        #         if thresholded[:,1].max()>0:
        #             temp = thresholded_predictions[i*step_size + np.argmax(thresholded[:,1]), 1]
        #             thresholded_predictions[i*step_size + np.argmax(thresholded[:,1]), 1] = max([thresholded[:,1].max(), temp])

        # pick_P, pick_S = np.argmax(thresholded_predictions, axis=0)
        
        # if pick_S>pick_P:
        #     pick_P, pick_S = start_time+(pick_P/stream[-1].stats.sampling_rate), start_time+(pick_S/stream[-1].stats.sampling_rate)
        # else: 
        #     return 0

        # pick_P, pick_S = pick_P.timestamp, pick_S.timestamp

        # ### PICK ALFA END

        ### PICK SEISBENCH START
        threshold = 0.2
        window_size = 3000
        step_size = 1000

        # Concatenate data from all three streams into a (3, N) shape
        stream_data = np.stack([
            np.nan_to_num(stream[0].data[:]),
            np.nan_to_num(stream[1].data[:]),
            np.nan_to_num(stream[2].data[:])
        ]) 

        # Create sliding windows of shape (M, 3, window_size)
        windows = sliding_window_view(stream_data, window_shape=(3, window_size)).squeeze(axis=-2)[::step_size]

        # Initialize predictions array
        thresholded_predictions = np.zeros([stream_data.shape[1], 2])

        # Process each window
        for i, window in enumerate(windows):
            window = window.transpose(1, 0).reshape(1, 3, window_size)  # Reshape to (1, 3, window_size)
            prediction_p = phasenet.predict(window)[0, :, 0]
            prediction_s = phasenet.predict(window)[0, :, 1]
            thresholded_p = (prediction_p > threshold).astype(int) * prediction_p
            thresholded_s = (prediction_s > threshold).astype(int) * prediction_s

            if thresholded_p[:, 0].max() > 0:
                temp = thresholded_predictions[i * step_size + np.argmax(thresholded_p[:, 0]), 0]
                thresholded_predictions[i * step_size + np.argmax(thresholded_p[:, 0]), 0] = max([thresholded_p[:, 0].max(), temp])

            if thresholded_s[:, 1].max() > 0:
                temp = thresholded_predictions[i * step_size + np.argmax(thresholded_s[:, 1]), 1]
                thresholded_predictions[i * step_size + np.argmax(thresholded_s[:, 1]), 1] = max([thresholded_s[:, 1].max(), temp])

        # Determine P and S picks
        pick_P, pick_S = np.argmax(thresholded_predictions, axis=0)

        if pick_S > pick_P:
            pick_P = start_time + (pick_P / stream[-1].stats.sampling_rate)
            pick_S = start_time + (pick_S / stream[-1].stats.sampling_rate)
        else:
            return 0

        pick_P, pick_S = pick_P.timestamp, pick_S.timestamp

        ### PICK SEISBENCH END

        if not str(pick_P).split('.')[0].isdigit() or not str(pick_S).split('.')[0].isdigit(): return 0
        if pick_P<0 or pick_S<0: return 0
        
        for pick, pick_id in zip(picks, pick_ids):
            break
        
        # Check duplicate
        for msg_id, fields in redis_client.xrange("ai_association", "-", "+"):
            # Extract the MiniSEED data and header from the message
            header_json = fields[b'data']
            
            # Decode the header information
            header = json.loads(header_json)
            try:
                _time = header['pick_p']['timestamp']
                try:
                    UTCDateTime(_time)
                except:
                    _time =_time[2:-2]
            except:
                continue
            
            print(f"Pick P: {pick_P}, Cache: {_time}")
            print(header["station"] == f"{db_station['network']}.{db_station['code']}")
            if header["station"] == f"{db_station['network']}.{db_station['code']}":
                print(f"Checking duplicate for", header["station"])
                if UTCDateTime(pick_P) - UTCDateTime(_time) < MIN_PICK_DIFF:
                    return 0
        
        # if not redis_client.get("flag_duplicated_pick_"+data['network']+"_"+data['station']):
        #     redis_client.set("flag_duplicated_pick_"+data['network']+"_"+data['station'], 1, ex=PICK_WAIT)
        # else:
        #     return 0
        
        pick_P_dt = to_time(pick_P)
        pick_S_dt = to_time(pick_S)
        pick_arrival_data = {
            'P': {'timestamp': pick_P_dt},
            'S': {'timestamp': pick_S_dt},
        }
        
        print("Sending", pick_arrival_data)
        
        p_arrival_id, s_arrival_id = send_arrivals_to_db(pick_arrival_data, db_station, pick_id, arrival_col)
        pick_arrival_data['P']['_id'] = p_arrival_id
        pick_arrival_data['S']['_id'] = s_arrival_id
        send_arrivals_to_kafka(pick_arrival_data, db_station, pick_id, producer)

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

            response = {
                "success": True,
                "code": task(message),
                "message": "Message consumed successfully!",
            }

            # Create a response
            if response['code']==1:
                print("Pick predicted successfully!")
            else:
                print("Message consumed successfully!")
        except Exception as e:
            # Create a response
            response = {
                "success": False,
                "code": 500,
                "message": str(e),
            }
        finally:
            print(response)
            return response


if __name__ == "__main__":
    print("Processing picking")
    app.run(debug=False)
