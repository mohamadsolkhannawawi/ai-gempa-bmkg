"""
metering/aggregator.py - MeteringAggregator dengan windowing + flush.

Tanggungjawab:
1. Buffer UsageEvent dalam window (5 menit)
2. Aggregasi per (workspace_id, user_id, date)
3. Flush ke UsageRepository ketika:
   - Window penuh
   - Timeout
   - Shutdown
4. Track breakdown by provider dan module
"""
from typing import Dict, Tuple, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import threading
import time
from collections import defaultdict

from metering.events import UsageEvent, AggregatedUsage
from infrastructure.repositories.usage_repo import UsageRepository

logger = logging.getLogger(__name__)


class MeteringAggregator:
    """
    Aggregate usage events dalam sliding window.
    
    Architecture:
    - Buffer: Dict[key, list[UsageEvent]] where key = (workspace_id, user_id, date)
    - Window: 5 menit (configurable)
    - Flush: periodic timer + on-demand
    - Storage: UsageRepository
    
    Usage:
        agg = MeteringAggregator(repo)
        agg.start()  # Start flush timer
        agg.handle_event(event)  # Handle incoming event
    """
    
    def __init__(
        self,
        repository: UsageRepository,
        window_seconds: int = 300,  # 5 menit
        flush_interval_seconds: int = 60  # Check every 1 menit
    ):
        self.repo = repository
        self.window_seconds = window_seconds
        self.flush_interval_seconds = flush_interval_seconds
        
        # Buffer: Dict[key, list[events]]
        self._buffer: Dict[Tuple[str, str, str], list[UsageEvent]] = defaultdict(list)
        self._buffer_lock = threading.Lock()
        
        # Windowing: Dict[key, timestamp]
        self._window_start: Dict[Tuple[str, str, str], float] = {}
        
        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start flush timer thread."""
        if self._running:
            logger.warning("Aggregator already running")
            return
        
        self._running = True
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            daemon=True,
            name="metering-aggregator-flush"
        )
        self._flush_thread.start()
        logger.info(f"MeteringAggregator started (window={self.window_seconds}s)")
    
    def handle_event(self, event: UsageEvent):
        """
        Handle incoming usage event.
        
        Aggregate ke buffer, flush jika window penuh.
        """
        # Extract key
        event_date = datetime.fromtimestamp(event.timestamp).strftime("%Y-%m-%d")
        key = (event.workspace_id, event.user_id, event_date)
        
        with self._buffer_lock:
            # Add event ke buffer
            self._buffer[key].append(event)
            
            # Initialize window jika belum
            if key not in self._window_start:
                self._window_start[key] = time.time()
            
            # Check apakah window penuh (arbitrary threshold: 100 events)
            if len(self._buffer[key]) >= 100:
                logger.info(f"Buffer full for {key}, flushing")
                self._flush_key(key)
    
    def _flush_loop(self):
        """
        Flush timer loop (runs every flush_interval_seconds).
        
        Check semua windows, flush yang expired.
        """
        while self._running:
            try:
                time.sleep(self.flush_interval_seconds)
                self._check_and_flush_expired()
            except Exception as e:
                logger.error(f"Flush loop error: {e}")
    
    def _check_and_flush_expired(self):
        """Check windows, flush expired ones."""
        now = time.time()
        keys_to_flush = []
        
        with self._buffer_lock:
            for key, window_start in self._window_start.items():
                elapsed = now - window_start
                
                # Flush jika:
                # 1. Window expired (window_seconds)
                # 2. Buffer not empty
                if elapsed >= self.window_seconds and len(self._buffer[key]) > 0:
                    keys_to_flush.append(key)
        
        # Flush expired keys
        for key in keys_to_flush:
            with self._buffer_lock:
                self._flush_key(key)
    
    def _flush_key(self, key: Tuple[str, str, str]):
        """
        Flush single key (aggregate + save).
        
        Args:
        - key: (workspace_id, user_id, date)
        """
        if key not in self._buffer or len(self._buffer[key]) == 0:
            return
        
        events = self._buffer[key]
        workspace_id, user_id, date_str = key
        
        # Aggregate events
        total_inferences = len(events)
        total_cost = Decimal("0")
        breakdown_by_provider: Dict[str, Decimal] = defaultdict(Decimal)
        breakdown_by_module: Dict[str, Decimal] = defaultdict(Decimal)
        
        for event in events:
            total_cost += event.cost_idr
            breakdown_by_provider[event.provider_name] += event.cost_idr
            breakdown_by_module[event.module] += event.cost_idr
        
        # Create aggregated usage
        agg = AggregatedUsage(
            workspace_id=workspace_id,
            user_id=user_id,
            date=date_str,
            total_inferences=total_inferences,
            total_cost_idr=total_cost,
            breakdown_by_provider=dict(breakdown_by_provider),
            breakdown_by_module=dict(breakdown_by_module),
            created_at=time.time()
        )
        
        # Save ke repository
        try:
            self.repo.save_aggregated_usage(agg)
            logger.info(
                f"Flushed {total_inferences} events for {key} "
                f"(cost: {total_cost} IDR)"
            )
        except Exception as e:
            logger.error(f"Failed to save aggregated usage: {e}")
            return
        
        # Clear buffer + window
        del self._buffer[key]
        del self._window_start[key]
    
    def flush_all(self) -> int:
        """
        Flush all buffers (call on shutdown).
        
        Returns:
        - Number of keys flushed
        """
        logger.info("Flushing all buffers")
        
        with self._buffer_lock:
            keys_to_flush = list(self._buffer.keys())
            for key in keys_to_flush:
                self._flush_key(key)
        
        return len(keys_to_flush)
    
    def stop(self):
        """Stop aggregator + flush remaining."""
        if not self._running:
            return
        
        self._running = False
        
        # Flush all remaining
        num_flushed = self.flush_all()
        logger.info(f"Aggregator stopped ({num_flushed} buffers flushed)")
        
        # Wait for flush thread
        if self._flush_thread:
            self._flush_thread.join(timeout=5)
    
    def get_buffer_stats(self) -> Dict[str, int]:
        """Get current buffer stats."""
        with self._buffer_lock:
            total_events = sum(len(events) for events in self._buffer.values())
            total_keys = len(self._buffer)
        
        return {
            "total_keys": total_keys,
            "total_events": total_events
        }
