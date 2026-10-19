"""
metering/consumer.py - MeteringConsumer untuk consume usage events dari Kafka.

Tanggungjawab:
1. Consume UsageEvent dari Kafka topic 'usage-events'
2. Parse events
3. Forward ke MeteringAggregator
4. Commit offsets
"""
from typing import Optional, Callable
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from infrastructure.kafka.consumer import KafkaConsumer
from metering.events import UsageEvent

logger = logging.getLogger(__name__)


class MeteringConsumer:
    """
    Consume usage events dari Kafka.
    
    Usage:
        consumer = MeteringConsumer()
        consumer.set_handler(aggregator.handle_event)
        consumer.start()  # Blocking
    """
    
    def __init__(
        self,
        kafka_consumer: Optional[KafkaConsumer] = None,
        topic: str = "usage-events",
        group_id: str = "metering-consumer",
        num_workers: int = 4
    ):
        self.consumer = kafka_consumer or KafkaConsumer(group_id=group_id)
        self.topic = topic
        self.group_id = group_id
        self.num_workers = num_workers
        self._handler: Optional[Callable[[UsageEvent], None]] = None
        self._initialized = False
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=num_workers)
    
    def initialize(self) -> bool:
        """Initialize consumer connection."""
        try:
            self.consumer.initialize()
            self.consumer.subscribe([self.topic])
            self._initialized = True
            logger.info(f"MeteringConsumer initialized (group={self.group_id})")
            return True
        except Exception as e:
            logger.error(f"MeteringConsumer init failed: {e}")
            return False
    
    def set_handler(self, handler: Callable[[UsageEvent], None]):
        """Set event handler."""
        self._handler = handler
        logger.info("Event handler set")
    
    def start(self):
        """
        Start consuming (blocking).
        
        Subscribe to topic, poll events, handle them.
        Call close() dari another thread to stop.
        """
        if not self._initialized:
            logger.error("MeteringConsumer not initialized")
            return
        
        if not self._handler:
            logger.error("No handler set")
            return
        
        self._running = True
        logger.info("MeteringConsumer started")
        
        try:
            while self._running:
                # Poll events (timeout 1s)
                messages = self.consumer.poll(timeout_ms=1000)
                
                if not messages:
                    continue
                
                # Process each message
                for msg in messages:
                    try:
                        # Parse event
                        event = UsageEvent.from_json(msg["value"].decode())
                        
                        # Handle via executor (parallel workers)
                        self._executor.submit(self._handle_event_safe, event)
                        
                        # Commit offset
                        self.consumer.commit()
                        
                    except Exception as e:
                        logger.error(f"Failed to process message: {e}")
                        # Continue despite error
        
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt, stopping consumer")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self.close()
    
    def _handle_event_safe(self, event: UsageEvent):
        """Handle event safely (error handling)."""
        try:
            if self._handler:
                self._handler(event)
        except Exception as e:
            logger.error(f"Handler error for event {event.event_id}: {e}")
    
    def close(self):
        """Stop consumer."""
        self._running = False
        try:
            self._executor.shutdown(wait=True)
            self.consumer.close()
            logger.info("MeteringConsumer closed")
        except Exception as e:
            logger.error(f"Error closing consumer: {e}")
    
    def health_check(self) -> tuple[bool, str]:
        """Check consumer health."""
        try:
            # Check if subscribed to topics
            subscribed = self.consumer.subscribed_topics()
            if not subscribed:
                return False, "Not subscribed to any topic"
            
            return True, f"Subscribed to {len(subscribed)} topics"
        except Exception as e:
            return False, str(e)
