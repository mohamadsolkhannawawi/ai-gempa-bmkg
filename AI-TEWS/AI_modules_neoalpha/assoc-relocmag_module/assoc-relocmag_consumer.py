import os, redis, pymongo, threading, time, json, pytz, copy, sys
import numpy as np
import pandas as pd
from bson.objectid import ObjectId
from obspy import UTCDateTime, Trace, Stream
from kafka import KafkaConsumer, KafkaProducer
from utils.messaging import json_serializer
from utils.messaging import json_serializer, \
                            send_station_magnitudes_to_db, \
                            send_magnitudes_to_db
                            
from utils.preprocessing import get_channel_stream, \
                                get_channel_fdsn, \
                                get_recordstream

import skydrifter as sd
from skydrifter.SeisEventAnalyzer.Magnitude import determine_station_magnitude_m100

from config import *

STADICT = {}
POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
origin_consumer = KafkaConsumer(ORIGIN_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
origin_col = db['origin']
magnitude_col = db['magnitude']
station_magnitude_col = db['station_magnitude']

to_timestamp = lambda x: UTCDateTime(x).timestamp

def calculate_conventional_M100(associated_arrivals, latitude, longitude, depth):
    """
    Calculate Conventional M100 for each station given associated arrival data, and average to get preferred magnitude.
    
    Parameters
    ----------
    associated_arrivals : pandas.DataFrame
        DataFrame containing associated arrival data with columns:
            - Station
            - Pick_source_id
            - P_dict
            - S_dict
            - P
            - S
            - X Station
            - Y Station
    
    Returns
    -------
    station_M100 : list of dict
        List of dictionaries containing station M100 data with keys:
            - pick_source_id
            - station_id
            - value
            - type
            - waveform_start
            - waveform_end
    preferred_M100 : float
        Preferred magnitude from average of station M100
    """
    ## Conventional M100
    station_M100 = []
    for i, arrival in associated_arrivals.iterrows():
        try:
            # Get station data and default channel from STADICT
            if STADICT.get(arrival['Station']) == None:
                print(f"Station {arrival['Station']} not found in DB")
                continue
            network, code = arrival['Station'].split('.')
            location, channel = STADICT[arrival['Station']].split('.')
            
            arrival['Station'] = code
            arrival['Latitude'] = latitude
            arrival['Longitude'] = longitude
            arrival['Depth'] = depth
            
            # Define waveform starttime and endtime for trace cutting
            S_BEFORE_OFFSET_SEC = 10
            S_AFTER_OFFSET_SEC = 100
            
            starttime = UTCDateTime(arrival['S']) - S_BEFORE_OFFSET_SEC
            endtime = UTCDateTime(arrival['S']) + S_AFTER_OFFSET_SEC
            window_size_sec = endtime - starttime
            start_finding = UTCDateTime.now()
            
            # Get stream for Z channel from waveform starttime and endtime from cache
            key = f"aicache_{network}.{code}.{location}.{channel}_data"
            st = Stream()
            print(f"[INFO M100] ({UTCDateTime.now()}) Getting stream for pick_source_id {arrival['Pick_source_ids']}, retrying until {start_finding + M100_CALC_TIME_LIMIT_SEC})")
            print(f"[INFO M100] ({UTCDateTime.now()}) {arrival['Pick_source_ids']}: {starttime} {endtime} {window_size_sec} {key}")
            while UTCDateTime.now() < start_finding + M100_CALC_TIME_LIMIT_SEC:
                # VERSION 1: Manual
                try:
                    st = get_channel_stream(key.replace(channel, channel[:-1]+'Z'), 
                                            endtime, 
                                            window_size_sec, 
                                            redis_client)
                except:
                    pass

                # Get stream for Z channel from waveform starttime and endtime from archive
                if len(st) == 0:
                    st = get_channel_fdsn(network, code, location, channel[:-1]+'Z', starttime, endtime, FDSN_SERVER_HOST)

                # # VERSION 2: Using recordstream
                # try:
                #     st = get_recordstream(network, code, location, channel[:-1]+'Z', starttime, endtime, RECORDSTREAM_SERVER_HOST)
                # except Exception as e:
                #     print(e)
                #     sys.stdout.flush()
                
                if len(st) == 0:
                    # print(f"[INFO M100] ({UTCDateTime.now()}) Stream for pick_source_id {arrival['Pick_source_ids']}, retrying until {endtime + M100_CALC_TIME_LIMIT_SEC})")
                    time.sleep(M100_CALC_TIME_INTERVAL_SEC)
                else:
                    # Check if stream is already correct
                    if st[0].stats.starttime - starttime > M100_WAVEFORM_MAX_DIFF or st[0].stats.endtime - endtime > M100_WAVEFORM_MAX_DIFF:
                        print(f"[INFO M100] ({UTCDateTime.now()}) Unique: Incomplete stream for pick_source_id {arrival['Pick_source_ids']}")
                        print("Waveform time:", st[0].stats.starttime, starttime, st[0].stats.endtime, endtime)
                        time.sleep(M100_CALC_TIME_INTERVAL_SEC)
                        continue
                        
                    print(f"[INFO M100] ({UTCDateTime.now()}) Stream for pick_source_id {arrival['Pick_source_ids']} found")
                    print("Waveform time:", st[0].stats.starttime, starttime, st[0].stats.endtime, endtime)
                    print("Differences:", st[0].stats.starttime - starttime, st[0].stats.endtime - endtime)
                    break
                
            # Debug stream
            print(st)
            sys.stdout.flush()
            
            # Check if stream is filled or not
            if len(st) == 0:
                print(f"[WARNING M100] ({UTCDateTime.now()}) Data from cache and archive not found, skipping magnitude for pick_source_id {arrival['Pick_source_ids']}")
                continue
                
            # # Fill in missing data with mean
            # temp_value = np.ones(len(st[0].data))*np.mean(st[0].data)
            # temp_value[:len(st[0].data)] = st[0].data[:len(st[0].data)]
            # st[0].data = temp_value[:]
            
            # # Fill in missing data with mean
            temp = st[0].data.copy()
            temp[temp == None] = 0
            st[0].data[st[0].data == None] = np.mean(temp)
                
            # Get local magnitude for current arrival and structure into DB object
            try:
                M100_value = determine_station_magnitude_m100(arrival, st, station_xml)
                station_M100.append({
                    'pick_source_id': ObjectId(arrival['Pick_source_ids']),
                    'station_id': ObjectId(arrival['P_dict']['station_id']),
                    'value': M100_value,
                    'type': 'M100',
                    'waveform_start': starttime.datetime,
                    'waveform_end': endtime.datetime
                })
            except Exception as e:
                raise e
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ERROR M100] ({UTCDateTime.now()}) Error while processing M100: pick_source_id {arrival['Pick_source_ids']}")
            print(e)
            sys.stdout.flush()
            continue
            
    # Get average of station M100 to get preferred magnitude
    preferred_M100 = np.median(np.array([M100['value'] for M100 in station_M100]))
    
    return preferred_M100, station_M100

