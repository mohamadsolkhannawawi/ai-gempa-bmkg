"""
core/workspace.py - Workspace & User Domain untuk AI-GEMPA (tanpa framework).

Konsep:
  - Workspace  : isolated environment per user/org, punya profile + usage + quota sendiri
  - User       : person yang bisa access 1+ workspace dengan role (admin, viewer, analyst)
  - Subscription : paket billing (basic, pro, enterprise), validity, quota
  - BillingAccount : payment method, invoice history, balance
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ----------------------------------------------------------------------------- enum
class Plan(str, Enum):
    """Subscription plan."""
    BASIC = "basic"            # read-only access, fixed default pipeline
    PRO = "pro"                # custom profile, 100 stations
    ENTERPRISE = "enterprise"  # unlimited custom, dedicated support


class UserRole(str, Enum):
    """User role dalam workspace."""
    ADMIN = "admin"            # create/update workspace, config, billing
    ANALYST = "analyst"        # view data, analyze events, create profile
    VIEWER = "viewer"          # read-only, view events only


class SubscriptionStatus(str, Enum):
    """Subscription lifecycle status."""
    ACTIVE = "active"
    TRIAL = "trial"            # free tier, limited quota
    SUSPENDED = "suspended"    # payment overdue
    CANCELLED = "cancelled"


# ----------------------------------------------------------------------------- value object
@dataclass(frozen=True)
class DateRange:
    """Period dengan start/end date."""
    start_date: str            # YYYY-MM-DD
    end_date: str              # YYYY-MM-DD
    
    def contains(self, date_str: str) -> bool:
        return self.start_date <= date_str <= self.end_date
    
    def days_remaining(self) -> int:
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        today = datetime.now(timezone.utc).date()
        return max(0, (end.date() - today).days)
    
    def is_active(self) -> bool:
        return self.days_remaining() > 0


@dataclass(frozen=True)
class Quota:
    """Monthly usage quota."""
    plan_id: str
    max_picks: int              # per bulan
    max_events: int
    max_waveform_gb: int
    max_api_calls: int
    
    @staticmethod
    def for_plan(plan: Plan) -> Quota:
        tiers = {
            Plan.BASIC: Quota("basic", 50000, 100, 100, 10000),
            Plan.PRO: Quota("pro", 500000, 1000, 1000, 100000),
            Plan.ENTERPRISE: Quota("enterprise", 999999999, 999999999, 999999999, 999999999),
        }
        return tiers[plan]


@dataclass(frozen=True)
class TrialQuota:
    """Free tier quota (first 30 days or first 10K picks, whichever first)."""
    free_picks: int = 10000
    free_events: int = 100
    free_waveform_gb: int = 50
    free_api_calls: int = 5000


# ----------------------------------------------------------------------------- entity
@dataclass
class User:
    """User dalam system."""
    user_id: str                # UUID
    email: str
    name: str
    organization: str = ""
    created_at: str = ""        # ISO8601
    last_login: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict:
        return {"user_id": self.user_id, "email": self.email, "name": self.name}


@dataclass
class Subscription:
    """User subscription ke workspace (paket billing)."""
    subscription_id: str        # UUID
    workspace_id: str
    plan: Plan
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    valid_from: str = ""        # YYYY-MM-DD
    valid_until: str = ""       # YYYY-MM-DD (None = perpetual basic)
    created_at: str = ""        # ISO8601
    quota: Quota = field(default_factory=lambda: Quota("basic", 0, 0, 0, 0))
    trial_quota: Optional[TrialQuota] = None
    
    def is_valid(self) -> bool:
        """Check if subscription active dan belum expired."""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        if not self.valid_until:
            return True  # perpetual (basic)
        today = datetime.now(timezone.utc).date().isoformat()
        return today <= self.valid_until
    
    def days_remaining(self) -> int:
        if not self.valid_until:
            return 999999  # perpetual
        end = datetime.strptime(self.valid_until, "%Y-%m-%d")
        today = datetime.now(timezone.utc).date()
        return max(0, (end.date() - today).days)
    
    def is_trial(self) -> bool:
        return self.status == SubscriptionStatus.TRIAL and self.trial_quota is not None


@dataclass
class WorkspaceUser:
    """User + role dalam workspace."""
    user_id: str
    workspace_id: str
    role: UserRole = UserRole.VIEWER
    added_at: str = ""          # ISO8601
    last_activity: Optional[str] = None
    
    def can_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    def can_edit(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.ANALYST)


@dataclass
class Workspace:
    """Isolated environment per user/org."""
    workspace_id: str           # UUID, globally unique
    owner_id: str               # user_id yang buat workspace
    name: str
    description: str = ""
    organization: str = ""
    created_at: str = ""        # ISO8601
    updated_at: str = ""
    is_active: bool = True
    
    # Members
    members: Dict[str, WorkspaceUser] = field(default_factory=dict)  # {user_id: WorkspaceUser}
    
    # Subscription (paket billing)
    subscription: Optional[Subscription] = None
    
    # Billing account
    billing_contact_email: str = ""
    payment_method: str = ""    # "credit_card" | "bank_transfer" | "none"
    invoice_history: List[str] = field(default_factory=list)  # [invoice_id]
    
    # Settings
    settings: Dict[str, str] = field(default_factory=dict)
    
    def add_member(self, user_id: str, role: UserRole = UserRole.VIEWER):
        """Add user ke workspace dengan role."""
        self.members[user_id] = WorkspaceUser(user_id, self.workspace_id, role, 
                                              datetime.now(timezone.utc).isoformat())
    
    def remove_member(self, user_id: str):
        """Remove user dari workspace."""
        if user_id in self.members:
            del self.members[user_id]
    
    def get_member_role(self, user_id: str) -> Optional[UserRole]:
        """Get user role dalam workspace."""
        m = self.members.get(user_id)
        return m.role if m else None
    
    def is_accessible_by(self, user_id: str) -> bool:
        """Check if user bisa access workspace."""
        if user_id == self.owner_id:
            return True  # owner selalu bisa
        return user_id in self.members
    
    def can_edit_by(self, user_id: str) -> bool:
        """Check if user bisa edit config."""
        if user_id == self.owner_id:
            return True
        m = self.members.get(user_id)
        return m and m.can_edit()
    
    def can_admin_by(self, user_id: str) -> bool:
        """Check if user adalah admin."""
        if user_id == self.owner_id:
            return True
        m = self.members.get(user_id)
        return m and m.can_admin()
    
    def to_dict(self) -> Dict:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "organization": self.organization,
            "plan": self.subscription.plan.value if self.subscription else None,
            "members_count": len(self.members),
        }


# ----------------------------------------------------------------------------- repository interface
class WorkspaceRepository:
    """Interface untuk Workspace persistence."""
    
    def save_user(self, user: User) -> str:
        """Save user, return user_id."""
        raise NotImplementedError
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        raise NotImplementedError
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        raise NotImplementedError
    
    def save_workspace(self, workspace: Workspace) -> str:
        """Save workspace, return workspace_id."""
        raise NotImplementedError
    
    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get workspace by ID."""
        raise NotImplementedError
    
    def get_workspaces_for_user(self, user_id: str) -> List[Workspace]:
        """Get all workspaces user bisa access."""
        raise NotImplementedError
    
    def save_subscription(self, sub: Subscription) -> str:
        """Save subscription, return subscription_id."""
        raise NotImplementedError
    
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        raise NotImplementedError


