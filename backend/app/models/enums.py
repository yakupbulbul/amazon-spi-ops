from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"


class InventoryAlertStatus(StrEnum):
    HEALTHY = "healthy"
    LOW = "low"
    CRITICAL = "critical"
    OUT_OF_STOCK = "out_of_stock"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DraftStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    READY_TO_PUBLISH = "ready_to_publish"
    PUBLISHED = "published"
    FAILED = "failed"


class JobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CatalogImportStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProductSource(StrEnum):
    SAMPLE = "sample"
    AMAZON_LISTING = "amazon_listing"
