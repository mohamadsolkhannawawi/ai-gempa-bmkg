import json
from kafka import KafkaConsumer

# Define the Kafka consumer
consumer = KafkaConsumer(
    'testing_ssh',  # Topic name
    bootstrap_servers='152.118.31.54:9999',
    group_id='my-group',
    auto_offset_reset='latest',
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)

# try:
print('Waiting for messages...')
for message in consumer:
        # Print the message value
    print(f"Received message: {message.value}")
# except Exception as e:
#     print(f"Error while consuming messages: {e}")
# finally:
#     # Close the consumer
#     consumer.close()
