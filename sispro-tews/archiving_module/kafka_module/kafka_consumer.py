from kafka import KafkaConsumer


def get_kafka_consumer():
    consumer = KafkaConsumer('record_stream_listen',
                         group_id='my-group',
                         bootstrap_servers=['194.195.92.242:9999'])
    print("kafka start listening")
    for message in consumer:
        print(message.value)