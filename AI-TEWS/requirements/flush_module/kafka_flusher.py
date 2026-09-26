from kafka.admin import KafkaAdminClient
import os
from dotenv import load_dotenv

# env constant
load_dotenv("./.env")
kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')

def delete_kafka():
    # Connect to Kafka
    admin_client = KafkaAdminClient(
        bootstrap_servers=[kafka_host+":"+kafka_port],
        client_id='test_client'
    )

    # List all topics
    topic_list = admin_client.list_topics()

    # Delete topics
    admin_client.delete_topics(topics=topic_list, timeout_ms=5000)

