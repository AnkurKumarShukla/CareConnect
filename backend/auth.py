from __future__ import annotations

import hashlib
import json
import os
import secrets

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False

DEFAULT_PASSWORD = os.getenv("DEFAULT_AUTH_PASSWORD", "admin")
DEFAULT_CONFIG_FILE = os.getenv(
    "AUTH_CONFIG_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".auth_config.json"),
)


def _hash_pbkdf2(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2:{salt}:{key.hex()}"


def _verify_pbkdf2(password: str, hashed: str) -> bool:
    try:
        parts = hashed.split(":", 2)
        if len(parts) != 3:
            return False
        _, salt, key_hex = parts
        check_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(check_key.hex(), key_hex)
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    """Hash a password securely using bcrypt if available, otherwise salted pbkdf2_hmac."""
    if _HAS_BCRYPT:
        try:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        except (ValueError, TypeError, RuntimeError):
            return _hash_pbkdf2(password)
    return _hash_pbkdf2(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plain password against a stored hash (bcrypt or pbkdf2)."""
    if not password or not hashed:
        return False
    if hashed.startswith("pbkdf2:"):
        return _verify_pbkdf2(password, hashed)
    if _HAS_BCRYPT:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError, RuntimeError):
            return False
    return False


class AuthManager:
    """Manages single-user local authentication and password persistence."""

    def __init__(self, config_path: str | None = None, default_password: str | None = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self.default_password = default_password or DEFAULT_PASSWORD

    def get_stored_hash(self) -> str:
        """Read the stored password hash from the local config file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    stored_hash = data.get("password_hash")
                    if stored_hash:
                        return stored_hash
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to read auth config: {e}")
        return ""

    def save_password_hash(self, hashed: str) -> bool:
        """Persist the hashed password to the local config file."""
        try:
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"password_hash": hashed}, f, indent=2)
            return True
        except OSError as e:
            print(f"Error saving auth config: {e}")
            return False

    def verify_login(self, password: str) -> bool:
        """Check if the provided password matches stored hash or default password."""
        stored_hash = self.get_stored_hash()
        if stored_hash:
            return verify_password(password, stored_hash)
        # If no config file exists yet, check against default password
        if password == self.default_password:
            # Initialize config with hashed default password
            self.save_password_hash(hash_password(self.default_password))
            return True
        return False

    def change_password(self, current_password: str, new_password: str, confirm_password: str) -> tuple[bool, str]:
        """Validate and update the password."""
        if not current_password:
            return False, "Current password is required."
        if not self.verify_login(current_password):
            return False, "Current password is incorrect."
        if not new_password:
            return False, "New password cannot be empty."
        if new_password != confirm_password:
            return False, "New password and confirmation do not match."
        if len(new_password) < 4:
            return False, "New password must be at least 4 characters long."

        new_hash = hash_password(new_password)
        if self.save_password_hash(new_hash):
            return True, "Password changed successfully."
        return False, "Failed to persist new password to configuration."


def init_auth_session():
    """Initialize authentication state in Streamlit session_state."""
    if _HAS_STREAMLIT and "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False


def is_authenticated() -> bool:
    """Check if the current session is authenticated."""
    if _HAS_STREAMLIT:
        return bool(st.session_state.get("authenticated", False))
    return False


def login_user():
    """Mark the session as authenticated."""
    if _HAS_STREAMLIT:
        st.session_state["authenticated"] = True


def logout_user():
    """Clear authentication session and reset state."""
    if _HAS_STREAMLIT:
        st.session_state["authenticated"] = False
        if "conversation_handler" in st.session_state:
            st.session_state["conversation_handler"] = None
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()


def render_login_screen(auth_manager: AuthManager | None = None):
    """Render a clean login screen when user is unauthenticated."""
    if not _HAS_STREAMLIT:
        return
    auth = auth_manager or AuthManager()
    st.title("🔒 CareConnect Login")
    st.markdown("Please enter your password to access CareConnect.")

    with st.form("login_form", clear_on_submit=False):
        password_input = st.text_input("Password", type="password", placeholder="Enter password")
        submitted = st.form_submit_button("Log In", use_container_width=True)

        if submitted:
            if not password_input:
                st.error("Please enter a password.")
            elif auth.verify_login(password_input):
                login_user()
                st.success("Authentication successful! Redirecting...")
                if hasattr(st, "rerun"):
                    st.rerun()
                elif hasattr(st, "experimental_rerun"):
                    st.experimental_rerun()
            else:
                st.error("Invalid password. Please try again.")


def render_auth_controls(auth_manager: AuthManager | None = None):
    """Render logout button and password change controls in the sidebar."""
    if not _HAS_STREAMLIT:
        return
    auth = auth_manager or AuthManager()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Account & Security")

    if st.sidebar.button("Log Out", key="logout_btn", use_container_width=True):
        logout_user()

    with st.sidebar.expander("Change Password"), st.form("change_password_form", clear_on_submit=True):
        current_pw = st.text_input("Current Password", type="password", key="cur_pw")
        new_pw = st.text_input("New Password", type="password", key="new_pw")
        confirm_pw = st.text_input("Confirm New Password", type="password", key="conf_pw")
        change_submitted = st.form_submit_button("Update Password", use_container_width=True)

        if change_submitted:
            success, message = auth.change_password(current_pw, new_pw, confirm_pw)
            if success:
                st.success(message)
            else:
                st.error(message)
