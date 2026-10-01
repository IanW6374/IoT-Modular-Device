"""IoT-MD V3 native service adapters.

The package deliberately performs no eager imports. Device code imports only
the adapter it needs, which keeps startup allocation bounded and prevents
retired transition components from becoming accidental runtime dependencies.
"""

__all__ = ()
