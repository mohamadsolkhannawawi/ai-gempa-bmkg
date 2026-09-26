from pick_dummy import DummySDSConsumer
from obspy import UTCDateTime, Trace
import os
from kafka import KafkaConsumer, KafkaProducer
from dotenv import load_dotenv
import redis
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import json
import tensorflow as tf
import pymongo
from stalta_model import get_stalta
import gc
from multiprocessing.pool import ThreadPool
import time

# env constant
import pprint
# gc.set_debug(gc.DEBUG_LEAK) # TODO: debug, please remove

load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

REDIS_HOST = os.getenv("redis_host")
REDIS_PORT = os.getenv("redis_port")

MONGO_HOST = os.getenv("database_host")
MONGO_PORT = os.getenv("database_port")

DB_NAME = os.getenv("database_name")

# Kafka topics
WAVEFORM_TOPIC = os.getenv("waveform_topic")
PICK_TOPIC = os.getenv("pick_topic")
ARRIVAL_WAVEFORM_TOPIC = os.getenv("arrival_waveform_topic")

# Other constant
SAMPLE_RATE = 20
WINDOW_SIZE_SEC = 8
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE # 10 second
STALTA_WINDOW = 80
STALTA_CHANNEL = 'Z'
THRESHOLD = 0.5
NORM_CONST = 1000
NCHECK = 2
MAX_WORKERS = 500

