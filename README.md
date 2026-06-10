# amazon-sp-api — Client Python pour l'API Amazon Selling Partner

**Auteur :** Allan ABATUCI  
**Version :** 3.0.0  
**Langage :** Python 3.11+

---

## Vue d'ensemble

Client Python modulaire pour l'**Amazon Selling Partner API (SP-API)**. Il gère l'authentification LWA, le routage EU/NA, le retry automatique, et expose des interfaces claires pour les commandes, le catalogue, et les listings.

---

## Modules

| Module | Rôle |
|---|---|
| `config.py` | Credentials, marketplace IDs, endpoints |
| `auth.py` | `TokenManager` — token LWA avec cache et renouvellement auto |
| `client.py` | `SPAPIClient` — HTTP avec retry, backoff exponentiel, exceptions typées |
| `orders.py` | `Orders` — API commandes v2026-01-01 (PII sans RDT) |
| `catalog.py` | `CatalogAPI` — Listings Items, Catalog Items, Reports, Search |
| `customer.py` | `CustomerAPI` — données acheteur |
| `loaders.py` | Import de SKUs depuis exports Seller Central (CSV) |
| `exceptions.py` | Hiérarchie d'exceptions : `SPAPIError`, `RateLimitError`, `AuthError`, `ServerError`, `NetworkError`, `ReportError` |
| `utils.py` | `save_json`, `_parse_money` |

---

## Prérequis

- Python 3.11+
- Application enregistrée sur [Seller Central](https://sellercentral.amazon.com) > Developer Console
- Rôle **Direct-to-Consumer Shipping** pour accéder aux données PII des commandes

---

## Installation

```bash
pip install requests python-dotenv
```

---

## Configuration

Créer un fichier `.env` à la racine du projet :

```env
AMAZON_REFRESH_TOKEN_PROD=Atzr|...
AMAZON_CLIENT_ID_PROD=amzn1.application-oa2-client...
AMAZON_CLIENT_SECRET_PROD=...
AMAZON_SELLER_ID=A...
```

---

## Utilisation

### Commandes

```python
from amazon_sp_api import SPAPIClient, Orders
from datetime import datetime, timezone

client = SPAPIClient(marketplace="FR")
orders_api = Orders(client)

# Récupérer les commandes des 7 derniers jours
orders, next_token = orders_api.get_orders(
    created_after=datetime(2026, 6, 1, tzinfo=timezone.utc)
)
for order in orders:
    print(order["AmazonOrderId"], order["OrderStatus"])
```

### Catalogue & Listings

```python
from amazon_sp_api import SPAPIClient, CatalogAPI

client = SPAPIClient(marketplace="FR")
catalog = CatalogAPI(client)

# Recherche dans le catalogue
results = catalog.search_catalog_items(keywords="smartphone")

# Récupérer les listings du vendeur
listings = catalog.get_listings_items(seller_id="A...")
```

### Marketplace multi-région

```python
# Europe
client_fr = SPAPIClient(marketplace="FR")   # → sellingpartnerapi-eu.amazon.com
client_de = SPAPIClient(marketplace="DE")

# Amérique du Nord
client_us = SPAPIClient(marketplace="US")   # → sellingpartnerapi-na.amazon.com
```

### Sauvegarde des réponses brutes

```python
client = SPAPIClient(marketplace="FR", save_responses=True)
# Les réponses JSON sont sauvegardées dans /api_responses/
```

### Gestion des erreurs

```python
from amazon_sp_api import SPAPIClient, Orders, AuthError, RateLimitError, SPAPIError

client = SPAPIClient(marketplace="FR")
try:
    orders_api = Orders(client)
    orders, _ = orders_api.get_orders()
except AuthError:
    print("Credentials LWA invalides")
except RateLimitError:
    print("Quota dépassé")
except SPAPIError as e:
    print(f"Erreur API : {e}")
```

---

## Marketplaces supportées

| Code | Marketplace | Région |
|---|---|---|
| FR | Amazon.fr | EU |
| DE | Amazon.de | EU |
| UK | Amazon.co.uk | EU |
| IT | Amazon.it | EU |
| ES | Amazon.es | EU |
| BE | Amazon.com.be | EU |
| US | Amazon.com | NA |
| CA | Amazon.ca | NA |
| MX | Amazon.com.mx | NA |

---

## Comportement du client HTTP

- **Retry** : 5 tentatives par défaut sur erreurs réseau et 5xx
- **Backoff exponentiel** : délai x2 à chaque retry (max 32s)
- **Rate limit 429** : respect du header `Retry-After` ou backoff exponentiel
- **Auth 401/403** : exception immédiate sans retry

---

## Licence

Usage interne — METM Corporate.
