from obspy.clients.filesystem.sds import Client
from obspy import UTCDateTime, Trace
import numpy as np
import gc
import traceback
from kafka_module.kafka_producer import get_kafka_producer
from datetime import datetime, timedelta
import json
import os
import aioredis
import time
import pandas as pd
kafka_producer = get_kafka_producer()


def get_record_stream_kafka_service(
        year:str,
        network:str,
        station:str,
        location:str,
        channel:str,
        sds_type:str,
        doy:str,
        starttime:str,
        endtime:str
):
    
    try:
        Client.FMTSTR= year+'/'+network+'/'+station+'/'+channel+'.'+sds_type+'/'+network+'.'+station+'.'+location+'.'+channel+'.'+sds_type+'.'+year+'.'+doy+'.mseed'
        client_sds = Client(sds_root='../archive')

        st = client_sds.get_waveforms(
            network=network, 
            station=station, 
            location=location, 
            channel=channel, 
            starttime=UTCDateTime(starttime), 
            endtime=UTCDateTime(endtime))
        st.merge()
        json_string = {
                "time_start":str(st[0].stats.starttime),
                "time_end":str(st[0].stats.endtime),
                "sampling_rate": st[0].stats.sampling_rate,
                    # "record_length": trace.stats.number_of_records,
                "delta": st[0].stats.delta,
                "location": st[0].stats.location,
                "npts": st[0].stats.npts,
                "station":st[0].stats.station,
                "network":st[0].stats.network,
                "channel":st[0].stats.channel,
                "waveform":(st[0].data/1000).tolist()
            }

        data = {
            "status" : True,
            "message" : "get data stream success",
            "data" :json_string
        }
        # del file_extension, img_shapes, filename, file_path, img_rgb, liveness_class, score
        gc.collect()
        data = json.dumps(data).encode('utf-8')
        kafka_producer.produce('record_stream_publish', key='key', value=data,)
        kafka_producer.poll(1)
        kafka_producer.flush()

        return 
    except Exception as e:
        data = {
            "status" : False,
            "message" : str(e),
            "data" :None
        }
        data = json.dumps(data).encode('utf-8')
        kafka_producer.produce('record_stream_publish', key='key', value=data,)
        kafka_producer.poll(1)
        kafka_producer.flush()
        # del file_extension, img_shapes, filename, file_path, img_rgb, liveness_class, score
        gc.collect()
        return data



