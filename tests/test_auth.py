import os
import pytest
from unittest.mock import patch, MagicMock

# Import the auth module functions
from backend.auth import (
    hash_password,
    verify_password,
    load_credentials,
    save_credentials,
    authenticate,
    update_password,
    DEFAULT_PASSWORD,
    check_authentication,
)


@pytest.fixture(autouse=True)
def temporary_credentials_file(tmp_path):
    """Ensure each test runs with an isolated credentials file."""
    temp_auth_file = str(tmp_path / ".auth_credentials.json")
    with patch("backend.auth.AUTH_FILE_PATH", temp_auth_file):
        yield temp_auth_file


def test_default_password_initialization():
    """Verify default credentials initialize and match default password."""
    creds = load_credentials()
    assert "salt" in creds
    assert "password_hash" in creds
    assert "username" in creds
    # Plaintext password must NOT be stored
    assert "password" not in creds
    assert DEFAULT_PASSWORD not in creds.values()

    # Default password authentication should succeed
    assert authenticate(DEFAULT_PASSWORD) is True
    # Wrong password should fail
    assert authenticate("wrong_password") is False


def test_password_hashing_and_verification():
    """Verify hash_password produces valid salt and hash, and verify_password verifies correctly."""
    salt_hex, hash_hex = hash_password("secret123")
    assert isinstance(salt_hex, str) and len(salt_hex) == 32
    assert isinstance(hash_hex, str) and len(hash_hex) == 64

    # Correct password matches
    assert verify_password(salt_hex, hash_hex, "secret123") is True
    # Incorrect password does not match
    assert verify_password(salt_hex, hash_hex, "other_password") is False


def test_update_password_success():
    """Verify changing password succeeds with correct current password."""
    # Ensure initialized
    load_credentials()

    # Update to new password
    success, msg = update_password(DEFAULT_PASSWORD, "NewSecurePassword456")
    assert success is True
    assert "successfully" in msg.lower()

    # New password now authenticates
    assert authenticate("NewSecurePassword456") is True
    # Old default password no longer authenticates
    assert authenticate(DEFAULT_PASSWORD) is False


def test_update_password_wrong_current():
    """Verify changing password fails if current password is wrong."""
    load_credentials()

    success, msg = update_password("incorrect_current_pw", "NewSecurePassword456")
    assert success is False
    assert "incorrect" in msg.lower()

    # Default password remains valid
    assert authenticate(DEFAULT_PASSWORD) is True


def test_update_password_validation():
    """Verify password length validation."""
    load_credentials()

    success, msg = update_password(DEFAULT_PASSWORD, "12")
    assert success is False
    assert "at least 4 characters" in msg


def test_persistence_across_reloads():
    """Verify updated credentials persist when reloaded."""
    load_credentials()
    update_password(DEFAULT_PASSWORD, "PersistentPass789")

    # Re-read from disk
    reloaded_creds = load_credentials()
    assert verify_password(reloaded_creds["salt"], reloaded_creds["password_hash"], "PersistentPass789") is True


def test_check_authentication_unauthenticated():
    """Verify check_authentication returns False and renders login when not authenticated."""
    mock_session = {"authenticated": False}
    with patch("streamlit.session_state", mock_session), \
         patch("backend.auth.render_login_page") as mock_login:
        result = check_authentication()
        assert result is False
        mock_login.assert_called_once()


def test_check_authentication_authenticated():
    """Verify check_authentication returns True and renders sidebar when authenticated."""
    mock_session = {"authenticated": True}
    with patch("streamlit.session_state", mock_session), \
         patch("backend.auth.render_auth_sidebar") as mock_sidebar:
        result = check_authentication()
        assert result is True
        mock_sidebar.assert_called_once()
