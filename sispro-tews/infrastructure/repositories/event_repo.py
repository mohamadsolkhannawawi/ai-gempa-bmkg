"""
infrastructure/repositories/event_repo.py - Event repository interface + MongoDB implementation.

Separation: interface (core domain) vs implementation (infrastructure).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class EventRepository(ABC):
    """Interface untuk Event persistence (port)."""
    
    @abstractmethod
    def save_event(self, event: dict) -> str:
        """Save event, return event_id."""
        pass
    
    @abstractmethod
    def get_event(self, event_id: str) -> Optional[dict]:
        """Get event by ID."""
        pass
    
    @abstractmethod
    def get_latest_events(self, workspace_id: str, limit: int = 10) -> List[dict]:
        """Get N latest events for workspace."""
        pass
    
    @abstractmethod
    def save_pick(self, pick: dict) -> str:
        """Save pick, return pick_id."""
        pass
    
    @abstractmethod
    def get_picks_for_cluster(self, cluster_id: str) -> List[dict]:
        """Get picks in cluster."""
        pass


class MongoEventRepository(EventRepository):
    """MongoDB implementation (adapter)."""
    
    def __init__(self, mongo_uri: str, db_name: str = "ai_gempa"):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self._client = None
        self._db = None
    
    def _ensure_connection(self):
        if not self._client:
            from pymongo import MongoClient
            self._client = MongoClient(self.mongo_uri)
            self._db = self._client[self.db_name]
    
    def save_event(self, event: dict) -> str:
        self._ensure_connection()
        event["created_at"] = datetime.utcnow()
        result = self._db.events.insert_one(event)
        return event["event_id"]
    
    def get_event(self, event_id: str) -> Optional[dict]:
        self._ensure_connection()
        doc = self._db.events.find_one({"event_id": event_id})
        return doc
    
    def get_latest_events(self, workspace_id: str, limit: int = 10) -> List[dict]:
        self._ensure_connection()
        cursor = self._db.events.find({"workspace_id": workspace_id}) \
                                .sort("created_at", -1) \
                                .limit(limit)
        return list(cursor)
    
    def save_pick(self, pick: dict) -> str:
        self._ensure_connection()
        result = self._db.picks.insert_one(pick)
        return pick.get("pick_id", str(result.inserted_id))
    
    def get_picks_for_cluster(self, cluster_id: str) -> List[dict]:
        self._ensure_connection()
        cursor = self._db.picks.find({"cluster_id": cluster_id})
        return list(cursor)


class InMemoryEventRepository(EventRepository):
    """In-memory implementation untuk test."""
    
    def __init__(self):
        self.events = {}    # {event_id: dict}
        self.picks = {}     # {pick_id: dict}
    
    def save_event(self, event: dict) -> str:
        event_id = event["event_id"]
        self.events[event_id] = event
        return event_id
    
    def get_event(self, event_id: str) -> Optional[dict]:
        return self.events.get(event_id)
    
    def get_latest_events(self, workspace_id: str, limit: int = 10) -> List[dict]:
        workspace_events = [e for e in self.events.values() if e["workspace_id"] == workspace_id]
        # Sort by created_at desc
        workspace_events.sort(key=lambda e: e.get("created_at", ""), reverse=True)
        return workspace_events[:limit]
    
    def save_pick(self, pick: dict) -> str:
        pick_id = pick["pick_id"]
        self.picks[pick_id] = pick
        return pick_id
    
    def get_picks_for_cluster(self, cluster_id: str) -> List[dict]:
        return [p for p in self.picks.values() if p.get("cluster_id") == cluster_id]


if __name__ == "__main__":
    # Example: in-memory repo
    repo = InMemoryEventRepository()
    
    event = {"event_id": "e123", "workspace_id": "ws1", "magnitude": 5.2, "created_at": "2026-10-19"}
    repo.save_event(event)
    
    retrieved = repo.get_event("e123")
    print(f"Event: {retrieved}")
    
    latest = repo.get_latest_events("ws1", limit=5)
    print(f"Latest events: {len(latest)}")
