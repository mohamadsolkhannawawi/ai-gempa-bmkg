import json
from obspy import UTCDateTime
from config import *
from bson import ObjectId

def ts_transform(x):
    return round(UTCDateTime(str(x)).timestamp*1000)

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
                'timestamp': pick,
                'snr': 15
            }
            for i, pick in enumerate(pick_candidates)
        ]
    }

    producer.send(PICK_TOPIC, json.dumps(kafka_data).encode())

def get_db_station(network, code, db):
    user_station_ids = db['user'].find_one({"username":USER_NAME})['stations']
    db_station = None
    for db_sta in db['station'].find({'network': network, 'code': code}):
        if db_sta['_id'] in user_station_ids: db_station = db_sta
    if db_station != None: return db_station