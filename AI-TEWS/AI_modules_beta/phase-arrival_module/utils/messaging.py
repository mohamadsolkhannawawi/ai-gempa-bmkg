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


def ts_transform(x):
    return round(UTCDateTime(str(x)).timestamp*1000)

# Arrivals
def send_arrivals_to_db(pick_arrival_data, db_station, pick_id, arrival_col):
    # Define DB data
    db_data = [
        # P arrival DB
        {
            "pick_source_id": ObjectId(pick_id),
            "station_id": ObjectId(db_station['_id']),
            "timestamp": pick_arrival_data['P']['timestamp'],
            "phase_type": "P",
            "modified_by": None,
            "created_at": UTCDateTime().now().datetime
        },
        {
            "pick_source_id": ObjectId(pick_id),
            "station_id": ObjectId(db_station['_id']),
            "timestamp": pick_arrival_data['S']['timestamp'],
            "phase_type": "S",
            "modified_by": None,
            "created_at": UTCDateTime().now().datetime
        }
    ]
    
    # Insert data to DB and get ID for each arrival timestamp
    arrival_ids = arrival_col.insert_many(db_data).inserted_ids
    return arrival_ids

def send_arrivals_to_kafka(pick_arrival_data, db_station, pick_id, producer):
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
                "modified_by": None,
            },
            {
                '_id': str(pick_arrival_data['S']['_id']),
                'timestamp': str(pick_arrival_data['S']['timestamp']),
                'type': 'S',
                "modified_by": None,
            },
        ],
    }

    producer.send(ARRIVAL_PICK_TOPIC, json.dumps(kafka_data).encode())

def get_db_station(network, code, db):
    user_station_ids = db['user'].find_one({"username":USER_NAME})['stations']
    db_station = None
    for db_sta in db['station'].find({'network': network, 'code': code}):
        if db_sta['_id'] in user_station_ids: db_station = db_sta
    if db_station != None: return db_station