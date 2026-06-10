"""
Amazon Selling Partner API (SP-API) - Orders API v2026-01-01
─────────────────────────────────────────────────────────────

Nouvelle version : PII sans Restricted Data Token.
Nécessite le rôle "Direct-to-Consumer Shipping" pour les données PII.

includedData : BUYER, RECIPIENT, PROCEEDS, EXPENSE, PROMOTION,
               CANCELLATION, FULFILLMENT, PACKAGES
"""

import time
import logging
from datetime import datetime, timezone
from datetime import timedelta

from .client import SPAPIClient
from .exceptions import RateLimitError, NetworkError, ServerError

logger = logging.getLogger(__name__)


class Orders:
    """Orders API v2026-01-01."""

    BASE_PATH = "/orders/2026-01-01"
    RATE_LIMIT_DELAY = 2.0

    def __init__(self, client: SPAPIClient):
        self.client = client

    # ── searchOrders ─────────────────────────────

    def search_orders_raw(self, created_after: str | None = None,
                          created_before: str | None = None,
                          last_updated_after: str | None = None,
                          order_statuses: list[str] | None = None,
                          included_data: list[str] | None = None,
                          max_results: int = 100) -> dict:
        if created_after is None and last_updated_after is None:
            now = datetime.now(timezone.utc)
            created_after = datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()

        params: dict = {
            "marketplaceIds": self.client.marketplace_id,
            "maxResults":     max_results,
        }
        if created_after:
            params["createdAfter"] = created_after
        if created_before:
            params["createdBefore"] = created_before
        if last_updated_after:
            params["lastUpdatedAfter"] = last_updated_after
        if order_statuses:
            params["orderStatuses"] = ",".join(order_statuses)
        if included_data:
            params["includedData"] = ",".join(included_data)

        return self.client.get(f"{self.BASE_PATH}/orders", params=params)

    def search_orders_db(self, created_after: str | None = None,
                         order_statuses: list[str] | None = None,
                         include_pii: bool = True) -> list[dict]:
        included = ["PROCEEDS"]
        if include_pii:
            included.extend(["BUYER", "RECIPIENT"])

        raw = self.search_orders_raw(created_after=created_after,
                                     order_statuses=order_statuses,
                                     included_data=included)
        return [self._order_to_db(o) for o in raw.get("orders", [])]

    # ── getOrder ─────────────────────────────────

    def get_order_raw(self, order_id: str,
                      included_data: list[str] | None = None) -> dict:
        params: dict = {}
        if included_data:
            params["includedData"] = ",".join(included_data)
        return self.client.get(f"{self.BASE_PATH}/orders/{order_id}", params=params)

    def get_order_full_raw(self, order_id: str) -> dict:
        return self.get_order_raw(order_id, included_data=[
            "BUYER", "RECIPIENT", "PROCEEDS", "EXPENSE",
            "PROMOTION", "FULFILLMENT", "PACKAGES",
        ])

    def get_order_db(self, order_id: str, include_pii: bool = True) -> dict:
        included = ["PROCEEDS"]
        if include_pii:
            included.extend(["BUYER", "RECIPIENT"])
        raw = self.get_order_raw(order_id, included_data=included)
        return self._order_to_db(raw)

    # ── Pagination complète ──────────────────────

    def get_all_orders_raw(self, created_after=None, created_before=None,
                        order_statuses=None, included_data=None,
                        chunk_days=7) -> list[dict]:
        all_orders: list[dict] = []

        start = datetime.fromisoformat(created_after) if created_after else datetime.now(timezone.utc).replace(day=1)
        end   = datetime.fromisoformat(created_before) if created_before else datetime.now(timezone.utc)

        def fetch_window(w_start, w_end, current_chunk):
            raw = self.search_orders_raw(
                created_after=w_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                created_before=w_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                order_statuses=order_statuses,
                included_data=included_data,
                max_results=100,
            )
            orders = raw.get("orders", [])
            has_more = bool(raw.get("pagination", {}).get("nextToken"))

            if has_more and current_chunk > 1:
                # Window too dense — split it in half and retry
                logger.warning("Fenêtre %s→%s trop dense, découpage en 2.", w_start.date(), w_end.date())
                mid = w_start + (w_end - w_start) / 2
                fetch_window(w_start, mid, current_chunk // 2)
                fetch_window(mid, w_end, current_chunk // 2)
            else:
                if has_more:
                    logger.error("Fenêtre %s→%s a encore des pages — chunk_days trop grand !", w_start.date(), w_end.date())
                all_orders.extend(orders)

        cursor = start
        while cursor < end:
            w_end = min(cursor + timedelta(days=chunk_days), end)
            fetch_window(cursor, w_end, chunk_days)
            cursor = w_end
            time.sleep(self.RATE_LIMIT_DELAY)

        logger.info("Total commandes : %d", len(all_orders))
        return all_orders

    def get_all_orders_db(self, created_after: str | None = None,
                          order_statuses: list[str] | None = None,
                          include_pii: bool = True) -> list[dict]:
        included = ["PROCEEDS"]
        if include_pii:
            included.extend(["BUYER", "RECIPIENT"])

        raw_orders = self.get_all_orders_raw(created_after=created_after,
                                             order_statuses=order_statuses,
                                             included_data=included)
        return [self._order_to_db(o) for o in raw_orders]

    # ── Conversion DB ────────────────────────────

    @staticmethod
    def _order_to_db(o: dict) -> dict:
        buyer     = o.get("buyer", {})
        recipient = o.get("recipient", {})
        address   = recipient.get("address", {})
        proceeds  = o.get("proceeds", {})
        items     = o.get("orderItems", [])

        full_name   = recipient.get("name", "") or buyer.get("name", "")
        name_parts  = full_name.rsplit(" ", 1) if full_name else ["", ""]
        prenom      = name_parts[0] if len(name_parts) > 1 else full_name
        nom         = name_parts[1] if len(name_parts) > 1 else ""

        proceeds_total = proceeds.get("proceedsTotal", {})
        quantite_totale    = sum(item.get("quantity", 0) for item in items)
        nb_lignes_commande = len(items)

        return {
            "id_commande":         o.get("orderId", ""),
            "statut":              o.get("orderStatus", ""),
            "date_creation":       o.get("createdTime", ""),
            "prix_commande": {
                "amount":   proceeds_total.get("amount", ""),
                "currency": proceeds_total.get("currencyCode", ""),
            },
            "nom":                 nom,
            "prenom":              prenom,
            "adresse":             address.get("addressLine1", ""),
            "adresse_ligne_2":     address.get("addressLine2", ""),
            "code_postal":         address.get("postalCode", ""),
            "ville":               address.get("city", ""),
            "pays":                address.get("countryCode", ""),
            "telephone":           address.get("phone", recipient.get("phone", "")),
            "entreprise":          address.get("companyName", buyer.get("companyName", "")),
            "email":               buyer.get("email", ""),
            "quantite_totale":     quantite_totale,
            "nb_lignes_commande":  nb_lignes_commande,
            "marketplace_id":      o.get("marketplaceId", ""),
            "sales_channel":       o.get("salesChannel", ""),
        }
