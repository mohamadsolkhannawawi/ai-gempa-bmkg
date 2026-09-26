

from repositories.origin_repository import origin_find_by_id_repository

from dotenv import load_dotenv
from utils.util import get_response
from utils.util import convert_object_id, convert_object_ids

from bson.objectid import ObjectId
from kafka import KafkaProducer, KafkaConsumer
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from confluent_kafka import Consumer
from utils.util import my_random_string
import json
import os

from geopy.distance import geodesic
from obspy.taup import TauPyModel
import os
import zipfile
import shutil
import time
import random
import obspy

import numpy as np
import pandas as pd

load_dotenv("./.env")

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')

def origin_get_detail_service(
        db, 
        origin_id,
        current_user
    ):
        
    event_data = origin_find_by_id_repository(db, origin_id=origin_id)
    if event_data != None:
        json_str = convert_object_ids(event_data)
        return get_response(
            True,
            "get origin detail success",
            json_str

        )
    
    return get_response(
        False,
        "cannot get origin detail",
        None
    )
    

async def origin_commit_service(
        origin_id,
        user_id
    ):

    # Send a message
    producer = AIOKafkaProducer(bootstrap_servers=kafka_host+":"+kafka_port)
    consumer = AIOKafkaConsumer("event_commit_feedback", bootstrap_servers=kafka_host+":"+kafka_port)
    try:
        # Sending data to relocmag module using kafka
        data = {
            "origin_id": origin_id,
            "user_id": user_id
        }

        await producer.start()
        await producer.send('origin_commit', json.dumps(data).encode())
        producer.flush()

        # Waiting response from relocmag module
        await consumer.start()
        async for msg in consumer:
            kafka_data = json.loads(msg.value.decode())
            print(kafka_data)
            print(kafka_data['_id'], origin_id)
            print(kafka_data['origin_auto_ref_id'], origin_id)
            if kafka_data['_id'] == origin_id or kafka_data['event_auto_ref_id'] == origin_id:
                data = kafka_data
                break
        
        return get_response(
            True,
                "update origin commit data success",
                data
            )
    except Exception as e:
        return get_response(
            False,
            "update origin commit data failed",
            None
        )
    finally:
        producer.stop()
        
def origin_psteoritical_service(
        eq_origin_time,
        eq_lat,
        eq_lon,
        eq_depth,
        sta_lat,
        sta_lon,
        current_user
):
    try:
        eq_origin_time = obspy.UTCDateTime(eq_origin_time)
        eq_coordinates = (eq_lat,eq_lon)  
        station_coordinates = (sta_lat,sta_lon) 
        distance_km = geodesic(eq_coordinates,station_coordinates).kilometers
        distance_deg = distance_km / 111.32 
        model = TauPyModel(model="ak135")
        arrival = {}
        try: arrival['P'] = (eq_origin_time + model.get_travel_times(source_depth_in_km=eq_depth, distance_in_degree=distance_deg,phase_list=["P"])[0].time).datetime
        except: arrival['P'] = -1
        try: arrival['S'] = (eq_origin_time +  model.get_travel_times(source_depth_in_km=eq_depth, distance_in_degree=distance_deg,phase_list=["S"])[0].time).datetime
        except: arrival['S'] = -1

        data = {
            "arrival":arrival
        }
        return get_response(
            True,
                "update origin commit data success",
                data
            )
    except Exception as e:
        print(e)
        return get_response(
            False,
            "get origin psteoritical failed",
            None
        ) 