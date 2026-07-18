"""Gmail OAuth 2.0 connect flow (B1, REQUIREMENTS.md ING-1/ING-2) and credential refresh.

Uses Google's official client libraries (ADR-0018) rather than hand-rolling OAuth/token-refresh
logic ourselves.
"""

import json
import os
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

_DEFAULT_CLIENT_SECRETS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "gmail_client_secret.json"
)

# Read-only only (ING-2) -- no send/delete/modify scope is ever requested.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailAuthError(Exception):
    """Raised when the OAuth flow or a token refresh fails.

    Always surfaced to the caller (never swallowed) so it can be routed to the needs-attention
    surface built in B5 (ING-8) once that exists.
    """


def _client_secrets_path() -> Path:
    return Path(os.environ.get("GMAIL_CLIENT_SECRET_PATH", str(_DEFAULT_CLIENT_SECRETS_PATH)))


def _redirect_uri() -> str:
    # Registered directly with Google (Cloud Console), independent of BACKEND_PORT (scripts/
    # dev.py) -- changing BACKEND_PORT alone must not silently break this without also
    # re-registering the redirect URI there.
    return os.environ.get("GMAIL_REDIRECT_URI", "http://localhost:8000/gmail/callback")


def _build_flow() -> Flow:
    path = _client_secrets_path()
    if not path.exists():
        raise GmailAuthError(
            f"Gmail OAuth client secret not found at {path}. Download it from Google Cloud "
            "Console (APIs & Services > Credentials) and save it there."
        )
    return Flow.from_client_secrets_file(str(path), scopes=SCOPES, redirect_uri=_redirect_uri())


# Single outstanding connect attempt at a time (REQUIREMENTS.md Assumption 1: one Gmail
# account, one user) -- tracked so the callback can reject a state it didn't just issue, rather
# than needing a persistent, multi-session store this single-user app doesn't need. Paired with
# the PKCE code_verifier Flow auto-generates alongside the state: the callback exchange builds a
# *new* Flow object (build_authorization_url's Flow is long gone by then), so without carrying
# this over explicitly Google rejects the exchange with "invalid_grant: Missing code verifier".
_last_issued_state: str | None = None
_pending_code_verifier: str | None = None


def build_authorization_url() -> str:
    global _last_issued_state, _pending_code_verifier
    flow = _build_flow()
    url, state = flow.authorization_url(
        access_type="offline",  # request a refresh_token (B1: refresh without user intervention)
        prompt="consent",  # force Google to reissue a refresh_token even on a repeat connect
    )
    _last_issued_state = state
    _pending_code_verifier = flow.code_verifier
    return url


def exchange_code(code: str, state: str) -> Credentials:
    global _last_issued_state, _pending_code_verifier
    if not state or state != _last_issued_state:
        raise GmailAuthError(
            "OAuth state mismatch -- possible CSRF attempt or a stale/duplicate callback."
        )
    code_verifier = _pending_code_verifier
    _last_issued_state = None
    _pending_code_verifier = None
    flow = _build_flow()
    flow.code_verifier = code_verifier
    try:
        flow.fetch_token(code=code)
    except Exception as exc:  # noqa: BLE001 -- any failure here must surface, never be swallowed
        raise GmailAuthError(f"Failed to exchange authorization code: {exc}") from exc
    return flow.credentials


def fetch_connected_email(credentials: Credentials) -> str:
    service = build(
        "gmail", "v1", credentials=credentials, cache_discovery=False, static_discovery=True
    )
    # num_retries: google-api-python-client's built-in backoff/retry for transient errors
    # (429/5xx) -- consistent with gmail_client.py's use of the same mechanism (ING-7).
    profile = service.users().getProfile(userId="me").execute(num_retries=5)
    return profile["emailAddress"]


def credentials_to_json(credentials: Credentials) -> str:
    return credentials.to_json()


def credentials_from_json(stored_json: str) -> Credentials:
    return Credentials.from_authorized_user_info(json.loads(stored_json))


def get_valid_credentials(stored_json: str) -> tuple[Credentials, str | None]:
    """Return usable credentials for a stored connection, refreshing if expired.

    Returns (credentials, new_json): new_json is the updated serialized credentials to persist
    if a refresh happened, or None if the stored tokens were already valid.
    """
    credentials = credentials_from_json(stored_json)
    if not credentials.expired:
        return credentials, None
    if not credentials.refresh_token:
        raise GmailAuthError(
            "Gmail access token expired and no refresh token is available -- reconnect required."
        )
    try:
        credentials.refresh(Request())
    except RefreshError as exc:
        raise GmailAuthError(f"Gmail token refresh failed: {exc}") from exc
    return credentials, credentials_to_json(credentials)
