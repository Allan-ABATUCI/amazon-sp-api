"""
Amazon Selling Partner API (SP-API) - Exceptions
─────────────────────────────────────────────────
"""


class SPAPIError(Exception):
    """Erreur de base pour toutes les erreurs SP-API."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str = ""):
        self.status_code   = status_code
        self.response_body = response_body
        super().__init__(message)


class RateLimitError(SPAPIError):
    """Rate limit (429) persistant après tous les retries."""
    pass


class AuthError(SPAPIError):
    """Erreur d'authentification (401/403)."""
    pass


class ServerError(SPAPIError):
    """Erreur serveur Amazon (5xx)."""
    pass


class NetworkError(SPAPIError):
    """Erreur réseau (timeout, connexion perdue, DNS…)."""
    pass


class ReportError(SPAPIError):
    """Erreur lors de la génération/récupération d'un rapport."""
    pass