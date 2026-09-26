import os, redis, pymongo, threading, time, json, pytz, logging, traceback
import numpy as np
import pandas as pd
import geopandas as gpd
from bson.objectid import ObjectId
from obspy import UTCDateTime, Trace, Stream
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer

from utils.messaging import json_serializer, \
                            send_or_update_cluster_to_db, \
                            send_or_update_event_to_db, \
                            send_or_update_arrival_to_db, \
                            send_relocmag_to_kafka
                

from utils.preprocessing import trace_processing

import skydrifter as sd
from skydrifter.PeculiarSupport.obspy_support import convert_timestamp

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

def ai_itb_relogmag_process(data, r, user_id):
    try:
        user_id = ObjectId(user_id)
        stations = {}
        if type(data['arrival_list'][0])==dict:
            print("Type dict, relocmag for event commit")
            for arrival in data['arrival_list']:
                # Insert or update arrivals to DB
                sta_id = arrival['station_id']
                station = db['station'].find_one({'_id': ObjectId(sta_id)})
                arrival_id = send_or_update_arrival_to_db(arrival, station, arrival['pick_source_id'], arrival_col, user_id)
                
                try:
                    stations[sta_id]['timestamp_'+arrival['phase_type']] = {'_id': str(arrival_id),
                                                                            'timestamp': arrival['timestamp']}
                    stations[sta_id]['pick_source_id'] = arrival['pick_source_id']
                    stations[sta_id]['station'] = station
                except:
                    stations[sta_id] = {'timestamp_'+arrival['phase_type']: {'_id': str(arrival_id),
                                                                            'timestamp': arrival['timestamp']}}
            
                # create arrival_pick object (db)
                # pick_arrival_data = {
                #     'P': {'timestamp': stations[key]['timestamp_P']},
                #     'S': {'timestamp': stations[key]['timestamp_S']},
                # }
                # pick_arrival_data['P']['_id'] = p_arrival_id
                # pick_arrival_data['S']['_id'] = s_arrival_id
                # send_arrivals_to_kafka(pick_arrival_data, stations[key]['station'], pick_id, producer, user_id)
        else:
            print("Relocmag for normal AI pipeline")
            # Used for relocmag with no event commit
            for arrival_id in data['arrival_list']:
                arrival = db['arrival'].find_one({'_id': ObjectId(arrival_id)})
                sta_id = arrival['station_id']
                # user = db['user'].find_one({'_id': user_id})
                # if sta_id in user['disable_stations']:
                #     continue
                station = db['station'].find_one({'_id': sta_id})
                try:
                    stations[sta_id]['timestamp_'+arrival['phase_type']] = {'_id': arrival_id,
                                                                            'timestamp': arrival['timestamp']}
                    stations[sta_id]['pick_source_id'] = arrival['pick_source_id']
                    stations[sta_id]['station'] = station
                except:
                    stations[sta_id] = {'timestamp_'+arrival['phase_type']: {'_id': arrival_id,
                                                                            'timestamp': arrival['timestamp']}}
            
        # TODO: needs handling on any None data        
        db_event = db['event'].find_one({'_id': ObjectId(data['event_id'])})
        if db_event.get('event_auto_ref_id') != None:
            event_auto_ref_id = ObjectId(db_event['event_auto_ref_id'])
            print("(Update) Preserving old auto id: ", event_auto_ref_id)
        else:
            event_auto_ref_id = data['event_id']
            print("(Insert) Using current event id as autorefid: ", event_auto_ref_id)
                
        df_event = pd.DataFrame({
            #'_id': str(db_event['cluster_id']),
            'Station': [stations[key]['station']['code'] for key in stations],
            'Pick_source_ids': [stations[key]['pick_source_id'] for key in stations],
            'P_dict': [stations[key]['timestamp_P'] for key in stations],
            'S_dict': [stations[key]['timestamp_S'] for key in stations],
            'P': [to_timestamp(stations[key]['timestamp_P']['timestamp']) for key in stations],
            'S': [to_timestamp(stations[key]['timestamp_S']['timestamp']) for key in stations],
            'X Station': [stations[key]['station']['longitude'] for key in stations],
            'Y Station': [stations[key]['station']['latitude'] for key in stations],
        }).sort_values('P').reset_index(drop=True)
        
        print(df_event)
        # Phase 4
        locator = sd.SeisAutoLoc(df_event, shp_dict)
        locator.execute(autoloc_model1=autoloc_model1, autoloc_model2=autoloc_model2)
        df_result = locator.df_loc
        
        # Send cluster to DB and kafka
        origin_time = min([UTCDateTime(p_pick_timestamp) for p_pick_timestamp in df_event['P'].values]) - ORIGIN_TIME_OFFSET_SEC
        cluster_id = send_or_update_cluster_to_db(df_event, str(db_event['cluster_id']), origin_time, cluster_col, user_id)
        # cluster_data = send_cluster_to_kafka(df_event, cluster_id, origin_time, producer, user_id)
        cluster_data = {
            '_id': str(cluster_id), 
            'origin_time': str(origin_time),
            'rank': 1,
            'picks': [str(pick_id) for pick_id in df_event['Pick_source_ids'].values],
            'modified_by': user_id,
        }

        # Phase 5
        # Validate event, if no relocation, then use old locmag
        if df_result['Longitude'].iloc[0]==-1 and df_result['Latitude'].iloc[0]==-1:
            print("AI relocmag didn't find new locmag, using old event data: ", event_auto_ref_id)
            db_magnitude = magnitude_col.find_one({"_id": db_event['magnitude_ids'][0]})
            
            if db_magnitude != None:
                event_data = {
                    'longitude': float(db_event['longitude']),
                    'latitude': float(db_event['latitude']),
                    'depth': float(db_event['depth']),
                    'region': db_event['region'],
                    'sub_region': db_event['sub_region'],
                    'terrain': db_event['terrain'],
                    'country': db_event['country'],
                    'magnitude': db_magnitude['value'],
                }
            else:
                 raise Exception(f"Magnitude with ID {db_event['magnitude_id']} not found! Please ensure that this is an update operation")
        else:
            print("AI relocmag found a new locmag: ", event_auto_ref_id)
            magnitude = sd.SeisAutoMag(df_event,locator.df_loc)
            magnitude.execute(automag_model=automag_model)
            df_result = magnitude.df_loc
        
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

        event_id, magnitude_ids = send_or_update_event_to_db(event_data, cluster_data, df_event, db_event, event_col, magnitude_col, user_id, event_auto_ref_id)
        send_relocmag_to_kafka(event_data, cluster_data, df_event, event_id, magnitude_ids, producer, user_id, event_auto_ref_id)
        print("Finished relocmag!")
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        
def task(message):
    data = json_serializer(message)
    ai_itb_relogmag_process(data, redis_client, data["user_id"])

if __name__ == "__main__":
    print("Processing ReLocMag")

    for message in relocmag_consumer:
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKER:
            print("System Overhead: Forced Stop!!!...............")
            break