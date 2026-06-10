"""
Amazon Selling Partner API (SP-API) Client
══════════════════════════════════════════

Package modulaire :
  config.py      → Configuration et credentials
  exceptions.py  → Exceptions typées
  utils.py       → Utilitaires (save_json, _parse_money)
  auth.py        → TokenManager (LWA)
  client.py      → SPAPIClient (HTTP avec retry)
  orders.py      → Orders (v2026-01-01, PII sans RDT)
  customer.py    → CustomerAPI
  catalog.py     → CatalogAPI (Listings + Catalog Items + Reports + Search)
  loaders.py     → Import CSV Seller Central
"""

# Config
from .config import (
    MARKETPLACE_IDS,
    MARKETPLACE_REGIONS,
    SP_API_ENDPOINTS,
    LWA_TOKEN_URL,
    JSON_OUTPUT_DIR,
)

# Exceptions
from .exceptions import (
    SPAPIError,
    RateLimitError,
    AuthError,
    ServerError,
    NetworkError,
    ReportError,
)

# Utils
from .utils import save_json, _parse_money

# Auth
from .auth import TokenManager, token_manager

# Client HTTP
from .client import SPAPIClient

# Orders
from .orders import Orders

# Customer
from .customer import CustomerAPI

# Catalog & Listings
from .catalog import CatalogAPI

# Loaders
from .loaders import load_skus_from_seller_central_export

__version__ = "3.0.0"

__all__ = [
    # Config
    "MARKETPLACE_IDS", "MARKETPLACE_REGIONS", "SP_API_ENDPOINTS",
    "LWA_TOKEN_URL", "JSON_OUTPUT_DIR",
    # Exceptions
    "SPAPIError", "RateLimitError", "AuthError",
    "ServerError", "NetworkError", "ReportError",
    # Utils
    "save_json", "_parse_money",
    # Auth
    "TokenManager", "token_manager",
    # Client
    "SPAPIClient",
    # Orders
    "Orders",
    # Customer
    "CustomerAPI",
    # Catalog
    "CatalogAPI",
    # Loaders
    "load_skus_from_seller_central_export",
]