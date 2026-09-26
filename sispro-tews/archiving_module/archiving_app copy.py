import asyncio
import logging
import os
import json
import numpy as np
from datetime import date, datetime
from dotenv import load_dotenv
from confluent_kafka import Consumer, KafkaException, KafkaError
from obspy import Stream, Trace, read

load_dotenv("./.env")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')

# Kafka configuration
conf = {
    # Adjust this to your Kafka server
    'bootstrap.servers': kafka_host + ':' + str(kafka_port),
    'group.id': 'YOUR_CONSUMER_GROUP',
    'auto.offset.reset': 'latest',  # Start consuming from the latest message
    'enable.auto.commit': False
}


def app():
    # Create a Consumer instance
    consumer = Consumer(conf)

    # Topic to consume
    topic = 'waveform_seedlink'  # Replace with your topic name

    # Subscribe to the topic
    consumer.subscribe([topic])

    try:
        while True:
            msg = consumer.poll(timeout=1.0)  # Poll for messages
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    logger.info(f'{msg.topic()} [{msg.partition()}] reached end at offset {msg.offset()}')
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                # Proper message
                today = datetime.utcnow().date()

                try:
                    kafka_data = json.loads(msg.value().decode("utf-8"))
                    print(kafka_data)  # Debugging line

                    required_keys = ["network", "station", "channel",
                                     "waveform", "location", "starttime", "sampling_rate"]
                    if all(key in kafka_data for key in required_keys):
                        # Proceed with your logic
                        path_save = f"../archive_data/{today}/{kafka_data['network']}/{kafka_data['station']}/{kafka_data['channel']}"
                        path_save_day = f"{path_save}/day_mseed"

                        os.makedirs(path_save, exist_ok=True)
                        os.makedirs(path_save_day, exist_ok=True)

                        utc_year = str(today.year)
                        utc_julian_day = today.strftime('%j')

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

                        day_mseed_filename = f"{kafka_data['network']}.{kafka_data['station']}.{kafka_data['location']}.{kafka_data['channel']}.{utc_year}.{utc_julian_day}.mseed"
                        day_mseed_filepath = os.path.join(
                            path_save_day, day_mseed_filename)
                        print(day_mseed_filepath)
                        print()
                        if not os.path.isfile(day_mseed_filepath):
                            stream = Stream([trace])
                            stream.write(day_mseed_filepath, format="MSEED")
                        else:
                            try:
                                import io
                                reclen = 512
                                with open(day_mseed_filepath, 'rb') as fh:
                                    data = []
                                    block = fh.read(reclen)
                                    while block:
                                        data.append(block)
                                        block = fh.read(reclen)

                                data = io.BytesIO(b''.join(data))
                                data.seek(0)

                                st1 = read(data, format='MSEED')

                                existing_traces = [
                                    tr for tr in st1 if tr.stats.station == trace.stats.station and
                                    tr.stats.network == trace.stats.network and
                                    tr.stats.starttime == trace.stats.starttime and
                                    tr.stats.endtime == trace.stats.endtime
                                ]

                                if existing_traces:
                                    # Replace the existing trace(s) with the new trace
                                    for tr in existing_traces:
                                        st1.remove(tr)
                                    st1.append(trace)
                                else:
                                    # Append the new trace if no matching traces are found
                                    st1.append(trace)

                                st1.sort(keys=['starttime'])
                                st1.write(day_mseed_filepath, format='MSEED')
                            except UserWarning as e:
                                logger.warning(f"Caught an exception: {e}")
                            except Exception as e:
                                logger.error(
                                    f"Error while reading MiniSEED file st1: {e}")

                        date_str = trace.stats.starttime.strftime("%Y.%j")
                        fmtstr = '/'.join(date_str.split('.')
                                          [:1] + [trace.id.split('.')[i] for i in [0, 1, 3]]) + ".D"
                        directory = f"../archive/{fmtstr}"

                        os.makedirs(directory, exist_ok=True)

                        filename1 = f"{directory}/{trace.id}.D.{date_str}.mseed"
                        print(directory)
                        print(filename1)
                        print()
                        # Check if the file exists to append or create a new one
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
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Close down consumer to commit final offsets.
        consumer.close()
        logger.info("Consumer closed.")


if __name__ == "__main__":
    print("Starting archiving app...")
    app()
