import json
from obspy import UTCDateTime
from config import *

# Function to serialize data to JSON format
def json_serializer(message):
    if type(message)==type({}):
        return message
    elif type(message) == str:
        return json.loads(message)
    return json.loads(message.value.decode('utf-8'))


def send_picks_to_kafka(db_station, picks, pick_ids, producer):
    kafka_data = {}
    # Produce pick
    kafka_data = {
        'station_id': db_station['_id'],
        'network': db_station['network'],
        'station': db_station['code'],
        'picks': [
            {
                '_id': str(pick_ids[i]),
                'timestamp': pick['timestamp']
            }
            for i, pick in enumerate(picks)
        ]
    }

    producer.send(PICK_TOPIC, json.dumps(kafka_data).encode())

def send_picks_to_db(db_station, pick_col, picks):
    # Define DB data
    db_data = [
        {
            'station_id': db_station['_id'],
            'timestamp': UTCDateTime(pick['timestamp']).datetime,
            'created_at': UTCDateTime().now().datetime
        }
        for pick in picks
    ]
    # Insert data to DB and get ID for each pick timestamp
    pick_ids = pick_col.insert_many(db_data).inserted_ids
    return pick_ids
    
def send_arrival_waveform_to_kafka(db_station, full_waveform, delta, picks, pick_ids, producer):
    # Send initial waveform to phase arrival pick to be stored
    for id, pick in zip(pick_ids, picks):
        # Calculate offset of waveform that will be pulled
        # Ideally, it should start at -(half_window) before pick timestamp
        start_of_window = UTCDateTime(pick['timestamp']) - WINDOW_SIZE_SEC / 2

        # Calculate offset (around pick) and get waveform by offset
        picked_timestamp_offset = round(start_of_window - full_waveform['starttime'], ndigits=3)
        picked_idx_offset = round(picked_timestamp_offset / delta)
        
        offset_waveform = {
            channel[-1]: waveform_data[picked_idx_offset:].tolist()
            for channel, waveform_data in full_waveform['waveform'].items()
        }

        # Send arrival waveform to kafka
        arrival_waveform = {
            'station_id': str(db_station['_id']),
            'network': db_station['network'],
            'station': db_station['code'],
            'pick_id': str(id),
            'starttime': str(start_of_window),
            'endtime': str(full_waveform['endtime']),
            'delta': delta,
            'waveform': offset_waveform,
        }

        producer.send(ARRIVAL_WAVEFORM_TOPIC, json.dumps(arrival_waveform).encode())