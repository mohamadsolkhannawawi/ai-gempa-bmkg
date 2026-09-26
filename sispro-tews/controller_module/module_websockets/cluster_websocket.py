from fastapi import FastAPI, WebSocket
import os
import asyncio
from dotenv import load_dotenv
import json
from aiokafka import AIOKafkaConsumer

# Load environment variables
load_dotenv()

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
kafka_url = f"{kafka_host}:{kafka_port}"




async def cluster_send_messages(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"status": "connected"})
    
    
    consumer = AIOKafkaConsumer(
        'cluster',
        bootstrap_servers=kafka_url,
    )
    

    await consumer.start()
    try:
        async for msg in consumer:
            try:
                decoded_message = json.loads(msg.value.decode('utf-8'))
                print("Received message: ", decoded_message)
                await websocket.send_json(decoded_message)
            except json.JSONDecodeError as e:
                print("Failed to decode message: ", e)
    except Exception as e:
        print("Error during message processing: ", e)
    finally:
        await websocket.close()
        await consumer.stop()
