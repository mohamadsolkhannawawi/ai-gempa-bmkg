import sys
import logging
import os
import io
import json
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from kafka import KafkaConsumer
from obspy import Stream, Trace, read
from filelock import FileLock
import threading
import gc
import multiprocessing
import asyncio
from aiokafka import AIOKafkaConsumer

load_dotenv("./.env")

MAX_PROCESS = 5

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')

# Kafka configuration
conf = {
    'bootstrap.servers': f'{kafka_host}:{kafka_port}',
    'group.id': 'YOUR_CONSUMER_GROUP',
    'auto.offset.reset': 'latest',
    'enable.auto.commit': False
}

def save_archive(msg):
    try:
        kafka_data = json.loads(msg.value.decode("utf-8"))

        required_keys = ["network", "station", "channel", "waveform", "location", "starttime", "sampling_rate"]
        if all(key in kafka_data for key in required_keys):
            trace = Trace(data=np.array(kafka_data["waveform"], dtype=float))
            trace.stats.station = kafka_data["station"]
            trace.stats.network = kafka_data["network"]
            trace.stats.location = kafka_data["location"]
            trace.stats.channel = kafka_data["channel"]
            trace.stats.starttime = kafka_data["starttime"]
            trace.stats.sampling_rate = float(kafka_data["sampling_rate"])
            print(trace)

            date_str = trace.stats.starttime.strftime("%Y.%j")
            fmtstr = '/'.join(date_str.split('.')[:1] + [trace.id.split('.')[i] for i in [0, 1, 3]]) + ".D"
            directory = f"/archive/{fmtstr}"

            os.makedirs(directory, exist_ok=True)
            filename1 = f"{directory}/{trace.id}.D.{date_str}.mseed"

            with FileLock(filename1 + ".lock"):
                if os.path.exists(filename1):
                    with open(filename1, 'rb') as fh:
                        data = fh.read()
                    st2 = read(io.BytesIO(data), format='MSEED')

                    existing_traces = [tr for tr in st2 if tr.stats.station == trace.stats.station and
                                       tr.stats.network == trace.stats.network and
                                       tr.stats.starttime == trace.stats.starttime and
                                       tr.stats.endtime == trace.stats.endtime]
                    if existing_traces:
                        for tr in existing_traces:
                            st2.remove(tr)
                        st2.append(trace)
                    else:
                        st2.append(trace)

                    st2.sort(keys=['starttime'])
                    st2.write(filename1, format='MSEED')
                else:
                    trace.write(filename1, format='MSEED')
        else:
            logger.error("Missing one or more required keys in kafka_data")
            raise Exception("Missing one or more required keys in kafka_data")
    except Exception as e:
        logger.error(f"Exception in save_archive: {e}")
    finally:
        gc.collect()
        return

def process(msg):
    try:
        threading.Thread(target=save_archive, args=(msg,)).start()
    except Exception as e:
        logger.error(f"Error: {e}")

async def consume_messages():
    consumer = AIOKafkaConsumer(
        "waveform_seedlink",
        bootstrap_servers=f"{kafka_host}:{kafka_port}",
        loop=asyncio.get_event_loop()
    )
    process_pool = multiprocessing.Pool(processes=MAX_PROCESS)

    await consumer.start()
    try:
        async for msg in consumer:
            process_pool.apply_async(process, args=(msg,))

    except KeyboardInterrupt:
        process_pool.close()
        process_pool.join()
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await consumer.stop()
        logger.info("Consumer stopped.")

async def main():
    try:
        await consume_messages()
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())
