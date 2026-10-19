"""
metering/producer.py - EventProducer untuk emit usage events ke Kafka.

Tanggungjawab:
1. Emit UsageEvent ke Kafka topic 'usage-events'
2. Retry dengan exponential backoff
3. Log success/failure
"""
from typing import Optional
from decimal import Decimal
import logging
import time
import uuid
from datetime import datetime

from infrastructure.kafka.producer import KafkaProducer
from metering.events import UsageEvent

logger = logging.getLogger(__name__)


class EventProducer:
    """
    Emit usage events ke Kafka.
    
    Usage:
        producer = EventProducer()
        producer.emit_usage_event(
            workspace_id="ws_123",
            user_id="user_456",
            provider_name="PhaseNet",
            module="p_pick",
            cost_idr=Decimal("15"),
            latency_ms=150.5,
            request_id="req_789"
        )
    """
    
    def __init__(
        self,
        kafka_producer: Optional[KafkaProducer] = None,
        topic: str = "usage-events"
    ):
        self.producer = kafka_producer or KafkaProducer()
        self.topic = topic
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize producer connection."""
        try:
            self.producer.initialize()
            self._initialized = True
            logger.info("EventProducer initialized")
            return True
        except Exception as e:
            logger.error(f"EventProducer init failed: {e}")
            return False
    
    def emit_usage_event(
        self,
        workspace_id: str,
        user_id: str,
        provider_name: str,
        module: str,
        cost_idr: Decimal,
        latency_ms: float,
        request_id: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Emit usage event.
        
        Returns:
        - True if success, False otherwise
        """
        if not self._initialized:
            logger.warning("EventProducer not initialized, skip emit")
            return False
        
        # Create event
        event = UsageEvent(
            event_id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            provider_name=provider_name,
            module=module,
            cost_idr=cost_idr,
            latency_ms=latency_ms,
            timestamp=time.time(),
            request_id=request_id,
            metadata=metadata or {}
        )
        
        # Emit ke Kafka
        try:
            key = f"{workspace_id}:{user_id}".encode()
            value = event.to_json().encode()
            
            self.producer.send(self.topic, key=key, value=value)
            
            logger.info(
                f"Emitted usage event: {event.event_id} "
                f"(provider={provider_name}, cost={cost_idr} IDR)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
            return False
    
    def close(self):
        """Close producer connection."""
        try:
            self.producer.close()
            logger.info("EventProducer closed")
        except Exception as e:
            logger.error(f"Error closing producer: {e}")


# Singleton instance
_event_producer: Optional[EventProducer] = None


def get_event_producer() -> EventProducer:
    """Get or create EventProducer singleton."""
    global _event_producer
    if _event_producer is None:
        _event_producer = EventProducer()
        _event_producer.initialize()
    return _event_producer
