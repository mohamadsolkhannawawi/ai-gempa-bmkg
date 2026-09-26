import json
import pymongo
import pandas as pd
from obspy import UTCDateTime
from config import *
from bson import ObjectId
from datetime import datetime
from typing import Tuple, List, Dict, Any

# Function to serialize data to JSON format
def json_serializer(message):
    if type(message)==type({}):
        return message
    elif type(message) == str:
        return json.loads(message)
    return json.loads(message.value.decode('utf-8'))

def convert_object_ids(docs):
    if isinstance(docs, list):
        for doc in docs:
            convert_object_ids(doc)
    elif isinstance(docs, dict):
        for k, v in docs.items():
            if isinstance(v, ObjectId):
                docs[k] = str(v)  # Convert ObjectId to string
            elif isinstance(v, datetime):
                docs[k] = v.isoformat()  # Convert datetime to string
            elif isinstance(v, list):
                docs[k] = [str(item) if isinstance(item, ObjectId) else convert_object_ids(item) if isinstance(item, dict) else item for item in v]
            elif isinstance(v, dict):
                convert_object_ids(v)  # Recursively process nested documents
            elif isinstance(v, UTCDateTime):
                docs[k] = str(v)
    return docs

def send_magnitudes_to_db(
    magnitudes: List[Dict[str, Any]], 
    user_id: str, 
    created_at: datetime, 
    magnitude_col: pymongo.collection.Collection, 
    modified_at: datetime = None
) -> List[ObjectId]:
    """
    Inserts magnitude data into the database and returns the inserted IDs.
    
    Parameters
    ----------
    magnitudes : list
        A list of dictionaries, each containing magnitude data.
    user_id : str
        The ID of the user who modified the magnitude data.
    created_at : datetime
        The timestamp when the data is created.
    magnitude_col : pymongo.collection.Collection
        The collection for magnitude data in the database.
    modified_at : datetime, optional
        The timestamp when the data is modified.

    Returns
    -------
    List[ObjectId]
        The IDs of the inserted magnitude data.
    """
    # Insert magnitude data and returns the ids
    db_magnitudes_data = [
        {
            **magnitude,
            'modified_by': user_id,
            'created_at': created_at,
            'modified_at': modified_at
        }
        for magnitude in magnitudes
    ]
    
    return magnitude_col.insert_many(db_magnitudes_data).inserted_ids

# Function to insert station magnitude data into the database and return the inserted IDs
def send_station_magnitudes_to_db(
    station_magnitudes_per_type: List[Dict[str, Any]], 
    user_id: str, 
    created_at: datetime, 
    station_magnitude_col: pymongo.collection.Collection, 
    modified_at: datetime = None
) -> List[Dict[str, Any]]:
    """
    Inserts station magnitude data into the database and returns the inserted IDs per type.
    
    Parameters
    ----------
    station_magnitudes_per_type : List[Dict[str, Any]]
        A list of dictionaries, each containing the station magnitude data for a specific type.
    user_id : str
        The ID of the user who modified the station magnitude data.
    created_at : datetime
        The timestamp when the data is created.
    station_magnitude_col : pymongo.collection.Collection
        The collection for station magnitude data in the database.
    modified_at : datetime, optional
        The timestamp when the data is modified.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries, each containing the type and corresponding station magnitude IDs.
    """
    # Initialize an empty list to store station magnitude data per type
    db_station_magnitudes_ids_per_type = []
    
    # Iterate over each type of station magnitude data
    for station_magnitudes in station_magnitudes_per_type:
        # Add station magnitude modifier and creation time
        db_station_magnitudes_data = [
            {
                **station_magnitude,
                'modified_by': user_id,
                'created_at': created_at,
                'modified_at': modified_at
            }
            for station_magnitude in station_magnitudes['station_magnitudes']
        ]

        # Insert the station magnitude data into the database and get the inserted IDs
        db_station_magnitudes_ids = station_magnitude_col.insert_many(db_station_magnitudes_data).inserted_ids
        
        # Append the type and corresponding station magnitude IDs to the list
        db_station_magnitudes_ids_per_type.append({
            'type': station_magnitudes['type'],
            'station_magnitude_ids': db_station_magnitudes_ids
        })        
    
    # Return the list of station magnitude data per type
    return db_station_magnitudes_ids_per_type
    
