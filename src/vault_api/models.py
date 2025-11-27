"""Pydantic models for API requests and responses."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ProjectCreationRequest(BaseModel):
    """Request model for project creation."""

    environments: List[str] | None = Field(
        default=None,
        description="List of environment names (defaults to dev, staging, production)",
        examples=[["dev", "staging", "production"]],
    )


class ProjectCreationResponse(BaseModel):
    """Response model for project creation."""

    project_name: str = Field(..., description="Name of the created project")
    created_paths: List[str] = Field(..., description="Paths that were created")
    skipped_paths: List[str] = Field(..., description="Paths that already existed")
    message: str = Field(..., description="Human-readable status message")


class ProjectListResponse(BaseModel):
    """Response model for listing projects."""

    projects: List[str] = Field(..., description="List of project names")
    count: int = Field(..., description="Number of projects")


class ProjectInfoResponse(BaseModel):
    """Response model for project information."""

    project_name: str = Field(..., description="Name of the project")
    environments: List[str] = Field(..., description="List of environment names")
    paths: List[str] = Field(..., description="Full paths for each environment")

class ProjectUpdateRequest(BaseModel):
    """Request model for project update."""

    add_environments: List[str] | None = Field(
        default=None,
        description="List of environment names to add to the project",
        examples=[["staging", "production"]],
    )
    remove_environments: List[str] | None = Field(
        default=None,
        description="List of environment names to remove from the project",
        examples=[["dev"]],
    )


class ProjectUpdateResponse(BaseModel):
    """Response model for project update."""

    project_name: str = Field(..., description="Name of the updated project")
    added_environments: List[str] = Field(..., description="Environments that were added")
    removed_environments: List[str] = Field(..., description="Environments that were removed")
    created_paths: List[str] = Field(..., description="Paths that were created")
    deleted_paths: List[str] = Field(..., description="Paths that were deleted")
    message: str = Field(..., description="Human-readable status message")


class ProjectDeleteResponse(BaseModel):
    """Response model for project deletion."""

    project_name: str = Field(..., description="Name of the deleted project")
    deleted_paths: List[str] = Field(..., description="Paths that were deleted")
    message: str = Field(..., description="Human-readable status message")

