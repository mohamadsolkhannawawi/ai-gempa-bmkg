import os, obspy, redis, pymongo, threading, time, json
import numpy as np
import pandas as pd
from obspy import UTCDateTime
from kafka import KafkaProducer
from bson import ObjectId
import asyncio
from aiokafka import AIOKafkaConsumer
from typing import List, Dict, Any, Tuple

from utils.messaging import json_serializer, \
                            convert_object_ids, \
                            send_or_update_arrival_to_db, \
                            handle_insert_or_update_existing_origin_to_db, \
                            send_origin_to_db
                            
from utils.preprocessing import get_channel_stream, \
                                get_channel_fdsn, \
                                convert_latitude_to_km, \
                                convert_longitude_to_km
                            
import skydrifter as sd
from skydrifter.SeisEventAnalyzer.Location import nlloc_global, region_binning
from skydrifter.SeisEventAnalyzer.Magnitude import determine_station_magnitude_MLv

from config import *

STADICT = {}

POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
# arrival_pick_consumer = KafkaConsumer(ARRIVAL_PICK_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
arrival_col = db['arrival']
origin_col = db['origin']
magnitude_col = db['magnitude']
station_magnitude_col = db['station_magnitude']
event_col = db['event']

# TODO: DEBUG, remove all test_col later
origin_test_col = db['origin_test']
magnitude_test_col = db['magnitude_test']
station_magnitude_test_col = db['station_magnitude_test']
# event_test_col = db['event_test']

to_timestamp = lambda x: UTCDateTime(x).timestamp

# Define redis key for association
redis_key = f"ai_association" 

