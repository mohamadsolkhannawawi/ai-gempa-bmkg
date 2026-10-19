"""
infrastructure/kafka/consumer.py - Kafka consumer abstraction (repository pattern).

Problem: KafkaConsumer hard-coded di app layer, sulit test + sulit swap.
Solution: Interface + implementation separation, dependency injection.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import json


@dataclass
class Message:
    """Kafka message wrapper."""
    topic: str
    partition: int
    offset: int
    key: Optional[str]
    value: dict              # parsed JSON
    timestamp: int           # ms since epoch
    headers: Dict[str, str]
    
    @staticmethod
    def from_kafka_record(record) -> Message:
        """Parse kafka-python ConsumerRecord."""
        return Message(
            topic=record.topic,
            partition=record.partition,
            offset=record.offset,
            key=record.key.decode() if record.key else None,
            value=json.loads(record.value.decode()),
            timestamp=record.timestamp,
            headers={k: v.decode() for k, v in (record.headers or [])}
        )


class KafkaConsumerRepository(ABC):
    """Interface untuk Kafka consumer (testable)."""
    
    @abstractmethod
    def subscribe(self, topics: List[str], group_id: str):
        """Subscribe ke topics dengan consumer group."""
        pass
    
    @abstractmethod
    def poll(self, timeout_ms: int = 1000) -> List[Message]:
        """Poll messages, return list."""
        pass
    
    @abstractmethod
    def commit(self):
        """Commit offsets (manual commit mode)."""
        pass
    
    @abstractmethod
    def seek_to_beginning(self, topic: str, partition: int):
        """Seek offset ke awal (replay)."""
        pass
    
    @abstractmethod
    def seek_to_end(self, topic: str, partition: int):
        """Seek offset ke akhir (skip old messages)."""
        pass
    
    @abstractmethod
    def close(self):
        """Close consumer connection."""
        pass


class RealKafkaConsumerRepository(KafkaConsumerRepository):
    """Production Kafka consumer (kafka-python library)."""
    
    def __init__(self, bootstrap_servers: str, 
                 enable_auto_commit: bool = False,
                 auto_offset_reset: str = "latest"):
        """
        Args:
            bootstrap_servers: "localhost:9092" or "kafka:9092"
            enable_auto_commit: False = manual commit (at-least-once semantics)
            auto_offset_reset: "earliest" | "latest"
        """
        self.bootstrap_servers = bootstrap_servers
        self.enable_auto_commit = enable_auto_commit
        self.auto_offset_reset = auto_offset_reset
        self._consumer = None
    
    def subscribe(self, topics: List[str], group_id: str):
        from kafka import KafkaConsumer  # lazy import
        self._consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=self.enable_auto_commit,
            auto_offset_reset=self.auto_offset_reset,
            value_deserializer=lambda v: v  # raw bytes, decode manual
        )
    
    def poll(self, timeout_ms: int = 1000) -> List[Message]:
        if not self._consumer:
            raise RuntimeError("consumer not subscribed")
        
        records = self._consumer.poll(timeout_ms=timeout_ms, max_records=100)
        messages = []
        for topic_partition, batch in records.items():
            for record in batch:
                messages.append(Message.from_kafka_record(record))
        return messages
    
    def commit(self):
        if self._consumer:
            self._consumer.commit()
    
    def seek_to_beginning(self, topic: str, partition: int):
        from kafka import TopicPartition
        tp = TopicPartition(topic, partition)
        self._consumer.seek_to_beginning(tp)
    
    def seek_to_end(self, topic: str, partition: int):
        from kafka import TopicPartition
        tp = TopicPartition(topic, partition)
        self._consumer.seek_to_end(tp)
    
    def close(self):
        if self._consumer:
            self._consumer.close()


class MockKafkaConsumerRepository(KafkaConsumerRepository):
    """Mock consumer untuk unit test (no network)."""
    
    def __init__(self):
        self.subscribed_topics = []
        self.group_id = ""
        self.messages_queue = []  # pre-populate di test
        self.committed = False
    
    def subscribe(self, topics: List[str], group_id: str):
        self.subscribed_topics = topics
        self.group_id = group_id
    
    def poll(self, timeout_ms: int = 1000) -> List[Message]:
        # Return queued messages (injected by test)
        if self.messages_queue:
            batch = self.messages_queue[:10]
            self.messages_queue = self.messages_queue[10:]
            return batch
        return []
    
    def commit(self):
        self.committed = True
    
    def seek_to_beginning(self, topic: str, partition: int):
        pass  # no-op
    
    def seek_to_end(self, topic: str, partition: int):
        pass
    
    def close(self):
        pass


class ConsumerWorker:
    """Worker loop untuk consume messages dengan callback handler."""
    
    def __init__(self, consumer: KafkaConsumerRepository, 
                 handler: Callable[[Message], None]):
        """
        Args:
            consumer: KafkaConsumerRepository instance
            handler: callback(message) untuk process 1 message
        """
        self.consumer = consumer
        self.handler = handler
        self._running = False
    
    def start(self, topics: List[str], group_id: str):
        """Start consuming loop."""
        self.consumer.subscribe(topics, group_id)
        self._running = True
        
        while self._running:
            messages = self.consumer.poll(timeout_ms=1000)
            for msg in messages:
                try:
                    self.handler(msg)
                except Exception as e:
                    # ponytail: log error, continue (no retry logic, dead letter queue later)
                    print(f"ERROR processing message {msg.topic}:{msg.offset} - {e}")
            
            # Manual commit after batch processed
            if messages:
                self.consumer.commit()
    
    def stop(self):
        """Stop consuming loop."""
        self._running = False
        self.consumer.close()


if __name__ == "__main__":
    # Example: mock consumer
    mock = MockKafkaConsumerRepository()
    mock.messages_queue = [
        Message("test.waveform", 0, 1, None, {"station": "BMKG"}, 1697000000, {}),
        Message("test.pick", 0, 2, None, {"phase": "P"}, 1697000001, {}),
    ]
    mock.subscribe(["test.waveform", "test.pick"], "test_group")
    
    batch = mock.poll()
    print(f"Polled {len(batch)} messages:")
    for m in batch:
        print(f"  {m.topic}:{m.offset} -> {m.value}")
