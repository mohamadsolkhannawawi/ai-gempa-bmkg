"""
infrastructure/repositories/usage_repo.py - UsageRepository untuk aggregated usage.

Interface + MongoDB adapter untuk menyimpan daily aggregated usage.
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging

from metering.events import AggregatedUsage

logger = logging.getLogger(__name__)


class UsageRepository:
    """
    Abstract interface untuk usage repository.
    
    Methods:
    - save_aggregated_usage: save daily aggregated usage
    - get_usage_by_date: query usage per day
    - get_usage_by_range: query usage dalam date range
    - delete_old_usage: cleanup old data
    """
    
    def save_aggregated_usage(self, usage: AggregatedUsage) -> bool:
        """Save aggregated usage."""
        raise NotImplementedError
    
    def get_usage_by_date(
        self,
        workspace_id: str,
        user_id: str,
        date_str: str
    ) -> Optional[AggregatedUsage]:
        """Get usage untuk specific date."""
        raise NotImplementedError
    
    def get_usage_by_range(
        self,
        workspace_id: str,
        user_id: str,
        start_date: str,
        end_date: str
    ) -> List[AggregatedUsage]:
        """Get usage dalam date range (YYYY-MM-DD)."""
        raise NotImplementedError
    
    def get_workspace_total(
        self,
        workspace_id: str,
        start_date: str,
        end_date: str
    ) -> Decimal:
        """Get total cost untuk workspace dalam period."""
        raise NotImplementedError
    
    def delete_old_usage(self, before_date: str) -> int:
        """Delete usage sebelum date. Returns count deleted."""
        raise NotImplementedError


class MongoUsageRepository(UsageRepository):
    """
    MongoDB implementation untuk UsageRepository.
    
    Collection: usage_daily
    Index: (workspace_id, user_id, date)
    """
    
    def __init__(self, db):
        """
        Args:
        - db: MongoDB database instance
        """
        self.db = db
        self.collection = db["usage_daily"]
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create indexes."""
        try:
            # Compound index untuk queries
            self.collection.create_index([
                ("workspace_id", 1),
                ("user_id", 1),
                ("date", 1)
            ], unique=True, name="idx_workspace_user_date")
            
            # Index untuk cleanup queries
            self.collection.create_index([
                ("date", 1)
            ], name="idx_date")
            
            logger.info("Usage indexes created")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    def save_aggregated_usage(self, usage: AggregatedUsage) -> bool:
        """Save aggregated usage (upsert)."""
        try:
            filter_doc = {
                "workspace_id": usage.workspace_id,
                "user_id": usage.user_id,
                "date": usage.date
            }
            
            # Upsert (insert if not exist, update if exist)
            result = self.collection.update_one(
                filter_doc,
                {"$set": usage.to_dict()},
                upsert=True
            )
            
            logger.info(
                f"Saved usage for {usage.workspace_id}:{usage.user_id} "
                f"on {usage.date}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save usage: {e}")
            return False
    
    def get_usage_by_date(
        self,
        workspace_id: str,
        user_id: str,
        date_str: str
    ) -> Optional[AggregatedUsage]:
        """Get usage untuk specific date."""
        try:
            doc = self.collection.find_one({
                "workspace_id": workspace_id,
                "user_id": user_id,
                "date": date_str
            })
            
            if not doc:
                return None
            
            # Convert back to AggregatedUsage
            doc.pop("_id", None)
            doc["total_cost_idr"] = Decimal(str(doc["total_cost_idr"]))
            doc["breakdown_by_provider"] = {
                k: Decimal(str(v)) for k, v in doc.get("breakdown_by_provider", {}).items()
            }
            doc["breakdown_by_module"] = {
                k: Decimal(str(v)) for k, v in doc.get("breakdown_by_module", {}).items()
            }
            
            return AggregatedUsage(**doc)
        except Exception as e:
            logger.error(f"Failed to get usage: {e}")
            return None
    
    def get_usage_by_range(
        self,
        workspace_id: str,
        user_id: str,
        start_date: str,
        end_date: str
    ) -> List[AggregatedUsage]:
        """Get usage dalam date range."""
        try:
            docs = self.collection.find({
                "workspace_id": workspace_id,
                "user_id": user_id,
                "date": {"$gte": start_date, "$lte": end_date}
            }).sort("date", 1)
            
            results = []
            for doc in docs:
                doc.pop("_id", None)
                doc["total_cost_idr"] = Decimal(str(doc["total_cost_idr"]))
                doc["breakdown_by_provider"] = {
                    k: Decimal(str(v)) for k, v in doc.get("breakdown_by_provider", {}).items()
                }
                doc["breakdown_by_module"] = {
                    k: Decimal(str(v)) for k, v in doc.get("breakdown_by_module", {}).items()
                }
                results.append(AggregatedUsage(**doc))
            
            return results
        except Exception as e:
            logger.error(f"Failed to get usage range: {e}")
            return []
    
    def get_workspace_total(
        self,
        workspace_id: str,
        start_date: str,
        end_date: str
    ) -> Decimal:
        """Get total cost untuk workspace dalam period."""
        try:
            pipeline = [
                {
                    "$match": {
                        "workspace_id": workspace_id,
                        "date": {"$gte": start_date, "$lte": end_date}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": "$total_cost_idr"}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                return Decimal(str(result[0]["total"]))
            return Decimal("0")
        except Exception as e:
            logger.error(f"Failed to get workspace total: {e}")
            return Decimal("0")
    
    def delete_old_usage(self, before_date: str) -> int:
        """Delete usage sebelum date."""
        try:
            result = self.collection.delete_many({
                "date": {"$lt": before_date}
            })
            
            logger.info(f"Deleted {result.deleted_count} old usage records")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete old usage: {e}")
            return 0


class InMemoryUsageRepository(UsageRepository):
    """
    In-memory implementation untuk testing.
    
    Usage:
        repo = InMemoryUsageRepository()
        agg = AggregatedUsage(...)
        repo.save_aggregated_usage(agg)
    """
    
    def __init__(self):
        self._data: Dict[Tuple[str, str, str], AggregatedUsage] = {}
    
    def save_aggregated_usage(self, usage: AggregatedUsage) -> bool:
        """Save aggregated usage."""
        key = (usage.workspace_id, usage.user_id, usage.date)
        self._data[key] = usage
        return True
    
    def get_usage_by_date(
        self,
        workspace_id: str,
        user_id: str,
        date_str: str
    ) -> Optional[AggregatedUsage]:
        """Get usage untuk specific date."""
        key = (workspace_id, user_id, date_str)
        return self._data.get(key)
    
    def get_usage_by_range(
        self,
        workspace_id: str,
        user_id: str,
        start_date: str,
        end_date: str
    ) -> List[AggregatedUsage]:
        """Get usage dalam date range."""
        results = []
        for (ws, uid, d), usage in self._data.items():
            if ws == workspace_id and uid == user_id and start_date <= d <= end_date:
                results.append(usage)
        return sorted(results, key=lambda u: u.date)
    
    def get_workspace_total(
        self,
        workspace_id: str,
        start_date: str,
        end_date: str
    ) -> Decimal:
        """Get total cost untuk workspace dalam period."""
        total = Decimal("0")
        for (ws, uid, d), usage in self._data.items():
            if ws == workspace_id and start_date <= d <= end_date:
                total += usage.total_cost_idr
        return total
    
    def delete_old_usage(self, before_date: str) -> int:
        """Delete usage sebelum date."""
        keys_to_delete = [
            key for key, usage in self._data.items()
            if usage.date < before_date
        ]
        
        for key in keys_to_delete:
            del self._data[key]
        
        return len(keys_to_delete)