def arrival_association(data, r):
    """
    Associate the arrival of P and S phase from the same event 
    and from the same station. The association is done towards data
    from the Redis within a certain time window.
    
    Parameters
    ----------
    data : dict
        The data to be stored in the Redis. The data should contain 
        the pick_source_id, station, pick_p, pick_s, station longitude, 
        and station latitude.
    r : redis client
        The Redis client to access the Redis database.
    
    Returns
    -------
    associated_arrivals : pandas.DataFrame
        The associated arrival of P and S phase.
    """
    
    # Restucture data to fit with the format
    # data =  {
    #     'station': data['station'],
    #     'pick_p': pick_P_dt,
    #     'pick_s': pick_S_dt,
    #     'longitude': station_data['longitude'],
    #     'latitude': station_data['latitude'],
    # }
    data = {
        'pick_source_id': data['pick_source_id'],
        'station': f"{data['network']}.{data['station']}",
        'pick_p': [pick for pick in data['picks'] if pick['type'] == 'P'][0],
        'pick_s': [pick for pick in data['picks'] if pick['type'] == 'S'][0],
        'longitude': data['longitude'],
        'latitude': data['latitude'] 
    }

    # Store data to redis
    r.xadd(redis_key, {"data": json.dumps(data)})
    
    expired_time = UTCDateTime(data['pick_p']['timestamp']) - OVERLAPS_SEC

    expired_time = UTCDateTime(data['pick_p']['timestamp']) - ASSOCIATION_EXPIRED_SEC

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

    if len(list_taken_time)<N_STATION: return 0
    
    # VERSION 1: use all station as reference
    # Associate picks and limit by station distance
    associated_arrival_times = [] # list[list[arrival_time]]
    associated_station_epicenters_km = [] # list[station_epicenter: np.array(longitude, latitude)]
    for arrival_time in list_taken_time:
        associated = False 
        taken_epicenter_km = np.array([convert_latitude_to_km(dict_taken_latitude[arrival_time]), 
                                       convert_longitude_to_km(dict_taken_longitude[arrival_time], dict_taken_latitude[arrival_time])])
        debug_distances_km = []
        for i, associated_station_epicenter_km in enumerate(associated_station_epicenters_km):
            # Calculate distance against each station
            distances_km = np.linalg.norm(associated_station_epicenter_km - taken_epicenter_km, axis=1)
            
            # Skip if there are same stations
            same_station = distances_km[distances_km == 0]
            if len(same_station) != 0:
                continue
            
            # If distance is less than threshold, insert arrival to associate with it
            if np.min(distances_km) <= ASSOCIATION_STATION_DISTANCE_MIN_KM:
                associated_arrival_times[i].append(arrival_time)
                associated_station_epicenters_km[i] = np.vstack((associated_station_epicenter_km, taken_epicenter_km)) 
                associated = True
            
            debug_distances_km.append(distances_km)
                
        # If can't associate with any available arrivals, make new one
        if not associated:
            associated_arrival_times.append([arrival_time])
            associated_station_epicenters_km.append([taken_epicenter_km])
        
        print(associated, debug_distances_km)
        print([np.min(distances) for distances in debug_distances_km])
    
    # VERSION 2: use only first station as reference
    # # Sort arrival time first
    # list_taken_time = sorted(list_taken_time, key=lambda x: UTCDateTime(x))
    # list_taken_time = [str(time) for time in list_taken_time]
    
    # # Associate picks and limit by station distance
    # associated_arrival_times = [] # list[list[arrival_time]]
    # associated_station_epicenters_km = [] # list[tuple(pivot_arrival: arrival_time, pivot_station_epicenters: tuple(longitude1, latitude1))]
    # for arrival_time in list_taken_time:
    #     taken_epicenter_km = (convert_latitude_to_km(dict_taken_latitude[arrival_time]), 
    #                           convert_longitude_to_km(dict_taken_longitude[arrival_time], dict_taken_latitude[arrival_time]))
        
    #     associated = []
    #     # Calculate distance against each pivot station (for each associated arrivals)
    #     if len(associated_station_epicenters_km) != 0:
    #         pivot_station_epicenters = np.array([epicenter_pair[1] for epicenter_pair in associated_station_epicenters_km], 
    #                                             dtype=np.float64)
            
    #         distances_km = np.linalg.norm(pivot_station_epicenters - taken_epicenter_km, axis=1)
            
    #         # Get indices where distance is less than threshold
    #         # Filter when distance = 0 (same station) as well
    #         associated = np.where((distances_km <= ASSOCIATION_STATION_DISTANCE_MIN_KM) & (distances_km > 0))[0]
        
    #     # If distance is less than threshold, insert arrival to associate with it
    #     if len(associated) > 0:
    #         print(associated, distances_km)
    #         for i in associated:
    #             associated_arrival_times[i].append(arrival_time)

    #             # Update pivot station epicenter if arrival time is earlier (optional, sorting time should be enough)
    #             if UTCDateTime(arrival_time) < UTCDateTime(associated_station_epicenters_km[i][0]):
    #                 associated_station_epicenters_km[i] = (arrival_time, taken_epicenter_km)
                                
    #     # If can't associate with any available arrivals, make new one
    #     else:
    #         associated_arrival_times.append([arrival_time])
    #         associated_station_epicenters_km.append((arrival_time, taken_epicenter_km))

    print("Associating by distance...")
    print(associated_arrival_times)
    print(associated_station_epicenters_km)
    
    # Only process valid associated arrivals
    valid_associated_arrivals = []
    for arrival_times in associated_arrival_times:
        # Skip if less than N_STATION
        if len(arrival_times) < N_STATION: continue
        
        # Structure important informations and append as valid arrival
        arrival_times = sorted(arrival_times)
        associated_arrivals = pd.DataFrame({
            'Station': [dict_taken_station[t] for t in arrival_times],
            'Pick_source_ids': [dict_taken_pick_source_id[t] for t in arrival_times],
            'P_dict': [dict_taken_pick_p[t] for t in arrival_times],
            'S_dict': [dict_taken_pick_s[t] for t in arrival_times],
            'P': [to_timestamp(dict_taken_pick_p[t]['timestamp']) for t in arrival_times],
            'S': [to_timestamp(dict_taken_pick_s[t]['timestamp']) for t in arrival_times],
            'X Station': [dict_taken_longitude[t] for t in arrival_times],
            'Y Station': [dict_taken_latitude[t] for t in arrival_times],
        })
        
        valid_associated_arrivals.append(associated_arrivals)

    print("Associated arrivals:", valid_associated_arrivals)
    
    return valid_associated_arrivals

