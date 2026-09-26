import os, redis, json
import numpy as np
import pandas as pd
from obspy import Trace, UTCDateTime
from numpy.lib.stride_tricks import sliding_window_view
from obspy.signal.trigger import aic_simple
from config import *

EXPIRY_TIME = 10 * 60

def detect_pick_station(segment, ncheck):
    return detect_pick(segment[...,-1], ncheck)

def detect_pick(segment, ncheck):
    picks = []
    for seg in segment:
        aic = aic_simple(seg)
        picks.append(np.max(aic[np.isfinite(aic)]) - np.min(aic[np.isfinite(aic)]))
    picks = np.array(picks)
    print(picks.max())
    if picks.max() > THRESHOLD:
        # Applied ncheck
        kernel = np.ones(ncheck)
        picks = np.where(picks >= THRESHOLD, 1, 0)
        picks = (np.convolve(np.pad(picks, len(kernel), mode="maximum")[len(kernel):-1], kernel, mode="valid")/len(kernel)).astype(int)
        # First pick only
        picks = np.pad(picks, 1)
        picks[(picks == 1) & (np.roll(picks, 1) == 1)] = 0
        picks = picks[1:-1]
        # picks = np.random.binomial(1, 0.5, size=picks.shape)
        return picks
    else:
        return np.zeros(picks.shape[0])

def trace_processing(data, sampling_rate):
    header = {
        'network': data['network'],
        'station': data['station'],
        'location': data['location'], 
        'channel': data['channel'],
        'starttime': data['starttime'], 
        'endtime': data['endtime'], 
        'sampling_rate': data['sampling_rate'], 
        'delta': data['delta'],
        'npts': data['npts'],
    }
    trace = Trace(data=np.array(data['waveform']), header=header)
    if trace.stats.sampling_rate!=sampling_rate:
        trace.interpolate(sampling_rate)
    return trace


