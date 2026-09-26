from fastapi import FastAPI, WebSocket
import os
import asyncio
from dotenv import load_dotenv
import json
from aiokafka import AIOKafkaConsumer, ConsumerRebalanceListener
import logging
import uuid
# Load environment variables
load_dotenv()

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
kafka_url = f"{kafka_host}:{kafka_port}"


class RebalanceListener(ConsumerRebalanceListener):
    async def on_partitions_revoked(self, revoked):
        logging.info(f"Partitions revoked: {revoked}")

    async def on_partitions_assigned(self, assigned):
        logging.info(f"Partitions assigned: {assigned}")



async def event_send_messages(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"status": "connected"})
    
    consumer = AIOKafkaConsumer(
        'event',
        bootstrap_servers=kafka_url,
        )
    # Get cluster layout and join group `my-group`
    await consumer.start()
    try:
        # Consume messages
        async for msg in consumer:
            try:
                decoded_message = json.loads(msg.value.decode('utf-8'))
                logging.info(f"Received message: {decoded_message}")
                await websocket.send_json(decoded_message)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode message: {e}")
    finally:
        # Will leave consumer group; perform autocommit if enabled.
        await consumer.stop()

    
    