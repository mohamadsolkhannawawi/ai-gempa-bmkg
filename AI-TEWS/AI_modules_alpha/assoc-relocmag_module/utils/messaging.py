import json
import logging
from obspy import UTCDateTime
from config import *
from bson import ObjectId
from utils.util import convert_object_ids

# Function to serialize data to JSON format
def json_serializer(message):
    if type(message)==type({}):
        return message
    elif type(message) == str:
        return json.loads(message)
    return json.loads(message.value.decode('utf-8'))


def send_picks_to_db(pick_candidates, db_station, pick_col):
    # Define DB data
    db_data = [
        {
            'station_id': db_station['_id'],
            'timestamp': UTCDateTime(pick).datetime,
            'created_at': UTCDateTime().now().datetime
        }
        for pick in pick_candidates
    ]
    # Insert data to DB and get ID for each pick timestamp
    pick_ids = pick_col.insert_many(db_data).inserted_ids
    return pick_ids

def send_picks_to_kafka(pick_candidates, db_station, pick_ids, producer):
    # Produce pick
    kafka_data = {
        'station_id': str(db_station['_id']),
        'network': db_station['network'],
        'station': db_station['code'],
        'picks': [
            {
                '_id': str(pick_ids[i]),
                'timestamp': pick
            }
            for i, pick in enumerate(pick_candidates)
        ]
    }

    producer.send(PICK_TOPIC, json.dumps(kafka_data).encode())

# Arrivals
def send_arrivals_to_db(pick_arrival_data, db_station, pick_id, arrival_col, user_id=None):
    # Define DB data
    db_data = [
        # P arrival DB
        {
            "pick_source_id": ObjectId(pick_id),
            "station_id": ObjectId(db_station['_id']),
            "timestamp": pick_arrival_data['P']['timestamp'],
            "phase_type": "P",
            "modified_by": user_id,
            "created_at": UTCDateTime().now().datetime
        },
        {
            "pick_source_id": ObjectId(pick_id),
            "station_id": ObjectId(db_station['_id']),
            "timestamp": pick_arrival_data['S']['timestamp'],
            "phase_type": "S",
            "modified_by": user_id,
            "created_at": UTCDateTime().now().datetime
        }
    ]
    
    # Insert data to DB and get ID for each arrival timestamp
    arrival_ids = arrival_col.insert_many(db_data).inserted_ids
    return arrival_ids

# Arrivals
def send_or_update_arrival_to_db(pick_arrival_data, db_station, pick_id, arrival_col, user_id=None):
    # Define DB data
    db_insert_data = {
        "pick_source_id": ObjectId(pick_id),
        "station_id": ObjectId(db_station['_id']),
        "timestamp": pick_arrival_data['timestamp'],
        "phase_type": pick_arrival_data['phase_type'],
        "modified_by": ObjectId(user_id),
        "created_at": UTCDateTime().now().datetime
    }
    
    # Check if arrival exists in DB
    db_arrival = arrival_col.find_one({"_id": ObjectId(pick_arrival_data['_id'])})
    if db_arrival:
        # If arrival is automatic (user is None), create new arrival for this event
        if db_arrival.get('modified_by') == None:
            # Insert data to DB and get ID for each arrival timestamp
            print(f"Inserting new arrival")
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

# def send_arrivals_to_kafka(pick_arrival_data, db_station, pick_id, producer, user_id=None):
#     # Produce pick
#     kafka_data = {
#         'pick_source_id': str(pick_id),
#         'station_id': str(db_station['_id']),
#         'network': db_station['network'],
#         'station': db_station['code'],
#         'longitude': db_station['longitude'],
#         'latitude': db_station['latitude'],
#         'picks': [
#             {
#                 '_id': str(pick_arrival_data['P']['_id']),
#                 'timestamp': str(pick_arrival_data['P']['timestamp']),
#                 'type': 'P',
#                 "modified_by": user_id,
#             },
#             {
#                 '_id': str(pick_arrival_data['S']['_id']),
#                 'timestamp': str(pick_arrival_data['S']['timestamp']),
#                 'type': 'S',
#                 "modified_by": user_id,
#             },
#         ],
#     }

#     producer.send(ARRIVAL_PICK_TOPIC, json.dumps(kafka_data).encode())

def send_or_update_cluster_to_db(cluster, cluster_id, origin_time, cluster_col, user_id=None):
    # Define DB data
    db_insert_data = {
        'pick_ids': [ObjectId(pick_id) for pick_id in cluster['Pick_source_ids'].values],
        'origin_time': origin_time.datetime,
        'rank': 1,
        'modified_by': ObjectId(user_id),
        'created_at': UTCDateTime().now().datetime
    }

    # Check if arrival exists in DB
    db_cluster = cluster_col.find_one({"_id": ObjectId(cluster_id)})
    if db_cluster:
        # If cluster is automatic (user is None), create new cluster for this event
        if db_cluster.get('modified_by') == None:
            print(f"Inserting new event")
            # Insert data to DB and get ID for each cluster timestamp
            cluster_id = cluster_col.insert_one(db_insert_data).inserted_id
        # Else, update existing cluster
        else:
            print(f"Updating cluster {db_cluster['_id']}")
            db_insert_data = {"$set": db_insert_data}
            cluster_col.update_one({"_id": ObjectId(db_cluster["_id"])}, db_insert_data)
            cluster_id = db_cluster["_id"]
    else:
        raise Exception(f"Cluster with ID {cluster['_id']} not found! Please ensure that this is an update operation")
                    
    return cluster_id

