from repositories.event_repository import event_find_all_repository
from repositories.event_repository import event_find_by_id_repository
from repositories.event_repository import event_find_all_between_date_repository
from repositories.event_repository import event_update_by_event_id_repository

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

load_dotenv("./.env")

kafka_host = os.getenv("kafka_host")
kafka_port = os.getenv("kafka_port")


def event_get_detail_service(db, event_id, current_user):

    event_data = event_find_by_id_repository(db, event_id=event_id)
    if event_data != None:
        json_str = convert_object_ids(event_data[0])
        return get_response(True, "get event detail success", json_str)

    return get_response(False, "cannot get event detail", None)


def event_get_arrival_list_service(db, event_id, current_user):

    event_data = event_find_by_id_repository(db, event_id=event_id)

    if event_data != None:
        json_str = convert_object_id(event_data)
        print(json_str["arrival_ids"])
        return get_response(True, "get event detail success", json_str)

    return get_response(False, "cannot get event detail", None)


def event_find_all_between_date_service(db, start_date, end_date):
    event_datas = event_find_all_between_date_repository(db, start_date, end_date)

    if event_datas != None:

        # for x in user_datas:
        #     print(x)
        # print()
        datas = []
        for event_data in event_datas:
            event_data = convert_object_id(event_data)
            datas.append(event_data)
        return get_response(True, "get event all success", datas)

    return get_response(False, "cannot get event detail", None)


def event_get_all_service(db, page, total_per_page, start_date, end_date, current_user):

    page = int(page)
    total_per_page = int(total_per_page)
    event_datas = event_find_all_repository(
        db, page, total_per_page, start_date, end_date, str(current_user["_id"])
    )

    if event_datas != None:

        # for x in user_datas:
        #     print(x)
        # print()
        datas = []

        for event_data in event_datas:

            json_str = convert_object_ids(event_data)
            datas.append(json_str)
        return get_response(True, "get event all success", datas)

    return get_response(False, "cannot get event detail", None)


def event_update_service(db, event_id, station_id, phase, timestamp):

    event_datas = event_update_by_event_id_repository(
        db, event_id, station_id, phase, timestamp
    )

    if event_datas != None:

        datas = []
        for event_data in event_datas:
            event_data = convert_object_id(event_data)
            datas.append(event_data)
        return get_response(True, "update event data success", datas)

    return get_response(False, "update event data failed", None)


async def event_commit_service(arrival_list, event_id, origin_id, user_id):

    # Send a message
    producer = AIOKafkaProducer(bootstrap_servers=kafka_host + ":" + kafka_port)
    consumer = AIOKafkaConsumer(
        "event_commit_feedback", bootstrap_servers=kafka_host + ":" + kafka_port
    )
    try:
        # Sending data to relocmag module using kafka
        data = {"arrival_list": arrival_list, "event_id": event_id, "origin_id": origin_id, "user_id": user_id}

        await producer.start()
        await producer.send("event_commit", json.dumps(data).encode())
        await producer.flush()

        # Waiting response from relocmag module
        await consumer.start()
        async for msg in consumer:
            kafka_data = json.loads(msg.value.decode())
            print(kafka_data)
            if (
                kafka_data["origin_id"] == origin_id and kafka_data["user_id"] == user_id
            ):
                data = kafka_data
                break
            
        if data.get('code') != 200:
            raise Exception(data.get("message"))

        return get_response(True, "update event commit data success", data["data"])
    except Exception as e:
        return get_response(False, "update event commit data failed:" + str(e), None)
    finally:
        await producer.stop()
