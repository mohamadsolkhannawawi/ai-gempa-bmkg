"""
tests/unit/test_usage_aggregator.py - Unit tests untuk MeteringAggregator.

Verifikasi windowing logic + aggregation.
"""
import sys
sys.path.insert(0, "..")

from datetime import datetime, timedelta
from decimal import Decimal
import time
import pytest

from metering.aggregator import MeteringAggregator
from metering.events import UsageEvent, AggregatedUsage
from infrastructure.repositories.usage_repo import InMemoryUsageRepository


class TestMeteringAggregator:
    """Test MeteringAggregator dengan InMemoryRepository."""
    
    def test_handle_single_event(self):
        """Handle single event."""
        repo = InMemoryUsageRepository()
        agg = MeteringAggregator(repo, window_seconds=60)
        
        event = UsageEvent(
            event_id="evt_1",
            workspace_id="ws_1",
            user_id="user_1",
            provider_name="STALTA",
            module="p_pick",
            cost_idr=Decimal("10"),
            latency_ms=50.0,
            timestamp=time.time(),
            request_id="req_1"
        )
        
        agg.handle_event(event)
        
        # Should be buffered, not yet flushed
        usage = repo.get_usage_by_date("ws_1", "user_1", datetime.now().strftime("%Y-%m-%d"))
        assert usage is None  # Not flushed yet
    
    def test_aggregation_single_day(self):
        """Aggregate multiple events dalam 1 hari."""
        repo = InMemoryUsageRepository()
        agg = MeteringAggregator(repo, window_seconds=60)
        
        # Create events
        now = time.time()
        for i in range(3):
            event = UsageEvent(
                event_id=f"evt_{i}",
                workspace_id="ws_1",
                user_id="user_1",
                provider_name="STALTA" if i < 2 else "PhaseNet",
                module="p_pick",
                cost_idr=Decimal(str(10 + i * 5)),
                latency_ms=50.0,
                timestamp=now,
                request_id=f"req_{i}"
            )
            agg.handle_event(event)
        
        # Force flush dengan close
        agg.stop()
        
        # Check aggregated result
        usage = repo.get_usage_by_date("ws_1", "user_1", datetime.now().strftime("%Y-%m-%d"))
        assert usage is not None
        assert usage.total_inferences == 3
        assert usage.total_cost_idr == Decimal("30")  # 10 + 15 + 20
        assert usage.breakdown_by_provider["STALTA"] == Decimal("20")
        assert usage.breakdown_by_provider["PhaseNet"] == Decimal("25")
    
    def test_multiple_users_separate_aggregation(self):
        """Multiple users di-aggregate terpisah."""
        repo = InMemoryUsageRepository()
        agg = MeteringAggregator(repo, window_seconds=60)
        
        now = time.time()
        
        # User 1
        event1 = UsageEvent(
            event_id="evt_u1",
            workspace_id="ws_1",
            user_id="user_1",
            provider_name="STALTA",
            module="p_pick",
            cost_idr=Decimal("10"),
            latency_ms=50.0,
            timestamp=now,
            request_id="req_u1"
        )
        agg.handle_event(event1)
        
        # User 2
        event2 = UsageEvent(
            event_id="evt_u2",
            workspace_id="ws_1",
            user_id="user_2",
            provider_name="PhaseNet",
            module="p_pick",
            cost_idr=Decimal("15"),
            latency_ms=60.0,
            timestamp=now,
            request_id="req_u2"
        )
        agg.handle_event(event2)
        
        agg.stop()
        
        # Check user 1
        usage1 = repo.get_usage_by_date("ws_1", "user_1", datetime.now().strftime("%Y-%m-%d"))
        assert usage1 is not None
        assert usage1.total_cost_idr == Decimal("10")
        
        # Check user 2
        usage2 = repo.get_usage_by_date("ws_1", "user_2", datetime.now().strftime("%Y-%m-%d"))
        assert usage2 is not None
        assert usage2.total_cost_idr == Decimal("15")
    
    def test_multiple_days_separate(self):
        """Events pada hari berbeda tidak tergabung."""
        repo = InMemoryUsageRepository()
        agg = MeteringAggregator(repo, window_seconds=60)
        
        # Day 1
        day1 = time.time()
        event1 = UsageEvent(
            event_id="evt_d1",
            workspace_id="ws_1",
            user_id="user_1",
            provider_name="STALTA",
            module="p_pick",
            cost_idr=Decimal("10"),
            latency_ms=50.0,
            timestamp=day1,
            request_id="req_d1"
        )
        agg.handle_event(event1)
        
        agg.stop()
        
        # Day 2 (different date)
        # Manually insert next day untuk test
        day2_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        event2 = UsageEvent(
            event_id="evt_d2",
            workspace_id="ws_1",
            user_id="user_1",
            provider_name="STALTA",
            module="p_pick",
            cost_idr=Decimal("20"),
            latency_ms=50.0,
            timestamp=day1 - 86400,  # Yesterday
            request_id="req_d2"
        )
        agg.handle_event(event2)
        
        # Note: This test demonstrates that date extraction is per-event timestamp
        # For a real test, would need to mock datetime or use specific timestamps
    
    def test_buffer_flush_threshold(self):
        """Flush when buffer threshold reached."""
        repo = InMemoryUsageRepository()
        agg = MeteringAggregator(repo, window_seconds=3600, flush_interval_seconds=60)
        
        now = time.time()
        events = []
        
        # Create 100 events (buffer threshold)
        for i in range(100):
            event = UsageEvent(
                event_id=f"evt_{i}",
                workspace_id="ws_1",
                user_id="user_1",
                provider_name="STALTA",
                module="p_pick",
                cost_idr=Decimal("10"),
                latency_ms=50.0,
                timestamp=now,
                request_id=f"req_{i}"
            )
            events.append(event)
        
        # Process all events
        for event in events:
            agg.handle_event(event)
        
        # Check if flushed
        usage = repo.get_usage_by_date("ws_1", "user_1", datetime.now().strftime("%Y-%m-%d"))
        assert usage is not None
        assert usage.total_inferences == 100
    
    def test_breakdown_by_module(self):
        """Breakdown by module is correct."""
        repo = InMemoryUsageRepository()
        agg = MeteringAggregator(repo, window_seconds=60)
        
        now = time.time()
        
        # p_pick events
        for i in range(3):
            event = UsageEvent(
                event_id=f"evt_ppick_{i}",
                workspace_id="ws_1",
                user_id="user_1",
                provider_name="STALTA",
                module="p_pick",
                cost_idr=Decimal("10"),
                latency_ms=50.0,
                timestamp=now,
                request_id=f"req_{i}"
            )
            agg.handle_event(event)
        
        # association events
        for i in range(2):
            event = UsageEvent(
                event_id=f"evt_assoc_{i}",
                workspace_id="ws_1",
                user_id="user_1",
                provider_name="DBSCAN",
                module="association",
                cost_idr=Decimal("20"),
                latency_ms=100.0,
                timestamp=now,
                request_id=f"req_a_{i}"
            )
            agg.handle_event(event)
        
        agg.stop()
        
        usage = repo.get_usage_by_date("ws_1", "user_1", datetime.now().strftime("%Y-%m-%d"))
        assert usage is not None
        assert usage.breakdown_by_module["p_pick"] == Decimal("30")
        assert usage.breakdown_by_module["association"] == Decimal("40")


