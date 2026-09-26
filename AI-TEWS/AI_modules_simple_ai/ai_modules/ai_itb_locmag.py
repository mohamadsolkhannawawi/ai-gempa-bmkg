import os, redis, pymongo, threading, time, json, pytz
import numpy as np
import pandas as pd
import geopandas as gpd
import tensorflow as tf
from obspy import UTCDateTime, Trace, Stream
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer

from datetime import datetime, timezone

from utils.messaging import json_serializer
from utils.preprocessing import trace_processing

import skydrifter as sd
from skydrifter.PeculiarSupport.obspy_support import convert_timestamp
from PhaseNet1D_3001 import *

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

REDIS_HOST = os.getenv("redis_host")
REDIS_PORT = os.getenv("redis_port")

MONGO_HOST = os.getenv("database_host")
MONGO_PORT = os.getenv("database_port")

DB_NAME = os.getenv("database_name")

# Kafka topics
ARRIVAL_WAVEFORM_TOPIC = os.getenv("arrival_waveform_topic")
EVENT_TOPIC = os.getenv("event_topic")

WINDOW_SIZE_SEC = 300
OVERLAPS_SEC = 180
MAX_WORKER = 1000

# Instantiate some clients
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
pick_consumer = KafkaConsumer(ARRIVAL_WAVEFORM_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]

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
    redis_key = f"timestamp_association" 

    # TODO
    # sesuaikan struktur data yang sekarang ke data yg dibutuhin mas bondan
    # data =  {
    #     'station': data['station'],
    #     'pick_p': pick_P_dt,
    #     'pick_s': pick_S_dt,
    #     'longitude': station_data['longitude'],
    #     'latitude': station_data['latitude'],
    # }
    r.xadd(redis_key, {"data": json.dumps(data)})

    expired_time = UTCDateTime.now() - OVERLAPS_SEC

    # Get all messages from the Redis stream
    messages = r.xrange(redis_key, "-", "+") 

    list_taken_time = []
    dict_taken_msg_id = {}
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
            _time = header['pick_p']
        except:
            continue
        _station = header['station']
        _pick_p = header['pick_p']
        _pick_s = header['pick_s']
        _longitude = float(header['longitude'])
        _latitude = float(header['latitude'])

        # Take the needed data back selection
        if expired_time > UTCDateTime(_time):
            # print("TAKEN =================", taken_starttime, _time)
            list_taken_time.append(_time)
            dict_taken_msg_id[_time] = msg_id
            dict_taken_station[_time] = _station
            dict_taken_pick_p[_time] = to_timestamp(_pick_p)
            dict_taken_pick_s[_time] = to_timestamp(_pick_s)
            dict_taken_longitude[_time] = _longitude
            dict_taken_latitude[_time] = _latitude
        else:
            # print("DELETE =================", _time)
            r.xdel(redis_key, msg_id)

    if len(list_taken_time)<4: return 0

    list_taken_time = sorted(list_taken_time)
    df_event = pd.DataFrame({
        'Station': [dict_taken_station[t] for t in list_taken_time],
        'P': [dict_taken_pick_p[t] for t in list_taken_time],
        'S': [dict_taken_pick_s[t] for t in list_taken_time],
        'X Station': [dict_taken_longitude[t] for t in list_taken_time],
        'Y Station': [dict_taken_latitude[t] for t in list_taken_time],
    })

    
    # Phase 4
    locator = sd.SeisAutoLoc(df_event, shp_dict)
    locator.execute(autoloc_model1=autoloc_model1, autoloc_model2=autoloc_model2)
    df_result = locator.df_loc
    
    print(UTCDateTime.now(), list_taken_time[0], df_result.iloc[0])
    # Validate event
    if df_result['Longitude'].iloc[0]==-1 and df_result['Latitude'].iloc[0]==-1: return 0
    
    # TODO
    # dibuat cluster dari df_event bisa, jika long lat valid

    # Phase 5
    magnitude = sd.SeisAutoMag(df_event,locator.df_loc)
    magnitude.execute(automag_model=automag_model)
    df_result = magnitude.df_loc
    
    event_data = {
        'longitude': df_result['Longitude'].iloc[0],
        'latitude': df_result['Latitude'].iloc[0],
        'depth': df_result['Depth'].iloc[0],
        'region': df_result['Region'].iloc[0],
        'sub_region': df_result['Sub Region'].iloc[0],
        'terrain': df_result['Terrain'].iloc[0],
        'country': df_result['Country'].iloc[0],
        'magnitude': df_result['Magnitude'].iloc[0],
    }
    producer.send(EVENT_TOPIC, json.dumps(event_data).encode())

def task(message):
    data = json_serializer(message)
    ai_itb_logmag_process(data, redis_client)


if __name__ == "__main__":
    print("Processing Locmag")

    redis_key = f"timestamp_association" 
    redis_client.delete(redis_key)

    for message in pick_consumer:
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKER:
            print("System Overhead: Forced Stop!!!...............")
            break