def process_origin_from_arrivals(associated_arrivals, df_ori_loc=[]):
    
    # Get necessary location data from defined models
    # print(associated_arrivals)
    # df_loc_ai = calculate_ai_loc(associated_arrivals)      # For depth
    # df_nlloc = calculate_nonlinloc(associated_arrivals)    # For longitude and latitude
    # df_nlloc.columns = df_nlloc.columns.str.strip()
    
    # # Get region from preferred location model (current: NLLoc)
    # df_region_loc = region_binning(df_nlloc['longitude'], df_nlloc['latitude'], df_nlloc['depth'], shp_dict)
    
    # Validate event
    # if df_result['latitude'].iloc[0]==-1 or df_result['longitude'].iloc[0]==-1: return 0, 0
    
    # Calculate global magnitude and define all global / preferred magnitude data
    # TODO: would be better with relocated location data
    if len(df_ori_loc) != 0:
        calculated_magnitudes = {
            'M100': calculate_conventional_M100(associated_arrivals,
                                                df_ori_loc['latitude'],
                                                df_ori_loc['longitude'],
                                                df_ori_loc['depth']),
        }
    else:
        print("No location, skipping magnitude calculation")
        return 0, 0
    print(calculated_magnitudes)
    
    # Restructure magnitude data and remove empty magnitudes
    magnitudes = []
    station_magnitudes_per_type = []
    for magnitude_type, magnitude_data in calculated_magnitudes.items():
        print(magnitude_data)
        # Handle station magnitude
        if type(magnitude_data) == tuple:
            # assert type(magnitude_data[0]) == float and type(magnitude_data[1]) == list, f"Station magnitude must include preferred magnitude and list of station magnitudes (received: {magnitude_data})"
            if len(magnitude_data[1]) == 0:
                print(f"[WARNING MAGNITUDE] ({UTCDateTime.now()}) Station magnitude not found for {magnitude_type}")
            else:
                magnitudes.append({
                    'type': magnitude_type,
                    'value': magnitude_data[0]
                })
                station_magnitudes_per_type.append({
                    'type': magnitude_type,
                    'station_magnitudes': magnitude_data[1]
                })
        # Handle magnitudes
        else:
            magnitudes.append({
                'type': magnitude_type,
                'value': magnitude_data
            })
    
    # Define origin
    # try:
    #     ## NLLoc
    #     origin_time = UTCDateTime(df_nlloc['date-time'].iloc[0])
    # except ValueError:
    #     ## No AI
    #     origin_time = min([UTCDateTime(p_pick_timestamp) for p_pick_timestamp in associated_arrivals['P'].values]) - ORIGIN_TIME_OFFSET_SEC
    
    locmag_data = {
        # 'longitude': float(df_nlloc['longitude'].iloc[0]),
        # 'latitude': float(df_nlloc['latitude'].iloc[0]),
        # 'depth': float(df_loc_ai['Depth'].iloc[0]),
        # 'region': df_region_loc['Region'].iloc[0],
        # 'sub_region': df_region_loc['Sub Region'].iloc[0],
        # 'terrain': df_region_loc['Terrain'].iloc[0],
        # 'country': df_region_loc['Country'].iloc[0],
        'magnitudes': magnitudes,
        'station_magnitudes_per_type': station_magnitudes_per_type
    }
    print(UTCDateTime.now(), locmag_data)
    
    # return locmag_data, origin_time
    return locmag_data, UTCDateTime.now()

