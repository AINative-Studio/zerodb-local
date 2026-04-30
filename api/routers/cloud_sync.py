"""
Cloud Sync Router
API endpoints for cloud API integration and sync operations
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from uuid import UUID

from services.cloud_client import CloudAPIClient
from schemas.cloud_sync import (
    CloudAuthRequest,
    CloudAuthResponse,
    BundleUploadRequest,
    BundleUploadResponse,
    BundleDownloadRequest,
    BundleDownloadResponse,
    CloudSyncStatus,
    BundleInfo,
    BundleStatus,
    CloudAPIError
)
from errors import (
    CloudAPIAuthenticationError,
    CloudAPIConnectionError,
    CloudAPINotFoundError,
    CloudAPIServerError,
    CloudAPITimeoutError
)


logger = logging.getLogger(__name__)


# Create router
router = APIRouter()


_cloud_client_instance: CloudAPIClient = None


def get_cloud_client() -> CloudAPIClient:
    """
    Dependency to get shared CloudAPIClient instance.
    Singleton so auth token persists between requests.
    """
    global _cloud_client_instance
    if _cloud_client_instance is None:
        _cloud_client_instance = CloudAPIClient()
    return _cloud_client_instance


@router.post(
    "/{project_id}/cloud/auth",
    response_model=CloudAuthResponse,
    summary="Authenticate with ZeroDB Cloud",
    description="""
    Authenticate with ZeroDB Cloud API using an API key.
    Returns a bearer token that expires after the specified duration.

    The token must be used for all subsequent cloud operations.
    """,
    responses={
        200: {"description": "Successfully authenticated", "model": CloudAuthResponse},
        401: {"description": "Authentication failed", "model": CloudAPIError},
        503: {"description": "Cloud API unavailable", "model": CloudAPIError}
    }
)
async def authenticate_with_cloud(
    project_id: UUID = Path(..., description="Project ID"),
    request: CloudAuthRequest = ...,
    cloud_client: CloudAPIClient = Depends(get_cloud_client)
):
    """
    Authenticate with ZeroDB Cloud API

    Args:
        project_id: Project UUID
        request: Authentication request with API key
        cloud_client: CloudAPIClient dependency

    Returns:
        CloudAuthResponse with bearer token

    Raises:
        HTTPException: 401 if authentication fails, 503 if cloud unavailable
    """
    try:
        logger.info(f"Authenticating with cloud for project {project_id}")

        async with cloud_client:
            auth_response = await cloud_client.authenticate(request.api_key)

        logger.info(f"Cloud authentication successful for project {project_id}")
        return auth_response

    except CloudAPIAuthenticationError as e:
        logger.error(f"Cloud authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "authentication_failed",
                "message": str(e),
                "details": getattr(e, 'api_details', None)
            }
        )
    except CloudAPIConnectionError as e:
        logger.error(f"Cloud connection failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "cloud_unavailable",
                "message": str(e),
                "url": getattr(e, 'url', None)
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during cloud authentication: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred during authentication"
            }
        )


@router.post(
    "/{project_id}/cloud/upload",
    response_model=BundleUploadResponse,
    summary="Upload sync bundle to cloud",
    description="""
    Upload a sync bundle containing local data to ZeroDB Cloud.

    The bundle can contain vectors, tables, memory, files, and events.
    Compression is enabled by default to reduce upload size.

    Requires prior authentication with the cloud API.
    """,
    responses={
        200: {"description": "Bundle uploaded successfully", "model": BundleUploadResponse},
        401: {"description": "Not authenticated", "model": CloudAPIError},
        500: {"description": "Upload failed", "model": CloudAPIError}
    }
)
async def upload_bundle_to_cloud(
    project_id: UUID = Path(..., description="Project ID"),
    request: BundleUploadRequest = ...,
    cloud_client: CloudAPIClient = Depends(get_cloud_client)
):
    """
    Upload sync bundle to ZeroDB Cloud

    Args:
        project_id: Project UUID
        request: Bundle upload request
        cloud_client: CloudAPIClient dependency

    Returns:
        BundleUploadResponse with upload details

    Raises:
        HTTPException: 401 if not authenticated, 500 if upload fails
    """
    try:
        logger.info(f"Uploading bundle to cloud for project {project_id}")

        async with cloud_client:
            # Note: Client should already be authenticated
            upload_response = await cloud_client.upload_bundle(
                project_id=str(project_id),
                bundle_data=request.bundle_data,
                bundle_name=request.bundle_name,
                metadata=request.metadata,
                compression=request.compression
            )

        logger.info(
            f"Bundle uploaded successfully: upload_id={upload_response.upload_id}, "
            f"bundle_id={upload_response.bundle_id}"
        )
        return upload_response

    except CloudAPIAuthenticationError as e:
        logger.error(f"Cloud upload authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "not_authenticated",
                "message": "Not authenticated with cloud. Call /cloud/auth first."
            }
        )
    except CloudAPIServerError as e:
        logger.error(f"Cloud upload failed: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error": "upload_failed",
                "message": str(e),
                "details": getattr(e, 'api_details', None)
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during bundle upload: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred during upload"
            }
        )


@router.get(
    "/{project_id}/cloud/download/{bundle_id}",
    response_model=BundleDownloadResponse,
    summary="Download sync bundle from cloud",
    description="""
    Download a sync bundle from ZeroDB Cloud.

    The bundle contains data previously uploaded to the cloud.
    Use the bundle ID obtained from the upload response or bundle list.

    Requires prior authentication with the cloud API.
    """,
    responses={
        200: {"description": "Bundle downloaded successfully", "model": BundleDownloadResponse},
        401: {"description": "Not authenticated", "model": CloudAPIError},
        404: {"description": "Bundle not found", "model": CloudAPIError}
    }
)
async def download_bundle_from_cloud(
    project_id: UUID = Path(..., description="Project ID"),
    bundle_id: str = Path(..., description="Bundle ID to download"),
    include_metadata: bool = Query(True, description="Include bundle metadata"),
    cloud_client: CloudAPIClient = Depends(get_cloud_client)
):
    """
    Download sync bundle from ZeroDB Cloud

    Args:
        project_id: Project UUID
        bundle_id: Bundle ID to download
        include_metadata: Include metadata in response
        cloud_client: CloudAPIClient dependency

    Returns:
        BundleDownloadResponse with bundle data

    Raises:
        HTTPException: 401 if not authenticated, 404 if bundle not found
    """
    try:
        logger.info(f"Downloading bundle {bundle_id} from cloud for project {project_id}")

        async with cloud_client:
            download_response = await cloud_client.download_bundle(
                project_id=str(project_id),
                bundle_id=bundle_id,
                include_metadata=include_metadata
            )

        logger.info(
            f"Bundle downloaded successfully: bundle_id={download_response.bundle_id}, "
            f"size={download_response.size_bytes} bytes"
        )
        return download_response

    except CloudAPIAuthenticationError as e:
        logger.error(f"Cloud download authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "not_authenticated",
                "message": "Not authenticated with cloud. Call /cloud/auth first."
            }
        )
    except CloudAPINotFoundError as e:
        logger.error(f"Bundle not found: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "bundle_not_found",
                "message": f"Bundle '{bundle_id}' not found in cloud"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during bundle download: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred during download"
            }
        )


@router.get(
    "/{project_id}/cloud/status",
    response_model=CloudSyncStatus,
    summary="Get cloud sync status",
    description="""
    Get the current cloud sync status for a project.

    Returns information about authentication state, last sync time,
    available bundles, pending conflicts, and storage usage.

    Requires prior authentication with the cloud API.
    """,
    responses={
        200: {"description": "Sync status retrieved", "model": CloudSyncStatus},
        401: {"description": "Not authenticated", "model": CloudAPIError}
    }
)
async def get_cloud_sync_status(
    project_id: UUID = Path(..., description="Project ID"),
    cloud_client: CloudAPIClient = Depends(get_cloud_client)
):
    """
    Get cloud sync status for a project

    Args:
        project_id: Project UUID
        cloud_client: CloudAPIClient dependency

    Returns:
        CloudSyncStatus with current sync state

    Raises:
        HTTPException: 401 if not authenticated
    """
    try:
        logger.info(f"Getting cloud sync status for project {project_id}")

        async with cloud_client:
            sync_status = await cloud_client.get_cloud_sync_state(str(project_id))

        logger.info(f"Cloud sync status retrieved for project {project_id}")
        return sync_status

    except CloudAPIAuthenticationError as e:
        logger.error(f"Cloud status authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "not_authenticated",
                "message": "Not authenticated with cloud. Call /cloud/auth first."
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error getting cloud sync status: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred retrieving sync status"
            }
        )


@router.get(
    "/{project_id}/cloud/bundles",
    response_model=List[BundleInfo],
    summary="List available cloud bundles",
    description="""
    List all available sync bundles in ZeroDB Cloud for a project.

    Returns bundle metadata including ID, name, status, size, and entity counts.
    Supports pagination and filtering by bundle status.

    Requires prior authentication with the cloud API.
    """,
    responses={
        200: {"description": "Bundles listed successfully", "model": List[BundleInfo]},
        401: {"description": "Not authenticated", "model": CloudAPIError}
    }
)
async def list_cloud_bundles(
    project_id: UUID = Path(..., description="Project ID"),
    status_filter: Optional[BundleStatus] = Query(
        None,
        description="Filter by bundle status"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum bundles to return"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Pagination offset"
    ),
    cloud_client: CloudAPIClient = Depends(get_cloud_client)
):
    """
    List available bundles in ZeroDB Cloud

    Args:
        project_id: Project UUID
        status_filter: Optional filter by bundle status
        limit: Maximum results to return
        offset: Pagination offset
        cloud_client: CloudAPIClient dependency

    Returns:
        List of BundleInfo objects

    Raises:
        HTTPException: 401 if not authenticated
    """
    try:
        logger.info(f"Listing cloud bundles for project {project_id}")

        async with cloud_client:
            bundles = await cloud_client.list_available_bundles(
                project_id=str(project_id),
                status_filter=status_filter,
                limit=limit,
                offset=offset
            )

        logger.info(f"Retrieved {len(bundles)} bundles for project {project_id}")
        return bundles

    except CloudAPIAuthenticationError as e:
        logger.error(f"Cloud bundles authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "not_authenticated",
                "message": "Not authenticated with cloud. Call /cloud/auth first."
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error listing cloud bundles: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred listing bundles"
            }
        )