# Instantiate some clients
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
waveform_consumer = KafkaConsumer(WAVEFORM_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
pick_col = db['pick']
station_col = db['station']

model : tf.keras.models.Model = tf.keras.models.load_model("./models/cnnset_8s_20hz_0.h5", compile=False)

# Handle with CNN-LSTM algorithm with 3 channel. Cache will only be deleted if window
# from all channel is already processed
def preprocess_data(data: dict):
    # Get necessary data
    pulled_waveform = data['waveform']
    channel = data['channel']
    station_metadata = {key: data[key] for key in ['network', 'station']}
    starttime = UTCDateTime(data['starttime'])
    endtime = UTCDateTime(data['endtime'])
    delta = data['delta']

    print(starttime, endtime)

    # Add old data to processed waveform if exists in cache
    station_as_key = "waveform:" + ".".join(station_metadata.values())
    print(station_as_key, channel)
    cache = None
    if redis_client.exists(station_as_key):
        cache : dict = json.loads(redis_client.get(station_as_key).decode())
        if cache.get(channel) != None:    
            # TODO: Add checking to empty data  
            # for now skip if cache is too far
            diff = UTCDateTime(data['starttime']) - UTCDateTime(cache[channel]['endtime'])
            if diff > delta or diff < 0:
                redis_client.delete(station_as_key)
                print("Missing data")
                print(f"{diff}")
            else:
                # Check delta (TODO: this is probably not needed, but just in case)
                assert delta == cache[channel]['delta'], "Delta in waveform is different from delta in cache, please check"

                print(f"{len(cache[channel]['waveform'])=}")
                pulled_waveform = cache[channel]['waveform'] + pulled_waveform

    # Update or add cache data
    if cache == None:
        store_cache = {}     
        cache_starttime = str(starttime)
    else:
        store_cache = cache
        cache_starttime = str(starttime) if cache.get(channel) == None else cache[channel]['starttime']
    
    store_cache[channel] = {
        "starttime": cache_starttime,
        "endtime": str(endtime),
        "delta": delta,
        "waveform": pulled_waveform
    }
    redis_client.set(station_as_key, json.dumps(store_cache))
    
    # Check if waveform from all channel is already valid
    # Check if there are 3 channel
    if len(store_cache) == 3:
        print(f"Channel count for station {station_as_key} sufficient")
        # Get min_start_timestamp and max_end_timestamp to clip all channels
        max_start_timestamp = UTCDateTime(cache_starttime) # init with current waveform channel timestamp
        min_end_timestamp = endtime
        for channel_data in store_cache.values():
            max_start_timestamp = max(max_start_timestamp, UTCDateTime(channel_data['starttime']))
            min_end_timestamp = min(min_end_timestamp, UTCDateTime(channel_data['endtime']))

        # Clip all channel according to min and max timestamp
        clipped_waveforms = {
            "E": [],
            "N": [],
            "Z": []
        }

        full_waveform = {
            "E": [],
            "N": [],
            "Z": []
        }

        valid = True
        for channel, channel_data in store_cache.items():
            # Copy the channel data instead of channel_data memory reference
            # Note: this solve bug where after store_cache is changed, the channel_data is changed as well 
            channel_data = channel_data.copy()

            # Calculate clipping offset
            start_timestamp_offset = max_start_timestamp - UTCDateTime(channel_data['starttime'])
            end_timestamp_offset =  UTCDateTime(channel_data['endtime']) - min_end_timestamp
            
            start_idx_offset = round(start_timestamp_offset / delta)
            end_idx_offset = round(end_timestamp_offset / delta)
            end_idx = len(channel_data['waveform']) - end_idx_offset

            print("*" * 50)
            print(UTCDateTime(channel_data['starttime']), max_start_timestamp)
            print(start_timestamp_offset, start_idx_offset)
            print(UTCDateTime(channel_data['endtime']), min_end_timestamp)
            print(end_timestamp_offset, end_idx_offset, len(channel_data['waveform']), end_idx)
            print("*" * 50)

            # Check if clipped window fits model requirement
            print("Channel:", channel)
            if end_idx - start_idx_offset < WINDOW_SIZE:
                print("Window size not fit:", end_idx - start_idx_offset)
                valid = False
                break
            else:
                # Clip waveform
                clipped_waveforms[channel[-1]] = channel_data['waveform'][start_idx_offset:end_idx]

                # Prepare excess data to be updated in cache
                # FIX
                # store_cache_starttime = min_end_timestamp - WINDOW_SIZE_SEC / 2
                # store_cache_startidx = end_idx - WINDOW_SIZE // 2
                # store_cache[channel]['starttime'] = str(store_cache_starttime)
                # store_cache[channel]['waveform'] = channel_data['waveform'][store_cache_startidx:]

                # TODO: might need fix
                store_cache[channel]['starttime'] = str(min_end_timestamp)
                store_cache[channel]['waveform'] = channel_data['waveform'][end_idx:]

                # Prepare full_waveform
                full_waveform[channel[-1]] = channel_data['waveform'][start_idx_offset:]

        # Sliding window if all data exists
        if valid:
            # Update cache
            redis_client.set(station_as_key, json.dumps(store_cache))

            clipped_waveforms = np.array([waveform_data for waveform_data in clipped_waveforms.values()]).T
            print(f"{clipped_waveforms.shape=}")

            # STA/LTA store to redis
            redis_key = 'stalta_' + '_' + data['network'] + '_' + data['station']
            keys = redis_client.keys(redis_key + "*")
            values_STA = []

            for key in sorted(list(keys)):
                if UTCDateTime(key.decode('utf-8').split('_')[-1]) > UTCDateTime(data['starttime']) - STALTA_WINDOW: 
                    values_STA.append(np.array([float(v.replace('[','').replace(']','')) for v in redis_client.get(key.decode('utf-8')).decode('utf-8').split(', ')]))
            
            values_STA.append(clipped_waveforms[...,['E','N','Z'].index(STALTA_CHANNEL)])
            if len(values_STA)>1:
                values_STA = np.concatenate(values_STA)
            else: 
                values_STA = np.array(values_STA[0])

            redis_client.set(redis_key+'_'+data['starttime'], json.dumps(clipped_waveforms[...,['E','N','Z'].index(STALTA_CHANNEL)].tolist()), ex=160)

            # Sliding windows
            # Get sliding window result from waveform
            windows = sliding_window_view(clipped_waveforms, WINDOW_SIZE, axis=0)
            windows = np.transpose(windows, axes=(0, 2, 1)) 
            print(f"{windows.shape=}")

            # STA/LTA sliding windows
            if values_STA.shape[0] < int(STALTA_WINDOW*SAMPLE_RATE):
                _temp = np.zeros([int(STALTA_WINDOW*SAMPLE_RATE) + (windows.shape[0]-1)])
                _temp[-values_STA.shape[0]:] = values_STA
                values_STA = _temp
            
            values_STA = sliding_window_view(values_STA, int(STALTA_WINDOW*SAMPLE_RATE), axis=0)[-windows.shape[0]:]


            # TODO: currently only handles detection algorithm
            # Set timestamp for each window (result)
            timestamps = []
            curr_time = max_start_timestamp + WINDOW_SIZE_SEC // 2 - delta
            while curr_time <= min_end_timestamp - WINDOW_SIZE_SEC // 2:
                timestamps.append(str(curr_time))
                curr_time += delta

            # Insert timestamp to windows
            windows_with_timestamp = {timestamp: window for timestamp, window in zip(timestamps, windows)}

            # Update cache to remove processed window
            redis_client.set(station_as_key, json.dumps(store_cache))

            return max_start_timestamp, full_waveform, [windows_with_timestamp, values_STA]
        
    else:
        print(f"Channel for station {station_as_key} isn't sufficient (currently {len(store_cache)} channel, needs 3)" )
        pass
    return None, None, [[], []]
    

# Handle with CNN-LSTM model
def get_picking_detection(data) -> np.ndarray:
    # Normalize data
    values = np.array(list(data[0].values()))
    values_STA = data[1]
    normalized_data = (values - values[:,:1]) / NORM_CONST

    # Detect P-picks
    # STA/LTA 
    thresholded_picks = np.array([min(
            len(get_stalta(pval, STALTA_WINDOW, SAMPLE_RATE)), 1
        ) for pval in values_STA])
    
    picks = model.predict(normalized_data)[:, 0]

    thresholded_picks = picks * thresholded_picks >= THRESHOLD

    kernel = np.ones(NCHECK)
    thresholded_picks = (np.convolve(np.pad(thresholded_picks, len(kernel), mode="maximum")[len(kernel):-1], kernel, mode="valid")/len(kernel)).astype(int)

    print("predict!!!")

    # picks = np.random.normal(-3, 1, len(data[0]))
    # thresholded_picks = picks >= THRESHOLD
    
    # Add timestamp to pick
    timestamps = np.array(list(data[0].keys()))
    picked_timestamp = timestamps[np.where(thresholded_picks)]

    return picked_timestamp

def consume_waveform(message):
    try:
        # Kafka consumer
        data = json.loads(message.value.decode('utf-8'))
        # data = json.loads(data) # Bug in producer where data needs to be JSON parsed twice
        
        # SDS consumer
        # data = message
        
        if data.get('starttime') != None:
            if len(data['starttime']) < 20: # TODO: remove in the future
                print("Wrong time format, please recheck the provider")
                print(data['starttime'])
                return
        else:
            print("No starttime, please recheck the provider")
            return
        
        if data.get('sampling_rate') != None:
            if data['sampling_rate'] != SAMPLE_RATE:
                print("Different sampling rate")
                return
            #     trace_waveform = Trace(data['waveform'])
            #     if data['sample_rate'] > SAMPLE_RATE:
            #         data['waveform'] = trace_waveform.resample()

        # Insert picks to DB
        # Get station ID
        db_station = station_col.find_one({
            'network': station_metadata['network'],
            'code': station_metadata['station'],
        })

        if db_station == None:
            print("Station not found:", station_metadata)
            return

        # Define DB data
        db_data = [
            {
                'station': db_station['_id'],
                'timestamp': UTCDateTime(timestamp).datetime,
                'created_at': UTCDateTime().now().datetime
            }
            for timestamp in pick_timestamps
        ]

        # Get station metadata
        station_metadata = {key: data[key] for key in ['network', 'station']}
        station_as_key = ".".join(station_metadata.values())

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

        # Get windows
        start_of_full_waveform, full_waveform, windows = preprocess_data(data)

        print(f"{len(windows[0])=}")
        if len(windows[0]) != 0:
            # Get picks
            pick_timestamps = get_picking_detection(windows).tolist()
            windows = windows[0] # STA/LTA delete
            print(f"{len(pick_timestamps)=}")
            
            if len(pick_timestamps) != 0:
                # Insert data to DB and get ID for each pick timestamp
                pick_ids = pick_col.insert_many(db_data).inserted_ids
                # pick_ids = np.random.randint(0, 1e9, size=len(pick_timestamps)) # TODO: dummy, please remove

                # Produce pick
                kafka_data = {
                    'network': station_metadata['network'],
                    'station': station_metadata['station'],
                    'picks': [
                        {
                            'id': str(id),
                            'timestamp': timestamp
                        }
                        for id, timestamp in zip(pick_ids, pick_timestamps)
                    ]
                }
                producer.send(PICK_TOPIC, json.dumps(kafka_data).encode())
                
                # Insert station data to redis to store waveforms in the future
                redis_client.sadd('picked_station', station_as_key)
                
                # Send initial waveform to phase arrival pick to be stored
                for id, timestamp in zip(pick_ids, pick_timestamps):
                    # Calculate offset of waveform that will be pulled
                    # Ideally, it should start at -(half_window) before pick timestamp
                    start_of_window = UTCDateTime(timestamp) - WINDOW_SIZE_SEC / 2

                    # Calculate offset
                    picked_timestamp_offset = round(start_of_window - start_of_full_waveform, ndigits=3)
                    picked_idx_offset = round(picked_timestamp_offset / data['delta'])
                    
                    offset_waveform = {
                        channel[-1]: waveform_data[picked_idx_offset:]
                        for channel, waveform_data in full_waveform.items()
                    }

                    arrival_waveform = {
                        'station_id': str(db_station['_id']),
                        'network': station_metadata['network'],
                        'station': station_metadata['station'],
                        'pick_id': str(id),
                        'starttime': str(start_of_window),
                        'endtime': data['endtime'],
                        'delta': data['delta'],
                        'waveform': offset_waveform,
                    }

                    producer.send(ARRIVAL_WAVEFORM_TOPIC, json.dumps(arrival_waveform).encode())
            
        print("#" * 100)
    except Exception as e:
        print("Error:", e)
    finally:
        # process_end = time.time() # TODO: Debug, please remove
        # elapsed_time = process_end - process_start # TODO: Debug, please remove
        # print(f"Time elapsed: {elapsed_time:.2f} - {window=} & {pred=}")
        # del window
        # del pred
        # del process_start
        # del process_end
        # del elapsed_time
        gc.collect()

        return # ref: https://stackoverflow.com/questions/47951352/python-multithreading-memory-not-released-when-ran-using-while-statement

import ctypes

def force_kill_thread(thread):
    # Try to raise a SystemExit exception in the target thread
    try:
        if thread.is_alive():
            # `SystemExit` raises a controlled exception to stop the thread
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), ctypes.py_object(SystemExit))
    except Exception as e:
        print(f"Failed to kill thread: {e}")

