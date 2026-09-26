import json
from obspy import UTCDateTime
from config import *
from bson import ObjectId

# Function to serialize data to JSON format
def json_serializer(message):
    if type(message)==type({}):
        return message
    elif type(message) == str:
        return json.loads(message)
    return json.loads(message.value.decode('utf-8'))

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

def send_arrivals_to_kafka(pick_arrival_data, db_station, pick_id, producer, user_id=None):
    # Produce pick
    kafka_data = {
        'pick_source_id': str(pick_id),
        'station_id': str(db_station['_id']),
        'network': db_station['network'],
        'station': db_station['code'],
        'longitude': db_station['longitude'],
        'latitude': db_station['latitude'],
        'picks': [
            {
                '_id': str(pick_arrival_data['P']['_id']),
                'timestamp': str(pick_arrival_data['P']['timestamp']),
                'type': 'P',
                "modified_by": user_id,
            },
            {
                '_id': str(pick_arrival_data['S']['_id']),
                'timestamp': str(pick_arrival_data['S']['timestamp']),
                'type': 'S',
                "modified_by": user_id,
            },
        ],
    }

    producer.send(ARRIVAL_PICK_TOPIC, json.dumps(kafka_data).encode())

def send_cluster_to_db(cluster, origin_time, cluster_col, user_id=None):
    # Define DB data
    db_data = {
        'pick_ids': [ObjectId(pick['_id']) for pick in cluster['P_dict'].values],
        'origin_time': origin_time.datetime,
        'rank': 1,
        'modified_by': user_id,
        'created_at': UTCDateTime().now().datetime
    }

    # Insert data to DB and get ID for each pick timestamp
    cluster_id = cluster_col.insert_one(db_data).inserted_id
    return cluster_id

def send_cluster_to_kafka(cluster, cluster_id, origin_time, producer, user_id=None):
    kafka_data = {
        '_id': str(cluster_id), 
        'origin_time': str(origin_time),
        'rank': 1,
        'picks': [
            {
                '_id': str(pick['_id']),
                'timestamp': pick['timestamp'],
            }
            for pick in cluster['P_dict'].values
        ],
        'modified_by': user_id,
    }
    
    producer.send(CLUSTER_TOPIC, json.dumps(kafka_data).encode())
    return kafka_data # Returned to be used while sending locmag to db / kafka

def send_event_to_db(event, cluster, arrivals, event_col, magnitude_col, user_id=None, event_auto_ref_id=None):
    db_magnitudes_data = [
        {
            'type': 'Mw',
            'value': event['magnitude'],  
            'modified_by': user_id,
        }
    ]

    magnitude_ids = magnitude_col.insert_many(db_magnitudes_data).inserted_ids

    db_event_data = {
        'name': "Earthquake " + cluster['origin_time'],
        'cluster_id': ObjectId(cluster['_id']),
        'arrival_ids': [ObjectId(arrival['_id']) for arrival in arrivals['P_dict'].values.tolist() + arrivals['S_dict'].values.tolist()],
        **event,
        'magnitude_ids': magnitude_ids,
        'modified_by': user_id,
        'event_auto_ref_id': event_auto_ref_id,
        "created_at": UTCDateTime().now().datetime
    }

    del db_event_data['magnitude']
    
    event_id = event_col.insert_one(db_event_data).inserted_id
    return event_id, magnitude_ids

def send_event_to_kafka(event, cluster, arrivals, event_id, magnitude_ids, producer, user_id=None, event_auto_ref_id=None):
    kafka_data = {
        '_id': str(event_id),
        'name': "Earthquake " + str(cluster['origin_time']),
        'cluster': cluster,
        'arrivals': [arrival for arrival in arrivals['P_dict'].values.tolist() + arrivals['S_dict'].values.tolist()],
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
        'modified_by': user_id,
        'event_auto_ref_id': event_auto_ref_id,
        "created_at": str(UTCDateTime().now())
    }
    del kafka_data['magnitude']
    
    producer.send(EVENT_TOPIC, json.dumps(kafka_data).encode())

def get_inventory(db):
    user_station_ids = db['user'].find_one({"username":USER_NAME})['stations']
    db_station = []
    for db_sta in db['station'].find({}):
        if db_sta['_id'] in user_station_ids: db_station += [db_sta]
    if len(db_station) > 0: return pd.DataFrame(db_station)