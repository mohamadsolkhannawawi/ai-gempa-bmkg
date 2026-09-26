import os, redis, pymongo, threading, time, json, pytz
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
                            send_reloc_to_kafka

from utils.preprocessing import trace_processing

import skydrifter as sd
from skydrifter.PeculiarSupport.obspy_support import convert_timestamp

from config import *

# Instantiate some clients
# from redis.cluster import RedisCluster as Redis
# from redis.cluster import ClusterNode
# nodes = [ClusterNode(REDIS_HOST, REDIS_PORT), ]
# redis_client = Redis(startup_nodes=nodes)
# redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
arrival_pick_consumer = KafkaConsumer(ARRIVAL_PICK_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
cluster_col = db['cluster']
magnitude_col = db['magnitude']
event_col = db['event']

# Load models and data
base_path = './'

autoloc_path1 = base_path + r"skydrifter_file/implementation31mei/important_file_2/autoloc_epicenter_model.npy"
autoloc_path2 = base_path + r"skydrifter_file/implementation31mei/important_file_2/autoloc_depth_model.npy"
autoloc_model1 = np.load(autoloc_path1,allow_pickle='TRUE').item()
autoloc_model2 = np.load(autoloc_path2,allow_pickle='TRUE').item()
automag_path = base_path + r"skydrifter_file/implementation31mei/important_file_3/automag_model.npy"
automag_model = np.load(automag_path,allow_pickle='TRUE').item()

path = {
    "World Marine": base_path + r"skydrifter_file/implementation31mei/important_file_4/world_marine.shp",
    "World Land": base_path + r"skydrifter_file/implementation31mei/important_file_4/world_land.shp",
    "Indonesia Marine": base_path + r"skydrifter_file/implementation31mei/important_file_4/indonesia_marine.shp",
    "Indonesia Land": base_path + r"skydrifter_file/implementation31mei/important_file_4/indonesia_land.shp"
}

shp_out_marine = gpd.read_file(path['World Marine'])
gdf_out_marine = gpd.GeoSeries(shp_out_marine['geometry'])
shp_out_land = gpd.read_file(path['World Land'])
gdf_out_land = gpd.GeoSeries(shp_out_land['geometry'])
shp_ind_land = gpd.read_file(path['Indonesia Land'])
gdf_ind_land = gpd.GeoSeries(shp_ind_land['geometry'])
shp_ind_marine = gpd.read_file(path['Indonesia Marine'])
gdf_ind_marine = gpd.GeoSeries(shp_ind_marine['geometry'])

shp_dict = {
    'shp_out_marine': shp_out_marine,
    'gdf_out_marine': gdf_out_marine,
    'shp_out_land': shp_out_land, 
    'gdf_out_land': gdf_out_land, 
    'shp_ind_land': shp_ind_land, 
    'gdf_ind_land': gdf_ind_land, 
    'shp_ind_marine': shp_ind_marine,
    'gdf_ind_marine': gdf_ind_marine
}

to_timestamp = lambda x: UTCDateTime(x).timestamp

def ai_itb_logmag_process(data, r):
    # Store to redis
    redis_key = f"ai_association" 

    # TODO
    # sesuaikan struktur data yang sekarang ke data yg dibutuhin mas bondan
    # data =  {
    #     'station': data['station'],
    #     'pick_p': pick_P_dt,
    #     'pick_s': pick_S_dt,
    #     'longitude': station_data['longitude'],
    #     'latitude': station_data['latitude'],
    # }

    data = {
        'pick_source_id': data['pick_source_id'],
        'station': data['station'],
        'pick_p': [pick for pick in data['picks'] if pick['type'] == 'P'][0],
        'pick_s': [pick for pick in data['picks'] if pick['type'] == 'S'][0],
        'longitude': data['longitude'],
        'latitude': data['latitude'] 
    }

    r.xadd(redis_key, {"data": json.dumps(data)})

    expired_time = UTCDateTime(data['pick_p']['timestamp']) - OVERLAPS_SEC

    # Get all messages from the Redis stream
    messages = r.xrange(redis_key, "-", "+") 

    list_taken_time = []
    dict_taken_msg_id = {}
    dict_taken_pick_source_id = {}
    dict_taken_station = {}
    dict_taken_pick_p = {}
    dict_taken_pick_s = {}
    dict_taken_longitude = {}
    dict_taken_latitude = {}
    
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
        _pick_source_id = header['pick_source_id']
        _station = header['station']
        _pick_p = header['pick_p']
        _pick_s = header['pick_s']
        _longitude = float(header['longitude'])
        _latitude = float(header['latitude'])

        # Take the needed data back selection
        if expired_time < UTCDateTime(_time):
            # print("TAKEN =================", taken_starttime, _time)
            list_taken_time.append(_time)
            dict_taken_msg_id[_time] = msg_id
            dict_taken_pick_source_id[_time] = _pick_source_id
            dict_taken_station[_time] = _station
            dict_taken_pick_p[_time] = _pick_p
            dict_taken_pick_s[_time] = _pick_s
            dict_taken_longitude[_time] = _longitude
            dict_taken_latitude[_time] = _latitude
        else:
            # print("DELETE =================", _time)
            r.xdel(redis_key, msg_id)

    if len(list_taken_time)<4: return 0

    list_taken_time = sorted(list_taken_time)
    df_event = pd.DataFrame({
        'Station': [dict_taken_station[t] for t in list_taken_time],
        'Pick_source_ids': [dict_taken_pick_source_id[t] for t in list_taken_time],
        'P_dict': [dict_taken_pick_p[t] for t in list_taken_time],
        'S_dict': [dict_taken_pick_s[t] for t in list_taken_time],
        'P': [to_timestamp(dict_taken_pick_p[t]['timestamp']) for t in list_taken_time],
        'S': [to_timestamp(dict_taken_pick_s[t]['timestamp']) for t in list_taken_time],
        'X Station': [dict_taken_longitude[t] for t in list_taken_time],
        'Y Station': [dict_taken_latitude[t] for t in list_taken_time],
    })

    
    # Phase 4
    locator = sd.SeisAutoLoc(df_event, shp_dict)
    locator.execute(autoloc_model1=autoloc_model1, autoloc_model2=autoloc_model2)
    df_result = locator.df_loc
    
    # Validate event
    if df_result['Longitude'].iloc[0]==-1 and df_result['Latitude'].iloc[0]==-1: return 0
    
    # TODO
    # dibuat cluster dari df_event bisa, jika long lat valid
    # print(str(r.get(redis_key+'_temp'))[2:-1], str(list_taken_time[:3]),
    #       str(r.get(redis_key+'_temp'))[2:-1] == str(list_taken_time[:3]))
    if str(r.get(redis_key+'_temp'))[2:-1] == str(list_taken_time[:3]):
        return 0
    else:
        r.set(redis_key+'_temp', str(list_taken_time[:3]))

    # Send cluster to DB and kafka
    origin_time = min([UTCDateTime(p_pick_timestamp) for p_pick_timestamp in df_event['P'].values]) - ORIGIN_TIME_OFFSET_SEC
    cluster_id = send_cluster_to_db(df_event, origin_time, cluster_col)
    cluster_data = send_cluster_to_kafka(df_event, cluster_id, origin_time, producer)

    # Phase 5
    magnitude = sd.SeisAutoMag(df_event,locator.df_loc)
    magnitude.execute(automag_model=automag_model)
    df_result = magnitude.df_loc
    
    # TODO
    # Update event kafka

    event_data = {
        'longitude': float(df_result['Longitude'].iloc[0]),
        'latitude': float(df_result['Latitude'].iloc[0]),
        'depth': float(df_result['Depth'].iloc[0]),
        'region': df_result['Region'].iloc[0],
        'sub_region': df_result['Sub Region'].iloc[0],
        'terrain': df_result['Terrain'].iloc[0],
        'country': df_result['Country'].iloc[0],
        'magnitude': float(df_result['Magnitude'].iloc[0]),
    }
    print(UTCDateTime.now(), event_data)

    event_id, magnitude_ids = send_event_to_db(event_data, cluster_data, df_event, event_col, magnitude_col)
    send_event_to_kafka(event_data, cluster_data, df_event, event_id, magnitude_ids, producer)
    send_reloc_to_kafka(df_event, event_id, producer)
    print('DONE!')
    
    # ### JSON DEBUG
    # mkey = str(UTCDateTime.now())
    # r.hset("DEBUG PICK", mkey, json.dumps(df_event.to_dict('records')))
    # r.hset("DEBUG EVENT", mkey, json.dumps(event_data))


def task(message):
    data = json_serializer(message)
    ai_itb_logmag_process(data, redis_client)


if __name__ == "__main__":
    print("Processing Locmag")

    # redis_key = f"timestamp_association" 
    # redis_client.delete(redis_key)

    for message in arrival_pick_consumer:
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKER:
            print("System Overhead: Forced Stop!!!...............")
            break