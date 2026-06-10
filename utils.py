"""
Amazon Selling Partner API (SP-API) - Fonctions utilitaires
────────────────────────────────────────────────────────────
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from .config import JSON_OUTPUT_DIR

logger = logging.getLogger(__name__)


def save_json(data: dict | list, label: str) -> Path:
    """Sauvegarde data en JSON horodaté dans api_responses/."""
    JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts         = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_label = label.replace("/", "_").replace(" ", "_").strip("_")
    filepath   = JSON_OUTPUT_DIR / f"{safe_label}_{ts}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Sauvegardé → %s", filepath)
    return filepath


def _parse_money(raw: dict | None) -> dict:
    """Normalise un bloc Amazon {Amount, CurrencyCode}."""
    if not raw:
        return {"amount": "0.00", "currency": "EUR"}
    return {
        "amount":   raw.get("Amount", "0.00"),
        "currency": raw.get("CurrencyCode", "EUR"),
    }