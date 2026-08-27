import hashlib
import hmac
import os
import secrets
import streamlit as st

DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "admin123")
DEFAULT_HASH_FILE = os.getenv(
    "AUTH_PASSWORD_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".password_hash")
)


def hash_password(password: str, salt: str = None) -> str:
    """Hash a password securely using PBKDF2-HMAC-SHA256 with a salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    return f"{salt}${key.hex()}"


def get_stored_hash(hash_file_path: str = None) -> str:
    """Retrieve the stored password hash from the local persistent file, or default hash."""
    if hash_file_path is None:
        hash_file_path = DEFAULT_HASH_FILE
    if os.path.exists(hash_file_path):
        try:
            with open(hash_file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass
    # If no file exists, return the cryptographic hash of the default password
    return hash_password(DEFAULT_PASSWORD, salt="default_careconnect_salt")


def save_password_hash(hashed_password: str, hash_file_path: str = None) -> bool:
    """Persist the hashed password to the local file securely."""
    if hash_file_path is None:
        hash_file_path = DEFAULT_HASH_FILE
    try:
        dirname = os.path.dirname(os.path.abspath(hash_file_path))
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(hash_file_path, "w", encoding="utf-8") as f:
            f.write(hashed_password)
        return True
    except Exception as e:
        if hasattr(st, "error"):
            st.error(f"Failed to save password hash: {e}")
        return False


def verify_password(password: str, stored_hash: str = None, hash_file_path: str = None) -> bool:
    """Verify a plain-text password against a cryptographic hash."""
    if stored_hash is None:
        stored_hash = get_stored_hash(hash_file_path)
    try:
        if "$" not in stored_hash:
            return False
        salt, _ = stored_hash.split("$", 1)
        computed_hash = hash_password(password, salt=salt)
        return hmac.compare_digest(computed_hash, stored_hash)
    except Exception:
        return False


def update_password(current_password: str, new_password: str, hash_file_path: str = None) -> tuple[bool, str]:
    """Validate current password and persist new hashed password."""
    if not verify_password(current_password, hash_file_path=hash_file_path):
        return False, "Incorrect current password."
    if not new_password or not new_password.strip():
        return False, "New password cannot be empty."
    new_hash = hash_password(new_password.strip())
    if save_password_hash(new_hash, hash_file_path=hash_file_path):
        return True, "Password successfully updated."
    return False, "Failed to persist new password."


def initialize_auth_state():
    """Ensure authentication session state variables are initialized."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False


def login_screen(app_title: str = "CareConnect"):
    """Render the login form and handle authentication."""
    st.subheader(f"Login to {app_title}")
    st.info("Please enter your password to access the application.")

    with st.form("login_form"):
        password_input = st.text_input("Password", type="password", placeholder="Enter password")
        submit_button = st.form_submit_button("Log In")

        if submit_button:
            if verify_password(password_input):
                st.session_state.authenticated = True
                st.success("Login successful!")
                if hasattr(st, "rerun"):
                    st.rerun()
            else:
                st.error("Incorrect password. Please try again.")


def logout():
    """Log out the current user and reset session state."""
    st.session_state.authenticated = False
    if hasattr(st, "rerun"):
        st.rerun()


def render_password_change_form(hash_file_path: str = None):
    """Render form to change the user's password."""
    with st.form("change_password_form"):
        st.write("### Change Password")
        current_password = st.text_input("Current Password", type="password", key="current_pwd")
        new_password = st.text_input("New Password", type="password", key="new_pwd")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_pwd")
        submit = st.form_submit_button("Update Password")

        if submit:
            if new_password != confirm_password:
                st.error("New passwords do not match.")
            else:
                success, message = update_password(current_password, new_password, hash_file_path=hash_file_path)
                if success:
                    st.success(message)
                else:
                    st.error(message)


def render_auth_sidebar(hash_file_path: str = None):
    """Render authentication management options in sidebar."""
    st.sidebar.markdown("### Account")
    st.sidebar.write("Status: Logged in")

    with st.sidebar.expander("Change Password"):
        render_password_change_form(hash_file_path=hash_file_path)

    if st.sidebar.button("Log Out", key="logout_btn"):
        logout()


def require_auth(app_title: str = "CareConnect") -> bool:
    """Check authentication status and render login screen if unauthenticated."""
    initialize_auth_state()
    if not st.session_state.authenticated:
        login_screen(app_title)
        return False
    return True
