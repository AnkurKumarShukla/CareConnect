import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from backend.auth import (
    hash_password,
    verify_password,
    hash_security_answer,
    verify_security_answer,
    AuthManager,
    init_auth_session_state,
    logout,
    render_auth_ui,
    render_user_menu,
    SECURITY_QUESTIONS,
)


@pytest.fixture
def temp_auth_manager():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    manager = AuthManager(storage_path=path)
    yield manager
    if os.path.exists(path):
        os.remove(path)


def test_hash_and_verify_password():
    password = "SuperSecretPassword123"
    h, salt = hash_password(password)
    assert h and salt
    assert verify_password(password, h, salt) is True
    assert verify_password("WrongPassword", h, salt) is False
    assert verify_password(password, "invalidhash", salt) is False


def test_hash_security_answer():
    ans = "  Fluffy  "
    h, salt = hash_security_answer(ans)
    assert verify_security_answer("fluffy", h, salt) is True
    assert verify_security_answer("FLUFFY", h, salt) is True
    assert verify_security_answer("  Fluffy  ", h, salt) is True
    assert verify_security_answer("Spot", h, salt) is False


def test_auth_signup_validation(temp_auth_manager):
    # Empty username
    success, msg = temp_auth_manager.signup("", "password123")
    assert success is False
    assert "Username cannot be empty" in msg

    # Short username
    success, msg = temp_auth_manager.signup("ab", "password123")
    assert success is False
    assert "at least 3 characters" in msg

    # Empty password
    success, msg = temp_auth_manager.signup("validuser", "")
    assert success is False
    assert "Password cannot be empty" in msg

    # Short password
    success, msg = temp_auth_manager.signup("validuser", "12345")
    assert success is False
    assert "at least 6 characters" in msg

    # Successful signup
    success, msg = temp_auth_manager.signup(
        "testuser",
        "password123",
        security_question=SECURITY_QUESTIONS[0],
        security_answer="Smith"
    )
    assert success is True
    assert "registered successfully" in msg

    # Duplicate username (case-insensitive)
    success, msg = temp_auth_manager.signup("TestUser", "newpassword123")
    assert success is False
    assert "already exists" in msg


def test_auth_login(temp_auth_manager):
    temp_auth_manager.signup("alice", "Password123")

    # Correct credentials
    success, msg = temp_auth_manager.login("alice", "Password123")
    assert success is True
    assert "Login successful" in msg

    # Case-insensitive username login
    success, msg = temp_auth_manager.login("ALICE", "Password123")
    assert success is True

    # Wrong password
    success, msg = temp_auth_manager.login("alice", "WrongPassword")
    assert success is False
    assert "Invalid username or password" in msg

    # Non-existent user
    success, msg = temp_auth_manager.login("bob", "Password123")
    assert success is False
    assert "Invalid username or password" in msg

    # Empty fields
    success, msg = temp_auth_manager.login("", "Password123")
    assert success is False


def test_auth_change_password(temp_auth_manager):
    temp_auth_manager.signup("bob", "OldPassword123")

    # Non-existent user
    success, msg = temp_auth_manager.change_password("unknown", "OldPassword123", "NewPassword123")
    assert success is False
    assert "User not found" in msg

    # Incorrect current password
    success, msg = temp_auth_manager.change_password("bob", "WrongOld", "NewPassword123")
    assert success is False
    assert "Current password is incorrect" in msg

    # Same password
    success, msg = temp_auth_manager.change_password("bob", "OldPassword123", "OldPassword123")
    assert success is False
    assert "cannot be the same" in msg

    # Short new password
    success, msg = temp_auth_manager.change_password("bob", "OldPassword123", "123")
    assert success is False
    assert "at least 6 characters" in msg

    # Valid change
    success, msg = temp_auth_manager.change_password("bob", "OldPassword123", "NewPassword123")
    assert success is True
    assert "Password changed successfully" in msg

    # Verify old password no longer works, new password works
    assert temp_auth_manager.login("bob", "OldPassword123")[0] is False
    assert temp_auth_manager.login("bob", "NewPassword123")[0] is True


def test_auth_reset_password(temp_auth_manager):
    temp_auth_manager.signup(
        "charlie",
        "InitialPwd123",
        security_question="What is your favorite book or movie?",
        security_answer="Inception"
    )

    # Check security question retrieval
    q = temp_auth_manager.get_security_question("charlie")
    assert q == "What is your favorite book or movie?"
    assert temp_auth_manager.get_security_question("nonexistent") is None

    # Reset with wrong answer
    success, msg = temp_auth_manager.reset_password("charlie", "Titanic", "RecoveredPwd123")
    assert success is False
    assert "Incorrect security answer" in msg

    # Reset with short password
    success, msg = temp_auth_manager.reset_password("charlie", "inception", "123")
    assert success is False
    assert "at least 6 characters" in msg

    # Valid reset (case-insensitive answer)
    success, msg = temp_auth_manager.reset_password("charlie", "  INCEPTION  ", "RecoveredPwd123")
    assert success is True
    assert "Password reset successfully" in msg

    # Verify login with new password
    assert temp_auth_manager.login("charlie", "InitialPwd123")[0] is False
    assert temp_auth_manager.login("charlie", "RecoveredPwd123")[0] is True

    # User without security question
    temp_auth_manager.signup("dave", "DavePassword123")
    success, msg = temp_auth_manager.reset_password("dave", "anything", "NewDavePwd123")
    assert success is False
    assert "No security question configured" in msg


def test_persistence(temp_auth_manager):
    temp_auth_manager.signup("persisted_user", "PersistPass123")

    # Create new manager pointing to the same file
    new_manager = AuthManager(storage_path=temp_auth_manager.storage_path)
    assert new_manager.user_exists("persisted_user") is True
    assert new_manager.login("persisted_user", "PersistPass123")[0] is True


class MockSessionState(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]
        else:
            raise AttributeError(key)


def test_session_state_and_ui_helpers(temp_auth_manager):
    mock_state = MockSessionState()
    with patch("streamlit.session_state", mock_state), \
         patch("streamlit.rerun") as mock_rerun:

        init_auth_session_state()
        assert mock_state.authenticated is False
        assert mock_state.username is None

        # Test render_auth_ui when not authenticated
        with patch("streamlit.tabs") as mock_tabs, \
             patch("streamlit.form") as mock_form, \
             patch("streamlit.text_input") as mock_text, \
             patch("streamlit.selectbox") as mock_select, \
             patch("streamlit.form_submit_button") as mock_submit:
            mock_tab = MagicMock()
            mock_tabs.return_value = [mock_tab, mock_tab, mock_tab]
            mock_form.return_value.__enter__.return_value = MagicMock()
            mock_submit.return_value = False

            auth_result = render_auth_ui(temp_auth_manager)
            assert auth_result is False

        # Now authenticate
        mock_state.authenticated = True
        mock_state.username = "alice"
        auth_result = render_auth_ui(temp_auth_manager)
        assert auth_result is True

        # Test render_user_menu
        with patch("streamlit.sidebar") as mock_sidebar:
            mock_sidebar.button.return_value = False
            render_user_menu(temp_auth_manager)
            mock_sidebar.markdown.assert_called()

        # Test logout
        logout()
        assert mock_state.authenticated is False
        assert mock_state.username is None
        mock_rerun.assert_called()
