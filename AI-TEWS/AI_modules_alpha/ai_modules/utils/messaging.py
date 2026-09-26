import json

# Function to serialize data to JSON format
def json_serializer(message):
    return json.loads(message.value.decode('utf-8'))