# def send_cluster_to_kafka(cluster, cluster_id, origin_time, producer, user_id=None):
#     kafka_data = {
#         '_id': str(cluster_id), 
#         'origin_time': str(origin_time),
#         'rank': 1,
#         'picks': [
#             {
#                 '_id': str(pick['_id']),
#                 'timestamp': pick['timestamp'],
#             }
#             for pick in cluster['P_dict'].values
#         ],
#         'modified_by': user_id,
#     }
    
#     producer.send(CLUSTER_TOPIC, json.dumps(kafka_data).encode())
#     return kafka_data # Returned to be used while sending locmag to db / kafka

def send_or_update_event_to_db(event, cluster, arrivals, db_event, event_col, magnitude_col, user_id=None, event_auto_ref_id=None):
    # Insert or update magnitudes
    db_magnitudes_insert_data = [
        {
            'type': 'Mw',
            'value': event['magnitude'],  
            'modified_by': user_id,
        }
    ]
    
    # Check if magnitudes exists in DB
    db_magnitude_ids = db_event['magnitude_ids']
    magnitude_ids = []
    for magnitude_id in db_magnitude_ids:
        db_magnitude = magnitude_col.find_one({"_id": ObjectId(magnitude_id)})
        if db_magnitude:
            
            # Find same type of magnitude
            db_magnitude_insert_data = [magnitude
                                        for magnitude in db_magnitudes_insert_data 
                                        if magnitude['type'] == db_magnitude['type']]
            
            if len(db_magnitude_insert_data) != 1:
                raise Exception(f"There are {len(db_magnitude_insert_data)} magnitude data found for {magnitude_id}")
            db_magnitude_insert_data = db_magnitude_insert_data[0]
            
            # If magnitude is automatic (user is None), create new magnitude for this event
            if db_magnitude.get('modified_by') == None:
                print(f"Inserting new magnitude")
                # Insert data to DB and get ID for each magnitude timestamp
                magnitude_id = magnitude_col.insert_one(db_magnitude_insert_data).inserted_id
            # Else, update existing magnitude
            else:
                print(f"Updating magnitude {db_magnitude['_id']}")
                db_magnitude_insert_data = {"$set": db_magnitude_insert_data}
                magnitude_col.update_one({"_id": ObjectId(db_magnitude["_id"])}, db_magnitude_insert_data)
                magnitude_id = db_magnitude["_id"]
            magnitude_ids.append(magnitude_id)
        else:
            raise Exception(f"Magnitude with ID {magnitude_id} not found! Please ensure that this is an update operation")
            
    # Insert or update event
    db_event_insert_data = {
        'name': "(Manual) Earthquake " + cluster['origin_time'],
        'cluster_id': ObjectId(cluster['_id']),
        'arrival_ids': [ObjectId(arrival['_id']) for arrival in arrivals['P_dict'].values.tolist() + arrivals['S_dict'].values.tolist()],
        **event,
        # 'longitude': event['longitude'],
        # 'latitude': event['latitude'],
        # 'depth': event['latitude'],
        'magnitude_ids': magnitude_ids,
        'modified_by': user_id,
        'event_auto_ref_id': ObjectId(event_auto_ref_id),
        "created_at": UTCDateTime().now().datetime
    }

    del db_event_insert_data['magnitude']
    
    # If event is automatic (user is None), create new event for this event
    if db_event.get('modified_by') == None:
        print("Inserting new event")
        # Insert data to DB and get ID for each event timestamp
        event_id = event_col.insert_one(db_event_insert_data).inserted_id
    # Else, update existing event
    else:
        print(f"Updating event {db_event['_id']}")
        db_event_insert_data = {"$set": db_event_insert_data}
        event_col.update_one({"_id": ObjectId(db_event["_id"])}, db_event_insert_data)
        event_id = db_event["_id"]
        
    return event_id, magnitude_ids

def send_relocmag_to_kafka(event, cluster, arrivals, event_id, magnitude_ids, producer, user_id=None, event_auto_ref_id=None):
    kafka_data = {
        '_id': str(event_id),
        'name': "Earthquake " + str(cluster['origin_time']),
        'cluster': cluster,
        'arrivals': [arrival for arrival in [arrivals['P_dict'].values.tolist()] + [arrivals['S_dict'].values.tolist()]],
        **event,
        # 'longitude': event['longitude'],
        # 'latitude': event['latitude'],
        # 'depth': event['depth'],
        'magnitudes': [
            {
                '_id': str(magnitude_ids[0]),
                'type': 'Mw',
                'value': event['magnitude'],  
                'modified_by': None,
            }
        ],
        'modified_by': str(user_id),
        'event_auto_ref_id': str(event_auto_ref_id),
        "created_at": str(UTCDateTime().now())
    }
    del kafka_data['magnitude']
    
    kafka_data = convert_object_ids(kafka_data)
    producer.send(RELOCATION_FEEDBACK_TOPIC, json.dumps(kafka_data).encode())