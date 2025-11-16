"""Yorko Control Room adapter for connecting robots to self-hosted Control Room.

This module implements a custom work item adapter that connects to Yorko Control Room
via HTTP REST API, enabling robots to interact with the centralized control room backend.

Features:
- RESTful API integration with authentication
- Compatible with Robocorp workitems library interface
- Support for work item queue management
- File attachment handling via API
- Full state lifecycle management
- Multi-workspace support

Usage:
    from robocorp.workitems import Inputs

    # Set environment variables
    os.environ["RC_WORKITEM_ADAPTER"] = "robocorp_adapters_custom._yorko_control_room.YorkoControlRoomAdapter"
    os.environ["YORKO_API_URL"] = "https://control-room.example.com"
    os.environ["YORKO_API_TOKEN"] = "your-api-token"
    os.environ["YORKO_WORKSPACE_ID"] = "workspace-uuid"
    os.environ["YORKO_WORKER_ID"] = "robot-worker-1"

    # Use work items as normal
    for item in Inputs:
        # Process work item...
        item.save()
"""

import logging
from typing import Optional
from urllib.parse import urljoin

from robocorp.workitems._adapters._base import BaseAdapter
from robocorp.workitems._exceptions import EmptyQueue
from robocorp.workitems._types import State
from robocorp.workitems._utils import JSONType, required_env

# Import requests with fallback for environments without it
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError as err:
    raise ImportError(
        "The YorkoControlRoomAdapter requires the 'requests' library. "
        "Install it with: pip install requests"
    ) from err

LOGGER = logging.getLogger(__name__)
ENCODING = "utf-8"