# ----------------------------------------------------------------------------- domain service
class WorkspaceService:
    """Pure business logic untuk workspace management."""
    
    @staticmethod
    def create_workspace(user: User, name: str, organization: str = "") -> Workspace:
        """Create new workspace untuk user."""
        import uuid
        now = datetime.now(timezone.utc).isoformat()
        workspace = Workspace(
            workspace_id=uuid.uuid4().hex[:12],
            owner_id=user.user_id,
            name=name,
            organization=organization,
            created_at=now,
            updated_at=now
        )
        # Owner adalah admin
        workspace.add_member(user.user_id, UserRole.ADMIN)
        return workspace
    
    @staticmethod
    def activate_subscription(workspace: Workspace, plan: Plan, 
                            trial: bool = False) -> Subscription:
        """Create subscription untuk workspace."""
        import uuid
        now = datetime.now(timezone.utc).isoformat()
        valid_from = datetime.now(timezone.utc).date().isoformat()
        
        if trial:
            # Trial: 30 hari atau 10K picks
            valid_until = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
            sub = Subscription(
                subscription_id=uuid.uuid4().hex[:12],
                workspace_id=workspace.workspace_id,
                plan=plan,
                status=SubscriptionStatus.TRIAL,
                valid_from=valid_from,
                valid_until=valid_until,
                created_at=now,
                quota=Quota.for_plan(plan),
                trial_quota=TrialQuota()
            )
        else:
            # Paid: perpetual (basic) atau 1 tahun (pro/enterprise)
            if plan == Plan.BASIC:
                valid_until = None  # perpetual
            else:
                valid_until = (datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat()
            sub = Subscription(
                subscription_id=uuid.uuid4().hex[:12],
                workspace_id=workspace.workspace_id,
                plan=plan,
                status=SubscriptionStatus.ACTIVE,
                valid_from=valid_from,
                valid_until=valid_until,
                created_at=now,
                quota=Quota.for_plan(plan)
            )
        
        workspace.subscription = sub
        return sub
    
    @staticmethod
    def check_quota(workspace: Workspace, resource: str, current_usage: int) -> Tuple[bool, int]:
        """Check if usage within quota. Return (is_ok, remaining)."""
        if not workspace.subscription:
            return False, 0
        
        quota = workspace.subscription.quota
        if workspace.subscription.is_trial():
            quota_obj = workspace.subscription.trial_quota
            limits = {"picks": quota_obj.free_picks, "events": quota_obj.free_events,
                     "waveform_gb": quota_obj.free_waveform_gb, "api_calls": quota_obj.free_api_calls}
        else:
            limits = {"picks": quota.max_picks, "events": quota.max_events,
                     "waveform_gb": quota.max_waveform_gb, "api_calls": quota.max_api_calls}
        
        limit = limits.get(resource, 0)
        if limit == 0:
            return False, 0
        
        remaining = max(0, limit - current_usage)
        return current_usage <= limit, remaining
    
    @staticmethod
    def downgrade_on_overuse(workspace: Workspace):
        """Suspend workspace jika quota exceeded."""
        if workspace.subscription and workspace.subscription.is_trial():
            # Trial overuse → suspend (upgrade to paid atau wait next month)
            workspace.subscription.status = SubscriptionStatus.SUSPENDED


# ----------------------------------------------------------------------------- aggregate
@dataclass
class WorkspaceAggregate:
    """Aggregate root: Workspace + Users + Subscription (accounting unit)."""
    workspace: Workspace
    owner: User
    members: List[User]
    
    def member_count(self) -> int:
        return len(self.members) + 1  # +1 owner


if __name__ == "__main__":
    # Example: create user → workspace → subscribe to pro plan
    user = User("u123", "admin@example.com", "Admin", "BMKG")
    ws = WorkspaceService.create_workspace(user, "BMKG Monitoring", "BMKG")
    sub = WorkspaceService.activate_subscription(ws, Plan.PRO)
    
    print(f"Workspace: {ws.name} ({ws.workspace_id})")
    print(f"Subscription: {sub.plan.value}, valid until {sub.valid_until}")
    print(f"Quota: {sub.quota.max_picks} picks/month")
    
    # Check quota
    ok, remaining = WorkspaceService.check_quota(ws, "picks", 100000)
    print(f"Can use 100K picks? {ok}, remaining={remaining}")
