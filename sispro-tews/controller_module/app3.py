import redis
import time

redis_client = redis.Redis(host="194.195.92.242", port=6380, db=0)

# Assuming redis_client is initialized as shown in your snippet
# redis_client = redis.Redis(host='194.195.92.242', port=6380, db=0)

def publish_message_with_metadata(channel, message, ttl_seconds=20):
    timestamp = int(time.time())
    message_key = f"{channel}_message_{timestamp}"
    expiration_timestamp = timestamp + ttl_seconds

    # Store the message with TTL
    redis_client.setex(message_key, ttl_seconds, message)

    # Check if the history key exists and is of the correct type
    history_key = f"{channel}_history"
    # if redis_client.exists(history_key):
    #     if redis_client.type(history_key).decode("utf-8") != "hash":
    #         print(f"Error: {history_key} exists but is not a hash. Consider using a different key or removing the existing one.")
    #         return
    
    # Store message metadata, including its expiration timestamp, using HSET
    redis_client.hset(history_key, message_key, expiration_timestamp)

    # Publish the message key to the channel
    redis_client.publish(channel, message_key)

try:
    publish_message_with_metadata('example_channel', 'Hello Redis!', 20)
except redis.exceptions.ResponseError as e:
    print(f"Redis error: {e}")