async def get_record_stream_api_service(
        year:str,
        network:str,
        station:str,
        location:str,
        channel:str,
        sds_type:str,
        doy:str,
        starttime:str,
        endtime:str
):
    
    try:
        
        Client.FMTSTR= '{year}/{network}/{station}/{channel}.{sds_type}/{network}.{station}.{location}.{channel}.{sds_type}.{year}.{doy}.mseed'
        client_sds = Client(sds_root='/archive')
        st = client_sds.get_waveforms(
            network=network, 
            station=station, 
            location=location, 
            channel=channel, 
            starttime=UTCDateTime(starttime), 
            endtime=UTCDateTime(endtime))
        
        for trace in st:
            trace.data = trace.data.astype('float32')

        # starttime_check = datetime.strptime(starttime, "%Y-%m-%dT%H:%M:%S.%fZ")

        # now = datetime.utcnow()

        # # Calculate the difference between the current time and starttime
        # time_difference = now  - starttime_check

        # Handling to prevent redis error if unneeded
        redis_connected = False
        try:
            channel_station_data = network+"."+station+"."+location+"."+channel
            redis_host = os.getenv('redis_host', 'localhost')
            redis_port = int(os.getenv('redis_port', 6379))
            redis_client = aioredis.from_url(f'redis://{redis_host}:{redis_port}', decode_responses=True)
            redis_connected = True
        except Exception as e:
            print(e)
            
        if redis_connected:
            starttime_timestamp = pd.Timestamp(datetime.strptime(starttime, "%Y-%m-%dT%H:%M:%S.%fZ"), tz='UTC')
            endtime_timestamp = pd.Timestamp(datetime.strptime(endtime, "%Y-%m-%dT%H:%M:%S.%fZ"), tz='UTC')
            current_timestamp = int(time.time())
            
            messages = await redis_client.lrange(f'ori_{channel_station_data}', 0, -1)  # Limit to the last 100 messages

            # Parse JSON strings efficiently
            data_list = json.loads('[' + ','.join(messages) + ']')  # Join messages and parse as a list

            # Create DataFrame directly from the list of dictionaries
            df = pd.DataFrame(data_list)
            
            if not df.empty:
                # Filter valid data
                df['starttime'] = pd.to_datetime(df['starttime'], errors='coerce')
                df['endtime'] = pd.to_datetime(df['endtime'], errors='coerce')
                df['expiration_timestamp'] = pd.to_numeric(df['expiration_timestamp'], errors='coerce')
                print(starttime_timestamp, endtime_timestamp)
                print(df['starttime'], df['endtime'], df['expiration_timestamp'])
                
                # condition_1 = df['expiration_timestamp'] >= current_timestamp
                # condition_2 = df['starttime'] >= starttime_timestamp
                # condition_3 = df['endtime'] <= endtime_timestamp

                # Combine conditions using logical AND
                valid_df = df[(df['starttime'] >= starttime_timestamp) & (df['endtime'] <= endtime_timestamp)]
                
                # Convert DataFrame back to list of dictionaries
                # valid_datas = valid_df.to_dict(orient='records')
                waveform_data = valid_df['waveform'].values
                stations = valid_df['station'].values
                networks = valid_df['network'].values
                locations = valid_df['location'].values
                channels = valid_df['channel'].values
                starttimes = valid_df['starttime'].dt.strftime('%Y-%m-%dT%H:%M:%S.%f').values
                sampling_rates = valid_df['sampling_rate'].values
                
                for i in range(len(valid_df)):
                    trace = Trace(data=np.array(waveform_data[i]))
                    trace.data = trace.data.astype('float32')
                    trace.stats.station = stations[i]
                    trace.stats.network = networks[i]
                    trace.stats.location = locations[i]
                    trace.stats.channel = channels[i]
                    trace.stats.starttime = UTCDateTime(starttimes[i])
                    trace.stats.sampling_rate = sampling_rates[i]
                    if len(st)>0:
                        if int(trace.stats.starttime.timestamp) >= int(st[-1].stats.endtime.timestamp):
                            st.append(trace)
                    else:
                        st.append(trace)
        
        st.merge()
        # waveforms = sum(valid_df["waveform"].tolist(), [])
        # data = {
        #     "status" : True,
        #     "message" : "get data stream success trace",
        #     "data" :{
        #         "time_difference":time_difference,
        #         "time_start":str(starttime),
        #         "time_end":UTCDateTime(starttime) + len(waveforms) / valid_df["sampling_rate"].tolist()[0],
        #         "sampling_rate": valid_df["sampling_rate"].tolist()[0],
        #             # "record_length": trace.stats.number_of_records,
        #         "delta": valid_df["delta"].tolist()[0],
        #         "location": location,
        #         "npts": len(waveforms),
        #         "station":station,
        #         "network":network,
        #         "channel":channel,
        #         "waveform": waveforms
        #     }
        # }
                
        if len(st) == 0:
            return []
        
        json_string = {
            "time_start":str(st[0].stats.starttime),
            "time_end":str(st[0].stats.endtime),
            "sampling_rate": st[0].stats.sampling_rate,
                # "record_length": trace.stats.number_of_records,
            "delta": st[0].stats.delta,
            "location": st[0].stats.location,
            "npts": st[0].stats.npts,
            "station":st[0].stats.station,
            "network":st[0].stats.network,
            "channel":st[0].stats.channel,
            "waveform":(st[0].data).tolist()
        }

        data = {
            "status" : True,
            "message" : "get data stream success",
            "data" :json_string
        }
        
        # del file_extension, img_shapes, filename, file_path, img_rgb, liveness_class, score
        gc.collect()
        return data
    except Exception as e:
        traceback.print_exc()
        data = {
            "status" : False,
            "message" : str(e),
            "data" :None
        }
        # del file_extension, img_shapes, filename, file_path, img_rgb, liveness_class, score
        gc.collect()
        return data

