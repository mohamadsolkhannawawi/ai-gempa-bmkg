
import redis, os

from dotenv import load_dotenv
import json
load_dotenv("./.env")

redis_host = os.getenv('redis_host')
redis_host = "194.195.92.242"
redis_port = os.getenv('redis_port')
# Connect to Redis
redis_client = redis.Redis(host=redis_host, port=int(redis_port), db=0)
pubsub = redis_client.pubsub()

# Retrieve historical messages
channel = 'GE.JAGI..BHE'
messages = redis_client.lrange(f'{channel}_history', 0, -1)
for message in messages:
    print(f"Historical message: {message.decode('utf-8')}")
    print(a)

# Subscribe to the channel
pubsub.subscribe(channel)

print("Subscribed to 'my_channel', listening for new messages...")
while True:
    message = pubsub.get_message()
    if message and message['type'] == 'message':
        data = json.loads(message['data'].decode('utf-8')) 
        print(data)
        print(data["station"])
        # print(f"New message: {message['data'].decode('utf-8')}")
