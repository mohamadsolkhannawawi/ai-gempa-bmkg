import os
import json
import time
import datetime
import asyncio
from typing import Dict, Any
from fastapi import FastAPI
from socketio import AsyncServer, ASGIApp
from dotenv import load_dotenv
import aioredis
import logging
import gc

# Load environment variables
load_dotenv()

# Initialize Redis with a connection pool
redis_host = os.getenv('redis_host', 'localhost')
redis_port = int(os.getenv('redis_port', 6379))
redis_client = aioredis.from_url(f'redis://{redis_host}:{redis_port}',)

# Create a Socket.IO server
sio = AsyncServer(async_mode='asgi', cors_allowed_origins='*', logger=True)
app = FastAPI()
app.mount("/", ASGIApp(sio, socketio_path='socket.io'))

# Store connected clients and their tasks to manage disconnections
clients = {}
tasks = {}


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@sio.event
async def connect(sid: str, environ: Dict[str, Any]):
    logger.info(f"Client connected: {sid}")
    clients[sid] = True
    try:
        # Additional setup if needed
        await sio.save_session(sid, {"connected": True})
    except Exception as e:
        logger.error(f"Error during client setup for {sid}: {e}")
    finally:
        gc.collect()

@sio.event
async def disconnect(sid: str):
    logger.info(f"Client disconnected: {sid}")
    try:
        if sid in clients:
            del clients[sid]
        if sid in tasks:
            tasks[sid].cancel()
            del tasks[sid]
        await sio.leave_room(sid, '*')
    except Exception as e:
        logger.error(f"Error during client disconnection for {sid}: {e}")
    finally:
        gc.collect()

@sio.event
async def waveform(sid: str, data: str):
    channel = data
    try:
        await sio.enter_room(sid, channel)
        await send_initial_data(sid, channel)
        task = asyncio.create_task(subscribe_to_channel(sid, channel))
        tasks[sid] = task
    except Exception as e:
        logger.error(f"Error handling waveform for {sid} on channel {channel}: {e}")

def parse_datetime(datetime_str: str) -> datetime.datetime:
    return datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")

async def fetch_valid_data(channel: str, batch_size: int = 100):
    current_timestamp = int(time.time())
    start = 0
    valid_datas = []

    while True:
        messages = await redis_client.lrange(f'{channel}_history', start, start + batch_size - 1)
        if not messages:
            break  # Exit the loop if no messages are returned
        start += batch_size

        for message in messages:
            data = json.loads(message)
            if int(data['expiration_timestamp']) > current_timestamp:
                valid_datas.append(data)

    return valid_datas


# Assuming the lock is initialized outside this function and is shared where necessary
lock = asyncio.Lock()

async def send_initial_data(sid: str, channel: str):
    async with lock:
        try:
            valid_datas = await fetch_valid_data(channel)
            # Sort by starttime using datetime parsing only if needed
            if valid_datas:
                sorted_valid_data = sorted(valid_datas, key=lambda x: parse_datetime(x['starttime']))
                await sio.emit(f'data-{channel}', sorted_valid_data, room=channel)
                logger.info(f"Initial data sent to {sid} for channel {channel}")
        except Exception as e:
            logger.error(f"Error in send_initial_data for {sid} and channel {channel}: {e}")

async def subscribe_to_channel(sid: str, channel: str):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    try:
        while clients.get(sid, False):
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    current_timestamp = int(time.time())
                    if int(data['expiration_timestamp']) > current_timestamp:
                        valid_datas = await fetch_valid_data(channel, batch_size=10)
                        valid_datas.append(data)
                        sorted_valid_data = sorted(valid_datas, key=lambda x: parse_datetime(x['starttime']))
                        try:
                            await sio.emit(f'data-{channel}', sorted_valid_data, room=channel)
                            logger.info(f"Data sent to channel {channel}")
                        except Exception as e:
                            logger.error(f"Error sending data to channel {channel}: {e}")
                        del valid_datas, sorted_valid_data
                    del data, current_timestamp
                except Exception as e:
                    logger.error(f"Error processing message for channel {channel}: {e}")
            await asyncio.sleep(0.1)
            del message
    except asyncio.CancelledError:
        logger.info(f"Subscription to {channel} for {sid} cancelled.")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()



if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
