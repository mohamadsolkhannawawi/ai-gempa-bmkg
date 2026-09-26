import json
from obspy import UTCDateTime

# Function to serialize data to JSON format
def json_serializer(message):
    data = json.loads(message.value.decode('utf-8'))
    # TODO: this is bug from data provider; please remove in the future
    if type(data) == str:
        data = json.loads(data)
    return data

def ts_transform(x):
    return round(UTCDateTime(str(x)).timestamp*1000)

def store_trace_data(trace_id, starttime, endtime, data, r):
    try:
        r.ts().add('aicache_'+trace_id, ts_transform(endtime), ts_transform(starttime), duplicate_policy="LAST")
        r.hset('aicache_'+trace_id+'_data', ts_transform(endtime), json.dumps({'data':data}))
    except Exception as e:
        print(e)
    
def delete_temporary(trace_id, endtime, r, expired=900):
    final = str(endtime-expired)
    try:
        messages = r.ts().range(key='aicache_'+trace_id, 
                                from_time=0,
                                to_time=ts_transform(final))
        
        true_delete = 0
        for i,(end,start) in enumerate(messages):
            true_delete += r.hdel('aicache_'+trace_id+'_data', end)
            
        true_delete_ts = r.ts().delete(key='aicache_'+trace_id, from_time=messages[0][0], to_time=messages[-1][0])
        return [true_delete, true_delete_ts]
    except Exception as e:
        print(e)
