"""
Dependency Injection Module.

This module provides factory functions for FastAPI Depends() to inject
dependencies into API endpoints. It ensures proper initialization and
provides singletons where appropriate.
"""

import sqlite3
from typing import Generator

from src.config.settings import settings
from src.modules.invoices.generator import InvoiceGenerator
from src.modules.invoices.repository import InvoiceRepository
from src.modules.invoices.service import InvoiceService
from src.modules.transfers.handler import TransferHandler
from src.modules.transfers.repository import TransferRepository
from src.modules.transfers.service import TransferService
from src.modules.webhooks.invoice_processor import InvoiceWebhookProcessor
from src.modules.webhooks.receiver import WebhookReceiver
from src.modules.webhooks.transfer_processor import TransferWebhookProcessor
from src.modules.webhooks.validator import WebhookValidator
from src.shared.database.connection import DatabaseConnection
from src.shared.events.bus import EventBus
from src.shared.stark.client import StarkBankClient
from src.shared.stark.invoice_api import StarkInvoiceAPI
from src.shared.stark.transfer_api import StarkTransferAPI
from src.shared.utils.logger import get_logger

logger = get_logger("dependencies")

# Singleton instances
_db_connection: DatabaseConnection = None
_event_bus: EventBus = None
_stark_client: StarkBankClient = None


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Get database connection for FastAPI Depends.

    Yields:
        sqlite3.Connection: Database connection
    """
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
        logger.info("Database connection initialized")
    
    with _db_connection.get_db() as conn:
        yield conn


def get_event_bus() -> EventBus:
    """
    Get EventBus singleton for FastAPI Depends.

    Returns:
        EventBus: Event bus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        logger.info("EventBus initialized")
    
    return _event_bus


def get_stark_client() -> StarkBankClient:
    """
    Get StarkBankClient singleton for FastAPI Depends.

    Returns:
        StarkBankClient: Stark Bank client instance
    """
    global _stark_client
    if _stark_client is None:
        _stark_client = StarkBankClient()
        logger.info("StarkBankClient initialized")
    
    return _stark_client


def get_stark_invoice_api() -> StarkInvoiceAPI:
    """
    Get StarkInvoiceAPI instance for FastAPI Depends.

    Returns:
        StarkInvoiceAPI: Stark Bank invoice API instance
    """
    return StarkInvoiceAPI()


def get_stark_transfer_api() -> StarkTransferAPI:
    """
    Get StarkTransferAPI instance for FastAPI Depends.

    Returns:
        StarkTransferAPI: Stark Bank transfer API instance
    """
    return StarkTransferAPI()


def get_invoice_repository() -> InvoiceRepository:
    """
    Get InvoiceRepository instance for FastAPI Depends.

    Returns:
        InvoiceRepository: Invoice repository instance
    """
    return InvoiceRepository()


def get_invoice_generator() -> InvoiceGenerator:
    """
    Get InvoiceGenerator instance for FastAPI Depends.

    Returns:
        InvoiceGenerator: Invoice generator instance
    """
    return InvoiceGenerator()


def get_invoice_service() -> InvoiceService:
    """
    Get InvoiceService instance for FastAPI Depends.

    Returns:
        InvoiceService: Invoice service instance
    """
    repository = get_invoice_repository()
    stark_api = get_stark_invoice_api()
    event_bus = get_event_bus()
    
    return InvoiceService(
        repository=repository,
        stark_api=stark_api,
        event_bus=event_bus
    )


def get_transfer_repository() -> TransferRepository:
    """
    Get TransferRepository instance for FastAPI Depends.

    Returns:
        TransferRepository: Transfer repository instance
    """
    return TransferRepository()


def get_transfer_service() -> TransferService:
    """
    Get TransferService instance for FastAPI Depends.

    Returns:
        TransferService: Transfer service instance
    """
    repository = get_transfer_repository()
    stark_api = get_stark_transfer_api()
    event_bus = get_event_bus()
    
    return TransferService(
        repository=repository,
        stark_api=stark_api,
        event_bus=event_bus
    )


def get_webhook_validator() -> WebhookValidator:
    """
    Get WebhookValidator instance for FastAPI Depends.

    Returns:
        WebhookValidator: Webhook validator instance
    """
    return WebhookValidator()


def get_webhook_receiver() -> WebhookReceiver:
    """
    Get WebhookReceiver instance for FastAPI Depends.

    Returns:
        WebhookReceiver: Webhook receiver instance
    """
    validator = get_webhook_validator()
    invoice_processor = InvoiceWebhookProcessor(
        invoice_repository=get_invoice_repository(),
        event_bus=get_event_bus()
    )
    transfer_processor = TransferWebhookProcessor(
        transfer_repository=get_transfer_repository(),
        event_bus=get_event_bus()
    )
    event_bus = get_event_bus()
    
    return WebhookReceiver(
        validator=validator,
        invoice_processor=invoice_processor,
        transfer_processor=transfer_processor,
        event_bus=event_bus
    )


def initialize_event_handlers() -> None:
    """
    Initialize and register all event handlers.

    This should be called during application startup to ensure
    all event handlers are properly registered with the EventBus.
    """
    logger.info("Initializing event handlers")
    
    event_bus = get_event_bus()
    invoice_repository = get_invoice_repository()
    transfer_service = get_transfer_service()
    
    # Initialize and register TransferHandler
    transfer_handler = TransferHandler(
        service=transfer_service,
        invoice_repository=invoice_repository
    )
    
    # Subscribe the handler to invoice.paid events
    event_bus.subscribe("invoice.paid", transfer_handler.handle_invoice_paid)
    
    logger.info("Event handlers initialized and registered")


def cleanup() -> None:
    """
    Cleanup resources on application shutdown.

    This should be called during application shutdown to ensure
    all resources are properly released.
    """
    global _db_connection, _event_bus, _stark_client
    
    logger.info("Cleaning up dependencies")
    
    # Close database connection
    if _db_connection and _db_connection._connection:
        _db_connection._connection.close()
        logger.info("Database connection closed")
    
    # Reset singletons
    _db_connection = None
    _event_bus = None
    _stark_client = None
    
    logger.info("Cleanup completed")
