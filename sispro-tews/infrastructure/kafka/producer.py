"""
infrastructure/kafka/producer.py - Kafka producer abstraction (repository pattern).

Problem: KafkaProducer hard-coded, sulit test.
Solution: Interface + mock implementation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional
import json


class KafkaProducerRepository(ABC):
    """Interface untuk Kafka producer (testable)."""
    
    @abstractmethod
    def send(self, topic: str, message: dict, key: Optional[str] = None, 
             headers: Optional[Dict[str, str]] = None):
        """Send message ke topic."""
        pass
    
    @abstractmethod
    def flush(self):
        """Flush pending messages (block until sent)."""
        pass
    
    @abstractmethod
    def close(self):
        """Close producer connection."""
        pass


class RealKafkaProducerRepository(KafkaProducerRepository):
    """Production Kafka producer (kafka-python)."""
    
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer = None
    
    def _ensure_producer(self):
        if not self._producer:
            from kafka import KafkaProducer
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode(),
                key_serializer=lambda k: k.encode() if k else None
            )
    
    def send(self, topic: str, message: dict, key: Optional[str] = None,
             headers: Optional[Dict[str, str]] = None):
        self._ensure_producer()
        headers_list = [(k, v.encode()) for k, v in (headers or {}).items()]
        self._producer.send(topic, value=message, key=key, headers=headers_list)
    
    def flush(self):
        if self._producer:
            self._producer.flush()
    
    def close(self):
        if self._producer:
            self._producer.close()


class MockKafkaProducerRepository(KafkaProducerRepository):
    """Mock producer untuk unit test."""
    
    def __init__(self):
        self.sent_messages = []  # [(topic, message, key, headers)]
    
    def send(self, topic: str, message: dict, key: Optional[str] = None,
             headers: Optional[Dict[str, str]] = None):
        self.sent_messages.append((topic, message, key, headers))
    
    def flush(self):
        pass
    
    def close(self):
        pass


if __name__ == "__main__":
    # Example: mock producer
    mock = MockKafkaProducerRepository()
    mock.send("test.waveform", {"station": "BMKG", "samples": [0.1, 0.2]}, key="ws1")
    mock.send("test.pick", {"phase": "P", "time": "2026-10-19T12:33:08Z"})
    
    print(f"Sent {len(mock.sent_messages)} messages:")
    for topic, msg, key, _ in mock.sent_messages:
        print(f"  {topic} (key={key}): {msg}")
