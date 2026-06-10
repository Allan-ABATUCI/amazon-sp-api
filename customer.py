"""
Amazon Selling Partner API (SP-API) - Customer Info
────────────────────────────────────────────────────

Extraction des infos client depuis les données de commande.
"""

from .utils import _parse_money


class CustomerAPI:
    """Extraction des infos client depuis les données de commande."""

    @staticmethod
    def extract_from_order_raw(order: dict) -> dict:
        return {
            "BuyerInfo":       order.get("BuyerInfo", {}),
            "ShippingAddress": order.get("ShippingAddress", {}),
            "OrderTotal":      order.get("OrderTotal", {}),
            "AmazonOrderId":   order.get("AmazonOrderId", ""),
        }

    @staticmethod
    def extract_from_order_db(order: dict) -> dict:
        buyer = order.get("BuyerInfo", {})
        addr  = order.get("ShippingAddress", {})
        tax   = buyer.get("BuyerTaxInfo", {})

        return {
            "order_id":        order.get("AmazonOrderId", ""),
            "purchase_date":   order.get("PurchaseDate", ""),
            "status":          order.get("OrderStatus", ""),
            "order_total":     _parse_money(order.get("OrderTotal")),
            "buyer": {
                "name":                  buyer.get("BuyerName", ""),
                "email":                 buyer.get("BuyerEmail", ""),
                "company_legal_name":    tax.get("CompanyLegalName", ""),
                "taxing_region":         tax.get("TaxingRegion", ""),
                "tax_classifications":   tax.get("TaxClassifications", []),
                "purchase_order_number": buyer.get("PurchaseOrderNumber", ""),
            },
            "shipping_address": {
                "name":          addr.get("Name", ""),
                "address_line1": addr.get("AddressLine1", ""),
                "address_line2": addr.get("AddressLine2", ""),
                "address_line3": addr.get("AddressLine3", ""),
                "city":          addr.get("City", ""),
                "postal_code":   addr.get("PostalCode", ""),
                "state_region":  addr.get("StateOrRegion", ""),
                "country_code":  addr.get("CountryCode", ""),
            },
        }

    def extract_from_orders_response_db(self, orders_response: dict) -> list[dict]:
        if "response" in orders_response:
            order_list = orders_response["response"].get("payload", {}).get("Orders", [])
        else:
            order_list = orders_response.get("payload", {}).get("Orders", [])
        return [self.extract_from_order_db(o) for o in order_list]