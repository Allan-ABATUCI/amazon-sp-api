"""
Amazon Selling Partner API (SP-API) - Client HTTP
──────────────────────────────────────────────────

Client HTTP bas niveau avec :
  • Routage automatique EU/NA/FE selon la marketplace
  • Exponential backoff sur 429 (rate limit)
  • Retry auto sur erreurs réseau et 5xx
  • Exceptions typées
"""

import time
import logging
import requests
import requests.exceptions

from .config import SP_API_ENDPOINTS, MARKETPLACE_REGIONS, MARKETPLACE_IDS
from .exceptions import SPAPIError, RateLimitError, AuthError, ServerError, NetworkError
from .auth import token_manager
from .utils import save_json

logger = logging.getLogger(__name__)


class SPAPIClient:
    """
    Client HTTP bas niveau SP-API.
    
    Le bon endpoint (EU/NA/FE) est sélectionné automatiquement
    en fonction de la marketplace.
    """

    BACKOFF_BASE    = 2.0
    BACKOFF_MAX     = 32.0
    BACKOFF_FACTOR  = 2.0

    _RETRYABLE_NETWORK = (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.ChunkedEncodingError,
    )

    def __init__(
        self,
        marketplace: str = "FR",
        marketplace_id: str = "A13V1IB3VIYZZH",
        region: str = "EU",
        save_responses: bool = False,
        max_retries: int = 5,
        timeout: int = 15,
    ):
        mp = marketplace.upper()
        region = MARKETPLACE_REGIONS[mp]
        self.base_url       = SP_API_ENDPOINTS[region]
        self.marketplace_id = MARKETPLACE_IDS[mp]
        self.marketplace    = mp
        self.save_responses = save_responses
        self.max_retries    = max_retries
        self.timeout        = timeout

    def _headers(self) -> dict:
        return {
            "x-amz-access-token": token_manager.get_access_token(),
            "Content-Type":       "application/json",
        }

    def _rdt_headers(self) -> dict:
        return {
            "x-amz-access-token": token_manager.get_rdt_access_token(),
            "Content-Type":       "application/json",
        }

    def _maybe_save(self, data: dict, path: str) -> None:
        if self.save_responses:
            save_json(data, path.strip("/").replace("/", "_"))

    def _backoff_delay(self, attempt: int, retry_after: int | None = None) -> float:
        exp_delay = min(self.BACKOFF_BASE * (self.BACKOFF_FACTOR ** attempt), self.BACKOFF_MAX)
        if retry_after and retry_after > exp_delay:
            return float(retry_after)
        return exp_delay

    def _handle_http_error(self, resp: requests.Response, path: str, attempt: int) -> None:
        code = resp.status_code
        body = resp.text[:500]

        if code in (401, 403):
            logger.error("Auth error %d sur %s : %s", code, path, body)
            raise AuthError(
                f"Authentification échouée ({code}) sur {path}: {body}.",
                status_code=code, response_body=body,
            )

        if code == 429:
            retry_after = int(resp.headers.get("Retry-After", 0)) or None
            delay = self._backoff_delay(attempt, retry_after)
            if attempt >= self.max_retries:
                raise RateLimitError(
                    f"Rate limit (429) persistant sur {path}",
                    status_code=429, response_body=body,
                )
            logger.warning("Rate limit 429 sur %s — retry %d/%d dans %.1fs",
                           path, attempt + 1, self.max_retries, delay)
            time.sleep(delay)
            return

        if 500 <= code < 600:
            delay = self._backoff_delay(attempt)
            if attempt >= self.max_retries:
                raise ServerError(
                    f"Erreur serveur ({code}) persistante sur {path}",
                    status_code=code, response_body=body,
                )
            logger.warning("Erreur serveur %d sur %s — retry %d/%d dans %.1fs",
                           code, path, attempt + 1, self.max_retries, delay)
            time.sleep(delay)
            return

        logger.error("Erreur HTTP %d sur %s : %s", code, path, body)
        raise SPAPIError(f"Erreur HTTP {code} sur {path}: {body}",
                         status_code=code, response_body=body)

    def _request(self, method: str, path: str,
                 params: dict | None = None, body: dict | None = None) -> dict:
        url        = f"{self.base_url}{path}"
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if method == "GET":
                    resp = requests.get(url, headers=self._headers(),
                                        params=params, timeout=self.timeout)
                else:
                    resp = requests.post(url, headers=self._headers(),
                                         json=body, timeout=self.timeout)

                if resp.ok:
                    data = resp.json()
                    self._maybe_save(data, path)
                    return data

                self._handle_http_error(resp, path, attempt)
                continue

            except (AuthError, SPAPIError):
                raise

            except self._RETRYABLE_NETWORK as exc:
                delay = self._backoff_delay(attempt)
                last_error = exc
                if attempt >= self.max_retries:
                    break
                logger.warning("Erreur réseau %s sur %s — retry %d/%d dans %.1fs",
                               type(exc).__name__, path, attempt + 1, self.max_retries, delay)
                time.sleep(delay)

        raise NetworkError(
            f"Erreur réseau persistante sur {path} après {self.max_retries} retries : {last_error}"
        )

    def get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: dict) -> dict:
        return self._request("POST", path, body=body)