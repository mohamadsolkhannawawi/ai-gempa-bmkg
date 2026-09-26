
import redis
import time

redis_client = redis.Redis(host="194.195.92.242", port=6380, db=0)

def get_non_expired_historical_messages(channel):
    current_time = int(time.time())
    history_key = f"{channel}_history"
    non_expired_messages = []

    # Fetch all message metadata
    all_messages = redis_client.hgetall(history_key)

    for message_key, exp_timestamp in all_messages.items():
        # Convert bytes to int for comparison
        exp_timestamp = int(exp_timestamp.decode('utf-8'))
        
        if exp_timestamp > current_time:
            # Message has not expired; fetch its content
            message_content = redis_client.get(message_key.decode('utf-8'))
            if message_content:
                non_expired_messages.append(message_content.decode('utf-8'))

    return non_expired_messages

# Example usage
non_expired_messages = get_non_expired_historical_messages('example_channel')
for message in non_expired_messages:
    print(message)