def consume_relocmag_task(message):
    """
    Consume relocmag task from Kafka. Insert or update arrivals to DB, associate arrivals with origin, process AI origin, associate origin with event, and send event to Kafka.

    Parameters
    ----------
    message : bytes
        Kafka message containing relocmag data in JSON format.

    Returns
    -------
    None
    """
    # Insert or update arrivals to DB
    data = json_serializer(message)
    stations = {}
    for arrival in data['arrivals']:
        sta_id = arrival['station_id']
        station = db['station'].find_one({'_id': ObjectId(sta_id)})
        
        try:
            stations[sta_id]['timestamp_'+arrival['phase_type']] = {'_id': str(arrival['_id']),
                                                                    'timestamp': arrival['timestamp'],
                                                                    'station_id': sta_id}
            stations[sta_id]['pick_source_id'] = arrival['pick_source_id']
            stations[sta_id]['station'] = station
        except Exception as e:
            stations[sta_id] = {'timestamp_'+arrival['phase_type']: {'_id': str(arrival['_id']),
                                                                    'timestamp': arrival['timestamp'],
                                                                    'station_id': sta_id}}
        stations[sta_id]['checked'] = arrival.get('checked', True)
    
    # Associate arrivals with origin
    associated_arrivals = pd.DataFrame({
        'Station': [f"{stations[key]['station']['network']}.{stations[key]['station']['code']}" for key in stations],
        'Pick_source_ids': [stations[key]['pick_source_id'] for key in stations],
        'P_dict': [stations[key]['timestamp_P'] for key in stations],
        'S_dict': [stations[key]['timestamp_S'] for key in stations],
        'P': [to_timestamp(stations[key]['timestamp_P']['timestamp']) for key in stations],
        'S': [to_timestamp(stations[key]['timestamp_S']['timestamp']) for key in stations],
        'X Station': [stations[key]['station']['longitude'] for key in stations],
        'Y Station': [stations[key]['station']['latitude'] for key in stations],
        'Used': [stations[key]['checked'] for key in stations],
    }).sort_values('P').reset_index(drop=True)
    print(associated_arrivals)
    # Process AI origin from associated arrivals
    locmag_data, origin_time = process_origin_from_arrivals(associated_arrivals, {
        "latitude": data['latitude'],
        "longitude": data['longitude'],
        "depth": data['depth']
    })

    if locmag_data == 0:
        return
    
    # Insert all new magnitudes to DB
    # TODO: validation when empty magnitudes
    magnitude_ids = send_magnitudes_to_db(locmag_data['magnitudes'], data['modified_by'], data['created_at'], magnitude_col, modified_at=UTCDateTime.now().datetime)
    station_magnitudes_ids_per_type = send_station_magnitudes_to_db(locmag_data['station_magnitudes_per_type'], data['modified_by'], data['created_at'], station_magnitude_col)
    
    ## Handle Origin data
    # Input shape:
    # origin_data['magnitudes'] = [
    #     {
    #         '_id': str(magnitude_id),
    #         **magnitude,
    #         'modified_by': user_id,
    #         'created_at': created_at,
    #         'modified_at': UTCDateTime().now().datetime if db_updated_origin == None else None
    #     }
    #     for magnitude_id, magnitude in zip(magnitude_ids, locmag_data['magnitudes'])
    # ]
    
    # origin_data['station_magnitudes_per_type'] = [
    #     {
    #         'type': station_magnitude_ids['type'],
    #         'station_magnitudes': [
    #             {
    #                 '_id': str(station_magnitude_id),
    #                 **station_magnitude_values,
    #                 'modified_by': user_id,
    #                 'created_at': created_at,
    #                 'modified_at': UTCDateTime().now().datetime if db_updated_origin == None else None
    #             }
    #             for station_magnitude_id, station_magnitude_values in zip(station_magnitude_ids['station_magnitude_ids'], station_magnitudes['station_magnitudes'])
    #         ]
    #     }
    #     for station_magnitude_ids, station_magnitudes in zip(station_magnitude_ids_per_type, locmag_data['station_magnitudes_per_type'])
    # ]
    
    # Get origin magnitude and station magnitude ids and combine with new magnitude and station magnitude ids
    relocmag_magnitude_ids = [ObjectId(magnitude['_id']) for magnitude in data['magnitudes']] + magnitude_ids
    relocmag_station_magnitude_ids_per_type = [
        {
            'type': station_magnitudes_per_type['type'],
            'station_magnitude_ids': [ObjectId(station_magnitude['_id']) for station_magnitude in station_magnitudes_per_type['station_magnitudes']]
        }
        for station_magnitudes_per_type in data['station_magnitudes_per_type']
    ] + station_magnitudes_ids_per_type
    
    # Insert origin data
    db_origin_data = {
        'magnitude_ids': relocmag_magnitude_ids,
        'station_magnitude_ids_per_type': relocmag_station_magnitude_ids_per_type,
    }

    print(f"Updating relocmag for origin {data['_id']}")
    db_origin_data = {"$set": db_origin_data}
    origin_col.update_one({"_id": ObjectId(data["_id"])}, db_origin_data)

if __name__ == "__main__":
    print("Processing ReLocMag")
    # TODO
    ### DUMMY
    # Get station default channels
    for sta in list(db['user'].find({"username":USER_NAME}))[0]['stations']:
        station = db['station'].find_one({"_id":ObjectId(sta)})
        try:
            # Filter channels (BH and SH)
            station['channel'] = sorted([ch for ch in station['channel'] if 'BH' in ch or 'SH' in ch])[0][:-1]
            code = station['network']+'.'+station['code']
            STADICT[code] = f"{station['location']}.{station['channel']}?"
        except: pass
    ###

    for message in origin_consumer:
        thread = threading.Thread(target=consume_relocmag_task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKERS:
            print("System Overhead: Forced Stop!!!...............")
            break