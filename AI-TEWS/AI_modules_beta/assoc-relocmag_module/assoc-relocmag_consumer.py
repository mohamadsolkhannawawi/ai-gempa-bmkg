import os, redis, pymongo, threading, time, json, pytz, copy
import numpy as np
import pandas as pd
import geopandas as gpd
from bson.objectid import ObjectId
from obspy import UTCDateTime, Trace, Stream
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer

from utils.messaging import json_serializer, \
                            send_cluster_to_db, \
                            send_cluster_to_kafka, \
                            send_event_to_db, \
                            send_event_to_kafka, \
                            send_arrivals_to_db, \
                            send_arrivals_to_kafka, \
                            get_inventory

import skydrifter as sd

from config import *

POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
relocmag_consumer = KafkaConsumer(RELOCATION_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
cluster_col = db['cluster']
magnitude_col = db['magnitude']
event_col = db['event']
arrival_col = db['arrival']

to_timestamp = lambda x: UTCDateTime(x).timestamp

def ai_itb_relogmag_process(data, r, username):
    user_id = ObjectId(username)
    stations = {}
    pick_arrival_list = {'P':[],'S':[]}
    if type(data['arrival_list'][0])==dict:
        for arrival in data['arrival_list']:
            print(arrival)
            sta_id = arrival['station_id']
            station = db['station'].find_one({'_id': ObjectId(sta_id)})
            try:
                stations[sta_id]['timestamp_'+arrival['phase_type']] = arrival['timestamp']
                stations[sta_id]['pick_source_id'] = arrival['pick_source_id']
                stations[sta_id]['station'] = station
            except:
                stations[sta_id] = {'timestamp_'+arrival['phase_type']: arrival['timestamp']}
        
        for key in stations:
            # create arrival_pick object (db)
            pick_arrival_data = {
                'P': {'timestamp': stations[key]['timestamp_P']},
                'S': {'timestamp': stations[key]['timestamp_S']},
            }
            pick_id = stations[key]['pick_source_id']
            p_arrival_id, s_arrival_id = send_arrivals_to_db(pick_arrival_data, stations[key]['station'], pick_id, arrival_col, user_id)
            pick_arrival_data['P']['_id'] = p_arrival_id
            pick_arrival_data['S']['_id'] = s_arrival_id
            send_arrivals_to_kafka(pick_arrival_data, stations[key]['station'], pick_id, producer, user_id)
            pick_arrival_list['P'].append(pick_arrival_data['P'])
            pick_arrival_list['S'].append(pick_arrival_data['S'])
    else:
        for arrival_id in data['arrival_list']:
            arrival = db['arrival'].find_one({'_id': ObjectId(arrival_id)})
            user = db['user'].find_one({'username': user_id})
            sta_id = arrival['station_id']
            if sta_id in user['disable_stations']:
                continue
            station = db['station'].find_one({'_id': sta_id})
            try:
                stations[sta_id]['timestamp_'+arrival['phase_type']] = arrival['timestamp']
                stations[sta_id]['pick_source_id'] = arrival['pick_source_id']
                stations[sta_id]['station'] = station
            except:
                stations[sta_id] = {'timestamp_'+arrival['phase_type']: arrival['timestamp']}
    
    try:
        event_auto_ref_id = ObjectId(data['event_auto_ref_id'])
    except:
        event_auto_ref_id = None

    df_event = pd.DataFrame({
        'station': [stations[key]['station']['code'] for key in stations],
        'P': [UTCDateTime(stations[key]['timestamp_P']) for key in stations],
        'P_snr': [15 for key in stations],
        'P_dict': pick_arrival_list['P'],
        'S_dict': pick_arrival_list['S'],
    }).sort_values('P')

    event_params = df_event[['station','P','P_snr']].to_dict('records')

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
        except:
            pass

    list_origin = []
    for key in list(flow.inactive_event.keys()):
        event_result = flow.inactive_event[key].event_feature
        if event_result['origin_time']==None: continue
        if event_result['event_longitude']<0: continue
        list_origin.append(event_result)
    for key in list(flow.active_event.keys()):
        event_result = flow.active_event[key].event_feature
        if event_result['origin_time']==None: continue
        if event_result['event_longitude']<0: continue
        list_origin.append(event_result)

    if len(list_origin)>0:
        event_result = list_origin[-1]
        # Send cluster to DB and kafka
        origin_time = event_result['origin_time']
        if type(origin_time)==str: origin_time = UTCDateTime(origin_time)

        # Send cluster to DB and kafka
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
        event_id, magnitude_ids = send_event_to_db(event_data, cluster_data, df_event, event_col, magnitude_col, user_id, event_auto_ref_id)
        send_event_to_kafka(event_data, cluster_data, df_event, event_id, magnitude_ids, producer, user_id, event_auto_ref_id)
        print('DONE!')

    
def task(message):
    RELOCMAG_MODULE = 'DEFAULT'
    data = json_serializer(message)
    for user in db['user'].find({}):
        print(user['username'])
        if RELOCMAG_MODULE.lower()=='default':
            ai_itb_relogmag_process(data, redis_client, user['_id'])
        elif RELOCMAG_MODULE.lower()=='specific':
            pass

if __name__ == "__main__":
    print("Processing ReLocMag")

    for message in relocmag_consumer:
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKERS:
            print("System Overhead: Forced Stop!!!...............")
            break