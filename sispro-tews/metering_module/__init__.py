"""
metering_module/__init__.py - MeteringModule orchestrator.

Koordinator end-to-end metering:
1. EventProducer: emit usage events ke Kafka
2. MeteringConsumer: consume events
3. MeteringAggregator: aggregate + save ke MongoDB

One entry point untuk semua metering tasks.
"""
from typing import Optional, Dict, Any
from decimal import Decimal
import logging
import threading
import time

from metering.producer import get_event_producer
from metering.consumer import MeteringConsumer
from metering.aggregator import MeteringAggregator
from infrastructure.repositories.usage_repo import UsageRepository

logger = logging.getLogger(__name__)


class MeteringModule:
    """
    Full metering orchestrator.
    
    Usage:
        module = MeteringModule(repository)
        module.start()  # Start consumer + aggregator
        module.emit_usage(...)  # Emit usage event
        module.stop()  # Shutdown gracefully
    """
    
    def __init__(
        self,
        repository: UsageRepository,
        window_seconds: int = 300,
        flush_interval_seconds: int = 60,
        kafka_consumer_group: str = "metering-module"
    ):
        # Repository
        self.repository = repository
        
        # Producer (singleton)
        self.producer = get_event_producer()
        
        # Aggregator
        self.aggregator = MeteringAggregator(
            repository=repository,
            window_seconds=window_seconds,
            flush_interval_seconds=flush_interval_seconds
        )
        
        # Consumer
        self.consumer = MeteringConsumer(
            group_id=kafka_consumer_group,
            num_workers=4
        )
        
        # Set aggregator sebagai consumer handler
        self.consumer.set_handler(self.aggregator.handle_event)
        
        # State
        self._running = False
        self._consumer_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start consumer thread + aggregator."""
        if self._running:
            logger.warning("MeteringModule already running")
            return
        
        # Initialize producer
        self.producer.initialize()
        
        # Initialize consumer
        if not self.consumer.initialize():
            logger.error("Failed to initialize consumer")
            return
        
        # Start aggregator flush loop
        self.aggregator.start()
        
        # Start consumer dalam thread
        self._consumer_thread = threading.Thread(
            target=self._run_consumer,
            daemon=True,
            name="metering-consumer-thread"
        )
        self._consumer_thread.start()
        
        self._running = True
        logger.info("MeteringModule started")
    
    def _run_consumer(self):
        """Run consumer (blocking)."""
        try:
            self.consumer.start()
        except Exception as e:
            logger.error(f"Consumer thread failed: {e}")
    
    def emit_usage(
        self,
        workspace_id: str,
        user_id: str,
        provider_name: str,
        module: str,
        cost_idr: Decimal,
        latency_ms: float,
        request_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Emit usage event.
        
        Shortcut ke producer.emit_usage_event.
        """
        if not self._running:
            logger.warning("MeteringModule not started, emit skipped")
            return False
        
        return self.producer.emit_usage_event(
            workspace_id=workspace_id,
            user_id=user_id,
            provider_name=provider_name,
            module=module,
            cost_idr=cost_idr,
            latency_ms=latency_ms,
            request_id=request_id,
            metadata=metadata
        )
    
    def stop(self):
        """Stop consumer, flush aggregator, close producer."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop consumer
        if self.consumer:
            self.consumer.close()
        
        # Stop aggregator (flush remaining)
        if self.aggregator:
            self.aggregator.stop()
        
        # Close producer
        if self.producer:
            self.producer.close()
        
        # Wait for consumer thread
        if self._consumer_thread:
            self._consumer_thread.join(timeout=5)
        
        logger.info("MeteringModule stopped")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check.
        
        Returns:
        - producer: bool
        - aggregator: buffer stats
        - consumer: health status
        """
        # Producer health
        producer_ok = self.producer is not None
        
        # Aggregator stats
        aggregator_stats = self.aggregator.get_buffer_stats() if self.aggregator else {}
        
        # Consumer health
        consumer_ok, consumer_msg = self.consumer.health_check() if self.consumer else (False, "No consumer")
        
        return {
            "producer": producer_ok,
            "aggregator": aggregator_stats,
            "consumer": consumer_ok,
            "consumer_message": consumer_msg,
            "running": self._running
        }
    
    def get_usage_by_date(
        self,
        workspace_id: str,
        user_id: str,
        date_str: str
    ):
        """
        Query usage for specific date.
        
        Delegates ke repository.
        """
        return self.repository.get_usage_by_date(
            workspace_id=workspace_id,
            user_id=user_id,
            date_str=date_str
        )
    
    def get_usage_by_range(
        self,
        workspace_id: str,
        user_id: str,
        start_date: str,
        end_date: str
    ):
        """
        Query usage dalam date range.
        
        Delegates ke repository.
        """
        return self.repository.get_usage_by_range(
            workspace_id=workspace_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_workspace_total(
        self,
        workspace_id: str,
        start_date: str,
        end_date: str
    ):
        """
        Get total cost untuk workspace.
        
        Delegates ke repository.
        """
        return self.repository.get_workspace_total(
            workspace_id=workspace_id,
            start_date=start_date,
            end_date=end_date
        )


# Singleton instance
_metering_module: Optional[MeteringModule] = None


def get_metering_module() -> MeteringModule:
    """
    Get or create MeteringModule singleton.
    
    Note: Must call .start() sebelum digunakan.
    """
    global _metering_module
    if _metering_module is None:
        # In-memory repository untuk fallback
        from infrastructure.repositories.usage_repo import InMemoryUsageRepository
        _metering_module = MeteringModule(
            repository=InMemoryUsageRepository()
        )
    return _metering_module


def start_metering_module():
    """Start singleton module."""
    module = get_metering_module()
    module.start()
    return module


def stop_metering_module():
    """Stop singleton module."""
    global _metering_module
    if _metering_module:
        _metering_module.stop()
        _metering_module = None
