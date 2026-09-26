from confluent_kafka import Consumer, KafkaException
from dotenv import load_dotenv
import logging
import os
load_dotenv("./.env")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')


# Configuration settings for the consumer
conf = {
    'bootstrap.servers': kafka_host + ':' + str(kafka_port),
    'group.id': 'YOUR_CONSUMER_GROUP',
    'auto.offset.reset': 'latest',  # Start consuming from the latest message
    'enable.auto.commit': False
}

# Create a Consumer instance
consumer = Consumer(conf)

# Subscribe to the topic
topic = 'waveform_seedlink'
consumer.subscribe([topic])

def consume_latest_message():
    while True:
        try:
            # Poll for new messages
            msg = consumer.poll(timeout=10.0)  # Timeout in seconds

            if msg is None:
                print('No new messages')
                return None
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    print('End of partition reached {0}/{1}'.format(msg.topic(), msg.partition()))
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                # Print the key and value of the message
                print('Received message: key={} value={}'.format(msg.key(), msg.value()))
                return msg.value()
        finally:
            # Close down consumer to commit final offsets.
            consumer.close()

# Call the function to consume the latest message
latest_message = consume_latest_message()
