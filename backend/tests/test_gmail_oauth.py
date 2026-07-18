import json
import time

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from app.infrastructure import gmail_oauth

FAKE_CLIENT_SECRETS = {
    "web": {
        "client_id": "fake-client-id.apps.googleusercontent.com",
        "client_secret": "fake-client-secret",  # noqa: S105 (test fixture value)
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8000/gmail/callback"],
    }
}

FAKE_STORED_CREDENTIALS = {
    "refresh_token": "refresh-tok",  # noqa: S105 (test fixture value)
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "fake-client-id",
    "client_secret": "fake-client-secret",  # noqa: S105 (test fixture value)
    "scopes": gmail_oauth.SCOPES,
}


@pytest.fixture(autouse=True)
def _reset_pending_state():
    gmail_oauth._last_issued_state = None
    gmail_oauth._pending_code_verifier = None
    yield
    gmail_oauth._last_issued_state = None
    gmail_oauth._pending_code_verifier = None


@pytest.fixture()
def client_secrets_file(tmp_path, monkeypatch):
    path = tmp_path / "gmail_client_secret.json"
    path.write_text(json.dumps(FAKE_CLIENT_SECRETS))
    monkeypatch.setenv("GMAIL_CLIENT_SECRET_PATH", str(path))
    yield path


def _stored_credentials_json(*, expired: bool) -> str:
    expiry = "2000-01-01T00:00:00Z" if expired else "2099-01-01T00:00:00Z"
    return json.dumps({**FAKE_STORED_CREDENTIALS, "token": "some-token", "expiry": expiry})


def test_build_authorization_url_points_at_google_with_expected_params(client_secrets_file):
    url = gmail_oauth.build_authorization_url()
    assert url.startswith("https://accounts.google.com/o/oauth2/auth")
    assert "client_id=fake-client-id.apps.googleusercontent.com" in url
    assert "gmail.readonly" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert gmail_oauth._last_issued_state is not None


def test_build_authorization_url_without_client_secrets_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_SECRET_PATH", str(tmp_path / "missing.json"))
    with pytest.raises(gmail_oauth.GmailAuthError, match="not found"):
        gmail_oauth.build_authorization_url()


def test_exchange_code_rejects_an_unissued_state(client_secrets_file):
    gmail_oauth.build_authorization_url()
    with pytest.raises(gmail_oauth.GmailAuthError, match="state mismatch"):
        gmail_oauth.exchange_code("some-code", "not-the-issued-state")


def test_exchange_code_passes_through_the_pkce_code_verifier(client_secrets_file, monkeypatch):
    # Regression test: exchange_code builds a brand-new Flow object, separate from the one
    # build_authorization_url used -- without explicitly carrying the code_verifier over, Google
    # rejects the real exchange with "invalid_grant: Missing code verifier" (caught during the
    # live consent test against a real account; mocking fetch_token alone doesn't catch this
    # since it never actually checks the verifier).
    gmail_oauth.build_authorization_url()
    issued_state = gmail_oauth._last_issued_state
    issued_verifier = gmail_oauth._pending_code_verifier
    assert issued_verifier  # sanity: PKCE is on, so this must be non-empty

    seen_verifier = None

    def fake_fetch_token(self, **kwargs):
        nonlocal seen_verifier
        seen_verifier = self.code_verifier
        self.oauth2session.token = {"access_token": "tok", "expires_at": time.time() + 3600}  # noqa: S106

    monkeypatch.setattr("google_auth_oauthlib.flow.Flow.fetch_token", fake_fetch_token)

    gmail_oauth.exchange_code("fake-code", issued_state)

    assert seen_verifier == issued_verifier


def test_exchange_code_success_and_state_is_single_use(client_secrets_file, monkeypatch):
    gmail_oauth.build_authorization_url()
    issued_state = gmail_oauth._last_issued_state

    def fake_fetch_token(self, **kwargs):
        self.oauth2session.token = {
            "access_token": "fake-access-token",  # noqa: S105 (test fixture value)
            "refresh_token": "fake-refresh-token",  # noqa: S105 (test fixture value)
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }

    monkeypatch.setattr("google_auth_oauthlib.flow.Flow.fetch_token", fake_fetch_token)

    credentials = gmail_oauth.exchange_code("fake-code", issued_state)

    assert credentials.token == "fake-access-token"
    assert credentials.refresh_token == "fake-refresh-token"
    assert gmail_oauth._last_issued_state is None  # single-use

    # Replaying the same (now-consumed) state must fail, not silently re-succeed.
    with pytest.raises(gmail_oauth.GmailAuthError, match="state mismatch"):
        gmail_oauth.exchange_code("fake-code", issued_state)


def test_exchange_code_wraps_fetch_token_failures(client_secrets_file, monkeypatch):
    gmail_oauth.build_authorization_url()
    issued_state = gmail_oauth._last_issued_state

    def fake_fetch_token(self, **kwargs):
        raise RuntimeError("network exploded")

    monkeypatch.setattr("google_auth_oauthlib.flow.Flow.fetch_token", fake_fetch_token)

    with pytest.raises(gmail_oauth.GmailAuthError, match="network exploded"):
        gmail_oauth.exchange_code("fake-code", issued_state)


def test_fetch_connected_email(monkeypatch):
    fake_credentials = Credentials(token="fake-access-token")  # noqa: S106

    class _Execution:
        def execute(self, num_retries=0):
            return {"emailAddress": "naveen@gmail.com"}

    class _FakeUsers:
        def getProfile(self, userId):
            assert userId == "me"
            return _Execution()

    class _FakeService:
        def users(self):
            return _FakeUsers()

    monkeypatch.setattr(gmail_oauth, "build", lambda *a, **k: _FakeService())

    assert gmail_oauth.fetch_connected_email(fake_credentials) == "naveen@gmail.com"


def test_get_valid_credentials_returns_unchanged_when_not_expired():
    stored = _stored_credentials_json(expired=False)
    credentials, new_json = gmail_oauth.get_valid_credentials(stored)
    assert new_json is None
    assert credentials.token == "some-token"


def test_get_valid_credentials_refreshes_expired_token(monkeypatch):
    stored = _stored_credentials_json(expired=True)

    def fake_refresh(self, request):
        self.token = "refreshed-token"

    monkeypatch.setattr(Credentials, "refresh", fake_refresh)

    credentials, new_json = gmail_oauth.get_valid_credentials(stored)

    assert credentials.token == "refreshed-token"
    assert new_json is not None
    assert json.loads(new_json)["token"] == "refreshed-token"


def test_get_valid_credentials_raises_when_no_refresh_token_available():
    stored = json.dumps(
        {
            "token": "expired-token",
            "refresh_token": None,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "fake-client-id",
            "client_secret": "fake-client-secret",  # noqa: S105 (test fixture value)
            "scopes": gmail_oauth.SCOPES,
            "expiry": "2000-01-01T00:00:00Z",
        }
    )
    with pytest.raises(gmail_oauth.GmailAuthError, match="reconnect required"):
        gmail_oauth.get_valid_credentials(stored)


def test_get_valid_credentials_surfaces_refresh_failure_rather_than_swallowing_it(monkeypatch):
    stored = _stored_credentials_json(expired=True)

    def fake_refresh(self, request):
        raise RefreshError("access revoked")

    monkeypatch.setattr(Credentials, "refresh", fake_refresh)

    with pytest.raises(gmail_oauth.GmailAuthError, match="access revoked"):
        gmail_oauth.get_valid_credentials(stored)
