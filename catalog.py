"""
Amazon Selling Partner API (SP-API) - Catalog & Listings
─────────────────────────────────────────────────────────

Listings Items API + Catalog Items API + Reports API
"""

import time
import json
import logging
import requests

from .client import SPAPIClient
from .exceptions import (
    SPAPIError, AuthError, RateLimitError,
    NetworkError, ServerError, ReportError,
)

logger = logging.getLogger(__name__)


class CatalogAPI:
    """
    Récupère les listings du vendeur et les infos produit détaillées
    via Listings Items API + Catalog Items API.
    """

    RATE_LIMIT_DELAY = 0.012  # ~83 req/s (limite Amazon : 100/s pour Listings)

    def __init__(self, client: SPAPIClient, seller_id: str):
        self.client    = client
        self.seller_id = seller_id

    # ─── Listings Items API ──────────────────────

    def get_listings_raw(self, sku: str, include_all: bool = True) -> dict:
        """
        Renvoie le listing brut pour un SKU donné.
        Inclut : summaries, attributes, issues, offers, fulfillmentAvailability, procurement.
        """
        path = f"/listings/2021-08-01/items/{self.seller_id}/{sku}"
        params = {
            "marketplaceIds": self.client.marketplace_id,
            "includedData":   "summaries,attributes,issues,offers,fulfillmentAvailability,procurement",
        }
        if include_all:
            params["issueLocale"] = "fr_FR"
        return self.client.get(path, params=params)

    def get_listings_db(self, sku: str) -> dict:
        raw = self.get_listings_raw(sku)
        return self._listing_to_db(raw)

    @staticmethod
    def _listing_to_db(raw: dict) -> dict:
        summaries = raw.get("summaries", [])
        summary   = summaries[0] if summaries else {}
        offers    = raw.get("offers", [])
        offer     = offers[0] if offers else {}
        price     = offer.get("price", {})

        return {
            "sku":             raw.get("sku", ""),
            "asin":            summary.get("asin", ""),
            "title":           summary.get("itemName", ""),
            "product_type":    summary.get("productType", ""),
            "status":          summary.get("status", []),
            "condition":       summary.get("conditionType", ""),
            "created_date":    summary.get("createdDate", ""),
            "last_updated":    summary.get("lastUpdatedDate", ""),
            "main_image_url":  summary.get("mainImage", {}).get("link", ""),
            "marketplace_id":  summary.get("marketplaceId", ""),
            "price_amount":    price.get("Amount", ""),
            "price_currency":  price.get("CurrencyCode", "EUR"),
            "fulfillment":     offer.get("fulfillmentChannel", ""),
            "attributes_raw":  raw.get("attributes", {}),
        }

    # ─── Catalog Items API ───────────────────────

    def get_catalog_item_raw(self, asin: str) -> dict:
        path = f"/catalog/2022-04-01/items/{asin}"
        params = {
            "marketplaceIds": self.client.marketplace_id,
            "includedData":   "summaries,attributes,dimensions,identifiers,images,productTypes,relationships",
        }
        return self.client.get(path, params=params)

    def get_catalog_item_db(self, asin: str) -> dict:
        raw = self.get_catalog_item_raw(asin)
        return self._catalog_item_to_db(raw)

    def _catalog_item_to_db(self, raw: dict) -> dict:
        summaries = raw.get("summaries", [])
        summary   = summaries[0] if summaries else {}
        attrs     = raw.get("attributes", {})
        images    = raw.get("images", [])
        dims      = raw.get("dimensions", [])

        image_urls = []
        for img_group in images:
            for img in img_group.get("images", []):
                if img.get("variant", "") == "MAIN":
                    image_urls.append(img.get("link", ""))

        dim_data = dims[0] if dims else {}
        package  = dim_data.get("package", {})
        item_dim = dim_data.get("item", {})

        title = summary.get("itemName", "")
        brand = summary.get("brand",
                            attrs.get("brand", [{}])[0].get("value", "") if attrs.get("brand") else "")

        product_description = self._attr_value(attrs, "product_description")
        if not product_description:
            product_description = self._attr_value(attrs, "bullet_point")

        return {
            "asin":                raw.get("asin", ""),
            "title":               title,
            "brand":               brand,
            "color":               self._attr_value(attrs, "color"),
            "model_number":        self._attr_value(attrs, "model_number"),
            "product_description": product_description,
            "manufacturer":        summary.get("manufacturer", self._attr_value(attrs, "manufacturer")),
            "product_type":        summary.get("productType", ""),
            "marketplace_id":      summary.get("marketplaceId", ""),
            "main_images":         image_urls,
            "item_length":         item_dim.get("length", {}).get("value"),
            "item_width":          item_dim.get("width", {}).get("value"),
            "item_height":         item_dim.get("height", {}).get("value"),
            "item_dim_unit":       item_dim.get("length", {}).get("unit", ""),
            "item_weight":         item_dim.get("weight", {}).get("value"),
            "item_weight_unit":    item_dim.get("weight", {}).get("unit", ""),
            "package_length":      package.get("length", {}).get("value"),
            "package_width":       package.get("width", {}).get("value"),
            "package_height":      package.get("height", {}).get("value"),
            "package_dim_unit":    package.get("length", {}).get("unit", ""),
            "package_weight":      package.get("weight", {}).get("value"),
            "package_weight_unit": package.get("weight", {}).get("unit", ""),
            "attributes_raw":      attrs,
        }

    @staticmethod
    def _attr_value(attrs: dict, key: str, default: str = "") -> str:
        values = attrs.get(key, [])
        if isinstance(values, list) and values:
            v = values[0]
            if isinstance(v, dict):
                return v.get("value", default)
            return str(v)
        return default

    # ─── Reports API — Catalogue complet ─────────

    def get_all_listings_raw(self) -> dict:
        """Récupère tous les listings via GET_MERCHANT_LISTINGS_ALL_DATA."""
        report_body = {
            "reportType":     "GET_MERCHANT_LISTINGS_ALL_DATA",
            "marketplaceIds": [self.client.marketplace_id],
        }
        try:
            create_resp = self.client.post("/reports/2021-06-30/reports", report_body)
        except SPAPIError as e:
            raise ReportError(f"Impossible de créer le rapport : {e}") from e

        report_id = create_resp.get("reportId", "")
        if not report_id:
            raise ReportError(f"Réponse sans reportId : {create_resp}")

        report_data = self._poll_report(report_id)
        doc_id      = report_data.get("reportDocumentId", "")
        if not doc_id:
            raise ReportError(f"Pas de reportDocumentId pour {report_id}")

        try:
            doc_resp = self.client.get(f"/reports/2021-06-30/documents/{doc_id}")
        except SPAPIError as e:
            raise ReportError(f"Impossible de récupérer le document {doc_id} : {e}") from e

        doc_url = doc_resp.get("url", "")
        if not doc_url:
            raise ReportError(f"Pas d'URL pour le document {doc_id}")

        content = self._download_report_document(doc_url)
        listings = self._parse_tsv_listings(content)
        logger.info("Catalogue : %d listings récupérés", len(listings))
        return {"listings": listings, "total": len(listings)}

    def _poll_report(self, report_id: str, timeout_s: int = 300, poll_interval: int = 15) -> dict:
        path     = f"/reports/2021-06-30/reports/{report_id}"
        deadline = time.time() + timeout_s
        poll_count = 0

        while time.time() < deadline:
            poll_count += 1
            try:
                resp = self.client.get(path)
            except (NetworkError, ServerError) as e:
                logger.warning("Erreur polling rapport %s (essai %d) : %s", report_id, poll_count, e)
                time.sleep(poll_interval)
                continue

            status = resp.get("processingStatus", "")
            logger.info("Rapport %s — statut : %s (poll %d)", report_id, status, poll_count)

            if status == "DONE":
                return resp
            if status in ("CANCELLED", "FATAL"):
                raise ReportError(f"Rapport {report_id} échoué : {status}")

            time.sleep(poll_interval)

        raise TimeoutError(f"Rapport {report_id} non terminé après {timeout_s}s")

    @staticmethod
    def _download_report_document(url: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries + 1):
            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                return resp.text
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt >= max_retries:
                    raise NetworkError(f"Téléchargement rapport échoué : {e}")
                time.sleep(2.0 * (2 ** attempt))
            except requests.exceptions.HTTPError as e:
                raise NetworkError(f"Erreur HTTP téléchargement : {e}")
        raise NetworkError("Échec téléchargement rapport")

    @staticmethod
    def _parse_tsv_listings(content: str) -> list[dict]:
        lines = content.strip().split("\n")
        if not lines:
            return []
        headers = lines[0].split("\t")
        return [
            dict(zip(headers, line.split("\t")))
            for line in lines[1:]
        ]

    # ─── searchListingsItems — Recherche en masse ─

    def search_listings_raw(
        self,
        created_after: str | None = None,
        created_before: str | None = None,
        last_updated_after: str | None = None,
        last_updated_before: str | None = None,
        with_status: list[str] | None = None,
        without_status: list[str] | None = None,
        with_issue_severity: list[str] | None = None,
        included_data: list[str] | None = None,
        page_size: int = 20,
        page_token: str | None = None,
        sort_by: str = "lastUpdatedDate",
        sort_order: str = "DESC",
    ) -> dict:
        """
        Recherche de listings via searchListingsItems.
        
        Statuts possibles : BUYABLE, DISCOVERABLE
        Sévérités issues  : ERROR, WARNING
        Sort by           : lastUpdatedDate, createdDate, sku
        
        ⚠️ Max 1000 résultats par recherche (pagination incluse).
        """
        path = f"/listings/2021-08-01/items/{self.seller_id}"
        params: dict = {
            "marketplaceIds": self.client.marketplace_id,
            "pageSize":       page_size,
            "sortBy":         sort_by,
            "sortOrder":      sort_order,
        }

        if included_data:
            params["includedData"] = ",".join(included_data)
        else:
            params["includedData"] = "summaries,attributes,issues,offers,fulfillmentAvailability"

        if created_after:
            params["createdAfter"] = created_after
        if created_before:
            params["createdBefore"] = created_before
        if last_updated_after:
            params["lastUpdatedAfter"] = last_updated_after
        if last_updated_before:
            params["lastUpdatedBefore"] = last_updated_before
        if with_status:
            params["withStatus"] = ",".join(with_status)
        if without_status:
            params["withoutStatus"] = ",".join(without_status)
        if with_issue_severity:
            params["withIssueSeverity"] = ",".join(with_issue_severity)
        if page_token:
            params["pageToken"] = page_token

        params["issueLocale"] = "fr_FR"

        return self.client.get(path, params=params)

    def search_listings_page(
        self,
        max_results: int = 1000,
        **kwargs,
    ) -> list[dict]:
        """
        Recherche avec pagination automatique.
        Retourne jusqu'à max_results listings (max 1000 par Amazon).
        """
        all_items: list[dict] = []
        page_token = None
        page = 0

        while len(all_items) < max_results:
            kwargs["page_token"] = page_token
            kwargs["page_size"] = min(20, max_results - len(all_items))

            resp = self.search_listings_raw(**kwargs)
            items = resp.get("items", [])          # ← correction ici
            all_items.extend(items)
            page += 1

            pagination = resp.get("pagination", {})
            page_token = pagination.get("nextToken")

            if not page_token or not items:
                break

            logger.info("  searchListings page %d — %d listings", page, len(all_items))
            time.sleep(self.RATE_LIMIT_DELAY)

        return all_items

    def search_all_listings_by_date(
        self,
        start_date: str = "2020-01-01T00:00:00Z",
        end_date: str | None = None,
        interval_days: int = 30,
        included_data: list[str] | None = None,
        min_interval_seconds: int = 60,   # seuil minimal pour ne pas subdiviser à l'infini
    ) -> list[dict]:
        """
        Récupère tous les listings en découpant par tranches de dates.
        Si une tranche retourne >=1000 résultats, elle est subdivisée récursivement.
        """
        from datetime import datetime, timedelta, timezone

        if end_date is None:
            end_date = datetime.now(timezone.utc).isoformat()

        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        all_listings: dict[str, dict] = {}

        # Fonction récursive interne
        def _fetch_range(range_start: datetime, range_end: datetime) -> list[dict]:
            # Ne pas subdiviser si l'intervalle est déjà très petit
            if (range_end - range_start).total_seconds() <= min_interval_seconds:
                # On tente quand même de récupérer (peu importe le nombre)
                return self.search_listings_page(
                    max_results=1000,
                    created_after=range_start.isoformat(),
                    created_before=range_end.isoformat(),
                    included_data=included_data,
                    sort_by="createdDate",
                    sort_order="ASC",
                )

            # Appel pour cet intervalle
            items = self.search_listings_page(
                max_results=1000,
                created_after=range_start.isoformat(),
                created_before=range_end.isoformat(),
                included_data=included_data,
                sort_by="createdDate",
                sort_order="ASC",
            )

            # Si on a moins de 1000 résultats, c'est complet
            if len(items) < 1000:
                return items

            # Sinon, on subdivise l'intervalle en deux
            logger.warning(
                "Intervalle %s → %s saturé (%d items) → subdivision",
                range_start.isoformat(), range_end.isoformat(), len(items)
            )
            mid = range_start + (range_end - range_start) / 2
            left_items = _fetch_range(range_start, mid)
            right_items = _fetch_range(mid, range_end)
            return left_items + right_items

        # Découpage initial par intervalles de `interval_days` jours
        current = start
        delta = timedelta(days=interval_days)

        while current < end:
            window_end = min(current + delta, end)

            logger.info("Tranche %s → %s", current.isoformat(), window_end.isoformat())

            try:
                items = _fetch_range(current, window_end)

                for item in items:
                    sku = item.get("sku", "")
                    if sku:
                        all_listings[sku] = item

                logger.info("  → %d listings dans cette tranche (total unique : %d)", len(items), len(all_listings))

            except AuthError:
                raise
            except SPAPIError as e:
                logger.warning("Erreur sur tranche %s : %s", current.isoformat(), e)

            current = window_end
            time.sleep(0.5)

        logger.info("Terminé : %d listings uniques", len(all_listings))
        return list(all_listings.values())