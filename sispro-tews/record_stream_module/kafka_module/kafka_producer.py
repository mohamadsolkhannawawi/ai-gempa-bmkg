from confluent_kafka import Producer
import os
from dotenv import load_dotenv
load_dotenv("./.env")
kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
def get_kafka_producer():
    conf = {'bootstrap.servers': kafka_host+':'+kafka_port}
    producer = Producer(**conf)
    return producer