def send_origin_to_db(
    locmag_data: Dict[str, Any], 
    origin_time: obspy.UTCDateTime, 
    arrivals_data: pd.DataFrame, 
    origin_col: pymongo.collection.Collection, 
    magnitude_col: pymongo.collection.Collection, 
    station_magnitude_col: pymongo.collection.Collection, 
    user_id: str=None, 
    auto_origin_ref_id: ObjectId=None, 
    created_at: datetime=None, 
    modified_at: datetime=None
) -> Tuple[ObjectId, List[ObjectId], List[Dict[str, Any]]]:
    """
    Process origin data to DB and get ID.

    Parameters
    ----------
    locmag_data : dict
        The origin and magnitude of an event.
    origin_time : obspy.UTCDateTime
        The origin time of an event.
    arrivals_data : pandas.DataFrame
        The associated arrival from the assoc_locmag_consumer.
    origin_col : pymongo.Collection
        The collection of origin data.
    magnitude_col : pymongo.Collection
        The collection of magnitude data.
    station_magnitude_col : pymongo.Collection
        The collection of station magnitude data.
    user_id : str, optional
        The ID of the user who modified the origin data.
    created_at : datetime, optional
        The time when the data is created.
    modified_at : datetime, optional
        The timestamp when the data is modified.

    Returns
    -------
    origin_id : ObjectId
        The ID of the inserted origin data.
    magnitude_ids : list
        The IDs of the inserted magnitude data.
    station_magnitudes_ids_per_type : list
        The IDs of the inserted station magnitude data per type.
    """
    # Use now as created_at if not specified
    # Done because specifying in args causes created_at to be when the service is run instead of now
    if created_at is None:
        created_at = UTCDateTime.now().datetime
    
    # Insert magnitudes and station_magnitudes
    magnitude_ids = send_magnitudes_to_db(locmag_data['magnitudes'], user_id, created_at, magnitude_col)
    station_magnitudes_ids_per_type = send_station_magnitudes_to_db(locmag_data['station_magnitudes_per_type'], user_id, created_at, station_magnitude_col)

    # Insert origin data
    db_origin_data = {
        'name': "Origin " + str(origin_time),
        'origin_time': origin_time,
        'arrival_ids': [ObjectId(arrival['_id']) 
                        for arrival in arrivals_data['P_dict'].values.tolist() + 
                                       arrivals_data['S_dict'].values.tolist()],
        **locmag_data,
        'magnitude_ids': magnitude_ids,
        'station_magnitude_ids_per_type': station_magnitudes_ids_per_type,
        'modified_by': user_id,
        'auto_origin_ref_id': auto_origin_ref_id,
        'created_at': created_at,
        'modified_at': modified_at
    }

    del db_origin_data['magnitudes']
    del db_origin_data['station_magnitudes_per_type']
    
    origin_id = origin_col.insert_one(db_origin_data).inserted_id
    return origin_id, magnitude_ids, station_magnitudes_ids_per_type

def handle_insert_or_update_existing_origin_to_db(
    locmag_data: dict, 
    origin_time: obspy.UTCDateTime, 
    arrivals_data: pd.DataFrame, 
    origin_col: pymongo.collection.Collection, 
    magnitude_col: pymongo.collection.Collection, 
    station_magnitude_col: pymongo.collection.Collection, 
    user_id: ObjectId, 
    db_updated_origin: dict
) -> Tuple[ObjectId, List[ObjectId], List[Dict[str, Any]]]:
    """
    Handles inserting or updating existing origin to the database.

    Parameters
    ----------
    locmag_data : dict
        The origin and magnitude data of an event.
    origin_time : obspy.UTCDateTime
        The origin time of an event.
    arrivals_data : pandas.DataFrame
        The associated arrival from the assoc_locmag_consumer.
    origin_col : pymongo.collection.Collection
        The collection for origin data in the database.
    magnitude_col : pymongo.collection.Collection
        The collection for magnitude data in the database.
    station_magnitude_col : pymongo.collection.Collection
        The collection for station magnitude data in the database.
    user_id : str
        The ID of the user who modified the origin data.
    db_updated_origin : dict
        The existing origin data in the DB.

    Returns
    -------
    origin_id : ObjectId
        The ID of the inserted origin data.
    magnitude_ids : list
        The IDs of the inserted magnitude data.
    station_magnitudes_ids_per_type : list
        The IDs of the inserted station magnitude data per type.
    """
    
    # Inserting new modified origin
    print(db_updated_origin)
    if db_updated_origin['modified_by'] is None:
        origin_id, magnitude_ids, station_magnitudes_ids_per_type = send_origin_to_db(
            locmag_data, origin_time, arrivals_data, origin_col, magnitude_col, station_magnitude_col, user_id, auto_origin_ref_id=db_updated_origin['_id'], created_at=db_updated_origin['created_at'], modified_at=UTCDateTime.now().datetime
        )
    # Updating already existing modified origin
    else:
        # Filter out unauthorized origin update early
        if db_updated_origin['modified_by'] != user_id:
            raise Exception(f"Unauthorized update for origin {db_updated_origin['_id']} by user {user_id}")
                
        ## Handle Magnitude data
        # Remove every old DB magnitudes
        magnitude_col.delete_many({'_id': { '$in': db_updated_origin['magnitude_ids'] }})
        
        # Insert all new magnitudes to DB
        magnitude_ids = send_magnitudes_to_db(locmag_data['magnitudes'], user_id, db_updated_origin['created_at'], magnitude_col, modified_at=UTCDateTime.now().datetime)
        
        ## Handle Station Magnitude data
        # Remove every old DB station magnitudes
        station_magnitude_col.delete_many({'_id': { '$in': db_updated_origin['station_magnitude_ids_per_type'] }})
        station_magnitudes_ids_per_type = send_station_magnitudes_to_db(locmag_data['station_magnitudes_per_type'], user_id, db_updated_origin['created_at'], station_magnitude_col, modified_at=UTCDateTime.now().datetime)
        
        ## Handle Origin data
        # Insert origin data
        db_origin_data = {
            'name': "Origin " + str(origin_time),
            'origin_time': origin_time,
            'arrival_ids': [ObjectId(arrival['_id']) 
                            for arrival in arrivals_data['P_dict'].values.tolist() + 
                                        arrivals_data['S_dict'].values.tolist()],
            **locmag_data,
            'magnitude_ids': magnitude_ids,
            'station_magnitude_ids_per_type': station_magnitudes_ids_per_type,
            'modified_by': user_id,
            'auto_origin_ref_id': db_updated_origin['_id'],
            'created_at': db_updated_origin['created_at'],
            'modified_at': UTCDateTime.now().datetime
        }

        del db_origin_data['magnitudes']
        del db_origin_data['station_magnitudes_per_type']
        
        print(f"Updating origin {db_updated_origin['_id']}")
        db_origin_data = {"$set": db_origin_data}
        origin_col.update_one({"_id": ObjectId(db_updated_origin["_id"])}, db_origin_data)
        origin_id = db_updated_origin["_id"]

    return origin_id, magnitude_ids, station_magnitudes_ids_per_type

