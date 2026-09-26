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
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import gc
# Load environment variables
load_dotenv()

# Initialize Redis with a connection pool
redis_host = os.getenv('redis_host', 'localhost')
redis_port = int(os.getenv('redis_port', 6379))
redis_client = aioredis.from_url(f'redis://{redis_host}:{redis_port}', decode_responses=True)

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

# Asynchronous event handler for 'waveform'
@sio.event
async def waveform(sid: str, data: str):
    channel = data
    await sio.enter_room(sid, channel)  # Join the client to the room
    task = asyncio.create_task(send_data(sid, channel))  # Create a subscription task
    tasks[sid] = task  # Track the task

# Helper function to parse datetime strings
def parse_datetime(datetime_str: str) -> datetime.datetime:
    return datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")

async def fetch_valid_data(channel: str) -> list:
    current_timestamp = int(time.time())
    messages = await redis_client.lrange(f'{channel}_history', 0, 4000)  # Limit to the last 100 messages

    # Parse JSON strings efficiently
    data_list = json.loads('[' + ','.join(messages) + ']')  # Join messages and parse as a list

    # Create DataFrame directly from the list of dictionaries
    df = pd.DataFrame(data_list)

    if df.empty:
        return []

    # Filter valid data
    df['expiration_timestamp'] = pd.to_numeric(df['expiration_timestamp'], errors='coerce')
    valid_df = df[df['expiration_timestamp'] > current_timestamp]

    # Convert DataFrame back to list of dictionaries
    valid_datas = valid_df.to_dict(orient='records')

    return valid_datas

# Send initial data from Redis to the client
async def send_data(sid: str, channel: str):
    async with asyncio.Lock():
        valid_datas = await fetch_valid_data(channel)
        sorted_valid_data = sorted(valid_datas, key=lambda x: parse_datetime(x['starttime']))
        if valid_datas:
            try:
                await sio.emit(f'data-{channel}', sorted_valid_data, room=channel)  # Emit to a specific client
                logger.info(f"Initial data sent to {sid} for channel {channel}")
            except Exception as e:
                logger.error(f"Error sending initial data to {sid}: {e}")


# Run the server with Uvicorn
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
