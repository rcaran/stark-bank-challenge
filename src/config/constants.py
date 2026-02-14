from enum import Enum


class InvoiceStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    CANCELED = "canceled"
    OVERDUE = "overdue"
    VOIDED = "voided"

class TransferStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"

class EventType(str, Enum):
    INVOICE_CREATED = "invoice.created"
    INVOICE_PAID = "invoice.paid"
    INVOICE_FAILED = "invoice.failed"
    TRANSFER_CREATED = "transfer.created"
    TRANSFER_COMPLETED = "transfer.completed"
    TRANSFER_FAILED = "transfer.failed"
    WEBHOOK_RECEIVED = "webhook.received"
    WEBHOOK_VALIDATION_FAILED = "webhook.validation.failed"

class LogType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"

PROJECT_NAME = "stark-bank-challenge"
DEFAULT_PAGE_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

STARKBANK_ENVIRONMENT_SANDBOX = "sandbox"
STARKBANK_ENVIRONMENT_PRODUCTION = "production"
