import os, glob, redis
from tqdm import tqdm
from obspy import UTCDateTime, read
from seedlink_player_utils import STARTTIME, ENDTIME

from dotenv import load_dotenv

load_dotenv("./.env")

redis_host = os.getenv('redis_host')
redis_port = os.getenv('redis_port')

# Connect to Redis
r = redis.Redis(host=redis_host, port=int(redis_port), db=0)

print("Processing...", STARTTIME, "to", ENDTIME)

# Get all data in this range
T = UTCDateTime(STARTTIME)

root = '../'
streams = [s.replace('\\','/').replace(root,'') for s in tqdm(sorted(glob.glob(root+f'archive_local/*/*/*/*/*.{T.strftime("%Y.%j")}')))]
print(len(streams))

for i,st in tqdm(enumerate(streams)):
    tr = read(root+st).merge()[0]

    # Get all messages from the Redis stream
    messages = r.xrange("mseed_stream_"+tr.id, "-", "+")
    messages2 = r.xrange("mseed_header_"+tr.id, "-", "+")

    # Iterate over each message in the stream
    for (msg_id,fields), (msg_id2,fields2) in zip(messages, messages2):
        # Extract the MiniSEED data and header from the message
        
        # Delete the message from the stream
        r.xdel("mseed_stream_"+tr.id, msg_id)
        r.xdel("mseed_header_"+tr.id, msg_id2)

print("Success!")