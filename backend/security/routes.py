"""Explicit, short-lived grants for individual external project folders."""

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from security.workspace_access import ProjectAccessError, create_external_project_grant, external_project_grants


router = APIRouter(tags=["access"])


class CreateProjectGrantRequest(BaseModel):
    project_path: str


class ProjectGrantResponse(BaseModel):
    grant_id: str
    project_path: str
    expires_in_seconds: int


@router.post("/grants", response_model=ProjectGrantResponse, status_code=status.HTTP_201_CREATED)
async def create_project_grant(request: CreateProjectGrantRequest):
    try:
        grant = create_external_project_grant(request.project_path)
    except ProjectAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return ProjectGrantResponse(
        grant_id=grant.grant_id,
        project_path=str(grant.canonical_path),
        expires_in_seconds=external_project_grants.TTL_SECONDS,
    )


@router.delete("/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_project_grant(grant_id: str):
    if not external_project_grants.revoke(grant_id):
        raise HTTPException(status_code=404, detail="Folder grant not found or expired.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
