import pytest

from backend.auth import (
    SECURITY_QUESTIONS,
    AuthManager,
    initialize_auth_state,
    render_auth_page,
    render_user_sidebar,
)


@pytest.fixture
def auth_mgr():
    """Create AuthManager with isolated dictionary."""
    db = {}
    return AuthManager(users_db=db)


class TestAuthManager:
    def test_initialization(self, auth_mgr):
        assert isinstance(auth_mgr.users, dict)

    def test_password_hashing(self):
        hash1 = AuthManager.hash_password("password123")
        hash2 = AuthManager.hash_password("password123")
        hash3 = AuthManager.hash_password("different_password")
        
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA-256 hexdigest length

    def test_user_registration_success(self, auth_mgr):
        success, msg = auth_mgr.register_user(
            username="john_doe",
            password="SecurePassword1!",
            security_question=SECURITY_QUESTIONS[0],
            security_answer="Smith"
        )
        assert success is True
        assert "Account created successfully" in msg
        assert auth_mgr.user_exists("john_doe")
        assert auth_mgr.user_exists("JOHN_DOE")  # Case insensitive check

    def test_user_registration_validation(self, auth_mgr):
        # Empty username
        success, msg = auth_mgr.register_user("", "pass123")
        assert success is False
        assert "Username cannot be empty" in msg

        # Empty password
        success, msg = auth_mgr.register_user("valid_user", "")
        assert success is False
        assert "Password cannot be empty" in msg

        # Duplicate username
        auth_mgr.register_user("existing_user", "pass123")
        success, msg = auth_mgr.register_user("Existing_User", "new_pass")
        assert success is False
        assert "already exists" in msg

    def test_user_authentication_success(self, auth_mgr):
        auth_mgr.register_user("alice", "AliceSecretPass")
        
        success, msg = auth_mgr.authenticate_user("alice", "AliceSecretPass")
        assert success is True
        assert "Welcome back" in msg

        # Case-insensitive username login
        success, msg = auth_mgr.authenticate_user("ALICE", "AliceSecretPass")
        assert success is True

    def test_user_authentication_failure(self, auth_mgr):
        auth_mgr.register_user("bob", "BobPass123")

        # Wrong password
        success, msg = auth_mgr.authenticate_user("bob", "WrongPass")
        assert success is False
        assert "Invalid username or password" in msg

        # Non-existent user
        success, msg = auth_mgr.authenticate_user("charlie", "AnyPass")
        assert success is False
        assert "Invalid username or password" in msg

        # Empty fields
        success, msg = auth_mgr.authenticate_user("", "")
        assert success is False

    def test_change_password_success(self, auth_mgr):
        auth_mgr.register_user("david", "OldPassword123")

        success, msg = auth_mgr.change_password("david", "OldPassword123", "NewPassword456")
        assert success is True
        assert "Password updated successfully" in msg

        # Old password should no longer authenticate
        success_old, _ = auth_mgr.authenticate_user("david", "OldPassword123")
        assert success_old is False

        # New password should authenticate
        success_new, _ = auth_mgr.authenticate_user("david", "NewPassword456")
        assert success_new is True

    def test_change_password_validation(self, auth_mgr):
        auth_mgr.register_user("eva", "CurrentPass")

        # Wrong current password
        success, msg = auth_mgr.change_password("eva", "WrongCurrent", "NewPass")
        assert success is False
        assert "Current password is incorrect" in msg

        # Empty new password
        success, msg = auth_mgr.change_password("eva", "CurrentPass", "")
        assert success is False
        assert "New password cannot be empty" in msg

        # Same new password
        success, msg = auth_mgr.change_password("eva", "CurrentPass", "CurrentPass")
        assert success is False
        assert "must be different" in msg

        # Non-existent user
        success, msg = auth_mgr.change_password("nonexistent", "CurrentPass", "NewPass")
        assert success is False
        assert "User not found" in msg

    def test_reset_password_success(self, auth_mgr):
        auth_mgr.register_user(
            username="frank",
            password="InitialPassword",
            security_question="What city were you born in?",
            security_answer="New York"
        )

        success, msg = auth_mgr.reset_password("frank", "new york", "ResetPassword789")
        assert success is True
        assert "Password reset successfully" in msg

        # Verify new password works
        auth_success, _ = auth_mgr.authenticate_user("frank", "ResetPassword789")
        assert auth_success is True

    def test_reset_password_validation(self, auth_mgr):
        auth_mgr.register_user(
            username="grace",
            password="Pass1",
            security_question="First pet?",
            security_answer="Buddy"
        )

        # Wrong security answer
        success, msg = auth_mgr.reset_password("grace", "WrongAnswer", "NewPass")
        assert success is False
        assert "Incorrect security answer" in msg

        # Non-existent user
        success, msg = auth_mgr.reset_password("unknown_user", "Buddy", "NewPass")
        assert success is False
        assert "not found" in msg

        # Empty new password
        success, msg = auth_mgr.reset_password("grace", "Buddy", "")
        assert success is False
        assert "New password cannot be empty" in msg

    def test_get_security_question(self, auth_mgr):
        auth_mgr.register_user(
            username="helen",
            password="Pass",
            security_question="Favorite color?",
            security_answer="Blue"
        )

        assert auth_mgr.get_security_question("helen") == "Favorite color?"
        assert auth_mgr.get_security_question("nonexistent") is None

    def test_initialize_auth_state_and_ui_helpers(self):
        initialize_auth_state()
        result = render_auth_page()
        assert result is False
        render_user_sidebar()
