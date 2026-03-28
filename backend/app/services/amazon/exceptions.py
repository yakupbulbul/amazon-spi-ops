class AmazonIntegrationError(Exception):
    """Base exception for Amazon integration failures."""


class AmazonAuthorizationError(AmazonIntegrationError):
    """Raised when LWA or AWS credentials are missing or rejected."""


class AmazonRequestError(AmazonIntegrationError):
    """Raised when an SP-API request fails."""
