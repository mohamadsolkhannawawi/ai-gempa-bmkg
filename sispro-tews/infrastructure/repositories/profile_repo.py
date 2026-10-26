"""
infrastructure/repositories/profile_repo.py - ProfileRepository (MongoDB adapter).

Interface + MongoDB implementation untuk profile persistence.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone

from core.profile_service import Profile, ProfileStatus


class IProfileRepository(ABC):
    """Interface untuk profile repository."""
    
    @abstractmethod
    async def save(self, profile: Profile) -> Profile:
        """Save atau update profile."""
        pass
    
    @abstractmethod
    async def get_by_id(self, profile_id: str) -> Optional[Profile]:
        """Get profile by ID."""
        pass
    
    @abstractmethod
    async def list_by_workspace(self, workspace_id: str, status: Optional[ProfileStatus] = None) -> List[Profile]:
        """List profiles by workspace, optionally filter by status."""
        pass
    
    @abstractmethod
    async def get_active_by_workspace(self, workspace_id: str) -> Optional[Profile]:
        """Get active profile per workspace (max 1)."""
        pass
    
    @abstractmethod
    async def delete(self, profile_id: str) -> bool:
        """Delete profile (hard delete, only DRAFT allowed)."""
        pass
    
    @abstractmethod
    async def deactivate_other_profiles(self, workspace_id: str, except_profile_id: str) -> int:
        """Set other profiles to ARCHIVED (before activating new one)."""
        pass


class MongoProfileRepository(IProfileRepository):
    """MongoDB implementation."""
    
    def __init__(self, db_client=None):
        """
        db_client: MongoDB client (injected, atau lazily initialized).
        Assumes collection 'profiles' exists.
        """
        self.db_client = db_client
        self._collection = None
    
    @property
    def collection(self):
        """Lazy-load MongoDB collection."""
        if self._collection is None:
            # TODO: initialize from db_client
            # For now, stub
            pass
        return self._collection
    
    async def save(self, profile: Profile) -> Profile:
        """Save profile to MongoDB."""
        data = profile.to_dict()
        
        # Upsert: insert if not exists, update if exists
        result = await self.collection.update_one(
            {"id": profile.id},
            {"$set": data},
            upsert=True
        )
        
        profile.updated_at = datetime.now(timezone.utc)
        return profile
    
    async def get_by_id(self, profile_id: str) -> Optional[Profile]:
        """Get profile by ID."""
        doc = await self.collection.find_one({"id": profile_id})
        if not doc:
            return None
        
        # Remove MongoDB _id field
        doc.pop("_id", None)
        return Profile.from_dict(doc)
    
    async def list_by_workspace(self, workspace_id: str, status: Optional[ProfileStatus] = None) -> List[Profile]:
        """List profiles by workspace."""
        query = {"workspace_id": workspace_id}
        
        if status:
            query["status"] = status.value
        
        docs = await self.collection.find(query).sort("created_at", -1).to_list(None)
        
        profiles = []
        for doc in docs:
            doc.pop("_id", None)
            profiles.append(Profile.from_dict(doc))
        
        return profiles
    
    async def get_active_by_workspace(self, workspace_id: str) -> Optional[Profile]:
        """Get active profile (max 1)."""
        doc = await self.collection.find_one({
            "workspace_id": workspace_id,
            "status": ProfileStatus.ACTIVE.value
        })
        
        if not doc:
            return None
        
        doc.pop("_id", None)
        return Profile.from_dict(doc)
    
    async def delete(self, profile_id: str) -> bool:
        """Delete profile (hard delete)."""
        # Check status first (only DRAFT allowed)
        profile = await self.get_by_id(profile_id)
        if profile and profile.status != ProfileStatus.DRAFT:
            raise ValueError(f"Cannot delete profile with status {profile.status}")
        
        result = await self.collection.delete_one({"id": profile_id})
        return result.deleted_count > 0
    
    async def deactivate_other_profiles(self, workspace_id: str, except_profile_id: str) -> int:
        """Archive other profiles when activating new one."""
        result = await self.collection.update_many(
            {
                "workspace_id": workspace_id,
                "id": {"$ne": except_profile_id},
                "status": ProfileStatus.ACTIVE.value
            },
            {
                "$set": {
                    "status": ProfileStatus.ARCHIVED.value,
                    "archived_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return result.modified_count


class InMemoryProfileRepository(IProfileRepository):
    """In-memory implementation untuk testing."""
    
    def __init__(self):
        self.profiles: dict[str, Profile] = {}
    
    async def save(self, profile: Profile) -> Profile:
        """Save profile to memory."""
        profile.updated_at = datetime.now(timezone.utc)
        self.profiles[profile.id] = profile
        return profile
    
    async def get_by_id(self, profile_id: str) -> Optional[Profile]:
        """Get profile by ID."""
        return self.profiles.get(profile_id)
    
    async def list_by_workspace(self, workspace_id: str, status: Optional[ProfileStatus] = None) -> List[Profile]:
        """List profiles by workspace."""
        result = [p for p in self.profiles.values() if p.workspace_id == workspace_id]
        
        if status:
            result = [p for p in result if p.status == status]
        
        return sorted(result, key=lambda p: p.created_at, reverse=True)
    
    async def get_active_by_workspace(self, workspace_id: str) -> Optional[Profile]:
        """Get active profile."""
        for profile in self.profiles.values():
            if profile.workspace_id == workspace_id and profile.status == ProfileStatus.ACTIVE:
                return profile
        return None
    
    async def delete(self, profile_id: str) -> bool:
        """Delete profile."""
        profile = self.profiles.get(profile_id)
        if profile and profile.status != ProfileStatus.DRAFT:
            raise ValueError(f"Cannot delete profile with status {profile.status}")
        
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            return True
        return False
    
    async def deactivate_other_profiles(self, workspace_id: str, except_profile_id: str) -> int:
        """Archive other profiles."""
        count = 0
        for profile in self.profiles.values():
            if (profile.workspace_id == workspace_id and
                profile.id != except_profile_id and
                profile.status == ProfileStatus.ACTIVE):
                profile.status = ProfileStatus.ARCHIVED
                profile.archived_at = datetime.now(timezone.utc)
                count += 1
        return count


if __name__ == "__main__":
    import asyncio
    from core.profile_service import ProfileService
    
    async def test():
        # Use in-memory repo untuk testing
        repo = InMemoryProfileRepository()
        service = ProfileService(repo)
        
        # Create profile
        profile = service.create_profile(
            workspace_id="ws_001",
            name="Test Profile",
            description="Test",
            created_by="user_001"
        )
        
        # Save
        saved = await repo.save(profile)
        print(f"Saved: {saved.id}")
        
        # Retrieve
        retrieved = await repo.get_by_id(saved.id)
        print(f"Retrieved: {retrieved.name} ({retrieved.status})")
        
        # List
        profiles = await repo.list_by_workspace("ws_001")
        print(f"Total profiles: {len(profiles)}")
    
    asyncio.run(test())
