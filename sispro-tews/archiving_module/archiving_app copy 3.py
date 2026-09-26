import sys
import logging
import os
import json
import numpy as np
from datetime import date, datetime
from dotenv import load_dotenv
from kafka import KafkaConsumer
# from confluent_kafka import Consumer, KafkaException, KafkaError
from obspy import Stream, Trace, read
from filelock import FileLock
import threading
import gc
from concurrent.futures import ProcessPoolExecutor
import asyncio
from aiokafka import AIOKafkaConsumer
load_dotenv("./.env")

MAX_PROCESS = 200
MAX_JOB = MAX_PROCESS * 100

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')

# def my_random_string(string_length=10):
#     """Returns a random string of length string_length."""
#     random = str(uuid.uuid4()) # Convert UUID format to a Python string.
#     random = random.replace("-","") # Remove the UUID '-'.
#     random = random.lower()
#     return random[0:string_length] # Return the random string.

# Kafka configuration
conf = {
    # Adjust this to your Kafka server
    'bootstrap.servers': kafka_host + ':' + str(kafka_port),
    'group.id': 'YOUR_CONSUMER_GROUP',
    'auto.offset.reset': 'latest',  # Start consuming from the latest message
    'enable.auto.commit': False
}

def save_archive(msg):
    try:
        kafka_data = json.loads(msg.value.decode("utf-8"))
        # print(kafka_data)  # Debugging line

        required_keys = ["network", "station", "channel",
                            "waveform", "location", "starttime", "sampling_rate"]

        if all(key in kafka_data for key in required_keys):
            # Proceed with your logic
            trace = Trace(data=np.array(
                kafka_data["waveform"], dtype=float))
            # Station name
            trace.stats.station = kafka_data["station"]
            # Network code
            trace.stats.network = kafka_data["network"]
            # Location code
            trace.stats.location = kafka_data["location"]
            # Channel code
            trace.stats.channel = kafka_data["channel"]
            trace.stats.starttime = kafka_data["starttime"]
            trace.stats.sampling_rate = float(
                kafka_data["sampling_rate"])

            date_str = trace.stats.starttime.strftime("%Y.%j")
            fmtstr = '/'.join(date_str.split('.')
                                [:1] + [trace.id.split('.')[i] for i in [0, 1, 3]]) + ".D"
            directory = f"../archive/{fmtstr}"

            os.makedirs(directory, exist_ok=True)

            filename1 = f"{directory}/{trace.id}.D.{date_str}.mseed"
            print(trace)
            # print(directory)
            # print(filename1)
            # print()

            if os.path.exists(filename1):
                try:
                    with FileLock(filename1 + ".lock"):
                        import io
                        reclen = 512
                        with open(filename1, 'rb') as fh:
                            data = []
                            block = fh.read(reclen)
                            while block:
                                data.append(block)
                                block = fh.read(reclen)

                        data = io.BytesIO(b''.join(data))
                        data.seek(0)

                        # Overwrite empty files caused by forced program stops
                        if (data.getbuffer().nbytes == 0):
                            trace.write(filename1, format='MSEED')
                        else:
                            st2 = read(data, format='MSEED')

                            existing_traces = [
                                tr for tr in st2 if tr.stats.station == trace.stats.station and
                                tr.stats.network == trace.stats.network and
                                tr.stats.starttime == trace.stats.starttime and
                                tr.stats.endtime == trace.stats.endtime
                            ]

                            if existing_traces:
                                # Replace the existing trace(s) with the new trace
                                for tr in existing_traces:
                                    st2.remove(tr)
                                st2.append(trace)
                            else:
                                st2.append(trace)

                            st2.sort(keys=['starttime'])
                            st2.write(filename1, format='MSEED')
                except UserWarning as e:
                    logger.warning(f"Caught an exception: {e}")
                    raise e
                except Exception as e:
                    logger.error(
                        f"Error while reading MiniSEED file st2: {e}")
                    raise e
            else:
                with FileLock(filename1 + ".lock"):                
                    trace.write(filename1, format='MSEED')
        else:
            logger.error(
                "Missing one or more required keys in kafka_data")
            raise Exception("Missing one or more required keys in kafka_data")
    except Exception as e:
        raise e
    finally:
        sys.stdout.flush()
        gc.collect()
        return
    
def process(msg,):
    try:
        threading.Thread(target=save_archive, args=(msg, )).start()
    except Exception as e:
        logger.error(f"Error: {e}")


async def consume_messages():
    consumer = AIOKafkaConsumer(
        "waveform_seedlink",
        bootstrap_servers=f"{kafka_host}:{kafka_port}",
        loop=asyncio.get_event_loop()
    )
    process_pool = ProcessPoolExecutor(max_workers=MAX_PROCESS)

    await consumer.start()

    try:
        async for msg in consumer:
            # uvicorprocess_pool.submit(process, msg)
            asyncio.create_task(process(msg))

    except KeyboardInterrupt:
        process_pool.shutdown()
    except Exception as e:
        logger.error(f"Error: {e}")

    await consumer.stop()
    logger.info("Consumer stopped.")

async def main():
    try:
        await consume_messages()
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    asyncio.run(main())