def single_channel_processing(trace, window_size, center, ncheck, r):
    starttime = UTCDateTime(trace.stats.starttime)
    next_starttime = starttime + (trace.stats.delta*(trace.stats.npts))
    redis_key = f"ai_pick_{trace.stats.network}.{trace.stats.station}.{trace.stats.location}.{trace.stats.channel}" 
    redis_value = {"time": [str(starttime), str(next_starttime)],
                   "data": trace.data[:].tolist(), 
                   "flag": (trace.data[:] * 0).tolist(),
                   "tail": 0}
    
    # Get all messages from the Redis stream
    messages = r.xrange(redis_key, "-", "+") 
    
    taken_starttime = starttime - (trace.stats.delta * (window_size))
    taken_next_starttime = next_starttime + (trace.stats.delta * (window_size))
    expired_time = starttime - EXPIRY_TIME # expired in a day 
    hold_condition = ((window_size+center)//(trace.stats.npts-1+1e-10))+1
    hold_condition_check = ((window_size)//(trace.stats.npts-1+1e-10))+1
    npts = trace.stats.npts
    
    list_taken_time = []
    dict_taken_msg_id = {}
    dict_taken_data = {}
    dict_taken_flag = {}
    dict_taken_tail = {} 
    
    for msg_id, fields in messages:
        # Extract the MiniSEED data and header from the message
        header_json = fields[b'data']
        
        # Decode the header information
        header = json.loads(header_json)
        _time = tuple(header['time'])
        _data = np.array(header['data'])
        _flag = np.array(header['flag'])
        _tail = int(header['tail'])
        
        # Dont use duplicated
        if _time[0]==starttime and _time[1]==next_starttime:
            return {}, 0 

        # Take the needed data back selection
        if taken_starttime < UTCDateTime(_time[1]) and taken_next_starttime > UTCDateTime(_time[0]):
            # print("TAKEN =================", taken_starttime, _time)
            list_taken_time.append(_time)
            dict_taken_msg_id[_time] = msg_id
            dict_taken_data[_time] = _data
            dict_taken_flag[_time] = _flag
            dict_taken_tail[_time] = _tail
        
        # Check if key_flag is full then delete id
        elif _tail >= hold_condition_check and _flag.sum()==_flag.shape[0]:
            # print("DELETE =================", _time)
            r.xdel(redis_key, msg_id)
        elif expired_time > UTCDateTime(_time[1]):
            # print("DELETE =================", _time)
            r.xdel(redis_key, msg_id)

    full_waveform = {}
    segment_data = []
    if len(list_taken_time):
        # print("MESSAGE =================")
        
        # Check if missing then exit
        _counter = 1
        list_taken_time = sorted(list_taken_time+[tuple(redis_value['time'])])
        for lt,lr in zip(list_taken_time[:-1], list_taken_time[1:]):
            
            # print(lt[0],lt[1],lr[0],lr[1], abs(UTCDateTime(lt[1]) - UTCDateTime(lr[0])))
            
            if abs(UTCDateTime(lt[1]) - UTCDateTime(lr[0])) > 1:
                
                # Check if after the current time data is unused
                if (_counter * npts) >= window_size and next_starttime == lt[1] :
                    list_taken_time = list_taken_time[:_counter]
                    break
                    
                # print("MISSING =================")
                # Store to redis
                r.xadd(redis_key, {"data": json.dumps(redis_value)})
                return full_waveform, segment_data

            else: 
                if starttime == lr[0]:
                    redis_value['tail'] = min(hold_condition, _counter)
                else:
                    dict_taken_tail[lr] = min(hold_condition, _counter)

            _counter+=1
        
        dict_taken_flag[tuple(redis_value['time'])] = np.array(redis_value['flag'])
        shitlen = len(list_taken_time)-list_taken_time.index(tuple(redis_value['time']))
        concatenated_flag = np.concatenate([dict_taken_flag[key] for key in list_taken_time])
        
        concatenated_data = []
        if concatenated_flag.shape[0]-npts >= window_size:
            # print("PROCESSED =================", tuple(redis_value['time']))
            
            # Getting sliding window
            dict_taken_data[tuple(redis_value['time'])] = np.array(redis_value['data'])
            concatenated_data = np.concatenate([dict_taken_data[key] for key in list_taken_time])[-window_size-int(shitlen*npts)+1:]
            segment = sliding_window_view(concatenated_data, window_size, axis=0)

            # Assign the latest flag
            concatenated_flag[-len(segment)-center+1:-center+1] += np.ones(len(segment), dtype=np.int64)
            i_ = 0
            reshaped_flag = []
            for key in list_taken_time:
                i__ = dict_taken_flag[key].shape[0] + i_
                reshaped_flag.append(concatenated_flag[i_:i__])
                i_ = i__
            reshaped_flag = {k:v for k,v in zip(list_taken_time, reshaped_flag)}

            # Assign the label
            label = np.zeros(len(concatenated_flag))
            label[-len(segment)-center+1:-center+1] = detect_pick(segment, ncheck)
            for idx in np.where(label)[0]:
                timestamp = str(UTCDateTime(list_taken_time[0][0]) + (trace.stats.delta * idx))
                segment_data.append({"station":trace.id, "timestamp":timestamp})
            
            list_taken_time.remove(tuple(redis_value['time']))
            
            # Update redis with delete the data and create new data
            for taken_key in list_taken_time:
                r.xdel(redis_key, dict_taken_msg_id[taken_key])
                r.xadd(redis_key, {"data": json.dumps({
                    "time": taken_key,
                    "data": dict_taken_data[taken_key].tolist(),
                    "flag": reshaped_flag[taken_key].tolist(),
                    "tail": dict_taken_tail[taken_key],
                })})
            
            # Update current flag
            redis_value['flag']= reshaped_flag[tuple(redis_value['time'])].tolist()

            # Get full waveform of the processed waveform
            full_waveform = {
                'waveform': {
                    trace.stats.channel: concatenated_data
                },
                'starttime': UTCDateTime(list_taken_time[0][0]),
                'endtime': UTCDateTime(list_taken_time[0][0]) + (trace.stats.delta * len(concatenated_data))
            }
            
    # Store to redis
    r.xadd(redis_key, {"data": json.dumps(redis_value)})

    return full_waveform, segment_data



def multi_channel_processing(trace, station_channels, window_size, center, ncheck, r):
    starttime = UTCDateTime(trace.stats.starttime)
    next_starttime = starttime + (trace.stats.delta*(trace.stats.npts))
    redis_key = f"ai_pick_{trace.stats.network}.{trace.stats.station}.{trace.stats.location}.{trace.stats.channel}" 
    redis_value = {"time": [str(starttime), str(next_starttime)],
                   "data": trace.data[:].tolist(), 
                   "flag": (trace.data[:] * 0).tolist(),
                   "tail": 0}
    
    messages = {}

    # Get all messages from the Redis stream
    messages[trace.stats.channel] = r.xrange(redis_key, "-", "+")

    taken_starttime = starttime - (trace.stats.delta * (window_size))
    taken_next_starttime = next_starttime + (trace.stats.delta * (window_size))
    expired_time = starttime - EXPIRY_TIME # expired in a day 
    hold_condition = ((window_size+center)//(trace.stats.npts-1))+1
    hold_condition_check = ((window_size)//(trace.stats.npts-1))+1
    npts = trace.stats.npts
    
    list_taken_time = []
    dict_taken_msg_id = {}
    dict_taken_data = {}
    dict_taken_flag = {}
    dict_taken_tail = {} 
    check_duplicated = []
    save_when_duplicated = {}

    for msg_id, fields in messages[trace.stats.channel]:
        # Extract the MiniSEED data and header from the message
        header_json = fields[b'data']
        
        # Decode the header information
        header = json.loads(header_json)
        _time = tuple(header['time'])
        _data = np.array(header['data'])
        _flag = np.array(header['flag'])
        _tail = int(header['tail'])
        
        # Dont use duplicated
        if _time[0]==starttime and _time[1]==next_starttime:
            return 0
        
        if _time in check_duplicated:
            r.xdel(redis_key, msg_id)
            d_time = check_duplicated[check_duplicated.index(_time)]
            dict_taken_flag[d_time] = dict_taken_flag[d_time] + _flag
            if dict_taken_tail[d_time]<_tail:
                dict_taken_tail[d_time] =_tail
            continue
        check_duplicated.append(_time)

        # Take the needed data back selection
        if taken_starttime < UTCDateTime(_time[1]) and taken_next_starttime > UTCDateTime(_time[0]):
            # print("TAKEN =================", taken_starttime, _time)
            list_taken_time.append(_time)
            dict_taken_msg_id[_time] = msg_id
            dict_taken_data[_time] = _data
            dict_taken_flag[_time] = _flag
            dict_taken_tail[_time] = _tail
        
        # Check if key_flag is full then delete id
        elif _tail >= hold_condition_check and _flag.sum()>=_flag.shape[0]:
            # print("DELETE =================", _time)
            r.xdel(redis_key, msg_id)
        elif expired_time > UTCDateTime(_time[1]):
            # print("DELETE =================", _time)
            r.xdel(redis_key, msg_id)

    segment_data = []
    if len(list_taken_time):
        # print("MESSAGE =================")
        
        # Check if missing then exit
        _counter = 1
        list_taken_time = sorted(list_taken_time+[tuple(redis_value['time'])])
        for lt,lr in zip(list_taken_time[:-1], list_taken_time[1:]):
            
            # print(lt[0],lt[1],lr[0],lr[1], abs(UTCDateTime(lt[1]) - UTCDateTime(lr[0])))
            
            if abs(UTCDateTime(lt[1]) - UTCDateTime(lr[0])) > 1:
                # Check if after the current time data is unused
                if (_counter * npts) >= window_size and next_starttime == lt[1] :
                    list_taken_time = list_taken_time[:_counter]
                    break
                    
                # print("MISSING =================")
                # Store to redis
                r.xadd(redis_key, {"data": json.dumps(redis_value)})
                return segment_data

            else: 
                if starttime == lr[0]:
                    redis_value['tail'] = min(hold_condition, _counter)
                else:
                    dict_taken_tail[lr] = min(hold_condition, _counter)

            _counter+=1
        
        trim_start = {trace.stats.channel: UTCDateTime(list_taken_time[0][0])}
        trim_end = {trace.stats.channel: UTCDateTime(list_taken_time[-1][-1]) - trace.stats.delta}

        # Get all messages form other channel
        other_redis_key = {}
        list_taken_time_ = {}
        dict_taken_msg_id_ = {}
        dict_taken_data_ = {}
        dict_taken_flag_ = {}
        dict_taken_tail_ = {} 
        # stream = Stream()

        for channel in station_channels:
            if channel != trace.stats.channel:
                list_taken_time_[channel] = []
                dict_taken_msg_id_[channel] = {}
                dict_taken_data_[channel] = {}
                dict_taken_flag_[channel] = {}
                dict_taken_tail_[channel] = {}
                check_duplicated = []
                other_redis_key[channel] = redis_key.replace(trace.stats.channel, channel)
                messages[channel] = r.xrange(other_redis_key[channel], "-", "+")
                for msg_id, fields in messages[channel]:
                    # Extract the MiniSEED data and header from the message
                    header_json = fields[b'data']
                    
                    # Decode the header information
                    header = json.loads(header_json)
                    _time = tuple(header['time'])
                    _data = np.array(header['data'])
                    _flag = np.array(header['flag'])
                    _tail = int(header['tail'])

                    if _time in check_duplicated:
                        r.xdel(other_redis_key[channel], msg_id)
                        d_time = check_duplicated[check_duplicated.index(_time)]
                        dict_taken_flag_[channel][d_time] = dict_taken_flag_[channel][d_time] + _flag
                        if dict_taken_tail_[channel][d_time]<_tail:
                            dict_taken_tail_[channel][d_time] =_tail
                        continue
                    check_duplicated.append(_time)
                    
                    # Take the needed data back selection
                    if list_taken_time[0][0] < UTCDateTime(_time[1]) and list_taken_time[-1][-1] > UTCDateTime(_time[0]):
                        # print("TAKEN =================", taken_starttime, _time)
                        list_taken_time_[channel].append(_time)
                        dict_taken_msg_id_[channel][_time] = msg_id
                        dict_taken_data_[channel][_time] = _data
                        dict_taken_flag_[channel][_time] = _flag
                        dict_taken_tail_[channel][_time] = _tail

                if len(list_taken_time_[channel]):
                    # Check other channels if missing then exit
                    _counter = 1
                    list_taken_time_[channel] = sorted(list_taken_time_[channel])
                    for lt,lr in zip(list_taken_time_[channel][:-1], list_taken_time_[channel][1:]):
                        if abs(UTCDateTime(lt[1]) - UTCDateTime(lr[0])) > 1:
                            return segment_data
                        _counter+=1

                    # Other channel concatenate
                    trim_start[channel] = UTCDateTime(list_taken_time_[channel][0][0])
                    trim_end[channel] = UTCDateTime(list_taken_time_[channel][-1][-1]) - trace.stats.delta
                    
        # FLAG AND DATA PROCESSING
        dict_taken_flag[tuple(redis_value['time'])] = np.array(redis_value['flag'])
        concatenated_flag = np.concatenate([dict_taken_flag[key] for key in list_taken_time])
        dict_taken_data[tuple(redis_value['time'])] = np.array(redis_value['data'])
        concatenated_data = np.concatenate([dict_taken_data[key] for key in list_taken_time])
        
        trim_delta = {}
        trim_npts = []
        
        for channel in trim_start.keys():
            trim_delta[channel] = round(trace.stats.sampling_rate * (max(trim_start.values()) - trim_start[channel]))
            trim_npts.append(round(trace.stats.sampling_rate * (min(trim_end.values()) - (trim_start[channel] + (trim_delta[channel]*trace.stats.delta)))))
        
        trim_npts = min(trim_npts)
        firstbound = []
        waveform = {}
        waveform_flag = {}
        for channel in trim_start.keys():
            if channel != trace.stats.channel:
                waveform[channel] = np.concatenate(
                                        [dict_taken_data_[channel][key] for key in list_taken_time_[channel]]
                                    )[trim_delta[channel]:trim_delta[channel]+trim_npts]
                waveform_flag[channel] = np.concatenate(
                                        [dict_taken_flag_[channel][key] for key in list_taken_time_[channel]]
                                    )[trim_delta[channel]:trim_delta[channel]+trim_npts]                                    
                # print("other:"+channel, len(list_taken_time_[channel]), waveform[channel].shape, max(trim_start.values()), min(trim_end.values()))
            else:
                waveform[channel] = concatenated_data[trim_delta[channel]:trim_delta[channel]+trim_npts]
                waveform_flag[channel] = concatenated_flag[trim_delta[channel]:trim_delta[channel]+trim_npts]
                # print("main:"+channel, len(list_taken_time), waveform[channel].shape, max(trim_start.values()), min(trim_end.values()))
            try:
                firstbound.append(max(np.where(waveform_flag[channel][:-center+1])[0]) - center)
            except:
                pass

        if firstbound:
            trim_npts -= min(firstbound)
            for channel in trim_start.keys():
                trim_delta[channel] += min(firstbound)
                waveform[channel] = waveform[channel][min(firstbound):]
                waveform_flag[channel] = waveform_flag[channel][min(firstbound):]
                # print("CHECK", waveform[channel].shape, waveform_flag[channel].shape, trim_delta[channel], trim_npts)

        if min(trim_npts, waveform[channel].shape[0], waveform_flag[channel].shape[0]) >= window_size:
            # print("PROCESSED =================", tuple(redis_value['time']))
            
            # Getting sliding window
            segment = sliding_window_view(np.moveaxis(np.array([
                            waveform[key] for key in sorted(station_channels)
                        ]), 1, 0), window_size, axis=0)

            # Assign the flag
            for ch in sorted(station_channels):
                waveform_flag[ch][-len(segment)-center+1:-center+1] += np.ones(len(segment), dtype=np.int64)
            
            concatenated_flag[trim_delta[trace.stats.channel]:trim_delta[trace.stats.channel]+trim_npts] = waveform_flag[trace.stats.channel]
            
            # Assign the label
            label = np.zeros(len(waveform[ch]))
            label[-len(segment)-center+1:-center+1] = detect_pick_station(segment, ncheck)
            for idx in np.where(label)[0]:
                timestamp = str(max(trim_start.values()) + (trace.stats.delta * idx))
                segment_data.append({"station":trace.id, "timestamp":timestamp})
            
            # Back to the single channel flag
            i_ = 0
            reshaped_flag = []
            for key in list_taken_time:
                i__ = dict_taken_flag[key].shape[0] + i_
                reshaped_flag.append(concatenated_flag[i_:i__])
                i_ = i__
            reshaped_flag = {k:v for k,v in zip(list_taken_time, reshaped_flag)}

            # Update redis with delete the data and create new data
            list_taken_time.remove(tuple(redis_value['time']))
            
            for taken_key in list_taken_time:
                r.xdel(redis_key, dict_taken_msg_id[taken_key])
                r.xadd(redis_key, {"data": json.dumps({
                    "time": taken_key,
                    "data": dict_taken_data[taken_key].tolist(),
                    "flag": reshaped_flag[taken_key].tolist(),
                    "tail": dict_taken_tail[taken_key],
                })})
                # mess = r.xrevrange(redis_key, max=dict_taken_msg_id[taken_key], 
                #                     min='-', count=4)[1:]
                # for m_i, f_i in mess:
                #     d_time = json.loads(f_i[b'data'])['time']
                #     print(m_i, d_time, taken_key)
                #     if d_time[0]==taken_key[0]: r.xdel(redis_key, m_i)

            # Update current flag
            redis_value['flag']= reshaped_flag[tuple(redis_value['time'])].tolist()
            
            # For other channel
            for channel in list_taken_time_.keys():
                con_flag = np.concatenate([dict_taken_flag_[channel][key] for key in list_taken_time_[channel]])
                con_flag[trim_delta[channel]:trim_delta[channel]+trim_npts] = waveform_flag[channel]
                # Back to the single channel flag
                i_ = 0
                reshaped_flag = []
                for key in list_taken_time_[channel]:
                    i__ = dict_taken_flag_[channel][key].shape[0] + i_
                    reshaped_flag.append(con_flag[i_:i__])
                    i_ = i__
                reshaped_flag = {k:v for k,v in zip(list_taken_time_[channel], reshaped_flag)}

                for taken_key in list_taken_time_[channel]:
                    r.xdel(other_redis_key[channel], dict_taken_msg_id_[channel][taken_key])
                    r.xadd(other_redis_key[channel], {"data": json.dumps({
                        "time": taken_key,
                        "data": dict_taken_data_[channel][taken_key].tolist(),
                        "flag": reshaped_flag[taken_key].tolist(),
                        "tail": dict_taken_tail_[channel][taken_key],
                    })})

    # Store to redis
    r.xadd(redis_key, {"data": json.dumps(redis_value)})

    return segment_data