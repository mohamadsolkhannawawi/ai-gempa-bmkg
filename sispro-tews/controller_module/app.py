from fastapi import FastAPI, WebSocket
import socketio
from kafka import KafkaConsumer
import asyncio
import json
# Create a FastAPI app
app = FastAPI()

# Set up Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Kafka consumer setup (adjust 'your_topic' and 'your_kafka_server' accordingly)
kafka_consumer = KafkaConsumer(
    'test',
    bootstrap_servers=['194.195.92.242:9999'],
    auto_offset_reset='latest',
    enable_auto_commit=True,
    group_id='my-group'
)

# Background task to consume messages from Kafka and emit to WebSocket
async def kafka_listener():
    await sio.sleep(10)  # Delay to allow server to start and clients to connect
    for message in kafka_consumer:
        print(message)
        message = json.loads(message.value.decode('utf-8'))
        await sio.emit('kafka_message', message)

# Start background task
@sio.event
async def connect(sid, environ, auth):
    print('Client connected:', sid)
    sio.start_background_task(kafka_listener)

@sio.event
def disconnect(sid):
    print('Client disconnected:', sid)

# Mount the Socket.IO app to make it available at the root
app.mount('/', socket_app)
