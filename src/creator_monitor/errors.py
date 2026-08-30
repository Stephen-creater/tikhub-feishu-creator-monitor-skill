"""Typed failures used by the creator monitoring runtime."""


class CreatorMonitorError(RuntimeError):
    """Base class for expected operational failures."""


class ConfigurationError(CreatorMonitorError):
    """Configuration is missing or invalid."""


class BudgetExceeded(CreatorMonitorError):
    """A TikHub call would exceed a configured safety limit."""