if __name__ == "__main__":
    # SDSConsumer for testing
    # waveform_consumer = DummySDSConsumer(30, 2)
    # waveform_consumer.set_client(2024, "GE", "JAGI", "BHZ", "D", "", 78)
    # waveform_consumer.fill_data(UTCDateTime(2024, 3, 18, 5, 56, 0), UTCDateTime(2024, 3, 18, 6, 7, 40))

    # Flush redis
    # redis_client.flushall()

    print("Processing picking")
    jobs = []
    pool = ThreadPool(MAX_WORKERS)
    i = 0
    for message in waveform_consumer:
        pool.imap_unordered(consume_waveform, [message])
        

        if i > MAX_WORKERS:
            gc.collect()
            i = 0
            # pprint.pprint(gc.garbage)
        i += 1

        
        # job = pool.imap_unordered(consume_waveform, [message])
        # jobs.append(job)

        # if len(jobs) >= MAX_WORKERS:
        #     print("Deleting jobs")
        #     for job in jobs:
        #         job._cond.acquire()
        #         job._cond.release

        #         # Ensure job is finished
        #         # force_kill_thread(job)

        #     # Delete all references to jobs
        #     jobs.clear()
        #     del jobs
        #     jobs = []

        #     # Collect garbages
        #     gc.collect()