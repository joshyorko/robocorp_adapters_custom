"""Type definitions and constants for custom adapters.

This module provides type aliases and constants that are compatible with
robocorp.workitems to enable drop-in replacement functionality.
"""

from enum import Enum
from typing import Any

# TTL for Redis keys (1 week in seconds)
TTL_WEEK_SECONDS = 604800  # 7 * 24 * 60 * 60


class State(str, Enum):
    """Work item lifecycle states.
    
    These states match the robocorp.workitems.State enum to ensure
    compatibility when using custom adapters.
    """
    
    DONE = "COMPLETED"  # Terminal state: work item successfully processed
    FAILED = "FAILED"   # Terminal state: work item processing failed
    
    @property
    def value(self) -> str:
        """Get string value of state.
        
        Returns:
            String representation of state
        """
        return super().value


# Type alias for JSON-serializable data
JSONType = dict[str, Any] | list | str | int | float | bool | None
