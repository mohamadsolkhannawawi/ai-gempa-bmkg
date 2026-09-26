import asyncio
import logging
import os
import json
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from aiokafka import AIOKafkaConsumer
from obspy import Trace, read

load_dotenv("./.env")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')

# Kafka configuration
conf = {
    'bootstrap_servers': f"{kafka_host}:{kafka_port}",
    'group_id': '',
    'auto_offset_reset': 'latest',
}


async def consume():
    consumer = AIOKafkaConsumer(
        'waveform_seedlink',  # Replace with your topic name
        **conf
    )
    await consumer.start()

    try:
        async for msg in consumer:
            today = datetime.utcnow().date()

            try:
                kafka_data = json.loads(msg.value.decode("utf-8"))
                required_keys = ["network", "station", "channel",
                                 "waveform", "location", "starttime", "sampling_rate"]
                if all(key in kafka_data for key in required_keys):
                    utc_year = str(today.year)
                    utc_julian_day = today.strftime('%j')

                    trace = Trace(data=np.array(
                        kafka_data["waveform"], dtype=float))
                    trace.stats.station = kafka_data["station"]
                    trace.stats.network = kafka_data["network"]
                    trace.stats.location = kafka_data["location"]
                    trace.stats.channel = kafka_data["channel"]
                    trace.stats.starttime = kafka_data["starttime"]
                    trace.stats.sampling_rate = float(
                        kafka_data["sampling_rate"])

                    fmtstr = f"{utc_year}/{kafka_data['network']}/{kafka_data['station']}/{kafka_data['channel']}.D/{kafka_data['network']}.{kafka_data['station']}.{kafka_data['location']}.{kafka_data['channel']}.D.{utc_year}.{utc_julian_day}"
                    directory = f"../archive/{fmtstr}"

                    os.makedirs(directory, exist_ok=True)

                    filename1 = f"{directory}.mseed"
                    print(trace)

                    if os.path.exists(filename1):
                        try:
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

                            st2 = read(data, format='MSEED')

                            existing_traces = [
                                tr for tr in st2 if tr.stats.station == trace.stats.station and
                                tr.stats.network == trace.stats.network and
                                tr.stats.starttime == trace.stats.starttime and
                                tr.stats.endtime == trace.stats.endtime
                            ]

                            if existing_traces:
                                for tr in existing_traces:
                                    st2.remove(tr)
                                st2.append(trace)
                            else:
                                st2.append(trace)

                            st2.sort(keys=['starttime'])
                            st2.write(filename1, format='MSEED')
                        except UserWarning as e:
                            logger.warning(f"Caught an exception: {e}")
                        except Exception as e:
                            logger.error(
                                f"Error while reading MiniSEED file st2: {e}")

                    else:
                        trace.write(filename1, format='MSEED')
                else:
                    logger.error(
                        "Missing one or more required keys in kafka_data")
                    continue
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error while parsing JSON: {e}")
                continue
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await consumer.stop()
        logger.info("Consumer closed.")


if __name__ == "__main__":
    print("Starting archiving app...")
    asyncio.run(consume())
