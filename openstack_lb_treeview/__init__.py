"""OpenStack Load Balancer Tree View Package"""

try:
    from ._version import version as __version__
except ImportError:
    # Fallback if version file doesn't exist (e.g., during development)
    __version__ = "dev"

__all__ = ["__version__"]