class YorkoControlRoomAdapter(BaseAdapter):
    """Adapter for connecting robots to Yorko Control Room via REST API.

    Required environment variables:

    * YORKO_API_URL:           Base URL of Yorko Control Room (e.g., https://control-room.example.com)
    * YORKO_API_TOKEN:         API authentication token for the workspace
    * YORKO_WORKSPACE_ID:      Workspace UUID
    * YORKO_WORKER_ID:         Worker/robot identifier (unique per robot instance)

    Optional environment variables:

    * YORKO_PROCESS_RUN_ID:    Process run ID for tracking (optional)
    * YORKO_REQUEST_TIMEOUT:   HTTP request timeout in seconds (default: 30)

    lazydocs: ignore
    """

    def __init__(self) -> None:
        """Initialize the Yorko Control Room adapter."""
        # Load required configuration
        self.api_url = required_env("YORKO_API_URL").rstrip("/")
        self.api_token = required_env("YORKO_API_TOKEN")
        self.workspace_id = required_env("YORKO_WORKSPACE_ID")
        self.worker_id = required_env("YORKO_WORKER_ID")

        # Optional configuration
        self.process_run_id = self._get_env("YORKO_PROCESS_RUN_ID")
        self.timeout = int(self._get_env("YORKO_REQUEST_TIMEOUT", "30"))

        # Initialize HTTP session with retry logic
        self.session = self._init_session()

        # Track current work item
        self._current_item_id: Optional[str] = None

        LOGGER.info(
            "YorkoControlRoomAdapter initialized: url=%s, workspace=%s, worker=%s",
            self.api_url,
            self.workspace_id,
            self.worker_id,
        )

    def _get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable with optional default."""
        import os

        return os.getenv(key, default)

    def _init_session(self) -> requests.Session:
        """Initialize requests session with retry logic and default headers."""
        session = requests.Session()

        # Configure retry strategy for transient failures
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST", "PATCH"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update(
            {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "YorkoControlRoomAdapter/1.0",
            }
        )

        return session

    def _url(self, *parts: str) -> str:
        """Construct full API URL from parts."""
        path = "/".join(str(part) for part in parts)
        return urljoin(self.api_url + "/", path)

    def _handle_response(self, response: requests.Response) -> requests.Response:
        """Handle HTTP response and raise appropriate exceptions."""
        try:
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            LOGGER.error(
                "HTTP error: status=%s, url=%s, response=%s",
                response.status_code,
                response.url,
                response.text[:500],
            )
            raise

    def reserve_input(self) -> str:
        """Reserve and return the next available work item ID from the queue.

        Returns:
            str: Work item ID

        Raises:
            EmptyQueue: If no work items are available in the queue
        """
        url = self._url(
            "api/v1/workspaces",
            self.workspace_id,
            "work-items/next",
        )

        params = {"worker_id": self.worker_id}

        LOGGER.info("Reserving next work item from: %s", url)

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            self._handle_response(response)

            data = response.json()

            # Handle empty queue (API returns None or empty object)
            if not data or data.get("id") is None:
                raise EmptyQueue("No work items available in the queue")

            item_id = data["id"]
            self._current_item_id = item_id

            LOGGER.info("Reserved work item: %s", item_id)
            return item_id

        except requests.RequestException as e:
            LOGGER.error("Failed to reserve work item: %s", e)
            raise

    def release_input(
        self, item_id: str, state: State, exception: Optional[dict] = None
    ):
        """Release a work item back to the Control Room with final state.

        Args:
            item_id: Work item ID to release
            state: Final state (DONE or FAILED)
            exception: Exception details if state is FAILED
        """
        if state == State.DONE:
            url = self._url(
                "api/v1/workspaces",
                self.workspace_id,
                "work-items",
                item_id,
                "complete",
            )
            body = {
                "worker_id": self.worker_id,
                "output_data": {},  # Can be extended to include output data
            }
            log_level = logging.INFO
        else:  # State.FAILED
            url = self._url(
                "api/v1/workspaces",
                self.workspace_id,
                "work-items",
                item_id,
                "fail",
            )

            # Process exception data
            error_message = "Unknown error"
            exception_data = {}

            if exception:
                # Clean up exception data (remove None and empty values)
                cleaned_exception = {}
                for key, value in exception.items():
                    value_str = str(value).strip() if value else None
                    if value_str:
                        cleaned_exception[key] = value_str

                error_message = cleaned_exception.get(
                    "message", cleaned_exception.get("type", "Unknown error")
                )
                exception_data = cleaned_exception

            body = {
                "worker_id": self.worker_id,
                "error_message": error_message,
                "exception_data": exception_data,
            }
            log_level = logging.ERROR

        LOGGER.log(
            log_level,
            "Releasing %s work item %s to: %s",
            state.value,
            item_id,
            url,
        )

        try:
            response = self.session.post(url, json=body, timeout=self.timeout)
            self._handle_response(response)
            LOGGER.info("Successfully released work item: %s", item_id)

        except requests.RequestException as e:
            LOGGER.error("Failed to release work item %s: %s", item_id, e)
            raise

    def create_output(self, parent_id: str, payload: Optional[JSONType] = None) -> str:
        """Create an output work item linked to the parent (input) work item.

        Args:
            parent_id: Parent work item ID
            payload: Output work item payload data

        Returns:
            str: Created output work item ID
        """
        url = self._url(
            "api/v1/workspaces",
            self.workspace_id,
            "work-items",
        )

        body = {
            "name": f"Output from {parent_id}",
            "payload": payload or {},
            "parent_id": parent_id,  # Link to parent work item
        }

        LOGGER.info("Creating output work item: %s", url)

        try:
            response = self.session.post(url, json=body, timeout=self.timeout)
            self._handle_response(response)

            data = response.json()
            output_id = data["id"]

            LOGGER.info("Created output work item: %s", output_id)
            return output_id

        except requests.RequestException as e:
            LOGGER.error("Failed to create output work item: %s", e)
            raise

    def load_payload(self, item_id: str) -> JSONType:
        """Load the payload data for a work item.

        Args:
            item_id: Work item ID

        Returns:
            JSONType: Work item payload data (may be empty dict if no payload)
        """
        url = self._url(
            "api/v1/workspaces",
            self.workspace_id,
            "work-items",
            item_id,
        )

        LOGGER.info("Loading work item payload from: %s", url)

        try:
            response = self.session.get(url, timeout=self.timeout)

            # Handle 404 as empty payload (work item exists but has no payload)
            if response.status_code == 404:
                LOGGER.warning("Work item %s not found, returning empty payload", item_id)
                return {}

            self._handle_response(response)

            data = response.json()
            payload = data.get("payload", {})

            LOGGER.debug("Loaded payload for work item %s", item_id)
            return payload

        except requests.RequestException as e:
            LOGGER.error("Failed to load payload for work item %s: %s", item_id, e)
            raise

    def save_payload(self, item_id: str, payload: JSONType):
        """Save/update the payload data for a work item.

        Args:
            item_id: Work item ID
            payload: New payload data to save
        """
        url = self._url(
            "api/v1/workspaces",
            self.workspace_id,
            "work-items",
            item_id,
        )

        body = {"payload": payload}

        LOGGER.info("Saving work item payload to: %s", url)

        try:
            response = self.session.patch(url, json=body, timeout=self.timeout)
            self._handle_response(response)

            LOGGER.debug("Saved payload for work item %s", item_id)

        except requests.RequestException as e:
            LOGGER.error("Failed to save payload for work item %s: %s", item_id, e)
            raise

    def list_files(self, item_id: str) -> list[str]:
        """List all file names attached to a work item.

        Args:
            item_id: Work item ID

        Returns:
            list[str]: List of file names
        """
        # Work item files are stored in the payload under a 'files' key
        # This is a simplified implementation - adjust based on your backend's file handling
        payload = self.load_payload(item_id)
        files = payload.get("files", [])

        # Handle both list of strings and list of dicts
        if files and isinstance(files[0], dict):
            file_names = [f["name"] for f in files if "name" in f]
        else:
            file_names = [str(f) for f in files]

        LOGGER.info("Listed %d files for work item %s", len(file_names), item_id)
        return file_names

    def get_file(self, item_id: str, name: str) -> bytes:
        """Download a file attached to a work item.

        Args:
            item_id: Work item ID
            name: File name to download

        Returns:
            bytes: File content
        """
        # This is a placeholder implementation
        # Your Control Room backend needs to implement file download endpoints
        url = self._url(
            "api/v1/workspaces",
            self.workspace_id,
            "work-items",
            item_id,
            "files",
            name,
        )

        LOGGER.info("Downloading file %s from work item %s: %s", name, item_id, url)

        try:
            response = self.session.get(url, timeout=self.timeout)
            self._handle_response(response)

            LOGGER.info("Downloaded file %s (%d bytes)", name, len(response.content))
            return response.content

        except requests.RequestException as e:
            LOGGER.error("Failed to download file %s from work item %s: %s", name, item_id, e)
            raise

    def add_file(self, item_id: str, name: str, content: bytes):
        """Upload a file to attach to a work item.

        Args:
            item_id: Work item ID
            name: File name
            content: File content as bytes
        """
        # This is a placeholder implementation
        # Your Control Room backend needs to implement file upload endpoints
        url = self._url(
            "api/v1/workspaces",
            self.workspace_id,
            "work-items",
            item_id,
            "files",
        )

        LOGGER.info(
            "Uploading file %s to work item %s: %s (size: %d bytes)",
            name,
            item_id,
            url,
            len(content),
        )

        try:
            # Use multipart/form-data for file upload
            files = {"file": (name, content)}
            # Temporarily remove Content-Type header for multipart upload
            headers = {"Authorization": f"Bearer {self.api_token}"}

            response = self.session.post(
                url,
                files=files,
                headers=headers,
                timeout=self.timeout,
            )
            self._handle_response(response)

            LOGGER.info("Uploaded file %s to work item %s", name, item_id)

        except requests.RequestException as e:
            LOGGER.error("Failed to upload file %s to work item %s: %s", name, item_id, e)
            raise

    def remove_file(self, item_id: str, name: str):
        """Remove a file attached to a work item.

        Args:
            item_id: Work item ID
            name: File name to remove
        """
        # This is a placeholder implementation
        # Your Control Room backend needs to implement file deletion endpoints
        url = self._url(
            "api/v1/workspaces",
            self.workspace_id,
            "work-items",
            item_id,
            "files",
            name,
        )

        LOGGER.info("Removing file %s from work item %s: %s", name, item_id, url)

        try:
            response = self.session.delete(url, timeout=self.timeout)
            self._handle_response(response)

            LOGGER.info("Removed file %s from work item %s", name, item_id)

        except requests.RequestException as e:
            LOGGER.error("Failed to remove file %s from work item %s: %s", name, item_id, e)
            raise
