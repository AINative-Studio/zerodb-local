"""
Cloud API Client Service
Handles communication with ZeroDB Cloud API for sync operations
"""
import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from schemas.cloud_sync import (
    CloudAuthRequest,
    CloudAuthResponse,
    BundleUploadRequest,
    BundleUploadResponse,
    BundleDownloadResponse,
    CloudSyncStatus,
    BundleInfo,
    ListBundlesResponse,
    CloudAPIError,
    BundleStatus
)
from errors import (
    CloudAPIAuthenticationError,
    CloudAPIConnectionError,
    CloudAPINotFoundError,
    CloudAPIServerError,
    CloudAPITimeoutError
)


logger = logging.getLogger(__name__)


class CloudAPIClient:
    """
    HTTP client for ZeroDB Cloud API

    Provides methods to authenticate, upload/download bundles,
    and retrieve sync state from ZeroDB Cloud.

    Features:
    - Automatic retry with exponential backoff
    - Timeout handling
    - Bearer token authentication
    - Progress tracking for large transfers
    - Comprehensive error handling
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3
    ):
        """
        Initialize Cloud API client

        Args:
            base_url: Cloud API base URL (defaults to env CLOUD_API_URL)
            timeout: Request timeout in seconds (defaults to env CLOUD_REQUEST_TIMEOUT or 30)
            max_retries: Maximum retry attempts for failed requests
        """
        self.base_url = base_url or os.getenv(
            "CLOUD_API_URL",
            "https://api.ainative.studio"
        )
        self.timeout = timeout or int(os.getenv("CLOUD_REQUEST_TIMEOUT", "30"))
        self.max_retries = max_retries

        # Authentication state
        self._api_key: Optional[str] = None
        self._auth_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # Create async HTTP client
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            f"CloudAPIClient initialized: base_url={self.base_url}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries}"
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _ensure_client(self):
        """Ensure HTTP client is initialized"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "User-Agent": "ZeroDB-Local/1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )

    async def close(self):
        """Close HTTP client and cleanup resources"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("CloudAPIClient closed")

    def _is_authenticated(self) -> bool:
        """Check if client has valid authentication (API key or token)"""
        if self._api_key:
            return True
        if not self._auth_token or not self._token_expires_at:
            return False
        buffer_seconds = 60
        return datetime.utcnow() + timedelta(seconds=buffer_seconds) < self._token_expires_at

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers (X-API-Key or Bearer token)"""
        if self._api_key:
            return {"X-API-Key": self._api_key}
        if self._auth_token and self._token_expires_at:
            if datetime.utcnow() + timedelta(seconds=60) < self._token_expires_at:
                return {"Authorization": f"Bearer {self._auth_token}"}
        raise CloudAPIAuthenticationError(
            "Not authenticated. Call authenticate() first."
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        auth_required: bool = True,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            auth_required: Whether authentication is required
            **kwargs: Additional arguments for httpx request

        Returns:
            httpx.Response object

        Raises:
            CloudAPIAuthenticationError: Authentication failed (401)
            CloudAPINotFoundError: Resource not found (404)
            CloudAPIServerError: Server error (500+)
            CloudAPITimeoutError: Request timeout
            CloudAPIConnectionError: Connection error
        """
        await self._ensure_client()

        # Add auth headers if required
        headers = kwargs.pop("headers", {})
        if auth_required:
            headers.update(self._get_auth_headers())

        try:
            logger.debug(f"{method} {endpoint}")
            response = await self._client.request(
                method,
                endpoint,
                headers=headers,
                **kwargs
            )

            # Handle error responses
            if response.status_code == 401:
                error_data = response.json() if response.content else {}
                raise CloudAPIAuthenticationError(
                    error_data.get("message", "Authentication failed"),
                    details=error_data
                )
            elif response.status_code == 403:
                error_data = response.json() if response.content else {}
                raise CloudAPIAuthenticationError(
                    error_data.get("message", "Access forbidden"),
                    details=error_data
                )
            elif response.status_code == 404:
                error_data = response.json() if response.content else {}
                raise CloudAPINotFoundError(
                    error_data.get("message", "Resource not found"),
                    details=error_data
                )
            elif response.status_code >= 500:
                error_data = response.json() if response.content else {}
                raise CloudAPIServerError(
                    error_data.get("message", "Server error"),
                    status_code=response.status_code,
                    details=error_data
                )

            response.raise_for_status()
            return response

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {endpoint}")
            raise CloudAPITimeoutError(
                f"Request timed out after {self.timeout}s",
                timeout=self.timeout
            ) from e
        except (httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(f"Connection error: {endpoint}")
            raise CloudAPIConnectionError(
                f"Failed to connect to {self.base_url}",
                url=self.base_url
            ) from e

    async def authenticate(self, api_key: str) -> CloudAuthResponse:
        """
        Authenticate with ZeroDB Cloud API using API key.

        Uses the API key directly via X-API-Key header (no token exchange needed).
        Validates the key by calling /v1/auth/me.

        Args:
            api_key: AINative platform API key (sk_...)

        Returns:
            CloudAuthResponse with auth confirmation

        Raises:
            CloudAPIAuthenticationError: Invalid API key
            CloudAPIConnectionError: Connection failed
        """
        logger.info("Authenticating with ZeroDB Cloud API via API key")

        self._api_key = api_key

        try:
            # Validate the key by listing API keys (supports X-API-Key auth)
            # Note: /v1/auth/me uses JWT-only auth, so we use /v1/api-keys instead
            response = await self._request(
                "GET",
                "/v1/api-keys",
                auth_required=True,
            )

            data = response.json()
            logger.info(
                f"Authentication successful. Account has {data.get('total', 0)} API keys."
            )

            # Return a CloudAuthResponse for backward compatibility
            return CloudAuthResponse(
                auth_token=api_key,
                expires_in=86400 * 365,  # API keys don't expire via time
            )

        except Exception as e:
            self._api_key = None
            logger.error(f"Authentication failed: {e}")
            raise

    async def upload_bundle(
        self,
        project_id: str,
        bundle_data: Dict[str, Any],
        bundle_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        compression: bool = True
    ) -> BundleUploadResponse:
        """
        Upload sync bundle to ZeroDB Cloud

        Args:
            project_id: Project ID in cloud
            bundle_data: Bundle data to upload
            bundle_name: Optional bundle name
            metadata: Optional metadata
            compression: Enable compression

        Returns:
            BundleUploadResponse with upload_id and bundle_id

        Raises:
            CloudAPIAuthenticationError: Not authenticated
            CloudAPIServerError: Upload failed
        """
        logger.info(f"Uploading bundle to project {project_id}")

        request = BundleUploadRequest(
            project_id=project_id,
            bundle_data=bundle_data,
            bundle_name=bundle_name,
            metadata=metadata or {},
            compression=compression
        )

        response = await self._request(
            "POST",
            f"/v1/projects/{project_id}/sync/import",
            json=request.model_dump()
        )

        upload_response = BundleUploadResponse(**response.json())

        logger.info(
            f"Bundle uploaded successfully: upload_id={upload_response.upload_id}, "
            f"bundle_id={upload_response.bundle_id}"
        )

        return upload_response

    async def download_bundle(
        self,
        project_id: str,
        bundle_id: str,
        include_metadata: bool = True
    ) -> BundleDownloadResponse:
        """
        Download sync bundle from ZeroDB Cloud

        Args:
            project_id: Project ID in cloud
            bundle_id: Bundle ID to download
            include_metadata: Include bundle metadata

        Returns:
            BundleDownloadResponse with bundle data

        Raises:
            CloudAPIAuthenticationError: Not authenticated
            CloudAPINotFoundError: Bundle not found
        """
        logger.info(f"Downloading bundle {bundle_id} from project {project_id}")

        response = await self._request(
            "GET",
            f"/v1/projects/{project_id}/sync/export/{bundle_id}",
            params={"include_metadata": include_metadata}
        )

        download_response = BundleDownloadResponse(**response.json())

        logger.info(
            f"Bundle downloaded successfully: bundle_id={download_response.bundle_id}, "
            f"size={download_response.size_bytes} bytes"
        )

        return download_response

    async def get_cloud_schema(self, project_id: str) -> Dict[str, Any]:
        """
        Get current schema from ZeroDB Cloud

        Args:
            project_id: Project ID in cloud

        Returns:
            Cloud schema data

        Raises:
            CloudAPIAuthenticationError: Not authenticated
            CloudAPINotFoundError: Project not found
        """
        logger.info(f"Fetching cloud schema for project {project_id}")

        response = await self._request(
            "GET",
            f"/v1/projects/{project_id}/schema"
        )

        schema_data = response.json()
        logger.info(f"Cloud schema retrieved for project {project_id}")

        return schema_data

    async def get_cloud_sync_state(self, project_id: str) -> CloudSyncStatus:
        """
        Get cloud sync state for a project

        Args:
            project_id: Project ID in cloud

        Returns:
            CloudSyncStatus with sync state

        Raises:
            CloudAPIAuthenticationError: Not authenticated
            CloudAPINotFoundError: Project not found
        """
        logger.info(f"Fetching cloud sync state for project {project_id}")

        response = await self._request(
            "GET",
            f"/v1/projects/{project_id}/sync/state"
        )

        sync_status = CloudSyncStatus(**response.json())

        logger.info(
            f"Cloud sync state retrieved: last_sync={sync_status.last_sync_at}"
        )

        return sync_status

    async def list_available_bundles(
        self,
        project_id: str,
        status_filter: Optional[BundleStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[BundleInfo]:
        """
        List available bundles in ZeroDB Cloud

        Args:
            project_id: Project ID in cloud
            status_filter: Optional filter by bundle status
            limit: Maximum bundles to return
            offset: Pagination offset

        Returns:
            List of BundleInfo objects

        Raises:
            CloudAPIAuthenticationError: Not authenticated
        """
        logger.info(f"Listing bundles for project {project_id}")

        params = {"limit": limit, "offset": offset}
        if status_filter:
            params["status"] = status_filter.value

        response = await self._request(
            "GET",
            f"/v1/projects/{project_id}/sync/bundles",
            params=params
        )

        bundles_response = ListBundlesResponse(**response.json())

        logger.info(
            f"Retrieved {len(bundles_response.bundles)} bundles "
            f"(total: {bundles_response.total})"
        )

        return bundles_response.bundles
