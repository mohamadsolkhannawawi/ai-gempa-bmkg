from fastapi import FastAPI, Response
from subprocess import Popen, PIPE
import logging
import redis
import os
from utils import *
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Store the PIDs of the running processes
pids = {}
print("Starting...")

r = redis.Redis(host=redis_host, port=int(redis_port), db=0)
FGSK = r.lrange('stored_seedlink_keys', 0, -1)
FGSK = [item.decode('utf-8') for item in FGSK]

@app.get("/start_player")
async def start_player():
    print(f"{len(FGSK)=}")
    CHANNEL_COUNT = len(FGSK)
    INSTANCE_COUNT = 10
    # Start the player.py process and pipe the output to player.log
    for i in range(INSTANCE_COUNT):
        start = i * int(CHANNEL_COUNT / INSTANCE_COUNT)
        end = (start + int(CHANNEL_COUNT / INSTANCE_COUNT)) if i < INSTANCE_COUNT-1 else CHANNEL_COUNT
        with open(f"player{i}.log", "w") as log_file:
            process = Popen(["python", "player.py", str(start), str(end)], stdout=log_file, stderr=log_file)
            pids["player"] = process.pid
            logging.info(f"Started player.py with PID {process.pid}")
    return {"message": "Player started"}

@app.get("/start_starter")
async def start_starter():
    with open(f"starter.log", "w") as log_file:
        process = Popen(["python", "starter.py"], stdout=log_file, stderr=log_file)
        pids["starter"] = process.pid
        logging.info(f"Started starter.py with PID {process.pid}")
    return {"message": "Starter started"}

@app.get("/kill_player")
async def kill_player():
    # Kill the player.py process
    Popen(["pkill", "-f", "-9", "player.py"])
    logging.info("Killed player.py")
    return {"message": "Player killed"}

@app.get("/kill_starter")
async def kill_starter():
    # Kill the starter.py process
    Popen(["pkill", "-f", "-9", "starter.py"])
    logging.info("Killed starter.py")
    return {"message": "Starter killed"}

@app.get("/status")
async def status():
    # Return the status of the running processes
    status = {}
    for name, pid in pids.items():
        status[name] = "running"
    return status

@app.get("/reset_history")
def reset_history():
    # Connect to Redis
    r = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
    # Iterate over keys that end with '_history' and delete them
    with ThreadPoolExecutor() as executor:
        keys = r.scan_iter(match="*_history")
        for key in keys:
            executor.submit(r.delete, key)
            print(f"Deleted key: {key.decode('utf-8')}")