"""
Invoices Module.

This module provides invoice management functionality including:
- InvoiceModel: Data model for invoices
- InvoiceRepository: Database operations
- InvoiceService: Business logic
- InvoiceGenerator: Batch invoice generation
- invoice_router: FastAPI endpoints
"""

from src.modules.invoices.api import invoice_router
from src.modules.invoices.generator import InvoiceGenerator
from src.modules.invoices.models import InvoiceModel, InvoiceStatus
from src.modules.invoices.repository import InvoiceRepository
from src.modules.invoices.service import InvoiceService

__all__ = [
    "InvoiceGenerator",
    "InvoiceModel",
    "InvoiceRepository",
    "InvoiceService",
    "InvoiceStatus",
    "invoice_router",
]
