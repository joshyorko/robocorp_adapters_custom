"""Test package for robocorp_adapters_custom.

This package ensures that robocorp_adapters_custom is imported before tests run,
setting up necessary module mappings for drop-in compatibility.
"""

# Import the package to set up sys.modules mappings for robocorp.workitems._adapters.*
import robocorp_adapters_custom  # noqa: F401
