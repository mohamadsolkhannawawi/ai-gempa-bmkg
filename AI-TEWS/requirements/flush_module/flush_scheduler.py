from rocketry import Rocketry
from rocketry.conds import every

import sys, time

sys.setrecursionlimit(100000) 

from datetime import datetime
from dotenv import load_dotenv
from redis_flusher import delete_redis
from kafka_flusher import delete_kafka
load_dotenv("./.env")


# Creating the Rocketry app
app = Rocketry(config={"task_execution": "async"})

# Creating some tasks
@app.task(every("900 seconds"))
async def profile_process():
    try:

        # Get the current time
        current_time = datetime.now()

        # Check if the current minute is 30
        print("Flushing...")
        delete_redis()
        # delete_kafka()
    except Exception as e:
        print(str(e))


if __name__ == "__main__":
    # If this script is run, only Rocketry is run
    app.run()

