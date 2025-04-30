"""Custom exception types for the Narratix application."""

class NarratixError(Exception):
    """Base class for exceptions in Narratix."""
    pass

class ConfigurationError(NarratixError):
    """Exception raised for errors in configuration."""
    pass

class DomainError(NarratixError):
    """Exception raised for errors related to domain logic."""
    pass

class InfrastructureError(NarratixError):
    """Exception raised for errors in the infrastructure layer (e.g., database, external APIs)."""
    pass

class ValidationError(DomainError):
    """Exception raised for data validation errors within domain entities or value objects."""
    pass

class NotFoundError(InfrastructureError):
    """Exception raised when a requested resource is not found (e.g., entity in DB)."""
    pass 