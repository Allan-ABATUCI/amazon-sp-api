"""
Amazon Selling Partner API (SP-API) - Configuration
────────────────────────────────────────────────────

Variables d'environnement requises :
  - AMAZON_REFRESH_TOKEN_PROD
  - AMAZON_CLIENT_ID_PROD
  - AMAZON_CLIENT_SECRET_PROD
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────
# Credentials (depuis .env)
# ─────────────────────────────────────────────────────────────

REFRESH_TOKEN = os.getenv("AMAZON_REFRESH_TOKEN_PROD", "").strip()
CLIENT_ID     = os.getenv("AMAZON_CLIENT_ID_PROD", "").strip()
CLIENT_SECRET = os.getenv("AMAZON_CLIENT_SECRET_PROD", "").strip()

_missing = [k for k, v in {
    "AMAZON_REFRESH_TOKEN_PROD": REFRESH_TOKEN,
    "AMAZON_CLIENT_ID_PROD":     CLIENT_ID,
    "AMAZON_CLIENT_SECRET_PROD": CLIENT_SECRET,
}.items() if not v]
if _missing:
    raise EnvironmentError(
        f"Variables d'environnement manquantes : {_missing}"
    )


# ─────────────────────────────────────────────────────────────
# URLs et configuration Amazon
# ─────────────────────────────────────────────────────────────

SP_API_ENDPOINTS = {
    "EU": "https://sellingpartnerapi-eu.amazon.com",
    "NA": "https://sellingpartnerapi-na.amazon.com",
}

MARKETPLACE_REGIONS = {
    "FR": "EU", "DE": "EU", "UK": "EU", "IT": "EU", "ES": "EU", "BE": "EU",
    "US": "NA", "CA": "NA", "MX": "NA",
}

LWA_TOKEN_URL   = "https://api.amazon.com/auth/o2/token"
RDT_TOKEN_URL   = "https://sellingpartnerapi-eu.amazon.com/tokens/2021-03-01/restrictedDataToken"
JSON_OUTPUT_DIR = Path("/home/stagiaires/scripts/amazon/api_responses")

MARKETPLACE_IDS = {
    # Europe
    "FR": "A13V1IB3VIYZZH",
    "DE": "A1PA6795UKMFR9",
    "UK": "A1F83G8C2ARO7P",
    "IT": "APJ6JRA9NG5V4",
    "ES": "A1RKKUPIHCS9HS",
    "BE": "AMEN7PMS3EDWL",
    # Amérique du Nord
    "US": "ATVPDKIKX0DER",
    "CA": "A2EUQ1WTGCTBG2",
    "MX": "A1AM78C64UM0Y8",
}


# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)