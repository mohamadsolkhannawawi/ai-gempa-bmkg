import redis, os,time

from dotenv import load_dotenv

load_dotenv("./.env")

redis_host = os.getenv('redis_host')
redis_port = os.getenv('redis_port')
# Connect to Redis
redis_client = redis.Redis(host=redis_host, port=int(redis_port), db=0)

def publish_redis_message(channel, message):
    # Use a consistent key for storing messages
    list_key = f"{channel}_history"

    # Push the message to the list
    redis_client.rpush(list_key, message)
    
    # Set or reset the expiry time to 20 seconds
    redis_client.expire(list_key, 1800)
    
    # Publish the message to the channel
    redis_client.publish(channel, message)

def store_redis_message(channel, message):
    # Use a consistent key for storing messages
    list_key = f"{channel}"
    
    # Push the message to the list
    redis_client.rpush(list_key, message)
    
def publish_redis_message_general(channel, message):
    redis_client.publish(channel, message)
