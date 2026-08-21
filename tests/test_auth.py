import json
import os
import tempfile
from unittest.mock import MagicMock

import backend.auth as auth_module
from backend.auth import (
    AuthManager,
    _hash_pbkdf2,
    _verify_pbkdf2,
    hash_password,
    init_auth_session,
    is_authenticated,
    login_user,
    logout_user,
    render_auth_controls,
    render_login_screen,
    verify_password,
)


def test_hash_and_verify_password():
    password = "MySecurePassword#2024"
    hashed = hash_password(password)

    # Password should not be stored in plain text
    assert hashed != password
    assert password not in hashed

    # Hashes for same password should differ due to salting
    hashed2 = hash_password(password)
    assert hashed != hashed2

    # Verification
    assert verify_password(password, hashed) is True
    assert verify_password(password, hashed2) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(password, "") is False


def test_pbkdf2_fallback_verification():
    import hashlib
    import secrets

    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", b"testpass", salt.encode("utf-8"), 100000)
    pbkdf2_hash = f"pbkdf2:{salt}:{key.hex()}"

    assert verify_password("testpass", pbkdf2_hash) is True
    assert verify_password("wrongpass", pbkdf2_hash) is False
    assert _verify_pbkdf2("testpass", pbkdf2_hash) is True
    assert _verify_pbkdf2("wrongpass", pbkdf2_hash) is False

    generated_hash = _hash_pbkdf2("testpass")
    assert generated_hash.startswith("pbkdf2:")
    assert _verify_pbkdf2("testpass", generated_hash) is True


def test_auth_manager_default_password():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, ".auth_config.json")
        auth = AuthManager(config_path=config_path, default_password="admin")

        # Initial login with wrong password should fail
        assert auth.verify_login("wrongpassword") is False
        assert not os.path.exists(config_path)

        # Initial login with default password should succeed and create config
        assert auth.verify_login("admin") is True
        assert os.path.exists(config_path)

        # Config file must contain hash and NOT plaintext
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "password_hash" in data
            assert data["password_hash"] != "admin"
            assert "admin" not in data["password_hash"]


def test_auth_manager_change_password_and_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "subdir", ".auth_config.json")
        auth = AuthManager(config_path=config_path, default_password="admin")

        # Authenticate with default
        assert auth.verify_login("admin") is True

        # Validation errors on password change
        ok, msg = auth.change_password("wrong_current", "newpass123", "newpass123")
        assert ok is False
        assert "current password is incorrect" in msg.lower()

        ok, msg = auth.change_password("admin", "newpass123", "mismatch456")
        assert ok is False
        assert "do not match" in msg.lower()

        ok, msg = auth.change_password("admin", "", "")
        assert ok is False
        assert "empty" in msg.lower()

        ok, msg = auth.change_password("admin", "ab", "ab")
        assert ok is False
        assert "at least 4 characters" in msg.lower()

        # Successful password change
        ok, msg = auth.change_password("admin", "newSecurePassword2024!", "newSecurePassword2024!")
        assert ok is True
        assert "successfully" in msg.lower()

        # Old password no longer works
        assert auth.verify_login("admin") is False
        # New password works
        assert auth.verify_login("newSecurePassword2024!") is True

        # Simulate restart by creating a new AuthManager instance pointing to the same file
        auth_restarted = AuthManager(config_path=config_path, default_password="admin")
        assert auth_restarted.verify_login("admin") is False
        assert auth_restarted.verify_login("newSecurePassword2024!") is True


def test_session_state_helpers():
    # Mock streamlit session_state
    mock_st = MagicMock()
    mock_st.session_state = {}
    auth_module.st = mock_st
    auth_module._HAS_STREAMLIT = True

    init_auth_session()
    assert is_authenticated() is False

    login_user()
    assert is_authenticated() is True

    logout_user()
    assert is_authenticated() is False


def test_render_login_screen_unauthenticated():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, ".auth_config.json")
        auth = AuthManager(config_path=config_path, default_password="admin")

        mock_st = MagicMock()
        mock_st.session_state = {"authenticated": False}
        auth_module.st = mock_st
        auth_module._HAS_STREAMLIT = True

        # Mock form submission with incorrect password
        mock_st.form.return_value.__enter__ = MagicMock()
        mock_st.form.return_value.__exit__ = MagicMock()
        mock_st.text_input.return_value = "wrong_password"
        mock_st.form_submit_button.return_value = True

        render_login_screen(auth)
        mock_st.error.assert_called_with("Invalid password. Please try again.")
        assert mock_st.session_state["authenticated"] is False

        # Mock form submission with correct password
        mock_st.text_input.return_value = "admin"
        mock_st.error.reset_mock()
        mock_st.success.reset_mock()

        render_login_screen(auth)
        mock_st.success.assert_called_with("Authentication successful! Redirecting...")
        assert mock_st.session_state["authenticated"] is True


def test_render_auth_controls_logout_and_password_change():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, ".auth_config.json")
        auth = AuthManager(config_path=config_path, default_password="admin")

        mock_st = MagicMock()
        mock_st.session_state = {"authenticated": True}
        auth_module.st = mock_st
        auth_module._HAS_STREAMLIT = True

        # Test logout button click
        mock_st.sidebar.button.return_value = True
        mock_st.sidebar.expander.return_value.__enter__ = MagicMock()
        mock_st.sidebar.expander.return_value.__exit__ = MagicMock()
        mock_st.form.return_value.__enter__ = MagicMock()
        mock_st.form.return_value.__exit__ = MagicMock()
        mock_st.form_submit_button.return_value = False

        render_auth_controls(auth)
        assert mock_st.session_state["authenticated"] is False
