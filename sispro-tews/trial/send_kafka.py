import json
from kafka import KafkaProducer

# Define the Kafka producer
producer = KafkaProducer(
    bootstrap_servers='152.118.31.62:9999',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

try:
    # Define the topic
    topic = 'event'

    # Define a sample message
    message = {
        'key1': 'value1',
        'key2': 'value2',
        'key3': 'value3'
    }

    # Send the message to the Kafka topic
    producer.send(topic, value=message)

    # Flush the producer to ensure the message is sent
    producer.flush()

    # Close the producer
    producer.close()

    print('Message sent successfully!')
except Exception as e:
    print(str(e))