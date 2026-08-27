import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock, patch

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.auth import (
    DEFAULT_PASSWORD,
    hash_password,
    get_stored_hash,
    save_password_hash,
    verify_password,
    update_password,
    initialize_auth_state,
    login_screen,
    logout,
    render_password_change_form,
    render_auth_sidebar,
    require_auth,
)


class TestPasswordHashing:
    def test_hash_password_format(self):
        h = hash_password("secret123")
        assert "$" in h
        salt, key_hex = h.split("$", 1)
        assert len(salt) == 32  # 16 bytes in hex
        assert len(key_hex) == 64  # SHA-256 is 32 bytes = 64 hex chars

    def test_hash_password_deterministic_with_salt(self):
        salt = "testsalt12345678"
        h1 = hash_password("my_password", salt=salt)
        h2 = hash_password("my_password", salt=salt)
        assert h1 == h2

    def test_hash_password_different_salts(self):
        h1 = hash_password("my_password")
        h2 = hash_password("my_password")
        assert h1 != h2

    def test_hash_password_different_passwords(self):
        salt = "testsalt12345678"
        h1 = hash_password("password1", salt=salt)
        h2 = hash_password("password2", salt=salt)
        assert h1 != h2


class TestPasswordVerification:
    def test_verify_password_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = os.path.join(tmpdir, "nonexistent.hash")
            assert verify_password(DEFAULT_PASSWORD, hash_file_path=temp_file) is True
            assert verify_password("wrong_password", hash_file_path=temp_file) is False

    def test_verify_password_with_stored_hash(self):
        hashed = hash_password("supersecret")
        assert verify_password("supersecret", stored_hash=hashed) is True
        assert verify_password("wrongsecret", stored_hash=hashed) is False

    def test_verify_password_invalid_hash(self):
        assert verify_password("any", stored_hash="invalid_hash_without_dollar") is False
        assert verify_password("any", stored_hash="") is False


class TestPasswordPersistence:
    def test_save_and_get_stored_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = os.path.join(tmpdir, "subdir", ".password_hash")
            hashed = hash_password("new_persisted_password")
            
            # Save hash
            assert save_password_hash(hashed, hash_file_path=temp_file) is True
            assert os.path.exists(temp_file)
            
            # Plaintext password is NEVER stored in the file
            with open(temp_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert "new_persisted_password" not in content
                assert content == hashed

            # Retrieve stored hash across simulated restart
            loaded_hash = get_stored_hash(hash_file_path=temp_file)
            assert loaded_hash == hashed
            assert verify_password("new_persisted_password", hash_file_path=temp_file) is True
            assert verify_password(DEFAULT_PASSWORD, hash_file_path=temp_file) is False


class TestUpdatePassword:
    def test_update_password_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = os.path.join(tmpdir, ".password_hash")
            
            # Initial default password works
            assert verify_password(DEFAULT_PASSWORD, hash_file_path=temp_file) is True
            
            # Change password from default to new password
            success, msg = update_password(DEFAULT_PASSWORD, "brand_new_pass_456", hash_file_path=temp_file)
            assert success is True
            assert "successfully" in msg.lower()
            
            # Now default password fails and new password succeeds
            assert verify_password(DEFAULT_PASSWORD, hash_file_path=temp_file) is False
            assert verify_password("brand_new_pass_456", hash_file_path=temp_file) is True

    def test_update_password_incorrect_current(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = os.path.join(tmpdir, ".password_hash")
            success, msg = update_password("wrong_curr_pass", "new_pass", hash_file_path=temp_file)
            assert success is False
            assert "incorrect current password" in msg.lower()

    def test_update_password_empty_new_password(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = os.path.join(tmpdir, ".password_hash")
            success, msg = update_password(DEFAULT_PASSWORD, "   ", hash_file_path=temp_file)
            assert success is False
            assert "empty" in msg.lower()


class TestStreamlitAuthFlows:
    @pytest.fixture(autouse=True)
    def setup_session_state(self):
        import streamlit as st
        st.session_state.clear()
        yield
        st.session_state.clear()

    def test_initialize_auth_state(self):
        import streamlit as st
        assert "authenticated" not in st.session_state
        initialize_auth_state()
        assert st.session_state.authenticated is False

    @patch("streamlit.form")
    @patch("streamlit.text_input")
    @patch("streamlit.form_submit_button")
    @patch("streamlit.success")
    @patch("streamlit.error")
    @patch("streamlit.rerun")
    def test_login_screen_correct_password(self, mock_rerun, mock_error, mock_success, mock_submit, mock_text, mock_form):
        import streamlit as st
        initialize_auth_state()
        mock_submit.return_value = True
        mock_text.return_value = DEFAULT_PASSWORD

        login_screen("CareConnect")

        assert st.session_state.authenticated is True
        mock_success.assert_called_once_with("Login successful!")
        mock_rerun.assert_called_once()
        mock_error.assert_not_called()

    @patch("streamlit.form")
    @patch("streamlit.text_input")
    @patch("streamlit.form_submit_button")
    @patch("streamlit.success")
    @patch("streamlit.error")
    @patch("streamlit.rerun")
    def test_login_screen_incorrect_password(self, mock_rerun, mock_error, mock_success, mock_submit, mock_text, mock_form):
        import streamlit as st
        initialize_auth_state()
        mock_submit.return_value = True
        mock_text.return_value = "invalid_password"

        login_screen("CareConnect")

        assert st.session_state.authenticated is False
        mock_error.assert_called_once_with("Incorrect password. Please try again.")
        mock_success.assert_not_called()
        mock_rerun.assert_not_called()

    @patch("streamlit.rerun")
    def test_logout(self, mock_rerun):
        import streamlit as st
        st.session_state.authenticated = True
        logout()
        assert st.session_state.authenticated is False
        mock_rerun.assert_called_once()

    @patch("backend.auth.login_screen")
    def test_require_auth_unauthenticated(self, mock_login):
        import streamlit as st
        st.session_state.authenticated = False
        result = require_auth("CareConnect")
        assert result is False
        mock_login.assert_called_once_with("CareConnect")

    @patch("backend.auth.login_screen")
    def test_require_auth_authenticated(self, mock_login):
        import streamlit as st
        st.session_state.authenticated = True
        result = require_auth("CareConnect")
        assert result is True
        mock_login.assert_not_called()

    @patch("streamlit.form")
    @patch("streamlit.text_input")
    @patch("streamlit.form_submit_button")
    @patch("streamlit.success")
    @patch("streamlit.error")
    def test_render_password_change_mismatch(self, mock_error, mock_success, mock_submit, mock_text, mock_form):
        mock_submit.return_value = True
        mock_text.side_effect = [DEFAULT_PASSWORD, "newpass1", "newpass2"]

        render_password_change_form()

        mock_error.assert_called_once_with("New passwords do not match.")
        mock_success.assert_not_called()

    @patch("streamlit.form")
    @patch("streamlit.text_input")
    @patch("streamlit.form_submit_button")
    @patch("streamlit.success")
    @patch("streamlit.error")
    def test_render_password_change_success(self, mock_error, mock_success, mock_submit, mock_text, mock_form):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = os.path.join(tmpdir, ".password_hash")
            mock_submit.return_value = True
            mock_text.side_effect = [DEFAULT_PASSWORD, "validNewPass", "validNewPass"]

            render_password_change_form(hash_file_path=temp_file)

            mock_success.assert_called_once_with("Password successfully updated.")
            mock_error.assert_not_called()
            assert verify_password("validNewPass", hash_file_path=temp_file) is True
