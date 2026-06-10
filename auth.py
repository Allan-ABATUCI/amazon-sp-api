"""
Amazon Selling Partner API (SP-API) - Authentification
───────────────────────────────────────────────────────

Gestion du token d'accès Login With Amazon (LWA)
"""

import time
import logging
import requests
import requests.exceptions
from datetime import datetime, timezone

from .config import LWA_TOKEN_URL, RDT_TOKEN_URL, REFRESH_TOKEN, CLIENT_ID, CLIENT_SECRET
from .exceptions import AuthError, NetworkError

import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TokenManager:
    """Access token LWA avec cache et renouvellement auto."""

    def __init__(self):
        self._access_token: str | None = None
        self._expires_at: float = 0.0
        self._rdt_token: str | None = None
        self._rdt_expires_at: float = 0.0


    def get_access_token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token

        logger.info("Renouvellement du access_token LWA…")
        last_error = None

        for attempt in range(3):
            try:
                resp = requests.post(
                    LWA_TOKEN_URL,
                    data={
                        "grant_type":    "refresh_token",
                        "refresh_token": REFRESH_TOKEN,
                        "client_id":     CLIENT_ID,
                        "client_secret": CLIENT_SECRET,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10,
                )

                if resp.status_code in (401, 403):
                    raise AuthError(
                        f"Credentials LWA invalides ({resp.status_code})",
                        status_code=resp.status_code,
                        response_body=resp.text[:300],
                    )

                if resp.status_code >= 500 or resp.status_code == 429:
                    delay = 2.0 * (2 ** attempt)
                    logger.warning(
                        "LWA error %d — retry %d/3 dans %.1fs",
                        resp.status_code, attempt + 1, delay,
                    )
                    time.sleep(delay)
                    continue

                if not resp.ok:
                    logger.error("LWA error %s : %s", resp.status_code, resp.text)
                    resp.raise_for_status()

                data = resp.json()
                if "access_token" not in data:
                    raise AuthError(f"Réponse LWA inattendue (pas de access_token) : {data}")

                self._access_token = data["access_token"]
                self._expires_at   = time.time() + data.get("expires_in", 3600)
                logger.info("Token obtenu, expire dans %ds", data.get("expires_in", 3600))
                return self._access_token

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_error = e
                delay = 2.0 * (2 ** attempt)
                logger.warning(
                    "Erreur réseau LWA (%s) — retry %d/3 dans %.1fs",
                    type(e).__name__, attempt + 1, delay,
                )
                time.sleep(delay)

        raise NetworkError(f"Impossible d'obtenir le token LWA après 3 retries : {last_error}")

    def get_rdt_access_token(self) -> str:
        if self._rdt_token and time.time() < self._rdt_expires_at - 60:
            return self._rdt_token

        logger.info("Renouvellement du access_token RDT…")
        last_error = None

        for attempt in range(3):
            try:
                token = self.get_access_token()
                payload = {
                    "restrictedResources": [
                        {
                        "method": "GET",
                        "path": "/orders/2026-01-01/orders"
                        },
                        {
                        "method": "GET",
                        "path": f"/listings/2021-08-01/items/{os.getenv('AMAZON_SELLER_ID')}"
                        }
                    ]
                }
                resp = requests.post(
                    RDT_TOKEN_URL,
                    json=payload,
                    headers = {
                        "x-amz-access-token": token,
                        "accept": "application/json",
                        "content-type": "application/json"
                    },
                    timeout=10,
                )

                if resp.status_code in (401, 403):
                    raise AuthError(
                        f"Credentials LWA invalides ({resp.status_code})",
                        status_code=resp.status_code,
                        response_body=resp.text[:300],
                    )

                if resp.status_code >= 500 or resp.status_code == 429:
                    delay = 2.0 * (2 ** attempt)
                    logger.warning(
                        "LWA error %d — retry %d/3 dans %.1fs",
                        resp.status_code, attempt + 1, delay,
                    )
                    time.sleep(delay)
                    continue

                if not resp.ok:
                    logger.error("LWA error %s : %s", resp.status_code, resp.text)
                    resp.raise_for_status()

                data = resp.json()
                if "restrictedDataToken" not in data:
                    raise AuthError(f"Réponse RDT inattendue : {data}")

                self._rdt_token = data["restrictedDataToken"]
                self._rdt_expires_at = time.time() + data.get("expiresIn", 3600)
                logger.info("Token obtenu, expire dans %ds", data.get("expires_in", 3600))
                return self._rdt_token

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_error = e
                delay = 2.0 * (2 ** attempt)
                logger.warning(
                    "Erreur réseau LWA (%s) — retry %d/3 dans %.1fs",
                    type(e).__name__, attempt + 1, delay,
                )
                time.sleep(delay)

        raise NetworkError(f"Impossible d'obtenir le token LWA après 3 retries : {last_error}")

    def debug_token(self) -> None:
        token = self.get_access_token()
        print(f"Token OK  : {token[:12]}…{token[-4:]}")
        print(f"Expire à  : {datetime.fromtimestamp(self._expires_at, tz=timezone.utc).isoformat()}")

    def debug_rdt_token(self) -> None:
        rdt_token = self.get_rdt_access_token()
        print(f"Token OK  : {rdt_token[:12]}…{rdt_token[-4:]}")
        print(f"Expire à  : {datetime.fromtimestamp(self._rdt_expires_at, tz=timezone.utc).isoformat()}")


# Instance globale du gestionnaire de token
token_manager = TokenManager()