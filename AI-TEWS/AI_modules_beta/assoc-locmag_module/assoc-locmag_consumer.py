import os, redis, pymongo, threading, time, json, pytz, copy
import numpy as np
import pandas as pd
import geopandas as gpd
from obspy import UTCDateTime, Trace, Stream
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer

from utils.messaging import json_serializer, \
                            send_cluster_to_db, \
                            send_cluster_to_kafka, \
                            send_event_to_db, \
                            send_event_to_kafka, \
                            send_reloc_to_kafka, \
                            get_inventory

import skydrifter as sd

from config import *

POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
pick_consumer = KafkaConsumer(PICK_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
cluster_col = db['cluster']
magnitude_col = db['magnitude']
event_col = db['event']

to_timestamp = lambda x: UTCDateTime(x).timestamp

def ai_itb_logmag_process(data, r):
    # Store to redis
    redis_key = f"ai_association" 

    data = {
        'station': data['station'],
        'pick_p': [pick for pick in data['picks']][0],
    }

    r.xadd(redis_key, {"data": json.dumps(data)})

    expired_time = UTCDateTime(data['pick_p']['timestamp']) - ASSOCIATION_EXPIRED_SEC

    # Get all messages from the Redis stream
    messages = r.xrange(redis_key, "-", "+") 

    list_taken_time = []
    dict_taken_msg_id = {}
    dict_taken_station = {}
    dict_taken_pick_p = {}
    
    for msg_id, fields in messages:
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
        _station = header['station']
        _pick_p = header['pick_p']

        # Take the needed data back selection
        if expired_time < UTCDateTime(_time):
            # print("TAKEN =================", taken_starttime, _time)
            list_taken_time.append(_time)
            dict_taken_msg_id[_time] = msg_id
            dict_taken_station[_time] = _station
            dict_taken_pick_p[_time] = _pick_p
        else:
            # print("DELETE =================", _time)
            r.xdel(redis_key, msg_id)

    if len(list_taken_time)<N_STATION: return 0

    list_taken_time = sorted(list_taken_time)

    df_event = pd.DataFrame({
        'station': [dict_taken_station[t] for t in list_taken_time],
        'P': [UTCDateTime(dict_taken_pick_p[t]['timestamp']) for t in list_taken_time],
        'P_snr': [dict_taken_pick_p[t]['snr'] for t in list_taken_time],
        'P_dict': [dict_taken_pick_p[t] for t in list_taken_time],
    })

    event_params = df_event[['station','P','P_snr']].to_dict('records')

    print('Event-params:', len(event_params))
    
    flow = sd.EventFlowController()
    flow.tabular_model = copy.deepcopy(TABULAR_MODEL)

    df_station = get_inventory(db)
    df_station.columns = [s.capitalize() for s in df_station.columns]
    df_station['Station'] = df_station['Code']
    flow.input_station_inventory(inventory=df_station)

    for params in event_params:
        try:
            flow.input_raw_event(params)
            flow.process_raw_event()
            station_feature = copy.deepcopy(flow.raw_event_processed)
            flow.update_event(station_feature)
            flow.update_parameter()
        except Exception as e:
            print(str(e))

    list_origin = []
    for key in list(flow.inactive_event.keys()):
        event_result = flow.inactive_event[key].event_feature
        if event_result['origin_time']==None: continue
        if event_result['event_longitude']<0: continue
        list_origin.append(event_result)
    
    try:
        print(list(flow.active_event.keys()), list(flow.inactive_event.keys()), event_result['origin_time'])
    except:
        pass
     
    for key in list(flow.active_event.keys()):
        event_result = flow.active_event[key].event_feature
        if event_result['origin_time']==None: continue
        if event_result['event_longitude']<0: continue
        list_origin.append(event_result)

    print("Saved events:", len(list_origin))
    print(list(flow.active_event.keys()), list(flow.inactive_event.keys()), event_result['origin_time'])

    if len(list_origin)>0:
        event_result = list_origin[-1]
        # Send cluster to DB and kafka
        origin_time = event_result['origin_time']
        if type(origin_time)==str: origin_time = UTCDateTime(origin_time)
        try:
            previous_origin_time = redis_client.get('flag_origin_time_auto')
            if int(origin_time.timestamp) <=  int(previous_origin_time): return 0
        except:
            pass
        cluster_id = send_cluster_to_db(df_event, origin_time, cluster_col)
        cluster_data = send_cluster_to_kafka(df_event, cluster_id, origin_time, producer)
    
        # Update event kafka
        event_data = {
            'longitude': float(event_result['event_longitude']),
            'latitude': float(event_result['event_latitude']),
            'depth': float(event_result['event_depth']),
            'region': event_result['event_region'],
            'sub_region': event_result['event_sub_region'],
            'terrain': event_result['event_terrain'],
            'country': event_result['event_country'],
            'magnitude': float(event_result['magnitude']),
        }
        print(UTCDateTime.now(), event_data)

        # Send event to DB and kafka
        event_id, magnitude_ids = send_event_to_db(event_data, cluster_data, df_event, event_col, magnitude_col)
        send_event_to_kafka(event_data, cluster_data, df_event, event_id, magnitude_ids, producer)
        send_reloc_to_kafka(df_event, event_id, producer)

        redis_client.set('flag_origin_time_auto', int(origin_time.timestamp))
        print('DONE!')
        

def task(message):
    data = json_serializer(message)
    print("associating", UTCDateTime(data['picks'][0]['timestamp']), UTCDateTime.now())
    ai_itb_logmag_process(data, redis_client)


if __name__ == "__main__":
    print("Processing Locmag")

    for message in pick_consumer:
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKERS:
            print("System Overhead: Forced Stop!!!...............")
            break