def calculate_conventional_MLv(associated_arrivals, latitude, longitude, depth):
    """
    Calculate Conventional MLv for each station given associated arrival data, and average to get preferred magnitude.
    
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
    station_MLv : list of dict
        List of dictionaries containing station MLv data with keys:
            - pick_source_id
            - station_id
            - value
            - type
            - waveform_start
            - waveform_end
    preferred_MLv : float
        Preferred magnitude from average of station MLv
    """
    ## Conventional MLv
    station_MLv = []
    for i, arrival in associated_arrivals.iterrows():
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
        P_OFFSET_SEC = 3
        S_OFFSET_SEC = 3
        MIN_WINDOW_SEC = 1 * 60
        
        endtime = UTCDateTime(arrival['S']) + S_OFFSET_SEC
        p_and_s_diff_sec = endtime - (UTCDateTime(arrival['P'])-P_OFFSET_SEC)
        window_size_sec = max(MIN_WINDOW_SEC, p_and_s_diff_sec)
        starttime = endtime - window_size_sec
        
        # Get stream for Z channel from waveform starttime and endtime from cache
        key = f"aicache_{network}.{code}.{location}.{channel}_data"
        st = []
        try:
            st = get_channel_stream(key.replace(channel, channel[:-1]+'Z'), 
                                    endtime, 
                                    window_size_sec, 
                                    redis_client)
        except:
            print(f"[WARNING MLv] ({UTCDateTime.now()}) Data in archive not found, finding waveform in archive for pick_source_id {arrival['Pick_source_ids']}")
            
        # Get stream for Z channel from waveform starttime and endtime from archive
        if len(st) == 0:
            st = get_channel_fdsn(network, code, location, channel[:-1]+'Z', starttime, endtime, FDSN_SERVER_HOST)

            if len(st) == 0:
                print(f"[WARNING MLv] ({UTCDateTime.now()}) Data from cache and archive not found, skipping magnitude for pick_source_id {arrival['Pick_source_ids']}")
                continue
            
        # Fill in missing data with mean
        temp_value = np.ones(len(st[0].data))*np.mean(st[0].data)
        temp_value[:len(st[0].data)] = st[0].data[:len(st[0].data)]
        st[0].data = temp_value[:]
            
        # Get local magnitude for current arrival and structure into DB object
        try:
            MLv_value = determine_station_magnitude_MLv(arrival, st, station_xml)
            station_MLv.append({
                'pick_source_id': ObjectId(arrival['Pick_source_ids']),
                'station_id': ObjectId(arrival['P_dict']['station_id']),
                'value': MLv_value,
                'type': 'MLv',
                'waveform_start': starttime.datetime,
                'waveform_end': endtime.datetime
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)
            continue

    # Get average of station MLv to get preferred magnitude
    preferred_MLv = np.median(np.array([MLv['value'] for MLv in station_MLv]))
    
    return preferred_MLv, station_MLv
    
def calculate_ai_Mw(associated_arrivals, df_loc):
    """
    Calculate the magnitude of an event using AI Alpha (SeisAutoMag).

    Parameters
    ----------
    associated_arrivals : pandas.DataFrame
        The associated arrival from the assoc_locmag_consumer.
    df_loc : pandas.DataFrame
        The location data of the associated arrivals.

    Returns
    -------
    float
        The Mw magnitude of the event calculated using AI Alpha.
    """
    ## AI Alpha
    ai_magnitude = sd.SeisAutoMag(associated_arrivals, df_loc)
    ai_magnitude.execute(automag_model=automag_model)
    df_Mw = ai_magnitude.df_loc
    
    return df_Mw['Magnitude'].iloc[0]

def calculate_nonlinloc(associated_arrivals):
    """
    Calculate the location of an event using NonLinLoc.

    Parameters
    ----------
    associated_arrivals : pandas.DataFrame
        The associated arrival from the assoc_locmag_consumer.

    Returns
    -------
    pandas.DataFrame
        The location data of the associated arrivals calculated using NonLinLoc.
    """
    ## NonLinLoc
    # Only get the station name
    associated_arrivals_input = associated_arrivals.copy()
    associated_arrivals_input['Station'] = associated_arrivals_input['Station'].apply(lambda x: x.split('.')[-1])
    
    df_nlloc = nlloc_global(associated_arrivals_input)
    df_nlloc.columns = df_nlloc.columns.str.strip()
    
    return df_nlloc

def calculate_ai_loc(associated_arrivals, df_loc=[]):
    # Get only the closest station location towards event (used to help limit depth calculation)
    if len(df_loc) != None:
        # Convert the longitude, latitude and X station, Y station to km, then find the distance
        station_epicenter = np.array([
            convert_latitude_to_km(associated_arrivals['Y Station']), 
            convert_longitude_to_km(associated_arrivals['X Station'], associated_arrivals['Y Station'])
        ]).transpose()
        
        event_epicenter = np.array([convert_latitude_to_km(df_loc['latitude'].iloc[0]), 
                                    convert_longitude_to_km(df_loc['longitude'].iloc[0], df_loc['latitude'].iloc[0])])
        
        
        associated_arrivals['distance'] = np.linalg.norm(event_epicenter - station_epicenter, axis=1)
        associated_arrivals = associated_arrivals.nsmallest(N_STATION, 'distance').reset_index()
        
        print("Filtering for closest stations")
        print(associated_arrivals) 
    
    ## AI Alpha
    locator = sd.SeisAutoLoc(associated_arrivals, shp_dict)
    locator.execute(autoloc_model1=autoloc_model1, autoloc_model2=autoloc_model2)
    
    return locator.df_loc

def process_origin_from_arrivals(associated_arrivals):
    """
    Process associated arrival to get the origin, and magnitude of an event.

    Parameters
    ----------
    associated_arrivals : pandas.DataFrame
        The associated arrival from the assoc_locmag_consumer.
    list_taken_time : list
        The list of taken time from the assoc_locmag_consumer.
    r : redis connection
        The redis connection.

    Returns
    -------
    locmag_data : dict
        The origin and magnitude of an event.
    origin_time : obspy.UTCDateTime
        The origin time of an event.
    """
    # Get necessary location data from defined models
    print(associated_arrivals)
    df_nlloc = calculate_nonlinloc(associated_arrivals)              # For longitude and latitude
    df_loc_ai = calculate_ai_loc(associated_arrivals, df_nlloc)      # For depth
    df_nlloc.columns = df_nlloc.columns.str.strip()
    
    # Get region from preferred location model (current: NLLoc)
    df_region_loc = region_binning(df_nlloc['longitude'], df_nlloc['latitude'], df_nlloc['depth'], shp_dict)
    
    # Validate event
    # if df_result['latitude'].iloc[0]==-1 or df_result['longitude'].iloc[0]==-1: return 0, 0
    
    # TODO
    # dibuat cluster dari df_event bisa, jika long lat valid
    # print(str(r.get(redis_key+'_temp'))[2:-1], str(list_taken_time[:3]),
    #       str(r.get(redis_key+'_temp'))[2:-1] == str(list_taken_time[:3]))
    
    # if str(r.get(redis_key+'_temp'))[2:-1] == str(list_taken_time[:3]):
    #     return 0, 0
    # else:
    #     r.set(redis_key+'_temp', str(list_taken_time[:3]))
    
    # Calculate global magnitude and define all global / preferred magnitude data
    calculated_magnitudes = {
        'Mw': calculate_ai_Mw(associated_arrivals, df_region_loc),
        'MLv': calculate_conventional_MLv(associated_arrivals, 
                                          df_nlloc['latitude'].iloc[0], 
                                          df_nlloc['longitude'].iloc[0], 
                                          df_loc_ai['Depth'].iloc[0])
    }
    
    # Restructure magnitude data and remove empty magnitudes
    magnitudes = []
    station_magnitudes_per_type = []
    for magnitude_type, magnitude_data in calculated_magnitudes.items():
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
    try:
        ## NLLoc
        origin_time = UTCDateTime(df_nlloc['date-time'].iloc[0])
    except ValueError:
        ## No AI
        origin_time = min([UTCDateTime(p_pick_timestamp) for p_pick_timestamp in associated_arrivals['P'].values]) - ORIGIN_TIME_OFFSET_SEC
    
    locmag_data = {
        'longitude': float(df_nlloc['longitude'].iloc[0]),
        'latitude': float(df_nlloc['latitude'].iloc[0]),
        'depth': float(df_loc_ai['Depth'].iloc[0]),
        'err_epicenter': float(df_nlloc['errH'].iloc[0]),
        'rms': float(df_nlloc['RMS'].iloc[0]),
        'gap': float(df_nlloc['Gap'].iloc[0]),
        'region': df_region_loc['Region'].iloc[0],
        'sub_region': df_region_loc['Sub Region'].iloc[0],
        'terrain': df_region_loc['Terrain'].iloc[0],
        'country': df_region_loc['Country'].iloc[0],
        'magnitudes': magnitudes,
        'station_magnitudes_per_type': station_magnitudes_per_type
    }
    print(UTCDateTime.now(), locmag_data)
    
    # # TODO: DEBUG, inserting pure nonlinloc to event_test
    # locmag_test_data = {
    #     'longitude': float(df_nlloc['longitude'].iloc[0]),
    #     'latitude': float(df_nlloc['latitude'].iloc[0]),
    #     'depth': float(df_nlloc['depth'].iloc[0]),
    #     'region': df_region_loc['Region'].iloc[0],
    #     'sub_region': df_region_loc['Sub Region'].iloc[0],
    #     'terrain': df_region_loc['Terrain'].iloc[0],
    #     'country': df_region_loc['Country'].iloc[0],
    #     'magnitudes': magnitudes,
    #     'station_magnitudes_per_type': station_magnitudes_per_type,
    #     'method': 'NonLinLoc-NLLOriginTime'
    # }
    # send_origin_to_db(locmag_test_data, df_nlloc['date-time'].iloc[0], associated_arrivals, origin_test_col, magnitude_test_col, station_magnitude_test_col)

    return locmag_data, origin_time
    
def send_origin_to_db_and_kafka(
    locmag_data: dict,
    origin_time: obspy.UTCDateTime,
    associated_arrivals: pd.DataFrame,
    user_id: str = None,
    db_updated_origin: dict = None
) -> Tuple[ObjectId, List[ObjectId], List[Dict[str, Any]]]:
    """
    Process origin data to DB and Kafka.

    Parameters
    ----------
    locmag_data : dict
        The origin and magnitude of an event.
    origin_time : obspy.UTCDateTime
        The origin time of an event.
    associated_arrivals : pandas.DataFrame
        The associated arrival from the assoc_locmag_consumer.
    user_id : str, optional
        The ID of the user who modified the origin data.
    db_updated_origin : dict, optional
        The existing origin data in the DB.

    Returns
    -------
    origin_data : tuple
        The origin data in proper form for kafka and redis.
    """
    # Send origin to DB and get ID
    if db_updated_origin == None:
        origin_id, magnitude_ids, station_magnitude_ids_per_type = \
            send_origin_to_db(locmag_data,
                origin_time.datetime,
                associated_arrivals,
                origin_col,
                magnitude_col,
                station_magnitude_col
            )
    else:
        origin_id, magnitude_ids, station_magnitude_ids_per_type = \
            handle_insert_or_update_existing_origin_to_db(
                locmag_data, 
                origin_time.datetime, 
                associated_arrivals, 
                origin_col, 
                magnitude_col, 
                station_magnitude_col, 
                user_id, 
                db_updated_origin
            )
    
    # Restructure associated arrivals into proper form
    arrivals = []
    created_at = UTCDateTime().now().datetime
    if db_updated_origin != None:
        created_at = db_updated_origin['created_at']
        
    for i, arrival in associated_arrivals.iterrows():
        arrivals += [
            {
                **arrival['P_dict'],
                'phase_type': 'P',
                'pick_source_id': arrival['Pick_source_ids'],
                'station': arrival['Station'],
            },
            {
                **arrival['S_dict'],
                'phase_type': 'S',
                'pick_source_id': arrival['Pick_source_ids'],
                'station': arrival['Station'],
            }
        ]
        
    # Define origin data structure for kafka and redis (needed to unroll arrival and magnitude)
    origin_data = {
        '_id': str(origin_id),
        'name': "Origin " + str(origin_time),
        'origin_time': str(origin_time),
        'arrivals': arrivals,
        **locmag_data,
        'modified_by': user_id,
        'created_at': created_at,
        'modified_at': UTCDateTime().now().datetime if db_updated_origin == None else None
    }
    
    origin_data['magnitudes'] = [
        {
            '_id': str(magnitude_id),
            **magnitude,
            'modified_by': user_id,
            'created_at': created_at,
            'modified_at': UTCDateTime().now().datetime if db_updated_origin == None else None
        }
        for magnitude_id, magnitude in zip(magnitude_ids, locmag_data['magnitudes'])
    ]
    
    origin_data['station_magnitudes_per_type'] = [
        {
            'type': station_magnitude_ids['type'],
            'station_magnitudes': [
                {
                    '_id': str(station_magnitude_id),
                    **station_magnitude_values,
                    'modified_by': user_id,
                    'created_at': created_at,
                    'modified_at': UTCDateTime().now().datetime if db_updated_origin == None else None
                }
                for station_magnitude_id, station_magnitude_values in zip(station_magnitude_ids['station_magnitude_ids'], station_magnitudes['station_magnitudes'])
            ]
        }
        for station_magnitude_ids, station_magnitudes in zip(station_magnitude_ids_per_type, locmag_data['station_magnitudes_per_type'])
    ]
    
    # Send to kafka
    origin_data = convert_object_ids(origin_data)
    producer.send(ORIGIN_TOPIC, json.dumps(origin_data).encode())
    
    return origin_data
    
def origin_association(origin_data, r):
    """
    Associate origin to events in redis cache based on the rank of 
    matching criteria. If no best match, create new event.
    
    Parameters
    ----------
    origin_data : dict
        The origin data to be associated
    r : redis client
        The redis client to access the redis database.
    
    Returns
    -------
    event_data : dict
        The event data associated with the origin. If no best match, 
        the event data is the newly created event.
    """
    # Get every event in cache
    cache_events = []
    
    # Update to use redis pipeline
    with r.pipeline() as pipe:
        # Queue all the GET commands
        for message in r.scan_iter(f"event:*"):
            pipe.get(message)

        # Execute all the queued commands
        results = pipe.execute()

        # Parse the results
        for result in results:
            if result:
                cache_events.append(json.loads(result))
        
    # Convert arrivals to pandas DataFrames for association
    df_current_origin_arrivals = pd.DataFrame(origin_data['arrivals'])
    
    # Find origin ranking in each event
    origin_rank_on_events = {}
    for event in cache_events:
        for prev_origin in event['origins']:
            # Initialize rank
            rank = 0
            
            # 1. Location and Time Matching (lowest rank)
            location_diff = abs(origin_data['longitude'] - prev_origin['longitude']) + abs(origin_data['latitude'] - prev_origin['latitude'])
            time_diff = abs(UTCDateTime(origin_data['origin_time']) - UTCDateTime(prev_origin['origin_time']))
            if location_diff <= ORIGIN_ASSOC_MAX_DISTANCE_DEG and time_diff <= ORIGIN_ASSOC_MAX_TIMESPAN_SEC:
                rank += 1
                
            # 2. Picks Matching
            # Convert prev arrivals to pandas DataFrames
            df_prev_origin_arrivals = pd.DataFrame(prev_origin['arrivals'])
            
            matching_picks = 0
            # Negative values means arrival matching uses arrival id
            if ORIGIN_ASSOC_MAX_ARRIVAL_TIME_DIFF_SEC < 0:
                # Count arrivals that have same _id
                matching_picks = len(df_current_origin_arrivals[df_current_origin_arrivals['_id'].isin(df_prev_origin_arrivals['_id'])]) 
            else:
                # Merge the two DataFrames on the 'station' column
                merged_by_station_df = pd.merge(df_current_origin_arrivals, df_prev_origin_arrivals, on='station', suffixes=('_A', '_B'))
                
                # Calculate the absolute difference between the timestamps and count how many is bellow the threshold
                matching_picks = len(merged_by_station_df[abs(UTCDateTime(merged_by_station_df['timestamp_A']) - UTCDateTime(merged_by_station_df['timestamp_B'])) 
                                                          <= ORIGIN_ASSOC_MAX_ARRIVAL_TIME_DIFF_SEC])
                
            if matching_picks >= ORIGIN_ASSOC_MIN_MATCHING_ARRIVAL:
                rank += 2
             
            # 3. Picks and Location and Time Matching (highest rank)
            # Case handled using rank summation from rule 1 and 2
            
            # Append to event rank dictionary
            if rank:
                origin_rank_on_events.setdefault(rank, []).append(event)
        
    # If no best match, create new event
    if len(cache_events) == 0 or len(origin_rank_on_events) == 0:
        # Insert new event to database
        event_data = {
            'name': "Event " + origin_data['origin_time'],
            'origin_ids': [ObjectId(origin_data['_id'])],
            'preferred_origin_id': ObjectId(origin_data['_id']),
            'created_at': UTCDateTime().now().datetime
        }
        
        event_id = event_col.insert_one(event_data).inserted_id
        event_data['_id'] = str(event_id)
        
        # Unroll origins and preferred origins
        event_data['origins'] = [origin_data]
        event_data['preferred_origin'] = origin_data
    # Else append origin to best matched event
    else:
        # Get best event by rank
        event_data = origin_rank_on_events[max(origin_rank_on_events.keys())][0]
        event_data['origins'].append(origin_data)
        event_data['origin_ids'].append(origin_data['_id'])
        
        preferred_origin = origin_ranking(event_data['origins'])
        
        # Update event in database
        event_col.update_one({'_id': ObjectId(event_data['_id'])}, 
                             {
                                '$set': {
                                    'name': "Event " + preferred_origin['origin_time'],
                                    'preferred_origin_id': ObjectId(preferred_origin['_id']),
                                    'origin_ids': [ObjectId(_id) for _id in event_data['origin_ids']],
                                    'created_at': UTCDateTime().now().datetime
                                }
                             }
                            )
        
    # Insert or update event in redis for future origin association
    event_data = convert_object_ids(event_data)
    r.set(f"event:{event_data['_id']}", json.dumps(event_data), ex=ORIGIN_ASSOC_MAX_EVENT_LINGER_SEC)
    
    return event_data

def origin_ranking(origins):
    """
    Rank origins based on origin ranking priorities.
    
    Parameters
    ----------
    origins : list
        List of origin dictionaries.
    
    Returns
    -------
    str
        The id of the preferred origin.
    """
    # Rank origins based on priority. Stop when there is only one origin left
    for priority in ORIGIN_RANKING_PRIORITIES:
        if len(origins) <= 1:
            break
        
        if priority == 'AUTO':
            # Get the first origin
            origins = [origin for origin in origins if origin['modified_by'] == None]
        elif priority == 'PHASES':
            # Count arrival phase for each origin, then get all origins with highest phase count
            max_phase_count = max([len(origin['arrivals']) for origin in origins])
            origins = [origin for origin in origins if len(origin['arrivals']) == max_phase_count]
        elif priority == 'CREATION_TIME':
            # Get all origins with latest creation time
            latest_creation_time = max([UTCDateTime(origin['origin_time']) for origin in origins])
            origins = [origin for origin in origins if UTCDateTime(origin['origin_time']) == latest_creation_time]
            
    if len(origins) > 0:
        return origins[0]
    else:
        raise ValueError("No origins left after ranking")
        
def consume_arrival_task(message):
    """
    Consume arrival task from Kafka. Associate arrivals with origin, 
    process AI origin, associate origin with event, and send event to Kafka.

    Parameters
    ----------
    message : bytes
        Kafka message containing arrival data in JSON format.

    Returns
    -------
    None
    """
    data = json_serializer(message)
    print(f"associating {data['network']}.{data['station']} {UTCDateTime(data['picks'][0]['timestamp'])} {UTCDateTime.now()}")
    
    # Associate arrivals with origin
    associated_arrivals = arrival_association(data, redis_client)
    if type(associated_arrivals) != list:
        return
    if len(associated_arrivals) == 0: # No valid associated arrival
        return
    
    for associated_arrival in associated_arrivals:
        # Process AI origin from associated arrivals
        locmag_data, origin_time = process_origin_from_arrivals(associated_arrival)

        if locmag_data == 0:
            return
        
        # Process origin from locmag data
        origin_data = send_origin_to_db_and_kafka(locmag_data, origin_time, associated_arrival)
        
        # Associate origin with event and send event to Kafka
        event_data = origin_association(origin_data, redis_client)
        producer.send(EVENT_TOPIC, json.dumps(event_data).encode())
        # send_reloc_to_kafka(df_event, event_id, producer)

def consume_repicking_task(message):
    """
    Consume repicking task from Kafka. Associate arrivals with origin, 
    process AI origin, associate origin with event, and send event to Kafka.

    Parameters
    ----------
    message : bytes
        Kafka message containing repicking data in JSON format.

    Returns
    -------
    None
    """
    try:
        data = json_serializer(message)
        user_id = ObjectId(data['user_id'])
        origin_id = ObjectId(data['origin_id'])
        
        # TODO: needs handling on missing origin  
        db_updated_origin = origin_col.find_one({'_id': ObjectId(origin_id)})
        if db_updated_origin == None:
            raise Exception(f"Origin {origin_id} not found in database")
        
        # Get unused arrival_ids from db_updated_origin
        # TODO: check this part, why arrival_ids not filtered by checked value?
        arrival_ids = [arrival['_id'] for arrival in data['arrival_list']]
        unused_arrival_ids = [arrival_id for arrival_id in db_updated_origin['arrival_ids'] if str(arrival_id) not in arrival_ids]
        unused_arrivals = [{**arrival, 'checked': False} for arrival in arrival_col.find({'_id': {'$in': unused_arrival_ids}})]
        
        # Insert or update arrivals to DB
        stations = {}
        for arrival in data['arrival_list'] + unused_arrivals:
            sta_id = arrival['station_id']
            station = db['station'].find_one({'_id': ObjectId(sta_id)})
            arrival_id = send_or_update_arrival_to_db(arrival, station, arrival['pick_source_id'], arrival_col, user_id, arrival.get('checked', True))
            
            try:
                stations[sta_id]['timestamp_'+arrival['phase_type']] = {'_id': str(arrival_id),
                                                                        'timestamp': arrival['timestamp'],
                                                                        'station_id': sta_id}
                stations[sta_id]['pick_source_id'] = arrival['pick_source_id']
                stations[sta_id]['station'] = station
            except:
                stations[sta_id] = {'timestamp_'+arrival['phase_type']: {'_id': str(arrival_id),
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

        # Process AI origin from associated arrivals (only used arrivals)
        locmag_data, origin_time = process_origin_from_arrivals(associated_arrivals[associated_arrivals['Used'] == True].reset_index(drop=True))
        
        # Validate event, if no repicking, then use old locmag
        # TODO: Dangerous, needs to handle this one as well
        # if locmag_data == 0:
        #     print("AI repicking didn't find new locmag, using old event data")
        #     db_magnitude = magnitude_col.find_one({"_id": db_updated_origin['magnitude_ids'][0]})
            
        #     if db_magnitude != None:
        #         locmag_data = {
        #             'longitude': float(db_updated_origin['longitude']),
        #             'latitude': float(db_updated_origin['latitude']),
        #             'depth': float(db_updated_origin['depth']),
        #             'region': db_updated_origin['region'],
        #             'sub_region': db_updated_origin['sub_region'],
        #             'terrain': db_updated_origin['terrain'],
        #             'country': db_updated_origin['country'],
        #             'magnitude': db_magnitude['value'],
        #         }
        #     else:
        #         raise Exception(f"Magnitude with ID {db_updated_origin['magnitude_id']} not found! Please ensure that this is an update operation")

        # if origin_time == 0:
        #     origin_time = UTCDateTime(db_updated_origin['origin_time'])
            
        # Process origin from locmag data
        origin_data = send_origin_to_db_and_kafka(locmag_data, origin_time, associated_arrivals, user_id, db_updated_origin)
        
        # Find event id that contains this origin
        db_event = event_col.find({'origin_ids': {'$in': [ObjectId(origin_id)]}}).limit(1)[0]
        
        # Insert origin id to event if new
        if origin_data['_id'] != origin_id and ObjectId(origin_data['_id']) not in db_event['origin_ids']:
            event_col.update_one({'_id': db_event['_id']}, {'$set': {'origin_ids': db_event['origin_ids'] + [ObjectId(origin_data['_id'])]}})
        
        # Send repicking feedback to kafka
        origin_data = convert_object_ids(origin_data)
        
        # TODO remove this after FE change
        event_data = db_event
        if origin_data['_id'] not in db_event['origin_ids']:
            event_data['origin_ids'] = db_event['origin_ids'] + [origin_data['_id']]
        event_data['updated_origin_id'] = origin_data['_id']
        print(event_data)
        
        producer.send(REPICKING_FEEDBACK_TOPIC, json.dumps({"code": 200, 
                                                            "origin_id": str(origin_id), 
                                                            "user_id": str(user_id),
                                                            "new_origin_id": str(origin_data['_id']), 
                                                            "message": "Success repicking AI", 
                                                            "data": convert_object_ids(event_data)
                                                        }).encode())
        print("Repicking finished, sent feedback to kafka")
        # send_reloc_to_kafka(df_event, event_id, producer)
    except Exception as e:
        producer.send(REPICKING_FEEDBACK_TOPIC, json.dumps({"code": 500,
                                                            "origin_id": str(origin_id), 
                                                            "user_id": str(user_id), 
                                                            "new_origin_id": None, 
                                                            "message": f"Error repicking AI: {e}",
                                                            "data": None
                                                        }).encode())
        raise e
    
async def consume_arrival():
    # Create a Kafka consumer instance
    print("Processing Arrival")
    arrival_pick_consumer = AIOKafkaConsumer(
        ARRIVAL_PICK_TOPIC,
        bootstrap_servers=f"{KAFKA_HOST}:{KAFKA_PORT}",
    )
    # Start the consumer
    await arrival_pick_consumer.start()
    async for message in arrival_pick_consumer:
        try:
            consume_arrival_task(message)
            # thread = threading.Thread(target=consume_arrival_task, args=(message,))
            # thread.start()
            # thread.join(0)
            # active_threads = threading.active_count()
            # if active_threads > MAX_WORKERS:
            #     print("System Overhead: Forced Stop!!!...............")
            #     break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)
    
    await arrival_pick_consumer.stop()
    
async def consume_repicking():
    # Create a Kafka consumer instance
    print("Processing Repicking")
    repicking_consumer = AIOKafkaConsumer(
        REPICKING_COMMIT_TOPIC,
        bootstrap_servers=f"{KAFKA_HOST}:{KAFKA_PORT}",
    )
    # Start the consumer
    await repicking_consumer.start()
    async for message in repicking_consumer:
        try:
            consume_repicking_task(message)
            # thread = threading.Thread(target=consume_repicking_task, args=(message,))
            # thread.start()
            # thread.join(0)
            # active_threads = threading.active_count()
            # if active_threads > MAX_WORKERS:
            #     print("System Overhead: Forced Stop!!!...............")
            #     break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)
            
    await repicking_consumer.stop()

async def main():
    """
    The main entry point for the asyncio application.

    This function creates two separate consumers for two different topics
    and waits for both consumers to finish (this will keep running until
    interrupted).

    """
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
    
    # Create two separate consumers for two different topics
    arrival_consumer_task = asyncio.create_task(consume_arrival())
    repicking_consumer_task = asyncio.create_task(consume_repicking())

    # Wait for both consumers to finish (this will keep running until interrupted)
    await asyncio.gather(arrival_consumer_task, repicking_consumer_task)

if __name__ == "__main__":
    print("Processing Locmag")
    asyncio.run(main())