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


def send_cluster_to_db(cluster, origin_time, cluster_col):
    # Define DB data
    db_data = {
        'pick_ids': [ObjectId(pick_id) for pick_id in cluster['Pick_source_ids'].values],
        'origin_time': origin_time.datetime,
        'rank': 1,
        'modified_by': None,
        'created_at': UTCDateTime().now().datetime
    }

    # Insert data to DB and get ID for each pick timestamp
    cluster_id = cluster_col.insert_one(db_data).inserted_id
    return cluster_id

def send_cluster_to_kafka(cluster, cluster_id, origin_time, producer):
    kafka_data = {
        '_id': str(cluster_id), 
        'origin_time': str(origin_time),
        'rank': 1,
        'picks': [str(pick_id) for pick_id in cluster['Pick_source_ids'].values],
        'modified_by': None,
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
        # 'longitude': event['longitude'],
        # 'latitude': event['latitude'],
        # 'depth': event['latitude'],
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
        'modified_by': user_id,
        'event_auto_ref_id': event_auto_ref_id,
        "created_at": str(UTCDateTime().now())
    }
    del kafka_data['magnitude']
    
    producer.send(EVENT_TOPIC, json.dumps(kafka_data).encode())

def send_reloc_to_kafka(arrivals, event_id, producer):
    kafka_data = {
        'arrival_list': [arrival for arrival in [arrivals['P_dict'].values.tolist()] + [arrivals['S_dict'].values.tolist()]],
        "event_auto_ref_id": event_id
    }
    producer.send(RELOCATION_TOPIC, json.dumps(kafka_data).encode())

    