def send_or_update_arrival_to_db(
    pick_arrival_data: dict,
    db_station: dict,
    pick_id: str,
    arrival_col,
    user_id,
    checked
) -> ObjectId:
    """
    Process arrival data to DB and get ID.

    Parameters
    ----------
    pick_arrival_data : dict
        The arrival data.
    db_station : dict
        The station data from DB.
    pick_id : str
        The ID of the pick associated with the arrival.
    arrival_col : pymongo.collection.Collection
        The collection of arrival data.
    user_id : str
        The ID of the user who modified the arrival data.
    checked : bool
        Whether the arrival is checked or not.

    Returns
    -------
    arrival_id : ObjectId
        The ID of the inserted or updated arrival data.
    """
    # Define DB data
    db_insert_data = {
        "pick_source_id": ObjectId(pick_id),
        "station_id": ObjectId(db_station['_id']),
        "timestamp": UTCDateTime(pick_arrival_data['timestamp']).datetime,
        "phase_type": pick_arrival_data['phase_type'],
        "checked": checked,
        "created_at": UTCDateTime.now().datetime,
        "modified_by": ObjectId(user_id),
        "modified_at": UTCDateTime.now().datetime
    }
    
    # Check if arrival exists in DB
    db_arrival = arrival_col.find_one({"_id": ObjectId(pick_arrival_data['_id'])})
    if db_arrival:
        # If arrival is automatic (user is None), create new arrival for this event
        db_insert_data['created_at'] = db_arrival['created_at']
        if db_arrival.get('modified_by') == None:
            # Insert data to DB and get ID for each arrival timestamp
            print(f"Inserting modified new arrival")
            arrival_id = arrival_col.insert_one(db_insert_data).inserted_id
        # Else, update existing arrival
        else:
            print(f"Updating arrival {db_arrival['_id']}")
            db_insert_data = {"$set": db_insert_data}
            arrival_col.update_one({"_id": ObjectId(db_arrival["_id"])}, db_insert_data)
            arrival_id = db_arrival["_id"]
    else:
        raise Exception(f"Arrival with ID {pick_arrival_data['_id']} not found! Please ensure that this is an update operation")
    
    return arrival_id

# def send_relocmag_to_kafka(event, cluster, arrivals, event_id, magnitude_ids, producer, user_id=None, event_auto_ref_id=None):
#     kafka_data = {
#         '_id': str(event_id),
#         'name': "Earthquake " + str(cluster['origin_time']),
#         'cluster': cluster,
#         'arrivals': [arrival for arrival in [arrivals['P_dict'].values.tolist()] + [arrivals['S_dict'].values.tolist()]],
#         **event,
#         # 'longitude': event['longitude'],
#         # 'latitude': event['latitude'],
#         # 'depth': event['depth'],
#         'magnitudes': [
#             {
#                 '_id': str(magnitude_ids[0]),
#                 'type': 'Mw',
#                 'value': event['magnitude'],  
#                 'modified_by': None,
#             }
#         ],
#         'modified_by': str(user_id),
#         'event_auto_ref_id': str(event_auto_ref_id),
#         "created_at": str(UTCDateTime().now())
#     }
#     del kafka_data['magnitude']
    
#     kafka_data = convert_object_ids(kafka_data)
#     producer.send(RELOCATION_FEEDBACK_TOPIC, json.dumps(kafka_data).encode())