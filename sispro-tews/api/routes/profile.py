"""
api/routes/profile.py - FastAPI router untuk profile endpoints.

7 endpoints:
1. GET  /api/v2/profiles — list profiles per workspace
2. GET  /api/v2/profiles/{id} — get single profile
3. POST /api/v2/profiles — create new profile
4. PUT  /api/v2/profiles/{id} — update profile (DRAFT only)
5. PATCH /api/v2/profiles/{id}/activate — activate profile (DRAFT → ACTIVE)
6. DELETE /api/v2/profiles/{id} — delete profile (DRAFT only)
7. POST /api/v2/profiles/{id}/validate — validate profile sebelum activate
8. GET  /api/v2/profiles/{id}/cost — estimate monthly cost

Version: v2
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from decimal import Decimal

from api.schemas.profile import (
    ProfileCreateRequest, ProfileUpdateRequest, ProfileSchema, ProfileListResponse,
    ProfileActivateRequest, ProfileArchiveRequest, ProfileValidationResponse,
    ProfileCostEstimateResponse
)
from core.profile_service import ProfileService, Profile, ProfileServiceError, ProfileStatus
from infrastructure.repositories.profile_repo import IProfileRepository, MongoProfileRepository, InMemoryProfileRepository

router = APIRouter(prefix="/api/v2", tags=["profile"])

# Inject repository (default: in-memory untuk testing)
# Production: use MongoProfileRepository
_repo = InMemoryProfileRepository()


def get_repo() -> IProfileRepository:
    return _repo


@router.get("/profiles", response_model=ProfileListResponse)
async def list_profiles(
    workspace_id: str,
    status: Optional[str] = None,
    repo: IProfileRepository = Depends(get_repo)
):
    """
    List profiles per workspace.
    
    Query params:
    - workspace_id (required): Workspace ID
    - status (optional): draft | active | archived
    """
    status_filter = ProfileStatus(status) if status else None
    profiles = await repo.list_by_workspace(workspace_id, status_filter)
    
    # Get active profile
    active = await repo.get_active_by_workspace(workspace_id)
    
    # Convert to schema
    profile_schemas = [
        ProfileSchema(
            id=p.id,
            workspace_id=p.workspace_id,
            name=p.name,
            description=p.description,
            p_pick_config=p.p_pick_config,
            association_config=p.association_config,
            locmag_config=p.locmag_config,
            preferences=p.preferences,
            status=p.status.value,
            created_at=p.created_at,
            updated_at=p.updated_at,
            activated_at=p.activated_at,
            archived_at=p.archived_at,
            created_by=p.created_by,
            updated_by=p.updated_by
        )
        for p in profiles
    ]
    
    return ProfileListResponse(
        profiles=profile_schemas,
        count=len(profile_schemas),
        active_profile_id=active.id if active else None
    )


@router.get("/profiles/{profile_id}", response_model=ProfileSchema)
async def get_profile(
    profile_id: str,
    repo: IProfileRepository = Depends(get_repo)
):
    """Get single profile by ID."""
    profile = await repo.get_by_id(profile_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    return ProfileSchema(
        id=profile.id,
        workspace_id=profile.workspace_id,
        name=profile.name,
        description=profile.description,
        p_pick_config=profile.p_pick_config,
        association_config=profile.association_config,
        locmag_config=profile.locmag_config,
        preferences=profile.preferences,
        status=profile.status.value,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        activated_at=profile.activated_at,
        archived_at=profile.archived_at,
        created_by=profile.created_by,
        updated_by=profile.updated_by
    )


@router.post("/profiles", response_model=ProfileSchema, status_code=201)
async def create_profile(
    request: ProfileCreateRequest,
    workspace_id: str = "default_ws",  # TODO: get from auth context
    created_by: str = "system",        # TODO: get from auth context
    repo: IProfileRepository = Depends(get_repo)
):
    """
    Create new profile (DRAFT status).
    
    Default providers:
    - p_pick: sta_lta (CPU)
    - association: dbscan (CPU)
    - locmag: geiger (CPU)
    """
    service = ProfileService(repo)
    
    profile = service.create_profile(
        workspace_id=workspace_id,
        name=request.name,
        description=request.description or "",
        created_by=created_by,
        p_pick_provider_id=request.p_pick_provider_id,
        association_provider_id=request.association_provider_id,
        locmag_provider_id=request.locmag_provider_id,
        preferences=request.preferences.to_dict() if request.preferences else None
    )
    
    saved = await repo.save(profile)
    
    return ProfileSchema(
        id=saved.id,
        workspace_id=saved.workspace_id,
        name=saved.name,
        description=saved.description,
        p_pick_config=saved.p_pick_config,
        association_config=saved.association_config,
        locmag_config=saved.locmag_config,
        preferences=saved.preferences,
        status=saved.status.value,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
        activated_at=None,
        archived_at=None,
        created_by=saved.created_by,
        updated_by=saved.updated_by
    )


@router.put("/profiles/{profile_id}", response_model=ProfileSchema)
async def update_profile(
    profile_id: str,
    request: ProfileUpdateRequest,
    updated_by: str = "system",  # TODO: get from auth context
    repo: IProfileRepository = Depends(get_repo)
):
    """Update profile (only if DRAFT status)."""
    profile = await repo.get_by_id(profile_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    if profile.status != ProfileStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update profile with status {profile.status.value}"
        )
    
    service = ProfileService(repo)
    
    kwargs = {}
    if request.name:
        kwargs["name"] = request.name
    if request.description is not None:
        kwargs["description"] = request.description
    if request.p_pick_provider_id:
        kwargs["p_pick_provider_id"] = request.p_pick_provider_id
    if request.association_provider_id:
        kwargs["association_provider_id"] = request.association_provider_id
    if request.locmag_provider_id:
        kwargs["locmag_provider_id"] = request.locmag_provider_id
    if request.preferences:
        kwargs["preferences"] = request.preferences.to_dict()
    
    updated = service.update_profile(profile, updated_by=updated_by, **kwargs)
    saved = await repo.save(updated)
    
    return ProfileSchema(
        id=saved.id,
        workspace_id=saved.workspace_id,
        name=saved.name,
        description=saved.description,
        p_pick_config=saved.p_pick_config,
        association_config=saved.association_config,
        locmag_config=saved.locmag_config,
        preferences=saved.preferences,
        status=saved.status.value,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
        activated_at=saved.activated_at,
        archived_at=saved.archived_at,
        created_by=saved.created_by,
        updated_by=saved.updated_by
    )


@router.post("/profiles/{profile_id}/activate", response_model=ProfileSchema)
async def activate_profile(
    profile_id: str,
    request: ProfileActivateRequest,
    updated_by: str = "system",  # TODO: get from auth context
    repo: IProfileRepository = Depends(get_repo)
):
    """Activate profile (DRAFT → ACTIVE)."""
    if request.profile_id != profile_id:
        raise HTTPException(
            status_code=400,
            detail="Profile ID in path and body must match"
        )
    
    profile = await repo.get_by_id(profile_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    if profile.status != ProfileStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot activate profile with status {profile.status.value}"
        )
    
    service = ProfileService(repo)
    valid, msg = service.validate_profile(profile)
    
    if not valid:
        raise HTTPException(
            status_code=400,
            detail=f"Profile validation failed: {msg}"
        )
    
    activated = service.activate_profile(profile, updated_by=updated_by)
    saved = await repo.save(activated)
    
    return ProfileSchema(
        id=saved.id,
        workspace_id=saved.workspace_id,
        name=saved.name,
        description=saved.description,
        p_pick_config=saved.p_pick_config,
        association_config=saved.association_config,
        locmag_config=saved.locmag_config,
        preferences=saved.preferences,
        status=saved.status.value,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
        activated_at=saved.activated_at,
        archived_at=saved.archived_at,
        created_by=saved.created_by,
        updated_by=saved.updated_by
    )


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: str,
    repo: IProfileRepository = Depends(get_repo)
):
    """Delete profile (only DRAFT status allowed)."""
    profile = await repo.get_by_id(profile_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    if profile.status != ProfileStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete profile with status {profile.status.value}"
        )
    
    success = await repo.delete(profile_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete profile")
    
    return None


@router.post("/profiles/{profile_id}/validate", response_model=ProfileValidationResponse)
async def validate_profile(
    profile_id: str,
    repo: IProfileRepository = Depends(get_repo)
):
    """Validate profile sebelum activate."""
    profile = await repo.get_by_id(profile_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    service = ProfileService(repo)
    valid, msg = service.validate_profile(profile)
    
    errors = [msg] if not valid else []
    
    return ProfileValidationResponse(
        valid=valid,
        errors=errors,
        warnings=[]
    )


@router.get("/profiles/{profile_id}/cost", response_model=ProfileCostEstimateResponse)
async def estimate_profile_cost(
    profile_id: str,
    repo: IProfileRepository = Depends(get_repo)
):
    """Estimate monthly cost untuk profile."""
    profile = await repo.get_by_id(profile_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    service = ProfileService(repo)
    cost = service.estimate_monthly_cost(profile)
    
    return ProfileCostEstimateResponse(
        profile_id=profile_id,
        estimated_monthly_cost_idr=cost
    )


@router.get("/health/profiles")
async def health_check():
    """Health check untuk profile service."""
    return {
        "status": "healthy",
        "service": "profile"
    }