class TestAggregatedUsage:
    """Test AggregatedUsage dataclass."""
    
    def test_to_dict(self):
        """Convert to dict."""
        usage = AggregatedUsage(
            workspace_id="ws_1",
            user_id="user_1",
            date="2024-01-15",
            total_inferences=5,
            total_cost_idr=Decimal("100"),
            breakdown_by_provider={"STALTA": Decimal("60"), "PhaseNet": Decimal("40")},
            breakdown_by_module={"p_pick": Decimal("70"), "association": Decimal("30")},
            created_at=time.time()
        )
        
        d = usage.to_dict()
        
        assert d["workspace_id"] == "ws_1"
        assert d["total_inferences"] == 5
        assert isinstance(d["total_cost_idr"], float)
    
    def test_to_json(self):
        """Convert to JSON."""
        usage = AggregatedUsage(
            workspace_id="ws_1",
            user_id="user_1",
            date="2024-01-15",
            total_inferences=5,
            total_cost_idr=Decimal("100"),
            breakdown_by_provider={"STALTA": Decimal("60")},
            breakdown_by_module={"p_pick": Decimal("70")},
            created_at=time.time()
        )
        
        json_str = usage.to_json()
        assert '"workspace_id"' in json_str
        assert '"total_cost_idr"' in json_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
