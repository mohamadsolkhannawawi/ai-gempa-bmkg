from kafka import KafkaConsumer
from kafka_module.kafka_producer import get_kafka_producer
import json
import os

from dotenv import load_dotenv
load_dotenv("./.env")
kafka_producer = get_kafka_producer()
kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
def get_kafka_consumer():
    
    try:
        consumer = KafkaConsumer('record_stream_listen',
                            group_id='my-group',
                            bootstrap_servers=[kafka_host+':'+kafka_port])
        print("start listening")
        for message in consumer:
            print(message)
            try:
                if message.value != "":
                    parsed_data = json.loads(message.value)
                    from service.record_stream_service import get_record_stream_kafka_service
                    get_record_stream_kafka_service(
                        year = parsed_data["year"],
                        network= parsed_data["network"],
                        station = parsed_data["station"],
                        location = parsed_data["location"],
                        channel = parsed_data["channel"],
                        sds_type = parsed_data["sds_type"],
                        doy= parsed_data["doy"],
                        starttime= parsed_data["starttime"],
                        endtime= parsed_data["endtime"],
                    )
            except Exception as e:
                data = {
                    "status" : False,
                    "message" : str(e),
                    "data" :None
                }
                data = json.dumps(data).encode('utf-8')
                kafka_producer.produce('record_stream_publish', key='key', value=data,)
                kafka_producer.poll(1)
                kafka_producer.flush()
                continue
    except Exception as e:
        print(str(e))
        data = {
            "status" : False,
            "message" : str(e),
            "data" :None
        }
        data = json.dumps(data).encode('utf-8')
        kafka_producer.produce('record_stream_publish', key='key', value=data,)
        kafka_producer.poll(1)
        kafka_producer.flush()