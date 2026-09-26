import asyncio
import uvicorn

from kafka_module.kafka_consumer import get_kafka_consumer
kafka_consumer = get_kafka_consumer()
